@echo off
set vodid=%1
set json=%2
set mp4=%3
CD %~dp0
TwitchDownloaderCLI.exe chatdownload --id %vodid% -o %json% -E
TwitchDownloaderCLI.exe chatrender -i %json% -o %mp4% --background-color #FF111111 -w 500 -h 1080 --outline true -f Arial --font-size 22 --update-rate 1.0 --offline --ffmpeg-path ./ffmpeg.exe --temp-path ./temp