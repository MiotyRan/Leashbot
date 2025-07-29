"""
Service de gestion de la configuration pour le module TEASER
Centralise la gestion des paramètres, sauvegarde et restauration
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session

from models import TeaserConfig
from config import settings

logger = logging.getLogger(__name__)

class ConfigService:
    """Service de gestion de la configuration TEASER"""
    
    def __init__(self):
        self.config_file_path = Path("data/config.json")
        self.backup_dir = Path("data/backups")
        
        # Configuration par défaut
        self.default_config = {
            # API Configuration
            "weather_api_key": settings.WEATHER_API_KEY,
            "weather_location": settings.WEATHER_LOCATION,
            "weather_refresh": settings.WEATHER_REFRESH_INTERVAL,
            "tide_api_key": settings.TIDE_API_KEY,
            "tide_lat": settings.TIDE_LOCATION_LAT,
            "tide_lon": settings.TIDE_LOCATION_LON,
            "tide_refresh": settings.TIDE_REFRESH_INTERVAL,
            
            # Système
            "carousel_speed": settings.DEFAULT_CAROUSEL_SPEED,
            "auto_play_videos": settings.AUTO_PLAY_VIDEOS,
            "video_volume": settings.VIDEO_VOLUME,
            "auto_cleanup": settings.AUTO_CLEANUP_ENABLED,
            "cleanup_days": settings.CLEANUP_AFTER_DAYS,
            "debug_mode": False,
            
            # Modules
            "selfie_path": settings.SELFIE_ROOT,
            "selfie_count": 3,
            "dj_url": "http://localhost:8001",
            "music_refresh": 5,
            "dj_auto_next": settings.DJ_AUTO_NEXT,
            "dj_shuffle": settings.DJ_SHUFFLE_MODE,
            "dj_volume": settings.DJ_VOLUME,
            
            # Zones
            "zones": {
                "left1": {
                    "title": "Zone Gauche 1",
                    "enabled": True,
                    "duration": 5
                },
                "left2": {
                    "title": "Zone Gauche 2", 
                    "enabled": True,
                    "duration": 5
                },
                "left3": {
                    "title": "Zone Gauche 3",
                    "enabled": True,
                    "duration": 5
                },
                "center": {
                    "title": "Zone Centrale",
                    "enabled": True,
                    "duration": 5
                }
            },
            
            # Métadonnées
            "version": "1.0",
            "last_updated": datetime.now().isoformat()
        }
        
        # Créer les dossiers nécessaires
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Créer les dossiers de configuration"""
        self.config_file_path.parent.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    async def get_full_config(self, db: Session) -> Dict[str, Any]:
        """
        Récupérer la configuration complète
        
        Args:
            db: Session de base de données
            
        Returns:
            Configuration complète fusionnée
        """
        try:
            # Récupérer depuis la base de données
            db_config = await self._get_config_from_db(db)
            
            # Récupérer depuis le fichier JSON
            file_config = await self._get_config_from_file()
            
            # Fusionner avec la config par défaut
            merged_config = self.default_config.copy()
            merged_config.update(file_config)
            merged_config.update(db_config)
            
            # Mettre à jour la timestamp
            merged_config["last_accessed"] = datetime.now().isoformat()
            
            return merged_config
            
        except Exception as e:
            logger.error(f"Erreur récupération configuration: {str(e)}")
            return self.default_config.copy()
    
    async def _get_config_from_db(self, db: Session) -> Dict[str, Any]:
        """Récupérer la configuration depuis la base de données"""
        try:
            config = {}
            
            # Récupérer tous les éléments de configuration
            config_items = db.query(TeaserConfig).all()
            
            for item in config_items:
                try:
                    # Essayer de parser en JSON
                    if item.value.startswith('{') or item.value.startswith('['):
                        config[item.key] = json.loads(item.value)
                    else:
                        # Conversion des types de base
                        value = item.value
                        
                        # Boolean
                        if value.lower() in ('true', 'false'):
                            config[item.key] = value.lower() == 'true'
                        # Numeric
                        elif value.replace('.', '').replace('-', '').isdigit():
                            config[item.key] = float(value) if '.' in value else int(value)
                        # String
                        else:
                            config[item.key] = value
                            
                except json.JSONDecodeError:
                    # En cas d'erreur, garder comme string
                    config[item.key] = item.value
                except Exception as e:
                    logger.warning(f"Erreur parsing config {item.key}: {str(e)}")
                    continue
            
            return config
            
        except Exception as e:
            logger.error(f"Erreur récupération config DB: {str(e)}")
            return {}
    
    async def _get_config_from_file(self) -> Dict[str, Any]:
        """Récupérer la configuration depuis le fichier JSON"""
        try:
            if not self.config_file_path.exists():
                return {}
            
            with open(self.config_file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            return config
            
        except Exception as e:
            logger.error(f"Erreur lecture config fichier: {str(e)}")
            return {}
    
    async def save_full_config(self, db: Session, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sauvegarder la configuration complète
        
        Args:
            db: Session de base de données
            config_data: Données de configuration à sauvegarder
            
        Returns:
            Résultat de la sauvegarde
        """
        try:
            saved_items = []
            
            # Traiter chaque section de configuration
            if "weather" in config_data:
                await self._save_weather_config(db, config_data["weather"])
                saved_items.append("weather")
            
            if "tide" in config_data:
                await self._save_tide_config(db, config_data["tide"])
                saved_items.append("tide")
            
            if "system" in config_data:
                await self._save_system_config(db, config_data["system"])
                saved_items.append("system")
            
            if "modules" in config_data:
                await self._save_modules_config(db, config_data["modules"])
                saved_items.append("modules")
            
            if "zones" in config_data:
                await self._save_zones_config(db, config_data["zones"])
                saved_items.append("zones")
            
            # Sauvegarder aussi dans le fichier JSON
            await self._save_config_to_file(config_data)
            
            # Créer une sauvegarde
            await self._create_backup(config_data)
            
            return {
                "success": True,
                "message": "Configuration sauvegardée avec succès",
                "saved_items": saved_items
            }
            
        except Exception as e:
            logger.error(f"Erreur sauvegarde configuration: {str(e)}")
            return {
                "success": False,
                "message": f"Erreur sauvegarde: {str(e)}"
            }
    
    async def _save_weather_config(self, db: Session, weather_config: Dict[str, Any]):
        """Sauvegarder la configuration météo"""
        config_items = {
            "weather_api_key": weather_config.get("weather_api_key", ""),
            "weather_location": weather_config.get("weather_location", ""),
            "weather_refresh": int(weather_config.get("weather_refresh", 5)) * 60  # Conversion en secondes
        }
        
        for key, value in config_items.items():
            await self._save_config_item(db, key, value)
    
    async def _save_tide_config(self, db: Session, tide_config: Dict[str, Any]):
        """Sauvegarder la configuration marées"""
        config_items = {
            "tide_api_key": tide_config.get("tide_api_key", ""),
            "tide_lat": float(tide_config.get("tide_lat", 0)),
            "tide_lon": float(tide_config.get("tide_lon", 0))
        }
        
        for key, value in config_items.items():
            await self._save_config_item(db, key, value)
    
    async def _save_system_config(self, db: Session, system_config: Dict[str, Any]):
        """Sauvegarder la configuration système"""
        config_items = {
            "carousel_speed": int(system_config.get("carousel_speed", 5)),
            "auto_play_videos": bool(system_config.get("auto_play_videos", True)),
            "video_volume": float(system_config.get("video_volume", 0.3)),
            "auto_cleanup": bool(system_config.get("auto_cleanup", False)),
            "cleanup_days": int(system_config.get("cleanup_days", 30)),
            "debug_mode": bool(system_config.get("debug_mode", False))
        }
        
        for key, value in config_items.items():
            await self._save_config_item(db, key, value)
    
    async def _save_modules_config(self, db: Session, modules_config: Dict[str, Any]):
        """Sauvegarder la configuration des modules"""
        config_items = {
            "selfie_path": modules_config.get("selfie_path", "/static/selfies/"),
            "selfie_count": int(modules_config.get("selfie_count", 3)),
            "dj_url": modules_config.get("dj_url", ""),
            "music_refresh": int(modules_config.get("music_refresh", 5))
        }
        
        for key, value in config_items.items():
            await self._save_config_item(db, key, value)
    
    async def _save_zones_config(self, db: Session, zones_config: Dict[str, Any]):
        """Sauvegarder la configuration des zones"""
        for zone_name, zone_config in zones_config.items():
            config_key = f"zone_{zone_name}_config"
            config_value = json.dumps(zone_config)
            await self._save_config_item(db, config_key, config_value)
    
    async def _save_config_item(self, db: Session, key: str, value: Any):
        """Sauvegarder un élément de configuration individuel"""
        try:
            # Chercher l'élément existant
            config_item = db.query(TeaserConfig).filter(TeaserConfig.key == key).first()
            
            # Convertir la valeur en string
            if isinstance(value, (dict, list)):
                value_str = json.dumps(value)
            else:
                value_str = str(value)
            
            if config_item:
                # Mettre à jour
                config_item.value = value_str
                config_item.updated_at = datetime.utcnow()
            else:
                # Créer
                config_item = TeaserConfig(key=key, value=value_str)
                db.add(config_item)
            
            db.commit()
            logger.debug(f"Config sauvegardée: {key} = {value_str}")
            
        except Exception as e:
            logger.error(f"Erreur sauvegarde config {key}: {str(e)}")
            db.rollback()
            raise
    
    async def _save_config_to_file(self, config_data: Dict[str, Any]):
        """Sauvegarder la configuration dans le fichier JSON"""
        try:
            # Ajouter des métadonnées
            file_config = {
                "saved_at": datetime.now().isoformat(),
                "version": "1.0",
                **config_data
            }
            
            with open(self.config_file_path, 'w', encoding='utf-8') as f:
                json.dump(file_config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Configuration sauvegardée dans {self.config_file_path}")
            
        except Exception as e:
            logger.error(f"Erreur sauvegarde config fichier: {str(e)}")
            raise
    
    async def _create_backup(self, config_data: Dict[str, Any]):
        """Créer une sauvegarde horodatée"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"config_backup_{timestamp}.json"
            
            backup_data = {
                "backup_created": datetime.now().isoformat(),
                "version": "1.0",
                "original_config": config_data
            }
            
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Sauvegarde créée: {backup_file}")
            
            # Nettoyer les anciennes sauvegardes (garder les 10 dernières)
            await self._cleanup_old_backups()
            
        except Exception as e:
            logger.warning(f"Erreur création sauvegarde: {str(e)}")
    
    async def _cleanup_old_backups(self, keep_count: int = 10):
        """Nettoyer les anciennes sauvegardes"""
        try:
            backup_files = list(self.backup_dir.glob("config_backup_*.json"))
            
            if len(backup_files) > keep_count:
                # Trier par date de modification
                backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                
                # Supprimer les plus anciennes
                for old_backup in backup_files[keep_count:]:
                    old_backup.unlink()
                    logger.debug(f"Ancienne sauvegarde supprimée: {old_backup}")
                    
        except Exception as e:
            logger.warning(f"Erreur nettoyage sauvegardes: {str(e)}")
    
    async def restore_config_from_backup(self, db: Session, backup_file: str) -> Dict[str, Any]:
        """
        Restaurer la configuration depuis une sauvegarde
        
        Args:
            db: Session de base de données
            backup_file: Nom du fichier de sauvegarde
            
        Returns:
            Résultat de la restauration
        """
        try:
            backup_path = self.backup_dir / backup_file
            
            if not backup_path.exists():
                return {
                    "success": False,
                    "message": f"Fichier de sauvegarde {backup_file} introuvable"
                }
            
            # Charger la sauvegarde
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            if "original_config" not in backup_data:
                return {
                    "success": False,
                    "message": "Format de sauvegarde invalide"
                }
            
            # Restaurer la configuration
            result = await self.save_full_config(db, backup_data["original_config"])
            
            if result["success"]:
                logger.info(f"Configuration restaurée depuis {backup_file}")
                return {
                    "success": True,
                    "message": f"Configuration restaurée depuis {backup_file}",
                    "backup_date": backup_data.get("backup_created")
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Erreur restauration sauvegarde: {str(e)}")
            return {
                "success": False,
                "message": f"Erreur restauration: {str(e)}"
            }
    
    async def get_backup_list(self) -> List[Dict[str, Any]]:
        """Obtenir la liste des sauvegardes disponibles"""
        try:
            backups = []
            
            for backup_file in self.backup_dir.glob("config_backup_*.json"):
                try:
                    stat = backup_file.stat()
                    
                    # Essayer de lire les métadonnées
                    backup_info = {
                        "filename": backup_file.name,
                        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "size": stat.st_size,
                        "size_kb": round(stat.st_size / 1024, 2)
                    }
                    
                    # Essayer de lire la date depuis le contenu
                    try:
                        with open(backup_file, 'r', encoding='utf-8') as f:
                            backup_data = json.load(f)
                            if "backup_created" in backup_data:
                                backup_info["backup_date"] = backup_data["backup_created"]
                    except:
                        pass
                    
                    backups.append(backup_info)
                    
                except Exception as e:
                    logger.warning(f"Erreur lecture info sauvegarde {backup_file}: {str(e)}")
                    continue
            
            # Trier par date de création (plus récent en premier)
            backups.sort(key=lambda x: x["created"], reverse=True)
            
            return backups
            
        except Exception as e:
            logger.error(f"Erreur liste sauvegardes: {str(e)}")
            return []
    
    async def reset_to_default(self, db: Session) -> Dict[str, Any]:
        """
        Réinitialiser la configuration aux valeurs par défaut
        
        Args:
            db: Session de base de données
            
        Returns:
            Résultat de la réinitialisation
        """
        try:
            # Créer une sauvegarde avant reset
            current_config = await self.get_full_config(db)
            await self._create_backup(current_config)
            
            # Supprimer toute la configuration en base
            db.query(TeaserConfig).delete()
            db.commit()
            
            # Supprimer le fichier de config
            if self.config_file_path.exists():
                self.config_file_path.unlink()
            
            logger.info("Configuration réinitialisée aux valeurs par défaut")
            
            return {
                "success": True,
                "message": "Configuration réinitialisée avec succès",
                "backup_created": True
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"Erreur réinitialisation config: {str(e)}")
            return {
                "success": False,
                "message": f"Erreur réinitialisation: {str(e)}"
            }
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Obtenir le schéma de configuration pour validation"""
        return {
            "weather": {
                "weather_api_key": {"type": "string", "required": True},
                "weather_location": {"type": "string", "required": True},
                "weather_refresh": {"type": "integer", "min": 1, "max": 60}
            },
            "tide": {
                "tide_api_key": {"type": "string"},
                "tide_lat": {"type": "float", "min": -90, "max": 90},
                "tide_lon": {"type": "float", "min": -180, "max": 180}
            },
            "system": {
                "carousel_speed": {"type": "integer", "min": 1, "max": 30},
                "auto_play_videos": {"type": "boolean"},
                "video_volume": {"type": "float", "min": 0, "max": 1},
                "auto_cleanup": {"type": "boolean"},
                "cleanup_days": {"type": "integer", "min": 1, "max": 365},
                "debug_mode": {"type": "boolean"}
            },
            "modules": {
                "selfie_path": {"type": "string"},
                "selfie_count": {"type": "integer", "min": 1, "max": 10},
                "dj_url": {"type": "string"},
                "music_refresh": {"type": "integer", "min": 1, "max": 60}
            }
        }


# Instance globale du service de configuration
config_service = ConfigService()