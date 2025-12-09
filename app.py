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

# --- COFFRE DE SECOURS (PLAN Z) ---
EMERGENCY_VAULT = [
    {"title": "Wolf of Wall Street - Sell me this pen", "url": "https://ia801602.us.archive.org/11/items/wolf-of-wall-street-sell-me-this-pen/Wolf_of_Wall_Street_Sell_Me_This_Pen.mp4", "caption": "Sell me this pen! 🖊️ #viral"},
    {"title": "OSS 117 Rire", "url": "https://ia902606.us.archive.org/3/items/oss-117-le-caire-nid-d-espions-bambino/OSS%20117%20Le%20Caire%20nid%20d%27espions%20-%20Bambino.mp4", "caption": "Habile ! 😎 #oss117"},
]

# --- 1. GÉNÉRATEUR DE PROXIES GRATUITS ---
def get_free_proxies():
    """Récupère une liste de proxies publics (HTTP/HTTPS)"""
    print("🌍 Récupération de proxies gratuits...")
    proxies = []
    sources = [
        "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=3000&country=all&ssl=all&anonymity=all",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    ]
    
    for source in sources:
        try:
            r = requests.get(source, timeout=5)
            if r.status_code == 200:
                lines = r.text.splitlines()
                # On en prend 20 au hasard pour ne pas tester toujours les mêmes
                proxies.extend(random.sample(lines, min(len(lines), 20)))
        except: pass
    
    print(f"🌍 {len(proxies)} Proxies récupérés.")
    return proxies

# --- IA ---
def get_search_query():
    if USE_AI:
        try:
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content("Donne-moi 1 idée de recherche youtube shorts viral (Business/Motivation). Juste les mots clés.")
            return response.text.strip()
        except: pass
    return random.choice(FALLBACK_QUERIES)

def get_caption(title, channel):
    if USE_AI:
        try:
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(f"Description tiktok courte pour '{title}'. 3 hashtags.")
            return response.text.strip()
        except: pass
    return f"Credit: {channel} 🔥 #viral"

# --- TÉLÉCHARGEMENT AVEC ROTATION ---
def download_secure_rotation(video_id):
    """Essaie de télécharger via Invidious en changeant d'IP à chaque échec"""
    
    invidious_servers = [
        "https://inv.tux.pizza",
        "https://yewtu.be",
        "https://vid.puffyan.us",
        "https://invidious.jing.rocks"
    ]
    
    # 1. On récupère les proxies
    proxy_list = get_free_proxies()
    # On ajoute "None" au début pour tester sans proxy d'abord
    proxy_configs = [None] + [{"http": f"http://{p}", "https": f"http://{p}"} for p in proxy_list]

    for server in invidious_servers:
        direct_url = f"{server}/latest_version?id={video_id}&itag=22"
        print(f"🎯 Cible : {server}")
        
        # On mitraille avec les proxies
        for proxy in proxy_configs:
            try:
                msg = "Direct" if not proxy else "Proxy"
                # print(f"   Trying {msg}...") # Décommenter pour debug
                
                headers = {"User-Agent": UserAgent().random}
                
                # Timeout court (5s) pour la connexion, long pour le download
                r = requests.get(direct_url, headers=headers, stream=True, proxies=proxy, timeout=5)
                
                if r.status_code == 200 and 'video' in r.headers.get('Content-Type', ''):
                    print(f"   ✅ CONNEXION RÉUSSIE ({msg}) ! Téléchargement...")
                    
                    with open(FILENAME, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=1024*1024):
                            if chunk: f.write(chunk)
                    
                    if os.path.getsize(FILENAME) > 50000:
                        return True
            except:
                continue # Proxy mort, au suivant

    return False

# --- ROUTES ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/run_bot', methods=['POST'])
def run_bot_api():
    if not API_KEY: return jsonify({"status": "error", "message": "Clé API manquante"})

    try:
        # Recherche
        youtube = build('youtube', 'v3', developerKey=API_KEY)
        request = youtube.search().list(part="snippet", maxResults=5, q=get_search_query(), type="video", videoDuration="short", order="viewCount")
        response = request.execute()
        
        success = False
        final_data = {}

        if response.get('items'):
            for item in random.sample(response['items'], min(2, len(response['items']))):
                vid_id = item['id']['videoId']
                title = html.unescape(item['snippet']['title'])
                
                # TENTATIVE DOWNLOAD (Rotation Proxy)
                if download_secure_rotation(vid_id):
                    success = True
                    final_data = {
                        "title": title,
                        "url": f"https://youtu.be/{vid_id}",
                        "caption": get_caption(title, item['snippet']['channelTitle'])
                    }
                    break
        
        # PLAN DE SECOURS (Si même les proxies gratuits sont trop lents)
        if not success:
            print("⚠️ ÉCHEC TOTAL. OUVERTURE DU COFFRE D'URGENCE.")
            backup = random.choice(EMERGENCY_VAULT)
            
            # Téléchargement direct (Archive.org ne bloque pas)
            try:
                r = requests.get(backup['url'], stream=True, timeout=30)
                with open(FILENAME, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=1024*1024):
                        if chunk: f.write(chunk)
                
                success = True
                final_data = {
                    "title": f"⚠️ SECOURS : {backup['title']}",
                    "url": backup['url'],
                    "caption": backup['caption']
                }
            except: pass

        if success:
            deliver(final_data)
            return jsonify({
                "status": "success", 
                "title": final_data['title'], 
                "caption": final_data['caption'], 
                "video_url": "/get_video_file",
                "ai_used": USE_AI
            })
        
        return jsonify({"status": "error", "message": "Impossible de télécharger."})

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


