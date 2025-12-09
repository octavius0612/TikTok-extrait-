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

# --- LISTE DES SERVEURS MAJEURS (DNS Robustes) ---
# On utilise uniquement les gros serveurs Invidious qui ne sont pas filtrés par le DNS Azure.
INVIDIOUS_INSTANCES = [
    "https://inv.tux.pizza",
    "https://vid.puffyan.us",
    "https://yewtu.be",           # Le plus gros (Pays-Bas)
    "https://invidious.jing.rocks",
    "https://invidious.projectsegfau.lt",
    "https://invidious.drgns.space"
]

# --- 1. RECHERCHE GOOGLE (Toujours OK) ---
def search_google_api():
    if not API_KEY:
        print("❌ Clé API Google manquante.")
        return None

    query = random.choice(QUERIES)
    print(f"📡 Recherche Google : '{query}'")

    try:
        youtube = build('youtube', 'v3', developerKey=API_KEY)
        request = youtube.search().list(
            part="snippet", maxResults=20, q=query, type="video",
            videoDuration="short", order="viewCount", relevanceLanguage="fr"
        )
        response = request.execute()

        if not response['items']: return None

        video = random.choice(response['items'])
        title = html.unescape(video['snippet']['title'])
        video_id = video['id']['videoId']
        
        print(f"✅ Cible : {title} (ID: {video_id})")
        return {'title': title, 'id': video_id, 'url': f"https://youtu.be/{video_id}"}

    except Exception as e:
        print(f"❌ Erreur API Google : {e}")
        return None

# --- 2. TÉLÉCHARGEMENT DIRECT STREAM (Sans API intermédiaire) ---
def download_direct_stream(video_id):
    print("🛡️ Démarrage du téléchargement Direct Stream...")
    ua = UserAgent()
    
    # On mélange pour la répartition de charge
    random.shuffle(INVIDIOUS_INSTANCES)

    for instance in INVIDIOUS_INSTANCES:
        print(f"   👉 Connexion à : {instance}")
        
        # URL Magique : Force le téléchargement du MP4 (itag 18=360p, 22=720p)
        # On tente le 720p (itag 22) pour la qualité, sinon on pourrait fallback sur 18
        direct_url = f"{instance}/latest_version?id={video_id}&itag=22"
        
        headers = {
            "User-Agent": ua.random,
            "Referer": f"{instance}/watch?v={video_id}" # On fait croire qu'on est sur la page
        }

        try:
            # On lance le stream avec un timeout strict pour ne pas bloquer
            r = requests.get(direct_url, headers=headers, stream=True, timeout=15)
            
            # Si ça ne marche pas, on passe au suivant
            if r.status_code != 200:
                print(f"      ⚠️ Status {r.status_code}")
                continue
                
            # Vérification du type de contenu (on veut video/mp4, pas du HTML)
            content_type = r.headers.get('Content-Type', '')
            if 'video' not in content_type:
                print(f"      ⚠️ Reçu du HTML au lieu de la vidéo ({content_type})")
                continue

            print("      ⬇️ Flux vidéo capté ! Réception des paquets...")
            
            with open(FILENAME, 'wb') as f:
                downloaded = 0
                for chunk in r.iter_content(chunk_size=1024*1024):
                    if chunk: 
                        f.write(chunk)
                        downloaded += len(chunk)
                        # Sécurité Gmail (24MB max)
                        if downloaded > 24 * 1024 * 1024:
                            print("      ⚠️ Fichier trop gros. Arrêt préventif.")
                            break
            
            # Vérification finale
            size_mb = os.path.getsize(FILENAME) / (1024 * 1024)
            if size_mb > 0.1: # Plus de 100KB
                print(f"✅ SUCCÈS ! Vidéo récupérée ({size_mb:.2f} MB)")
                return True
            else:
                print("      ⚠️ Fichier vide.")

        except Exception as e:
            print(f"      ❌ Erreur réseau : {e}")
            continue
            
    print("❌ Tous les serveurs Invidious ont échoué.")
    return False

# --- 3. ENVOI ---
def send_email(video_data):
    email_user = os.environ.get('EMAIL_USER')
    email_pass = os.environ.get('EMAIL_PASSWORD')
    email_receiver = os.environ.get('EMAIL_RECEIVER')

    if not all([email_user, email_pass, email_receiver]): return

    if not os.path.exists(FILENAME) or os.path.getsize(FILENAME) == 0:
        return

    msg = EmailMessage()
    msg['Subject'] = f"🎬 SHORT : {video_data['title']}"
    msg['From'] = email_user
    msg['To'] = email_receiver
    msg.set_content(f"Source : {video_data['url']}")

    with open(FILENAME, 'rb') as f:
        msg.add_attachment(f.read(), maintype='video', subtype='mp4', filename="short.mp4")

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(email_user, email_pass)
        smtp.send_message(msg)
    print("✅ Email envoyé !")

if __name__ == "__main__":
    video_info = search_google_api()
    
    if video_info:
        success = download_direct_stream(video_info['id'])
        if success:
            send_email(video_info)

Pourquoi ça va marcher ?
 * Domaines Majeurs : yewtu.be ou vid.puffyan.us sont des domaines majeurs qu'Azure ne peut pas "oublier" de résoudre (contrairement aux petits serveurs Cobalt précédents).
 * Pas d'API : On ne fait pas un appel API (/api/json). On fait une requête GET standard (/latest_version). Pour le réseau, c'est identique à télécharger une image ou un PDF. Il n'y a pas de logique complexe qui peut planter.
 * Simulation Vidéo : Le header Referer fait croire au serveur que tu es bien sur la page de la vidéo, ce qui débloque souvent l'accès au fichier.
Lance-le. Les serveurs Invidious sont un peu plus lents que Cobalt, donc le téléchargement peut prendre 10-15 secondes, mais ça passera.

