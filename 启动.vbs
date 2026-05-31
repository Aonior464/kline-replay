Set ws = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
dir = fso.GetParentFolderName(WScript.ScriptFullName)

' 后台启动Python后端（无窗口）
ws.Run "cmd /c cd /d """ & dir & """ && python backend.py", 0, False

' 等2秒让后端启动
WScript.Sleep 2000

' 打开网页
ws.Run """" & dir & "\kline-replay.html""", 1, False
