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
# Récupération des clés depuis Render
API_KEY = os.environ.get('YOUTUBE_API_KEY') 
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
FILENAME = "/tmp/viral_video.mp4"

# --- CONFIGURATION IA (HYBRIDE) ---
USE_AI = False
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        USE_AI = True
        print("✅ Mode IA (Gemini) : ACTIVÉ")
    except Exception as e:
        print(f"⚠️ Erreur config Gemini : {e}")

# Listes de secours (Si pas d'IA ou erreur)
FALLBACK_QUERIES = [
    "wolf of wall street motivation shorts",
    "peaky blinders thomas shelby shorts",
    "business mindset advice shorts",
    "david goggins discipline shorts",
    "kaamelott replique drole shorts",
    "oss 117 scene culte shorts"
]

# --- FONCTIONS INTELLIGENTES (IA) ---

def get_search_query():
    """Demande à Gemini une idée de recherche ou utilise l'aléatoire"""
    if USE_AI:
        try:
            model = genai.GenerativeModel('gemini-2.0-flash')
            prompt = "Donne-moi une courte phrase de recherche pour trouver un short youtube viral sur la motivation, le business ou l'humour. Juste les mots clés. Exemple : 'peaky blinders sigma edit'"
            response = model.generate_content(prompt)
            query = response.text.strip()
            return query
        except:
            pass # Si erreur, on passe à la suite
    
    return random.choice(FALLBACK_QUERIES)

def get_caption(video_title, channel_name):
    """Génère une description TikTok via IA"""
    if USE_AI:
        try:
            model = genai.GenerativeModel('gemini-2.0-flash')
            prompt = f"Agis comme un expert TikTok. Je poste une vidéo intitulée '{video_title}'. Rédige une description virale courte (max 3 lignes) avec 3 hashtags pertinents."
            response = model.generate_content(prompt)
            return response.text.strip()
        except:
            pass
            
    return f"Credit: {channel_name} 🔥\n\nAbonne-toi !\n#viral #shorts #fyp"

# --- MOTEUR DE TÉLÉCHARGEMENT MASSIF ---

def download_engine_hybrid(video_id):
    """Essaie de télécharger la vidéo en utilisant toutes les méthodes possibles"""
    ua = UserAgent()
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    
    # 1. LISTE COBALT (Priorité Qualité 1080p)
    cobalt_servers = [
        "https://api.cobalt.tools/api/json",
        "https://cobalt.kwiatekmiki.pl/api/json",
        "https://cobalt.q11.de/api/json",
        "https://cobalt.synced.vn/api/json",
        "https://cobalt.rive.cafe/api/json",
        "https://api.wkr.fr/api/json"
    ]
    
    print("🛡️ [1/3] Tentative Cobalt...")
    for server in cobalt_servers:
        try:
            payload = {"url": video_url, "vQuality": "1080", "isAudioOnly": False}
            headers = {
                "Accept": "application/json", 
                "Content-Type": "application/json", 
                "User-Agent": ua.random,
                "Origin": server.replace("/api/json", ""),
                "Referer": server.replace("/api/json", "")
            }
            r = requests.post(server, json=payload, headers=headers, timeout=8)
            if r.status_code == 200:
                data = r.json()
                if data.get('url'):
                    if download_file(data['url']): return True
        except: continue

    # 2. LISTE PIPED (Backup API)
    print("🛡️ [2/3] Tentative Piped...")
    piped_servers = [
        "https://pipedapi.kavin.rocks",
        "https://api.piped.otton.uk",
        "https://pipedapi.moomoo.me",
        "https://pipedapi.smnz.de",
        "https://api.piped.privacy.com.de"
    ]
    for server in piped_servers:
        try:
            r = requests.get(f"{server}/streams/{video_id}", timeout=8)
            if r.status_code == 200:
                data = r.json()
                for s in data.get('videoStreams', []):
                    # On cherche du MP4 en HD ou SD
                    if s.get('format') == 'MPEG-4' and ('1080p' in s['quality'] or '720p' in s['quality']):
                        if download_file(s['url']): return True
        except: continue

    # 3. LISTE INVIDIOUS (Direct Stream - Dernier recours)
    print("🛡️ [3/3] Tentative Invidious Direct...")
    invidious_servers = [
        "https://inv.tux.pizza",
        "https://vid.puffyan.us",
        "https://yewtu.be",
        "https://invidious.jing.rocks"
    ]
    for server in invidious_servers:
        try:
            # itag 22 = 720p MP4 (Standard YouTube)
            direct_url = f"{server}/latest_version?id={video_id}&itag=22"
            headers = {"User-Agent": ua.random}
            if download_file(direct_url, headers): return True
        except: continue

    return False

def download_file(url, headers=None):
    """Télécharge physiquement le fichier sur le disque"""
    try:
        if not headers: headers = {"User-Agent": UserAgent().random}
        
        # Stream=True est crucial pour ne pas saturer la mémoire
        r = requests.get(url, headers=headers, stream=True, timeout=20)
        
        # Vérification anti-erreur (Si on reçoit du HTML au lieu d'une vidéo, c'est un échec)
        content_type = r.headers.get('Content-Type', '')
        if 'text/html' in content_type: return False

        with open(FILENAME, 'wb') as f:
            downloaded = 0
            for chunk in r.iter_content(chunk_size=1024*1024):
                if chunk: 
                    f.write(chunk)
                    downloaded += len(chunk)
                    if downloaded > 24 * 1024 * 1024: break # Stop à 24MB pour Gmail
        
        # On vérifie que le fichier n'est pas vide (> 50KB)
        return os.path.getsize(FILENAME) > 50000 
    except: return False

# --- ROUTES DU SITE WEB ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/run_bot', methods=['POST'])
def run_bot_api():
    if not API_KEY:
        return jsonify({"status": "error", "message": "Clé API YouTube manquante !"})

    try:
        # 1. Recherche (IA ou Classique)
        search_query = get_search_query()

        # 2. Appel YouTube API
        youtube = build('youtube', 'v3', developerKey=API_KEY)
        request = youtube.search().list(
            part="snippet", maxResults=20, q=search_query, type="video",
            videoDuration="short", order="viewCount", relevanceLanguage="fr"
        )
        response = request.execute()
        
        # Si la recherche IA est trop bizarre et ne donne rien, on fallback sur du classique
        if not response['items'] and USE_AI:
            search_query = random.choice(FALLBACK_QUERIES)
            request = youtube.search().list(
                part="snippet", maxResults=20, q=search_query, type="video",
                videoDuration="short", order="viewCount", relevanceLanguage="fr"
            )
            response = request.execute()

        if not response['items']:
            return jsonify({"status": "error", "message": "Aucune vidéo trouvée."})
        
        # --- STRATÉGIE MULTI-CIBLES ---
        # On ne parie pas tout sur une seule vidéo. On en sélectionne 3 potentielles.
        # Si la première échoue au téléchargement, on tente la suivante.
        candidates = random.sample(response['items'], min(3, len(response['items'])))
        
        for video in candidates:
            title = html.unescape(video['snippet']['title'])
            channel = html.unescape(video['snippet']['channelTitle'])
            video_id = video['id']['videoId']
            
            print(f"🎯 Cible : {title}")

            # TENTATIVE DE TÉLÉCHARGEMENT
            if download_engine_hybrid(video_id):
                # SUCCÈS ! On génère la description et on envoie
                caption = get_caption(title, channel)
                
                # Envoi Email
                deliver({'title': title, 'url': f"https://youtu.be/{video_id}", 'caption': caption})
                
                # Réponse au site web
                return jsonify({
                    "status": "success", 
                    "title": title, 
                    "channel": channel,
                    "caption": caption,
                    "video_url": "/get_video_file",
                    "ai_used": USE_AI
                })
        
        # Si on arrive ici, c'est que les 3 vidéos ont échoué sur tous les serveurs
        return jsonify({"status": "error", "message": "Échec téléchargement (3 vidéos testées)."})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/get_video_file')
def get_video_file():
    return send_file(FILENAME, mimetype='video/mp4')

def deliver(video_data):
    email_user = os.environ.get('EMAIL_USER')
    email_pass = os.environ.get('EMAIL_PASSWORD')
    email_receiver = os.environ.get('EMAIL_RECEIVER')
    if not all([email_user, email_pass, email_receiver]): return

    msg = EmailMessage()
    msg['Subject'] = f"🎬 {video_data['title']}"
    msg['From'] = email_user
    msg['To'] = email_receiver
    msg.set_content(f"Voici ta vidéo.\n\nDescription :\n{video_data['caption']}\n\nSource : {video_data['url']}")
    
    with open(FILENAME, 'rb') as f:
        msg.add_attachment(f.read(), maintype='video', subtype='mp4', filename="short.mp4")
        
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(email_user, email_pass)
        smtp.send_message(msg)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
