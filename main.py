import os
import smtplib
import random
import time
import requests
from email.message import EmailMessage
from duckduckgo_search import DDGS # C'est notre nouveau moteur de recherche
from huggingface_hub import InferenceClient

# --- CONFIGURATION ---
FILENAME = "viral_video.mp4"
MAX_SIZE_MB = 24.0

# LISTE DES INSTANCES COBALT (Serveurs de téléchargement)
COBALT_INSTANCES = [
    "https://api.cobalt.tools/api/json",
    "https://cobalt.startpage.ch/api/json",
    "https://cobalt.kwiatekmiki.pl/api/json",
    "https://cobalt.q11.de/api/json"
]

BACKUP_QUERIES = [
    "Wolf of Wall Street motivational shorts vertical",
    "Peaky Blinders thomas shelby edit vertical",
    "The Office michael scott funny shorts",
    "Kaamelott perceval best of shorts vertical",
    "Oss 117 blanquette shorts vertical"
]

def get_ai_search_query():
    """Génère une idée de recherche."""
    token = os.environ.get('HF_TOKEN')
    if not token: return random.choice(BACKUP_QUERIES)

    try:
        client = InferenceClient(model="Qwen/Qwen2.5-72B-Instruct", token=token)
        prompt = "Donne-moi UNE SEULE requête pour trouver un Short Youtube viral (Business/Humour). Juste les mots clés. Exemple: Suits harvey specter edit vertical"
        messages = [{"role": "user", "content": prompt}]
        response = client.chat_completion(messages, max_tokens=50, temperature=1.0)
        return response.choices[0].message.content.strip().replace('"', '').split('\n')[0]
    except:
        return random.choice(BACKUP_QUERIES)

def find_video_url_via_ddg(query):
    """Utilise DuckDuckGo pour trouver le lien YouTube sans toucher à YouTube."""
    print(f"🦆 Recherche DuckDuckGo pour : {query}")
    
    try:
        # On force la recherche sur le site youtube.com
        search_term = f"site:youtube.com/shorts {query}"
        
        results = DDGS().text(search_term, max_results=3)
        
        if not results:
            print("❌ DuckDuckGo n'a rien trouvé.")
            return None
            
        # On prend le premier résultat valide
        for res in results:
            link = res['href']
            title = res['title']
            if "youtube.com" in link:
                print(f"🎯 Lien trouvé via DDG : {title} ({link})")
                return {'title': title, 'url': link}
                
        print("❌ Aucun lien YouTube trouvé dans les résultats.")
        return None

    except Exception as e:
        print(f"❌ Erreur DuckDuckGo : {e}")
        return None

def download_with_cobalt(youtube_url):
    """Télécharge via les serveurs Cobalt."""
    
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    
    payload = {
        "url": youtube_url,
        "vCodec": "h264",
        "vQuality": "720",
        "aFormat": "mp3",
        "isAudioOnly": False
    }

    for api_url in COBALT_INSTANCES:
        print(f"🛡️ Essai download via : {api_url}")
        try:
            response = requests.post(api_url, json=payload, headers=headers, timeout=20)
            if response.status_code == 200:
                data = response.json()
                download_link = data.get('url')
                
                if download_link:
                    print("⬇️ Lien reçu, téléchargement...")
                    video_response = requests.get(download_link, stream=True)
                    with open(FILENAME, 'wb') as f:
                        for chunk in video_response.iter_content(chunk_size=1024*1024):
                            if chunk: f.write(chunk)
                    print("✅ Vidéo sauvegardée !")
                    return True
        except:
            continue # Si ça rate, on passe au suivant
        
        time.sleep(1)

    print("❌ Tous les serveurs Cobalt ont échoué.")
    return False

def send_email(video_data, query):
    email_user = os.environ.get('EMAIL_USER')
    email_pass = os.environ.get('EMAIL_PASSWORD')
    email_receiver = os.environ.get('EMAIL_RECEIVER')

    if not all([email_user, email_pass, email_receiver]): return
    if not os.path.exists(FILENAME): return

    msg = EmailMessage()
    msg['Subject'] = f'🚀 Viral Found : {video_data["title"]}'
    msg['From'] = email_user
    msg['To'] = email_receiver
    msg.set_content(f"Source : {video_data['url']}\nRecherche : {query}")

    with open(FILENAME, 'rb') as f:
        msg.add_attachment(f.read(), maintype='video', subtype='mp4', filename="viral.mp4")

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(email_user, email_pass)
        smtp.send_message(msg)
    print("✅ Email envoyé !")

if __name__ == "__main__":
    time.sleep(2)
    query = get_ai_search_query()
    
    if query:
        # Étape 1 : Trouver le lien sans toucher à YouTube (via DuckDuckGo)
        video_info = find_video_url_via_ddg(query)
        
        if video_info:
            # Étape 2 : Télécharger via serveur tiers (Cobalt)
            success = download_with_cobalt(video_info['url'])
            if success:
                send_email(video_info, query)
            else:
                print("❌ Echec du téléchargement.")
        else:
            print("❌ Echec de la recherche.")
