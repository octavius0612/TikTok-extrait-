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
MAX_SIZE_MB = 24.0

# Tes thèmes de recherche (Contenu YouTube pour TikTok)
QUERIES = [
    "wolf of wall street motivation shorts",
    "peaky blinders thomas shelby shorts",
    "business mindset advice shorts",
    "david goggins discipline shorts",
    "kaamelott replique drole shorts",
    "oss 117 scene culte shorts",
    "motivation sport speech shorts"
]

# --- INSTANCES PIPED (Alternative robuste) ---
# Ces serveurs utilisent une infrastructure différente d'Invidious/Cobalt
PIPED_INSTANCES = [
    "https://pipedapi.kavin.rocks",  # Instance principale
    "https://api.piped.otton.uk",    # UK
    "https://pipedapi.moomoo.me",    # Alternative
    "https://pipedapi.smnz.de",      # Allemagne
    "https://api.piped.privacy.com.de"
]

# --- 1. RECHERCHE LÉGITIME (API GOOGLE) ---
def search_google_api():
    if not API_KEY:
        print("❌ Clé API Google manquante.")
        return None

    query = random.choice(QUERIES)
    print(f"📡 Recherche YouTube Officielle : '{query}'")

    try:
        youtube = build('youtube', 'v3', developerKey=API_KEY)
        request = youtube.search().list(
            part="snippet",
            maxResults=20, # Large choix
            q=query,
            type="video",
            videoDuration="short", # Shorts uniquement
            order="viewCount",     # Les plus virales
            relevanceLanguage="fr"
        )
        response = request.execute()

        if not response['items']: return None

        video = random.choice(response['items'])
        title = html.unescape(video['snippet']['title'])
        video_id = video['id']['videoId']
        
        print(f"✅ Cible trouvée : {title}")
        print(f"🔗 ID : {video_id}")
        
        return {'title': title, 'id': video_id, 'url': f"https://youtu.be/{video_id}"}

    except Exception as e:
        print(f"❌ Erreur API Google : {e}")
        return None

# --- 2. TÉLÉCHARGEMENT VIA PIPED (Cloudflare Routing) ---
def download_via_piped(video_id):
    print("🛡️ Démarrage téléchargement Piped...")
    ua = UserAgent()
    
    random.shuffle(PIPED_INSTANCES)

    for instance in PIPED_INSTANCES:
        print(f"   👉 Connexion à : {instance}")
        
        # Endpoint pour obtenir les flux vidéo
        api_url = f"{instance}/streams/{video_id}"
        
        try:
            r = requests.get(api_url, timeout=15)
            if r.status_code != 200:
                print(f"      ⚠️ API Error {r.status_code}")
                continue
            
            data = r.json()
            video_streams = data.get('videoStreams', [])
            
            # On cherche un flux MP4 en 720p ou 1080p qui contient AUSSI l'audio
            # (Piped sépare souvent audio et vidéo, on cherche 'videoOnly': False)
            target_url = None
            
            # 1. Chercher flux combiné (rare sur Piped mais possible)
            for s in video_streams:
                if s.get('videoOnly') == False and s.get('format') == 'MPEG-4':
                    target_url = s.get('url')
                    print("      ✨ Flux combiné trouvé !")
                    break
            
            # 2. Si pas de combiné, on prend le flux vidéo seul (tant pis pour l'audio pour ce test, 
            # ou on prend un format compatible. GitHub Actions ne peut pas fusionner audio/vidéo facilement sans FFmpeg complexe)
            # ASTUCE : Pour TikTok, on veut surtout l'image. Mais essayons de trouver le meilleur compromis.
            
            # Note : Sur les Shorts, Piped renvoie souvent un flux HLS (.m3u8).
            hls_url = data.get('hls')
            if hls_url and not target_url:
                 # Le HLS contient tout, mais il faut le télécharger via requests stream... complexe.
                 pass

            # PLAN B : Utiliser l'API de proxy Piped pour forcer le MP4
            if not target_url:
                # On tente de trouver le stream vidéo '1080p'
                for s in video_streams:
                    if s.get('quality') == '1080p' and s.get('format') == 'MPEG-4':
                        target_url = s.get('url') # Ce sera vidéo seulement souvent
                        break
            
            if not target_url:
                print("      ❌ Pas de flux MP4 compatible.")
                continue

            print("      ⬇️ Téléchargement du flux...")
            
            # Téléchargement
            headers = {"User-Agent": ua.random}
            file_resp = requests.get(target_url, headers=headers, stream=True, timeout=30)
            
            if file_resp.status_code == 200:
                with open(FILENAME, 'wb') as f:
                    downloaded = 0
                    for chunk in file_resp.iter_content(chunk_size=1024*1024):
                        if chunk: 
                            f.write(chunk)
                            downloaded += len(chunk)
                            if downloaded > 24 * 1024 * 1024:
                                break
                
                if os.path.getsize(FILENAME) > 5000:
                    print(f"✅ SUCCÈS via {instance} !")
                    return True

        except Exception as e:
            print(f"      ❌ Erreur : {e}")
            continue

    print("❌ Tous les serveurs Piped ont échoué.")
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
    msg.set_content(f"Source YouTube : {video_data['url']}")

    with open(FILENAME, 'rb') as f:
        msg.add_attachment(f.read(), maintype='video', subtype='mp4', filename="short.mp4")

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(email_user, email_pass)
        smtp.send_message(msg)
    print("✅ Email envoyé !")

if __name__ == "__main__":
    video_info = search_google_api()
    if video_info:
        success = download_via_piped(video_info['id'])
        if success:
            send_email(video_info)

