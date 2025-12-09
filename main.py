import os
import smtplib
import random
import html
import requests
from email.message import EmailMessage
from googleapiclient.discovery import build
from fake_useragent import UserAgent

# --- CONFIGURATION ---
API_KEY = os.environ.get('YOUTUBE_API_KEY') 
FILENAME = "viral_video.mp4"
MAX_SIZE_MB = 24.0

# Thèmes de recherche
QUERIES = [
    "wolf of wall street motivation shorts",
    "peaky blinders thomas shelby shorts",
    "business success advice shorts",
    "david goggins discipline shorts",
    "kaamelott replique drole shorts",
    "oss 117 scene culte shorts",
    "motivation sport speech shorts"
]

# --- INSTANCES INVIDIOUS (API MODE) ---
INSTANCES = [
    "https://inv.tux.pizza",
    "https://vid.puffyan.us",
    "https://yewtu.be",
    "https://invidious.jing.rocks",
    "https://invidious.projectsegfau.lt",
    "https://invidious.drgns.space"
]

# --- COFFRE DE SECOURS (Si le téléchargement échoue, on prend ça) ---
# Ce sont des liens directs vers des fichiers MP4 hébergés sur des CDN publics
BACKUP_VIDEOS = [
    {"title": "Backup - Wolf of Wall Street", "url": "https://cdn.discordapp.com/attachments/1063836773223530557/111000000000000000/wolf.mp4"}, # Fictif pour l'exemple, le bot essaiera de le télécharger
    # NOTE: Si le téléchargement échoue, tu recevras un mail d'erreur mais propre.
    # Pour que le backup marche à 100%, il faut des liens directs mp4. 
    # Pour l'instant, le script va se concentrer sur la méthode Invidious.
]

# --- 1. RECHERCHE GOOGLE ---
def search_google_api():
    if not API_KEY:
        print("❌ Clé API Google manquante.")
        return None

    query = random.choice(QUERIES)
    print(f"📡 Recherche Google : '{query}'")

    try:
        youtube = build('youtube', 'v3', developerKey=API_KEY)
        request = youtube.search().list(
            part="snippet", maxResults=15, q=query, type="video",
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

# --- 2. TÉLÉCHARGEMENT CHIRURGICAL (API JSON) ---
def download_via_invidious_api(video_id):
    print("🛡️ Démarrage méthode API JSON...")
    ua = UserAgent()
    
    # Mélange des serveurs
    random.shuffle(INSTANCES)

    for instance in INSTANCES:
        print(f"   👉 API Call sur : {instance}")
        
        # On demande les métadonnées en JSON (pas le fichier vidéo direct)
        api_url = f"{instance}/api/v1/videos/{video_id}"
        
        try:
            r = requests.get(api_url, timeout=10)
            if r.status_code != 200:
                print(f"      ⚠️ API Error {r.status_code}")
                continue
            
            data = r.json()
            
            # On cherche le format MP4 720p ou 360p
            # formatStreams contient les liens directs googlevideo
            streams = data.get('formatStreams', [])
            
            target_url = None
            
            # Priorité HD (720p)
            for s in streams:
                if s.get('container') == 'mp4' and '720p' in s.get('resolution', ''):
                    target_url = s.get('url')
                    print("      ✨ Lien HD trouvé !")
                    break
            
            # Fallback SD (360p)
            if not target_url:
                for s in streams:
                    if s.get('container') == 'mp4' and '360p' in s.get('resolution', ''):
                        target_url = s.get('url')
                        print("      ⚠️ Lien SD trouvé (pas de HD).")
                        break
            
            if not target_url:
                print("      ❌ Aucun flux MP4 valide trouvé.")
                continue

            # TÉLÉCHARGEMENT DU LIEN MAGIQUE
            print("      ⬇️ Téléchargement du flux final...")
            headers = {"User-Agent": ua.random}
            
            file_resp = requests.get(target_url, headers=headers, stream=True, timeout=20)
            
            if file_resp.status_code == 200:
                with open(FILENAME, 'wb') as f:
                    downloaded = 0
                    for chunk in file_resp.iter_content(chunk_size=1024*1024):
                        if chunk: 
                            f.write(chunk)
                            downloaded += len(chunk)
                            if downloaded > 24 * 1024 * 1024:
                                print("      ⚠️ Fichier trop gros. Arrêt.")
                                return False
                
                if os.path.getsize(FILENAME) > 50000: # >50KB
                    print(f"✅ SUCCÈS ! Vidéo récupérée via {instance}")
                    return True
            
        except Exception as e:
            print(f"      ❌ Erreur : {e}")
            continue

    print("❌ Tous les serveurs API ont échoué.")
    return False

# --- 3. ENVOI ---
def send_email(video_data):
    email_user = os.environ.get('EMAIL_USER')
    email_pass = os.environ.get('EMAIL_PASSWORD')
    email_receiver = os.environ.get('EMAIL_RECEIVER')

    if not all([email_user, email_pass, email_receiver]): return

    if not os.path.exists(FILENAME) or os.path.getsize(FILENAME) == 0:
        print("❌ Pas de fichier à envoyer.")
        return

    msg = EmailMessage()
    msg['Subject'] = f"🎬 {video_data['title']}"
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
    # 1. Recherche
    video_info = search_google_api()
    
    if video_info:
        # 2. Téléchargement API
        success = download_via_invidious_api(video_info['id'])
        
        if success:
            send_email(video_info)
        else:
            print("❌ Échec total du téléchargement.")
