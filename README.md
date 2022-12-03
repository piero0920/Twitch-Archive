# Twitch Archive
Inspired by https://github.com/EnterGin/Auto-Stream-Recording-Twitch

Python script to monitor a twitch channel:
## Requirements
- [Python 3](https://www.python.org/downloads/)
- [Streamlink](https://github.com/streamlink/streamlink)
## Getting started
1. Install Python 3
2. Install Streamlink
3. If you want to upload to a remote service using rclone, [configure it](https://rclone.org/docs/#configure) (Doesnt need to download, the `rclone.exe` is avalible in [tools/rclone.exe](https://github.com/piero0920/Twitch-Archive/blob/main/tools/rclone.exe)).
4. `git clone https://github.com/piero0920/Twitch-Archive.git`
5. `cd Twitch-Archive`
6. `pip install -r requirements.txt`
7. Edit the `.env.sample` and rename it to `.env`
```.env
CLIENT-ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
CLIENT-SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OAUTH-PRIVATE-TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```
8. if you want to enable/disable more available options, open `twitch-archive.py`
9. run `Python twitch-archive.py` or for multiple streamers `Python twitch-archive.py -u streamer` 
## Features 
- Auto records the live stream
- Downloads the VOD after stream ended
- Downloads the chat logs of the VOD and renders it 
- Downloads the metadata of the VOD
- Uploads them to the Cloud
- Notifies you through Gmail of the progress 

## Explanation
### Record live stream:
Using [Streamlink](https://streamlink.github.io/) downloads the `.ts` file from the live stream since the script starred running, if the script was running since before the beginning of the stream, it will record everything and save it to: `/root_path/streamer_username/video/recorded/LIVE_yyyymmdd_hhmmss.ts`

This option will need a oauth-token to record without ADS.
After the stream ended, the `.ts` file will be processed to `.mp4` file. using [ffmpeg](https://ffmpeg.org/) and save it to: `/root_path/streamer_username/video/processed/LIVE_yyyymmdd_hhmmss.mp4`
> [Here's](https://youtu.be/1MBsUoFGuls) a tutorial that shows you how to get the oauth-token.
### Download VOD
Using [Streamlink](https://streamlink.github.io/) downloads the `.ts` file from the VOD, the download is faster and is available to get the unmuted segments before twitch mutes the entire VOD. it will be save it to: `/root_path/streamer_username/video/recorded/VOD_yyyymmdd_hhmmss.ts`

Then the `.ts` file will be processed to `.mp4` file. using [ffmpeg](https://ffmpeg.org/) and save it to: `/root_path/streamer_username/video/processed/VOD_yyyymmdd_hhmmss.mp4`
This option will Download the latest public VOD, if the streamer hasn't published or has hide the VOD, the current VOD will no be downloaded instead the previous VOD.
### Download and render chat   
 Using [TwitchDownloaderCLI](https://github.com/lay295/TwitchDownloader) downloads the `.json` file of the chat logs from the VOD, ands saves it to: `/root_path/streamer_username/chat/json/CHAT_yyyymmdd_hhmmss.json`
 
 Then after the `.json` file is downloaded using again [TwitchDownloaderCLI](https://github.com/lay295/TwitchDownloader) renders it to a viewable `.mp4` file and saves it to:
 `/root_path/streamer_username/chat/rendered/CHAT_yyyymmdd_hhmmss.mp4`
 
 If you want to change the rendered settings go to [chat.bat]() file and change the parameters:
 `--background-color #FF111111 -w 500 -h 1080 --outline true -f Arial --font-size 22 --update-rate 1.0`
### Download metadata
Using a simple api request downloads the `.json` metadata of the latest VOD and saves it to:
`/root_path/streamer_username/metadata/metada_yyyymmdd_hhmmss.json`
### Upload to the cloud
Using [rclone](https://rclone.org/) after everything being downloaded and rendered , it will upload every file from the `root_path/streamer` folder  to any cloud service supported by rclone such as [Google Drive, Mega, One Drive, etc.](https://rclone.org/overview/#features)
 The destination path to where it will be uploaded it has to be stated in the `.env` file.
 Example:
 ```env
remote=GoogleDrive:Archive
 ```
 ### Gmail notification
 Using the python library [smtplib](https://docs.python.org/3/library/smtplib.html) sends gmail messages to desire gmail. To be run correctly the emails have to be stated in the `.env` file.
 Example:
 ```.env
 SENDER=example@gmail.com 
 PWD=xxxxxxxxxxxxxxxx
 RECEIVER=example@gmail.com
 ```
 the `PWD` env is NOT your normal password is a 16 character password generated by google. 
 > [Here's](https://stackoverflow.com/a/73214197) a well documented way of how to get your PWD.

### Seccion finished
After every option if enabled is done it will go back to check again.
Here's an example of how a regular PATH will look like.
```
root_path
└───username
    ├───chat
    │   ├───json
    │   │       CHAT_20221203_06h40m41s.json
    │   │       
    │   └───rendered
    │           CHAT_20221203_06h40m41s.mp4
    │
    ├───metadata
    │       metadata_20221203_06h40m41s.json
    │       
    └───video
        ├───processed
        │       LIVE_20221203_06h40m41s.mp4
        │       VOD_20221203_06h40m41s.mp4
        │       
        └───recorded
                LIVE_20221203_06h40m41s.ts
                VOD_20221203_06h40m41s.ts
```
