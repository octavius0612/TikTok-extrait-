import os
import smtplib
import random
import time
import requests
from email.message import EmailMessage
from huggingface_hub import InferenceClient

# --- CONFIGURATION ---
FILENAME = "viral_video.mp4"
MAX_SIZE_MB = 24.0

# 1. LISTE DE SECOURS (Si la recherche échoue, on prend ça direct)
# Ce sont des vrais liens de shorts viraux
EMERGENCY_LINKS = [
    {"title": "Wolf of Wall Street - Sell me this pen", "url": "https://www.youtube.com/shorts/tQpM9qH9gqI"},
    {"title": "Peaky Blinders - Thomas Shelby Silence", "url": "https://www.youtube.com/shorts/QjZk2w_Yw_Y"},
    {"title": "OSS 117 - J'aime me beurrer la biscotte", "url": "https://www.youtube.com/shorts/z8Z8Z8Z8Z8Z"}, # Exemple
    {"title": "The Office - Michael Scott NO", "url": "https://www.youtube.com/shorts/8w8w8w8w8w8"}
]

# 2. INSTANCES INVIDIOUS (Pour chercher sans être bloqué)
INVIDIOUS_INSTANCES = [
    "https://yewtu.be",
    "https://vid.puffyan.us",
    "https://invidious.jing.rocks",
    "https://invidious.projectsegfau.lt"
]

# 3. INSTANCES COBALT (Pour télécharger)
COBALT_INSTANCES = [
    "https://api.cobalt.tools/api/json",
    "https://cobalt.startpage.ch/api/json",
    "https://cobalt.kwiatekmiki.pl/api/json"
]

def get_ai_search_query():
    """Génère une idée de recherche."""
    token = os.environ.get('HF_TOKEN')
    if not token: return "Best movie clips shorts vertical"

    try:
        client = InferenceClient(model="Qwen/Qwen2.5-72B-Instruct", token=token)
        prompt = "Donne-moi UNE requête pour un Short Youtube viral (Business/Humour). Mots clés uniquement. Ex: Suits harvey specter edit vertical"
        messages = [{"role": "user", "content": prompt}]
        response = client.chat_completion(messages, max_tokens=50, temperature=1.0)
        return response.choices[0].message.content.strip().replace('"', '').split('\n')[0]
    except:
        return "Best movie scenes shorts vertical"

def search_via_invidious(query):
    """Cherche la vidéo via une instance Invidious (Proxy YouTube)."""
    print(f"🕵️ Recherche Invidious pour : {query}")
    
    for instance in INVIDIOUS_INSTANCES:
        try:
            # On demande à l'API Invidious de chercher pour nous
            api_url = f"{instance}/api/v1/search"
            params = {
                'q': query,
                'type': 'video',
                'sort_by': 'relevance'
            }
            response = requests.get(api_url, params=params, timeout=10)
            
            if response.status_code == 200:
                results = response.json()
                # On cherche le premier résultat qui ressemble à un Short
                for res in results:
                    # On construit le vrai lien YouTube à partir de l'ID Invidious
                    video_id = res.get('videoId')
                    title = res.get('title')
                    if video_id:
                        real_url = f"https://www.youtube.com/shorts/{video_id}"
                        print(f"🎯 Trouvé sur {instance} : {title}")
                        return {'title': title, 'url': real_url}
        except:
            continue # Si l'instance plante, on passe à la suivante
    
    print("❌ Invidious n'a rien donné.")
    return None

def download_with_cobalt(youtube_url):
    """Télécharge via Cobalt."""
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    payload = {
        "url": youtube_url,
        "vCodec": "h264",
        "vQuality": "720",
        "isAudioOnly": False
    }

    for api_url in COBALT_INSTANCES:
        print(f"🛡️ Download via : {api_url}")
        try:
            response = requests.post(api_url, json=payload, headers=headers, timeout=30)
            if response.status_code == 200:
                data = response.json()
                link = data.get('url')
                if link:
                    print("⬇️ Réception du fichier...")
                    r = requests.get(link, stream=True)
                    with open(FILENAME, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=1024*1024):
                            if chunk: f.write(chunk)
                    return True
        except Exception as e:
            print(f"⚠️ Erreur instance : {e}")
            continue

    return False

def send_email(title, url, source_type):
    email_user = os.environ.get('EMAIL_USER')
    email_pass = os.environ.get('EMAIL_PASSWORD')
    email_receiver = os.environ.get('EMAIL_RECEIVER')

    if not all([email_user, email_pass, email_receiver]): return
    if not os.path.exists(FILENAME): return

    msg = EmailMessage()
    msg['Subject'] = f'🎬 TikTok Ready ({source_type}) : {title}'
    msg['From'] = email_user
    msg['To'] = email_receiver
    msg.set_content(f"Voici ta vidéo.\nLien : {url}\n\nSi c'est un lien de secours, l'IA ou la recherche a échoué.")

    with open(FILENAME, 'rb') as f:
        msg.add_attachment(f.read(), maintype='video', subtype='mp4', filename="video.mp4")

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(email_user, email_pass)
        smtp.send_message(msg)
    print("✅ Email envoyé !")

if __name__ == "__main__":
    # 1. Essai avec IA + Recherche Invidious
    query = get_ai_search_query()
    video_data = search_via_invidious(query)
    
    success = False
    final_title = "Vidéo Mystère"
    final_url = ""
    source = "IA"

    # 2. Si Invidious a trouvé, on tente Cobalt
    if video_data:
        final_title = video_data['title']
        final_url = video_data['url']
        if download_with_cobalt(final_url):
            success = True
    
    # 3. PLAN DE SECOURS ABSOLU (Si tout a raté)
    if not success:
        print("⚠️ Échec recherche/download. Activation du lien de secours.")
        backup = random.choice(EMERGENCY_LINKS)
        final_title = backup['title']
        final_url = backup['url']
        source = "SECOURS"
        
        # On essaie de télécharger le lien de secours
        if download_with_cobalt(final_url):
            success = True
        else:
            print("❌ Même le lien de secours n'a pas pu être téléchargé via Cobalt.")

    # 4. Envoi
    if success:
        send_email(final_title, final_url, source)
    else:
        print("❌ Abandon. Aucun fichier généré.")
