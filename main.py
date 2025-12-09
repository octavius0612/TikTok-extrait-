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
        print("✅ Mode IA (Gemini) : ACTIVÉ")
    except Exception as e:
        print(f"⚠️ Erreur config Gemini : {e}")

FALLBACK_QUERIES = [
    "wolf of wall street motivation shorts",
    "peaky blinders thomas shelby shorts",
    "business mindset advice shorts",
    "david goggins discipline shorts",
    "kaamelott replique drole shorts",
    "oss 117 scene culte shorts"
]

# --- FONCTIONS IA ---
def get_search_query():
    if USE_AI:
        try:
            model = genai.GenerativeModel('gemini-2.0-flash')
            prompt = "Donne-moi une courte phrase de recherche pour trouver un short youtube viral sur la motivation, le business ou l'humour. Juste les mots clés. Exemple : 'peaky blinders sigma edit'"
            response = model.generate_content(prompt)
            query = response.text.strip()
            return query
        except: pass
    return random.choice(FALLBACK_QUERIES)

def get_caption(video_title, channel_name):
    if USE_AI:
        try:
            model = genai.GenerativeModel('gemini-2.0-flash')
            prompt = f"Agis comme un expert TikTok. Je poste une vidéo intitulée '{video_title}'. Rédige une description virale courte (max 3 lignes) avec 3 hashtags pertinents."
            response = model.generate_content(prompt)
            return response.text.strip()
        except: pass
    return f"Credit: {channel_name} 🔥\n\nAbonne-toi !\n#viral #shorts #fyp"

# --- MOTEUR TÉLÉCHARGEMENT ---
def download_engine_hybrid(video_id):
    ua = UserAgent()
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    
    # 1. COBALT
    cobalt_servers = [
        "https://api.cobalt.tools/api/json",
        "https://cobalt.kwiatekmiki.pl/api/json",
        "https://cobalt.q11.de/api/json",
        "https://cobalt.synced.vn/api/json",
        "https://cobalt.rive.cafe/api/json",
        "https://api.wkr.fr/api/json"
    ]
    for server in cobalt_servers:
        try:
            payload = {"url": video_url, "vQuality": "1080", "isAudioOnly": False}
            headers = {"Accept": "application/json", "Content-Type": "application/json", "User-Agent": ua.random, "Origin": server.replace("/api/json", ""), "Referer": server.replace("/api/json", "")}
            r = requests.post(server, json=payload, headers=headers, timeout=6)
            if r.status_code == 200:
                data = r.json()
                if data.get('url'):
                    if download_file(data['url']): return True
        except: continue

    # 2. PIPED
    piped_servers = ["https://pipedapi.kavin.rocks", "https://api.piped.otton.uk", "https://pipedapi.moomoo.me", "https://pipedapi.smnz.de", "https://api.piped.privacy.com.de"]
    for server in piped_servers:
        try:
            r = requests.get(f"{server}/streams/{video_id}", timeout=6)
            if r.status_code == 200:
                data = r.json()
                for s in data.get('videoStreams', []):
                    if s.get('format') == 'MPEG-4' and ('1080p' in s['quality'] or '720p' in s['quality']):
                        if download_file(s['url']): return True
        except: continue

    # 3. INVIDIOUS
    invidious_servers = ["https://inv.tux.pizza", "https://vid.puffyan.us", "https://yewtu.be", "https://invidious.jing.rocks"]
    for server in invidious_servers:
        try:
            direct_url = f"{server}/latest_version?id={video_id}&itag=22"
            headers = {"User-Agent": ua.random}
            if download_file(direct_url, headers): return True
        except: continue

    return False

def download_file(url, headers=None):
    try:
        if not headers: headers = {"User-Agent": UserAgent().random}
        r = requests.get(url, headers=headers, stream=True, timeout=60)
        content_type = r.headers.get('Content-Type', '')
        if 'text/html' in content_type: return False

        with open(FILENAME, 'wb') as f:
            downloaded = 0
            for chunk in r.iter_content(chunk_size=1024*1024):
                if chunk: 
                    f.write(chunk)
                    downloaded += len(chunk)
                    if downloaded > 24 * 1024 * 1024: break
        return os.path.getsize(FILENAME) > 50000 
    except: return False

# --- SECTION SPÉCIALE ENVOI EMAIL ---

def process_email_delivery(video_data):
    """Fonction dédiée à l'envoi de l'email avec la vidéo"""
    print("📧 Démarrage de la procédure d'envoi d'email...")
    
    email_user = os.environ.get('EMAIL_USER')
    email_pass = os.environ.get('EMAIL_PASSWORD')
    email_receiver = os.environ.get('EMAIL_RECEIVER')
    
    # Vérification des identifiants
    if not all([email_user, email_pass, email_receiver]):
        print("❌ Erreur : Identifiants email manquants dans les variables d'environnement.")
        return False

    # Vérification de la présence du fichier
    if not os.path.exists(FILENAME):
        print("❌ Erreur : Le fichier vidéo n'existe pas sur le disque.")
        return False

    msg = EmailMessage()
    msg['Subject'] = f"🎬 {video_data['title']}"
    msg['From'] = email_user
    msg['To'] = email_receiver
    msg.set_content(f"{video_data['caption']}\n\nSource: {video_data['url']}")
    
    try:
        with open(FILENAME, 'rb') as f:
            file_data = f.read()
            msg.add_attachment(file_data, maintype='video', subtype='mp4', filename="short.mp4")
        
        print("🚀 Connexion au serveur SMTP Gmail...")
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(email_user, email_pass)
            smtp.send_message(msg)
        
        print("✅ Email envoyé avec succès !")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de l'envoi de l'email : {str(e)}")
        return False

# --- ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/run_bot', methods=['POST'])
def run_bot_api():
    if not API_KEY:
        return jsonify({"status": "error", "message": "Clé API YouTube manquante !"})

    try:
        search_query = get_search_query()
        youtube = build('youtube', 'v3', developerKey=API_KEY)
        request = youtube.search().list(part="snippet", maxResults=20, q=search_query, type="video", videoDuration="short", order="viewCount", relevanceLanguage="fr")
        response = request.execute()
        
        if not response['items'] and USE_AI:
            search_query = random.choice(FALLBACK_QUERIES)
            request = youtube.search().list(part="snippet", maxResults=20, q=search_query, type="video", videoDuration="short", order="viewCount", relevanceLanguage="fr")
            response = request.execute()

        if not response['items']:
            return jsonify({"status": "error", "message": "Aucune vidéo trouvée."})
        
        candidates = random.sample(response['items'], min(3, len(response['items'])))
        
        for video in candidates:
            title = html.unescape(video['snippet']['title'])
            channel = html.unescape(video['snippet']['channelTitle'])
            video_id = video['id']['videoId']
            
            print(f"🎯 Cible : {title}")

            if download_engine_hybrid(video_id):
                caption = get_caption(title, channel)
                
                # --- APPEL DE LA FONCTION D'ENVOI D'EMAIL ICI ---
                email_success = process_email_delivery({
                    'title': title, 
                    'url': f"https://youtu.be/{video_id}", 
                    'caption': caption
                })
                
                status_msg = "succès" if email_success else "warning"
                msg_text = "Vidéo téléchargée et envoyée !" if email_success else "Vidéo téléchargée mais erreur d'envoi email."

                return jsonify({
                    "status": status_msg, 
                    "message": msg_text,
                    "title": title, 
                    "channel": channel,
                    "caption": caption,
                    "video_url": "/get_video_file",
                    "ai_used": USE_AI
                })
        
        return jsonify({"status": "error", "message": "Échec téléchargement (3 vidéos testées)."})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/get_video_file')
def get_video_file():
    try:
        return send_file(FILENAME, mimetype='video/mp4')
    except:
        return "Fichier introuvable ou pas encore téléchargé", 404

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)


