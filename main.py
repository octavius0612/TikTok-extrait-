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

QUERIES = [
    "wolf of wall street motivation shorts",
    "peaky blinders sigma rule shorts",
    "business mindset advice shorts",
    "david goggins discipline shorts",
    "kaamelott replique drole shorts",
    "oss 117 scene culte shorts",
    "motivation sport speech shorts"
]

# --- LISTE DES MIROIRS DE L'OMBRE (Shadow Mirrors) ---
# Ce sont des instances Cobalt "Tier 2" moins connues et donc moins bloquées.
# Elles agissent comme des proxys résidentiels pour nous.
SHADOW_MIRRORS = [
    "https://cobalt.rive.cafe/api/json",      # Mirror très rapide
    "https://cobalt.nicetry.me/api/json",     # Souvent non blacklisté
    "https://cobalt.ghost.net.in/api/json",   # Mirror Indien (bonne rotation IP)
    "https://api.wkr.fr/api/json",            # Mirror Français 🇫🇷
    "https://cobalt.ducks.party/api/json",    # Mirror communautaire
    "https://cobalt.kwiatekmiki.pl/api/json", # Pologne
    "https://cobalt.q11.de/api/json"          # Allemagne
]

# --- 1. RECHERCHE LÉGITIME (API GOOGLE) ---
def search_google_api():
    if not API_KEY:
        print("❌ Clé API Google manquante dans les Secrets.")
        return None

    query = random.choice(QUERIES)
    print(f"📡 Recherche Officielle : '{query}'")

    try:
        youtube = build('youtube', 'v3', developerKey=API_KEY)
        
        request = youtube.search().list(
            part="snippet",
            maxResults=15,
            q=query,
            type="video",
            videoDuration="short",
            order="viewCount", # On veut du viral
            relevanceLanguage="fr"
        )
        response = request.execute()

        if not response['items']: return None

        # Choix aléatoire pondéré (pour ne pas prendre toujours le 1er)
        video = random.choice(response['items'])
        
        title = html.unescape(video['snippet']['title'])
        video_id = video['id']['videoId']
        
        # On construit l'url standard
        url = f"https://www.youtube.com/watch?v={video_id}"
        
        print(f"✅ Cible trouvée : {title}")
        print(f"🔗 Lien : {url}")
        
        return {'title': title, 'url': url}

    except Exception as e:
        print(f"❌ Erreur API Google : {e}")
        return None

# --- 2. TÉLÉCHARGEMENT VIA MIROIRS ROTATIFS ---
def download_via_shadow_mirrors(url):
    print("🛡️ Démarrage du protocole Miroirs...")
    ua = UserAgent()
    
    # On mélange les miroirs pour ne pas être prévisible
    random.shuffle(SHADOW_MIRRORS)

    for mirror in SHADOW_MIRRORS:
        print(f"   👉 Tentative sur : {mirror}")
        
        # Headers pour ressembler à un utilisateur n8n/Twin
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": ua.random,
            "Origin": mirror.replace("/api/json", ""), # On fait croire qu'on vient du site
            "Referer": mirror.replace("/api/json", "")
        }
        
        payload = {
            "url": url,
            "vCodec": "h264",
            "vQuality": "1080", # Qualité Max
            "isAudioOnly": False,
            "filenamePattern": "basic"
        }

        try:
            # 1. Demande de traitement au miroir
            r = requests.post(mirror, json=payload, headers=headers, timeout=15)
            
            if r.status_code != 200:
                print(f"      ⚠️ Erreur HTTP {r.status_code}")
                continue

            try:
                data = r.json()
            except:
                continue

            download_link = data.get('url')
            
            if not download_link:
                # Parfois le miroir renvoie un status "error" ou "processing"
                if 'text' in data: print(f"      ⚠️ Info Miroir: {data['text']}")
                continue
            
            # 2. Téléchargement du fichier final
            print("      ⬇️ Lien généré ! Téléchargement...")
            
            # On télécharge le fichier depuis l'URL générée par le miroir
            # C'est souvent un lien direct vers Google Video ou un CDN intermédiaire
            file_resp = requests.get(download_link, stream=True, timeout=30)
            
            with open(FILENAME, 'wb') as f:
                size = 0
                for chunk in file_resp.iter_content(chunk_size=1024*1024):
                    if chunk: 
                        f.write(chunk)
                        size += len(chunk)
            
            # Validation du fichier
            file_size_mb = os.path.getsize(FILENAME) / (1024 * 1024)
            if file_size_mb > 0.05: # Plus de 50KB
                print(f"✅ SUCCÈS via {mirror} ! ({file_size_mb:.2f} MB)")
                return True
            else:
                print("      ⚠️ Fichier vide reçu.")

        except Exception as e:
            print(f"      ❌ Timeout ou erreur connexion : {e}")
            continue
            
    print("❌ Tous les miroirs ont échoué.")
    return False

# --- 3. ENVOI ---
def send_email(video_data):
    email_user = os.environ.get('EMAIL_USER')
    email_pass = os.environ.get('EMAIL_PASSWORD')
    email_receiver = os.environ.get('EMAIL_RECEIVER')

    if not all([email_user, email_pass, email_receiver]): return

    # Vérif taille max pour Gmail (25MB)
    if os.path.getsize(FILENAME) > 24.5 * 1024 * 1024:
        print("⚠️ Fichier trop lourd pour Gmail. Annulation envoi.")
        return

    msg = EmailMessage()
    msg['Subject'] = f"🔥 PRÊT : {video_data['title']}"
    msg['From'] = email_user
    msg['To'] = email_receiver
    
    body = f"Vidéo téléchargée en haute qualité.\nSource : {video_data['url']}"
    msg.set_content(body)

    with open(FILENAME, 'rb') as f:
        msg.add_attachment(f.read(), maintype='video', subtype='mp4', filename="viral.mp4")

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(email_user, email_pass)
        smtp.send_message(msg)
    print("✅ Email envoyé !")

if __name__ == "__main__":
    # Étape 1 : Trouver la pépite (API Google)
    video_info = search_google_api()
    
    if video_info:
        # Étape 2 : Passer par les miroirs de l'ombre
        success = download_via_shadow_mirrors(video_info['url'])
        
        if success:
            # Étape 3 : Livrer
            send_email(video_info)

