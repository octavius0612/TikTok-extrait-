import os
import smtplib
import math
import random
from email.message import EmailMessage
import yt_dlp
from huggingface_hub import InferenceClient

# --- CONFIGURATION ---
FILENAME = "viral_video.mp4"
MAX_SIZE_MB = 24.5

# LISTE DE SECOURS (Si l'IA est surchargée)
BACKUP_QUERIES = [
    "Wolf of Wall Street sell me this pen shorts vertical",
    "OSS 117 blanquette scene shorts vertical",
    "Peaky Blinders thomas shelby badass edit vertical",
    "The Office best moments shorts vertical",
    "François Damiens l'embrouille best of shorts",
    "Brice de Nice cassé best of vertical",
    "Suits harvey specter quotes shorts vertical"
]

def calculate_virality_score(view_count, like_count):
    """Calcule le potentiel viral."""
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
    """Utilise Hugging Face (Mistral 7B) pour trouver une idée."""
    token = os.environ.get('HF_TOKEN')
    
    if not token:
        print("⚠️ Pas de token HF, utilisation de la liste de secours.")
        return random.choice(BACKUP_QUERIES)

    # On utilise le modèle Mistral-7B (gratuit, rapide et intelligent)
    client = InferenceClient(model="mistralai/Mistral-7B-Instruct-v0.3", token=token)

    prompt = """
    Tu es un expert TikTok. Donne-moi UNE SEULE requête de recherche YouTube pour trouver un "Edit" viral (vidéo montée dynamique).
    
    Styles possibles (choisis au hasard) :
    1. Business/Sigma (Loup de Wall Street, Suits, Peaky Blinders)
    2. Humour Culte (OSS 117, La Cité de la Peur, Kaamelott, The Office)

    Format de réponse attendu : Uniquement la phrase à taper dans YouTube.
    Doit inclure : "shorts", "vertical", "edit".
    Exemple : Kaamelott best of perceval shorts vertical edit
    """

    try:
        # On demande à l'IA de compléter le prompt
        response = client.text_generation(prompt, max_new_tokens=50, temperature=0.9)
        query = response.strip().replace('"', '').split('\n')[0] # Nettoyage
        print(f"🧠 L'IA HuggingFace propose : {query}")
        return query
    except Exception as e:
        print(f"⚠️ Erreur IA ({e}), bascule sur secours.")
        return random.choice(BACKUP_QUERIES)

def download_and_analyze(search_query):
    print(f"🔍 Traitement de : {search_query}")
    
    # 1. Analyse sans télécharger
    ydl_opts_meta = {
        'default_search': 'ytsearch1',
        'noplaylist': True,
        'quiet': True,
        'match_filter': yt_dlp.utils.match_filter_func("duration > 5 & duration < 120"),
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts_meta) as ydl:
            info = ydl.extract_info(search_query, download=False)
            video_data = info['entries'][0] if 'entries' in info else info
            
            title = video_data.get('title', 'Inconnu')
            views = video_data.get('view_count', 0)
            likes = video_data.get('like_count', 0)
            score = calculate_virality_score(views, likes)
            
            print(f"📊 {title} | Score: {score}% | Vues: {views}")

            if score < 40: # Filtre de qualité
                print("❌ Score trop faible, on annule.")
                return None

            data = {'title': title, 'score': score, 'views': views, 'url': video_data.get('webpage_url'), 'uploader': video_data.get('uploader')}

    except Exception as e:
        print(f"❌ Erreur analyse : {e}")
        return None

    # 2. Téléchargement réel
    print(f"⬇️ Téléchargement...")
    ydl_opts_download = {
        'format': 'bestvideo[ext=mp4,height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]',
        'outtmpl': FILENAME,
        'default_search': 'ytsearch1',
        'noplaylist': True,
        'quiet': True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts_download) as ydl:
            ydl.download([search_query])
        return data
    except Exception as e:
        print(f"❌ Erreur DL : {e}")
        return None

def send_email(video_data, query):
    email_user = os.environ.get('EMAIL_USER')
    email_pass = os.environ.get('EMAIL_PASSWORD')
    email_receiver = os.environ.get('EMAIL_RECEIVER')

    if not all([email_user, email_pass, email_receiver]): return

    if not os.path.exists(FILENAME) or os.path.getsize(FILENAME) > MAX_SIZE_MB * 1024 * 1024:
        print("⚠️ Fichier absent ou trop lourd.")
        return

    msg = EmailMessage()
    msg['Subject'] = f'🔥 Viral {video_data["score"]}% : {video_data["title"]}'
    msg['From'] = email_user
    msg['To'] = email_receiver
    msg.set_content(f"Source: {video_data['url']}\nViews: {video_data['views']}\nQuery: {query}")

    with open(FILENAME, 'rb') as f:
        msg.add_attachment(f.read(), maintype='video', subtype='mp4', filename="video.mp4")

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(email_user, email_pass)
        smtp.send_message(msg)
    print("✅ Email envoyé !")

if __name__ == "__main__":
    query = get_ai_search_query()
    if query:
        data = download_and_analyze(query)
        if data: send_email(data, query)
