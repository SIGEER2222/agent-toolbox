@echo off
rem verify.cmd — joinguard regression suite (real stub path + wsl non-e)
rem Expected markers noted per line. Run: verify.cmd
set B=C:\Windows\System32\bash.exe

echo == $ family ==
%B% -c "echo A1_svar:$HOME:END"            rem /home/<user>
%B% -c "echo A2_sq:'$HOME':END"            rem $HOME literal
%B% -c "x=abc; echo A3_var:x=$x"           rem x=abc
%B% -c "echo A4_arith:$((3+4*5))"          rem 23
%B% -c "echo A5_subst:$(echo inner)"       rem inner
%B% -c "echo A6_btick:`echo btick`"        rem btick
%B% -c "echo A7_pid:$$"                    rem real pid
%B% -c "echo A8_default:${NOPE_X:-fb}:END" rem fb
%B% -c "v=7; echo A9_escaped:\$v"          rem $v LITERAL (std semantics)

echo == syntax ==
%B% -c "echo c1 | tr a-z A-Z"
%B% -c "true && echo C2_ok || echo bad"
%B% -c "(cd /tmp;pwd);cd /etc;pwd"
%B% -c "if [ 1 -eq 1 ];then echo C4_if;fi"
%B% -c "a=(x y);echo C5_arr:${a[1]}"
%B% -c "for i in 1 2;do echo C6_$i;done"
%B% -c "f(){ echo C7_f;};f"
%B% -c "cat <(echo C8_psub)"

echo == redirects ==
%B% -c "echo D1 >/tmp/vd.txt;cat /tmp/vd.txt"
%B% -c "ls /nope_xyz 2>/tmp/ve.txt;head -c 10 /tmp/ve.txt;echo :D2"
%B% -c "read v </etc/hostname;echo D3:$v"

echo == errors ==
%B% -c "nonexistent_cmd 2>/dev/null;echo E1_rc:$?"   rem 127
%B% -c "exit 7"
echo E2_exitcode=%ERRORLEVEL%                         rem 7
%B% -c "echo E3_err >&2; echo E3_out"

echo == nested/flag shapes ==
%B% -c "bash -c 'echo N1_inner:$HOME'"
%B% -c "sh -c 'echo N2_sh:$HOME'"
%B% -lc "echo N3_lc:$HOME"
%B% -ex -c "n=4;echo N4_ex:$n" 2>NUL
%B% --noprofile --norc -c "echo N5_np:$HOME"
%B% --version
echo echo N6_stdin | %B% -s
%B% -c "echo PA_$0_PA" arg0val                        rem PA_arg0val_PA

echo == wsl.exe non-e ==
wsl.exe bash -c "echo 'W1_sq:$HOME':END"              rem literal
wsl.exe bash -c "w=2;echo W2_var:$w"                  rem 2
wsl.exe sh -c "echo 'W3_sh:$HOME':END"                rem literal
wsl.exe bash -lc "echo 'W4_trail:$HOME':END" " "
wsl.exe -u root bash -c "echo 'W5_root:$HOME':END;id -u"
wsl.exe -e bash -c "echo 'W6_exec:$HOME':END"         rem literal
wsl.exe --cd /tmp bash -c "pwd"                        rem /tmp
wsl.exe bash -c "echo W8_pos_$0" pname                rem pname

echo == done ==
