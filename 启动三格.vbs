Option Explicit
Dim shell, fso, exe, appDir, homeDir, launchArgs
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
homeDir = shell.ExpandEnvironmentStrings("%USERPROFILE%")
exe = homeDir & "\.codex\whale-widget\desktop-runtime\node_modules\electron\dist\electron.exe"
appDir = homeDir & "\Documents\deepseek-harness\default-workspace\triage\desktop"
launchArgs = ""
If WScript.Arguments.Named.Exists("autostart") Then launchArgs = " --autostart"
If Not fso.FileExists(exe) Then
  MsgBox "找不到 Electron 运行时：" & vbCrLf & exe, 16, "三格"
  WScript.Quit 1
End If
shell.Run """" & exe & """ """ & appDir & """" & launchArgs, 0, False
