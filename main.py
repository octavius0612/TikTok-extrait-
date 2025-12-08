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

# LISTE DE SECOURS (Si l'IA plante)
BACKUP_QUERIES = [
    "Wolf of Wall Street sell me this pen shorts vertical",
    "Peaky Blinders thomas shelby sigma edit vertical",
    "The Office best moments shorts vertical",
    "Kaamelott perceval faux cul shorts vertical",
    "Oss 117 rire shorts vertical"
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
    """Utilise Hugging Face (Zephyr/Mistral) en mode Chat."""
    token = os.environ.get('HF_TOKEN')
    
    if not token:
        print("⚠️ Pas de token HF, utilisation de la liste de secours.")
        return random.choice(BACKUP_QUERIES)

    # On utilise Zephyr, très bon modèle gratuit
    client = InferenceClient(model="HuggingFaceH4/zephyr-7b-beta", token=token)

    prompt = """
    Tu es un expert TikTok. Donne-moi UNE SEULE requête de recherche YouTube pour trouver un "Edit" viral.
    La requête doit être en ANGLAIS ou FRANÇAIS.
    Doit inclure : "shorts", "vertical".
    Exemple : Kaamelott best of perceval shorts vertical
    """

    try:
        # Correction : Utilisation de chat_completion au lieu de text_generation
        messages = [{"role": "user", "content": prompt}]
        response = client.chat_completion(messages, max_tokens=50, temperature=0.9)
        query = response.choices[0].message.content.strip().replace('"', '').split('\n')[0]
        
        # Petit nettoyage si l'IA bavarde
        if len(query) > 100: query = "The Wolf of Wall Street motivation shorts vertical"
        
        print(f"🧠 L'IA propose : {query}")
        return query
    except Exception as e:
        print(f"⚠️ Erreur IA ({e}), bascule sur secours.")
        return random.choice(BACKUP_QUERIES)

def download_and_analyze(search_query):
    print(f"🔍 Traitement de : {search_query}")
    
    # --- RUSE ANTI-BOT ---
    # On se fait passer pour un client Android mobile pour éviter le blocage "Sign in"
    ydl_opts = {
        'format': 'bestvideo[ext=mp4,height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]',
        'outtmpl': FILENAME,
        'default_search': 'ytsearch1',
        'noplaylist': True,
        'quiet': True,
        # C'est ici que la magie opère pour contourner le blocage :
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
        'user_agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36',
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # On extrait d'abord les infos sans télécharger pour vérifier
            info = ydl.extract_info(search_query, download=True) # On télécharge directement pour éviter double requête
            
            if 'entries' in info:
                video_data = info['entries'][0]
            else:
                video_data = info

            title = video_data.get('title', 'Inconnu')
            views = video_data.get('view_count', 0)
            likes = video_data.get('like_count', 0)
            url = video_data.get('webpage_url', '')
            
            score = calculate_virality_score(views, likes)
            print(f"✅ Téléchargé : {title} | Score: {score}%")
            
            return {'title': title, 'score': score, 'views': views, 'url': url}

    except Exception as e:
        print(f"❌ Erreur critique YouTube : {e}")
        return None

def send_email(video_data, query):
    email_user = os.environ.get('EMAIL_USER')
    email_pass = os.environ.get('EMAIL_PASSWORD')
    email_receiver = os.environ.get('EMAIL_RECEIVER')

    if not all([email_user, email_pass, email_receiver]): 
        print("❌ Secrets manquants.")
        return

    if not os.path.exists(FILENAME):
        print("⚠️ Fichier vidéo absent.")
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
        print(f"❌ Erreur email : {e}")

if __name__ == "__main__":
    # Petit délai pour ne pas paraître suspect
    time.sleep(2)
    
    query = get_ai_search_query()
    if query:
        data = download_and_analyze(query)
        if data: 
            send_email(data, query)
        else:
            print("❌ Échec téléchargement. YouTube bloque peut-être l'IP.")
