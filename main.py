import os
import smtplib
import random
import html
import time
import requests
from email.message import EmailMessage
from googleapiclient.discovery import build
from fake_useragent import UserAgent
import google.generativeai as genai

# --- CONFIGURATION ---
API_KEY = os.environ.get('YOUTUBE_API_KEY') 
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
FILENAME = "viral_video.mp4"

# --- IA SETUP ---
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

# --- INSTANCES INVIDIOUS (Miroirs YouTube) ---
# Ces serveurs font l'intermédiaire. On va leur demander le lien de streaming.
INVIDIOUS_INSTANCES = [
    "https://inv.tux.pizza",
    "https://vid.puffyan.us",
    "https://yewtu.be",
    "https://invidious.jing.rocks",
    "https://invidious.projectsegfau.lt",
    "https://invidious.drgns.space",
    "https://iv.ggtyler.dev",
    "https://invidious.lunar.icu"
]

# --- COFFRE DE SECOURS (Plan Z - 100% Sûr) ---
EMERGENCY_VAULT = [
    {"title": "Wolf of Wall Street", "url": "https://ia801602.us.archive.org/11/items/wolf-of-wall-street-sell-me-this-pen/Wolf_of_Wall_Street_Sell_Me_This_Pen.mp4", "caption": "Sell me this pen! 🖊️ #viral"},
    {"title": "OSS 117", "url": "https://ia902606.us.archive.org/3/items/oss-117-le-caire-nid-d-espions-bambino/OSS%20117%20Le%20Caire%20nid%20d%27espions%20-%20Bambino.mp4", "caption": "Habile ! 😎 #oss117"},
]

# --- 1. FONCTIONS IA ---
def get_search_query():
    if USE_AI:
        try:
            model = genai.GenerativeModel('gemini-2.0-flash')
            prompt = "Donne-moi 1 idée de recherche youtube shorts viral (Business/Humour). Juste les mots clés."
            response = model.generate_content(prompt)
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

# --- 2. TÉLÉCHARGEMENT HUMANISÉ (INVIDIOUS API) ---
def download_via_invidious(video_id):
    print(f"🕵️ Tentative Invidious (Humanized) pour ID: {video_id}")
    ua = UserAgent()
    
    # En-têtes complets pour ressembler à un vrai Chrome
    browser_headers = {
        "User-Agent": ua.chrome,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1"
    }

    random.shuffle(INVIDIOUS_INSTANCES)

    for instance in INVIDIOUS_INSTANCES:
        try:
            print(f"   👉 Connexion API: {instance}")
            # On utilise l'API pour obtenir le lien direct googlevideo
            api_url = f"{instance}/api/v1/videos/{video_id}"
            
            # 1. Récupération des infos
            r = requests.get(api_url, headers=browser_headers, timeout=10)
            if r.status_code != 200: continue
            
            data = r.json()
            
            # 2. Recherche du meilleur flux MP4 (avec audio)
            target_url = None
            # On cherche d'abord en 720p
            for s in data.get('formatStreams', []):
                if s['container'] == 'mp4' and '720p' in s['resolution']:
                    target_url = s['url']
                    break
            # Sinon n'importe quel MP4
            if not target_url:
                for s in data.get('formatStreams', []):
                    if s['container'] == 'mp4':
                        target_url = s['url']
                        break
            
            if not target_url: continue

            # 3. Téléchargement du fichier final
            print("      ⬇️ Téléchargement du flux...")
            video_r = requests.get(target_url, headers=browser_headers, stream=True, timeout=60)
            
            if video_r.status_code == 200:
                with open(FILENAME, 'wb') as f:
                    for chunk in video_r.iter_content(chunk_size=1024*1024):
                        if chunk: f.write(chunk)
                
                if os.path.getsize(FILENAME) > 50000:
                    print("✅ SUCCÈS via Invidious !")
                    return True

        except Exception as e:
            print(f"      ❌ Erreur: {e}")
            continue
            
    return False

# --- 3. PLAN B : DAILYMOTION (Moins protégé) ---
def try_dailymotion(query):
    print("⚠️ YouTube bloqué. Bascule Dailymotion...")
    try:
        url = f"https://api.dailymotion.com/videos?fields=id,title,owner.screenname&shorter_than=120&sort=relevance&search={query}&limit=5"
        r = requests.get(url, timeout=10)
        data = r.json()
        if not data.get('list'): return None
        
        video = random.choice(data['list'])
        
        # Hack pour avoir le lien MP4
        meta = requests.get(f"https://www.dailymotion.com/player/metadata/video/{video['id']}", timeout=10).json()
        dl_link = meta['qualities']['auto'][0]['url']
        
        # Téléchargement
        dl = requests.get(dl_link, stream=True)
        with open(FILENAME, 'wb') as f:
            for chunk in dl.iter_content(chunk_size=1024*1024):
                if chunk: f.write(chunk)
                
        return {"title": video['title'], "url": f"https://dailymotion.com/video/{video['id']}", "caption": get_caption(video['title'], video['owner.screenname']), "source": "Dailymotion"}
    except: return None

# --- ENVOI ---
def deliver(data):
    user = os.environ.get('EMAIL_USER')
    pwd = os.environ.get('EMAIL_PASSWORD')
    rcv = os.environ.get('EMAIL_RECEIVER')
    
    if not all([user, pwd, rcv]): return

    msg = EmailMessage()
    msg['Subject'] = f"🎬 {data['source']} : {data['title']}"
    msg['From'] = user
    msg['To'] = rcv
    msg.set_content(f"{data['caption']}\n\nSource: {data['url']}")
    
    with open(FILENAME, 'rb') as f:
        msg.add_attachment(f.read(), maintype='video', subtype='mp4', filename="short.mp4")
        
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(user, pwd)
        smtp.send_message(msg)
    print("✅ Email envoyé !")

# --- MAIN LOOP ---
if __name__ == "__main__":
    if not API_KEY: exit()

    query = get_search_query()
    
    # 1. Recherche YouTube
    youtube = build('youtube', 'v3', developerKey=API_KEY)
    request = youtube.search().list(part="snippet", maxResults=5, q=query, type="video", videoDuration="short", order="viewCount")
    response = request.execute()
    
    success = False
    final_data = {}

    # Tentative YouTube (Invidious Humanisé)
    if response.get('items'):
        for item in random.sample(response['items'], min(2, len(response['items']))):
            vid_id = item['id']['videoId']
            title = html.unescape(item['snippet']['title'])
            
            if download_via_invidious(vid_id):
                success = True
                final_data = {
                    "title": title,
                    "url": f"https://youtu.be/{vid_id}",
                    "caption": get_caption(title, item['snippet']['channelTitle']),
                    "source": "YouTube"
                }
                break
    
    # Tentative Dailymotion (Si Invidious échoue)
    if not success:
        res_dm = try_dailymotion(query)
        if res_dm:
            success = True
            final_data = res_dm

    # Tentative Coffre-Fort (Dernier recours)
    if not success:
        print("🚨 MODE URGENCE ACTIVÉ")
        backup = random.choice(EMERGENCY_VAULT)
        r = requests.get(backup['url'], stream=True)
        with open(FILENAME, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024*1024):
                if chunk: f.write(chunk)
        
        success = True
        final_data = {
            "title": backup['title'],
            "url": backup['url'],
            "caption": backup['caption'],
            "source": "COFFRE DE SECOURS"
        }

    if success:
        deliver(final_data)
    else:
        print("❌ Échec critique.")


