# agent-toolbox

AI agent 实操过的工具/流程 runbook 集合。每篇都是**真实跑通并验证过**的记录，
供 AI（或人）照着复现。写作标准见下方规范，模板见 [TEMPLATE.md](TEMPLATE.md)。

## 索引

| 目录 | 主题 | 状态 |
|---|---|---|
| [tvbox-video/](tvbox-video/) | Windows 下 TVBox/zyfun 在线点播 + 4K 磁链下载 + B 站弹幕转 ASS + mpv 播放全流程 | 已验证 2026-10-11 |
| [tabbit-browser-automation/](tabbit-browser-automation/) | WSL → Windows 调 tabbit-cli 驱动 Tabbit Browser：开页/接管标签页、注入 Playwright JS、取页面内容 | 已验证 2026-10-11 |
| [windows-window-automation/](windows-window-automation/) | 后台/非侵入窗口自动化矩阵：UIA（pywinauto）读写+点按钮、Win32 消息、PrintWindow 遮挡截图；含锁屏/最小化/自绘控件实测边界 | 已验证 2026-10-11 |
| [wmm-backend-api/](wmm-backend-api/) | Wyccc Mod Manager backend.api 进程内调用：playset / scan_mods / 深度冲突报告 | 已验证 2026-10-11 |
| [steam-web-api/](steam-web-api/) | Steam Web API 无 key 端点查工坊条目元数据（GetPublishedFileDetails） | 已验证 2026-10-11 |
| [github-rest-api/](github-rest-api/) | GitHub REST 匿名只读：rate_limit / 仓库元数据 / contents / raw 文件 | 已验证 2026-10-11 |
| [wsl-windows-interop/](wsl-windows-interop/) | WSL↔Windows 通道：cmd.exe、wslpath、Windows Python、GCM 推送、$剥离/CRLF/9P 延迟、node/PowerShell 桥（winnode.sh/winps.sh）、90 会话复盘坑表 | 已验证 2026-10-14 |

| [qoder-acp/](qoder-acp/) | ACP 协议解剖 + Qoder CLI 的 ACP 模式（qoder --acp / Zed 接入 / 权限与终端反向能力）+ ACP Registry 分发路径 | 文档整理+部分实测 2026-10-13 |
| [cline-pass/](cline-pass/) | Cline Pass 订阅全流程：KOL 80 码首月 ~¥15、Stripe 收银台/卡组织坑、API key + cline CLI 配置、上游路由实测 | 已验证 2026-10-18 |

> 新增工具记录时，在本表登记一行，保持索引与目录同步。

## 外部参考

写新 runbook 前先查 [REFERENCES.md](REFERENCES.md)：按「元索引 / Agent 技能库 / MCP 服务 / 桌面 UI 自动化 / 浏览器自动化 / 资源获取 / 三方 API 集成 / 可执行 runbook」分类的同类合集索引，能站轮子就别重造。

## 仓库规范（新增记录必须遵守）

### 1. 目录结构

```
<tool-or-topic>/          # 一个主题一个目录，kebab-case 命名
├── README.md             # 必需，面向 AI 的操作手册
└── scripts/              # 示例代码/脚本一律放这里，README 用相对路径引用
```

根目录只放仓库级文件（本 README、TEMPLATE、许可证），不放具体工具的散文件。

### 2. README.md 必备章节（按此顺序）

1. **概述**：这个工具/流程做什么，最终效果一句话
2. **环境前提**：操作系统、依赖软件及安装命令
3. **操作步骤**：编号步骤 + 命令块 + 每步预期输出——**必须写成 AI 能逐步执行的形式**，不要写成散文叙述
4. **验证方法**：怎么确认它真的成功了（实测命令 + 期望结果，不接受只看 exit code）
5. **已知坑**：踩过的坑及规避方法，标注 `[实测]` 或 `[需验证]`
6. **文件清单**：scripts/ 里每个文件一行说明

### 3. 路径规范

- **禁止写死个人路径**（`C:\Users\<用户名>\`、`/home/<用户名>/`、内网 IP 等）
- 一律用环境变量或占位符：`%APPDATA%`、`%LOCALAPPDATA%`、`$HOME`、`<WORK_DIR>`、`<INTERFACE_IP>`
- 标准安装路径（如 `C:\Program Files\<App>\`）可保留，但注明"默认安装位置"
- 本机实测过的具体取值（IP、网卡名、域名白名单等）放「验证记录」小节，并标注是本机示例

### 4. 可信度规范

- 只记录**实际跑通过**的步骤；没验证过的标注 `[需验证]`
- 时效性内容（接口地址、源列表、版本号）标注验证日期
- 验证证据（分辨率、条数、文件大小等硬指标）写进「验证方法」，不要只写"可行"
