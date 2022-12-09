import requests, os, time, json, sys, subprocess, getopt, smtplib, pathlib, glob
from colorama import Fore, Style
from datetime import datetime, timedelta
from pytz import timezone
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
        self.refresh            = 5.0                              # Time between checking (5.0 is recommended), avoid less than 1.0
        self.notifications      = 1                                # 0 - disable email notification of current seccion, 1 - enable email notification of current seccion
        self.downloadMETADATA   = 1                                # 0 - disable metadata downloading, 1 - enable metadata downloading
        self.downloadVOD        = 1                                # 0 - disable VOD downloading after stream finished, 1 - enable VOD downloading after stream finished (this option downloads the latest public vod)
        self.downloadCHAT       = 1                                # 0 - disable chat downloading and rendering, 1 - enable chat downloading and rendering
        self.uploadCloud        = 1                                # 0 - disable upload to remote cloud, 1 - enable upload to remote cloud
        self.deleteFiles        = 0                                # 0 - disable the deleting of files from current seccion after being uploaded to the cloud, 1 - enable the deleting files of files from current seccion after being uploaded to the cloud (BE CAREFUL WITH THIS OPTION)
        self.cleanRaw           = 1                                # 0 - disable the deleting of raw (.ts) files, 1 - enable the deleteing of raw (.ts) files (if upload enable they will be deleted before) 
        self.hls_segments       = 3                                # 1-10 for live stream, it's possible to use multiple threads to potentially increase the throughput. 2-3 is enough
        self.hls_segmentsVOD    = 10                               # 1-10 for downloading vod, it's possible to use multiple threads to potentially increase the throughput

    def run(self):        
        self.os = self.get_OS()
        print('Twitch-Archive')
        print('Configuration:')
        print(f'Root path: {Fore.GREEN}' + str(pathlib.Path(self.root_path).resolve()) + f'{Style.RESET_ALL}')
        print(f'Refresh rate: {Fore.GREEN} {str(self.refresh)}{Style.RESET_ALL}')
        if self.notifications == 1: print(f'Email notifications: {Fore.GREEN}Enabled{Style.RESET_ALL}')
        else: print(f'Email notifications: {Fore.RED}Disabled{Style.RESET_ALL}')
        if self.downloadMETADATA == 1: print(f'Metada downloading {Fore.GREEN}Enabled{Style.RESET_ALL}')
        else: print(f'Metada downloading: {Fore.RED}Disabled{Style.RESET_ALL}')
        if self.downloadVOD == 1: print(f'VOD downloading {Fore.GREEN}Enabled{Style.RESET_ALL}')
        else: print(f'VOD downloading: {Fore.RED}Disabled{Style.RESET_ALL}')
        if self.downloadCHAT == 1: print(f'Chat downloading {Fore.GREEN}Enabled{Style.RESET_ALL}')
        else: print(f'Chat downloading: {Fore.RED}Disabled{Style.RESET_ALL}')
        if self.uploadCloud == 1: print(f'Upload to cloud storage: {Fore.GREEN}Enabled{Style.RESET_ALL}')
        else: print(f'Upload to cloud storage: {Fore.RED}Disabled{Style.RESET_ALL}')
        if self.deleteFiles == 1: print(f'{Fore.RED}'+'\033[1m'+f'CAREFUL FILES ARE CONFIGURATED TO BE DELETED{Style.RESET_ALL}')
        else: print(f'{Fore.GREEN}'+'\033[1m'+f'Files will NOT be deleted{Style.RESET_ALL}')
        if self.uploadCloud == 0 and self.deleteFiles == 1: print(f'{Fore.RED}'+'\033[1m'+f'FILES WILL BE DELETED AND NO UPLOADED {Style.RESET_ALL}{Fore.GREEN}\n"CTRL + C"{Style.RESET_ALL}{Fore.RED}'+'\033[1m'+f' TO STOP AND CHANGED CONFIGURATION{Style.RESET_ALL}')

        self.oauth_token = self.get_oauth_token()
        self.channel_id = self.get_channel_id()

        self.raw_path = str(pathlib.Path(os.path.join(self.root_path,self.username,"video", "raw")).absolute())
        self.video_path = str(pathlib.Path(os.path.join(self.root_path, self.username, "video")).absolute())
        self.chatJSON_path = str(pathlib.Path(os.path.join(self.root_path, self.username, "chat", "json")).absolute())
        self.chatMP4_path = str(pathlib.Path(os.path.join(self.root_path, self.username, "chat")).absolute())
        self.metadata_path = str(pathlib.Path(os.path.join(self.root_path, self.username, "metadata")).absolute())

        if(os.path.isdir(self.raw_path) is False): os.makedirs(self.raw_path)
        if(os.path.isdir(self.video_path) is False): os.makedirs(self.video_path)
        if(os.path.isdir(self.chatJSON_path) is False): os.makedirs(self.chatJSON_path)
        if(os.path.isdir(self.chatMP4_path) is False): os.makedirs(self.chatMP4_path)
        if(os.path.isdir(self.metadata_path) is False): os.makedirs(self.metadata_path)
        if not os.path.exists(os.path.join(self.root_path, ".log")):
            with open(os.path.join(self.root_path, ".log"), 'w'): pass

        print(f"Checking for {Fore.GREEN}{self.username}{Style.RESET_ALL} every {Fore.GREEN}{self.refresh}{Style.RESET_ALL} seconds. Record with {Fore.GREEN}{self.quality}{Style.RESET_ALL} quality.")
        self.sendNotif("TWITCH ARCHIVE", f"Checking for {self.username} every {self.refresh} seconds. Record with {self.quality} quality.")
        self.loopcheck()

    def get_OS(self):
        if sys.platform.startswith('win32'):
            return 'windows'
        elif sys.platform.startswith('linux'):
            return 'linux'
        else:
            print('OS no supported')
            return

    def get_oauth_token(self):
        try:
            return requests.post(f"https://id.twitch.tv/oauth2/token?client_id={os.getenv('CLIENT-ID')}&client_secret={os.getenv('CLIENT-SECRET')}&grant_type=client_credentials").json()['access_token']
        except:
            return None

    def get_channel_id(self):
        try:
            r = requests.get(f'https://api.twitch.tv/helix/users?login={self.username}', headers = {"Authorization" : "Bearer " + self.oauth_token, "Client-ID": os.getenv('CLIENT-ID')}, timeout = 15)
            r.raise_for_status()
            info = r.json()
            if info["data"] != []: 
                return info["data"][0]["id"]
            else: 
                return None
        except requests.exceptions.RequestException as e:
            print(f'\n{e}\n')
    def check_user(self):
        try:
            url = 'https://api.twitch.tv/helix/streams?user_id=' + self.channel_id
            live = requests.get(url, headers = {"Authorization" : "Bearer " + self.oauth_token, "Client-ID": os.environ.get('CLIENT-ID')}, timeout = 30)
            stream_data =  live.json()
            if len(stream_data['data']) == 1:
                self.live_info = stream_data['data'][0]               
                return True
            else:
                return False
        except Exception as e:
            print("ERROR checking user: ", e)
            return False

    def sendNotif(self, subject, content):
        if self.notifications == 1:
            sender = os.getenv("SENDER")
            receiver = os.getenv("RECEIVER")
            msg = MIMEMultipart()
            msg['From'] = sender
            msg['To'] = receiver
            msg['Subject'] = self.username + " _ " + subject
            body = "Current seccion is for " + self.username + "\n\n\n\n" + content
            msg.attach(MIMEText((body), 'plain'))
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(sender, os.getenv("PASSWD"))
            txt = msg.as_string()
            server.sendmail(sender, receiver, txt)
            server.quit()

    def loopcheck(self):
        while True:
            if self.check_user() is True:
                live_date = datetime.strptime(self.live_info["started_at"],'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone('UTC')).astimezone(tz=None).replace(tzinfo=None)
                live_raw_filename = datetime.strftime(live_date,'%Y%m%d_%Hh%Mm%Ss')
                        
                live_raw_path = os.path.join(self.raw_path, "LIVE_" + live_raw_filename + ".ts")
                live_proc_path = os.path.join(self.video_path, "LIVE_" + live_raw_filename + ".mp4")
                
                with open(os.path.join(self.root_path, ".log")) as logs:
                    logs = logs.read()
                    log_id = self.live_info["started_at"] + " - " + self.live_info["title"]
                    if log_id in logs:
                        time.sleep(self.refresh)

                with open(os.path.join(self.root_path, ".log"), "r+") as logs:
                    log_id = self.live_info["started_at"] + " - " + self.username + " - " + self.live_info["title"]
                    for line in logs:
                        if log_id in line:
                            break
                    else:
                        logs.write(self.live_info["started_at"] + " - " + self.username + " - " + self.live_info["title"] + "\n")


                self.sendNotif('Stream - ' + live_raw_filename, 'Streamer went live: ' + self.live_info["title"])
                subprocess.call(['streamlink', 'twitch.tv/'+ self.username, self.quality, '--twitch-api-header', 'Authorization=OAuth ' + os.getenv('OAUTH-PRIVATE-TOKEN'), '--hls-segment-threads', str(self.hls_segments), '--hls-live-restart', '--retry-streams', str(self.refresh), '-o', live_raw_path])
                if(os.path.exists(live_raw_path) is True):
                    if self.os == 'windows': subprocess.call([str(pathlib.Path(__file__).parent.resolve())+'/bin/ffmpeg.exe', '-y', '-i', live_raw_path, '-analyzeduration', '2147483647', '-probesize', '2147483647', '-c:v', 'copy', '-c:a', 'copy', '-start_at_zero', '-copyts', live_proc_path], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)                   
                    elif self.os == 'linux': subprocess.call([str(pathlib.Path(__file__).parent.resolve())+'/bin/ffmpeg', '-y', '-i', live_raw_path, '-analyzeduration', '2147483647', '-probesize', '2147483647', '-c:v', 'copy', '-c:a', 'copy', '-start_at_zero', '-copyts', live_proc_path], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)                    
                else:
                    print("Skip fixing. File not found.")
                try:
                    vodurl      = f'https://api.twitch.tv/helix/videos?user_id={str(self.channel_id)}&period=day&type=archive'
                    vods        = requests.get(vodurl, headers = {"Authorization" : "Bearer " + self.oauth_token, "Client-ID": os.getenv('CLIENT-ID')}, timeout = 30)
                    vodsinfo = json.loads(vods.text)
                    if vodsinfo["data"][0] != []:
                        vod_date = datetime.strptime(vodsinfo["data"][0]["created_at"],'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone('UTC')).astimezone(tz=None).replace(tzinfo=None)
                        vod_raw_filename = datetime.strftime(vod_date,'%Y%m%d_%Hh%Mm%Ss') 
                        if self.live_info["id"] == vodsinfo["data"][0]["stream_id"]:
                            current_vod = vodsinfo["data"][0]
                            vod_raw_path = os.path.join(self.raw_path, "VOD_" + live_raw_filename + ".ts")
                            vod_proc_path = os.path.join(self.video_path, "VOD_" + live_raw_filename + ".mp4")

                            if self.downloadMETADATA == 1:
                                self.sendNotif('Metadata - ' + live_raw_filename,'Downloading and saving metadata:\n' + json.dumps(current_vod, indent=4))
                                with open(os.path.join(self.metadata_path, "METADA_" + live_raw_filename + ".json"), 'w', encoding='utf-8') as f:
                                    json.dump(current_vod, f, ensure_ascii=False, indent=4)

                            if self.downloadVOD == 1:
                                print('Downloading VOD: ' + current_vod["title"])
                                self.sendNotif('VOD - ' + live_raw_filename,'Downloading VOD: ' + current_vod["title"])
                                try:
                                    subprocess.call(['streamlink', 'twitch.tv/videos/' + current_vod["id"], self.quality, '--twitch-api-header', 'Authorization=OAuth ' + os.getenv('OAUTH-PRIVATE-TOKEN'), "--hls-segment-threads", str(self.hls_segmentsVOD), "-o", vod_raw_path])
                                    if(os.path.exists(vod_raw_path) is True):
                                        if self.os == 'windows':subprocess.call([str(pathlib.Path(__file__).parent.resolve())+'/bin/ffmpeg.exe', '-y', '-i', vod_raw_path, '-analyzeduration', '2147483647', '-probesize', '2147483647', '-c:v', 'copy', '-c:a', 'copy', '-start_at_zero', '-copyts', vod_proc_path], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)                                     
                                        elif self.os == 'linux':subprocess.call([str(pathlib.Path(__file__).parent.resolve())+'/bin/ffmpeg', '-y', '-i', vod_raw_path, '-analyzeduration', '2147483647', '-probesize', '2147483647', '-c:v', 'copy', '-c:a', 'copy', '-start_at_zero', '-copyts', vod_proc_path], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)                                     
                                    else:
                                        print("Skip fixing. File not found.")
                                except Exception as e:
                                    print('Error', 'A ERROR has ocurred and the VOD will not be downloaded.\n')
                                    self.sendNotif('ERROR - ' + live_raw_filename, 'A ERROR has ocurred and the VOD will not be downloaded.\n')
                            
                            if self.downloadCHAT == 1:
                                print('Downloading and rendering CHAT: ' + current_vod["title"])
                                self.sendNotif('CHAT - ' + live_raw_filename,'Downloading JSON and rendering chat logs from VOD:\n' + current_vod["title"])
                                try:
                                    if self.os == 'windows':subprocess.call([str(pathlib.Path(__file__).parent.resolve())+"/bin/chat.bat", current_vod["id"], os.path.join(self.chatJSON_path, "CHAT_" + live_raw_filename + ".json"), os.path.join(self.chatMP4_path, "CHAT_" + live_raw_filename + ".mp4")])
                                    elif self.os == 'linux':subprocess.call([str(pathlib.Path(__file__).parent.resolve())+"/bin/chat.sh", current_vod["id"], os.path.join(self.chatJSON_path, "CHAT_" + live_raw_filename + ".json"), os.path.join(self.chatMP4_path, "CHAT_" + live_raw_filename + ".mp4")])
                                except Exception as e:
                                    self.sendNotif('ERROR - ' + live_raw_filename, "A ERROR has ocurred and chat will need to be downloaded and rendered manually.\n")
                                    print("A ERROR has ocurred and chat will need to be downloaded and rendered manually\n")
                        else:
                            print('A ERROR has ocurred, the latest VOD doesnt match with the livestream, the VOD is not published\nThe VOD and chat will not be downloaded and rendered.\nThe current livestream date: ' + live_raw_filename + '\nThe VOD date: ' + vod_raw_filename)
                            self.sendNotif('ERROR - ' + live_raw_filename, 'A ERROR has ocurred, the latest VOD doesnt match with the livestream, the VOD is not published\nThe VOD and chat will not be downloaded and rendered.\nThe current livestream date: ' + live_raw_filename + '\nThe VOD date: ' + vod_raw_filename)       
                except Exception as e:
                    print('An error has occurred. VOD and chat will not be downloaded. Please check them manually.\n')
                    self.sendNotif('ERROR - ' + live_raw_filename, 'An error has occurred. VOD and chat will not be downloaded. Please check them manually.\n')
 
                if self.cleanRaw == 1:
                    print('Deleting raw files')
                    if(os.path.exists(live_raw_path) is True): os.remove(live_raw_path)
                    if self.downloadVOD == 1:
                        if(os.path.exists(os.path.join(self.raw_path, "VOD_" + live_raw_filename + ".ts")) is True):
                            os.remove(os.path.join(self.raw_path, "VOD_" + live_raw_filename + ".ts"))
                if self.uploadCloud == 1:
                    if self.os == 'windows':
                        tree = subprocess.run(['powershell.exe','tree', f'{self.root_path}/{self.username}', '/f'], capture_output=True, text=True).stdout.split("\n",2)[2]
                    elif self.os == 'linux':
                        tree = subprocess.check_output(['tree', str(pathlib.Path(self.root_path).resolve())+'/'+self.username]).decode(sys.stdout.encoding)
                    print('Uploading the following files:\n' + tree)
                    self.sendNotif("UPLOADING - " + live_raw_filename, 'Uploading the following files: \n' + tree)
                    if self.os == 'windows':subprocess.call([str(pathlib.Path(__file__).parent.resolve())+'/bin/upload.bat', str(pathlib.Path(self.root_path).resolve()),self.username])
                    elif self.os == 'linux':subprocess.call([str(pathlib.Path(__file__).parent.resolve())+'/bin/upload.sh', str(pathlib.Path(self.root_path).resolve()),self.username])
                if self.deleteFiles == 1:
                    self.sendNotif("DELETING - " + live_raw_filename, "Deleting the files from current seccion.")
                    print(f'{Fore.RED}DELETING FILES{Style.RESET_ALL}')
                    if self.cleanRaw == 0:
                        print(f'{Fore.RED}Deleting ' + live_raw_path + f'{Style.RESET_ALL}')
                        os.remove(live_raw_path)
                    print(f'{Fore.RED}Deleting ' + live_proc_path + f'{Style.RESET_ALL}')
                    os.remove(live_proc_path)
                    if self.downloadVOD == 1:
                        if(os.path.exists(os.path.join(self.raw_path, "VOD_" + live_raw_filename + ".ts")) is True):
                            if self.cleanRaw == 0:
                                print(f'{Fore.RED}Deleting ' + os.path.join(self.raw_path, "VOD_" + live_raw_filename + ".ts") + f'{Style.RESET_ALL}')
                                os.remove(os.path.join(self.raw_path, "VOD_" + live_raw_filename + ".ts"))
                        if(os.path.exists(os.path.join(self.video_path, "VOD_" + live_raw_filename + ".mp4")) is True):
                            print(f'{Fore.RED}Deleting ' + os.path.join(self.video_path, "VOD_" + live_raw_filename + ".mp4") + f'{Style.RESET_ALL}')
                            os.remove(os.path.join(self.video_path, "VOD_" + live_raw_filename + ".mp4"))
                    if self.downloadCHAT == 1:
                        if(os.path.exists(os.path.join(self.chatJSON_path, "CHAT_"+live_raw_filename + ".json")) is True):
                            print(f'{Fore.RED}Deleting ' + os.path.join(self.chatJSON_path, "CHAT_"+live_raw_filename + ".json") + f'{Style.RESET_ALL}')
                            os.remove(os.path.join(self.chatJSON_path, "CHAT_"+live_raw_filename + ".json"))
                        if(os.path.exists(os.path.join(self.chatMP4_path, "CHAT_"+live_raw_filename + ".mp4")) is True):
                            print(f'{Fore.RED}Deleting ' + os.path.join(self.chatMP4_path, "CHAT_"+live_raw_filename + ".mp4") + f'{Style.RESET_ALL}')
                            os.remove(os.path.join(self.chatMP4_path, "CHAT_"+live_raw_filename + ".mp4"))
                    if self.downloadMETADATA == 1:
                        if(os.path.exists(os.path.join(self.metadata_path, "METADA_"+live_raw_filename+".json")) is True):
                            print(f'{Fore.RED}Deleting ' + os.path.join(self.metadata_path, "METADA_"+live_raw_filename+".json") + f'{Style.RESET_ALL}')
                            os.remove(os.path.join(self.metadata_path, "METADA_"+live_raw_filename+".json"))
                print('CURRENT SECCION HAVE FINISHED GOING BACK TO CHECKING')
                self.sendNotif("SECCION DONE - " + live_raw_filename, 'CURRENT SECCION HAVE FINISHED GOING BACK TO CHECKING')
                time.sleep(self.refresh)
def main(argv):
    twitch_archive = TwitchArchive()
    help_msg = 'Twitch-Archive\nPython script to record twitch live stream, download the VOD, metadata, chat and render it, and uploads them to any cloud storage.\n -h, --help          Display this information\n -u, --username      <username> Twitch channel username\n -q, --quality       <quality> best/source high/720p medium/480p worst/360p\n -v, --vod           <1/0> Download vod\n -c, --chat          <1/0> Download chat and render it\n -m, --metadata      <1/0> Download metadata\n -r, --upload        <1/0> Upload to cloud storage\n -d, --delete        <1/0> Delete all files after upload (CAREFUL with this arg)\n -n, --notifications <1/0> Receive email notification of the proccess through gmail\n'
    try:
        opts, args = getopt.getopt(argv,"h:u:q:v:c:m:r:d:n",["username=","quality=","vod=","chat=","metadata=","upload=","delete=","notifications="])
    except getopt.GetoptError:
        print (help_msg)
        sys.exit(2)
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            print(help_msg)
            sys.exit()
        elif opt in ("-u", "--username"): twitch_archive.username = arg
        elif opt in ("-q", "--quality"): twitch_archive.quality = arg
        elif opt in ("-v", "--vod"): twitch_archive.quality = int(arg)
        elif opt in ("-c", "--chat"): twitch_archive.quality = int(arg)
        elif opt in ("-m", "--metadata"): twitch_archive.quality = int(arg)
        elif opt in ("-r", "--upload"): twitch_archive.quality = int(arg)
        elif opt in ("-d", "--delete"): twitch_archive.quality = int(arg)
        elif opt in ("-n", "--notifications"): twitch_archive.quality = int(arg)
    twitch_archive.run()
if __name__ == "__main__":
    main(sys.argv[1:])