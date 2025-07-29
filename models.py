from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class TeaserConfig(Base):
    """Configuration globale du module Teaser"""
    __tablename__ = "teaser_config"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True)  # ex: "weather_api_key", "carousel_speed"
    value = Column(Text)  # Valeur JSON ou texte
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class MediaContent(Base):
    """Contenu média pour les carrousels"""
    __tablename__ = "media_content"
    
    id = Column(Integer, primary_key=True, index=True)
    zone = Column(String(50), index=True)  # "left1", "left2", "left3", "center"
    type = Column(String(20))  # "image", "video", "url"
    filename = Column(String(255))  # nom fichier ou URL
    title = Column(String(255), nullable=True)
    order = Column(Integer, default=0)
    duration = Column(Integer, default=5)  # durée affichage en secondes
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Selfie(Base):
    """Photos selfie du module Selfie"""
    __tablename__ = "selfies"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), unique=True)
    client_name = Column(String(100), nullable=True)
    taken_at = Column(DateTime, default=datetime.utcnow)
    is_featured = Column(Boolean, default=False)  # Photo mise en avant
    path = Column(String(500))  # chemin complet vers le fichier

class Music(Base):
    """Musiques et playlist DJ/Jukebox"""
    __tablename__ = "music"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), index=True)
    artist = Column(String(255), nullable=True)
    filename = Column(String(255))
    duration = Column(Integer, nullable=True)  # en secondes
    client_request = Column(String(100), nullable=True)  # nom du client qui a demandé
    genre = Column(String(100), nullable=True)
    is_playing = Column(Boolean, default=False)
    play_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class Playlist(Base):
    """Playlist en cours"""
    __tablename__ = "playlist"
    
    id = Column(Integer, primary_key=True, index=True)
    music_id = Column(Integer, index=True)
    position = Column(Integer)  # ordre dans la playlist
    requested_by = Column(String(100), nullable=True)
    is_current = Column(Boolean, default=False)
    played = Column(Boolean, default=False)
    added_at = Column(DateTime, default=datetime.utcnow)

class WeatherData(Base):
    """Cache des données météo"""
    __tablename__ = "weather_data"
    
    id = Column(Integer, primary_key=True, index=True)
    location = Column(String(100), index=True)
    temperature = Column(Float)
    description = Column(String(255))
    humidity = Column(Integer)
    wind_speed = Column(Float)
    icon = Column(String(50))  # code icône météo
    fetched_at = Column(DateTime, default=datetime.utcnow)

class TideData(Base):
    """Cache des données de marée"""
    __tablename__ = "tide_data"
    
    id = Column(Integer, primary_key=True, index=True)
    location = Column(String(100), index=True)
    tide_type = Column(String(20))  # "high" ou "low"
    time = Column(DateTime)
    height = Column(Float)  # hauteur en mètres
    fetched_at = Column(DateTime, default=datetime.utcnow)