from flask import Blueprint, request, jsonify
import logging
from src.services.performance_optimizer import performance_optimizer
from src.middleware.performance_middleware import monitor_performance

logger = logging.getLogger(__name__)

performance_bp = Blueprint('performance', __name__, url_prefix='/api/performance')

@performance_bp.route('/metrics', methods=['GET'])
@monitor_performance
def get_performance_metrics():
    """Récupère les métriques de performance actuelles"""
    try:
        metrics = performance_optimizer.get_performance_metrics()
        return jsonify({
            'success': True,
            'metrics': metrics
        })
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des métriques: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@performance_bp.route('/history', methods=['GET'])
@monitor_performance
def get_performance_history():
    """Récupère l'historique des performances"""
    try:
        duration = request.args.get('duration', 60, type=int)  # minutes
        history = performance_optimizer.get_performance_history(duration)
        
        return jsonify({
            'success': True,
            'history': history,
            'duration_minutes': duration
        })
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de l'historique: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@performance_bp.route('/recommendations', methods=['GET'])
@monitor_performance
def get_optimization_recommendations():
    """Récupère les recommandations d'optimisation"""
    try:
        recommendations = performance_optimizer.get_optimization_recommendations()
        return jsonify({
            'success': True,
            'recommendations': recommendations,
            'count': len(recommendations)
        })
    except Exception as e:
        logger.error(f"Erreur lors de la génération des recommandations: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@performance_bp.route('/optimization-rules', methods=['GET'])
@monitor_performance
def get_optimization_rules():
    """Récupère les règles d'optimisation actuelles"""
    try:
        return jsonify({
            'success': True,
            'rules': performance_optimizer.optimization_rules
        })
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des règles: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@performance_bp.route('/optimization-rules', methods=['PUT'])
@monitor_performance
def update_optimization_rules():
    """Met à jour les règles d'optimisation"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Données requises'
            }), 400
        
        # Valider les règles
        valid_rules = {
            'max_concurrent_connections',
            'connection_timeout',
            'cache_ttl_default',
            'memory_threshold',
            'cpu_threshold',
            'cleanup_interval'
        }
        
        invalid_rules = set(data.keys()) - valid_rules
        if invalid_rules:
            return jsonify({
                'success': False,
                'error': f'Règles invalides: {list(invalid_rules)}'
            }), 400
        
        # Valider les valeurs
        for key, value in data.items():
            if not isinstance(value, (int, float)) or value <= 0:
                return jsonify({
                    'success': False,
                    'error': f'Valeur invalide pour {key}: {value}'
                }), 400
        
        # Mettre à jour les règles
        performance_optimizer.update_optimization_rules(data)
        
        return jsonify({
            'success': True,
            'message': 'Règles d\'optimisation mises à jour',
            'updated_rules': data
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour des règles: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@performance_bp.route('/monitoring/start', methods=['POST'])
@monitor_performance
def start_monitoring():
    """Démarre le monitoring des performances"""
    try:
        if performance_optimizer.monitoring_active:
            return jsonify({
                'success': True,
                'message': 'Monitoring déjà actif'
            })
        
        performance_optimizer.start_monitoring()
        
        return jsonify({
            'success': True,
            'message': 'Monitoring des performances démarré'
        })
        
    except Exception as e:
        logger.error(f"Erreur lors du démarrage du monitoring: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@performance_bp.route('/monitoring/stop', methods=['POST'])
@monitor_performance
def stop_monitoring():
    """Arrête le monitoring des performances"""
    try:
        if not performance_optimizer.monitoring_active:
            return jsonify({
                'success': True,
                'message': 'Monitoring déjà arrêté'
            })
        
        performance_optimizer.stop_monitoring()
        
        return jsonify({
            'success': True,
            'message': 'Monitoring des performances arrêté'
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de l'arrêt du monitoring: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@performance_bp.route('/cache/stats', methods=['GET'])
@monitor_performance
def get_cache_stats():
    """Récupère les statistiques du cache"""
    try:
        cache_size = len(performance_optimizer.cache)
        cache_keys = list(performance_optimizer.cache.keys())[:10]  # Premiers 10 pour exemple
        
        return jsonify({
            'success': True,
            'cache_stats': {
                'size': cache_size,
                'sample_keys': cache_keys,
                'ttl_count': len(performance_optimizer.cache_ttl)
            }
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des stats du cache: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@performance_bp.route('/cache/clear', methods=['POST'])
@monitor_performance
def clear_cache():
    """Vide le cache"""
    try:
        cache_size_before = len(performance_optimizer.cache)
        
        performance_optimizer.cache.clear()
        performance_optimizer.cache_ttl.clear()
        
        return jsonify({
            'success': True,
            'message': f'Cache vidé ({cache_size_before} entrées supprimées)'
        })
        
    except Exception as e:
        logger.error(f"Erreur lors du vidage du cache: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@performance_bp.route('/connections', methods=['GET'])
@monitor_performance
def get_active_connections():
    """Récupère les connexions actives"""
    try:
        connections = []
        for conn_id, conn_data in performance_optimizer.connection_pool.items():
            connections.append({
                'id': conn_id,
                'created_at': conn_data.get('created_at'),
                'last_activity': conn_data.get('last_activity'),
                'type': conn_data.get('connection_type', 'unknown')
            })
        
        return jsonify({
            'success': True,
            'connections': connections,
            'count': len(connections),
            'max_connections': performance_optimizer.optimization_rules['max_concurrent_connections']
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des connexions: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@performance_bp.route('/connections/cleanup', methods=['POST'])
@monitor_performance
def cleanup_connections():
    """Force le nettoyage des connexions expirées"""
    try:
        aggressive = request.args.get('aggressive', 'false').lower() == 'true'
        
        connections_before = len(performance_optimizer.connection_pool)
        performance_optimizer.cleanup_expired_connections(aggressive=aggressive)
        connections_after = len(performance_optimizer.connection_pool)
        
        cleaned_count = connections_before - connections_after
        
        return jsonify({
            'success': True,
            'message': f'{cleaned_count} connexions nettoyées',
            'connections_before': connections_before,
            'connections_after': connections_after,
            'aggressive': aggressive
        })
        
    except Exception as e:
        logger.error(f"Erreur lors du nettoyage des connexions: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@performance_bp.route('/system-info', methods=['GET'])
@monitor_performance
def get_system_info():
    """Récupère les informations système"""
    try:
        import psutil
        import platform
        
        # Informations système
        system_info = {
            'platform': platform.system(),
            'platform_release': platform.release(),
            'platform_version': platform.version(),
            'architecture': platform.machine(),
            'processor': platform.processor(),
            'cpu_count': psutil.cpu_count(),
            'cpu_count_logical': psutil.cpu_count(logical=True),
            'memory_total': psutil.virtual_memory().total,
            'memory_available': psutil.virtual_memory().available,
            'disk_usage': dict(psutil.disk_usage('/')._asdict()),
            'boot_time': psutil.boot_time()
        }
        
        # Processus Python actuel
        process = psutil.Process()
        process_info = {
            'pid': process.pid,
            'memory_info': dict(process.memory_info()._asdict()),
            'cpu_percent': process.cpu_percent(),
            'num_threads': process.num_threads(),
            'create_time': process.create_time()
        }
        
        return jsonify({
            'success': True,
            'system_info': system_info,
            'process_info': process_info
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des infos système: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@performance_bp.route('/health', methods=['GET'])
@monitor_performance
def health_check():
    """Point de contrôle de santé de l'application"""
    try:
        metrics = performance_optimizer.get_performance_metrics()
        recommendations = performance_optimizer.get_optimization_recommendations()
        
        # Déterminer l'état de santé
        health_status = 'healthy'
        issues = []
        
        # Vérifier les seuils critiques
        if metrics['system']['cpu_usage_current'] > 90:
            health_status = 'critical'
            issues.append('CPU usage critique')
        elif metrics['system']['cpu_usage_current'] > 80:
            health_status = 'warning'
            issues.append('CPU usage élevé')
        
        if metrics['system']['memory_usage_current'] > 90:
            health_status = 'critical'
            issues.append('Memory usage critique')
        elif metrics['system']['memory_usage_current'] > 80:
            health_status = 'warning'
            issues.append('Memory usage élevé')
        
        # Vérifier les connexions
        connection_ratio = (metrics['application']['active_connections'] / 
                          metrics['application']['max_connections'])
        if connection_ratio > 0.95:
            health_status = 'critical'
            issues.append('Connexions proches de la limite')
        elif connection_ratio > 0.8:
            if health_status == 'healthy':
                health_status = 'warning'
            issues.append('Nombre de connexions élevé')
        
        return jsonify({
            'success': True,
            'health_status': health_status,
            'issues': issues,
            'monitoring_active': metrics['monitoring_active'],
            'recommendations_count': len(recommendations),
            'timestamp': metrics['timestamp']
        })
        
    except Exception as e:
        logger.error(f"Erreur lors du contrôle de santé: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'health_status': 'error'
        }), 500

