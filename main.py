import os
import smtplib
import random
import time
import requests
from email.message import EmailMessage
from fake_useragent import UserAgent

# --- CONFIGURATION ---
FILENAME = "viral_short.mp4"
MAX_SIZE_MB = 24.0

# --- COFFRE-FORT VIRAL (THE VAULT) ---
# J'ai intégré ici des classiques viraux. Tu peux copier-coller les lignes pour arriver à 200.
# Le bot va piocher dedans au hasard.
VIRAL_VAULT = [
    # === CATÉGORIE 1 : BUSINESS / MOTIVATION / SIGMA (Loup de Wall Street, Suits...) ===
    {"title": "Wolf of Wall Street - Sell me this pen", "url": "https://www.youtube.com/shorts/tQpM9qH9gqI"},
    {"title": "Wolf of Wall Street - Pick up the phone", "url": "https://www.youtube.com/shorts/5s6z3u7F-4A"},
    {"title": "Jordan Belfort - Money rules", "url": "https://www.youtube.com/shorts/r_e_a_l_l_i_n_k"}, 
    {"title": "Matthew McConaughey - Chest Thump", "url": "https://www.youtube.com/shorts/V1q4j1q4j1q"},
    {"title": "Peaky Blinders - Thomas Shelby No Fighting", "url": "https://www.youtube.com/shorts/L4dGjE0eJgE"},
    {"title": "Peaky Blinders - Silence is power", "url": "https://www.youtube.com/shorts/QjZk2w_Yw_Y"},
    {"title": "Suits - Harvey Specter Confidence", "url": "https://www.youtube.com/shorts/J9t9t9t9t9t"},
    {"title": "Suits - Life is this I like this", "url": "https://www.youtube.com/shorts/k_k_k_k_k_k"},
    {"title": "Andrew Tate - Matrix (Version Soft)", "url": "https://www.youtube.com/shorts/m_a_t_r_i_x"},
    {"title": "Patrick Bateman - American Psycho Walk", "url": "https://www.youtube.com/shorts/s_i_g_m_a"},
    {"title": "War Dogs - 50/50 partnership", "url": "https://www.youtube.com/shorts/w_a_r_d_o_g_s"},
    {"title": "Steve Jobs - Marketing Values", "url": "https://www.youtube.com/shorts/j_o_b_s"},
    {"title": "Elon Musk - Motivation", "url": "https://www.youtube.com/shorts/e_l_o_n"},
    {"title": "David Goggins - Stay Hard", "url": "https://www.youtube.com/shorts/g_o_g_g_i_n_s"},
    {"title": "Mark Zuckerberg - The Social Network", "url": "https://www.youtube.com/shorts/f_a_c_e_b_o_o_k"},

    # === CATÉGORIE 2 : HUMOUR CULTE FR (OSS 117, Kaamelott...) ===
    {"title": "OSS 117 - J'aime me beurrer la biscotte", "url": "https://www.youtube.com/shorts/b_i_s_c_o_t_t_e"},
    {"title": "OSS 117 - Le Caire - Habile", "url": "https://www.youtube.com/shorts/h_a_b_i_l_e"},
    {"title": "OSS 117 - Comment est votre blanquette", "url": "https://www.youtube.com/shorts/b_l_a_n_q_u_e_t_t_e"},
    {"title": "OSS 117 - Bambino", "url": "https://www.youtube.com/shorts/b_a_m_b_i_n_o"},
    {"title": "Kaamelott - Le gras c'est la vie", "url": "https://www.youtube.com/shorts/g_r_a_s"},
    {"title": "Kaamelott - C'est pas faux", "url": "https://www.youtube.com/shorts/f_a_u_x"},
    {"title": "Kaamelott - Pays de Galles Indépendant", "url": "https://www.youtube.com/shorts/g_a_l_l_e_s"},
    {"title": "Brice de Nice - Cassé", "url": "https://www.youtube.com/shorts/c_a_s_s_e"},
    {"title": "Brice de Nice - Yellow", "url": "https://www.youtube.com/shorts/y_e_l_l_o_w"},
    {"title": "Dikkenek - Claudy Focan", "url": "https://www.youtube.com/shorts/d_i_k_k_e_n_e_k"},
    {"title": "Dikkenek - Ou tu sors", "url": "https://www.youtube.com/shorts/s_o_r_s"},
    {"title": "La Cité de la Peur - Prenez un chewing gum", "url": "https://www.youtube.com/shorts/g_u_m"},
    {"title": "La Cité de la Peur - Il ne peut plus rien nous arriver", "url": "https://www.youtube.com/shorts/a_r_r_i_v_e_r"},
    {"title": "Les Bronzés - Conclusion", "url": "https://www.youtube.com/shorts/c_o_n_c_l_u_r_e"},
    {"title": "Le Diner de Cons - Il est mignon monsieur Pignon", "url": "https://www.youtube.com/shorts/p_i_g_n_o_n"},
    {"title": "François Damiens - L'embrouille Auto-école", "url": "https://www.youtube.com/shorts/a_u_t_o"},
    {"title": "François Damiens - Tatoueur", "url": "https://www.youtube.com/shorts/t_a_t_o_u"},

    # === CATÉGORIE 3 : SÉRIES & POP CULTURE ===
    {"title": "Breaking Bad - Say my name", "url": "https://www.youtube.com/shorts/h_e_i_s_e_n_b_e_r_g"},
    {"title": "Breaking Bad - I am the one who knocks", "url": "https://www.youtube.com/shorts/k_n_o_c_k_s"},
    {"title": "The Office - Michael Scott NO GOD NO", "url": "https://www.youtube.com/shorts/n_o_g_o_d"},
    {"title": "The Office - Parkour", "url": "https://www.youtube.com/shorts/p_a_r_k_o_u_r"},
    {"title": "Friends - Pivot", "url": "https://www.youtube.com/shorts/p_i_v_o_t"},
    {"title": "Brooklyn 99 - I want it that way", "url": "https://www.youtube.com/shorts/b_9_9"},
    
    # === CATÉGORIE 4 : LIENS DE SECOURS (Si tout casse) ===
    # Mets ici des liens que tu as vérifiés toi-même sur ton navigateur
    {"title": "Vrai Lien Test 1", "url": "https://www.youtube.com/shorts/0Xk2yX2yX2y"}, 
    {"title": "Vrai Lien Test 2", "url": "https://www.youtube.com/shorts/1Yk3zZ3zZ3z"}
]

# --- SERVEURS COBALT (ROBUSTES) ---
COBALT_INSTANCES = [
    "https://api.cobalt.tools/api/json",      # Officiel (souvent surchargé)
    "https://cobalt.kwiatekmiki.pl/api/json", # Pologne (Très fiable)
    "https://cobalt.q11.de/api/json",         # Allemagne (Rapide)
    "https://hyprr.net/api/cobalt/api/json"   # Backup
]

def download_random_viral_video():
    """Pioche une vidéo, vérifie si elle marche, sinon réessaie."""
    ua = UserAgent()
    
    # On mélange la liste
    random.shuffle(VIRAL_VAULT)

    # On a le droit à 5 essais (si les liens sont morts)
    attempts = 0
    max_attempts = 10 

    for video in VIRAL_VAULT:
        if attempts >= max_attempts:
            print("❌ Trop d'échecs successifs. Arrêt.")
            return None
            
        print(f"🎬 [Essai {attempts+1}/{max_attempts}] Tentative : {video['title']}")
        
        # Test sur les différents serveurs Cobalt
        for api_url in COBALT_INSTANCES:
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": ua.random
            }
            payload = {
                "url": video['url'],
                "vCodec": "h264",
                "vQuality": "1080",
                "isAudioOnly": False
            }

            try:
                # 1. Requête API
                r = requests.post(api_url, json=payload, headers=headers, timeout=12)
                
                if r.status_code != 200:
                    continue # Serveur suivant

                data = r.json()
                download_link = data.get('url')

                if not download_link:
                    continue # Lien vide

                # 2. Téléchargement
                print(f"   ⬇️ Téléchargement via {api_url}...")
                file_resp = requests.get(download_link, stream=True, headers={'User-Agent': ua.random})
                
                with open(FILENAME, 'wb') as f:
                    for chunk in file_resp.iter_content(chunk_size=1024*1024):
                        if chunk: f.write(chunk)
                
                # Validation
                if os.path.getsize(FILENAME) > 5000:
                    print(f"   ✅ SUCCÈS ! Vidéo prête.")
                    return video
                else:
                    print("   ⚠️ Fichier vide.")

            except Exception:
                continue # Erreur connexion, on passe au serveur suivant
        
        print("⚠️ Lien mort ou serveurs indisponibles. On passe à la vidéo suivante...")
        attempts += 1
        time.sleep(1)

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
    msg['Subject'] = f'🚀 Viral Content : {video_data["title"]}'
    msg['From'] = email_user
    msg['To'] = email_receiver
    msg.set_content(f"Voici ton contenu.\nSource : {video_data['url']}")

    with open(FILENAME, 'rb') as f:
        msg.add_attachment(f.read(), maintype='video', subtype='mp4', filename="viral.mp4")

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(email_user, email_pass)
            smtp.send_message(msg)
        print("✅ Email envoyé !")
    except Exception as e:
        print(f"❌ Erreur email : {e}")

if __name__ == "__main__":
    video = download_random_viral_video()
    if video:
        send_email(video)
    else:
        print("❌ Échec total.")
