import os
import smtplib
import random
import requests
from flask import Flask, render_template, jsonify, send_file, request
from email.message import EmailMessage
from fake_useragent import UserAgent
import google.generativeai as genai

app = Flask(__name__)

# --- CONFIGURATION ---
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
EMAIL_USER = os.environ.get('EMAIL_USER')
EMAIL_PASS = os.environ.get('EMAIL_PASSWORD')
EMAIL_RECEIVER = os.environ.get('EMAIL_RECEIVER')
FILENAME = "/tmp/viral_video.mp4"

# --- IA ---
USE_AI = False
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        USE_AI = True
    except: pass

ARCHIVE_TOPICS = [
    "tiktok viral", "funny short", "movie clip vertical", 
    "motivation video", "sigma grindset", "peaky blinders short"
]

def get_ai_topic():
    if USE_AI:
        try:
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content("Donne-moi 1 mot-clé pour chercher une vidéo virale sur Archive.org (Ex: 'funny cats').")
            return response.text.strip()
        except: pass
    return random.choice(ARCHIVE_TOPICS)

def generate_caption_ai(title):
    if USE_AI:
        try:
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(f"Description TikTok pour '{title}'. 3 hashtags.")
            return response.text.strip()
        except: pass
    return f"Regarde ça ! 🔥 #viral #fyp"

# --- RECHERCHE ARCHIVE.ORG ---
def search_archive_org():
    topic = get_ai_topic()
    print(f"📚 Recherche : {topic}")
    try:
        url = "https://archive.org/advancedsearch.php"
        params = {
            "q": f"{topic} AND mediatype:movies AND format:MPEG4",
            "fl[]": "identifier,title",
            "sort[]": "downloads desc",
            "rows": "20",
            "page": "1",
            "output": "json"
        }
        data = requests.get(url, params=params, timeout=10).json()
        if not data.get('response') or not data['response']['docs']: return None
        
        item = random.choice(data['response']['docs'])
        
        # Trouver le fichier MP4
        meta = requests.get(f"https://archive.org/metadata/{item['identifier']}", timeout=10).json()
        for f in meta.get('files', []):
            if f['name'].lower().endswith('.mp4'):
                return {
                    "title": item.get('title', 'Vidéo Virale'),
                    "url": f"https://archive.org/download/{item['identifier']}/{f['name']}",
                    "source": "Archive.org"
                }
    except: return None
    return None

# --- TÉLÉCHARGEMENT ---
def download_file(url):
    print(f"⬇️ DL : {url}")
    try:
        r = requests.get(url, stream=True, timeout=60, headers={"User-Agent": UserAgent().random})
        if r.status_code != 200: return False
        
        with open(FILENAME, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024*1024):
                if chunk: f.write(chunk)
        return os.path.getsize(FILENAME) > 50000
    except: return False

# --- EMAIL ---
def process_email_delivery(video_data):
    if not all([EMAIL_USER, EMAIL_PASS, EMAIL_RECEIVER]): return False
    try:
        msg = EmailMessage()
        msg['Subject'] = f"🎬 {video_data['title']}"
        msg['From'] = EMAIL_USER
        msg['To'] = EMAIL_RECEIVER
        msg.set_content(f"{video_data['caption']}\n\nSource : {video_data['url']}")
        with open(FILENAME, 'rb') as f:
            msg.add_attachment(f.read(), maintype='video', subtype='mp4', filename="short.mp4")
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_USER, EMAIL_PASS)
            smtp.send_message(msg)
        return True
    except: return False

# --- ROUTES ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/run_bot', methods=['POST'])
def run_bot_api():
    try:
        # 1. Recherche & Download
        video_data = search_archive_org()
        if not video_data: video_data = search_archive_org() # Retry
        
        if video_data and download_file(video_data['url']):
            # 2. IA & Email
            video_data['caption'] = generate_caption_ai(video_data['title'])
            email_sent = process_email_delivery(video_data)
            
            status = "succès" if email_sent else "warning"
            msg = "Email envoyé !" if email_sent else "Echec envoi email (Récupère la vidéo ci-dessous)"

            return jsonify({
                "status": status,
                "message": msg,
                "title": video_data['title'],
                "caption": video_data['caption'],
                "video_url": "/get_video_file", # Lien pour lire
                "download_url": "/get_video_file?force=true" # Lien pour télécharger
            })
            
        return jsonify({"status": "error", "message": "Impossible de trouver/télécharger une vidéo."})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/get_video_file')
def get_video_file():
    # Si ?force=true, on force le téléchargement du fichier
    as_attachment = request.args.get('force') == 'true'
    return send_file(FILENAME, mimetype='video/mp4', as_attachment=as_attachment, download_name='viral_video.mp4')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)


