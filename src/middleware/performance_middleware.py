import time
import logging
from functools import wraps
from flask import request, g
from src.services.performance_optimizer import performance_optimizer

logger = logging.getLogger(__name__)

class PerformanceMiddleware:
    """Middleware Flask pour le monitoring et l'optimisation des performances"""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialise le middleware avec l'application Flask"""
        app.before_request(self.before_request)
        app.after_request(self.after_request)
        app.teardown_appcontext(self.teardown_request)
        
        # Démarrer le monitoring des performances
        performance_optimizer.start_monitoring()
        
        logger.info("Middleware de performance initialisé")
    
    def before_request(self):
        """Exécuté avant chaque requête"""
        g.start_time = time.time()
        g.endpoint = request.endpoint or 'unknown'
        
        # Vérifier le cache pour les requêtes GET
        if request.method == 'GET':
            cache_key = self._generate_cache_key(request)
            cached_response = performance_optimizer.get_cache(cache_key)
            if cached_response:
                logger.debug(f"Cache hit pour {cache_key}")
                return cached_response
    
    def after_request(self, response):
        """Exécuté après chaque requête"""
        if hasattr(g, 'start_time'):
            response_time = time.time() - g.start_time
            
            # Enregistrer le temps de réponse
            performance_optimizer.record_response_time(g.endpoint, response_time)
            
            # Mettre en cache les réponses GET réussies
            if (request.method == 'GET' and 
                response.status_code == 200 and 
                self._is_cacheable_endpoint(g.endpoint)):
                
                cache_key = self._generate_cache_key(request)
                cache_ttl = self._get_cache_ttl(g.endpoint)
                performance_optimizer.set_cache(cache_key, response, cache_ttl)
                logger.debug(f"Réponse mise en cache: {cache_key}")
            
            # Ajouter des headers de performance
            response.headers['X-Response-Time'] = f"{response_time:.3f}s"
            response.headers['X-Cache-Status'] = 'MISS'  # Sera 'HIT' si depuis le cache
            
            # Log des requêtes lentes
            if response_time > 2.0:
                logger.warning(f"Requête lente détectée: {g.endpoint} - {response_time:.3f}s")
        
        return response
    
    def teardown_request(self, exception):
        """Exécuté à la fin de chaque requête"""
        if exception:
            logger.error(f"Exception dans la requête {g.endpoint}: {exception}")
    
    def _generate_cache_key(self, request):
        """Génère une clé de cache pour la requête"""
        # Inclure l'URL, les paramètres de requête et les headers pertinents
        key_parts = [
            request.path,
            str(sorted(request.args.items())),
            request.headers.get('Accept', ''),
            request.headers.get('Accept-Language', '')
        ]
        return '|'.join(key_parts)
    
    def _is_cacheable_endpoint(self, endpoint):
        """Détermine si un endpoint peut être mis en cache"""
        # Endpoints qui peuvent être mis en cache (lecture seule)
        cacheable_endpoints = [
            'labs.get_labs',
            'labs.get_lab',
            'ssl.get_ssl_status',
            'ssl.get_certificates',
            'remote_access.get_connection_info'
        ]
        return endpoint in cacheable_endpoints
    
    def _get_cache_ttl(self, endpoint):
        """Détermine le TTL du cache pour un endpoint"""
        # TTL personnalisés par endpoint
        ttl_mapping = {
            'labs.get_labs': 60,        # 1 minute
            'labs.get_lab': 30,         # 30 secondes
            'ssl.get_ssl_status': 300,  # 5 minutes
            'ssl.get_certificates': 600, # 10 minutes
            'remote_access.get_connection_info': 10  # 10 secondes
        }
        return ttl_mapping.get(endpoint, 300)  # 5 minutes par défaut

def monitor_performance(func):
    """Décorateur pour monitorer les performances d'une fonction"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            execution_time = time.time() - start_time
            performance_optimizer.record_response_time(
                f"{func.__module__}.{func.__name__}", 
                execution_time
            )
            
            if execution_time > 1.0:
                logger.warning(f"Fonction lente: {func.__name__} - {execution_time:.3f}s")
    
    return wrapper

def cache_result(ttl=300):
    """Décorateur pour mettre en cache le résultat d'une fonction"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Générer une clé de cache basée sur la fonction et ses arguments
            cache_key = f"{func.__module__}.{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            
            # Vérifier le cache
            cached_result = performance_optimizer.get_cache(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Exécuter la fonction et mettre en cache le résultat
            result = func(*args, **kwargs)
            performance_optimizer.set_cache(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator

def rate_limit(max_requests=100, window_seconds=60):
    """Décorateur pour limiter le taux de requêtes"""
    def decorator(func):
        request_counts = {}
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_time = time.time()
            client_id = request.remote_addr if request else 'unknown'
            
            # Nettoyer les anciens compteurs
            cutoff_time = current_time - window_seconds
            request_counts[client_id] = [
                timestamp for timestamp in request_counts.get(client_id, [])
                if timestamp > cutoff_time
            ]
            
            # Vérifier la limite
            if len(request_counts[client_id]) >= max_requests:
                logger.warning(f"Rate limit dépassé pour {client_id}")
                from flask import jsonify
                return jsonify({'error': 'Rate limit exceeded'}), 429
            
            # Enregistrer la requête
            request_counts[client_id].append(current_time)
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

class ConnectionPoolManager:
    """Gestionnaire de pool de connexions optimisé"""
    
    def __init__(self):
        self.pools = {}
    
    def get_connection(self, pool_name, connection_factory):
        """Récupère une connexion du pool ou en crée une nouvelle"""
        if pool_name not in self.pools:
            self.pools[pool_name] = []
        
        pool = self.pools[pool_name]
        
        # Réutiliser une connexion existante si disponible
        for conn in pool:
            if not conn.get('in_use', False):
                conn['in_use'] = True
                conn['last_used'] = time.time()
                performance_optimizer.update_connection_activity(conn['id'])
                return conn
        
        # Créer une nouvelle connexion si le pool n'est pas plein
        max_pool_size = performance_optimizer.optimization_rules['max_concurrent_connections']
        if len(pool) < max_pool_size:
            new_conn = connection_factory()
            new_conn.update({
                'id': f"{pool_name}_{len(pool)}",
                'in_use': True,
                'created_at': time.time(),
                'last_used': time.time()
            })
            pool.append(new_conn)
            performance_optimizer.register_connection(new_conn['id'], new_conn)
            return new_conn
        
        return None  # Pool plein
    
    def release_connection(self, pool_name, connection_id):
        """Libère une connexion dans le pool"""
        if pool_name in self.pools:
            for conn in self.pools[pool_name]:
                if conn['id'] == connection_id:
                    conn['in_use'] = False
                    conn['last_used'] = time.time()
                    break
    
    def cleanup_idle_connections(self, max_idle_time=300):
        """Nettoie les connexions inactives"""
        current_time = time.time()
        
        for pool_name, pool in self.pools.items():
            idle_connections = []
            for conn in pool:
                if (not conn.get('in_use', False) and 
                    current_time - conn.get('last_used', 0) > max_idle_time):
                    idle_connections.append(conn)
            
            for conn in idle_connections:
                pool.remove(conn)
                performance_optimizer.unregister_connection(conn['id'])
                logger.debug(f"Connexion inactive supprimée: {conn['id']}")

# Instance globale du gestionnaire de pool
connection_pool_manager = ConnectionPoolManager()

