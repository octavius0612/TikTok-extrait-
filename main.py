import os
import smtplib
import random
import time
import requests
from email.message import EmailMessage
import yt_dlp
from huggingface_hub import InferenceClient

# --- CONFIGURATION ---
FILENAME = "viral_video.mp4"
MAX_SIZE_MB = 24.0

# LISTE DES INSTANCES COBALT (Si une plante, on passe à l'autre)
COBALT_INSTANCES = [
    "https://api.cobalt.tools/api/json",      # Instance officielle (souvent chargée)
    "https://cobalt.startpage.ch/api/json",   # Instance Suisse (rapide)
    "https://cobalt.kwiatekmiki.pl/api/json", # Instance backup
]

BACKUP_QUERIES = [
    "Wolf of Wall Street sell me this pen shorts vertical",
    "Peaky Blinders thomas shelby sigma edit vertical",
    "The Office best moments shorts vertical",
    "Kaamelott perceval faux cul shorts vertical",
    "Oss 117 rire shorts vertical"
]

def get_ai_search_query():
    """Génère une recherche via Hugging Face."""
    token = os.environ.get('HF_TOKEN')
    if not token: return random.choice(BACKUP_QUERIES)

    try:
        client = InferenceClient(model="Qwen/Qwen2.5-72B-Instruct", token=token)
        prompt = "Donne-moi UNE SEULE requête YouTube pour un Short viral. Juste les mots clés en anglais ou français. Exemple: Suits harvey specter edit vertical"
        messages = [{"role": "user", "content": prompt}]
        response = client.chat_completion(messages, max_tokens=50, temperature=1.0)
        return response.choices[0].message.content.strip().replace('"', '').split('\n')[0]
    except:
        return random.choice(BACKUP_QUERIES)

def download_with_cobalt(youtube_url):
    """Essaie de télécharger via plusieurs serveurs Cobalt."""
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    payload = {
        "url": youtube_url,
        "vCodec": "h264",
        "vQuality": "720",
        "aFormat": "mp3",
        "isAudioOnly": False
    }

    # On boucle sur la liste des serveurs
    for api_url in COBALT_INSTANCES:
        print(f"🛡️ Essai avec le serveur : {api_url}")
        
        try:
            response = requests.post(api_url, json=payload, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                download_link = data.get('url')
                
                if download_link:
                    print("⬇️ Lien reçu, téléchargement de la vidéo...")
                    video_response = requests.get(download_link, stream=True)
                    
                    with open(FILENAME, 'wb') as f:
                        for chunk in video_response.iter_content(chunk_size=1024 * 1024):
                            if chunk: f.write(chunk)
                    
                    print("✅ Succès Cobalt !")
                    return True
                else:
                    print(f"⚠️ Serveur OK mais pas de lien : {data}")
            else:
                print(f"⚠️ Serveur erreur {response.status_code}")

        except Exception as e:
            print(f"❌ Erreur connexion serveur : {e}")
        
        print("🔄 Passage au serveur suivant...")
        time.sleep(1)

    print("❌ Tous les serveurs Cobalt ont échoué.")
    return False

def find_video_url(search_query):
    print(f"🔍 Recherche URL pour : {search_query}")
    
    # On utilise yt-dlp uniquement pour CHERCHER le lien (pas télécharger)
    # C'est beaucoup moins bloqué par YouTube que le téléchargement
    ydl_opts_search = {
        'default_search': 'ytsearch1',
        'noplaylist': True,
        'quiet': True,
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts_search) as ydl:
            info = ydl.extract_info(search_query, download=False)
            if 'entries' in info:
                data = info['entries'][0]
            else:
                data = info
            
            print(f"🎯 Trouvé : {data.get('title')} ({data.get('webpage_url')})")
            return {'title': data.get('title'), 'url': data.get('webpage_url')}
            
    except Exception as e:
        print(f"❌ Erreur recherche : {e}")
        return None

def send_email(video_data, query):
    email_user = os.environ.get('EMAIL_USER')
    email_pass = os.environ.get('EMAIL_PASSWORD')
    email_receiver = os.environ.get('EMAIL_RECEIVER')

    if not all([email_user, email_pass, email_receiver]): 
        print("❌ Secrets manquants.")
        return

    if not os.path.exists(FILENAME): return

    msg = EmailMessage()
    msg['Subject'] = f'🚀 Viral : {video_data["title"]}'
    msg['From'] = email_user
    msg['To'] = email_receiver
    msg.set_content(f"Lien : {video_data['url']}\nRecherche : {query}")

    with open(FILENAME, 'rb') as f:
        msg.add_attachment(f.read(), maintype='video', subtype='mp4', filename="video.mp4")

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(email_user, email_pass)
            smtp.send_message(msg)
        print("✅ Email envoyé !")
    except Exception as e:
        print(f"❌ Erreur email : {e}")

if __name__ == "__main__":
    time.sleep(2)
    query = get_ai_search_query()
    if query:
        video_info = find_video_url(query)
        if video_info:
            success = download_with_cobalt(video_info['url'])
            if success:
                send_email(video_info, query)
            else:
                print("❌ Impossible de télécharger la vidéo via Cobalt.")
        else:
            print("❌ Aucune vidéo trouvée.")
