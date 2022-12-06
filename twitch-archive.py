import requests, os, time, json, sys, subprocess, getopt, smtplib, pathlib
from colorama import Fore, Style
from datetime import datetime, timedelta
from pytz import timezone
from dateutil import parser
from dotenv import load_dotenv, find_dotenv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
load_dotenv(find_dotenv())
class TwitchArchive:
    def __init__(self):
        # user configuration
        self.username = "KalathrasLolweapon"                       # Twitch streamer username
        self.quality  = "best"                                     # Qualities options: best/source high/720p medium/540p low/360p
        # global configuration
        self.root_path          = r"archive"                       # Path where this script saves everything (livestream,VODs,chat,metadata)
        self.timezone           = "US/Eastern"                     # Timezones, you can see a list of the format timezone here: https://gist.github.com/heyalexej/8bf688fd67d7199be4a1682b3eec7568
        self.refresh            = 5.0                              # Time between checking (5.0 is recommended)
        self.notifications      = 0                                # 0 - disable email notification of current seccion, 1 - enable email notification of current seccion
        self.downloadMETADATA   = 1                                # 0 - disable metadata downloading, 1 - enable metadata downloading
        self.downloadVOD        = 1                                # 0 - disable VOD downloading after stream finished, 1 - enable VOD downloading after stream finished (this option downloads the latest public vod)
        self.downloadCHAT       = 1                                # 0 - disable chat downloading and rendering, 1 - enable chat downloading and rendering
        self.uploadCloud        = 0                                # 0 - disable upload to remote cloud, 1 - enable upload to remote cloud
        self.deleteFiles        = 0                                # 0 - disable the deleting of files from current seccion after being uploaded to the cloud, 1 - enable the deleting files of files from current seccion after being uploaded to the cloud (BE CAREFUL WITH THIS OPTION)
        self.streamlink_debug   = 0                                # 0 - disable streamlink debug display, 1 - enable streamlink debug display
        self.hls_segments       = 3                                # 1-10 for live stream, it's possible to use multiple threads to potentially increase the throughput. 2-3 is enough
        self.hls_segmentsVOD    = 10                               # 1-10 for downloading vod, it's possible to use multiple threads to potentially increase the throughput

    def run(self):
        print('Twitch-Archive')
        print('Configuration:')
        print(f'Root path: {Fore.GREEN}' + str(pathlib.Path(self.root_path).resolve()) + f'{Style.RESET_ALL}')
        print(f'Timezone: {Fore.GREEN}{self.timezone}{Style.RESET_ALL}')
        print(f'Refresh rate: {Fore.GREEN} {str(self.refresh)}{Style.RESET_ALL}')
        if self.notifications == 1: print(f'Email notifications: {Fore.GREEN}Enabled{Style.RESET_ALL}')
        else: print(f'Email notifications: {Fore.RED}Disabled{Style.RESET_ALL}')
        if self.downloadMETADATA == 1: print(f'Metada downloading {Fore.GREEN}Enabled{Style.RESET_ALL}')
        else: print(f'Metada downloading: {Fore.RED}Disabled{Style.RESET_ALL}')
        if self.downloadVOD == 1: print(f'VOD downloading {Fore.GREEN}Enabled{Style.RESET_ALL}')
        else: print(f'VOD downloading: {Fore.RED}Disabled{Style.RESET_ALL}')
        if self.downloadCHAT == 1: print(f'Chat downloading {Fore.GREEN}Enabled{Style.RESET_ALL}')
        else: print(f'Chat downloading: {Fore.RED}Disabled{Style.RESET_ALL}')
        if self.uploadCloud == 1: print(f'Upload to Google Drive: {Fore.GREEN}Enabled{Style.RESET_ALL}')
        else: print(f'Upload to cloud service: {Fore.RED}Disabled{Style.RESET_ALL}')
        if self.deleteFiles == 1: print(f'{Fore.RED}'+'\033[1m'+f'CAREFUL FILES ARE CONFIGURATED TO BE DELETED{Style.RESET_ALL}')
        else: print(f'{Fore.GREEN}'+'\033[1m'+f'Files will NOT be deleted{Style.RESET_ALL}')
        if self.uploadCloud == 0 and self.deleteFiles == 1: print(f'{Fore.RED}'+'\033[1m'+f'FILES WILL BE DELETED AND NO UPLOADED {Style.RESET_ALL}{Fore.GREEN}\n"CTRL + C"{Style.RESET_ALL}{Fore.RED}'+'\033[1m'+f' TO STOP AND CHANGED CONFIGURATION{Style.RESET_ALL}')

        self.oauth_token = self.get_oauth_token()
        self.get_channel_id()
        if self.streamlink_debug == 1: self.debug_cmd = "--loglevel trace".split()
        else: self.debug_cmd = "".split()

        self.recorded_path = str(pathlib.Path(os.path.join(self.root_path,self.username,"video", "recorded")).absolute())
        self.processed_path = str(pathlib.Path(os.path.join(self.root_path, self.username, "video", "processed")).absolute())
        self.chatJSON_path = str(pathlib.Path(os.path.join(self.root_path, self.username, "chat", "json")).absolute())
        self.chatMP4_path = str(pathlib.Path(os.path.join(self.root_path, self.username, "chat", "rendered")).absolute())
        self.metadata_path = str(pathlib.Path(os.path.join(self.root_path, self.username, "metadata")).absolute())

        if(os.path.isdir(self.recorded_path) is False): os.makedirs(self.recorded_path)
        if(os.path.isdir(self.processed_path) is False): os.makedirs(self.processed_path)
        if(os.path.isdir(self.chatJSON_path) is False): os.makedirs(self.chatJSON_path)
        if(os.path.isdir(self.chatMP4_path) is False): os.makedirs(self.chatMP4_path)
        if(os.path.isdir(self.metadata_path) is False): os.makedirs(self.metadata_path)

        try:
            video_list = [f for f in os.listdir(self.recorded_path) if os.path.isfile(os.path.join(self.recorded_path, f))]
            if(len(video_list) > 0):
                print('Fixing previously recorded files.')
            for f in video_list:
                recorded_filename = os.path.join(self.recorded_path, f)
                stream_dir_path = self.processed_path
                if(os.path.isdir(stream_dir_path) is False):
                    os.makedirs(stream_dir_path)
                    print('Fixing ' + recorded_filename + '.')
                    try:
                        subprocess.call([str(pathlib.Path(__file__).parent.resolve())+'/bin/ffmpeg.exe' , '-y', '-i', recorded_filename, '-analyzeduration', '2147483647', '-probesize', '2147483647', '-c:v', 'copy', '-c:a', 'copy', '-start_at_zero', '-copyts', os.path.join(stream_dir_path, f[:-2]+"mp4")], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
                    except Exception as e:
                        print(e)
                elif(os.path.exists(os.path.join(stream_dir_path, f)) is False):
                    print('Fixing ' + recorded_filename + '.')
                    try:
                        subprocess.call([str(pathlib.Path(__file__).parent.resolve())+'/bin/ffmpeg.exe', '-y', '-i', recorded_filename, '-analyzeduration', '2147483647', '-probesize', '2147483647', '-c:v', 'copy', '-c:a', 'copy', '-start_at_zero', '-copyts', os.path.join(stream_dir_path, f[:-2]+"mp4")], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
                    except Exception as e:
                        print(e)
        except Exception as e:
            print(e)

        print(f"Checking for {Fore.GREEN}{self.username}{Style.RESET_ALL} every {Fore.GREEN}{self.refresh}{Style.RESET_ALL} seconds. Record with {Fore.GREEN}{self.quality}{Style.RESET_ALL} quality.")
        self.sendNotif("TWITCH ARCHIVE", f"Checking for {self.username} every {self.refresh} seconds. Record with {self.quality} quality.")
        self.loopcheck()

    def get_oauth_token(self):
        try:
            return requests.post(f"https://id.twitch.tv/oauth2/token?client_id={os.environ.get('CLIENT-ID')}&client_secret={os.environ.get('CLIENT-SECRET')}&grant_type=client_credentials").json()['access_token']
        except:
            return None

    def get_channel_id(self):
        self.getting_channel_id_error = 0
        self.user_not_found           = 0
        if self.oauth_token == None:
            self.getting_channel_id_error = 1
            return
        url = 'https://api.twitch.tv/helix/users?login=' + self.username
        try:
            r = requests.get(url, headers = {"Authorization" : "Bearer " + self.oauth_token, "Client-ID": os.environ.get('CLIENT-ID')}, timeout = 15)
            r.raise_for_status()
            info = r.json()
            if info["data"] != []: self.channel_id = info["data"][0]["id"]
            else: self.user_not_found = 1
        except requests.exceptions.RequestException as e:
            self.getting_channel_id_error = 1
            print(f'\n{e}\n')

    def check_user(self):
        # 0: online, 1: not found, 2: error, 3: channel id error
        info = None
        if self.user_not_found != 1 and self.getting_channel_id_error != 1:
            url    = 'https://api.twitch.tv/helix/channels?broadcaster_id=' + str(self.channel_id)
            status = 2
            try:
                r = requests.get(url, headers = {"Authorization" : "Bearer " + self.oauth_token, "Client-ID": os.environ.get('CLIENT-ID')}, timeout = 15)
                r.raise_for_status()
                info   = r.json()
                status = 0
            except requests.exceptions.RequestException as e:
                if e.response != None:
                    if e.response.status_code == 401:
                        print('\nRequest to Twitch returned an error %s, trying to get new oauth_token...'% (e.response.status_code))
                        self.getting_channel_id_error = 1
                    else:
                        print('\nRequest to Twitch returned an error %s, the response is:\n%s\n'% (e.response.status_code, e.response))
                else:
                    print(f'\n{e}\n')
        elif self.user_not_found == 1:
            status = 1
        else:
            self.oauth_token = self.get_oauth_token()
            self.get_channel_id()
            status = 3

        return status, info

    def toTZ(self, utc_str):
        new_date = str(datetime.fromisoformat(utc_str.replace('Z', '+00:00')).astimezone(timezone(self.timezone)))
        year = new_date[:4]
        month = new_date[5:7]
        day = new_date[8:10]
        hour = new_date[11:13]
        minute = new_date[14:16]
        seconds = new_date[17:19]
        date_formated = year + month + day + "_" + hour + "h" + minute + "m" + seconds + "s"
        return date_formated

    def sendNotif(self, subject, content):
        if self.notifications == 1:
            sender = os.environ.get("SENDER")
            receiver = os.environ.get("RECEIVER")
            msg = MIMEMultipart()
            msg['From'] = sender
            msg['To'] = receiver
            msg['Subject'] = self.username + " _ " + subject
            body = "Current seccion is for " + self.username + "\n\n\n\n" + content
            msg.attach(MIMEText((body), 'plain'))
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(sender, os.environ.get("PASSWD"))
            txt = msg.as_string()
            server.sendmail(sender, receiver, txt)
            server.quit()

    def loopcheck(self):
        while True:
            status, info = self.check_user()
            if status == 1:
                print("Username not found. Invalid username or typo.")
                time.sleep(self.refresh)
            elif status == 2:
                print(datetime.now(timezone(self.timezone)).strftime("%Y%m%d_%Hh%Mm%Ss")," ","Unexpected error. Try to check internet connection or client-id. Will try again in", self.refresh, "seconds.")
                time.sleep(self.refresh)
            elif status == 3:
                print(datetime.now(timezone(self.timezone)).strftime("%Y%m%d_%Hh%Mm%Ss")," ","Error with channel id or oauth token. Try to check internet connection or client-id and client-secret. Will try again in", self.refresh, "seconds.")
                time.sleep(self.refresh)
            elif status == 0:
                live_date = datetime.now(timezone('UTC'))
                live_date_min = live_date - timedelta(minutes=5)
                live_date_plus = live_date + timedelta(minutes=5)
                present_datetime = datetime.now(timezone(self.timezone)).strftime("%Y%m%d_%Hh%Mm%Ss")
                raw_filename = present_datetime + ".ts"
                live_filename = "LIVE_" + raw_filename
                raw_vod_filename = "VOD_" + raw_filename
                chat_json_filename = "CHAT_" + present_datetime + ".json"
                chat_mp4_filename = "CHAT_" + present_datetime + ".mp4"
                metadata_filename = "metadata_" + present_datetime + ".json"
                recorded_filename = os.path.join(self.recorded_path, live_filename)
                # start streamlink process
                subprocess.call(["streamlink", '--http-header', 'Authorization=OAuth ' + os.environ.get('OAUTH-PRIVATE-TOKEN'), "--hls-segment-threads", str(self.hls_segments), "--hls-live-restart", "--twitch-disable-hosting", "twitch.tv/" + self.username, self.quality, "--retry-streams", str(self.refresh)] + self.debug_cmd + ["-o", recorded_filename])
                if(os.path.exists(recorded_filename) is True):
                    status, info_tmp = self.check_user()
                    if info_tmp != None:
                        info = info_tmp
                    try:
                        vodurl      = 'https://api.twitch.tv/helix/videos?user_id=' + str(self.channel_id) + '&type=archive'
                        vods        = requests.get(vodurl, headers = {"Authorization" : "Bearer " + self.oauth_token, "Client-ID": os.environ.get('CLIENT-ID')}, timeout = 30)
                        vodsinfodic = json.loads(vods.text)
                        if vodsinfodic["data"][0] != []:
                            if live_date_min <= parser.parse(vodsinfodic["data"][0]["created_at"]) <= live_date_plus:
                                vod_id = vodsinfodic["data"][0]["id"]
                                created_at = vodsinfodic["data"][0]["created_at"]
                                created_at = self.toTZ(created_at)
                                raw_filename = created_at + ".ts"
                                live_filename = "LIVE_" + raw_filename
                                raw_vod_filename = "VOD_" + raw_filename
                                chat_json_filename = "CHAT_" + created_at + ".json"
                                chat_mp4_filename = "CHAT_" + created_at + ".mp4"
                                metadata_filename = "metadata_" + created_at + ".json"
                                try:
                                    os.rename(recorded_filename,os.path.join(self.recorded_path, live_filename))
                                    recorded_filename  = os.path.join(self.recorded_path, live_filename)
                                except Exception as e:
                                    raw_filename = present_datetime + ".ts"
                                    live_filename = "LIVE_" + raw_filename
                                    raw_vod_filename = "VOD_" + raw_filename
                                    chat_json_filename = "CHAT_" + present_datetime + ".json"
                                    chat_mp4_filename = "CHAT_" + present_datetime + ".mp4"
                                    metadata_filename = "metadata_" + present_datetime + ".json"
                                    os.rename(recorded_filename,os.path.join(self.recorded_path, live_filename))
                                    recorded_filename  = os.path.join(self.recorded_path, live_filename)
                                    print('first exception as e\nAn error has occurred. VOD and chat will not be downloaded. Please check them manually.\n' + e)
                                    self.sendNotif('ERROR - '+ present_datetime, 'An error has occurred. VOD and chat will not be downloaded. Please check them manually.\n ' + e)
                                if self.downloadMETADATA == 1:
                                    self.sendNotif('Metadata - ' + created_at,'Downloading and saving metadata:\n' + json.dumps(vodsinfodic["data"][0], indent=4))
                                    with open(os.path.join(self.metadata_path, metadata_filename), 'w', encoding='utf-8') as f:
                                        json.dump(vodsinfodic["data"][0], f, ensure_ascii=False, indent=4)
                                if self.downloadVOD == 1:
                                    print('Downloading VOD: ' + vodsinfodic["data"][0]["title"])
                                    self.sendNotif('VOD - ' + created_at,'Downloading VOD: ' + vodsinfodic["data"][0]["title"])
                                    try:
                                        subprocess.call(['streamlink', '--http-header', 'Authorization=OAuth ' + os.environ.get('OAUTH-PRIVATE-TOKEN'), "--hls-segment-threads", str(self.hls_segmentsVOD), "twitch.tv/videos/" + vod_id, self.quality] + self.debug_cmd + ["-o", os.path.join(self.recorded_path, raw_vod_filename)])
                                    except Exception as e:
                                        print('Error', 'A ERROR has ocurred and the VOD will not be downloaded.\n' + e)
                                        self.sendNotif('ERROR - ' + created_at, 'A ERROR has ocurred and the VOD will not be downloaded. \nerror:\n' + e)
                                if self.downloadCHAT == 1:
                                    print('Downloading and rendering CHAT: ' + vodsinfodic["data"][0]["title"])
                                    self.sendNotif('CHAT - ' + created_at,'Downloading JSON and rendering chat logs from VOD:\n' + vodsinfodic["data"][0]["title"])
                                    try:
                                        subprocess.call([str(pathlib.Path(__file__).parent.resolve())+"/bin/chat.bat", vod_id, os.path.join(self.chatJSON_path, chat_json_filename), os.path.join(self.chatMP4_path, chat_mp4_filename)])
                                    except Exception as e:
                                        self.sendNotif('ERROR - ' + created_at, "A ERROR has ocurred and chat will need to be downloaded and rendered manually.\n" + e)
                                        print("A ERROR has ocurred and chat will need to be downloaded and rendered manually\n" + e)
                            else:
                                print('A ERROR has ocurred, the latest VOD doesnt match with the livestream, the VOD is not published\nThe VOD and chat will not be downloaded and rendered.\nThe current livestream date: ' + present_datetime + '\nThe VOD date: ' + self.toTZ(vodsinfodic["data"][0]["created_at"]))
                                self.sendNotif('ERROR - ' + present_datetime, 'A ERROR has ocurred, the latest VOD doesnt match with the livestream, the VOD is not published\nThe VOD and chat will not be downloaded and rendered.\nThe current livestream date: ' + present_datetime + '\nThe VOD date: ' + self.toTZ(vodsinfodic["data"][0]["created_at"]))       
                        else:
                            raw_filename = present_datetime + ".ts"
                            live_filename = "LIVE_" + raw_filename
                            raw_vod_filename = "VOD_" + raw_filename
                            chat_json_filename = "CHAT_" + present_datetime + ".json"
                            chat_mp4_filename = "CHAT_" + present_datetime + ".mp4"
                            metadata_filename = "metadata_" + present_datetime + ".json"
                            os.rename(recorded_filename,os.path.join(self.recorded_path, live_filename))
                            recorded_filename  = os.path.join(self.recorded_path, live_filename)
                    except Exception as e:
                        raw_filename = present_datetime + ".ts"
                        live_filename = "LIVE_" + raw_filename
                        raw_vod_filename = "VOD_" + raw_filename
                        chat_json_filename = "CHAT_" + present_datetime + ".json"
                        chat_mp4_filename = "CHAT_" + present_datetime + ".mp4"
                        metadata_filename = "metadata_" + present_datetime + ".json"
                        os.rename(recorded_filename,os.path.join(self.recorded_path, live_filename))
                        recorded_filename  = os.path.join(self.recorded_path, live_filename)
                        print('An error has occurred. VOD and chat will not be downloaded. Please check them manually.\n' + e)
                        self.sendNotif('ERROR - ' + present_datetime, 'An error has occurred. VOD and chat will not be downloaded. Please check them manually.\n' + e)
                print("Recording stream is done. Fixing video file.")
                self.sendNotif("STREAM DONE - " + present_datetime, "Recording stream is done. Fixing video file.")
                if(os.path.exists(recorded_filename) is True):
                    file_mp4 = live_filename[:-2] + "mp4"
                    vod_filename = raw_vod_filename[:-2] + "mp4"
                    processed_filename = os.path.join(self.processed_path, file_mp4)
                    subprocess.call([str(pathlib.Path(__file__).parent.resolve())+'/bin/ffmpeg.exe', '-y', '-i', recorded_filename, '-analyzeduration', '2147483647', '-probesize', '2147483647', '-c:v', 'copy', '-c:a', 'copy', '-start_at_zero', '-copyts', processed_filename], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
                    if(os.path.exists(os.path.join(self.recorded_path, raw_vod_filename)) is True):
                        subprocess.call([str(pathlib.Path(__file__).parent.resolve())+'/bin/ffmpeg.exe', '-y', '-i', os.path.join(self.recorded_path, raw_vod_filename), '-analyzeduration', '2147483647', '-probesize', '2147483647', '-c:v', 'copy', '-c:a', 'copy', '-start_at_zero', '-copyts', os.path.join(self.processed_path, vod_filename)], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
                else:
                    print("Skip fixing. File not found.")
                print("Fixing is done.")
                if self.uploadCloud == 1:
                    tree = subprocess.run(["powershell.exe","tree", f"'{self.root_path}/{self.username}'", "/f"], capture_output=True, text=True).stdout.split("\n",2)[2]
                    print('Uploading the following files:\n' + tree)
                    self.sendNotif("UPLOADING - " + present_datetime, 'Uploading the following files: \n' + tree)
                    subprocess.call([str(pathlib.Path(__file__).parent.resolve())+'/bin/upload.bat', str(pathlib.Path(self.root_path).resolve()),self.username])
                if self.deleteFiles == 1:
                    self.sendNotif("DELETING - " + present_datetime, "Deleting the files from current seccion.")
                    print(f'{Fore.RED}DELETING FILES{Style.RESET_ALL}')
                    print(f'{Fore.RED}Deleting ' + recorded_filename + f'{Style.RESET_ALL}')
                    os.remove(recorded_filename)
                    print(f'{Fore.RED}Deleting ' + processed_filename + f'{Style.RESET_ALL}')
                    os.remove(processed_filename)
                    if self.downloadVOD == 1:
                        if(os.path.exists(os.path.join(self.recorded_path, raw_vod_filename)) is True):
                            print(f'{Fore.RED}Deleting ' + os.path.join(self.recorded_path, raw_vod_filename) + f'{Style.RESET_ALL}')
                            os.remove(os.path.join(self.recorded_path, raw_vod_filename))
                        if(os.path.exists(os.path.join(self.processed_path, vod_filename)) is True):
                            print(f'{Fore.RED}Deleting ' + os.path.join(self.processed_path, vod_filename) + f'{Style.RESET_ALL}')
                            os.remove(os.path.join(self.processed_path, vod_filename))
                    if self.downloadCHAT == 1:
                        if(os.path.exists(os.path.join(self.chatJSON_path, chat_json_filename)) is True):
                            print(f'{Fore.RED}Deleting ' + os.path.join(self.chatJSON_path, chat_json_filename) + f'{Style.RESET_ALL}')
                            os.remove(os.path.join(self.chatJSON_path, chat_json_filename))
                        if(os.path.exists(os.path.join(self.chatMP4_path, chat_mp4_filename)) is True):
                            print(f'{Fore.RED}Deleting ' + os.path.join(self.chatMP4_path, chat_mp4_filename) + f'{Style.RESET_ALL}')
                            os.remove(os.path.join(self.chatMP4_path, chat_mp4_filename))
                    if self.downloadMETADATA == 1:
                        if(os.path.exists(os.path.join(self.metadata_path, metadata_filename)) is True):
                            print(f'{Fore.RED}Deleting ' + os.path.join(self.metadata_path, metadata_filename) + f'{Style.RESET_ALL}')
                            os.remove(os.path.join(self.metadata_path, metadata_filename))
                print('CURRENT SECCION HAVE FINISHED GOING BACK TO CHECKING')
                self.sendNotif("SECCION DONE - " + present_datetime, 'CURRENT SECCION HAVE FINISHED GOING BACK TO CHECKING')
                time.sleep(self.refresh)
def main(argv):
    twitch_recorder = TwitchArchive()
    usage_message = 'twitch-archive.py -u <username> -q <quality>'
    try:
        opts, args = getopt.getopt(argv,"u:q:",["username=","quality="])
    except getopt.GetoptError:
        print (usage_message)
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print(usage_message)
            sys.exit()
        elif opt in ("-u", "--username"):
            twitch_recorder.username = arg
        elif opt in ("-q", "--quality"):
            twitch_recorder.quality = arg
    twitch_recorder.run()
if __name__ == "__main__":
    main(sys.argv[1:])