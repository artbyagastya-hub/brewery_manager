"""
Brewery Manager - WebSocket Manager
Real-time event broadcasting for live updates
"""

from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime
import json
import threading
import time
import queue
from typing import Optional, Dict, Any, Callable
import os

# Try to import Redis - fall back to in-memory if not available
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class MessageQueue:
    """
    High-volume message queue with optional Redis backing.
    Falls back to in-memory queue if Redis is not available.
    """
    
    def __init__(self, redis_url: Optional[str] = None, maxsize: int = 10000):
        self.maxsize = maxsize
        self._in_memory_queue: queue.Queue = queue.Queue(maxsize=maxsize)
        self._redis_client: Optional[redis.Redis] = None
        self._redis_available = False
        
        # Try to connect to Redis
        if REDIS_AVAILABLE and redis_url:
            try:
                self._redis_client = redis.from_url(redis_url)
                self._redis_client.ping()
                self._redis_available = True
                print(f"MessageQueue: Connected to Redis")
            except Exception as e:
                print(f"MessageQueue: Redis not available ({e}), using in-memory queue")
                self._redis_client = None
                self._redis_available = False
    
    def put(self, message: Dict[str, Any], channel: str = 'default'):
        """Add a message to the queue"""
        message_data = {
            'channel': channel,
            'data': message,
            'timestamp': time.time()
        }
        
        if self._redis_available and self._redis_client:
            try:
                # Publish to Redis channel
                self._redis_client.publish(channel, json.dumps(message_data))
                # Also store in list for persistence
                self._redis_client.lpush(f'queue:{channel}', json.dumps(message_data))
                self._redis_client.ltrim(f'queue:{channel}', 0, self.maxsize - 1)
            except Exception as e:
                print(f"MessageQueue: Redis error ({e}), falling back to in-memory")
                self._in_memory_queue.put(message_data)
        else:
            try:
                self._in_memory_queue.put_nowait(message_data)
            except queue.Full:
                # Remove oldest message and add new one
                try:
                    self._in_memory_queue.get_nowait()
                    self._in_memory_queue.put_nowait(message_data)
                except queue.Empty:
                    pass
    
    def get_recent(self, channel: str = 'default', count: int = 100) -> list:
        """Get recent messages from a channel"""
        if self._redis_available and self._redis_client:
            try:
                messages = self._redis_client.lrange(f'queue:{channel}', 0, count - 1)
                return [json.loads(m) for m in messages]
            except Exception:
                return []
        return []
    
    def clear(self, channel: str = None):
        """Clear messages from queue"""
        if self._redis_available and self._redis_client:
            try:
                if channel:
                    self._redis_client.delete(f'queue:{channel}')
                else:
                    # Clear all queue keys
                    for key in self._redis_client.scan_iter('queue:*'):
                        self._redis_client.delete(key)
            except Exception:
                pass
        
        # Clear in-memory queue
        while not self._in_memory_queue.empty():
            try:
                self._in_memory_queue.get_nowait()
            except queue.Empty:
                break


class SessionStore:
    """
    Redis-backed session storage for WebSocket connections.
    Falls back to in-memory storage if Redis is not available.
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        self._in_memory_sessions: Dict[str, Dict[str, Any]] = {}
        self._redis_client: Optional[redis.Redis] = None
        self._redis_available = False
        
        # Try to connect to Redis
        if REDIS_AVAILABLE and redis_url:
            try:
                self._redis_client = redis.from_url(redis_url)
                self._redis_client.ping()
                self._redis_available = True
                print(f"SessionStore: Connected to Redis")
            except Exception as e:
                print(f"SessionStore: Redis not available ({e}), using in-memory storage")
                self._redis_client = None
                self._redis_available = False
    
    def set(self, session_id: str, data: Dict[str, Any], ttl: int = 3600):
        """Store session data"""
        if self._redis_available and self._redis_client:
            try:
                self._redis_client.setex(
                    f'session:{session_id}',
                    ttl,
                    json.dumps(data)
                )
            except Exception as e:
                print(f"SessionStore: Redis error ({e}), using in-memory")
                self._in_memory_sessions[session_id] = data
        else:
            self._in_memory_sessions[session_id] = data
    
    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        if self._redis_available and self._redis_client:
            try:
                data = self._redis_client.get(f'session:{session_id}')
                if data:
                    return json.loads(data)
            except Exception:
                pass
        
        return self._in_memory_sessions.get(session_id)
    
    def delete(self, session_id: str):
        """Delete session data"""
        if self._redis_available and self._redis_client:
            try:
                self._redis_client.delete(f'session:{session_id}')
            except Exception:
                pass
        
        self._in_memory_sessions.pop(session_id, None)
    
    def get_all_sessions(self) -> Dict[str, Dict[str, Any]]:
        """Get all active sessions (in-memory only for simplicity)"""
        return self._in_memory_sessions.copy()
    
    def cleanup_expired(self, max_age: int = 3600):
        """Clean up expired sessions (for in-memory storage)"""
        # Redis handles TTL automatically, but for in-memory we need manual cleanup
        current_time = time.time()
        expired = [
            sid for sid, data in self._in_memory_sessions.items()
            if current_time - data.get('created_at', 0) > max_age
        ]
        for sid in expired:
            del self._in_memory_sessions[sid]


class WebSocketManager:
    """Manages WebSocket connections and real-time event broadcasting"""
    
    def __init__(self, app=None):
        self.socketio = None
        self.connected_clients = {}
        self.rooms = {
            'dashboard': set(),
            'inventory': set(),
            'production': set(),
            'notifications': set(),
            'temperature': set()
        }
        self._lock = threading.Lock()
        
        # Initialize performance components
        redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        self._message_queue = MessageQueue(redis_url=redis_url)
        self._session_store = SessionStore(redis_url=redis_url)
        
        # Message processing thread
        self._processing_thread: Optional[threading.Thread] = None
        self._should_stop = threading.Event()
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize SocketIO with Flask app"""
        self.socketio = SocketIO(
            app,
            cors_allowed_origins="*",
            async_mode='threading',
            logger=False,
            engineio_logger=False
        )
        self._register_events()
        return self.socketio
    
    def _register_events(self):
        """Register WebSocket event handlers"""
        
        @self.socketio.on('connect')
        def handle_connect():
            """Handle client connection"""
            from flask import request
            client_id = request.sid
            
            with self._lock:
                self.connected_clients[client_id] = {
                    'connected_at': datetime.now().isoformat(),
                    'rooms': set()
                }
            
            emit('connected', {
                'status': 'connected',
                'client_id': client_id,
                'timestamp': datetime.now().isoformat()
            })
            
            print(f"WebSocket client connected: {client_id}")
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection"""
            from flask import request
            client_id = request.sid
            
            with self._lock:
                if client_id in self.connected_clients:
                    # Remove from all rooms
                    for room in self.connected_clients[client_id]['rooms']:
                        if room in self.rooms:
                            self.rooms[room].discard(client_id)
                    del self.connected_clients[client_id]
            
            print(f"WebSocket client disconnected: {client_id}")
        
        @self.socketio.on('join')
        def handle_join(data):
            """Handle client joining a room"""
            from flask import request
            client_id = request.sid
            room = data.get('room', 'dashboard')
            
            if room in self.rooms:
                join_room(room)
                with self._lock:
                    self.rooms[room].add(client_id)
                    if client_id in self.connected_clients:
                        self.connected_clients[client_id]['rooms'].add(room)
                
                emit('joined', {
                    'room': room,
                    'timestamp': datetime.now().isoformat()
                })
                
                print(f"Client {client_id} joined room: {room}")
        
        @self.socketio.on('leave')
        def handle_leave(data):
            """Handle client leaving a room"""
            from flask import request
            client_id = request.sid
            room = data.get('room')
            
            if room in self.rooms:
                leave_room(room)
                with self._lock:
                    self.rooms[room].discard(client_id)
                    if client_id in self.connected_clients:
                        self.connected_clients[client_id]['rooms'].discard(room)
                
                emit('left', {
                    'room': room,
                    'timestamp': datetime.now().isoformat()
                })
        
        @self.socketio.on('ping')
        def handle_ping():
            """Handle ping from client"""
            emit('pong', {'timestamp': datetime.now().isoformat()})
    
    def broadcast_dashboard_update(self, data):
        """Broadcast dashboard update to all dashboard subscribers"""
        if self.socketio:
            self.socketio.emit('dashboard_update', {
                'type': 'dashboard',
                'data': data,
                'timestamp': datetime.now().isoformat()
            }, room='dashboard')
    
    def broadcast_inventory_update(self, action, item):
        """Broadcast inventory change"""
        if self.socketio:
            self.socketio.emit('inventory_update', {
                'type': 'inventory',
                'action': action,  # 'added', 'updated', 'deleted', 'adjusted'
                'item': item,
                'timestamp': datetime.now().isoformat()
            }, room='inventory')
    
    def broadcast_batch_update(self, batch_id, status, details=None):
        """Broadcast batch status change"""
        if self.socketio:
            self.socketio.emit('batch_update', {
                'type': 'production',
                'batch_id': batch_id,
                'status': status,
                'details': details,
                'timestamp': datetime.now().isoformat()
            }, room='production')
    
    def broadcast_notification(self, notification):
        """Broadcast new notification"""
        if self.socketio:
            self.socketio.emit('new_notification', {
                'type': 'notification',
                'notification': notification,
                'timestamp': datetime.now().isoformat()
            }, room='notifications')
    
    def broadcast_temperature_alert(self, tank_id, temperature, alert_type):
        """Broadcast temperature alert"""
        if self.socketio:
            self.socketio.emit('temperature_alert', {
                'type': 'temperature',
                'tank_id': tank_id,
                'temperature': temperature,
                'alert_type': alert_type,  # 'high', 'low', 'critical'
                'timestamp': datetime.now().isoformat()
            }, room='temperature')
    
    def broadcast_low_stock_alert(self, material):
        """Broadcast low stock alert"""
        if self.socketio:
            self.socketio.emit('low_stock_alert', {
                'type': 'alert',
                'alert_type': 'low_stock',
                'material': material,
                'timestamp': datetime.now().isoformat()
            }, room='notifications')
    
    def broadcast_order_update(self, order_id, status):
        """Broadcast order status update"""
        if self.socketio:
            self.socketio.emit('order_update', {
                'type': 'sales',
                'order_id': order_id,
                'status': status,
                'timestamp': datetime.now().isoformat()
            }, room='dashboard')
    
    def broadcast_maintenance_alert(self, equipment):
        """Broadcast maintenance alert"""
        if self.socketio:
            self.socketio.emit('maintenance_alert', {
                'type': 'alert',
                'alert_type': 'maintenance',
                'equipment': equipment,
                'timestamp': datetime.now().isoformat()
            }, room='notifications')
    
    def send_to_user(self, user_id, event, data):
        """Send message to specific user (requires user session tracking)"""
        if self.socketio:
            self.socketio.emit(event, {
                'data': data,
                'timestamp': datetime.now().isoformat()
            }, room=f'user_{user_id}')
    
    def queue_event(self, event_type: str, data: Dict[str, Any], room: str = None):
        """
        Queue an event for broadcasting. Handles high-volume events by using message queue.
        """
        event = {
            'type': event_type,
            'data': data,
            'room': room,
            'timestamp': time.time()
        }
        self._message_queue.put(event, channel=room or 'default')
        
        # Also broadcast immediately for real-time updates
        if room:
            self.socketio.emit(event_type, data, room=room)
    
    def get_recent_events(self, channel: str = 'default', count: int = 100) -> list:
        """Get recent events from a channel"""
        return self._message_queue.get_recent(channel, count)
    
    def store_session(self, session_id: str, data: Dict[str, Any], ttl: int = 3600):
        """Store session data for a WebSocket connection"""
        data['created_at'] = time.time()
        self._session_store.set(session_id, data, ttl)
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data for a WebSocket connection"""
        return self._session_store.get(session_id)
    
    def delete_session(self, session_id: str):
        """Delete session data"""
        self._session_store.delete(session_id)
    
    def get_all_sessions(self) -> Dict[str, Dict[str, Any]]:
        """Get all active sessions"""
        return self._session_store.get_all_sessions()
    
    def get_stats(self):
        """Get WebSocket connection statistics"""
        with self._lock:
            return {
                'connected_clients': len(self.connected_clients),
                'rooms': {room: len(clients) for room, clients in self.rooms.items()},
                'message_queue': {
                    'redis_available': self._message_queue._redis_available,
                    'maxsize': self._message_queue.maxsize
                },
                'session_store': {
                    'redis_available': self._session_store._redis_available,
                    'active_sessions': len(self._session_store.get_all_sessions())
                }
            }


# Singleton instance
_ws_manager = None


def get_ws_manager(app=None):
    """Get or create WebSocket manager singleton"""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WebSocketManager(app)
    elif app is not None:
        _ws_manager.init_app(app)
    return _ws_manager