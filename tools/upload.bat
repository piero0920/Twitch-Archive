@echo off
set root_path=%1
set user=%2
FOR /F "eol=# tokens=*" %%i in (%~dp0\..\.env) do SET %%i
CD %~dp0
rclone.exe copy ../%root_path%/%user% %remote%/%root_path%/%user% --progress --drive-chunk-size 512M