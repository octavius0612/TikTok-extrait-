import os
import smtplib
import random
import html
import requests
from email.message import EmailMessage
from googleapiclient.discovery import build # La librairie officielle Google

# --- CONFIGURATION ---
# Mets ta clé API Google ici (ou dans les Secrets GitHub sous YOUTUBE_API_KEY)
# C'est la seule chose dont tu as besoin pour ne plus être bloqué.
API_KEY = os.environ.get('YOUTUBE_API_KEY') 

FILENAME = "viral_masterpiece.mp4"
MAX_SIZE_MB = 24.0

# Tes thèmes de recherche
QUERIES = [
    "motivation discipline speech",
    "sigma male grindset",
    "business success advice",
    "peaky blinders thomas shelby",
    "wolf of wall street sales",
    "kaamelott replique culte",
    "oss 117 drôle"
]

# --- FONCTION 1 : RECHERCHE VIA API OFFICIELLE (Comme n8n) ---
def search_viral_video_official():
    if not API_KEY:
        print("❌ Erreur : Il manque la clé API YouTube (YOUTUBE_API_KEY).")
        return None

    query = random.choice(QUERIES)
    print(f"📡 Appel API YouTube Officielle pour : '{query}'")

    try:
        # Connexion officielle à Google
        youtube = build('youtube', 'v3', developerKey=API_KEY)

        # La requête précise (Shorts, triés par vues, haute pertinence)
        request = youtube.search().list(
            part="snippet",
            maxResults=5,          # On en prend 5 pour avoir le choix
            q=query,
            type="video",
            videoDuration="short", # Filtre Shorts natif
            order="viewCount",     # Les plus virales d'abord
            relevanceLanguage="fr" # Priorité au contenu FR/Compréhensible
        )
        
        response = request.execute()

        # On prend un résultat au hasard parmi le Top 5 pour varier
        if not response['items']:
            print("⚠️ Aucun résultat trouvé par l'API.")
            return None

        video = random.choice(response['items'])
        
        video_id = video['id']['videoId']
        title = html.unescape(video['snippet']['title'])
        channel = video['snippet']['channelTitle']
        
        # Lien propre
        video_url = f"https://www.youtube.com/shorts/{video_id}"
        
        print(f"✅ Trouvé (Légitime) : {title} par {channel}")
        print(f"🔗 Lien : {video_url}")
        
        return {'title': title, 'url': video_url, 'channel': channel}

    except Exception as e:
        print(f"❌ Erreur API Google : {e}")
        return None

# --- FONCTION 2 : TÉLÉCHARGEMENT VIA COBALT (Qualité Max) ---
def download_clean_video(url):
    # Liste de serveurs robustes
    cobalt_servers = [
        "https://api.cobalt.tools/api/json",
        "https://cobalt.kwiatekmiki.pl/api/json",
        "https://cobalt.xy24.eu/api/json"
    ]
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    payload = {
        "url": url,
        "vCodec": "h264",
        "vQuality": "1080", # On force la HD
        "isAudioOnly": False
    }

    for server in cobalt_servers:
        print(f"🛡️ Téléchargement via : {server}")
        try:
            r = requests.post(server, json=payload, headers=headers, timeout=20)
            
            if r.status_code == 200:
                data = r.json()
                dl_link = data.get('url')
                
                if dl_link:
                    print("⬇️ Réception du fichier...")
                    file_resp = requests.get(dl_link, stream=True)
                    
                    with open(FILENAME, 'wb') as f:
                        for chunk in file_resp.iter_content(chunk_size=1024*1024):
                            if chunk: f.write(chunk)
                    
                    if os.path.getsize(FILENAME) > 5000:
                        return True
        except:
            continue
            
    print("❌ Impossible de télécharger la vidéo.")
    return False

# --- FONCTION 3 : LIVRAISON ---
def deliver_content(video_data):
    email_user = os.environ.get('EMAIL_USER')
    email_pass = os.environ.get('EMAIL_PASSWORD')
    email_receiver = os.environ.get('EMAIL_RECEIVER')

    if not all([email_user, email_pass, email_receiver]):
        print("❌ Secrets Email manquants.")
        return

    msg = EmailMessage()
    msg['Subject'] = f"🚀 PRÊT À POSTER : {video_data['title']}"
    msg['From'] = email_user
    msg['To'] = email_receiver
    
    body = f"""
    Salut,
    
    L'API Google a détecté ce contenu viral ({video_data['channel']}).
    Le fichier joint est propre (pas de filigrane), HD 1080p.
    
    1. Télécharge la pièce jointe sur ton téléphone.
    2. Ouvre TikTok / YouTube Shorts.
    3. Ajoute une musique tendance (volume 5%).
    4. Publie !
    
    Source originale : {video_data['url']}
    """
    msg.set_content(body)

    with open(FILENAME, 'rb') as f:
        msg.add_attachment(f.read(), maintype='video', subtype='mp4', filename="viral_short.mp4")

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(email_user, email_pass)
            smtp.send_message(msg)
        print("✅ Email envoyé avec succès !")
    except Exception as e:
        print(f"❌ Erreur envoi : {e}")

if __name__ == "__main__":
    # 1. On cherche proprement (Comme n8n)
    video_info = search_viral_video_official()
    
    if video_info:
        # 2. On télécharge proprement
        success = download_clean_video(video_info['url'])
        
        if success:
            # 3. On livre
            deliver_content(video_info)
    else:
        print("❌ Aucune vidéo trouvée ou erreur API.")

