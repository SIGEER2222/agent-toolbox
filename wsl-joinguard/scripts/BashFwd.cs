// bashfwd — bash.exe shim: forwards argv verbatim into WSL via
// `wsl.exe -e bash <args...>` (direct argv exec, no joining shell).
//
// ── 根因 ────────────────────────────────────────────────────────────────
// devin.exe (Windows) 探 bash 的顺序：%SystemRoot%\System32\bash.exe →
// where.exe(排除 system32/windowsapps) → Git\bin\bash.exe 探测路径。
// 本机无 Git Bash → 永远命中 System32\bash.exe（WSL 启动器 stub）。
// stub 调 `wsl.exe bash -c "<CMD>"`（非 -e）：wsl 把 argv 拼回命令行交
// /bin/bash -c 解析 —— 外层 bash 对 "<CMD>" 做一次双引号展开，
// $VAR/$$/$(...) 全部先被外层吃掉（CMD 内单引号在外层只是字面字符，
// 不保护），展开结果才作为 -c 参数交给内层 bash。
// `wsl.exe -e` = 直接 exec，argv 逐字传递 → 单次展开，语义正常。
//
// ── 两种装载方式 ────────────────────────────────────────────────────────
// 1) IFEO Debugger（HKLM 一次注册，需一次提权；注意火绒等 HIPS 会
//    静默拦截 IFEO Debugger 写入——拦了就用 joinguard 方案）：
//      HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\
//        Image File Execution Options\bash.exe
//      Debugger = <本 exe 的绝对路径>
//    IFEO 触发时本 exe 的 argv = [self, <原 image>, <原 args...>]；
//    原 image 是已知 WSL stub（system32/windowsapps 下的 bash.exe 或裸
//    名字 bash）→ 参数转发 wsl -e；非 stub 路径（如未来真 Git Bash）→
//    原样 exec 透传，不改变其行为。
// 2) PATH/探测位放置：把本 exe 改名 bash.exe 放到调用方会找到的
//    目录（如 %LOCALAPPDATA%\Programs\Git\bin\bash.exe）——对按名字
//    找 bash 的调用方生效；对写死 System32 绝对路径的调用方不生效。
//
// ── 行为 ────────────────────────────────────────────────────────────────
//   - 参数逐字转发（MSVCRT 引号规则）。
//   - 非 -c/-s 载荷的独立 Windows 路径参数 X:\foo → /mnt/x/foo。
//   - 继承 stdin/stdout/stderr 与 cwd（wsl -e 自动把 Windows cwd 译成
//     /mnt/<盘>）；退出码透传。
//   - 调试日志：环境变量 BASHFWD_LOG=<file> 追加 argv+cwd。
//   - 防递归：wsl -e 跑的是 Linux /bin/bash，不会再碰 bash.exe。

using System;
using System.Diagnostics;
using System.IO;
using System.Text;

public static class BashFwd
{
    static string Quote(string s)
    {
        var sb = new StringBuilder(s.Length + 2);
        sb.Append('"');
        int bs = 0;
        foreach (char c in s)
        {
            if (c == '\\') { bs++; continue; }
            if (c == '"') { sb.Append('\\', bs * 2 + 1).Append('"'); bs = 0; continue; }
            if (bs > 0) { sb.Append('\\', bs); bs = 0; }
            sb.Append(c);
        }
        if (bs > 0) sb.Append('\\', bs * 2);
        sb.Append('"');
        return sb.ToString();
    }

    static bool IsStubImage(string s)
    {
        // 裸名字 / 已知 WSL stub 路径 -> true；其他全路径 -> false（exec 透传）
        if (string.IsNullOrEmpty(s)) return false;
        var n = s.Replace('/', '\\').ToLowerInvariant();
        if (n == "bash" || n == "bash.exe") return true;
        if (n.EndsWith("\\system32\\bash.exe")) return true;
        if (n.EndsWith("\\windowsapps\\bash.exe")) return true;
        return false;
    }

    static bool LooksLikeImage(string s)
    {
        if (string.IsNullOrEmpty(s)) return false;
        var n = s.Replace('/', '\\').ToLowerInvariant();
        return n == "bash" || n.EndsWith("\\bash.exe") || n.EndsWith("/bash.exe") || n == "bash.exe";
    }

    // IFEO matches the image FILENAME — launching any *bash.exe re-triggers
    // the debugger (incl. our own copies). A real non-stub bash is run via a
    // renamed copy so its filename no longer matches the IFEO key.
    static string EnsureRealCopy(string image)
    {
        try
        {
            string dir = Path.Combine(Path.GetTempPath(), "bashfwd");
            Directory.CreateDirectory(dir);
            string dst = Path.Combine(dir,
                "real-" + Math.Abs(image.GetHashCode()).ToString("x") + ".exe");
            if (!File.Exists(dst) ||
                new FileInfo(dst).Length != new FileInfo(image).Length)
            {
                File.Copy(image, dst, true);
            }
            return dst;
        }
        catch { return null; }
    }

    static string ToMnt(string p)
    {
        if (p.Length >= 3 && char.IsLetter(p[0]) && p[1] == ':' &&
            (p[2] == '\\' || p[2] == '/'))
        {
            var rest = p.Substring(2).Replace('\\', '/');
            return "/mnt/" + char.ToLowerInvariant(p[0]) + rest;
        }
        return p;
    }

    static int Run(string exe, string argLine)
    {
        var psi = new ProcessStartInfo(exe, argLine) { UseShellExecute = false };
        try
        {
            using (var p = Process.Start(psi))
            {
                p.WaitForExit();
                return p.ExitCode;
            }
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine("bashfwd: launch " + exe + " failed: " + ex.Message);
            return 127;
        }
    }

    public static int Main(string[] args)
    {
        string image = null;
        // IFEO Debugger 形态：argv[0] 是原 image 名/路径
        if (args.Length > 0 && LooksLikeImage(args[0]))
        {
            image = args[0];
            var rest = new string[args.Length - 1];
            Array.Copy(args, 1, rest, 0, rest.Length);
            args = rest;
        }

        // 非 stub 的真实 bash（例如未来安装的 Git Bash）：经改名副本透传
        // （直接跑原名会再次命中 IFEO -> 无限递归）
        if (image != null && !IsStubImage(image) && image.IndexOf(':') >= 0)
        {
            string real = EnsureRealCopy(image);
            if (real != null)
            {
                var through = new StringBuilder();
                foreach (var a in args) { if (through.Length > 0) through.Append(' '); through.Append(Quote(a)); }
                return Run(real, through.ToString());
            }
            // 副本失败 -> 退化到 wsl -e
        }

        var cl = new StringBuilder("-e bash");
        bool nextIsPayload = false;
        foreach (var raw in args)
        {
            string a = raw;
            if (!nextIsPayload && a != null && a.Length >= 3 &&
                char.IsLetter(a[0]) && a[1] == ':' && (a[2] == '\\' || a[2] == '/'))
            {
                a = ToMnt(a);
            }
            cl.Append(' ').Append(Quote(a));
            nextIsPayload = (raw == "-c" || raw == "-s");
        }

        string log = Environment.GetEnvironmentVariable("BASHFWD_LOG");
        if (!string.IsNullOrEmpty(log))
        {
            try
            {
                File.AppendAllText(log,
                    DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss.fff") +
                    " img=" + (image ?? "-") + " cwd=" + Environment.CurrentDirectory +
                    " | wsl.exe " + cl + Environment.NewLine);
            }
            catch { }
        }

        return Run(@"C:\Windows\System32\wsl.exe", cl.ToString());
    }
}
