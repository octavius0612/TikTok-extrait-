import os
import random
import requests
from fake_useragent import UserAgent
import google.generativeai as genai

# --- CONFIGURATION ---
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
VIDEO_FILENAME = "viral_video.mp4"
HTML_FILENAME = "index.html"

# --- IA ---
USE_AI = False
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        USE_AI = True
    except: pass

ARCHIVE_TOPICS = ["tiktok viral", "funny short", "motivation video", "sigma grindset"]

def get_ai_topic():
    if USE_AI:
        try:
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content("Donne-moi 1 mot-clé anglais pour chercher une vidéo virale sur Archive.org.")
            return response.text.strip()
        except: pass
    return random.choice(ARCHIVE_TOPICS)

def generate_caption_ai(title):
    if USE_AI:
        try:
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(f"Description TikTok pour '{title}'. 3 hashtags.")
            return response.text.strip()
        except: pass
    return f"Regarde ça ! 🔥 #viral"

# --- MOTEUR ---
def run_bot():
    print("🚀 Démarrage du bot...")
    topic = get_ai_topic()
    
    # 1. Recherche Archive.org
    print(f"📚 Recherche : {topic}")
    try:
        url = "https://archive.org/advancedsearch.php"
        params = {"q": f"{topic} AND mediatype:movies AND format:MPEG4", "fl[]": "identifier,title", "sort[]": "downloads desc", "rows": "15", "page": "1", "output": "json"}
        data = requests.get(url, params=params, timeout=10).json()
        docs = data['response']['docs']
        item = random.choice(docs)
        
        # Trouver le MP4
        meta = requests.get(f"https://archive.org/metadata/{item['identifier']}", timeout=10).json()
        mp4_url = None
        for f in meta['files']:
            if f['name'].lower().endswith('.mp4'):
                mp4_url = f"https://archive.org/download/{item['identifier']}/{f['name']}"
                break
        
        if not mp4_url:
            print("❌ Pas de MP4 trouvé.")
            return

        # 2. Téléchargement
        print(f"⬇️ Téléchargement : {mp4_url}")
        r = requests.get(mp4_url, stream=True, headers={"User-Agent": UserAgent().random})
        with open(VIDEO_FILENAME, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024*1024):
                if chunk: f.write(chunk)
        
        # 3. Génération IA
        caption = generate_caption_ai(item['title'])
        
        # 4. Création du fichier HTML (Le rapport)
        create_html_report(item['title'], caption, mp4_url)
        print("✅ SUCCÈS ! Vidéo et HTML générés.")

    except Exception as e:
        print(f"❌ Erreur : {e}")

def create_html_report(title, caption, source_url):
    html_content = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Résultat Viral</title>
        <style>
            body {{ background: #000; color: #fff; font-family: sans-serif; text-align: center; padding: 20px; }}
            .container {{ max-width: 400px; margin: 0 auto; border: 1px solid #333; padding: 20px; border-radius: 10px; }}
            h1 {{ color: #FE2C55; }}
            .caption {{ background: #222; padding: 10px; border-radius: 5px; text-align: left; font-family: monospace; margin: 15px 0; }}
            video {{ width: 100%; border-radius: 10px; }}
            a {{ color: #25F4EE; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>✅ VIDÉO TROUVÉE</h1>
            <h3>{title}</h3>
            
            <video controls>
                <source src="{VIDEO_FILENAME}" type="video/mp4">
                Ton navigateur ne supporte pas la vidéo.
            </video>

            <div class="caption">
                <strong>Description à copier :</strong><br><br>
                {caption}
            </div>

            <p><small>Source : <a href="{source_url}" target="_blank">Lien original</a></small></p>
        </div>
    </body>
    </html>
    """
    with open(HTML_FILENAME, "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    run_bot()


