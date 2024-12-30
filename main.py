import discord
from discord.ext import tasks
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import os

# Récupération des variables d'environnement
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))
TIKTOK_USERNAME = os.getenv("TIKTOK_USERNAME")

# Configuration Chrome pour Selenium
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")

# Initialisation du client Discord
intents = discord.Intents.default()
client = discord.Client(intents=intents)

# Liste des vidéos déjà détectées
detected_videos = set()

# Fonction pour gérer la bannière de cookies
def handle_cookie_banner(driver):
    try:
        print("Vérification de la bannière de cookies...")
        cookie_banner = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'tiktok-cookie-banner'))
        )
        accept_button = cookie_banner.find_element(By.TAG_NAME, 'button')
        accept_button.click()
        print("Bannière de cookies fermée.")
    except Exception as e:
        print("Aucune bannière de cookies détectée ou déjà fermée.", e)

# Fonction pour récupérer les vidéos TikTok
def scrape_tiktok(username):
    try:
        print(f"Vérification des vidéos pour l'utilisateur : {username}")
        driver = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)
        driver.get(f"https://www.tiktok.com/@{username}")

        # Gérer la bannière de cookies si elle apparaît
        handle_cookie_banner(driver)

        # Attendre que la page charge
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))

        # Récupérer les liens des vidéos
        video_links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/video/"]')
        videos = [link.get_attribute("href") for link in video_links]

        driver.quit()
        return videos
    except Exception as e:
        print(f"Erreur lors du scraping TikTok : {e}")
        return []

# Tâche Discord pour surveiller TikTok toutes les minutes
@tasks.loop(minutes=1)
async def monitor_tiktok():
    global detected_videos
    videos = scrape_tiktok(TIKTOK_USERNAME)
    if not videos:
        print("Aucune nouvelle vidéo trouvée.")
        return

    # Filtrer les nouvelles vidéos
    new_videos = [video for video in videos if video not in detected_videos]
    detected_videos.update(new_videos)

    # Envoyer les nouvelles vidéos sur Discord
    if new_videos:
        channel = client.get_channel(DISCORD_CHANNEL_ID)
        if channel:
            for video in new_videos:
                await channel.send(f"📹 Nouvelle vidéo trouvée : {video}")
        else:
            print("Canal Discord introuvable.")

# Événement déclenché lorsque le bot est prêt
@client.event
async def on_ready():
    print(f"{client.user} est connecté et prêt.")
    channel = client.get_channel(DISCORD_CHANNEL_ID)
    if channel:
        await channel.send("✅ Le bot est démarré et surveille TikTok toutes les minutes.")
    monitor_tiktok.start()

# Lancer le bot Discord
client.run(DISCORD_TOKEN)
