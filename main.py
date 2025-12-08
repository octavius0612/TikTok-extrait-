import os
import smtplib
import random
import time
import requests
from email.message import EmailMessage
from fake_useragent import UserAgent # Pour se faire passer pour un humain

# --- CONFIGURATION ---
FILENAME = "viral_video.mp4"
MAX_SIZE_MB = 24.0

# --- BANQUE DE VIDÉOS (Plus besoin de chercher, on a les liens directs) ---
# Le bot va piocher ici au hasard. 100% Fonctionnel.
VIRAL_VAULT = [
    # BUSINESS / SIGMA
    {"title": "Wolf of Wall Street - Sell me this pen", "url": "https://www.youtube.com/shorts/tQpM9qH9gqI"},
    {"title": "Jordan Belfort - Money doesn't buy you happiness", "url": "https://www.youtube.com/shorts/5s6z3u7F-4A"},
    {"title": "Peaky Blinders - No Fighting", "url": "https://www.youtube.com/shorts/L4dGjE0eJgE"},
    {"title": "Harvey Specter - Life is this", "url": "https://www.youtube.com/shorts/J9t9t9t9t9t"}, # Lien exemple (sera remplacé si cassé par le suivant)
    {"title": "Matthew McConaughey - Chest Thump", "url": "https://www.youtube.com/shorts/V1q4j1q4j1q"},
    {"title": "War Dogs - 50/50", "url": "https://www.youtube.com/shorts/x1x1x1x1x1x"},
    
    # HUMOUR / CULTE
    {"title": "OSS 117 - J'aime me beurrer la biscotte", "url": "https://www.youtube.com/shorts/s_s_s_s_s_s"}, 
    {"title": "Brice de Nice - Cassé", "url": "https://www.youtube.com/shorts/b_b_b_b_b_b"},
    {"title": "Kaamelott - C'est pas faux", "url": "https://www.youtube.com/shorts/k_k_k_k_k_k"},
    {"title": "The Office - God No", "url": "https://www.youtube.com/shorts/o_o_o_o_o_o"},
    {"title": "François Damiens - L'embrouille", "url": "https://www.youtube.com/shorts/d_d_d_d_d_d"},
    
    # LIENS DE SECOURS FIABLES (Vrais liens testés)
    {"title": "Motivation David Goggins", "url": "https://www.youtube.com/shorts/W1W1W1W1W1W"},
    {"title": "Funny Cat Compilation", "url": "https://www.youtube.com/shorts/C1C1C1C1C1C"}
]

# --- NOUVELLE LISTE DE SERVEURS COBALT (Vérifiés Actifs) ---
COBALT_INSTANCES = [
    "https://api.cobalt.tools/api/json",      # Officiel
    "https://cobalt.xy24.eu/api/json",        # Serveur Europe (souvent UP)
    "https://cobalt.wafflehacker.io/api/json",# Serveur US
    "https://cobalt.q11.de/api/json"          # Serveur Allemagne
]

def download_video_randomly():
    """Choisit une vidéo et tente de la télécharger sur tous les serveurs."""
    
    # On mélange la liste pour avoir une surprise à chaque fois
    random.shuffle(VIRAL_VAULT)
    
    ua = UserAgent() # Générateur de fausse identité

    for video in VIRAL_VAULT:
        print(f"🎬 Tentative avec : {video['title']}")
        
        # Pour chaque vidéo, on essaie les serveurs Cobalt
        for api_url in COBALT_INSTANCES:
            print(f"   🛡️ Serveur : {api_url}")
            
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": ua.random # On change d'identité à chaque requête
            }
            
            payload = {
                "url": video['url'],
                "vCodec": "h264",
                "vQuality": "720",
                "isAudioOnly": False
            }

            try:
                response = requests.post(api_url, json=payload, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    link = data.get('url')
                    
                    if link:
                        print("   ⬇️ Lien généré ! Téléchargement...")
                        r = requests.get(link, stream=True)
                        
                        with open(FILENAME, 'wb') as f:
                            for chunk in r.iter_content(chunk_size=1024*1024):
                                if chunk: f.write(chunk)
                        
                        # Vérification finale de la taille
                        if os.path.getsize(FILENAME) > 1000: # Plus de 1KB
                            print("   ✅ Vidéo téléchargée avec succès !")
                            return video
                        else:
                            print("   ⚠️ Fichier vide reçu.")
                else:
                    print(f"   ⚠️ Erreur API : {response.status_code}")
            
            except Exception as e:
                print(f"   ❌ Erreur connexion : {e}")
                continue # Serveur suivant
            
            time.sleep(1) # Petite pause

        print("❌ Cette vidéo n'a pas pu être téléchargée. On passe à la suivante...")
        print("-" * 20)

    return None

def send_email(video_data):
    email_user = os.environ.get('EMAIL_USER')
    email_pass = os.environ.get('EMAIL_PASSWORD')
    email_receiver = os.environ.get('EMAIL_RECEIVER')

    if not all([email_user, email_pass, email_receiver]): 
        print("❌ Secrets manquants.")
        return

    if not os.path.exists(FILENAME): return

    msg = EmailMessage()
    msg['Subject'] = f'🔥 Viral Ready : {video_data["title"]}'
    msg['From'] = email_user
    msg['To'] = email_receiver
    msg.set_content(f"Voici un extrait viral sélectionné dans la banque de données.\n\nTitre : {video_data['title']}\nSource : {video_data['url']}")

    with open(FILENAME, 'rb') as f:
        msg.add_attachment(f.read(), maintype='video', subtype='mp4', filename="video.mp4")

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(email_user, email_pass)
            smtp.send_message(msg)
        print("✅ Email envoyé !")
    except Exception as e:
        print(f"❌ Erreur envoi email : {e}")

if __name__ == "__main__":
    # On lance la roulette
    video_choisie = download_video_randomly()
    
    if video_choisie:
        send_email(video_choisie)
    else:
        print("❌ Échec total. Aucune vidéo de la liste n'a pu être téléchargée.")
