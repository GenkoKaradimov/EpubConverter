' Run EpubConverter without showing a console window (Windows).
' Double-click this file to start the app with only the GUI visible.
' (Alternatively, double-click run.pyw for the same result.)
Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.Run "pythonw run.pyw", 0, False
