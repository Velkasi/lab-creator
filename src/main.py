import os
import sys
from flask import Flask, send_from_directory
from src.models.lab import db, Lab, Machine, Snapshot, CustomPlaybook, DeploymentLog # Import all models
from src.models.remote_connection import RemoteConnection # Import new model
from src.routes.labs import labs_bp
from src.routes.remote_access import remote_access_bp
from src.routes.ssl_management import ssl_bp
from src.routes.performance import performance_bp
from src.middleware.performance_middleware import PerformanceMiddleware
from src.services.websocket_proxy import websocket_app
from flask_cors import CORS
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set environment variables for workspace directories
os.environ["TERRAFORM_WORKSPACE_DIR"] = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "terraform_workspaces")
os.environ["ANSIBLE_WORKSPACE_DIR"] = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ansible_workspaces")
os.environ["BACKUP_DIR"] = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backups")

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
CORS(app) # Enable CORS for all routes

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "super-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

# Initialize performance middleware
performance_middleware = PerformanceMiddleware(app)

# Register blueprints
app.register_blueprint(labs_bp, url_prefix="/api")
app.register_blueprint(remote_access_bp, url_prefix="/api")
app.register_blueprint(ssl_bp, url_prefix="/api")
app.register_blueprint(performance_bp, url_prefix="/api")

with app.app_context():
    db.create_all() # Create all tables based on models

@app.route("/")
def serve_index():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/<path:path>")
def serve_static(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, "index.html")

if __name__ == "__main__":

    
    app.run(host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", 5000)), debug=os.getenv("FLASK_DEBUG", "True") == "True")




# Start WebSocket server using uvicorn in a separate thread
@app.before_first_request
def start_websocket_server():
    websocket_thread = threading.Thread(target=uvicorn.run, args=(websocket_app, ), kwargs={"host": "0.0.0.0", "port": 8765, "log_level": "info"}, daemon=True)
    websocket_thread.start()
    logger.info("Uvicorn WebSocket server started successfully in a separate thread.")


