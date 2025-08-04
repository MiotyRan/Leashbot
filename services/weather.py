import requests
import os
from dotenv import load_dotenv
import aiohttp

load_dotenv()

OPENWEATHER_API_KEY=os.getenv("OPENWEATHER_API_KEY")

async def get_weather(ville: str = None, lat: float = None, lon: float = None):
    try:

        if not OPENWEATHER_API_KEY:
            print("Clé API OpenWeahterMap manquante")
            return get_default_weather()
        # url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric&lang=fr"
        base_url =f"https://api.openweathermap.org/data/2.5/weather"

        if lat is not None and lon is not None:
            # Utiliser les coordonnées GPS
            url = f"{base_url}?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric&lang=fr"
            print(f"Appel API avec coordonnées: {lat}, {lon}")
        elif ville:
            # Utiliser le nom de la ville
            url = f"{base_url}?q={ville}&appid={OPENWEATHER_API_KEY}&units=metric&lang=fr"
            print(f"Appel API avec ville: {ville}")
        else:
            # Par défaut Paris
            url = f"{base_url}?q=Paris,FR&appid={OPENWEATHER_API_KEY}&units=metric&lang=fr"
            print("Appel API par défaut: Paris")
        
        # Appel API avec aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                print(f"Status API: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    city_name = data["name"]

                    if lat is not None and lon is not None:
                        if "country" in data.get("sys", {}):
                            city_name = f"{data['name']}, {data['sys']['country']}"
                    
                    print(f"Données reçues: {data['name']}, {data['main']['temp']}°C")
                                            
                    return {
                       "ville": city_name,
                        "temperature": round(data["main"]["temp"]),
                        "description": data["weather"][0]["description"].capitalize(),
                        "icone": f"fa-{get_weather_icon(data['weather'][0]['icon'])}"
                    }
                else:
                    print(f"Erreur API: {response.status}")
                    return get_default_weather()
    except Exception as e:
        print(f"Exception météo: {e}")
        return get_default_weather()
        
    #     response = requests.get(url)
    #     data = response.json()
    #     async with aiohttp.ClientSession() as session:
    #         async with session.get(url) as response:
    #             if response.status == 200:
    #                 data = await response.json()

    #     return {
    #         "ville" : data["name"],
    #         "temperature" : round(data["main"]["temp"]),
    #         "description" : data["weather"][0]["description"].capitalize(),
    #         "icone" : f"fa-{get_weather_icon(data['weather'][0]['icon'])}",
    #         "maree" : "Haute à 15h" # à voir plus tard
    #     }
    
    # except:
    #     return {
    #        "ville" : "Paris",
    #        "temperature" : "23",
    #        "description" :  "Ensoleillé",
    #        "icone" : "fa-sun",
    #        "maree" : "Haute à 15h"
    #     }

def get_weather_icon(icon_code):
    icon_map = {
        '01d': 'sun',             '01n': 'moon',
        '02d': 'cloud-sun',       '02n': 'cloud-moon',
        '03d': 'cloud',           '03n': 'cloud',
        '04d': 'cloud-meatball',  '04n': 'cloud-meatball',
        '09d': 'cloud-rain',      '09n': 'cloud-rain',
        '10d': 'umbrella',        '10n': 'umbrella',
        '11d': 'bolt',            '11n': 'bolt',
        '13d': 'snowflake',       '13n': 'snowflake',
        '50d': 'smog',            '50n': 'smog'
    }
    return icon_map.get(icon_code, icon_map.get(icon_code[:2], 'cloud'))

def get_default_weather():
    return {
        "ville" : "Paris",
           "temperature" : "23",
           "description" :  "Ensoleillé",
           "icone" : "fa-sun"
    }