Set ws = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
Set http = CreateObject("MSXML2.XMLHTTP.6.0")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
logFile = dir & "\backend.log"
htmlFile = dir & "\kline-replay.html"

' 后台启动Python后端
ws.Run "cmd /c cd /d """ & dir & """ && python backend.py > """ & logFile & """ 2>&1", 0, False

' 轮询等待后端就绪（最多15秒）
ready = False
For i = 1 To 30
    WScript.Sleep 500
    On Error Resume Next
    http.Open "GET", "http://localhost:8000/api/health", False
    http.Send
    If Err.Number = 0 And http.Status = 200 Then
        ready = True
        Exit For
    End If
    On Error GoTo 0
Next

If ready Then
    ws.Run """" & htmlFile & """", 1, False
Else
    msg = "后端启动失败，请检查：" & vbCrLf & vbCrLf
    msg = msg & "1. Python 是否已安装" & vbCrLf
    msg = msg & "2. 依赖是否已安装 (pip install -r requirements.txt)" & vbCrLf
    msg = msg & "3. 查看 backend.log 了解详情"
    MsgBox msg, vbExclamation, "K线回放"
End If
