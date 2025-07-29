"""
Service de gestion des selfies pour le module TEASER
Récupération et gestion des photos selfie depuis le module dédié
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import json

from config import settings

logger = logging.getLogger(__name__)

class SelfieService:
    """Service de gestion des selfies"""
    
    def __init__(self):
        self.base_selfie_path = Path(settings.SELFIE_ROOT.lstrip('/'))
        self.allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        self.cache = {}
        self.cache_duration = timedelta(minutes=1)  # Cache court pour les selfies
        
        # Créer le dossier de base si nécessaire
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Créer les dossiers nécessaires pour les selfies"""
        try:
            self.base_selfie_path.mkdir(parents=True, exist_ok=True)
            
            # Créer les dossiers pour l'année actuelle et suivante
            current_year = datetime.now().year
            for year in [current_year, current_year + 1]:
                for month in range(1, 13):
                    month_dir = self.base_selfie_path / f"{year}-{month:02d}"
                    month_dir.mkdir(exist_ok=True)
                    
                    # Créer un fichier .gitkeep pour maintenir la structure
                    gitkeep_file = month_dir / '.gitkeep'
                    if not gitkeep_file.exists():
                        gitkeep_file.touch()
            
            logger.info(f"Dossiers selfies initialisés: {self.base_selfie_path}")
            
        except Exception as e:
            logger.error(f"Erreur création dossiers selfies: {str(e)}")
    
    def get_latest_selfies(self, limit: int = 3, month: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Récupérer les derniers selfies
        
        Args:
            limit: Nombre maximum de selfies à retourner
            month: Mois spécifique (format YYYY-MM) ou None pour le mois actuel
            
        Returns:
            Liste des selfies avec leurs informations
        """
        try:
            # Utiliser le cache si disponible
            cache_key = f"latest_selfies_{limit}_{month or 'current'}"
            if cache_key in self.cache:
                cached_data, cached_time = self.cache[cache_key]
                if datetime.now() - cached_time < self.cache_duration:
                    logger.debug("Selfies servis depuis le cache")
                    return cached_data
            
            # Déterminer le mois à utiliser
            if not month:
                month = datetime.now().strftime("%Y-%m")
            
            month_path = self.base_selfie_path / month
            
            if not month_path.exists():
                logger.warning(f"Dossier selfie inexistant: {month_path}")
                return []
            
            # Récupérer tous les selfies du mois
            selfies = []
            for file_path in month_path.iterdir():
                if self._is_valid_selfie_file(file_path):
                    selfie_info = self._get_selfie_info(file_path, month)
                    if selfie_info:
                        selfies.append(selfie_info)
            
            # Trier par date de création (plus récent en premier)
            selfies.sort(key=lambda x: x['taken_at'], reverse=True)
            
            # Limiter le nombre de résultats
            result = selfies[:limit]
            
            # Mettre en cache
            self.cache[cache_key] = (result, datetime.now())
            
            logger.info(f"Récupéré {len(result)} selfies pour {month}")
            return result
            
        except Exception as e:
            logger.error(f"Erreur récupération selfies: {str(e)}")
            return []
    
    def _is_valid_selfie_file(self, file_path: Path) -> bool:
        """Vérifier si un fichier est un selfie valide"""
        try:
            if not file_path.is_file():
                return False
            
            # Vérifier l'extension
            if file_path.suffix.lower() not in self.allowed_extensions:
                return False
            
            # Ignorer les fichiers système
            if file_path.name.startswith('.'):
                return False
            
            # Vérifier la taille minimale (éviter les fichiers corrompus)
            if file_path.stat().st_size < 1024:  # 1KB minimum
                return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Erreur validation selfie {file_path}: {str(e)}")
            return False
    
    def _get_selfie_info(self, file_path: Path, month: str) -> Optional[Dict[str, Any]]:
        """Obtenir les informations d'un selfie"""
        try:
            stat = file_path.stat()
            
            # Extraire le nom du client depuis le nom du fichier si possible
            client_name = self._extract_client_name(file_path.name)
            
            # Construire le chemin web
            web_path = f"/static/selfies/{month}/{file_path.name}"
            
            selfie_info = {
                'filename': file_path.name,
                'path': web_path,
                'client_name': client_name,
                'taken_at': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'file_size': stat.st_size,
                'file_size_kb': round(stat.st_size / 1024, 2),
                'month': month,
                'is_recent': self._is_recent_selfie(stat.st_ctime),
                'display_time': datetime.fromtimestamp(stat.st_ctime).strftime('%H:%M'),
                'display_date': datetime.fromtimestamp(stat.st_ctime).strftime('%d/%m/%Y')
            }
            
            return selfie_info
            
        except Exception as e:
            logger.error(f"Erreur info selfie {file_path}: {str(e)}")
            return None
    
    def _extract_client_name(self, filename: str) -> Optional[str]:
        """
        Extraire le nom du client depuis le nom du fichier
        Convention: selfie_CLIENTNAME_timestamp.jpg ou CLIENTNAME_selfie.jpg
        """
        try:
            # Supprimer l'extension
            name_without_ext = filename.rsplit('.', 1)[0]
            
            # Patterns courants
            parts = name_without_ext.split('_')
            
            # Pattern: selfie_CLIENTNAME_timestamp
            if len(parts) >= 2 and parts[0].lower() == 'selfie':
                return parts[1].capitalize()
            
            # Pattern: CLIENTNAME_selfie
            if len(parts) >= 2 and parts[-1].lower() == 'selfie':
                return parts[0].capitalize()
            
            # Pattern: CLIENTNAME_timestamp
            if len(parts) >= 2 and parts[-1].isdigit():
                return parts[0].capitalize()
            
            # Si aucun pattern ne correspond, utiliser le premier segment
            if len(parts) >= 1 and not parts[0].isdigit():
                return parts[0].capitalize()
            
            return None
            
        except Exception as e:
            logger.warning(f"Erreur extraction nom client: {str(e)}")
            return None
    
    def _is_recent_selfie(self, timestamp: float, hours: int = 24) -> bool:
        """Vérifier si un selfie est récent"""
        try:
            selfie_time = datetime.fromtimestamp(timestamp)
            cutoff_time = datetime.now() - timedelta(hours=hours)
            return selfie_time > cutoff_time
        except Exception:
            return False
    
    def get_selfie_stats(self) -> Dict[str, Any]:
        """Obtenir les statistiques des selfies"""
        try:
            stats = {
                'total_selfies': 0,
                'months_with_selfies': 0,
                'latest_selfie': None,
                'monthly_stats': {},
                'recent_count': 0,
                'total_size_mb': 0
            }
            
            if not self.base_selfie_path.exists():
                return stats
            
            # Parcourir tous les dossiers de mois
            for month_dir in self.base_selfie_path.iterdir():
                if not month_dir.is_dir() or not month_dir.name.count('-') == 1:
                    continue
                
                try:
                    # Compter les selfies de ce mois
                    month_selfies = []
                    month_size = 0
                    
                    for file_path in month_dir.iterdir():
                        if self._is_valid_selfie_file(file_path):
                            month_selfies.append(file_path)
                            month_size += file_path.stat().st_size
                            stats['total_selfies'] += 1
                    
                    if month_selfies:
                        stats['months_with_selfies'] += 1
                        stats['total_size_mb'] += month_size / (1024 * 1024)
                        
                        # Stats mensuelles
                        stats['monthly_stats'][month_dir.name] = {
                            'count': len(month_selfies),
                            'size_mb': round(month_size / (1024 * 1024), 2),
                            'latest': max(month_selfies, key=lambda x: x.stat().st_ctime).name
                        }
                        
                        # Compter les récents (dernières 24h)
                        cutoff_time = datetime.now() - timedelta(hours=24)
                        for selfie_file in month_selfies:
                            if datetime.fromtimestamp(selfie_file.stat().st_ctime) > cutoff_time:
                                stats['recent_count'] += 1
                                
                except Exception as e:
                    logger.warning(f"Erreur stats mois {month_dir.name}: {str(e)}")
                    continue
            
            # Arrondir la taille totale
            stats['total_size_mb'] = round(stats['total_size_mb'], 2)
            
            # Trouver le dernier selfie global
            if stats['total_selfies'] > 0:
                try:
                    all_selfies = []
                    for month_dir in self.base_selfie_path.iterdir():
                        if month_dir.is_dir():
                            for file_path in month_dir.iterdir():
                                if self._is_valid_selfie_file(file_path):
                                    all_selfies.append(file_path)
                    
                    if all_selfies:
                        latest_file = max(all_selfies, key=lambda x: x.stat().st_ctime)
                        stats['latest_selfie'] = {
                            'filename': latest_file.name,
                            'month': latest_file.parent.name,
                            'taken_at': datetime.fromtimestamp(latest_file.stat().st_ctime).isoformat()
                        }
                        
                except Exception as e:
                    logger.warning(f"Erreur recherche dernier selfie: {str(e)}")
            
            return stats
            
        except Exception as e:
            logger.error(f"Erreur calcul stats selfies: {str(e)}")
            return {'error': str(e)}
    
    def get_selfies_by_month(self, month: str) -> List[Dict[str, Any]]:
        """
        Récupérer tous les selfies d'un mois donné
        
        Args:
            month: Mois au format YYYY-MM
            
        Returns:
            Liste complète des selfies du mois
        """
        try:
            month_path = self.base_selfie_path / month
            
            if not month_path.exists():
                return []
            
            selfies = []
            for file_path in month_path.iterdir():
                if self._is_valid_selfie_file(file_path):
                    selfie_info = self._get_selfie_info(file_path, month)
                    if selfie_info:
                        selfies.append(selfie_info)
            
            # Trier par date de création
            selfies.sort(key=lambda x: x['taken_at'], reverse=True)
            
            return selfies
            
        except Exception as e:
            logger.error(f"Erreur récupération selfies mois {month}: {str(e)}")
            return []
    
    def get_available_months(self) -> List[str]:
        """Obtenir la liste des mois avec des selfies"""
        try:
            months = []
            
            if not self.base_selfie_path.exists():
                return months
            
            for month_dir in self.base_selfie_path.iterdir():
                if month_dir.is_dir() and month_dir.name.count('-') == 1:
                    # Vérifier s'il y a des selfies dans ce mois
                    has_selfies = any(
                        self._is_valid_selfie_file(f) 
                        for f in month_dir.iterdir()
                    )
                    
                    if has_selfies:
                        months.append(month_dir.name)
            
            # Trier par ordre chronologique (plus récent en premier)
            months.sort(reverse=True)
            
            return months
            
        except Exception as e:
            logger.error(f"Erreur récupération mois disponibles: {str(e)}")
            return []
    
    def search_selfies(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Rechercher des selfies par nom de client
        
        Args:
            query: Terme de recherche (nom du client)
            limit: Nombre maximum de résultats
            
        Returns:
            Liste des selfies correspondants
        """
        try:
            query_lower = query.lower()
            results = []
            
            # Parcourir tous les mois
            for month_dir in self.base_selfie_path.iterdir():
                if not month_dir.is_dir():
                    continue
                
                month = month_dir.name
                for file_path in month_dir.iterdir():
                    if self._is_valid_selfie_file(file_path):
                        client_name = self._extract_client_name(file_path.name)
                        
                        # Recherche dans le nom du client ou du fichier
                        if (client_name and query_lower in client_name.lower()) or \
                           query_lower in file_path.name.lower():
                            
                            selfie_info = self._get_selfie_info(file_path, month)
                            if selfie_info:
                                results.append(selfie_info)
            
            # Trier par date (plus récent en premier)
            results.sort(key=lambda x: x['taken_at'], reverse=True)
            
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Erreur recherche selfies: {str(e)}")
            return []
    
    def cleanup_old_selfies(self, keep_months: int = 6) -> Dict[str, Any]:
        """
        Nettoyer les anciens selfies
        
        Args:
            keep_months: Nombre de mois à conserver
            
        Returns:
            Résultats du nettoyage
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=keep_months * 30)
            cutoff_month = cutoff_date.strftime("%Y-%m")
            
            deleted_files = 0
            deleted_dirs = 0
            total_size_freed = 0
            
            for month_dir in self.base_selfie_path.iterdir():
                if not month_dir.is_dir() or month_dir.name >= cutoff_month:
                    continue
                
                # Supprimer tous les fichiers du mois
                for file_path in month_dir.iterdir():
                    if file_path.is_file() and file_path.name != '.gitkeep':
                        try:
                            total_size_freed += file_path.stat().st_size
                            file_path.unlink()
                            deleted_files += 1
                        except Exception as e:
                            logger.warning(f"Impossible de supprimer {file_path}: {str(e)}")
                
                # Supprimer le dossier s'il est vide (sauf .gitkeep)
                remaining_files = [f for f in month_dir.iterdir() if f.name != '.gitkeep']
                if not remaining_files:
                    try:
                        # Garder le .gitkeep mais le dossier peut être considéré comme nettoyé
                        deleted_dirs += 1
                        logger.info(f"Dossier nettoyé: {month_dir}")
                    except Exception as e:
                        logger.warning(f"Impossible de marquer comme nettoyé {month_dir}: {str(e)}")
            
            # Vider le cache
            self.clear_cache()
            
            result = {
                'deleted_files': deleted_files,
                'deleted_directories': deleted_dirs,
                'size_freed_mb': round(total_size_freed / (1024 * 1024), 2),
                'cutoff_date': cutoff_month
            }
            
            logger.info(f"Nettoyage selfies terminé: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Erreur nettoyage selfies: {str(e)}")
            return {'error': str(e)}
    
    def clear_cache(self):
        """Vider le cache des selfies"""
        self.cache.clear()
        logger.info("Cache selfies vidé")
    
    def test_module_connectivity(self) -> Dict[str, Any]:
        """Tester la connectivité du module selfie"""
        try:
            # Vérifier que le dossier base existe
            if not self.base_selfie_path.exists():
                return {
                    'success': False,
                    'error': f'Dossier base inexistant: {self.base_selfie_path}'
                }
            
            # Obtenir les statistiques
            stats = self.get_selfie_stats()
            
            # Tenter de récupérer les derniers selfies
            latest_selfies = self.get_latest_selfies(limit=1)
            
            return {
                'success': True,
                'path': str(self.base_selfie_path),
                'total_selfies': stats.get('total_selfies', 0),
                'available_months': len(self.get_available_months()),
                'latest_selfie': latest_selfies[0] if latest_selfies else None,
                'storage_mb': stats.get('total_size_mb', 0)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


# Instance globale du service selfie
selfie_service = SelfieService()

# Fonctions d'interface pour compatibilité
def get_latest_selfies(limit: int = 3, month: Optional[str] = None) -> List[Dict[str, Any]]:
    """Interface pour récupérer les derniers selfies"""
    return selfie_service.get_latest_selfies(limit, month)

def get_selfie_stats() -> Dict[str, Any]:
    """Interface pour les statistiques selfies"""
    return selfie_service.get_selfie_stats()

def get_selfies_by_month(month: str) -> List[Dict[str, Any]]:
    """Interface pour les selfies par mois"""
    return selfie_service.get_selfies_by_month(month)

def search_selfies(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Interface pour la recherche de selfies"""
    return selfie_service.search_selfies(query, limit)

def test_selfie_connectivity() -> Dict[str, Any]:
    """Interface pour tester la connectivité"""
    return selfie_service.test_module_connectivity()