#!/bin/sh
$(dirname "$0")/TwitchDownloaderCLI -m ChatDownload --id $1 -o $2 --embed-emotes
$(dirname "$0")/TwitchDownloaderCLI -m ChatRender -i $2 -o $3 --background-color "#FF111111" -w 500 -h 1080 --outline true -f Arial --font-size 22 --update-rate 1.0 --ffmpeg-path $(dirname "$0")/ffmpeg --temp-path $(dirname "$0")/temp