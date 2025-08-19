import asyncio
import websockets
import socket
import threading
import logging
from typing import Dict, Optional
import uuid
import uvicorn
from starlette.applications import Starlette
from starlette.routing import WebSocketRoute
from starlette.websockets import WebSocket

logger = logging.getLogger(__name__)

class WebSocketProxy:
    def __init__(self):
        self.active_connections: Dict[str, dict] = {}
        
    async def handle_vnc_connection(self, websocket: WebSocket):
        """Handle VNC WebSocket connection"""
        try:
            # Extract connection parameters from path
            # Expected format: /vnc/{lab_id}/{machine_id}
            path_parts = websocket.url.path.strip(\"/\").split(\"/\")
            if len(path_parts) != 3 or path_parts[0] != \"vnc\":
                await websocket.close(code=4000, reason="Invalid path format")
                return
                
            lab_id = path_parts[1]
            machine_id = path_parts[2]
            
            # Get machine info and VNC details
            machine_info = self._get_machine_info(lab_id, machine_id)
            if not machine_info:
                await websocket.close(code=4001, reason="Machine not found")
                return
                
            vnc_host = machine_info.get(\"ip_address\", \"localhost\")
            vnc_port = machine_info.get(\"vnc_port\", 5901)
            
            # Create connection ID
            connection_id = str(uuid.uuid4())
            
            # Connect to VNC server
            try:
                vnc_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                vnc_socket.connect((vnc_host, vnc_port))
                vnc_socket.settimeout(30)
                
                # Store connection info
                self.active_connections[connection_id] = {
                    \"type\": \"vnc\",
                    \"websocket\": websocket,
                    \"socket\": vnc_socket,
                    \"machine_id\": machine_id,
                    \"lab_id\": lab_id
                }
                
                # Start bidirectional data forwarding
                await self._forward_data(websocket, vnc_socket, connection_id)
                
            except Exception as e:
                logger.error(f"Failed to connect to VNC server {vnc_host}:{vnc_port}: {e}")
                await websocket.close(code=4002, reason=f"VNC connection failed: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error in VNC connection handler: {e}")
            await websocket.close(code=4003, reason="Internal server error")
        finally:
            if connection_id in self.active_connections:
                self._cleanup_connection(connection_id)
    
    async def handle_rdp_connection(self, websocket: WebSocket):
        """Handle RDP WebSocket connection (via FreeRDP proxy)"""
        try:
            # Extract connection parameters from path
            # Expected format: /rdp/{lab_id}/{machine_id}
            path_parts = websocket.url.path.strip(\"/\").split(\"/\")
            if len(path_parts) != 3 or path_parts[0] != \"rdp\":
                await websocket.close(code=4000, reason="Invalid path format")
                return
                
            lab_id = path_parts[1]
            machine_id = path_parts[2]
            
            # Get machine info and RDP details
            machine_info = self._get_machine_info(lab_id, machine_id)
            if not machine_info:
                await websocket.close(code=4001, reason="Machine not found")
                return
                
            rdp_host = machine_info.get(\"ip_address\", \"localhost\")
            rdp_port = machine_info.get(\"rdp_port\", 3389)
            
            # Create connection ID
            connection_id = str(uuid.uuid4())
            
            # For RDP, we would need to implement a more complex proxy
            # This is a simplified version - in production, consider using
            # libraries like python-rdp or integrating with FreeRDP
            
            await websocket.close(code=4004, reason="RDP support not yet implemented")
            
        except Exception as e:
            logger.error(f"Error in RDP connection handler: {e}")
            await websocket.close(code=4003, reason="Internal server error")
    
    async def _forward_data(self, websocket: WebSocket, socket_conn, connection_id):
        """Forward data bidirectionally between WebSocket and socket"""
        try:
            # Create tasks for both directions
            ws_to_socket_task = asyncio.create_task(
                self._forward_ws_to_socket(websocket, socket_conn, connection_id)
            )
            socket_to_ws_task = asyncio.create_task(
                self._forward_socket_to_ws(websocket, socket_conn, connection_id)
            )
            
            # Wait for either task to complete (or fail)
            done, pending = await asyncio.wait(
                [ws_to_socket_task, socket_to_ws_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel remaining tasks
            for task in pending:
                task.cancel()
                
        except Exception as e:
            logger.error(f"Error in data forwarding: {e}")
        finally:
            self._cleanup_connection(connection_id)
    
    async def _forward_ws_to_socket(self, websocket: WebSocket, socket_conn, connection_id):
        """Forward data from WebSocket to socket"""
        try:
            async for message in websocket.iter_bytes():
                socket_conn.send(message)
        except websockets.exceptions.ConnectionClosedOK:
            logger.info(f"WebSocket connection closed for {connection_id}")
        except Exception as e:
            logger.error(f"Error forwarding WS to socket: {e}")
    
    async def _forward_socket_to_ws(self, websocket: WebSocket, socket_conn, connection_id):
        """Forward data from socket to WebSocket"""
        try:
            loop = asyncio.get_event_loop()
            while True:
                # Read from socket in a non-blocking way
                data = await loop.run_in_executor(None, socket_conn.recv, 4096)
                if not data:
                    break
                await websocket.send_bytes(data)
        except Exception as e:
            logger.error(f"Error forwarding socket to WS: {e}")
    
    def _get_machine_info(self, lab_id: str, machine_id: str) -> Optional[dict]:
        """Get machine information from database"""
        try:
            from src.models.lab import Machine
            machine = Machine.query.filter_by(id=int(machine_id), lab_id=int(lab_id)).first()
            if machine:
                return {
                    \"ip_address\": machine.ip_address,
                    \"vnc_port\": 5901,  # Default VNC port
                    \"rdp_port\": 3389,  # Default RDP port
                }
            return None
        except Exception as e:
            logger.error(f"Error getting machine info: {e}")
            return None
    
    def _cleanup_connection(self, connection_id: str):
        """Clean up connection resources"""
        if connection_id in self.active_connections:
            conn_info = self.active_connections[connection_id]
            try:
                if \"socket\" in conn_info:
                    conn_info[\"socket\"].close()
            except:
                pass
            del self.active_connections[connection_id]
            logger.info(f"Cleaned up connection {connection_id}")

# Global proxy instance
proxy = WebSocketProxy()

async def vnc_websocket_endpoint(websocket: WebSocket):
    await proxy.handle_vnc_connection(websocket)

async def rdp_websocket_endpoint(websocket: WebSocket):
    await proxy.handle_rdp_connection(websocket)

websocket_app = Starlette(routes=[
    WebSocketRoute("/vnc/{lab_id}/{machine_id}", vnc_websocket_endpoint),
    WebSocketRoute("/rdp/{lab_id}/{machine_id}", rdp_websocket_endpoint),
])

def run_websocket_server_thread(host=\"0.0.0.0\", port=8765):
    """Run WebSocket server in a separate thread using uvicorn"""
    def run_server():
        uvicorn.run(websocket_app, host=host, port=port, log_level="info")

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    logger.info(f"WebSocket server started on {host}:{port}")
    return thread


