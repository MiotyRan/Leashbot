from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import List
import uvicorn
import requests
from dotenv import load_dotenv
from services.weather import get_weather
from services.music import get_music

load_dotenv()
app = FastAPI()

# Configuration HTML
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/")
async def afficher_teaser(request: Request):
    # Récupération météo 
    meteo = await get_weather()

    # Récupération musique
    musique = await get_music()

    return templates.TemplateResponse("teaser.html", {
        "request": request,
        "data": {
            "meteo": meteo,
            "musique": musique,
            "cocktail": {
                "nom": "Mojito IA",
                "description": "Rhum, menthe, citron vert",
                "image": "cocktail.jpg"
            }
        }
    })


# Route pour l'API meteo
@app.get("/api/meteo")
async def api_meteo(ville: str = None, lat: float = None, lon: float = None):
    print(f"API météo appelée avec: lat={lat}, lon={lon}, ville={ville}")
    meteo = await get_weather(ville=ville, lat=lat, lon=lon)
    return meteo

# Route pour l'API musique
@app.get("/api/musique/now-playing")
async def api_music():
    music = await get_music()
    return music

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)