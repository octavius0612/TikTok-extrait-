import os
import smtplib
import random
import html
import requests
import time
from flask import Flask, render_template, jsonify, send_file
from email.message import EmailMessage
from googleapiclient.discovery import build
from fake_useragent import UserAgent
import google.generativeai as genai
import yt_dlp

app = Flask(__name__)

# --- CONFIGURATION ---
API_KEY = os.environ.get('YOUTUBE_API_KEY') 
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# IMPORTANT : Sur Render, on DOIT écrire dans /tmp
# Sinon : "Read-only file system error"
FILENAME = "/tmp/viral_video.mp4"

# --- CONFIG IA ---
USE_AI = False
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        USE_AI = True
    except: pass

FALLBACK_QUERIES = [
    "wolf of wall street motivation shorts",
    "peaky blinders thomas shelby shorts",
    "business mindset advice shorts",
    "david goggins discipline shorts",
    "kaamelott replique drole shorts"
]

# --- COFFRE DE SECOURS (Si YouTube bloque l'IP) ---
EMERGENCY_VAULT = [
    {"title": "Wolf of Wall Street - Sell me this pen", "url": "https://ia801602.us.archive.org/11/items/wolf-of-wall-street-sell-me-this-pen/Wolf_of_Wall_Street_Sell_Me_This_Pen.mp4", "caption": "Sell me this pen! 🖊️ #viral"},
    {"title": "OSS 117 Rire", "url": "https://ia902606.us.archive.org/3/items/oss-117-le-caire-nid-d-espions-bambino/OSS%20117%20Le%20Caire%20nid%20d%27espions%20-%20Bambino.mp4", "caption": "Habile ! 😎 #oss117"},
]

# --- FONCTIONS ---

def get_search_query():
    if USE_AI:
        try:
            model = genai.GenerativeModel('gemini-2.0-flash')
            prompt = "Donne-moi 1 idée de recherche youtube shorts viral (Business/Motivation). Juste les mots clés."
            response = model.generate_content(prompt)
            return response.text.strip()
        except: pass
    return random.choice(FALLBACK_QUERIES)

def get_caption(title, channel):
    if USE_AI:
        try:
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(f"Description tiktok virale pour '{title}'. 3 hashtags.")
            return response.text.strip()
        except: pass
    return f"Credit: {channel} 🔥 #viral"

# --- MOTEUR SMART TV (Avec correctif disque) ---
def download_with_smart_tv(video_url):
    print("📺 Tentative mode Smart TV...")
    
    # Configuration stricte pour Render : TOUT doit aller dans /tmp
    ydl_opts = {
        'format': 'best[ext=mp4]/best', 
        'outtmpl': FILENAME,
        'paths': {'home': '/tmp', 'temp': '/tmp'}, # Force les dossiers temp
        'cache_dir': '/tmp/yt-dlp-cache',          # Force le cache dans tmp
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'extractor_args': {'youtube': {'player_client': ['android_tv', 'web']}},
        'user_agent': 'Mozilla/5.0 (Linux; Android 9; BRAVIA 4K UR3 Build/PPR1.180610.011; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/78.0.3904.108 Mobile Safari/537.36'
    }

    try:
        # Nettoyage préventif
        if os.path.exists(FILENAME): 
            os.remove(FILENAME)
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        
        # Vérification
        if os.path.exists(FILENAME) and os.path.getsize(FILENAME) > 50000:
            print("✅ Succès téléchargement Smart TV !")
            return True
            
    except Exception as e:
        print(f"⚠️ Échec Smart TV : {e}")
    
    return False

# --- TÉLÉCHARGEMENT DIRECT (ARCHIVE.ORG) ---
def download_direct_file(url):
    print("🛡️ Téléchargement Direct (Coffre-fort)...")
    try:
        if os.path.exists(FILENAME): os.remove(FILENAME)
        
        r = requests.get(url, stream=True, timeout=60, headers={"User-Agent": UserAgent().random})
        if r.status_code != 200: return False
        
        with open(FILENAME, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024*1024):
                if chunk: f.write(chunk)
        return os.path.getsize(FILENAME) > 50000
    except Exception as e:
        print(f"❌ Erreur Disque/Réseau : {e}")
        return False

# --- ROUTES ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/run_bot', methods=['POST'])
def run_bot_api():
    if not API_KEY: return jsonify({"status": "error", "message": "Clé API manquante"})

    try:
        # 1. Recherche
        youtube = build('youtube', 'v3', developerKey=API_KEY)
        request = youtube.search().list(part="snippet", maxResults=5, q=get_search_query(), type="video", videoDuration="short", order="viewCount")
        response = request.execute()
        
        success = False
        final_data = {}

        # 2. Tentative Smart TV
        if response.get('items'):
            for item in random.sample(response['items'], min(2, len(response['items']))):
                vid_id = item['id']['videoId']
                title = html.unescape(item['snippet']['title'])
                url = f"https://www.youtube.com/watch?v={vid_id}"
                
                if download_with_smart_tv(url):
                    success = True
                    final_data = {
                        "title": title,
                        "url": url,
                        "caption": get_caption(title, item['snippet']['channelTitle']),
                        "source": "YouTube (Smart TV)"
                    }
                    break
        
        # 3. PLAN Z : COFFRE-FORT (Si l'IP est bannie)
        if not success:
            print("🚨 MODE URGENCE ACTIVÉ")
            backup = random.choice(EMERGENCY_VAULT)
            if download_direct_file(backup['url']):
                success = True
                final_data = {
                    "title": backup['title'],
                    "url": backup['url'],
                    "caption": backup['caption'],
                    "source": "COFFRE DE SECOURS (Archive.org)"
                }

        if success:
            deliver(final_data)
            return jsonify({
                "status": "success", 
                "title": final_data['title'], 
                "caption": final_data['caption'], 
                "video_url": "/get_video_file",
                "ai_used": USE_AI
            })
        
        return jsonify({"status": "error", "message": "Erreur critique : Impossible d'écrire sur le disque ou IP bannie."})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/get_video_file')
def get_video_file():
    return send_file(FILENAME, mimetype='video/mp4')

def deliver(data):
    user = os.environ.get('EMAIL_USER')
    pwd = os.environ.get('EMAIL_PASSWORD')
    rcv = os.environ.get('EMAIL_RECEIVER')
    if not all([user, pwd, rcv]): return

    msg = EmailMessage()
    msg['Subject'] = f"🎬 {data['title']}"
    msg['From'] = user
    msg['To'] = rcv
    msg.set_content(f"{data['caption']}\n\nSource: {data['url']}")
    
    with open(FILENAME, 'rb') as f:
        msg.add_attachment(f.read(), maintype='video', subtype='mp4', filename="short.mp4")
        
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(user, pwd)
        smtp.send_message(msg)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)


