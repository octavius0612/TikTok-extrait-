import os
import smtplib
import random
import html
import time
import requests
from email.message import EmailMessage
from googleapiclient.discovery import build
import yt_dlp

# --- CONFIGURATION ---
API_KEY = os.environ.get('YOUTUBE_API_KEY') 
FILENAME = "viral_masterpiece.mp4"
MAX_SIZE_MB = 24.0

QUERIES = [
    "motivation discipline speech shorts",
    "sigma male grindset shorts",
    "business success advice shorts",
    "peaky blinders thomas shelby shorts",
    "wolf of wall street sales shorts",
    "kaamelott replique culte shorts",
    "oss 117 drôle shorts"
]

# --- 1. RECHERCHE PRO (API GOOGLE) ---
def search_viral_video_official():
    if not API_KEY:
        print("❌ Clé API manquante.")
        return None

    query = random.choice(QUERIES)
    print(f"📡 API Google : Recherche '{query}'")

    try:
        youtube = build('youtube', 'v3', developerKey=API_KEY)
        request = youtube.search().list(
            part="snippet", maxResults=10, q=query, type="video",
            videoDuration="short", order="viewCount", relevanceLanguage="fr"
        )
        response = request.execute()

        if not response['items']: return None

        video = random.choice(response['items'])
        title = html.unescape(video['snippet']['title'])
        video_id = video['id']['videoId']
        
        # On construit l'URL classique (plus compatible que /shorts/)
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        print(f"✅ Cible verrouillée : {title}")
        print(f"🔗 Lien : {video_url}")
        
        return {'title': title, 'url': video_url}

    except Exception as e:
        print(f"❌ Erreur API Google : {e}")
        return None

# --- 2. TÉLÉCHARGEMENT : PLAN A (YT-DLP MODE IPHONE) ---
def download_with_ytdlp_ios(url):
    print("💿 Plan A : Tentative yt-dlp (Mode iPhone)...")
    
    # Configuration spéciale pour contourner le blocage "Sign in"
    ydl_opts = {
        'format': 'bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]',
        'outtmpl': FILENAME,
        'quiet': True,
        'no_warnings': True,
        # L'ASTUCE EST ICI : On simule un client iOS
        'extractor_args': {'youtube': {'player_client': ['ios']}},
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        if os.path.exists(FILENAME) and os.path.getsize(FILENAME) > 5000:
            print("✅ Succès Plan A (yt-dlp) !")
            return True
    except Exception as e:
        print(f"⚠️ Plan A échoué : {e}")
    
    return False

# --- 3. TÉLÉCHARGEMENT : PLAN B (COBALT AVEC HEADERS) ---
def download_with_cobalt(url):
    print("🛡️ Plan B : Tentative Cobalt API...")
    
    # Liste mise à jour et nettoyée
    servers = [
        "https://cobalt.kwiatekmiki.pl/api/json",
        "https://cobalt.q11.de/api/json",
        "https://api.cobalt.tools/api/json",
        "https://cobalt.synced.vn/api/json"
    ]
    
    # On se fait passer pour un navigateur Firefox
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
        "Origin": "https://cobalt.tools",
        "Referer": "https://cobalt.tools/"
    }
    
    payload = {
        "url": url,
        "vCodec": "h264",
        "vQuality": "1080",
        "isAudioOnly": False
    }

    for server in servers:
        print(f"   Trying {server}...")
        try:
            r = requests.post(server, json=payload, headers=headers, timeout=15)
            if r.status_code != 200: continue
            
            data = r.json()
            dl_link = data.get('url')
            
            if dl_link:
                print("   ⬇️ Téléchargement du fichier...")
                file_resp = requests.get(dl_link, stream=True)
                with open(FILENAME, 'wb') as f:
                    for chunk in file_resp.iter_content(chunk_size=1024*1024):
                        if chunk: f.write(chunk)
                
                if os.path.getsize(FILENAME) > 5000:
                    print("✅ Succès Plan B (Cobalt) !")
                    return True
        except:
            continue
            
    print("❌ Tous les plans de téléchargement ont échoué.")
    return False

# --- 4. LIVRAISON ---
def deliver(video_data):
    email_user = os.environ.get('EMAIL_USER')
    email_pass = os.environ.get('EMAIL_PASSWORD')
    email_receiver = os.environ.get('EMAIL_RECEIVER')

    if not all([email_user, email_pass, email_receiver]): return

    if os.path.getsize(FILENAME) > 25 * 1024 * 1024:
        print("⚠️ Vidéo trop lourde pour Gmail (>25Mo).")
        # Ici on pourrait implémenter un upload WeTransfer, mais restons simple
        return

    msg = EmailMessage()
    msg['Subject'] = f"🚀 VIRAL : {video_data['title']}"
    msg['From'] = email_user
    msg['To'] = email_receiver
    msg.set_content(f"Voici ta vidéo HD.\nSource : {video_data['url']}")

    with open(FILENAME, 'rb') as f:
        msg.add_attachment(f.read(), maintype='video', subtype='mp4', filename="video.mp4")

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(email_user, email_pass)
        smtp.send_message(msg)
    print("✅ Email envoyé !")

if __name__ == "__main__":
    # 1. Recherche
    video_info = search_viral_video_official()
    
    if video_info:
        # 2. Téléchargement (Essai A puis B)
        success = download_with_ytdlp_ios(video_info['url'])
        if not success:
            success = download_with_cobalt(video_info['url'])
        
        # 3. Envoi
        if success:
            deliver(video_info)

