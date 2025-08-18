import asyncio
import logging
import time
import psutil
import threading
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import deque
import json

logger = logging.getLogger(__name__)

class PerformanceOptimizer:
    """Service d'optimisation des performances pour l'application Lab Creator"""
    
    def __init__(self):
        self.metrics = {
            'cpu_usage': deque(maxlen=100),
            'memory_usage': deque(maxlen=100),
            'network_io': deque(maxlen=100),
            'disk_io': deque(maxlen=100),
            'active_connections': deque(maxlen=100),
            'response_times': deque(maxlen=100)
        }
        
        self.connection_pool = {}
        self.cache = {}
        self.cache_ttl = {}
        self.monitoring_active = False
        self.optimization_rules = {
            'max_concurrent_connections': 50,
            'connection_timeout': 300,  # 5 minutes
            'cache_ttl_default': 300,   # 5 minutes
            'memory_threshold': 80,     # %
            'cpu_threshold': 85,        # %
            'cleanup_interval': 60      # seconds
        }
        
    def start_monitoring(self):
        """Démarre le monitoring des performances"""
        if self.monitoring_active:
            return
            
        self.monitoring_active = True
        
        # Thread pour collecter les métriques système
        metrics_thread = threading.Thread(target=self._collect_system_metrics, daemon=True)
        metrics_thread.start()
        
        # Thread pour le nettoyage automatique
        cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        cleanup_thread.start()
        
        logger.info("Monitoring des performances démarré")
    
    def stop_monitoring(self):
        """Arrête le monitoring des performances"""
        self.monitoring_active = False
        logger.info("Monitoring des performances arrêté")
    
    def _collect_system_metrics(self):
        """Collecte les métriques système en continu"""
        while self.monitoring_active:
            try:
                # CPU et mémoire
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                
                # I/O réseau et disque
                net_io = psutil.net_io_counters()
                disk_io = psutil.disk_io_counters()
                
                # Stocker les métriques
                timestamp = time.time()
                self.metrics['cpu_usage'].append((timestamp, cpu_percent))
                self.metrics['memory_usage'].append((timestamp, memory.percent))
                
                if net_io:
                    self.metrics['network_io'].append((timestamp, {
                        'bytes_sent': net_io.bytes_sent,
                        'bytes_recv': net_io.bytes_recv
                    }))
                
                if disk_io:
                    self.metrics['disk_io'].append((timestamp, {
                        'read_bytes': disk_io.read_bytes,
                        'write_bytes': disk_io.write_bytes
                    }))
                
                # Connexions actives
                active_conns = len(self.connection_pool)
                self.metrics['active_connections'].append((timestamp, active_conns))
                
                # Vérifier les seuils et optimiser si nécessaire
                self._check_thresholds_and_optimize()
                
            except Exception as e:
                logger.error(f"Erreur lors de la collecte des métriques: {e}")
            
            time.sleep(5)  # Collecte toutes les 5 secondes
    
    def _cleanup_loop(self):
        """Boucle de nettoyage automatique"""
        while self.monitoring_active:
            try:
                self.cleanup_expired_connections()
                self.cleanup_expired_cache()
                time.sleep(self.optimization_rules['cleanup_interval'])
            except Exception as e:
                logger.error(f"Erreur lors du nettoyage: {e}")
    
    def _check_thresholds_and_optimize(self):
        """Vérifie les seuils et applique les optimisations"""
        if not self.metrics['cpu_usage'] or not self.metrics['memory_usage']:
            return
        
        current_cpu = self.metrics['cpu_usage'][-1][1]
        current_memory = self.metrics['memory_usage'][-1][1]
        
        # Optimisation si CPU élevé
        if current_cpu > self.optimization_rules['cpu_threshold']:
            self._optimize_cpu_usage()
        
        # Optimisation si mémoire élevée
        if current_memory > self.optimization_rules['memory_threshold']:
            self._optimize_memory_usage()
    
    def _optimize_cpu_usage(self):
        """Optimise l'utilisation CPU"""
        logger.warning("CPU usage élevé, application d'optimisations")
        
        # Réduire le nombre de connexions simultanées
        max_conns = max(10, self.optimization_rules['max_concurrent_connections'] // 2)
        self._limit_concurrent_connections(max_conns)
        
        # Augmenter les timeouts pour réduire la charge
        self.optimization_rules['connection_timeout'] = min(600, 
            self.optimization_rules['connection_timeout'] * 1.5)
    
    def _optimize_memory_usage(self):
        """Optimise l'utilisation mémoire"""
        logger.warning("Utilisation mémoire élevée, application d'optimisations")
        
        # Nettoyer le cache agressivement
        self._aggressive_cache_cleanup()
        
        # Fermer les connexions inactives
        self.cleanup_expired_connections(aggressive=True)
    
    def _limit_concurrent_connections(self, max_connections: int):
        """Limite le nombre de connexions simultanées"""
        if len(self.connection_pool) <= max_connections:
            return
        
        # Trier par dernière activité et fermer les plus anciennes
        sorted_connections = sorted(
            self.connection_pool.items(),
            key=lambda x: x[1].get('last_activity', 0)
        )
        
        connections_to_close = len(self.connection_pool) - max_connections
        for i in range(connections_to_close):
            conn_id, conn_data = sorted_connections[i]
            self._close_connection(conn_id)
    
    def _aggressive_cache_cleanup(self):
        """Nettoyage agressif du cache"""
        # Réduire le TTL du cache
        current_time = time.time()
        expired_keys = []
        
        for key, ttl in self.cache_ttl.items():
            if current_time > ttl:
                expired_keys.append(key)
        
        # Supprimer aussi 50% du cache restant pour libérer de la mémoire
        remaining_keys = list(set(self.cache.keys()) - set(expired_keys))
        additional_cleanup = len(remaining_keys) // 2
        
        for key in expired_keys + remaining_keys[:additional_cleanup]:
            self.cache.pop(key, None)
            self.cache_ttl.pop(key, None)
        
        logger.info(f"Cache nettoyé: {len(expired_keys + remaining_keys[:additional_cleanup])} entrées supprimées")
    
    def register_connection(self, connection_id: str, connection_data: Dict):
        """Enregistre une nouvelle connexion"""
        if len(self.connection_pool) >= self.optimization_rules['max_concurrent_connections']:
            # Fermer la connexion la plus ancienne
            oldest_conn = min(
                self.connection_pool.items(),
                key=lambda x: x[1].get('created_at', 0)
            )
            self._close_connection(oldest_conn[0])
        
        self.connection_pool[connection_id] = {
            **connection_data,
            'created_at': time.time(),
            'last_activity': time.time()
        }
        
        logger.debug(f"Connexion enregistrée: {connection_id}")
    
    def update_connection_activity(self, connection_id: str):
        """Met à jour l'activité d'une connexion"""
        if connection_id in self.connection_pool:
            self.connection_pool[connection_id]['last_activity'] = time.time()
    
    def unregister_connection(self, connection_id: str):
        """Désenregistre une connexion"""
        if connection_id in self.connection_pool:
            del self.connection_pool[connection_id]
            logger.debug(f"Connexion désenregistrée: {connection_id}")
    
    def _close_connection(self, connection_id: str):
        """Ferme une connexion spécifique"""
        if connection_id in self.connection_pool:
            conn_data = self.connection_pool[connection_id]
            
            # Notifier la fermeture si callback disponible
            if 'close_callback' in conn_data:
                try:
                    conn_data['close_callback']()
                except Exception as e:
                    logger.error(f"Erreur lors de la fermeture de connexion {connection_id}: {e}")
            
            self.unregister_connection(connection_id)
            logger.info(f"Connexion fermée pour optimisation: {connection_id}")
    
    def cleanup_expired_connections(self, aggressive: bool = False):
        """Nettoie les connexions expirées"""
        current_time = time.time()
        timeout = self.optimization_rules['connection_timeout']
        
        if aggressive:
            timeout = timeout // 2  # Timeout plus agressif
        
        expired_connections = []
        for conn_id, conn_data in self.connection_pool.items():
            last_activity = conn_data.get('last_activity', conn_data.get('created_at', 0))
            if current_time - last_activity > timeout:
                expired_connections.append(conn_id)
        
        for conn_id in expired_connections:
            self._close_connection(conn_id)
        
        if expired_connections:
            logger.info(f"Connexions expirées nettoyées: {len(expired_connections)}")
    
    def set_cache(self, key: str, value: any, ttl: Optional[int] = None):
        """Définit une valeur dans le cache avec TTL"""
        if ttl is None:
            ttl = self.optimization_rules['cache_ttl_default']
        
        self.cache[key] = value
        self.cache_ttl[key] = time.time() + ttl
    
    def get_cache(self, key: str) -> Optional[any]:
        """Récupère une valeur du cache"""
        if key not in self.cache:
            return None
        
        # Vérifier l'expiration
        if time.time() > self.cache_ttl.get(key, 0):
            self.cache.pop(key, None)
            self.cache_ttl.pop(key, None)
            return None
        
        return self.cache[key]
    
    def cleanup_expired_cache(self):
        """Nettoie le cache expiré"""
        current_time = time.time()
        expired_keys = []
        
        for key, ttl in self.cache_ttl.items():
            if current_time > ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            self.cache.pop(key, None)
            self.cache_ttl.pop(key, None)
        
        if expired_keys:
            logger.debug(f"Cache expiré nettoyé: {len(expired_keys)} entrées")
    
    def record_response_time(self, endpoint: str, response_time: float):
        """Enregistre le temps de réponse d'un endpoint"""
        timestamp = time.time()
        self.metrics['response_times'].append((timestamp, {
            'endpoint': endpoint,
            'response_time': response_time
        }))
    
    def get_performance_metrics(self) -> Dict:
        """Récupère les métriques de performance actuelles"""
        current_time = time.time()
        
        # Calculer les moyennes sur les 5 dernières minutes
        five_minutes_ago = current_time - 300
        
        def calculate_average(metric_name: str, time_threshold: float) -> float:
            recent_metrics = [
                value for timestamp, value in self.metrics[metric_name]
                if timestamp > time_threshold
            ]
            return sum(recent_metrics) / len(recent_metrics) if recent_metrics else 0
        
        # Métriques système
        avg_cpu = calculate_average('cpu_usage', five_minutes_ago)
        avg_memory = calculate_average('memory_usage', five_minutes_ago)
        
        # Connexions actives
        current_connections = len(self.connection_pool)
        
        # Temps de réponse moyen
        recent_response_times = [
            data['response_time'] for timestamp, data in self.metrics['response_times']
            if timestamp > five_minutes_ago
        ]
        avg_response_time = sum(recent_response_times) / len(recent_response_times) if recent_response_times else 0
        
        # Taille du cache
        cache_size = len(self.cache)
        
        return {
            'timestamp': current_time,
            'system': {
                'cpu_usage_avg': round(avg_cpu, 2),
                'memory_usage_avg': round(avg_memory, 2),
                'cpu_usage_current': self.metrics['cpu_usage'][-1][1] if self.metrics['cpu_usage'] else 0,
                'memory_usage_current': self.metrics['memory_usage'][-1][1] if self.metrics['memory_usage'] else 0
            },
            'application': {
                'active_connections': current_connections,
                'max_connections': self.optimization_rules['max_concurrent_connections'],
                'cache_size': cache_size,
                'avg_response_time': round(avg_response_time, 3)
            },
            'optimization_rules': self.optimization_rules.copy(),
            'monitoring_active': self.monitoring_active
        }
    
    def get_performance_history(self, duration_minutes: int = 60) -> Dict:
        """Récupère l'historique des performances"""
        current_time = time.time()
        time_threshold = current_time - (duration_minutes * 60)
        
        history = {}
        for metric_name, metric_data in self.metrics.items():
            history[metric_name] = [
                {'timestamp': timestamp, 'value': value}
                for timestamp, value in metric_data
                if timestamp > time_threshold
            ]
        
        return history
    
    def update_optimization_rules(self, new_rules: Dict):
        """Met à jour les règles d'optimisation"""
        self.optimization_rules.update(new_rules)
        logger.info(f"Règles d'optimisation mises à jour: {new_rules}")
    
    def get_optimization_recommendations(self) -> List[Dict]:
        """Génère des recommandations d'optimisation"""
        recommendations = []
        metrics = self.get_performance_metrics()
        
        # Recommandations CPU
        if metrics['system']['cpu_usage_avg'] > 70:
            recommendations.append({
                'type': 'cpu',
                'severity': 'high' if metrics['system']['cpu_usage_avg'] > 85 else 'medium',
                'message': f"Utilisation CPU élevée ({metrics['system']['cpu_usage_avg']}%)",
                'suggestions': [
                    "Réduire le nombre de connexions simultanées",
                    "Optimiser les requêtes de base de données",
                    "Implémenter plus de mise en cache"
                ]
            })
        
        # Recommandations mémoire
        if metrics['system']['memory_usage_avg'] > 70:
            recommendations.append({
                'type': 'memory',
                'severity': 'high' if metrics['system']['memory_usage_avg'] > 85 else 'medium',
                'message': f"Utilisation mémoire élevée ({metrics['system']['memory_usage_avg']}%)",
                'suggestions': [
                    "Nettoyer le cache plus fréquemment",
                    "Réduire la taille du cache",
                    "Fermer les connexions inactives plus rapidement"
                ]
            })
        
        # Recommandations connexions
        connection_ratio = metrics['application']['active_connections'] / metrics['application']['max_connections']
        if connection_ratio > 0.8:
            recommendations.append({
                'type': 'connections',
                'severity': 'medium',
                'message': f"Nombre de connexions proche de la limite ({metrics['application']['active_connections']}/{metrics['application']['max_connections']})",
                'suggestions': [
                    "Augmenter la limite de connexions simultanées",
                    "Optimiser la gestion des connexions",
                    "Implémenter une file d'attente pour les connexions"
                ]
            })
        
        # Recommandations temps de réponse
        if metrics['application']['avg_response_time'] > 1.0:
            recommendations.append({
                'type': 'response_time',
                'severity': 'medium',
                'message': f"Temps de réponse élevé ({metrics['application']['avg_response_time']}s)",
                'suggestions': [
                    "Optimiser les requêtes de base de données",
                    "Implémenter plus de mise en cache",
                    "Utiliser la compression des réponses"
                ]
            })
        
        return recommendations

# Instance globale
performance_optimizer = PerformanceOptimizer()

