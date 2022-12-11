# Twitch Archive
Inspired by https://github.com/EnterGin/Auto-Stream-Recording-Twitch

Python script to check, download live stream, VOD, chat and upload them to any cloud storage supported by rclone.
## Requirements
- [Python 3](https://www.python.org/downloads/)
- [Streamlink](https://github.com/streamlink/streamlink)
## Getting started
1. Install Python 3.x
2. Install Streamlink 5.1.x
3. If you want to upload to any cloud storage using rclone, [configure rclone](https://rclone.org/docs/#configure).
4. `git clone https://github.com/piero0920/Twitch-Archive.git`
5. `cd Twitch-Archive`
6. `pip install -r requirements.txt`
7. Edit the `.env.sample` and rename it to `.env`
```.env
CLIENT-ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
CLIENT-SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OAUTH-PRIVATE-TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx # optional to record without ADS or download sub-only VODS
```
8. if you want to enable/disable more available options, edit `twitch-archive.py`
9. run `Python twitch-archive.py` or for multiple streamers `Python twitch-archive.py -u streamer` 
<!---
## Features 
- Auto records the live stream                         | [Streamlink](https://streamlink.github.io/)
- Downloads the VOD after stream ended                 | [Streamlink](https://streamlink.github.io/)
- Downloads the chat logs of the VOD and renders it    | [TwitchDownloaderCLI](https://github.com/lay295/TwitchDownloader)
- Downloads the metadata of the VOD                    | [Twitch api](https://dev.twitch.tv/docs/api/reference#get-videos)
- Uploads them to the Cloud                            | [rclone](https://rclone.org/)
- Notifies you through Gmail of the progress           | [smtplib](https://docs.python.org/3/library/smtplib.html)
-->