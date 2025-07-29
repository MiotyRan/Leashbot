"""
Service de gestion des fichiers pour le module TEASER
Upload, validation, nettoyage et organisation des médias
"""

import os
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
import logging
import mimetypes
import hashlib
import json
from PIL import Image
import aiofiles

logger = logging.getLogger(__name__)

class FileManager:
    """Gestionnaire de fichiers pour TEASER"""
    
    def __init__(self):
        self.base_media_path = Path("static/media")
        self.base_selfie_path = Path("static/selfies")
        self.base_music_path = Path("static/music")
        self.upload_temp_path = Path("uploads/temp")
        
        # Configuration des types de fichiers autorisés
        self.allowed_image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
        self.allowed_video_extensions = {'.mp4', '.webm', '.ogg', '.avi', '.mov', '.mkv'}
        self.allowed_audio_extensions = {'.mp3', '.wav', '.ogg', '.m4a', '.aac', '.flac'}
        
        # Tailles maximales (en bytes)
        self.max_image_size = 10 * 1024 * 1024  # 10MB
        self.max_video_size = 100 * 1024 * 1024  # 100MB
        self.max_audio_size = 20 * 1024 * 1024   # 20MB
        
        # Créer les dossiers nécessaires
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Créer les dossiers nécessaires"""
        directories = [
            self.base_media_path,
            self.base_selfie_path,
            self.base_music_path,
            self.upload_temp_path,
            self.base_media_path / "left1",
            self.base_media_path / "left2", 
            self.base_media_path / "left3",
            self.base_media_path / "center",
            self.base_media_path / "backgrounds",
            self.base_music_path / "uploads",
            self.base_music_path / "library"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            
        logger.info("Dossiers de fichiers initialisés")
    
    def is_valid_media_file(self, file) -> bool:
        """
        Vérifier si un fichier est valide pour l'upload
        
        Args:
            file: Objet fichier (UploadFile de FastAPI)
            
        Returns:
            True si le fichier est valide
        """
        try:
            if not file.filename:
                return False
            
            # Vérifier l'extension
            file_extension = Path(file.filename).suffix.lower()
            
            if file_extension not in (
                self.allowed_image_extensions | 
                self.allowed_video_extensions | 
                self.allowed_audio_extensions
            ):
                logger.warning(f"Extension non autorisée: {file_extension}")
                return False
            
            # Vérifier le type MIME
            if not self._is_valid_mime_type(file.content_type, file_extension):
                logger.warning(f"Type MIME invalide: {file.content_type} pour {file_extension}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur validation fichier: {str(e)}")
            return False
    
    def _is_valid_mime_type(self, content_type: str, file_extension: str) -> bool:
        """Vérifier la cohérence entre type MIME et extension"""
        if not content_type:
            return False
        
        # Mapping des extensions vers les types MIME autorisés
        mime_mappings = {
            '.jpg': ['image/jpeg'],
            '.jpeg': ['image/jpeg'],
            '.png': ['image/png'],
            '.gif': ['image/gif'],
            '.webp': ['image/webp'],
            '.bmp': ['image/bmp'],
            '.mp4': ['video/mp4'],
            '.webm': ['video/webm'],
            '.ogg': ['video/ogg', 'audio/ogg'],
            '.avi': ['video/avi', 'video/x-msvideo'],
            '.mov': ['video/quicktime'],
            '.mkv': ['video/x-matroska'],
            '.mp3': ['audio/mpeg'],
            '.wav': ['audio/wav'],
            '.m4a': ['audio/m4a', 'audio/x-m4a'],
            '.aac': ['audio/aac'],
            '.flac': ['audio/flac']
        }
        
        allowed_mimes = mime_mappings.get(file_extension, [])
        return content_type in allowed_mimes
    
    def get_file_type(self, content_type: str) -> str:
        """Déterminer le type de fichier (image/video/audio)"""
        if content_type.startswith('image/'):
            return 'image'
        elif content_type.startswith('video/'):
            return 'video'
        elif content_type.startswith('audio/'):
            return 'audio'
        else:
            return 'unknown'
    
    def detect_url_type(self, url: str) -> str:
        """Détecter le type de contenu depuis une URL"""
        url_lower = url.lower()
        
        # Extensions d'images
        if any(ext in url_lower for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']):
            return 'image'
        
        # Extensions de vidéos
        if any(ext in url_lower for ext in ['.mp4', '.webm', '.ogg', '.avi', '.mov']):
            return 'video'
        
        # Services de streaming
        if any(service in url_lower for service in ['youtube.com', 'youtu.be', 'vimeo.com']):
            return 'video'
        
        # Par défaut, traiter comme image
        return 'image'
    
    async def save_uploaded_file(self, file, destination_path: Path) -> Dict[str, Any]:
        """
        Sauvegarder un fichier uploadé
        
        Args:
            file: Fichier uploadé
            destination_path: Chemin de destination
            
        Returns:
            Informations sur le fichier sauvegardé
        """
        try:
            # Créer le dossier de destination
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Lire et sauvegarder le fichier
            async with aiofiles.open(destination_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
            
            # Obtenir les informations du fichier
            file_info = await self.get_file_info(destination_path)
            
            # Traitement spécifique selon le type
            if file_info['type'] == 'image':
                file_info.update(await self._process_image(destination_path))
            elif file_info['type'] == 'video':
                file_info.update(await self._process_video(destination_path))
            
            logger.info(f"Fichier sauvegardé: {destination_path}")
            return file_info
            
        except Exception as e:
            logger.error(f"Erreur sauvegarde fichier: {str(e)}")
            # Nettoyer en cas d'erreur
            if destination_path.exists():
                destination_path.unlink()
            raise
    
    async def get_file_info(self, file_path: Path) -> Dict[str, Any]:
        """Obtenir les informations d'un fichier"""
        try:
            stat = file_path.stat()
            
            # Déterminer le type depuis l'extension
            extension = file_path.suffix.lower()
            if extension in self.allowed_image_extensions:
                file_type = 'image'
            elif extension in self.allowed_video_extensions:
                file_type = 'video'
            elif extension in self.allowed_audio_extensions:
                file_type = 'audio'
            else:
                file_type = 'unknown'
            
            return {
                'filename': file_path.name,
                'size': stat.st_size,
                'size_mb': round(stat.st_size / (1024 * 1024), 2),
                'type': file_type,
                'extension': extension,
                'created': datetime.fromtimestamp(stat.st_ctime),
                'modified': datetime.fromtimestamp(stat.st_mtime),
                'path': str(file_path),
                'relative_path': str(file_path.relative_to(Path.cwd())),
                'hash': await self._calculate_file_hash(file_path)
            }
            
        except Exception as e:
            logger.error(f"Erreur info fichier {file_path}: {str(e)}")
            return {
                'filename': file_path.name if file_path else 'unknown',
                'error': str(e)
            }
    
    async def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculer le hash MD5 d'un fichier"""
        try:
            hash_md5 = hashlib.md5()
            async with aiofiles.open(file_path, 'rb') as f:
                async for chunk in self._read_chunks(f):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return ""
    
    async def _read_chunks(self, file_handle, chunk_size: int = 8192):
        """Lire un fichier par chunks"""
        while chunk := await file_handle.read(chunk_size):
            yield chunk
    
    async def _process_image(self, image_path: Path) -> Dict[str, Any]:
        """Traitement spécifique des images"""
        try:
            with Image.open(image_path) as img:
                # Informations de base
                info = {
                    'width': img.width,
                    'height': img.height,
                    'format': img.format,
                    'mode': img.mode,
                    'has_transparency': img.mode in ('RGBA', 'LA') or 'transparency' in img.info
                }
                
                # Créer une miniature si l'image est grande
                if img.width > 1920 or img.height > 1080:
                    await self._create_thumbnail(image_path, img)
                    info['has_thumbnail'] = True
                
                # Optimiser si nécessaire
                if image_path.stat().st_size > self.max_image_size:
                    await self._optimize_image(image_path, img)
                    info['optimized'] = True
                
                return info
                
        except Exception as e:
            logger.error(f"Erreur traitement image {image_path}: {str(e)}")
            return {'processing_error': str(e)}
    
    async def _process_video(self, video_path: Path) -> Dict[str, Any]:
        """Traitement spécifique des vidéos"""
        try:
            # Pour l'instant, juste les informations de base
            # TODO: Utiliser ffprobe pour obtenir durée, résolution, etc.
            
            return {
                'duration': None,  # Sera implémenté avec ffprobe
                'resolution': None,
                'bitrate': None,
                'codec': None
            }
            
        except Exception as e:
            logger.error(f"Erreur traitement vidéo {video_path}: {str(e)}")
            return {'processing_error': str(e)}
    
    async def _create_thumbnail(self, image_path: Path, img: Image.Image):
        """Créer une miniature pour une image"""
        try:
            thumbnail_size = (300, 300)
            thumbnail_path = image_path.parent / f"thumb_{image_path.name}"
            
            # Créer la miniature
            img.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)
            img.save(thumbnail_path, optimize=True, quality=85)
            
            logger.debug(f"Miniature créée: {thumbnail_path}")
            
        except Exception as e:
            logger.error(f"Erreur création miniature: {str(e)}")
    
    async def _optimize_image(self, image_path: Path, img: Image.Image):
        """Optimiser une image trop lourde"""
        try:
            # Réduire la qualité pour diminuer la taille
            optimized_path = image_path.parent / f"opt_{image_path.name}"
            
            # Convertir en RGB si nécessaire
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # Sauvegarder avec compression
            img.save(optimized_path, optimize=True, quality=75)
            
            # Remplacer l'original si l'optimisation a fonctionné
            if optimized_path.stat().st_size < image_path.stat().st_size:
                shutil.move(optimized_path, image_path)
                logger.debug(f"Image optimisée: {image_path}")
            else:
                optimized_path.unlink()
                
        except Exception as e:
            logger.error(f"Erreur optimisation image: {str(e)}")
    
    async def cleanup_old_files(self, days: int = 30) -> int:
        """
        Nettoyer les fichiers anciens
        
        Args:
            days: Nombre de jours après lesquels supprimer
            
        Returns:
            Nombre de fichiers supprimés
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            deleted_count = 0
            
            # Dossiers à nettoyer
            cleanup_paths = [
                self.upload_temp_path,
                self.base_media_path,
                # Ne pas nettoyer les selfies automatiquement
            ]
            
            for path in cleanup_paths:
                if not path.exists():
                    continue
                
                # Parcourir récursivement
                for file_path in path.rglob('*'):
                    if file_path.is_file():
                        try:
                            # Vérifier la date de modification
                            mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                            
                            if mod_time < cutoff_date:
                                # Ne pas supprimer les fichiers .gitkeep
                                if file_path.name == '.gitkeep':
                                    continue
                                
                                file_path.unlink()
                                deleted_count += 1
                                logger.debug(f"Fichier supprimé: {file_path}")
                                
                        except Exception as e:
                            logger.warning(f"Impossible de supprimer {file_path}: {str(e)}")
            
            # Nettoyer les dossiers vides
            await self._cleanup_empty_directories(cleanup_paths)
            
            logger.info(f"Nettoyage terminé: {deleted_count} fichiers supprimés")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Erreur nettoyage: {str(e)}")
            return 0
    
    async def _cleanup_empty_directories(self, paths: List[Path]):
        """Supprimer les dossiers vides"""
        for path in paths:
            if not path.exists():
                continue
                
            try:
                # Parcourir de bas en haut pour supprimer les dossiers vides
                for dir_path in sorted(path.rglob('*'), key=lambda p: len(p.parts), reverse=True):
                    if dir_path.is_dir() and dir_path != path:
                        try:
                            # Vérifier si le dossier est vide (sauf .gitkeep)
                            contents = list(dir_path.iterdir())
                            if not contents or (len(contents) == 1 and contents[0].name == '.gitkeep'):
                                if contents:  # Garder .gitkeep
                                    continue
                                dir_path.rmdir()
                                logger.debug(f"Dossier vide supprimé: {dir_path}")
                        except OSError:
                            # Dossier pas vide ou autres erreurs
                            continue
            except Exception as e:
                logger.warning(f"Erreur nettoyage dossiers vides: {str(e)}")
    
    def get_media_files(self, zone: str) -> List[Dict[str, Any]]:
        """
        Récupérer la liste des fichiers média d'une zone
        
        Args:
            zone: Zone à scanner (left1, left2, left3, center)
            
        Returns:
            Liste des fichiers avec leurs informations
        """
        try:
            zone_path = self.base_media_path / zone
            if not zone_path.exists():
                return []
            
            files = []
            for file_path in zone_path.iterdir():
                if file_path.is_file() and file_path.name != '.gitkeep':
                    try:
                        file_info = {
                            'name': file_path.name,
                            'path': f"/static/media/{zone}/{file_path.name}",
                            'size': file_path.stat().st_size,
                            'modified': file_path.stat().st_mtime,
                            'type': self._get_file_type_from_extension(file_path.suffix)
                        }
                        files.append(file_info)
                    except Exception as e:
                        logger.warning(f"Erreur info fichier {file_path}: {str(e)}")
            
            # Trier par date de modification (plus récent en premier)
            files.sort(key=lambda x: x['modified'], reverse=True)
            return files
            
        except Exception as e:
            logger.error(f"Erreur lecture zone {zone}: {str(e)}")
            return []
    
    def _get_file_type_from_extension(self, extension: str) -> str:
        """Déterminer le type depuis l'extension"""
        extension = extension.lower()
        if extension in self.allowed_image_extensions:
            return 'image'
        elif extension in self.allowed_video_extensions:
            return 'video'
        elif extension in self.allowed_audio_extensions:
            return 'audio'
        else:
            return 'unknown'
    
    def get_selfie_files(self, month: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Récupérer les fichiers selfie
        
        Args:
            month: Mois au format YYYY-MM (optionnel, défaut = mois actuel)
            limit: Nombre maximum de fichiers à retourner
            
        Returns:
            Liste des selfies avec leurs informations
        """
        try:
            if not month:
                month = datetime.now().strftime("%Y-%m")
            
            month_path = self.base_selfie_path / month
            if not month_path.exists():
                return []
            
            selfies = []
            for file_path in month_path.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in self.allowed_image_extensions:
                    try:
                        selfie_info = {
                            'name': file_path.name,
                            'path': f"/static/selfies/{month}/{file_path.name}",
                            'size': file_path.stat().st_size,
                            'taken_at': file_path.stat().st_mtime,
                            'month': month
                        }
                        selfies.append(selfie_info)
                    except Exception as e:
                        logger.warning(f"Erreur info selfie {file_path}: {str(e)}")
            
            # Trier par date (plus récent en premier) et limiter
            selfies.sort(key=lambda x: x['taken_at'], reverse=True)
            return selfies[:limit]
            
        except Exception as e:
            logger.error(f"Erreur lecture selfies {month}: {str(e)}")
            return []
    
    async def move_file(self, source_path: Path, destination_path: Path) -> bool:
        """
        Déplacer un fichier
        
        Args:
            source_path: Chemin source
            destination_path: Chemin destination
            
        Returns:
            True si le déplacement a réussi
        """
        try:
            # Créer le dossier de destination
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Déplacer le fichier
            shutil.move(str(source_path), str(destination_path))
            
            logger.info(f"Fichier déplacé: {source_path} -> {destination_path}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur déplacement fichier: {str(e)}")
            return False
    
    async def copy_file(self, source_path: Path, destination_path: Path) -> bool:
        """
        Copier un fichier
        
        Args:
            source_path: Chemin source
            destination_path: Chemin destination
            
        Returns:
            True si la copie a réussi
        """
        try:
            # Créer le dossier de destination
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copier le fichier
            shutil.copy2(str(source_path), str(destination_path))
            
            logger.info(f"Fichier copié: {source_path} -> {destination_path}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur copie fichier: {str(e)}")
            return False
    
    async def delete_file(self, file_path: Path) -> bool:
        """
        Supprimer un fichier
        
        Args:
            file_path: Chemin du fichier à supprimer
            
        Returns:
            True si la suppression a réussi
        """
        try:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Fichier supprimé: {file_path}")
                return True
            else:
                logger.warning(f"Fichier introuvable: {file_path}")
                return False
                
        except Exception as e:
            logger.error(f"Erreur suppression fichier: {str(e)}")
            return False
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Obtenir les statistiques de stockage
        
        Returns:
            Statistiques détaillées par zone
        """
        try:
            stats = {
                'total_size': 0,
                'total_files': 0,
                'zones': {},
                'selfies': {},
                'music': {}
            }
            
            # Statistiques par zone média
            zones = ['left1', 'left2', 'left3', 'center', 'backgrounds']
            for zone in zones:
                zone_path = self.base_media_path / zone
                zone_stats = self._get_directory_stats(zone_path)
                stats['zones'][zone] = zone_stats
                stats['total_size'] += zone_stats['size']
                stats['total_files'] += zone_stats['files']
            
            # Statistiques selfies
            if self.base_selfie_path.exists():
                selfie_stats = self._get_directory_stats(self.base_selfie_path)
                stats['selfies'] = selfie_stats
                stats['total_size'] += selfie_stats['size']
                stats['total_files'] += selfie_stats['files']
            
            # Statistiques musique
            if self.base_music_path.exists():
                music_stats = self._get_directory_stats(self.base_music_path)
                stats['music'] = music_stats
                stats['total_size'] += music_stats['size']
                stats['total_files'] += music_stats['files']
            
            # Formatage
            stats['total_size_mb'] = round(stats['total_size'] / (1024 * 1024), 2)
            stats['total_size_gb'] = round(stats['total_size'] / (1024 * 1024 * 1024), 2)
            
            return stats
            
        except Exception as e:
            logger.error(f"Erreur calcul statistiques: {str(e)}")
            return {'error': str(e)}
    
    def _get_directory_stats(self, directory_path: Path) -> Dict[str, Any]:
        """Calculer les statistiques d'un dossier"""
        try:
            if not directory_path.exists():
                return {'size': 0, 'files': 0, 'directories': 0}
            
            total_size = 0
            file_count = 0
            dir_count = 0
            
            for item in directory_path.rglob('*'):
                if item.is_file():
                    total_size += item.stat().st_size
                    file_count += 1
                elif item.is_dir():
                    dir_count += 1
            
            return {
                'size': total_size,
                'size_mb': round(total_size / (1024 * 1024), 2),
                'files': file_count,
                'directories': dir_count,
                'path': str(directory_path)
            }
            
        except Exception as e:
            logger.error(f"Erreur stats dossier {directory_path}: {str(e)}")
            return {'size': 0, 'files': 0, 'error': str(e)}
    
    async def backup_media_config(self, backup_path: Path) -> bool:
        """
        Créer une sauvegarde de la configuration média
        
        Args:
            backup_path: Chemin du fichier de sauvegarde
            
        Returns:
            True si la sauvegarde a réussi
        """
        try:
            # Rassembler les informations de configuration
            config_data = {
                'backup_date': datetime.now().isoformat(),
                'version': '1.0',
                'storage_stats': self.get_storage_stats(),
                'zones': {}
            }
            
            # Configuration par zone
            zones = ['left1', 'left2', 'left3', 'center']
            for zone in zones:
                config_data['zones'][zone] = {
                    'files': self.get_media_files(zone),
                    'path': str(self.base_media_path / zone)
                }
            
            # Sauvegarder en JSON
            async with aiofiles.open(backup_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(config_data, indent=2, ensure_ascii=False))
            
            logger.info(f"Sauvegarde média créée: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur sauvegarde média: {str(e)}")
            return False


# Instance globale du gestionnaire de fichiers
file_manager = FileManager()