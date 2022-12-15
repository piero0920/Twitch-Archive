import requests, os, time, json, sys, subprocess, getopt, pathlib, locale, re
from colorama import Fore, Style
from datetime import datetime, timedelta
locale.setlocale(locale.LC_TIME, "es_ES") 
from pytz import timezone
from dotenv import load_dotenv, find_dotenv

class TwitchArchive:
    def __init__(self):
        # user configuration
        self.username = "KalathrasLolweapon"                       # Twitch streamer username
        self.quality  = "best"                                     # Qualities options: best/source high/720p medium/540p low/360p
        # global configuration
        self.root_path          = r"archive"                       # Path where this script saves everything (livestream,VODs,chat,metadata)
        self.refresh            = 60                              # Time between checking (5.0 is recommended), avoid less than 1.0
        self.downloadVOD        = 1                                # 0 - disable VOD downloading after stream finished, 1 - enable VOD downloading after stream finished (this option downloads the latest public vod)
        self.downloadCHAT       = 1                                # 0 - disable chat downloading and rendering, 1 - enable chat downloading and rendering
        self.downloadClips      = 1
        self.downloadMuted      = 1
        self.downloadChatHTML   = 1
        self.uploadCloud        = 1                                # 0 - disable upload to remote cloud, 1 - enable upload to remote cloud
        self.deleteFiles        = 0                                # 0 - disable the deleting of files from current seccion after being uploaded to the cloud, 1 - enable the deleting files of files from current seccion after being uploaded to the cloud (BE CAREFUL WITH THIS OPTION)
        self.hls_segmentsVOD    = 10                               # 1-10 for downloading vod, it's possible to use multiple threads to potentially increase the throughput

    def run(self):        
        self.os = self.get_OS()

        if load_dotenv(find_dotenv()): load_dotenv(find_dotenv())
        else:
            print(f'{Fore.RED}\033[1mCREATE .env file with variables{Style.RESET_ALL}')
            quit()

        self.correct_user()

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

        if not os.path.exists(os.path.join(str(pathlib.Path(__file__).parent.resolve())+'/bin/temp/', ".log")):
            with open(os.path.join(str(pathlib.Path(__file__).parent.resolve())+'/bin/temp/', ".log"), 'w'): pass

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
            print(f'{Fore.RED}\033[1mCheck your client-id and secret{Style.RESET_ALL}')
            quit()
    
    def correct_user(self):
        try:
            url = f'https://api.twitch.tv/helix/users?login={self.username}'
            response = requests.get(url,headers = {"Authorization" : "Bearer " + self.get_oauth_token(), "Client-ID": os.getenv('CLIENT-ID')}, timeout = 15).json()
            if response['data'] == []:
                print(f'{Fore.RED}\033[1mUse a correct username{Style.RESET_ALL}')
                quit()
        except requests.exceptions.RequestException as e:
            print(e)
    
    def check_user(self):
        query = 'query{user(login: "' + self.username + '") {stream{archiveVideo{id}title createdAt}}}'
        try:
            response = requests.post('https://gql.twitch.tv/gql',json={'query': query},headers={"Client-ID": "kimne78kx3ncx6brgo4mv6wki5h1ko"})
            return json.loads(response.text)
        except requests.exceptions.RequestException as e:
            print(e)
            quit()

    def get_vod(self):
        query = 'query {user(login: "' + self.username + '"){videos(first: 1){edges {node {id title recordedAt lengthSeconds tags muteInfo{ mutedSegmentConnection{ nodes{ duration offset }}} topClips(first: 10) { edges{ node{ id slug viewCount title createdAt curator { displayName } durationSeconds url thumbnailURL(width: 480, height: 272)}}}}}}}}'
        try:
            response = requests.post('https://gql.twitch.tv/gql', json={'query': query}, headers={"Client-ID": "kimne78kx3ncx6brgo4mv6wki5h1ko"})
            return json.loads(response.text)
        except requests.exceptions.RequestException as e:
            print(e)

    def loopcheck(self):
        while True:
            is_live = self.check_user()['data']['user']['stream']
            if is_live is not None:
                is_live_ready = self.check_user()['data']['user']['stream']['archiveVideo']
                if is_live_ready is not None:
                    bin_path = str(pathlib.Path(__file__).parent.resolve())+"/bin"
                    live_temp_path = os.path.join(bin_path+'/temp/', "live_temp.ts")
                    
                    with open(os.path.join(bin_path+'/temp/', ".log")) as logs:
                        logs = logs.read()
                        log_id = is_live["createdAt"] + " - " + self.username + " - " + is_live["title"]
                        if log_id in logs:
                            time.sleep(self.refresh)

                    with open(os.path.join(bin_path+'/temp/', ".log"), "r+") as logs:
                        log_id = is_live["createdAt"] + " - " + self.username + " - " + is_live["title"]
                        for line in logs:
                            if log_id in line:
                                break
                        else:
                            logs.write(is_live["createdAt"] + " - " + self.username + " - " + is_live["title"] +"\n")

                    subprocess.call(['streamlink', 'twitch.tv/'+ self.username, self.quality, '--twitch-api-header', 'Authorization=OAuth ' + os.getenv('OAUTH-PRIVATE-TOKEN'), '--hls-live-restart', '--retry-streams', str(self.refresh), '--twitch-disable-reruns', '-o', live_temp_path])
                    os.remove(live_temp_path)
                    
                    current_vod = self.get_vod()['data']['user']['videos']['edges'][0]['node']
                    vod_date = datetime.strptime(current_vod["recordedAt"],'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone('UTC')).astimezone(tz=None).replace(tzinfo=None)
                    vod_raw_filename = datetime.strftime(vod_date,'%Y%m%d_%Hh%Mm%Ss')
                    
                    if is_live_ready['id'] == current_vod['id']:
                        print('VOD AND CHAT AVAILABLE')
                        self.vod_path = str(pathlib.Path(os.path.join("VODS",self.root_path, self.username,  vod_raw_filename ,"vod")).absolute())
                        self.clips_path = str(pathlib.Path(os.path.join("VODS",self.root_path, self.username, vod_raw_filename , "clips")).absolute())
                        self.muted_path = str(pathlib.Path(os.path.join("VODS",self.root_path, self.username, vod_raw_filename , "muted")).absolute())
                        self.json_path = str(pathlib.Path(os.path.join("VODS",self.root_path, self.username,  vod_raw_filename ,"chat", "json")).absolute())
                        self.chat_path = str(pathlib.Path(os.path.join("VODS",self.root_path, self.username, vod_raw_filename , "chat")).absolute())
                        self.html_path = str(pathlib.Path(os.path.join("VODS",self.root_path, self.username,  vod_raw_filename ,"chat", "html")).absolute())
                        
                        if(os.path.isdir(self.vod_path) is False): os.makedirs(self.vod_path)
                        if(os.path.isdir(self.clips_path) is False): os.makedirs(self.clips_path)
                        if(os.path.isdir(self.muted_path) is False): os.makedirs(self.muted_path)
                        if(os.path.isdir(self.json_path) is False): os.makedirs(self.json_path)
                        if(os.path.isdir(self.chat_path) is False): os.makedirs(self.chat_path)
                        if(os.path.isdir(self.html_path) is False): os.makedirs(self.html_path)

                        vod_raw_path = os.path.join(bin_path+'/temp', "vod_temp.ts")
                        vod_proc_path = os.path.join(self.vod_path, vod_raw_filename + ".mp4")
                        chat_json_path = os.path.join(self.json_path, vod_raw_filename + ".json")
                        chat_video_path = os.path.join(self.chat_path, vod_raw_filename + ".mp4")

                        with open(os.path.join(str(pathlib.Path(os.path.join("VODS",self.root_path, self.username,  vod_raw_filename)).absolute()), 'metadata.json'), 'w', encoding='utf-8') as f:
                            json.dump(current_vod, f, ensure_ascii=False, indent=4)
                        
                        if self.username == 'KalathrasLolweapon':
                            file_date = datetime.strptime(vod_raw_filename, '%Y%m%d_%Hh%Mm%Ss').date()

                            week_first = file_date - timedelta(days=file_date.weekday())
                            week_last = week_first + timedelta(days=6)

                            vod_year = 'VOD - ' + str(file_date.year)
                            vod_month = f'{file_date.month:02d} - ' + file_date.strftime("%B").upper()
                            vod_week = file_date.strftime("%B").capitalize() + ' ' + str(week_first.day) + '-' + str(week_last.day)
                            
                            chat_year = 'Chat - ' + str(file_date.year)
                            chat_month = f'{file_date.month:02d} - ' + file_date.strftime("%B")

                            vod_path = str(pathlib.Path(os.path.join("VODS",vod_year,vod_month,vod_week)).absolute())
                            chat_path = str(pathlib.Path(os.path.join("Chat",chat_year,chat_month)).absolute())
                            if(os.path.isdir(vod_path) is False): os.makedirs(vod_path)
                            if(os.path.isdir(chat_path) is False): os.makedirs(chat_path)
                            clean_vod_title =  re.sub(r'[/\\:*?"<>|]', '_', current_vod['title'])
                            if len(clean_vod_title) > 202:
                                dif = len(clean_vod_title) - 202
                                clean_vod_title[:-dif] 
                            chat_video_path = os.path.join(chat_path, vod_raw_filename + ".mp4")
                            vod_proc_path = os.path.join(vod_path, vod_raw_filename + '_'+ clean_vod_title + ".mp4")

                        if self.downloadVOD == 1:
                            print('Downloading VOD: ' + current_vod["title"])
                            try:
                                subprocess.call([bin_path+"/TwitchDownloaderCLI.exe", 'videoDownload', '-u', str(current_vod["id"]), '-q', self.quality, "-t", str(self.hls_segmentsVOD), "--ffmpeg-path", bin_path +"/ffmpeg.exe", '--temp-path', bin_path+"/temp", "-o", vod_proc_path])
                            except Exception as e:
                                print('Error', 'A ERROR has ocurred and the VOD will not be downloaded.\n')                                                       
                        if self.downloadMuted == 1:
                            if current_vod['muteInfo']['mutedSegmentConnection'] is not None:
                                mutedSegments = current_vod['muteInfo']['mutedSegmentConnection']['nodes']
                                print('Downloading ' + len(mutedSegments) + ' muted segmes')
                                for muted in mutedSegments:
                                    beg = time.strftime('%Hh%Mm%Ss', time.gmtime(muted['offset']))
                                    end = time.strftime('%Hh%Mm%Ss', time.gmtime(muted['offset'] + muted['duration']))
                                    muted_filename_path = os.path.join(self.muted_path, beg + '-' + end + ".mp4")
                                    subprocess.call([bin_path+"/TwitchDownloaderCLI.exe", 'videoDownload', '-u', current_vod['id'], '-q', self.quality, '-b', str(muted['offset']), '-e', str(muted['offset'] + muted['duration']), "-t", str(self.hls_segmentsVOD), "--ffmpeg-path", bin_path+"/ffmpeg.exe", '--temp-path', bin_path+"/temp" '-o', muted_filename_path])
                            else:
                                print('The VOD has no muted segments')
                        if self.downloadClips == 1:
                            topClips = current_vod['topClips']['edges']
                            if topClips != []:
                                print('Downloading Clips')
                                for clips in topClips:
                                    clip = clips['node']
                                    clean_title = re.sub(r'[/\\:*?"<>|]', '_', clip['title'])
                                    clip_filename_path = os.path.join(self.clips_path, clean_title + '_'+ clip['id'] +".mp4")
                                    subprocess.call([bin_path+"/TwitchDownloaderCLI.exe", 'clipDownload', '-u', clip['slug'], '-q', self.quality, '-o', clip_filename_path])

                            else:
                                print('No Clips has being made during the stream')
                        if self.downloadCHAT == 1:
                            print('Downloading CHAT: ' + current_vod["title"])
                            chat_settings = ["--background-color", "#FF111111", "-w", "500", "-h", "1080", "--outline", "true", "-f", "Arial", "--font-size", "22", "--update-rate", "1.0", "--offline", "--ffmpeg-path", f"{bin_path}/ffmpeg.exe", "--temp-path", f"{bin_path}/temp"]
                            try:
                                if self.os == 'windows':
                                    subprocess.call([bin_path + '/TwitchDownloaderCLI.exe', 'chatdownload', '--id', current_vod["id"], '-o', chat_json_path, '-E'])
                                    print('Rendering CHAT: ' + current_vod["title"])
                                    subprocess.call([bin_path + '/TwitchDownloaderCLI.exe', 'chatrender', '-i', chat_json_path, '-o', chat_video_path] + chat_settings)
                                elif self.os == 'linux':
                                    subprocess.call([bin_path + '/TwitchDownloaderCLI', 'chatdownload', '--id', current_vod["id"], '-o', chat_json_path, '-E'])
                                    subprocess.call([bin_path + '/TwitchDownloaderCLI', 'chatrender', '-i', chat_json_path, '-o', chat_video_path] + chat_settings)
                            except Exception as e:
                                print("A ERROR has ocurred and chat will need to be downloaded and rendered manually\n")
                            
                        if self.downloadChatHTML == 1:
                            print('Downloading chat to html format')
                            chat_html_path = os.path.join(self.html_path, vod_raw_filename + ".html")
                            try:
                                if self.os == 'windows': subprocess.call([bin_path+"/TwitchDownloaderCLI.exe", "chatupdate", "-i", chat_json_path, "-o", chat_html_path, "-E", "--temp-path", f"{bin_path}/temp"])
                                elif self.os == 'linux': subprocess.call([bin_path+"/TwitchDownloaderCLI", "chatupdate", "-i", chat_json_path, "-o", chat_html_path, "-E", "--temp-path", f"{bin_path}/temp"])
                                if self.username == 'KalathrasLolweapon':
                                    print('Uploading html chat to b2 bucket')
                                    subprocess.call(['rclone', 'copy', chat_html_path, 'b2:kala-help/chat_html', '--progress'])
                            except Exception as e:
                                print('A ERROR has ocurred and chat will need to be updated to html manually')
                        
                        if self.uploadCloud == 1:
                            print('Uploading files:')
                            if self.os == 'windows':
                                if self.username == 'KalathrasLolweapon':
                                    subprocess.call(['rclone', 'copy', str(pathlib.Path(__file__).parent.resolve())+'/VODS', 'GD:VODS', '--progress'])
                                    subprocess.call(['rclone', 'copy', str(pathlib.Path(__file__).parent.resolve())+'/Chat', 'GD:Chat', '--progress'])
                                else:subprocess.call(['rclone', 'copy', str(pathlib.Path(__file__).parent.resolve())+'/VODS',  'GD:VODS', '--progress'])
                            elif self.os == 'linux':subprocess.call([bin_path+'/upload.sh', str(pathlib.Path(self.root_path).resolve()),self.username])

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
                        print('THE VOD/CHAT FOR CURRENT LIVESTREAM IS NOT AVAILABLE\nThe current livestream date: ' + is_live["createdAt"] + '\nThe VOD date: ' + current_vod["recordedAt"])
                    print('CURRENT SECCION HAVE FINISHED GOING BACK TO CHECKING')
                    time.sleep(self.refresh)
                else: time.sleep(self.refresh)
            else: time.sleep(self.refresh)
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