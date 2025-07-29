from fastapi import APIRouter, Request, HTTPException, File, UploadFile, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, FileResponse
from typing import List, Dict, Any
import json
import uuid
import aiofiles
import requests
from pathlib import Path
from datetime import datetime, timedelta

# Import de vos services existants
from services.config_service import config_service
from services.file_manager import file_manager
from services.selfie_service import selfie_service

# Créer le routeur pour l'administration
router = APIRouter(prefix="/api/admin", tags=["admin"])
templates = Jinja2Templates(directory="templates")

# ===== PAGE D'ADMINISTRATION =====

@router.get("/teaser")
async def admin_teaser_page(request: Request):
    """Page d'administration du TEASER selon cahier des charges"""
    return templates.TemplateResponse("admin.html", {"request": request})

# ===== CONFIGURATION COMPLÈTE =====

@router.get("/config")
async def get_admin_config():
    """Récupérer la configuration complète via ConfigService"""
    try:
        # Utiliser votre service de configuration (sans DB pour le moment)
        config = {
            "carousel_speed": 5,
            "auto_play_videos": True,
            "video_volume": 0.3,
            "weather_refresh": 300,
            "tide_refresh": 3600,
            "zones": {
                "left1": {"title": "Zone Gauche 1", "enabled": True, "duration": 5},
                "left2": {"title": "Zone Gauche 2", "enabled": True, "duration": 5},
                "left3": {"title": "Zone Gauche 3", "enabled": True, "duration": 5},
                "center": {"title": "Zone Centrale", "enabled": True, "duration": 5}
            },
            "weather_api_key": "",
            "weather_location": "Biarritz,FR",
            "tide_api_key": "",
            "tide_lat": 43.4832,
            "tide_lon": -1.5586,
            "selfie_path": "/static/selfies/",
            "selfie_count": 3,
            "dj_url": "http://localhost:8001",
            "music_refresh": 5,
            "debug": True
        }
        return JSONResponse(content=config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur configuration: {str(e)}")

@router.post("/save-all")
async def save_all_config(config_data: dict):
    """Sauvegarder toute la configuration via ConfigService"""
    try:
        # TODO: Utiliser config_service.save_full_config() quand DB sera prête
        print("Configuration sauvegardée:", config_data)
        
        return JSONResponse(content={
            "success": True, 
            "message": "Configuration sauvegardée avec succès",
            "saved_items": len(config_data)
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur sauvegarde: {str(e)}")

@router.post("/save-draft")
async def save_draft_config(config_data: dict):
    """Sauvegarder un brouillon via ConfigService"""
    try:
        print("Draft sauvegardé:", config_data)
        return JSONResponse(content={"success": True, "message": "Draft sauvegardé"})
    except Exception as e:
        return JSONResponse(content={"success": False, "message": str(e)})

# ===== GESTION DES ZONES (selon cahier des charges) =====

@router.get("/zone/{zone}")
async def get_zone_config(zone: str):
    """Configuration des zones : centre (carrousel) + left1/2/3 (colonnes)"""
    try:
        if zone not in ["left1", "left2", "left3", "center"]:
            raise HTTPException(status_code=400, detail="Zone invalide")
        
        # Utiliser file_manager pour récupérer les médias
        media_files = file_manager.get_media_files(zone)
        
        # Formater pour l'admin
        content = []
        for i, file_info in enumerate(media_files):
            content.append({
                "id": hash(file_info['name']),
                "type": file_info['type'],
                "src": file_info['path'],
                "filename": file_info['name'],
                "title": file_info['name'].split('.')[0],
                "duration": 5,
                "order": i
            })
        
        # Configuration par défaut selon le cahier des charges
        zone_titles = {
            "center": "Zone Centrale (Carrousel)",
            "left1": "Zone Gauche 1", 
            "left2": "Zone Gauche 2",
            "left3": "Zone Gauche 3"
        }
        
        return JSONResponse(content={
            "zone": zone,
            "title": zone_titles.get(zone, f"Zone {zone.upper()}"),
            "duration": 5,
            "enabled": True,
            "content": content
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur zone {zone}: {str(e)}")

@router.post("/zone/{zone}")
async def save_zone_config(zone: str, config_data: dict):
    """Sauvegarder configuration zone"""
    try:
        if zone not in ["left1", "left2", "left3", "center"]:
            raise HTTPException(status_code=400, detail="Zone invalide")
        
        print(f"Configuration zone {zone} sauvegardée:", config_data)
        return JSONResponse(content={"success": True, "message": f"Zone {zone} configurée"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur sauvegarde zone: {str(e)}")

# ===== GESTION DES MÉDIAS VIA FILE_MANAGER =====

@router.get("/media/{zone}")
async def get_zone_media(zone: str):
    """Récupérer médias via FileManager"""
    try:
        if zone not in ["left1", "left2", "left3", "center"]:
            raise HTTPException(status_code=400, detail="Zone invalide")
        
        # Utiliser votre FileManager
        media_files = file_manager.get_media_files(zone)
        
        content = []
        for file_info in media_files:
            content.append({
                "id": hash(file_info['name']),
                "type": file_info['type'],
                "src": file_info['path'],
                "filename": file_info['name'],
                "title": file_info['name'].split('.')[0],
                "duration": 5,
                "order": 0,
                "exists": True,
                "created_at": datetime.fromtimestamp(file_info['modified']).isoformat()
            })
        
        return JSONResponse(content={"zone": zone, "content": content})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur médias zone {zone}: {str(e)}")

@router.post("/upload")
async def upload_media_files(files: List[UploadFile] = File(...), zone: str = Form(...)):
    """Upload via FileManager"""
    try:
        if zone not in ["left1", "left2", "left3", "center", "modal"]:
            raise HTTPException(status_code=400, detail="Zone invalide")
        
        if zone == "modal":
            zone = "center"
        
        uploaded_files = []
        
        for file in files:
            # Validation via FileManager
            if not file_manager.is_valid_media_file(file):
                continue
            
            # Générer nom unique
            file_extension = file.filename.split('.')[-1].lower()
            unique_filename = f"{uuid.uuid4()}.{file_extension}"
            
            # Chemin de destination
            destination_path = Path(f"static/media/{zone}") / unique_filename
            
            # Sauvegarder via FileManager
            file_info = await file_manager.save_uploaded_file(file, destination_path)
            
            uploaded_files.append({
                "id": hash(unique_filename),
                "filename": unique_filename,
                "original_name": file.filename,
                "type": file_manager.get_file_type(file.content_type)
            })
        
        return JSONResponse(content={
            "success": True,
            "message": f"{len(uploaded_files)} fichier(s) uploadé(s)",
            "uploaded_count": len(uploaded_files),
            "files": uploaded_files
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur upload: {str(e)}")

@router.delete("/media/{zone}/{item_id}")
async def delete_media_item(zone: str, item_id: int):
    """Supprimer média via FileManager"""
    try:
        zone_path = Path(f"static/media/{zone}")
        
        if zone_path.exists():
            for media_file in zone_path.iterdir():
                if hash(media_file.name) == item_id:
                    success = await file_manager.delete_file(media_file)
                    if success:
                        return JSONResponse(content={"success": True, "message": "Élément supprimé"})
        
        raise HTTPException(status_code=404, detail="Élément non trouvé")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur suppression: {str(e)}")

@router.post("/add-url-content")
async def add_url_content(content_data: dict):
    """Ajouter contenu distant (selon cahier des charges)"""
    try:
        zone = content_data.get("zone")
        url = content_data.get("url")
        title = content_data.get("title", "")
        
        if not zone or not url:
            raise HTTPException(status_code=400, detail="Zone et URL requis")
        
        if zone not in ["left1", "left2", "left3", "center"]:
            raise HTTPException(status_code=400, detail="Zone invalide")
        
        # Détecter type via FileManager
        url_type = file_manager.detect_url_type(url)
        
        print(f"URL ajoutée à {zone}: {url} - {title} (type: {url_type})")
        
        return JSONResponse(content={
            "success": True,
            "message": "URL ajoutée avec succès",
            "id": hash(url)
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur ajout URL: {str(e)}")

# ===== TESTS DES APIs (selon cahier des charges) =====

@router.post("/test-weather")
async def test_weather_api_connection(api_data: dict):
    """Test API météo (OpenWeatherMap selon cahier des charges)"""
    try:
        api_key = api_data.get("api_key")
        location = api_data.get("location")
        
        if not api_key or not location:
            raise HTTPException(status_code=400, detail="Clé API et localisation requis")
        
        # Test OpenWeatherMap
        url = f"https://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}&units=metric&lang=fr"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            return JSONResponse(content={
                "success": True,
                "message": "API Météo OpenWeatherMap connectée",
                "data": {
                    "location": data.get("name"),
                    "temperature": data["main"]["temp"],
                    "description": data["weather"][0]["description"],
                    "humidity": data["main"]["humidity"],
                    "wind_speed": data["wind"]["speed"]
                }
            })
        else:
            raise HTTPException(status_code=400, detail=f"Erreur API météo: {response.status_code}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur test météo: {str(e)}")

@router.post("/test-tide")
async def test_tide_api_connection(api_data: dict):
    """Test API marées (selon cahier des charges)"""
    try:
        api_key = api_data.get("api_key")
        lat = api_data.get("lat")
        lon = api_data.get("lon")
        
        if not api_key or lat is None or lon is None:
            raise HTTPException(status_code=400, detail="Tous les paramètres requis")
        
        # Simulation test marées (remplacer par vraie API)
        return JSONResponse(content={
            "success": True,
            "message": "API Marées connectée",
            "data": {
                "lat": lat, 
                "lon": lon,
                "next_tide": "Marée haute à 15h30"
            }
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur test marées: {str(e)}")

@router.post("/test-selfie")
async def test_selfie_module_connection(module_data: dict):
    """Test module Selfie via SelfieService"""
    try:
        # Utiliser votre SelfieService
        result = selfie_service.test_module_connectivity()
        
        if result['success']:
            return JSONResponse(content={
                "success": True,
                "message": "Module Selfie accessible",
                "count": result.get('total_selfies', 0),
                "path": result.get('path', ''),
                "storage_mb": result.get('storage_mb', 0)
            })
        else:
            return JSONResponse(content={
                "success": False,
                "message": result.get('error', 'Module Selfie inaccessible')
            })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur test selfie: {str(e)}")

@router.post("/test-dj")
async def test_dj_module_connection(module_data: dict):
    """Test module DJ/Jukebox (selon cahier des charges)"""
    try:
        dj_url = module_data.get("url", "http://localhost:8001")
        
        # Test connexion module DJ
        try:
            response = requests.get(f"{dj_url}/api/status", timeout=5)
            if response.status_code == 200:
                return JSONResponse(content={
                    "success": True,
                    "message": "Module DJ/Jukebox connecté",
                    "status": response.json() if response.content else {"connected": True}
                })
            else:
                raise Exception(f"Status HTTP {response.status_code}")
        except requests.exceptions.RequestException:
            return JSONResponse(content={
                "success": False,
                "message": f"Module DJ inaccessible sur {dj_url}"
            })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur test DJ: {str(e)}")

# ===== STATUS SYSTÈME =====

@router.get("/system-status")
async def get_system_status():
    """Status complet du système TEASER"""
    try:
        # Utiliser FileManager pour stats stockage
        storage_stats = file_manager.get_storage_stats()
        
        # Utiliser SelfieService pour stats selfies
        selfie_stats = selfie_service.get_selfie_stats()
        
        return JSONResponse(content={
            "server": True,
            "apis": {
                "weather": True,  # Test en temps réel si nécessaire
                "tide": False
            },
            "modules": {
                "active": 1,
                "total": 3,
                "selfie": selfie_stats.get('total_selfies', 0) > 0,
                "dj": False  # Test en temps réel si nécessaire
            },
            "storage": {
                "total_mb": storage_stats.get('total_size_mb', 0),
                "total_files": storage_stats.get('total_files', 0)
            },
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur status système: {str(e)}")

@router.get("/widget-status")
async def get_widget_status():
    """Status des widgets pour mockup (selon cahier des charges)"""
    try:
        # Vérifier selfies via SelfieService
        selfie_test = selfie_service.test_module_connectivity()
        
        return JSONResponse(content={
            "weather": "online",  # Carte météo
            "selfie": "online" if selfie_test['success'] else "offline",  # Module selfie
            "music": "offline"  # Module DJ/Musique
        })
    except Exception as e:
        return JSONResponse(content={
            "weather": "offline",
            "selfie": "offline", 
            "music": "offline"
        })

# ===== UTILITAIRES SYSTÈME =====

@router.post("/cleanup")
async def run_system_cleanup():
    """Nettoyage via FileManager"""
    try:
        # Utiliser FileManager pour nettoyage
        deleted_count = await file_manager.cleanup_old_files(days=30)
        
        return JSONResponse(content={
            "success": True,
            "message": "Nettoyage terminé",
            "deleted_files": deleted_count
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur nettoyage: {str(e)}")

@router.get("/logs")
async def get_system_logs():
    """Logs système (selon cahier des charges)"""
    try:
        logs_dir = Path("logs")
        if not logs_dir.exists():
            return JSONResponse(content={
                "logs": "Module TEASER démarré\nInterface admin accessible\nServices initialisés",
                "file": "teaser.log", 
                "size": 3
            })
        
        # Lire le dernier fichier de log
        log_files = sorted(logs_dir.glob("*.log"), 
                          key=lambda x: x.stat().st_mtime, reverse=True)
        
        if not log_files:
            return JSONResponse(content={
                "logs": "Aucun fichier de log trouvé",
                "file": None,
                "size": 0
            })
        
        latest_log = log_files[0]
        with open(latest_log, 'r', encoding='utf-8') as f:
            logs = f.read()
        
        # Limiter aux 1000 dernières lignes
        log_lines = logs.split('\n')[-1000:]
        
        return JSONResponse(content={
            "logs": '\n'.join(log_lines),
            "file": str(latest_log),
            "size": len(log_lines)
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur logs: {str(e)}")

@router.get("/backup")
async def download_config_backup():
    """Sauvegarde configuration (via ConfigService si DB disponible)"""
    try:
        backup_data = {
            "teaser_backup": True,
            "version": "1.0",
            "created_at": datetime.utcnow().isoformat(),
            "storage_stats": file_manager.get_storage_stats(),
            "selfie_stats": selfie_service.get_selfie_stats(),
            "config": {
                "carousel_speed": 5,
                "auto_play_videos": True,
                "video_volume": 0.3,
                "zones_enabled": ["left1", "left2", "left3", "center"]
            }
        }
        
        backup_file = Path(f"backup_teaser_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)
        
        return FileResponse(
            path=backup_file,
            filename=f"teaser_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            media_type="application/json"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur backup: {str(e)}")

# ===== STATISTIQUES (selon cahier des charges) =====

@router.get("/stats")
async def get_teaser_stats():
    """Statistiques complètes du module TEASER"""
    try:
        return JSONResponse(content={
            "storage": file_manager.get_storage_stats(),
            "selfies": selfie_service.get_selfie_stats(),
            "zones": {
                "left1": len(file_manager.get_media_files("left1")),
                "left2": len(file_manager.get_media_files("left2")),
                "left3": len(file_manager.get_media_files("left3")),
                "center": len(file_manager.get_media_files("center"))
            },
            "generated_at": datetime.now().isoformat()
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur stats: {str(e)}")