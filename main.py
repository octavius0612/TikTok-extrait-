import os
import smtplib
import random
import html
import time
import requests
from email.message import EmailMessage
from googleapiclient.discovery import build
from fake_useragent import UserAgent

# --- CONFIGURATION ---
API_KEY = os.environ.get('YOUTUBE_API_KEY') 
FILENAME = "viral_video.mp4"
# Gmail bloque à 25Mo, on se limite à 24Mo pour être sûr
MAX_SIZE_MB = 24.0

QUERIES = [
    "wolf of wall street motivation shorts",
    "peaky blinders sigma rule shorts",
    "business mindset advice shorts",
    "david goggins discipline shorts",
    "kaamelott replique drole shorts",
    "oss 117 scene culte shorts",
    "motivation sport speech shorts"
]

# --- LISTE DES SERVEURS INVIDIOUS (ROBUSTES) ---
INVIDIOUS_INSTANCES = [
    "https://inv.tux.pizza",
    "https://vid.puffyan.us",
    "https://yewtu.be",
    "https://invidious.jing.rocks",
    "https://invidious.projectsegfau.lt",
    "https://invidious.drgns.space"
]

# --- 1. RECHERCHE GOOGLE (Toujours OK) ---
def search_google_api():
    if not API_KEY:
        print("❌ Clé API Google manquante.")
        return None

    query = random.choice(QUERIES)
    print(f"📡 Recherche Google : '{query}'")

    try:
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
        
        print(f"✅ Cible : {title} (ID: {video_id})")
        return {'title': title, 'id': video_id, 'url': f"https://youtu.be/{video_id}"}

    except Exception as e:
        print(f"❌ Erreur API Google : {e}")
        return None

# --- 2. TÉLÉCHARGEMENT DIRECT STREAM (Sans API intermédiaire) ---
def download_direct_stream(video_id):
    print("🛡️ Démarrage du téléchargement Direct Stream...")
    ua = UserAgent()
    
    # On mélange pour la répartition de charge
    random.shuffle(INVIDIOUS_INSTANCES)

    for instance in INVIDIOUS_INSTANCES:
        print(f"   👉 Connexion à : {instance}")
        
        # URL Magique : Force le téléchargement du MP4
        # itag 22 = 720p (HD Light)
        # itag 18 = 360p (SD - Backup si HD échoue)
        itags_to_try = ['22', '18']

        for itag in itags_to_try:
            direct_url = f"{instance}/latest_version?id={video_id}&itag={itag}"
            
            headers = {
                "User-Agent": ua.random,
                "Referer": f"{instance}/watch?v={video_id}"
            }

            try:
                # On lance le stream avec un timeout strict
                r = requests.get(direct_url, headers=headers, stream=True, timeout=15)
                
                if r.status_code != 200:
                    continue
                    
                content_type = r.headers.get('Content-Type', '')
                if 'video' not in content_type:
                    continue

                print(f"      ⬇️ Flux vidéo détecté (itag {itag}) ! Réception...")
                
                with open(FILENAME, 'wb') as f:
                    downloaded = 0
                    for chunk in r.iter_content(chunk_size=1024*1024):
                        if chunk: 
                            f.write(chunk)
                            downloaded += len(chunk)
                            # Sécurité Gmail (24MB max)
                            if downloaded > 24 * 1024 * 1024:
                                print("      ⚠️ Fichier trop gros. Arrêt.")
                                break
                
                # Vérification finale
                size_mb = os.path.getsize(FILENAME) / (1024 * 1024)
                if size_mb > 0.1: # Plus de 100KB
                    print(f"✅ SUCCÈS ! Vidéo récupérée ({size_mb:.2f} MB)")
                    return True

            except Exception as e:
                continue
            
    print("❌ Tous les serveurs Invidious ont échoué.")
    return False

# --- 3. ENVOI ---
def send_email(video_data):
    email_user = os.environ.get('EMAIL_USER')
    email_pass = os.environ.get('EMAIL_PASSWORD')
    email_receiver = os.environ.get('EMAIL_RECEIVER')

    if not all([email_user, email_pass, email_receiver]): return

    if not os.path.exists(FILENAME) or os.path.getsize(FILENAME) == 0:
        return

    msg = EmailMessage()
    msg['Subject'] = f"🎬 SHORT : {video_data['title']}"
    msg['From'] = email_user
    msg['To'] = email_receiver
    msg.set_content(f"Source : {video_data['url']}")

    with open(FILENAME, 'rb') as f:
        msg.add_attachment(f.read(), maintype='video', subtype='mp4', filename="short.mp4")

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(email_user, email_pass)
        smtp.send_message(msg)
    print("✅ Email envoyé !")

if __name__ == "__main__":
    video_info = search_google_api()
    
    if video_info:
        success = download_direct_stream(video_info['id'])
        if success:
            send_email(video_info)

