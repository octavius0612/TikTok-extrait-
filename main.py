import os
import smtplib
import random
import html
import requests
from flask import Flask
from email.message import EmailMessage
from googleapiclient.discovery import build
from fake_useragent import UserAgent

app = Flask(__name__)

# --- CONFIGURATION ---
# Sur Render, ces clés seront dans les "Environment Variables"
API_KEY = os.environ.get('YOUTUBE_API_KEY') 
FILENAME = "/tmp/viral_video.mp4" # Important: Sur Render on écrit dans /tmp
MAX_SIZE_MB = 24.0

QUERIES = [
    "wolf of wall street motivation shorts",
    "peaky blinders thomas shelby shorts",
    "business mindset advice shorts",
    "david goggins discipline shorts",
    "kaamelott replique drole shorts",
    "oss 117 scene culte shorts",
    "motivation sport speech shorts"
]

# Liste des serveurs Piped (qui ne bloquent pas Render)
PIPED_INSTANCES = [
    "https://pipedapi.kavin.rocks",
    "https://api.piped.otton.uk",
    "https://pipedapi.moomoo.me",
    "https://pipedapi.smnz.de",
    "https://api.piped.privacy.com.de"
]

@app.route('/')
def home():
    return "Le Bot TikTok est en ligne. Va sur /run pour le lancer."

@app.route('/run')
def run_bot():
    """Cette URL déclenche tout le processus"""
    try:
        # 1. Recherche
        video_info = search_google_api()
        if not video_info:
            return "❌ Erreur Recherche: Rien trouvé ou Clé API invalide."
        
        # 2. Téléchargement
        success = download_via_piped(video_info['id'])
        if not success:
            return "❌ Erreur Téléchargement: Piped n'a pas répondu."
        
        # 3. Envoi
        deliver(video_info)
        return f"✅ SUCCÈS ! Email envoyé pour : {video_info['title']}"
        
    except Exception as e:
        return f"❌ Erreur Critique : {str(e)}"

# --- FONCTIONS UTILES (Les mêmes qu'avant) ---

def search_google_api():
    if not API_KEY: return None
    query = random.choice(QUERIES)
    print(f"📡 Recherche : {query}")
    
    youtube = build('youtube', 'v3', developerKey=API_KEY)
    request = youtube.search().list(
        part="snippet", maxResults=20, q=query, type="video",
        videoDuration="short", order="viewCount", relevanceLanguage="fr"
    )
    response = request.execute()
    if not response['items']: return None
    
    video = random.choice(response['items'])
    title = html.unescape(video['snippet']['title'])
    video_id = video['id']['videoId']
    return {'title': title, 'id': video_id, 'url': f"https://youtu.be/{video_id}"}

def download_via_piped(video_id):
    ua = UserAgent()
    random.shuffle(PIPED_INSTANCES)
    
    for instance in PIPED_INSTANCES:
        try:
            print(f"Essai sur {instance}...")
            r = requests.get(f"{instance}/streams/{video_id}", timeout=10)
            if r.status_code != 200: continue
            
            data = r.json()
            target_url = None
            
            # On cherche le MP4
            for s in data.get('videoStreams', []):
                if s.get('format') == 'MPEG-4' and s.get('quality') == '1080p':
                    target_url = s.get('url')
                    break
            
            if not target_url:
                 for s in data.get('videoStreams', []):
                    if s.get('format') == 'MPEG-4' and s.get('quality') == '720p':
                        target_url = s.get('url')
                        break
            
            if target_url:
                resp = requests.get(target_url, headers={"User-Agent": ua.random}, stream=True, timeout=30)
                with open(FILENAME, 'wb') as f:
                    dl = 0
                    for chunk in resp.iter_content(chunk_size=1024*1024):
                        if chunk:
                            f.write(chunk)
                            dl += len(chunk)
                            if dl > 24*1024*1024: break
                
                if os.path.getsize(FILENAME) > 5000:
                    return True
        except:
            continue
    return False

def deliver(video_data):
    email_user = os.environ.get('EMAIL_USER')
    email_pass = os.environ.get('EMAIL_PASSWORD')
    email_receiver = os.environ.get('EMAIL_RECEIVER')
    
    msg = EmailMessage()
    msg['Subject'] = f"🎬 {video_data['title']}"
    msg['From'] = email_user
    msg['To'] = email_receiver
    msg.set_content(f"Source : {video_data['url']}")
    
    with open(FILENAME, 'rb') as f:
        msg.add_attachment(f.read(), maintype='video', subtype='mp4', filename="short.mp4")
        
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(email_user, email_pass)
        smtp.send_message(msg)

if __name__ == "__main__":
    # Ceci est pour tester en local, sur Render gunicorn s'en charge
    app.run(host='0.0.0.0', port=5000)
