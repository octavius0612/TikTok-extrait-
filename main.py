import os
import smtplib
import random
import time
import requests
import xml.etree.ElementTree as ET
from email.message import EmailMessage
from fake_useragent import UserAgent

# --- CONFIGURATION ---
FILENAME = "original_short.mp4"
MAX_SIZE_MB = 24.0

# 1. THEMES DE RECHERCHE (Ce que le bot va chercher dans les RSS)
SEARCH_THEMES = [
    "Wolf of Wall Street shorts vertical edit",
    "OSS 117 replique culte shorts vertical",
    "Peaky Blinders shelby motivation shorts",
    "Kaamelott best of shorts vertical",
    "Suits harvey specter sigma edit shorts",
    "Funny movie clips vertical shorts",
    "War Dogs money scene shorts vertical",
    "Breaking Bad funny moments shorts vertical"
]

# 2. LISTE DE SECOURS (Si le RSS est en panne, on prend ces classiques)
BACKUP_LINKS = [
    "https://www.youtube.com/shorts/tQpM9qH9gqI", # Wolf of wall street
    "https://www.youtube.com/shorts/5s6z3u7F-4A", # Jordan Belfort
    "https://www.youtube.com/shorts/L4dGjE0eJgE"  # Peaky Blinders
]

# 3. INSTANCES INVIDIOUS (Pour le RSS)
RSS_INSTANCES = [
    "https://yewtu.be",
    "https://vid.puffyan.us",
    "https://inv.tux.pizza"
]

# 4. INSTANCES COBALT (Pour le téléchargement HD)
COBALT_INSTANCES = [
    "https://cobalt.xy24.eu/api/json",
    "https://cobalt.wafflehacker.io/api/json",
    "https://api.cobalt.tools/api/json"
]

def get_video_from_rss():
    """Cherche une vidéo via les flux RSS Invidious (Indétectable)."""
    ua = UserAgent()
    query = random.choice(SEARCH_THEMES)
    formatted_query = query.replace(" ", "+")
    
    print(f"📡 Scan RSS pour le thème : '{query}'")

    for instance in RSS_INSTANCES:
        try:
            # URL magique du flux RSS de recherche
            rss_url = f"{instance}/feed/search?q={formatted_query}&sort=relevance"
            
            headers = {'User-Agent': ua.random}
            response = requests.get(rss_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                # Analyse du XML
                root = ET.fromstring(response.content)
                # On cherche les balises 'entry'
                ns = {'yt': 'http://www.youtube.com/xml/schemas/2015'} # Namespace parfois utilisé
                
                entries = root.findall("{http://www.w3.org/2005/Atom}entry")
                
                if not entries:
                    continue

                # On prend une vidéo au hasard parmi les résultats
                entry = random.choice(entries[:5]) # Parmi les 5 premiers
                
                title = entry.find("{http://www.w3.org/2005/Atom}title").text
                video_id = entry.find("{http://www.youtube.com/xml/schemas/2015}videoId").text
                
                real_url = f"https://www.youtube.com/shorts/{video_id}"
                
                print(f"🎯 Trouvé via RSS : {title}")
                return {'title': title, 'url': real_url}
                
        except Exception as e:
            print(f"⚠️ Erreur RSS sur {instance}: {e}")
            continue
    
    print("❌ Echec RSS. Passage au backup.")
    return None

def download_via_cobalt(url):
    """Télécharge la vidéo YouTube proprement."""
    ua = UserAgent()
    
    payload = {
        "url": url,
        "vCodec": "h264",
        "vQuality": "1080", # On demande du 1080p
        "isAudioOnly": False
    }

    for api_url in COBALT_INSTANCES:
        print(f"🛡️ Download via : {api_url}")
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": ua.random
        }
        
        try:
            # 1. Demande du lien
            r = requests.post(api_url, json=payload, headers=headers, timeout=15)
            if r.status_code != 200:
                continue
                
            data = r.json()
            download_link = data.get('url')
            
            if not download_link:
                continue
            
            # 2. Téléchargement fichier
            print("⬇️ Réception du fichier HD...")
            file_resp = requests.get(download_link, stream=True)
            
            with open(FILENAME, 'wb') as f:
                for chunk in file_resp.iter_content(chunk_size=1024*1024):
                    if chunk: f.write(chunk)
            
            if os.path.getsize(FILENAME) > 1000:
                print("✅ Vidéo sauvegardée !")
                return True
                
        except Exception as e:
            print(f"⚠️ Erreur instance : {e}")
            continue

    return False

def send_email(title, url):
    email_user = os.environ.get('EMAIL_USER')
    email_pass = os.environ.get('EMAIL_PASSWORD')
    email_receiver = os.environ.get('EMAIL_RECEIVER')

    if not all([email_user, email_pass, email_receiver]): return
    if not os.path.exists(FILENAME): return

    msg = EmailMessage()
    msg['Subject'] = f'🎬 YouTube Original : {title}'
    msg['From'] = email_user
    msg['To'] = email_receiver
    msg.set_content(f"Voici un short original (YouTube HD).\nLien source : {url}")

    with open(FILENAME, 'rb') as f:
        msg.add_attachment(f.read(), maintype='video', subtype='mp4', filename="viral.mp4")

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(email_user, email_pass)
            smtp.send_message(msg)
        print("✅ Email envoyé !")
    except:
        print("❌ Erreur email.")

if __name__ == "__main__":
    # 1. Essai via RSS (Recherche dynamique)
    video_data = get_video_from_rss()
    
    url_to_download = ""
    title = "Vidéo Backup"
    
    if video_data:
        url_to_download = video_data['url']
        title = video_data['title']
    else:
        # 2. Si RSS vide, on prend un backup
        url_to_download = random.choice(BACKUP_LINKS)
    
    # 3. Téléchargement
    if download_via_cobalt(url_to_download):
        send_email(title, url_to_download)
    else:
        print("❌ Échec total du téléchargement.")
