import os
import smtplib
import random
import html
from email.message import EmailMessage
from googleapiclient.discovery import build
import yt_dlp
import google.generativeai as genai

# --- CONFIGURATION ---
API_KEY = os.environ.get('YOUTUBE_API_KEY') 
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
FILENAME = "viral_video.mp4"

# --- CONFIG IA ---
USE_AI = False
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        USE_AI = True
        print("✅ IA Connectée")
    except: pass

FALLBACK_QUERIES = [
    "wolf of wall street motivation shorts",
    "peaky blinders thomas shelby shorts",
    "business mindset advice shorts",
    "david goggins discipline shorts",
    "kaamelott replique drole shorts"
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
            response = model.generate_content(f"Description tiktok courte pour '{title}'. 3 hashtags.")
            return response.text.strip()
        except: pass
    return f"Credit: {channel} 🔥 #viral"

def download_video_vpn(video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"
    print(f"⬇️ Téléchargement via VPN : {url}")
    
    # Configuration standard (Le VPN fait le reste)
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': FILENAME,
        'quiet': True,
        'no_warnings': True
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return os.path.exists(FILENAME)
    except Exception as e:
        print(f"❌ Erreur yt-dlp : {e}")
        return False

def deliver(title, url, caption):
    user = os.environ.get('EMAIL_USER')
    pwd = os.environ.get('EMAIL_PASSWORD')
    rcv = os.environ.get('EMAIL_RECEIVER')
    
    msg = EmailMessage()
    msg['Subject'] = f"🎬 {title}"
    msg['From'] = user
    msg['To'] = rcv
    msg.set_content(f"{caption}\n\nSource: {url}")
    
    with open(FILENAME, 'rb') as f:
        msg.add_attachment(f.read(), maintype='video', subtype='mp4', filename="short.mp4")
        
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(user, pwd)
        smtp.send_message(msg)
    print("✅ Email envoyé !")

# --- EXÉCUTION ---
if __name__ == "__main__":
    if not API_KEY:
        print("❌ Clé API Google manquante")
        exit()

    # 1. Recherche
    youtube = build('youtube', 'v3', developerKey=API_KEY)
    request = youtube.search().list(part="snippet", maxResults=10, q=get_search_query(), type="video", videoDuration="short", order="viewCount")
    response = request.execute()
    
    if response.get('items'):
        # On essaie jusqu'à 3 vidéos
        for item in random.sample(response['items'], min(3, len(response['items']))):
            vid_id = item['id']['videoId']
            title = html.unescape(item['snippet']['title'])
            
            if download_video_vpn(vid_id):
                caption = get_caption(title, item['snippet']['channelTitle'])
                deliver(title, f"https://youtu.be/{vid_id}", caption)
                break
    else:
        print("❌ Aucune vidéo trouvée.")

