from fastapi import APIRouter, Request, HTTPException, File, UploadFile, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, FileResponse
from typing import List, Dict, Any
import json
import uuid
import requests
from pathlib import Path
from datetime import datetime, timedelta

from pathlib import Path
import aiofiles

# Import de vos services existants
from services.config_service import ConfigService, config_service
from services.file_manager import file_manager
from services.selfie_service import selfie_service

def ensure_media_directories():
    """Créer les dossiers de médias s'ils n'existent pas"""
    media_zones = ['left1', 'left2', 'left3', 'center']
    
    for zone in media_zones:
        zone_dir = Path(f"static/media/{zone}")
        zone_dir.mkdir(parents=True, exist_ok=True)
        print(f"Dossier créé/vérifié: {zone_dir}")

# Appeler cette fonction
ensure_media_directories()

# Créer le routeur pour l'administration
router = APIRouter(prefix="/api/admin", tags=["admin"])
templates = Jinja2Templates(directory="templates")

# ===== PAGE D'ADMINISTRATION =====

@router.get("/teaser")
async def admin_teaser_page(request: Request):
    """Page d'administration du TEASER"""
    return templates.TemplateResponse("admin.html", {"request": request})

# ===== CONFIGURATION COMPLETE =====

@router.get("/config")
async def get_admin_config():
    """Récupérer la configuration complète via ConfigService"""
    try:
        # Service de configuration (sans DB pour le moment)
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

# ===== GESTION DES ZONES =====

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
        
        # Configuration par défaut 
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

# ===== GESTION DES MEDIAS VIA FILE_MANAGER =====

@router.post("/upload")
async def upload_media_files(files: List[UploadFile] = File(...), zone: str = Form(...)):
    # Upload de fichier avec support ammélioré
    try:
        # Gérer le cas où zone = modal (depuis la modale admin)
        if zone == "modal":
            zone = "center"

        if zone not in ["left1", "left2", "left3", "center"]:
            raise HTTPException(status_code=400, detail="Zone invalide")
        
        print(f"Upload reçu: {len(files)} fichiers pour zone {zone}")

        # Créer le dossier de destination
        zone_dir = Path(f"static/media/{zone}")
        zone_dir.mkdir(parents=True, exist_ok=True)
        print(f"Dossier créé/vérifié: {zone_dir}")

        uploaded_files = []
        for file in files:
            print(f"Traitement fichier: {file.filename}, Type: {file.content_type}")
            # Validation du type de fichier
            allowed_types = [
                'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp',
                'video/mp4', 'video/webm', 'video/mov', 'video/avi'
            ]

            if file.content_type not in allowed_types:
                print(f"Type de fichier non supporté: {file.content_type}")
                continue

            # Validation de la taille (50MB max)
            filename = file.filename
            file_path = zone_dir / filename

            # Si le fichier existe déjà, ajouter un timestamp
            if file_path.exists():
                name, ext = filename.rsplit('.', 1)
                filename = f"{name}_{int(datetime.now().timestamp())}.{ext}"
                file_path = zone_dir / filename

            # Sauvegarder le fichier
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            print(f"Fichier sauvé: {file_path}")
            uploaded_files.append({
                "filename": filename,
                "original_name": file.filename,
                "path": f"/static/media/{zone}/{filename}",
                "zone": zone,
                "type": "image" if file.content_type.startswith('image/') else "video"
            })

        if not uploaded_files:
            return JSONResponse(content={
                "success": False,
                "message": "Aucun fichier valide n'a pu être uploadé"
            })
        
        return JSONResponse(content={
            "success": True,
            "message": f"{len(uploaded_files)} fichier(s) uploadé(s) avec succès",
            "uploaded_count": len(uploaded_files),
            "files": uploaded_files
        })
        
    except Exception as e:
        print(f"ERREUR UPLOAD: {str(e)}")
        return JSONResponse(content={
            "success": False,
            "message": f"Erreur d'upload: {str(e)}"
        }, status_code=500)
    
# Route pour lister les medias d'une zone
@router.get("/media/{zone}")
async def get_zone_media(zone: str):
    """Récupérer les médias d'une zone pour l'admin"""
    try:
        zone_path = Path(f"static/media/{zone}")
        if not zone_path.exists():
            return JSONResponse(content={"zone": zone, "content": []})
        
        files = []
        for file_path in zone_path.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.mp4', '.webm', '.webp', '.mov']:
                # Déterminer le type de fichier
                file_type = "image" if file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.webp'] else "video"
                files.append({
                    "id": hash(file_path.name),
                    "filename": file_path.name,
                    "src": f"/static/media/{zone}/{file_path.name}",
                    "path": f"/static/media/{zone}/{file_path.name}",
                    "size": file_path.stat().st_size,
                    # "type": "image" if file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif'] else "video"
                    "type": file_type,
                    "created_at": datetime.fromtimestamp(file_path.stat().st_ctime).isoformat()
                })

        # Trier par date de création : plus récent d'abord
        files.sort(key=lambda x: x['created_at'], reverse=True)
        
        print(f"API retourne pour {zone}: {len(files)} fichiers")  # DEBUG
        return JSONResponse(content={"zone": zone, "content": files})
        
    except Exception as e:
        print(f"Erreur API {zone}: {str(e)}")  # DEBUG
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@router.delete("/media/{zone}/{item_id}")
async def delete_media_item(zone: str, item_id: int):
    # Supprimer média via FileManager
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
    
@router.post("/upload")


# ===== TESTS DES APIs =====

@router.post("/test-weather")
async def test_weather_api_connection(api_data: dict):
    try:
        # api_key = api_data.get("api_key")
        location = api_data.get("location", "Paris,FR")

        from services.weather import get_weather

        result = await get_weather(ville=location)

        if not result or not result.get('ville') or result.get('ville') == 'None':
            raise ValueError("Données météo invalides reçues")
        
        return JSONResponse(content={
            "success": True,
            "message": f"Méteo récupérée pour {result['ville']}",
            "data": {
                "location": result["ville"],
                "temperature": f"{result['temperature']}°C",
                "description": result["description"],
                "icon": result["icone"],
                "full_data": result  # Toutes les données pour l'affichage
            }
        })
        
        # if not api_key or not location:
        #     raise HTTPException(status_code=400, detail="Clé API et localisation requis")
        
        # Test OpenWeatherMap
        # url = f"https://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}&units=metric&lang=fr"
        # response = requests.get(url, timeout=5)
        
        # if response.status_code == 200:
        #     data = response.json()
        #     return JSONResponse(content={
        #         "success": True,
        #         "message": "API Météo OpenWeatherMap connectée",
        #         "data": {
        #             "location": data.get("name"),
        #             "temperature": data["main"]["temp"],
        #             "description": data["weather"][0]["description"],
        #         }
        #     })
        # else:
        #     raise HTTPException(status_code=400, detail=f"Erreur API météo: {response.status_code}")
    # except Exception as e:
    #     raise HTTPException(status_code=500, detail=f"Erreur test météo: {str(e)}")
    except Exception as e:
        error_message = str(e)
        print(f"Erreur de test météo: {error_message}")

        return JSONResponse(content={
            "success": False,
            "message": f"Erreur météo: {error_message}",
            "details": "Vérifiez votre clé APi ou la connéctivité réseau"
        }, status_code=400)

@router.post("/test-tide")
async def test_tide_api_connection(api_data: dict):
    try:
        # api_key = api_data.get("api_key")
        lat = float(api_data.get("lat", 43.4832))
        lon = float(api_data.get("lon", -1.5586))

        from services.tide import get_tide_data
        result = await get_tide_data(lat=lat, lon=lon)

        return JSONResponse(content={
            "success": True,
            "message": f"Marées récupérées pour {lat:.4f}, {lon:.4f}",
            "data": {
                 "lat": lat,
                "lon": lon,
                "tide_type": result.get("type", "haute"),
                "tide_time": result.get("time", "15h30"),
                "tide_text": result.get("text", "Marée haute à 15h30"),
                "full_data": result  # Toutes les donnees pour l'affichage
            }
        })
        
        # if not api_key or lat is None or lon is None:
        #     raise HTTPException(status_code=400, detail="Tous les paramètres requis")
        
        # Simulation test marées (remplacer par vraie API)
    #     return JSONResponse(content={
    #         "success": True,
    #         "message": "API Marées connectée",
    #         "data": {
    #             "lat": lat, 
    #             "lon": lon,
    #             "next_tide": "Marée haute à 15h30"
    #         }
    #     })
    # except Exception as e:
    #     raise HTTPException(status_code=500, detail=f"Erreur test marées: {str(e)}")
    except Exception as e:
        return JSONResponse(content={
            "success": False,
            "message": f"Erreur marées: {str(e)}"
        })

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

# ===== STATISTIQUES =====

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
    
@router.get("/stats/dashboard")
async def get_dashboard_stats():
    try:
        stats = {
            "medias": 0,
            "selfies": 0,
            "pistes": 0,
            "storage_mb": 0
        }

        # 1- Compter les medias dans toutes les zones
        zones = ['left1', 'left2', 'left3', 'center']
        total_files = 0
        total_size = 0

        for zone in zones:
            zone_path = Path(f"static/media/{zone}")
            if zone_path.exists():
                for file_path in zone_path.iterdir():
                    if file_path.is_file() and file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.mp4', '.webm', '.webp', '.mov']:
                        total_files += 1
                        total_size += file_path.stat().st_size

        stats["medias"] = total_files
        stats["storage_mb"] = round(total_size / (1024 * 1024), 1)  # Convertir en MB

        # 2- Compter les selfies
        selfies_path = Path("/static/selfies")
        if selfies_path.exists():
            selfies_count = len([f for f in selfies_path.iterdir() 
                               if f.is_file() and f.suffix.lower() in ['.jpg', '.jpeg', '.png']])
            stats["selfies"] = selfies_count

        return JSONResponse(content={
            "success": True,
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        return JSONResponse(content={
            "success": False,
            "error": str(e),
            "stats": {
                "medias": 0,
                "selfies": 0, 
                "pistes": 0,
                "storage_mb": 0
            }
        })