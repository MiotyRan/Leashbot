import requests
from datetime import datetime
import json

async def get_tide_data(lat: float = None, lon: float = None):
    try:
        if lat and lon:
            url = "https://www.worldtides.info/api/v3"
            params = {
                "lat": lat,
                "lon": lon,
                "length": 86400, # 24heures
                "datum": "LAT"
            }

            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return format_real_tide_data(data)
            else:
                print(f"Erreur API: {response.status_code}")
                return get_fallback_tide_data(lat, lon)
        else:
            return get_fallback_tide_data()
        
    except Exception as e:
        print(f"Erreur lors de la récupération des marées: {e}")
        return get_fallback_tide_data(lat, lon)
    
def format_real_tide_data(data):
    try:
        extremes = data.get("extremes", [])
        if not extremes:
            return get_fallback_tide_data()
        now = datetime.now()
        for extreme in extremes:
            tide_time = datetime.fromtimestamp(extreme["dt"])

            if tide_time > now:
                tide_type = "haute" if extreme["type"] == "High" else "basse"
                time_str = tide_time.strftime("%Hh%M")

                return {
                    "type": tide_type,
                    "time": time_str,
                    "text": f"Marée {tide_type} à {time_str}"
                }
        return get_fallback_tide_data()
    except Exception as e:
        print(f"Erreur formatage: {e}")
        return get_fallback_tide_data()
        
def get_fallback_tide_data(lat=None, lon=None):
    now = datetime.now()
    current_hour = now.hour

    hour_offset = 0
    if lat and lon:
        if -5 < lon < 5 and 42 < lat < 51:
            hour_offset = int(lon*0.5)

    tide_times = [
        (6 + hour_offset) % 24, # marée haute matin 
        (18 + hour_offset) % 24 # marée haute soir
    ] 

    for tide_hour in tide_times:
        if current_hour < tide_hour:
            return {
                "type": "haute",
                "time": f"{tide_hour:02d}h30",
                "text": f"Marée haute à {tide_hour:02d}h30"
            }
        
    next_tide = tide_times[0]
    return {
        "type": "haute", 
        "time": f"{next_tide:02d}h30",
        "text": f"Marée haute à {next_tide:02d}h30"
    }