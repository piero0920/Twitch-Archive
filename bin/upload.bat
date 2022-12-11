@echo off
set root_path=%1
set user=%2
if "%root_path:~-1%" == "\" set "root_path_1=%root_path:~0,-1%"
for %%f in ("%root_path_1%") do set "root_path_name=%%~nxf"
FOR /F "eol=# tokens=*" %%i in (%~dp0\..\.env) do SET %%i
CD %~dp0
rclone.exe copy %root_path%/%user% %remote%/%root_path_name%/%user% --progress --include-from %~dp0/temp/upload.txt