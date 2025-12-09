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

app = Flask(__name__)

# --- CONFIGURATION ---
API_KEY = os.environ.get('YOUTUBE_API_KEY') 
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
FILENAME = "/tmp/viral_video.mp4"

# --- CONFIGURATION IA ---
USE_AI = False
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        USE_AI = True
    except: pass

FALLBACK_QUERIES = [
    "motivation success",
    "peaky blinders",
    "business mindset",
    "david goggins",
    "kaamelott",
    "oss 117"
]

# --- 1. FONCTIONS INTELLIGENTES (IA) ---

def get_search_query():
    """Demande à l'IA un mot-clé simple pour la recherche"""
    if USE_AI:
        try:
            model = genai.GenerativeModel('gemini-2.0-flash')
            # Dailymotion préfère les mots-clés simples
            prompt = "Donne-moi 1 seul mot-clé ou une expression courte (max 3 mots) pour trouver une vidéo virale drôle ou motivation. Exemple: 'sigma rule' ou 'oss 117'. Pas de phrase."
            response = model.generate_content(prompt)
            return response.text.strip()
        except: pass
    return random.choice(FALLBACK_QUERIES)

def get_caption(title, channel):
    """Génère la description TikTok"""
    if USE_AI:
        try:
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(f"Ecris une description tiktok virale pour la vidéo '{title}'. Ajoute 3 hashtags.")
            return response.text.strip()
        except: pass
    return f"Credit: {channel} 🔥 #viral #fyp"

# --- 2. MODULE DAILYMOTION (PLAN B ROBUSTE) ---

def search_and_download_dailymotion(query):
    print(f"🔵 Tentative Dailymotion pour : {query}")
    try:
        # Recherche API Dailymotion (Publique, pas besoin de clé)
        # On filtre : pas de live, moins de 2 min (format short)
        dm_url = f"https://api.dailymotion.com/videos?fields=id,title,owner.screenname&flags=no_live&shorter_than=120&sort=visited&search={query}&limit=10"
        
        r = requests.get(dm_url, timeout=10)
        data = r.json()
        
        if not data.get('list'):
            print("❌ Dailymotion : Aucun résultat trouvé.")
            return None
            
        # On prend une vidéo au hasard
        video = random.choice(data['list'])
        video_id = video['id']
        title = video['title']
        channel = video['owner.screenname']
        
        print(f"✅ Dailymotion Trouvé : {title}")
        
        # Astuce de Hacker : On interroge les métadonnées du player pour avoir le lien direct MP4
        meta_url = f"https://www.dailymotion.com/player/metadata/video/{video_id}"
        meta_r = requests.get(meta_url, timeout=10)
        meta_data = meta_r.json()
        
        qualities = meta_data.get('qualities', {})
        download_url = None
        
        # On cherche la meilleure qualité disponible
        for q in ['1080', '720', '480', '380', 'auto']:
            if q in qualities:
                download_url = qualities[q][0]['url']
                break
        
        if download_url:
            if download_file(download_url):
                return {
                    'title': title, 
                    'channel': channel, 
                    'url': f"https://dailymotion.com/video/{video_id}", 
                    'source': 'Dailymotion'
                }
                
    except Exception as e:
        print(f"❌ Erreur Dailymotion : {e}")
        return None
    
    return None

# --- 3. MODULE YOUTUBE (COBALT) ---

def download_youtube_hybrid(video_id):
    ua = UserAgent()
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    
    # Serveurs Cobalt
    servers = [
        "https://api.cobalt.tools/api/json",
        "https://cobalt.kwiatekmiki.pl/api/json",
        "https://api.wkr.fr/api/json",
        "https://cobalt.rive.cafe/api/json"
    ]
    
    for server in servers:
        try:
            r = requests.post(server, 
                json={"url": video_url, "vQuality": "1080", "isAudioOnly": False},
                headers={"Accept": "application/json", "User-Agent": ua.random},
                timeout=6)
            
            if r.status_code == 200:
                data = r.json()
                if data.get('url'):
                    if download_file(data['url']): return True
        except: continue
    return False

def download_file(url):
    try:
        # User-Agent aléatoire pour ne pas être bloqué
        headers = {"User-Agent": UserAgent().random}
        r = requests.get(url, stream=True, headers=headers, timeout=60)
        
        # On vérifie que c'est bien une vidéo et pas une page d'erreur
        content_type = r.headers.get('Content-Type', '')
        if 'text/html' in content_type: return False

        with open(FILENAME, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024*1024):
                if chunk: f.write(chunk)
        
        # Vérif taille (> 50KB)
        return os.path.getsize(FILENAME) > 50000
    except: return False

# --- ROUTES DU SITE ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/run_bot', methods=['POST'])
def run_bot_api():
    try:
        search_query = get_search_query()
        youtube_success = False
        
        # --- ESSAI 1 : YOUTUBE ---
        if API_KEY:
            try:
                youtube = build('youtube', 'v3', developerKey=API_KEY)
                request = youtube.search().list(part="snippet", maxResults=5, q=search_query, type="video", videoDuration="short", order="viewCount")
                response = request.execute()
                
                if response.get('items'):
                    # On tente jusqu'à 2 vidéos YouTube
                    for item in random.sample(response['items'], min(2, len(response['items']))):
                        vid_id = item['id']['videoId']
                        title = html.unescape(item['snippet']['title'])
                        channel = html.unescape(item['snippet']['channelTitle'])
                        
                        if download_youtube_hybrid(vid_id):
                            caption = get_caption(title, channel)
                            deliver(title, f"https://youtu.be/{vid_id}", caption, "YouTube")
                            return jsonify({"status": "success", "title": title, "caption": caption, "video_url": "/get_video_file", "source": "YouTube"})
            except Exception as e:
                print(f"⚠️ YouTube erreur : {e}")

        # --- ESSAI 2 : DAILYMOTION (Si YouTube rate) ---
        print("⚠️ Passage au Plan B : Dailymotion")
        dm_result = search_and_download_dailymotion(search_query)
        
        if dm_result:
            caption = get_caption(dm_result['title'], dm_result['channel'])
            deliver(dm_result['title'], dm_result['url'], caption, "Dailymotion")
            return jsonify({
                "status": "success", 
                "title": dm_result['title'], 
                "caption": caption, 
                "video_url": "/get_video_file", 
                "source": "Dailymotion"
            })

        return jsonify({"status": "error", "message": "Impossible de télécharger sur YouTube ET Dailymotion."})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/get_video_file')
def get_video_file():
    try:
        return send_file(FILENAME, mimetype='video/mp4')
    except:
        return "Fichier introuvable", 404

def deliver(title, url, caption, source):
    email_user = os.environ.get('EMAIL_USER')
    email_pass = os.environ.get('EMAIL_PASSWORD')
    email_receiver = os.environ.get('EMAIL_RECEIVER')
    if not all([email_user, email_pass, email_receiver]): return

    msg = EmailMessage()
    msg['Subject'] = f"🎬 {source} : {title}"
    msg['From'] = email_user
    msg['To'] = email_receiver
    msg.set_content(f"{caption}\n\nSource: {url}")
    
    with open(FILENAME, 'rb') as f:
        msg.add_attachment(f.read(), maintype='video', subtype='mp4', filename="short.mp4")
        
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(email_user, email_pass)
        smtp.send_message(msg)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
