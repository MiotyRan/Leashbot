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
import asyncio
import urllib.parse
import mimetypes
from PIL import Image
import io
import math

# Import de vos services existants
from services.config_service import ConfigService, config_service
from services.file_manager import file_manager
from services.selfie_service import selfie_service

def count_files_for_date(target_date):
    """Fonction helper pour compter les fichiers d'une date donnée"""
    daily_count = 0
    zones = ['left1', 'left2', 'left3', 'center']
    
    for zone in zones:
        zone_path = Path(f"static/media/{zone}")
        if zone_path.exists():
            for file_path in zone_path.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.mp4', '.webm', '.webp', '.mov']:
                    file_date = datetime.fromtimestamp(file_path.stat().st_ctime)
                    if file_date.date() == target_date.date():
                        daily_count += 1
    
    return daily_count

# Calcul arrondi de la taille MB
def custom_roun_mb(size_mb):
    decimal_part = size_mb - math.floor(size_mb)
    if decimal_part >= 0.55:
        return math.ceil(size_mb)
    else:
        return math.floor(size_mb)

# ACTIVITES RECENTES
class SimpleActivityLog:
    def __init__(self):
        self.log_file = Path("logs/admin_activity.json")
        self.log_file.parent.mkdir(exist_ok=True)
        
    def add(self, activity_type: str, message: str, details: str = None, size_mb: float = None):
        """Ajouter une activité avec plus de détails"""
        try:
            activity = {
                "id": str(uuid.uuid4())[:8],
                "type": activity_type,
                "message": message,
                "details": details,
                "size_mb": round(size_mb, 2) if size_mb else None,
                "timestamp": datetime.now().isoformat(),
                "time_ago": self._calculate_time_ago(datetime.now())
            }
            
            # Lire activités existantes
            activities = self._load_activities()
            
            # Ajouter nouvelle activité au début
            activities.insert(0, activity)
            
            # Garder seulement les 100 dernières
            activities = activities[:100]
            
            # Sauvegarder
            self._save_activities(activities)
                
            print(f"📝 {message}")
        except Exception as e:
            print(f"Erreur log activité: {e}")
    
    def get_recent_activities(self, limit: int = 20):
        """Récupérer les activités récentes avec formatage pour l'UI"""
        try:
            activities = self._load_activities()
            
            # Mettre à jour les temps relatifs
            for activity in activities:
                if 'timestamp' in activity:
                    timestamp = datetime.fromisoformat(activity['timestamp'])
                    activity['time_ago'] = self._calculate_time_ago(timestamp)
                    activity['icon'], activity['bg'] = self._get_activity_style(activity['type'])
                    activity['description'] = activity['message']
            
            return activities[:limit]
        except Exception as e:
            print(f"Erreur récupération activités: {e}")
            return []
    
    def _load_activities(self):
        """Charger les activités depuis le fichier"""
        if self.log_file.exists():
            try:
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def _save_activities(self, activities):
        """Sauvegarder les activités dans le fichier"""
        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump(activities, f, indent=2, ensure_ascii=False)
    
    def _calculate_time_ago(self, timestamp):
        """Calculer le temps écoulé en français"""
        now = datetime.now()
        diff = now - timestamp
        
        if diff.days > 0:
            return f"Il y a {diff.days} jour{'s' if diff.days > 1 else ''}"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"Il y a {hours} heure{'s' if hours > 1 else ''}"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"Il y a {minutes} minute{'s' if minutes > 1 else ''}"
        else:
            return "À l'instant"
    
    def _get_activity_style(self, activity_type):
        """Retourner l'icône et le style pour chaque type d'activité"""
        styles = {
            "upload": ("fas fa-upload text-blue-600", "bg-blue-100 dark:bg-blue-900/30"),
            "config": ("fas fa-cog text-gray-600", "bg-gray-100 dark:bg-gray-700"),
            "api_test": ("fas fa-vial text-purple-600", "bg-purple-100 dark:bg-purple-900/30"),
            "cleanup": ("fas fa-broom text-orange-600", "bg-orange-100 dark:bg-orange-900/30"),
            "backup": ("fas fa-download text-green-600", "bg-green-100 dark:bg-green-900/30"),
            "error": ("fas fa-exclamation-circle text-red-600", "bg-red-100 dark:bg-red-900/30"),
            "system": ("fas fa-server text-indigo-600", "bg-indigo-100 dark:bg-indigo-900/30"),
            "media": ("fas fa-images text-cyan-600", "bg-cyan-100 dark:bg-cyan-900/30"),
            "selfie": ("fas fa-camera text-pink-600", "bg-pink-100 dark:bg-pink-900/30")
        }
        return styles.get(activity_type, ("fas fa-info-circle text-gray-600", "bg-gray-100 dark:bg-gray-700"))

activity_log = SimpleActivityLog()

def log_startup_activity():
    """Enregistrer l'activité de démarrage"""
    activity_log.add(
        "system",
        "Module TEASER démarré",
        f"Interface admin accessible sur {datetime.now().strftime('%H:%M')}"
    )
# Appel à la fonction
log_startup_activity()

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

        activity_log.add(
            "config", 
            "Configuration système sauvegardée", 
            f"{len(config_data)} paramètres mis à jour"
        )
        
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
        total_size_bytes = 0

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
        
        # Enregistrer l'activité avec la taille totale
        total_size_mb = total_size_bytes / (1024 * 1024)
        file_types = list(set(f['type'] for f in uploaded_files))
        
        activity_log.add(
            "upload", 
            f"Upload de {len(uploaded_files)} fichier(s) dans {zone.upper()}", 
            f"Types: {', '.join(file_types)}", 
            total_size_mb
        )
        
        return JSONResponse(content={
            "success": True,
            "message": f"{len(uploaded_files)} fichier(s) uploadé(s) avec succès",
            "uploaded_count": len(uploaded_files),
            "files": uploaded_files
        })
        
    except Exception as e:
        activity_log.add("error", f"Erreur upload dans {zone}", str(e))
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
            if file_path.is_file():
                # Médias classiques
                if file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.mp4', '.webm', '.webp', '.mov']:
                    file_type = "image" if file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.webp'] else "video"
                    files.append({
                        "id": hash(file_path.name),
                        "filename": file_path.name,
                        "src": f"/static/media/{zone}/{file_path.name}",
                        "path": f"/static/media/{zone}/{file_path.name}",
                        "size": file_path.stat().st_size,
                        "type": file_type,
                        "created_at": datetime.fromtimestamp(file_path.stat().st_ctime).isoformat()
                    })
                
                # URLs distantes (fichiers .json)
                elif file_path.suffix.lower() == '.json' and file_path.name.startswith('url_'):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            url_data = json.load(f)
                        
                        files.append({
                            "id": hash(file_path.name),
                            "filename": url_data.get("title", "URL distante"),
                            "src": url_data.get("url", ""),
                            "path": url_data.get("url", ""),
                            "size": file_path.stat().st_size,
                            "type": "url",
                            "url": url_data.get("url", ""),
                            "created_at": url_data.get("created_at", datetime.fromtimestamp(file_path.stat().st_ctime).isoformat())
                        })
                    except:
                        continue

        # Trier par date de création : plus récent d'abord
        files.sort(key=lambda x: x['created_at'], reverse=True)
        
        return JSONResponse(content={"zone": zone, "content": files})
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")
    
@router.delete("/media/{zone}/{filename}")
async def delete_media_item(zone: str, filename: str):
    try:
        # Décoder le nom de fichier
        filename = urllib.parse.unquote(filename)
        
        zone_path = Path(f"static/media/{zone}")
        file_path = zone_path / filename
        
        if file_path.exists() and file_path.is_file():
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            
            # Supprimer le fichier
            file_path.unlink()
            
            activity_log.add(
                "media",
                f"Média supprimé de {zone.upper()}",
                f"Fichier: {filename}",
                file_size_mb
            )
            
            return JSONResponse(content={
                "success": True, 
                "message": "Élément supprimé avec succès"
            })
        else:
            raise HTTPException(status_code=404, detail="Fichier non trouvé")
            
    except Exception as e:
        activity_log.add("error", f"Erreur suppression média {zone}", str(e))
        raise HTTPException(status_code=500, detail=f"Erreur suppression: {str(e)}")

@router.post("/add-url-content")
async def add_url_content(content_data: dict):
    """Ajouter contenu distant avec téléchargement"""
    try:
        zone = content_data.get("zone")
        url = content_data.get("url")
        title = content_data.get("title", "")
        
        if not zone or not url:
            raise HTTPException(status_code=400, detail="Zone et URL requis")
        
        if zone not in ["left1", "left2", "left3", "center"]:
            raise HTTPException(status_code=400, detail="Zone invalide")
        
        # Créer le dossier de destination
        zone_dir = Path(f"static/media/{zone}")
        zone_dir.mkdir(parents=True, exist_ok=True)
        
        # Télécharger le contenu
        try:
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response.raise_for_status()
            
            # Détecter le type de contenu
            content_type = response.headers.get('content-type', '').lower()
            
            if content_type.startswith('image/'):
                # C'est une image - la télécharger directement
                file_extension = mimetypes.guess_extension(content_type) or '.jpg'
                
                # Générer un nom de fichier unique
                url_id = str(hash(url))[-8:]
                clean_title = "".join(c for c in (title or "image") if c.isalnum() or c in (' ', '-', '_')).strip()
                filename = f"{clean_title}_{url_id}{file_extension}".replace(' ', '_')
                file_path = zone_dir / filename
                
                # Sauvegarder l'image
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                
                # Optimiser l'image si c'est un JPEG/PNG
                if file_extension.lower() in ['.jpg', '.jpeg', '.png']:
                    try:
                        with Image.open(file_path) as img:
                            # Redimensionner si trop grande (max 1920x1080)
                            if img.width > 1920 or img.height > 1080:
                                img.thumbnail((1920, 1080), Image.Resampling.LANCZOS)
                            
                            # Sauvegarder optimisée
                            img.save(file_path, optimize=True, quality=85)
                    except Exception as e:
                        print(f"Erreur optimisation image: {e}")
                
                file_size_mb = file_path.stat().st_size / (1024 * 1024)
                
                activity_log.add(
                    "upload", 
                    f"Image URL téléchargée dans {zone.upper()}", 
                    f"Fichier: {filename} ({file_size_mb:.2f} MB)",
                    file_size_mb
                )
                
                return JSONResponse(content={
                    "success": True,
                    "message": f"Image téléchargée et sauvegardée: {filename}",
                    "filename": filename,
                    "size_mb": file_size_mb
                })
                
            elif content_type.startswith('video/'):
                # C'est une vidéo - créer un fichier de référence
                # url_id = str(hash(url))[-8:]
                # filename = f"video_url_{url_id}.json"
                # file_path = zone_dir / filename
                file_extension = mimetypes.guess_extension(content_type) or '.mp4'
                
                # Générer un nom de fichier unique
                url_id = str(hash(url))[-8:]
                clean_title = "".join(c for c in (title or "video") if c.isalnum() or c in (' ', '-', '_')).strip()
                filename = f"{clean_title}_{url_id}{file_extension}".replace(' ', '_')
                file_path = zone_dir / filename

                 # Vérifier la taille du contenu avant téléchargement
                content_length = response.headers.get('content-length')
                if content_length and int(content_length) > 100 * 1024 * 1024:  # 100MB max pour vidéos
                    raise ValueError("Vidéo trop volumineuse (max 100MB)")
                
                 # Sauvegarder la vidéo
                with open(file_path, 'wb') as f:
                    # Télécharger par chunks pour les gros fichiers
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                file_size_mb = file_path.stat().st_size / (1024 * 1024)

                activity_log.add(
                    "upload", 
                    f"Vidéo URL téléchargée dans {zone.upper()}", 
                    f"Fichier: {filename} ({file_size_mb:.2f} MB)",
                    file_size_mb
                )
                return JSONResponse(content={
                    "success": True,
                    "message": f"Vidéo téléchargée et sauvegardée: {filename}",
                    "filename": filename,
                    "size_mb": file_size_mb
                })
                
            else:
                # Type non supporté
                raise ValueError(f"Type de contenu non supporté: {content_type}")
                
        except requests.RequestException as e:
            raise ValueError(f"Impossible de télécharger l'URL: {str(e)}")
        
    except Exception as e:
        activity_log.add("error", f"Erreur ajout URL dans {zone}", str(e))
        raise HTTPException(status_code=500, detail=f"Erreur ajout URL: {str(e)}")


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
        
        activity_log.add(
            "api_test", 
            f"Test météo réussi pour {result['ville']}", 
            f"Température: {result['temperature']}°C"
        )
        
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
    except Exception as e:
        error_message = str(e)
        print(f"Erreur de test météo: {error_message}")

        activity_log.add("error", "Test météo échoué", error_message)

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

        activity_log.add(
            "api_test", 
            f"Test marées réussi", 
            f"Position: {lat:.4f}, {lon:.4f}"
        )

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
    except Exception as e:
        activity_log.add("error", "Test marées échoué", str(e))
        return JSONResponse(content={
            "success": False,
            "message": f"Erreur marées: {str(e)}"
        })

@router.post("/test-selfie")
async def test_selfie_module_connection(module_data: dict):
    """Test module Selfie via SelfieService"""
    try:
        # Utiliser le SelfieService
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

        size_freed = deleted_count * 2.5  # Estimation
        activity_log.add(
            "cleanup", 
            f"Nettoyage système terminé", 
            f"{deleted_count} fichiers supprimés",
            size_freed
        )
        
        return JSONResponse(content={
            "success": True,
            "message": "Nettoyage terminé",
            "deleted_files": deleted_count
        })
    except Exception as e:
        activity_log.add("error", "Erreur nettoyage système", str(e))
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
        activity_log.add("backup", "Génération du backup en cours")
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
        activity_log.add("error", "Erreur génération backup", str(e))
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
        # Réutiliser la logique des stats détaillées
        detailed_response = await get_detailed_stats()
        detailed_data = detailed_response.body.decode('utf-8')
        detailed_json = json.loads(detailed_data)
        
        if detailed_json["success"]:
            stats = detailed_json["stats"]

            raw_storage_mb = stats["storage"]["total_mb"]
            rounded_storage_mb = custom_roun_mb(raw_storage_mb)

            return JSONResponse(content={
                "success": True,
                "stats": {
                    "medias": stats["media_total"],
                    "selfies": stats["selfies"]["total"],
                    "pistes": stats["music"]["total_tracks"],
                    "storage_mb": rounded_storage_mb
                },
                "timestamp": datetime.now().isoformat()
            })
        else:
            raise Exception("Erreur récupération stats détaillées")
            
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
    
@router.get("/stats/media-evolution")
async def get_media_evolution_stats(period: str = "7_days"):
    """Statistiques d'évolution des médias avec filtres corrigés"""
    try:
        from datetime import datetime, timedelta
        import calendar
        
        today = datetime.now()
        days_data = []

        if period == "7_days":
            # 7 derniers jours (existant - fonctionne déjà)
            for i in range(6, -1, -1):
                target_date = today - timedelta(days=i)
                day_label = target_date.strftime("%d")
                full_date = target_date.strftime("%Y-%m-%d")
                
                daily_count = count_files_for_date(target_date)
                
                days_data.append({
                    "day": day_label,
                    "date": full_date,
                    "count": daily_count,
                    "is_today": i == 0
                })

        elif period == "30_days":
            # 30 derniers jours par périodes de 5 jours - de la plus récente à la plus ancienne
            for i in range(6):  # 6 périodes de 5 jours
                # La période la plus récente commence à aujourd'hui-4 et finit aujourd'hui
                end_date = today - timedelta(days=i*5)
                start_date = end_date - timedelta(days=4)
                
                # S'assurer qu'on ne va pas dans le futur
                if end_date > today:
                    end_date = today
                
                # Compter les fichiers dans cette période (rétrograde)
                period_count = 0
                check_date = start_date
                while check_date <= end_date:
                    period_count += count_files_for_date(check_date)
                    check_date += timedelta(days=1)
                
                # Label : jours du mois (du plus ancien au plus récent dans la période)
                day_label = f"{start_date.day:02d}-{end_date.day:02d}"
                full_date = start_date.strftime("%Y-%m-%d")
                
                # Insérer au début pour avoir l'ordre chronologique dans l'affichage
                days_data.insert(0, {
                    "day": day_label,
                    "date": full_date,
                    "count": period_count
                })

        elif period == "current_month":
            # Mois actuel par semaines 
            import calendar
            first_day = today.replace(day=1)
            last_day = calendar.monthrange(today.year, today.month)[1]
            last_day_of_month = today.replace(day=last_day)
            
            # Calculer le nombre total de semaines dans le mois
            total_weeks = 0
            temp_date = first_day
            while temp_date <= last_day_of_month:
                temp_date += timedelta(days=7)
                total_weeks += 1
            
            # Créer TOUTES les semaines S1 à S[total_weeks]
            for week_num in range(1, total_weeks + 1):
                # Calculer le début et fin de cette semaine
                week_start = first_day + timedelta(days=(week_num - 1) * 7)
                week_end = week_start + timedelta(days=6)
                
                # Limiter à la fin du mois
                if week_end > last_day_of_month:
                    week_end = last_day_of_month
                
                # Compter les fichiers de cette semaine (0 si semaine future)
                week_count = 0
                if week_start <= today:  # Seulement si la semaine a commencé
                    check_date = week_start
                    while check_date <= min(week_end, today):  # Jusqu'à aujourd'hui max
                        week_count += count_files_for_date(check_date)
                        check_date += timedelta(days=1)
                
                day_label = f"S{week_num}"
                full_date = week_start.strftime("%Y-%m-%d")
                
                days_data.append({
                    "day": day_label,
                    "date": full_date,
                    "count": week_count  # Sera 0 pour les semaines futures
                })
        
        return JSONResponse(content={
            "success": True,
            "data": {
                "labels": [day["day"] for day in days_data],
                "counts": [day["count"] for day in days_data],
                "full_dates": [day["date"] for day in days_data],
                "period": period
            }
        })
        
    except Exception as e:
        return JSONResponse(content={
            "success": False,
            "error": str(e),
            "data": {
                "labels": ["29", "30", "31", "1", "2", "3", "4"],
                "counts": [0, 0, 0, 0, 0, 0, 0],
                "period": "7_days"
            }
        })

@router.get("/stats/zones-distribution")
async def get_zones_distribution_stats():
    """Répartition des médias par zones"""
    try:
        zones_data = {}
        zones = ['left1', 'left2', 'left3', 'center']
        zone_names = {
            'left1': 'Zone 1',
            'left2': 'Zone 2', 
            'left3': 'Zone 3',
            'center': 'Centre'
        }
        
        for zone in zones:
            zone_path = Path(f"static/media/{zone}")
            count = 0
            if zone_path.exists():
                count = len([f for f in zone_path.iterdir() 
                           if f.is_file() and f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.mp4', '.webm', '.webp', '.mov']])
            
            zones_data[zone] = {
                "name": zone_names[zone],
                "count": count
            }
        
        return JSONResponse(content={
            "success": True,
            "data": {
                "labels": [zones_data[zone]["name"] for zone in zones],
                "counts": [zones_data[zone]["count"] for zone in zones]
            }
        })
        
    except Exception as e:
        return JSONResponse(content={
            "success": False,
            "error": str(e),
            "data": {
                "labels": ["Zone 1", "Zone 2", "Zone 3", "Centre"],
                "counts": [0, 0, 0, 0]
            }
        })

# @router.get("/stats/detailed")
# async def get_detailed_stats():
#     """Statistiques détaillées pour la section Analytics"""
#     try:
#         from datetime import datetime, timedelta
        
#         # Stats des médias par zones
#         zones = ['left1', 'left2', 'left3', 'center']
#         zones_stats = {}
#         total_media = 0
#         total_storage_bytes = 0
        
#         for zone in zones:
#             zone_path = Path(f"static/media/{zone}")
#             zone_count = 0
#             zone_size = 0
            
#             if zone_path.exists():
#                 for file_path in zone_path.iterdir():
#                     if file_path.is_file() and file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.mp4', '.webm', '.webp', '.mov']:
#                         zone_count += 1
#                         zone_size += file_path.stat().st_size
                        
#             zones_stats[zone] = {
#                 "count": zone_count,
#                 "size_mb": round(zone_size / (1024 * 1024), 1)
#             }
#             total_media += zone_count
#             total_storage_bytes += zone_size
        
#         # Stats des selfies avec détails temporels
#         selfies_path = Path("static/selfies")
#         selfies_stats = {
#             "total": 0,
#             "today": 0,
#             "week": 0,
#             "total_size_mb": 0,
#             "storage_mb": 0
#         }
        
#         if selfies_path.exists():
#             today = datetime.now().date()
#             week_ago = today - timedelta(days=7)
#             selfie_files = []
            
#             for file_path in selfies_path.iterdir():
#                 if file_path.is_file() and file_path.suffix.lower() in ['.jpg', '.jpeg', '.png']:
#                     file_date = datetime.fromtimestamp(file_path.stat().st_ctime).date()
#                     file_size = file_path.stat().st_size
                    
#                     selfie_files.append({
#                         "date": file_date,
#                         "size": file_size
#                     })
                    
#                     # Compter par période
#                     if file_date == today:
#                         selfies_stats["today"] += 1
#                     if file_date >= week_ago:
#                         selfies_stats["week"] += 1
            
#             selfies_stats["total"] = len(selfie_files)
#             if selfie_files:
#                 total_selfie_size = sum(f["size"] for f in selfie_files)
#                 selfies_stats["storage_mb"] = total_selfie_size / (1024 * 1024)
#                 selfies_stats["total_size_mb"] = total_selfie_size / (1024 * 1024)
        
#         # Stats de stockage détaillées
#         storage_stats = {
#             "total_mb": round(total_storage_bytes / (1024 * 1024), 1),
#             "images_mb": 0,
#             "videos_mb": 0,
#             "selfies_mb": selfies_stats["storage_mb"]
#         }
        
#         # Séparer images et vidéos
#         for zone in zones:
#             zone_path = Path(f"static/media/{zone}")
#             if zone_path.exists():
#                 for file_path in zone_path.iterdir():
#                     if file_path.is_file():
#                         file_size_mb = file_path.stat().st_size / (1024 * 1024)
#                         if file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
#                             storage_stats["images_mb"] += file_size_mb
#                         elif file_path.suffix.lower() in ['.mp4', '.webm', '.mov']:
#                             storage_stats["videos_mb"] += file_size_mb
        
#         storage_stats["images_mb"] = round(storage_stats["images_mb"], 1)
#         storage_stats["videos_mb"] = round(storage_stats["videos_mb"], 1)
        
#         return JSONResponse(content={
#             "success": True,
#             "stats": {
#                 "media_total": total_media,
#                 "zones": zones_stats,
#                 "selfies": selfies_stats,
#                 "storage": storage_stats,
#                 "music": {
#                     "total_tracks": 0,  # À implémenter selon le système DJ
#                     "current_track": "Aucune",
#                     "total_duration": "0h 0m",
#                     "dj_status": "offline"
#                 }
#             },
#             "timestamp": datetime.now().isoformat()
#         })
        
#     except Exception as e:
#         return JSONResponse(content={
#             "success": False,
#             "error": str(e),
#             "stats": {
#                 "media_total": 0,
#                 "zones": {"left1": {"count": 0, "size_mb": 0}, "left2": {"count": 0, "size_mb": 0}, 
#                          "left3": {"count": 0, "size_mb": 0}, "center": {"count": 0, "size_mb": 0}},
#                 "selfies": {"total": 0, "today": 0, "week": 0, "total_size_mb": 0, "storage_mb": 0},
#                 "storage": {"total_mb": 0, "images_mb": 0, "videos_mb": 0, "selfies_mb": 0}
#             }
#         })

@router.get("/stats/detailed")
async def get_detailed_stats():
    """Statistiques détaillées pour la section Analytics"""
    try:
        from datetime import datetime, timedelta
        
        # Stats des médias par zones
        zones = ['left1', 'left2', 'left3', 'center']
        zones_stats = {}
        total_media = 0
        total_storage_bytes = 0
        
        for zone in zones:
            zone_path = Path(f"static/media/{zone}")
            zone_count = 0
            zone_size = 0
            
            if zone_path.exists():
                for file_path in zone_path.iterdir():
                    if file_path.is_file() and file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.mp4', '.webm', '.webp', '.mov']:
                        zone_count += 1
                        zone_size += file_path.stat().st_size
                        
            zones_stats[zone] = {
                "count": zone_count,
                "size_mb": round(zone_size / (1024 * 1024), 1)
            }
            total_media += zone_count
            total_storage_bytes += zone_size
        
        # Stats des selfies avec détails temporels
        selfies_path = Path("static/selfies")
        selfies_stats = {
            "total": 0,
            "today": 0,
            "week": 0,
            "total_size_mb": 0,
            "storage_mb": 0
        }
        
        if selfies_path.exists():
            today = datetime.now().date()
            # calculer le début de la semaine courante (lundi)
            days_since_monday = today.weekday() # lundi=0, mardi=1, ..., dimanche=6
            week_start = today - timedelta(days=days_since_monday)
            # week_ago = today - timedelta(days=7)
            selfie_files = []
            
            for file_path in selfies_path.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                    file_date = datetime.fromtimestamp(file_path.stat().st_ctime).date()
                    file_size = file_path.stat().st_size
                    
                    selfie_files.append({
                        "date": file_date,
                        "size": file_size
                    })
                    
                    # Compter par période
                    if file_date == today:
                        selfies_stats["today"] += 1
                    # Compter depuis le lundi de la semain courante
                    if file_date >= week_start:
                        selfies_stats["week"] += 1
            
            selfies_stats["total"] = len(selfie_files)
            if selfie_files:
                total_selfie_size = sum(f["size"] for f in selfie_files)
                selfies_stats["storage_mb"] = total_selfie_size / (1024 * 1024)
                selfies_stats["total_size_mb"] = total_selfie_size / (1024 * 1024)
        
        # Stats de stockage détaillées
        storage_stats = {
            "total_mb": round(total_storage_bytes / (1024 * 1024), 2),
            "images_mb": 0,
            "videos_mb": 0,
            "selfies_mb": selfies_stats["storage_mb"]
        }
        
        # Séparer images et vidéos
        for zone in zones:
            zone_path = Path(f"static/media/{zone}")
            if zone_path.exists():
                for file_path in zone_path.iterdir():
                    if file_path.is_file():
                        file_size_mb = file_path.stat().st_size / (1024 * 1024)
                        if file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                            storage_stats["images_mb"] += file_size_mb
                        elif file_path.suffix.lower() in ['.mp4', '.webm', '.mov']:
                            storage_stats["videos_mb"] += file_size_mb
        
        storage_stats["images_mb"] = round(storage_stats["images_mb"], 2)
        storage_stats["videos_mb"] = round(storage_stats["videos_mb"], 2)
        
        # Ajouter l'activité récente
        recent_activity = activity_log.get_recent_activities(limit=15)
        
        return JSONResponse(content={
            "success": True,
            "stats": {
                "media_total": total_media,
                "zones": zones_stats,
                "selfies": selfies_stats,
                "storage": storage_stats,
                "music": {
                    "total_tracks": 0,
                    "current_track": "Aucune",
                    "total_duration": "0h 0m",
                    "dj_status": "offline"
                },
                "activity": recent_activity  # ← LIGNE AJOUTÉE
            },
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        # En cas d'erreur, retourner des valeurs par défaut avec activité vide
        return JSONResponse(content={
            "success": False,
            "error": str(e),
            "stats": {
                "media_total": 0,
                "zones": {"left1": {"count": 0, "size_mb": 0}, "left2": {"count": 0, "size_mb": 0}, 
                         "left3": {"count": 0, "size_mb": 0}, "center": {"count": 0, "size_mb": 0}},
                "selfies": {"total": 0, "today": 0, "week": 0, "total_size_mb": 0, "storage_mb": 0},
                "storage": {"total_mb": 0, "images_mb": 0, "videos_mb": 0, "selfies_mb": 0},
                "music": {"total_tracks": 0, "current_track": "Aucune", "total_duration": "0h 0m", "dj_status": "offline"},
                "activity": []
            }
        })
    

# Route pour activité
@router.get("/activity")
async def get_recent_activity():
    """Récupérer l'activité récente formatée pour l'UI"""
    try:
        activities = activity_log.get_recent_activities(limit=20)
        
        return JSONResponse(content={
            "success": True,
            "activities": activities,
            "count": len(activities)
        })
    except Exception as e:
        return JSONResponse(content={
            "success": False,
            "error": str(e),
            "activities": []
        })