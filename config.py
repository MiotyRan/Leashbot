from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    """Configuration de l'application"""
    
    # API Météo (OpenWeatherMap)
    WEATHER_API_KEY: str = os.getenv("WEATHER_API_KEY", "YOUR_WEATHER_API_KEY")
    WEATHER_API_URL: str = "https://api.openweathermap.org/data/2.5/weather"
    WEATHER_LOCATION: str = "Biarritz,FR"
    WEATHER_REFRESH_INTERVAL: int = 300  # 5 minutes
    
    # API Marées
    TIDE_API_KEY: str = os.getenv("TIDE_API_KEY", "YOUR_TIDE_API_KEY")
    TIDE_API_URL: str = "https://api.worldtides.info/v2/heights"
    TIDE_LOCATION_LAT: float = 43.4832  # Biarritz latitude
    TIDE_LOCATION_LON: float = -1.5586  # Biarritz longitude
    TIDE_REFRESH_INTERVAL: int = 3600   # 1 heure
    
    # Chemins médias
    MEDIA_ROOT: str = "static/media"
    SELFIE_ROOT: str = "static/selfies"
    MUSIC_ROOT: str = "static/music"
    
    # Configuration carrousels
    DEFAULT_CAROUSEL_SPEED: int = 5  # secondes
    AUTO_PLAY_VIDEOS: bool = True
    VIDEO_VOLUME: float = 0.3
    
    # Nettoyage automatique
    AUTO_CLEANUP_ENABLED: bool = False
    CLEANUP_AFTER_DAYS: int = 30
    
    # Module DJ/Lecteur
    DJ_AUTO_NEXT: bool = True
    DJ_SHUFFLE_MODE: bool = False
    DJ_VOLUME: float = 0.7
    
    # Sécurité Admin
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "teaser2024"
    
    class Config:
        case_sensitive = True

settings = Settings()