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

# LISTE DE SECOURS
BACKUP_QUERIES = [
    "Wolf of Wall Street sell me this pen shorts vertical",
    "Peaky Blinders thomas shelby sigma edit vertical",
    "The Office best moments shorts vertical",
    "Kaamelott perceval faux cul shorts vertical",
    "Oss 117 rire shorts vertical",
    "Suits harvey specter quotes shorts vertical"
]

def get_ai_search_query():
    """Génère une recherche via Hugging Face."""
    token = os.environ.get('HF_TOKEN')
    if not token: return random.choice(BACKUP_QUERIES)

    try:
        client = InferenceClient(model="Qwen/Qwen2.5-72B-Instruct", token=token)
        prompt = "Donne-moi UNE SEULE requête YouTube pour un Short viral (Business/Motivation/Humour). Juste les mots clés. Exemple: Suits harvey specter edit vertical"
        messages = [{"role": "user", "content": prompt}]
        response = client.chat_completion(messages, max_tokens=50, temperature=1.0)
        return response.choices[0].message.content.strip().replace('"', '').split('\n')[0]
    except:
        return random.choice(BACKUP_QUERIES)

# --- LA SOLUTION MAGIQUE : COBALT ---
def download_with_cobalt(youtube_url):
    print(f"🛡️ ACTIVATION DU PLAN B (Cobalt) pour : {youtube_url}")
    
    # On utilise une instance publique de l'API Cobalt
    api_url = "https://api.cobalt.tools/api/json"
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

    try:
        # 1. On demande à Cobalt de traiter la vidéo
        response = requests.post(api_url, json=payload, headers=headers)
        
        # Vérification si Cobalt est en surcharge
        if response.status_code != 200:
            print(f"⚠️ Cobalt a répondu : {response.status_code} - {response.text}")
            return False

        data = response.json()

        # Cobalt peut renvoyer l'URL de différentes manières
        download_link = data.get('url')
        
        if not download_link:
            print(f"❌ Cobalt n'a pas renvoyé de lien : {data}")
            return False
        
        # 2. On télécharge le fichier final
        print("⬇️ Téléchargement du fichier depuis Cobalt...")
        video_response = requests.get(download_link, stream=True)
        
        with open(FILENAME, 'wb') as f:
            for chunk in video_response.iter_content(chunk_size=1024 * 1024): # Chunk de 1MB
                if chunk: f.write(chunk)
        
        print("✅ Fichier sauvegardé avec succès via Cobalt !")
        return True

    except Exception as e:
        print(f"❌ Échec Cobalt : {e}")
        return False

def find_and_download_video(search_query):
    print(f"🔍 Recherche de l'URL pour : {search_query}")
    
    # On utilise yt-dlp JUSTE pour trouver l'URL (généralement ça passe mieux que le download)
    ydl_opts_search = {
        'default_search': 'ytsearch1',
        'noplaylist': True,
        'quiet': True,
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
    }

    video_url = ""
    title = "Vidéo Virale"
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts_search) as ydl:
            # On demande juste les infos, pas le téléchargement
            info = ydl.extract_info(search_query, download=False)
            
            if 'entries' in info:
                video_data = info['entries'][0]
            else:
                video_data = info
                
            video_url = video_data.get('webpage_url')
            title = video_data.get('title')
            print(f"🎯 Lien trouvé : {video_url}")
            
    except Exception as e:
        print(f"❌ Erreur lors de la recherche : {e}")
        return None

    if not video_url:
        print("❌ Aucune URL trouvée.")
        return None

    # MAINTENANT ON TÉLÉCHARGE VIA COBALT (Contourne le blocage Bot)
    success = download_with_cobalt(video_url)
    
    if success:
        return {'title': title, 'url': video_url}
    else:
        return None

def send_email(video_data, query):
    email_user = os.environ.get('EMAIL_USER')
    email_pass = os.environ.get('EMAIL_PASSWORD')
    email_receiver = os.environ.get('EMAIL_RECEIVER')

    if not all([email_user, email_pass, email_receiver]): 
        print("❌ Secrets manquants.")
        return

    if not os.path.exists(FILENAME) or os.path.getsize(FILENAME) > MAX_SIZE_MB * 1024 * 1024:
        print("⚠️ Fichier absent ou trop lourd.")
        return

    msg = EmailMessage()
    msg['Subject'] = f'🚀 TikTok Ready : {video_data["title"]}'
    msg['From'] = email_user
    msg['To'] = email_receiver
    msg.set_content(f"Voici ton edit viral.\n\nSource: {video_data['url']}\nRecherche: {query}")

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
    time.sleep(2) # Pause anti-spam
    
    query = get_ai_search_query()
    if query:
        data = find_and_download_video(query)
        if data: 
            send_email(data, query)
        else:
            print("❌ Échec du processus.")
