import requests, os, time, json, sys, subprocess, getopt, pathlib
from colorama import Fore, Style
from datetime import datetime
from pytz import timezone
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())
class TwitchArchive:
    def __init__(self):
        # user configuration
        self.username = "KalathrasLolweapon"                       # Twitch streamer username
        self.quality  = "best"                                     # Qualities options: best/source high/720p medium/540p low/360p
        # global configuration
        self.root_path          = r"archive"                       # Path where this script saves everything (livestream,VODs,chat,metadata)
        self.refresh            = 60                              # Time between checking (5.0 is recommended), avoid less than 1.0
        self.downloadVOD        = 0                                # 0 - disable VOD downloading after stream finished, 1 - enable VOD downloading after stream finished (this option downloads the latest public vod)
        self.downloadCHAT       = 1                                # 0 - disable chat downloading and rendering, 1 - enable chat downloading and rendering
        self.uploadCloud        = 1                                # 0 - disable upload to remote cloud, 1 - enable upload to remote cloud
        self.deleteFiles        = 1                                # 0 - disable the deleting of files from current seccion after being uploaded to the cloud, 1 - enable the deleting files of files from current seccion after being uploaded to the cloud (BE CAREFUL WITH THIS OPTION)
        self.hls_segmentsVOD    = 10                               # 1-10 for downloading vod, it's possible to use multiple threads to potentially increase the throughput

    def run(self):        
        self.os = self.get_OS()
        print('Twitch-Archive --- ONLY VOD/CHAT')
        print('Configuration:')
        print(f'Root path: {Fore.GREEN}' + str(pathlib.Path(self.root_path).resolve()) + f'{Style.RESET_ALL}')
        print(f'Refresh rate: {Fore.GREEN} {str(self.refresh)}{Style.RESET_ALL}')
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

        self.temp_path = str(pathlib.Path(os.path.join(self.root_path,self.username,"vod", "temp")).absolute())
        self.vod_path = str(pathlib.Path(os.path.join(self.root_path, self.username, "vod")).absolute())
        self.json_path = str(pathlib.Path(os.path.join(self.root_path, self.username, "chat", "json")).absolute())
        self.chat_path = str(pathlib.Path(os.path.join(self.root_path, self.username, "chat")).absolute())

        if(os.path.isdir(self.temp_path) is False): os.makedirs(self.temp_path)
        if(os.path.isdir(self.vod_path) is False): os.makedirs(self.vod_path)
        if(os.path.isdir(self.json_path) is False): os.makedirs(self.json_path)
        if(os.path.isdir(self.chat_path) is False): os.makedirs(self.chat_path)

        if not os.path.exists(os.path.join(self.root_path, ".log")):
            with open(os.path.join(self.root_path, ".log"), 'w'): pass

        print(f"Checking for {Fore.GREEN}{self.username}{Style.RESET_ALL} every {Fore.GREEN}{self.refresh}{Style.RESET_ALL} seconds to download VOD/CHAT")
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
            print(e)
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
            print("API request ERROR")
            print(e)
            return False

    def loopcheck(self):
        while True:
            if self.check_user() is True:
                live_temp_path = os.path.join(self.temp_path, "live_temp.ts")
                with open(os.path.join(self.root_path, ".log")) as logs:
                    logs = logs.read()
                    log_id = self.live_info["started_at"] + " - " + self.username + " - " + self.live_info["title"]
                    if log_id in logs:
                        time.sleep(self.refresh)
                with open(os.path.join(self.root_path, ".log"), "r+") as logs:
                    log_id = self.live_info["started_at"] + " - " + self.username + " - " + self.live_info["title"]
                    for line in logs:
                        if log_id in line:
                            break
                    else:
                        logs.write(self.live_info["started_at"] + " - " + self.username + " - " + self.live_info["title"] + "\n")

                subprocess.call(['streamlink', 'twitch.tv/'+ self.username, 'worst', '--hls-segment-threads', '3', '--retry-streams', str(self.refresh), '--twitch-disable-reruns', '-o', live_temp_path])
                try:
                    vodurl      = f'https://api.twitch.tv/helix/videos?user_id={str(self.channel_id)}&period=day&type=archive'
                    vods        = requests.get(vodurl, headers = {"Authorization" : "Bearer " + self.oauth_token, "Client-ID": os.getenv('CLIENT-ID')}, timeout = 30)
                    vodsinfo = json.loads(vods.text)
                    if vodsinfo["data"][0] != []:
                        vod_date = datetime.strptime(vodsinfo["data"][0]["created_at"],'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone('UTC')).astimezone(tz=None).replace(tzinfo=None)
                        vod_raw_filename = datetime.strftime(vod_date,'%Y%m%d_%Hh%Mm%Ss') 
                        if self.live_info["id"] == vodsinfo["data"][0]["stream_id"]:
                            print('VOD AND CHAT AVAILABLE')
                            current_vod = vodsinfo["data"][0]
                            vod_raw_path = os.path.join(self.temp_path, "vod_temp.ts")
                            vod_proc_path = os.path.join(self.vod_path, vod_raw_filename + ".mp4")
                            chat_json_path = os.path.join(self.json_path, vod_raw_filename + ".json")
                            chat_video_path = os.path.join(self.chat_path, vod_raw_filename + ".mp4")

                            if self.downloadVOD == 1:
                                print('Downloading VOD: ' + current_vod["title"])
                                try:
                                    subprocess.call(['streamlink', 'twitch.tv/videos/' + current_vod["id"], self.quality, "--hls-segment-threads", str(self.hls_segmentsVOD), "-o", vod_raw_path])
                                    if(os.path.exists(vod_raw_path) is True):
                                        if self.os == 'windows':subprocess.call([str(pathlib.Path(__file__).parent.resolve())+'/bin/ffmpeg.exe', '-y', '-i', vod_raw_path, '-analyzeduration', '2147483647', '-probesize', '2147483647', '-c:v', 'copy', '-c:a', 'copy', '-start_at_zero', '-copyts', vod_proc_path], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)                                     
                                        elif self.os == 'linux':subprocess.call([str(pathlib.Path(__file__).parent.resolve())+'/bin/ffmpeg', '-y', '-i', vod_raw_path, '-analyzeduration', '2147483647', '-probesize', '2147483647', '-c:v', 'copy', '-c:a', 'copy', '-start_at_zero', '-copyts', vod_proc_path], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)                                     
                                    else:
                                        print("Skip fixing. File not found.")
                                except Exception as e:
                                    print('Error', 'A ERROR has ocurred and the VOD will not be downloaded.\n')                                                       
                            if self.downloadCHAT == 1:
                                print('Downloading and rendering CHAT: ' + current_vod["title"])
                                try:
                                    if self.os == 'windows':subprocess.call([str(pathlib.Path(__file__).parent.resolve())+"/bin/chat.bat", current_vod["id"], chat_json_path, chat_video_path])
                                    elif self.os == 'linux':subprocess.call([str(pathlib.Path(__file__).parent.resolve())+"/bin/chat.sh", current_vod["id"], chat_json_path, chat_video_path])
                                except Exception as e:
                                    print("A ERROR has ocurred and chat will need to be downloaded and rendered manually\n")
                                
                            if self.uploadCloud == 1:
                                if self.os == 'windows':
                                    tree = subprocess.run(['powershell.exe','tree', f'{self.root_path}/{self.username}', '/f'], capture_output=True, text=True).stdout.split("\n",2)[2]
                                elif self.os == 'linux':
                                    tree = subprocess.check_output(['tree', str(pathlib.Path(self.root_path).resolve())+'/'+self.username]).decode(sys.stdout.encoding)
                                print('Uploading the following files:\n' + tree)
                                if self.os == 'windows':subprocess.call([str(pathlib.Path(__file__).parent.resolve())+'/bin/upload.bat', str(pathlib.Path(self.root_path).resolve()),self.username])
                                elif self.os == 'linux':subprocess.call([str(pathlib.Path(__file__).parent.resolve())+'/bin/upload.sh', str(pathlib.Path(self.root_path).resolve()),self.username])

                            if self.deleteFiles == 1:
                                print(f'{Fore.RED}DELETING FILES{Style.RESET_ALL}')
                                if self.downloadVOD == 1:
                                    if(os.path.exists(vod_raw_path) is True):
                                        print(f'{Fore.RED}Deleting ' + vod_raw_path + f'{Style.RESET_ALL}')
                                        os.remove(vod_raw_path)
                                    if(os.path.exists(vod_proc_path) is True):
                                        print(f'{Fore.RED}Deleting ' + vod_proc_path + f'{Style.RESET_ALL}')
                                        os.remove(vod_proc_path)
                                if self.downloadCHAT == 1:
                                    if(os.path.exists(chat_json_path) is True):
                                        print(f'{Fore.RED}Deleting ' + chat_json_path + f'{Style.RESET_ALL}')
                                        os.remove(chat_json_path)
                                    if(os.path.exists(chat_video_path) is True):
                                        print(f'{Fore.RED}Deleting ' + chat_video_path + f'{Style.RESET_ALL}')
                                        os.remove(chat_video_path)
                        else:
                            print('THE VOD/CHAT FOR CURRENT LIVESTREAM IS NOT AVAILABLE\nThe current livestream date: ' + self.live_info['started_at'] + '\nThe VOD date: ' + vodsinfo["data"][0]["created_at"])
                except Exception as e:
                    print('API request error.')
                    print(e) 

                print('CURRENT SECCION HAVE FINISHED GOING BACK TO CHECKING')
                time.sleep(self.refresh)
def main(argv):
    twitch_archive = TwitchArchive()
    help_msg = 'Twitch-Archive\nPython script to download the VOD and/or chat and render it, upload them to any cloud storage.\n -h, --help          Display this information\n -u, --username      <username> Twitch channel username\n -q, --quality       <quality> best/source high/720p medium/480p worst/360p\n -v, --vod           <1/0> Download vod\n -c, --chat          <1/0> Download chat and render it\n -r, --upload        <1/0> Upload to cloud storage\n -d, --delete        <1/0> Delete all files after upload (CAREFUL with this arg)\n'
    try:
        opts, args = getopt.getopt(argv,"h:u:q:v:c:r:d",["username=","quality=","vod=","chat=","metadata=","upload=","delete=","notifications="])
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
        elif opt in ("-r", "--upload"): twitch_archive.quality = int(arg)
        elif opt in ("-d", "--delete"): twitch_archive.quality = int(arg)
    twitch_archive.run()
if __name__ == "__main__":
    main(sys.argv[1:])