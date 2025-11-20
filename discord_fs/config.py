import os

# Constants
BASE_URL = "https://discord.com/api/v9/channels/"
INDEX_FILE = "index.txt"
CHUNK_SIZE = 8 * 1000 * 1000  # Discord 8MB file limit

# Global configuration
CHANNEL_ID = ""
TOKEN = ""
CDN_BASE_URL = ""
HEADERS = {}

def load_config():
    global TOKEN, CHANNEL_ID, HEADERS, CDN_BASE_URL
    
    try:
        with open(".env", "r") as f:
            lines = f.readlines()
            for line in lines:
                if line.startswith("TOKEN="):
                    TOKEN = line.split("=")[1].strip()
                elif line.startswith("CHANNEL_ID="):
                    CHANNEL_ID = line.split("=")[1].strip()
    except (FileNotFoundError, IndexError):
        pass

    # If not found in .env, the caller is responsible for prompting or handling missing config.

    if TOKEN and CHANNEL_ID:
        HEADERS = {"Authorization": f"Bot {TOKEN}"}
        CDN_BASE_URL = f"https://cdn.discordapp.com/attachments/{CHANNEL_ID}/"

def save_config(token, channel_id):
    global TOKEN, CHANNEL_ID, HEADERS, CDN_BASE_URL
    TOKEN = token
    CHANNEL_ID = channel_id
    HEADERS = {"Authorization": f"Bot {TOKEN}"}
    CDN_BASE_URL = f"https://cdn.discordapp.com/attachments/{CHANNEL_ID}/"
    
    with open(".env", "w") as f:
        f.write(f"TOKEN={TOKEN}\nCHANNEL_ID={CHANNEL_ID}")
