import os
import smtplib
import math
import random
import time
from email.message import EmailMessage
import yt_dlp
from huggingface_hub import InferenceClient

# --- CONFIGURATION ---
FILENAME = "viral_video.mp4"
MAX_SIZE_MB = 24.5

# LISTE DE SECOURS (Si l'IA plante ou est surchargée)
BACKUP_QUERIES = [
    "Wolf of Wall Street sell me this pen shorts vertical",
    "Peaky Blinders thomas shelby sigma edit vertical",
    "The Office best moments shorts vertical",
    "Kaamelott perceval faux cul shorts vertical",
    "Oss 117 rire shorts vertical",
    "Suits harvey specter quotes shorts vertical",
    "Breaking Bad funny moments shorts vertical"
]

def calculate_virality_score(view_count, like_count):
    if not view_count: return 0
    try:
        score_views = min(100, math.log10(view_count) * 14) 
    except:
        score_views = 10
    
    if like_count and view_count > 0:
        ratio = (like_count / view_count) * 100
        score_engagement = min(100, ratio * 20)
    else:
        score_engagement = 50
    
    return round((score_views * 0.7) + (score_engagement * 0.3), 1)

def get_ai_search_query():
    """Utilise Hugging Face (Qwen/Mistral) pour générer une idée."""
    token = os.environ.get('HF_TOKEN')
    
    if not token:
        print("⚠️ Pas de token HF, passage au mode manuel.")
        return random.choice(BACKUP_QUERIES)

    # On utilise Qwen 2.5 (Modèle très performant et souvent dispo gratuitement)
    # Si celui-ci échoue, on bascule direct sur la backup list
    client = InferenceClient(model="Qwen/Qwen2.5-72B-Instruct", token=token)

    prompt = """
    Donne-moi UNE SEULE requête de recherche YouTube pour trouver un "Edit" viral (Shorts).
    Sujets : Business (Wolf of Wall Street, Suits) OU Humour (OSS 117, Kaamelott).
    Format : Uniquement les mots clés.
    Doit inclure : "shorts", "vertical".
    Exemple : Kaamelott best of perceval shorts vertical
    """

    try:
        # On utilise chat_completion qui est le standard actuel
        messages = [{"role": "user", "content": prompt}]
        response = client.chat_completion(messages, max_tokens=50, temperature=1.0)
        query = response.choices[0].message.content.strip().replace('"', '').split('\n')[0]
        
        print(f"🧠 L'IA propose : {query}")
        return query
    except Exception as e:
        print(f"⚠️ L'IA n'est pas dispo ({e}). Utilisation de la liste de secours.")
        return random.choice(BACKUP_QUERIES)

def download_and_analyze(search_query):
    print(f"🔍 Traitement de : {search_query}")
    
    # --- CONFIGURATION YT-DLP ---
    # Correction de l'erreur "Invalid filter" : On sépare bien les crochets [ext=mp4][height<=1080]
    ydl_opts = {
        'format': 'bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': FILENAME,
        'default_search': 'ytsearch1',
        'noplaylist': True,
        'quiet': True,
        # Ruse Anti-Bot : On simule un téléphone Android
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
        'user_agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36',
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # On force le téléchargement direct pour éviter les requêtes doubles qui déclenchent le blocage
            info = ydl.extract_info(search_query, download=True)
            
            if 'entries' in info:
                video_data = info['entries'][0]
            else:
                video_data = info

            title = video_data.get('title', 'Inconnu')
            views = video_data.get('view_count', 0)
            likes = video_data.get('like_count', 0)
            url = video_data.get('webpage_url', '')
            
            score = calculate_virality_score(views, likes)
            print(f"✅ Vidéo téléchargée : {title}")
            print(f"📊 Score viralité : {score}%")
            
            return {'title': title, 'score': score, 'views': views, 'url': url}

    except Exception as e:
        print(f"❌ Erreur YouTube : {e}")
        return None

def send_email(video_data, query):
    email_user = os.environ.get('EMAIL_USER')
    email_pass = os.environ.get('EMAIL_PASSWORD')
    email_receiver = os.environ.get('EMAIL_RECEIVER')

    if not all([email_user, email_pass, email_receiver]): 
        print("❌ Secrets Email manquants.")
        return

    if not os.path.exists(FILENAME):
        print("⚠️ Fichier vidéo absent (échec téléchargement).")
        return

    msg = EmailMessage()
    msg['Subject'] = f'🔥 Viral {video_data["score"]}% : {video_data["title"]}'
    msg['From'] = email_user
    msg['To'] = email_receiver
    msg.set_content(f"Lien: {video_data['url']}\nVues: {video_data['views']}\nRecherche: {query}")

    with open(FILENAME, 'rb') as f:
        msg.add_attachment(f.read(), maintype='video', subtype='mp4', filename="video.mp4")

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(email_user, email_pass)
            smtp.send_message(msg)
        print("✅ Email envoyé !")
    except Exception as e:
        print(f"❌ Erreur lors de l'envoi de l'email : {e}")

if __name__ == "__main__":
    # Petit délai de sécurité au lancement
    time.sleep(2)
    
    query = get_ai_search_query()
    
    if query:
        data = download_and_analyze(query)
        if data: 
            send_email(data, query)
        else:
            print("❌ Échec total. Vérifie les logs.")
    else:
        print("Erreur fatale : Pas de requête de recherche.")
