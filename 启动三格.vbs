Option Explicit
Dim shell, fso, exe, appDir, homeDir, launchArgs
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
homeDir = shell.ExpandEnvironmentStrings("%USERPROFILE%")
appDir = fso.GetParentFolderName(WScript.ScriptFullName) & "\desktop"
exe = appDir & "\node_modules\electron\dist\electron.exe"
If Not fso.FileExists(exe) Then exe = homeDir & "\.codex\whale-widget\desktop-runtime\node_modules\electron\dist\electron.exe"
launchArgs = ""
If WScript.Arguments.Named.Exists("autostart") Then launchArgs = " --autostart"
If Not fso.FileExists(exe) Then
  MsgBox "首次使用请先在 desktop 目录安装依赖，再启动三格。", 16, "三格"
  WScript.Quit 1
End If
shell.Run """" & exe & """ """ & appDir & """" & launchArgs, 0, False
