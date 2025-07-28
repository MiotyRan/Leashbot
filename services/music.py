import requests
import random

DEEZER_API_URL = "https://api.deezer.com"

async def get_music():
    try:
        response = requests.get(f"{DEEZER_API_URL}/chart/0/tracks?limit=50")
        data = response.json()

        if 'data' in data:
            track = random.choice(data['data'])
            return {
                "titre" : track['title'],
                "artiste": track['artist']['name'],
                "cover": track['album']['cover_small'],
                "preview": track['preview']
            }
    except Exception as e:
        print (f"Erreur API Deezer : {e}")