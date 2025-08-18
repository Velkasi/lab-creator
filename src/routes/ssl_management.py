from flask import Blueprint, request, jsonify
import logging
from src.services.ssl_manager import ssl_manager

logger = logging.getLogger(__name__)

ssl_bp = Blueprint('ssl', __name__, url_prefix='/api/ssl')

@ssl_bp.route('/status', methods=['GET'])
def get_ssl_status():
    """Récupère le statut de la configuration SSL/TLS"""
    try:
        # Vérifier si Caddy est installé
        caddy_installed = ssl_manager.is_caddy_installed()
        
        if not caddy_installed:
            return jsonify({
                'success': True,
                'ssl_enabled': False,
                'caddy_installed': False,
                'message': 'Caddy n\'est pas installé'
            })
        
        # Récupérer le statut du service
        caddy_status = ssl_manager.get_caddy_status()
        
        # Récupérer les informations sur les certificats
        certificates = ssl_manager.get_certificates_info()
        
        return jsonify({
            'success': True,
            'ssl_enabled': caddy_status['active'],
            'caddy_installed': True,
            'caddy_active': caddy_status['active'],
            'caddy_enabled': caddy_status['enabled'],
            'certificates': len(certificates),
            'certificate_details': certificates[:5]  # Limiter à 5 certificats
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du statut SSL: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ssl_bp.route('/setup', methods=['POST'])
def setup_ssl():
    """Configure SSL/TLS pour un domaine"""
    try:
        data = request.get_json()
        
        # Validation des paramètres
        domain = data.get('domain')
        if not domain:
            return jsonify({
                'success': False,
                'error': 'Domaine requis'
            }), 400
        
        email = data.get('email')
        flask_port = data.get('flask_port', 5000)
        websocket_port = data.get('websocket_port', 8765)
        static_dir = data.get('static_dir', '/home/ubuntu/src/static')
        staging = data.get('staging', False)
        
        # Valider l'email pour les domaines publics
        if not domain.startswith('localhost') and not email:
            return jsonify({
                'success': False,
                'error': 'Email requis pour les certificats Let\'s Encrypt'
            }), 400
        
        # Configurer SSL
        success = ssl_manager.setup_ssl_for_domain(
            domain=domain,
            email=email,
            flask_port=flask_port,
            websocket_port=websocket_port,
            static_dir=static_dir,
            staging=staging
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': f'SSL/TLS configuré avec succès pour {domain}',
                'domain': domain,
                'https_url': f'https://{domain}'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Erreur lors de la configuration SSL/TLS'
            }), 500
            
    except Exception as e:
        logger.error(f"Erreur lors de la configuration SSL: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ssl_bp.route('/caddy/status', methods=['GET'])
def get_caddy_status():
    """Récupère le statut détaillé de Caddy"""
    try:
        if not ssl_manager.is_caddy_installed():
            return jsonify({
                'success': False,
                'error': 'Caddy n\'est pas installé'
            }), 404
        
        status = ssl_manager.get_caddy_status()
        
        return jsonify({
            'success': True,
            'caddy_status': status
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du statut Caddy: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ssl_bp.route('/caddy/restart', methods=['POST'])
def restart_caddy():
    """Redémarre le service Caddy"""
    try:
        if not ssl_manager.is_caddy_installed():
            return jsonify({
                'success': False,
                'error': 'Caddy n\'est pas installé'
            }), 404
        
        success = ssl_manager.restart_caddy()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Caddy redémarré avec succès'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Erreur lors du redémarrage de Caddy'
            }), 500
            
    except Exception as e:
        logger.error(f"Erreur lors du redémarrage de Caddy: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ssl_bp.route('/caddy/reload', methods=['POST'])
def reload_caddy():
    """Recharge la configuration Caddy"""
    try:
        if not ssl_manager.is_caddy_installed():
            return jsonify({
                'success': False,
                'error': 'Caddy n\'est pas installé'
            }), 404
        
        success = ssl_manager.reload_caddy()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Configuration Caddy rechargée avec succès'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Erreur lors du rechargement de la configuration'
            }), 500
            
    except Exception as e:
        logger.error(f"Erreur lors du rechargement de Caddy: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ssl_bp.route('/certificates', methods=['GET'])
def get_certificates():
    """Récupère la liste des certificats SSL"""
    try:
        certificates = ssl_manager.get_certificates_info()
        
        return jsonify({
            'success': True,
            'certificates': certificates,
            'count': len(certificates)
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des certificats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ssl_bp.route('/generate-caddyfile', methods=['POST'])
def generate_caddyfile():
    """Génère un Caddyfile pour prévisualisation"""
    try:
        data = request.get_json()
        
        domain = data.get('domain', 'localhost')
        email = data.get('email')
        flask_port = data.get('flask_port', 5000)
        websocket_port = data.get('websocket_port', 8765)
        static_dir = data.get('static_dir', '/home/ubuntu/src/static')
        staging = data.get('staging', False)
        
        caddyfile_content = ssl_manager.generate_caddyfile(
            domain=domain,
            flask_port=flask_port,
            websocket_port=websocket_port,
            static_dir=static_dir,
            email=email,
            staging=staging
        )
        
        return jsonify({
            'success': True,
            'caddyfile': caddyfile_content,
            'domain': domain
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la génération du Caddyfile: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ssl_bp.route('/install-caddy', methods=['POST'])
def install_caddy():
    """Installe Caddy"""
    try:
        if ssl_manager.is_caddy_installed():
            return jsonify({
                'success': True,
                'message': 'Caddy est déjà installé'
            })
        
        success = ssl_manager.install_caddy()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Caddy installé avec succès'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Erreur lors de l\'installation de Caddy'
            }), 500
            
    except Exception as e:
        logger.error(f"Erreur lors de l'installation de Caddy: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ssl_bp.route('/create-setup-script', methods=['POST'])
def create_setup_script():
    """Crée un script de configuration SSL automatisé"""
    try:
        data = request.get_json()
        output_path = data.get('output_path', '/home/ubuntu/setup_ssl.sh')
        
        success = ssl_manager.create_ssl_setup_script(output_path)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Script de configuration créé avec succès',
                'script_path': output_path
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Erreur lors de la création du script'
            }), 500
            
    except Exception as e:
        logger.error(f"Erreur lors de la création du script: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

