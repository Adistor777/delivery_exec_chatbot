# services/websocket_manager.py
import json
import asyncio
from typing import Dict, List, Set
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime
import logging
from services.redis_service import RedisService
from services.auth_service import AuthService

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Active WebSocket connections by user_id
        self.active_connections: Dict[int, WebSocket] = {}
        
        # Subscriptions: user_id -> set of channels they're subscribed to
        self.subscriptions: Dict[int, Set[str]] = {}
        
        # Reverse mapping: channel -> set of user_ids subscribed
        self.channel_subscribers: Dict[str, Set[int]] = {}
        
        self.redis = RedisService()
        self.auth_service = AuthService()
        
        # Start Redis subscriber task
        self.redis_subscriber_task = None
    
    async def connect(self, websocket: WebSocket, user_id: int, token: str) -> bool:
        """Connect a user's WebSocket with authentication"""
        try:
            # Verify JWT token
            if not self.auth_service.verify_token(token):
                await websocket.close(code=4003, reason="Invalid token")
                return False
            
            await websocket.accept()
            
            # Store connection
            self.active_connections[user_id] = websocket
            self.subscriptions[user_id] = set()
            
            logger.info(f"User {user_id} connected via WebSocket")
            
            # Send connection confirmation
            await self.send_personal_message({
                "type": "connection_confirmed",
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat()
            }, user_id)
            
            # Start Redis subscriber if not already running
            if self.redis_subscriber_task is None:
                self.redis_subscriber_task = asyncio.create_task(self._start_redis_subscriber())
            
            return True
            
        except Exception as e:
            logger.error(f"WebSocket connection error for user {user_id}: {e}")
            return False
    
    async def disconnect(self, user_id: int):
        """Disconnect a user and clean up subscriptions"""
        if user_id in self.active_connections:
            # Clean up subscriptions
            if user_id in self.subscriptions:
                for channel in self.subscriptions[user_id]:
                    if channel in self.channel_subscribers:
                        self.channel_subscribers[channel].discard(user_id)
                        if not self.channel_subscribers[channel]:
                            del self.channel_subscribers[channel]
                del self.subscriptions[user_id]
            
            del self.active_connections[user_id]
            logger.info(f"User {user_id} disconnected from WebSocket")
    
    async def send_personal_message(self, message: dict, user_id: int):
        """Send message to specific user"""
        if user_id in self.active_connections:
            try:
                websocket = self.active_connections[user_id]
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to user {user_id}: {e}")
                await self.disconnect(user_id)
    
    async def subscribe_to_channel(self, user_id: int, channel: str):
        """Subscribe user to a Redis channel"""
        if user_id not in self.subscriptions:
            return False
        
        self.subscriptions[user_id].add(channel)
        
        if channel not in self.channel_subscribers:
            self.channel_subscribers[channel] = set()
        self.channel_subscribers[channel].add(user_id)
        
        logger.info(f"User {user_id} subscribed to channel {channel}")
        return True
    
    async def unsubscribe_from_channel(self, user_id: int, channel: str):
        """Unsubscribe user from a Redis channel"""
        if user_id in self.subscriptions:
            self.subscriptions[user_id].discard(channel)
        
        if channel in self.channel_subscribers:
            self.channel_subscribers[channel].discard(user_id)
            if not self.channel_subscribers[channel]:
                del self.channel_subscribers[channel]
    
    async def broadcast_to_channel(self, channel: str, message: dict):
        """Broadcast message to all users subscribed to a channel"""
        if channel in self.channel_subscribers:
            subscribers = self.channel_subscribers[channel].copy()
            for user_id in subscribers:
                await self.send_personal_message(message, user_id)
    
    async def _start_redis_subscriber(self):
        """Start Redis subscriber to listen for real-time updates"""
        if not self.redis.redis_client:
            logger.warning("Redis not available, skipping subscriber")
            return
        
        try:
            pubsub = self.redis.redis_client.pubsub()
            
            # Subscribe to all delivery update channels
            pubsub.psubscribe("delivery_updates:*")
            pubsub.psubscribe("location_updates:*")
            pubsub.psubscribe("system_notifications:*")
            
            logger.info("Redis subscriber started")
            
            for message in pubsub.listen():
                if message['type'] == 'pmessage':
                    channel = message['channel']
                    data = json.loads(message['data'])
                    
                    # Broadcast to WebSocket subscribers
                    await self.broadcast_to_channel(channel, {
                        "type": "redis_update",
                        "channel": channel,
                        "data": data,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
        except Exception as e:
            logger.error(f"Redis subscriber error: {e}")
        finally:
            self.redis_subscriber_task = None

# Global connection manager instance
manager = ConnectionManager()

class WebSocketHandler:
    def __init__(self):
        self.manager = manager
        self.redis = RedisService()
    
    async def handle_websocket(self, websocket: WebSocket, user_id: int, token: str):
        """Main WebSocket handler"""
        if not await self.manager.connect(websocket, user_id, token):
            return
        
        try:
            # Auto-subscribe to user-specific channels
            await self._setup_user_subscriptions(user_id)
            
            while True:
                # Listen for messages from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                await self._handle_client_message(user_id, message)
                
        except WebSocketDisconnect:
            await self.manager.disconnect(user_id)
        except Exception as e:
            logger.error(f"WebSocket handler error for user {user_id}: {e}")
            await self.manager.disconnect(user_id)
    
    async def _setup_user_subscriptions(self, user_id: int):
        """Set up default subscriptions for a user"""
        # Subscribe to user-specific notifications
        await self.manager.subscribe_to_channel(user_id, f"user_notifications:{user_id}")
        
        # Subscribe to delivery updates for user's deliveries
        user_deliveries = await self.redis.get_active_deliveries(user_id)
        if user_deliveries:
            for delivery in user_deliveries:
                order_id = delivery.get('order_id')
                if order_id:
                    await self.manager.subscribe_to_channel(user_id, f"delivery_updates:{order_id}")
        
        # Subscribe to system-wide notifications
        await self.manager.subscribe_to_channel(user_id, "system_notifications:all")
    
    async def _handle_client_message(self, user_id: int, message: dict):
        """Handle messages from WebSocket clients"""
        message_type = message.get('type')
        
        if message_type == 'subscribe':
            # Client wants to subscribe to a channel
            channel = message.get('channel')
            if channel:
                await self.manager.subscribe_to_channel(user_id, channel)
                await self.manager.send_personal_message({
                    "type": "subscription_confirmed",
                    "channel": channel
                }, user_id)
        
        elif message_type == 'unsubscribe':
            # Client wants to unsubscribe from a channel
            channel = message.get('channel')
            if channel:
                await self.manager.unsubscribe_from_channel(user_id, channel)
                await self.manager.send_personal_message({
                    "type": "unsubscription_confirmed",
                    "channel": channel
                }, user_id)
        
        elif message_type == 'location_update':
            # Client is sending location update
            lat = message.get('lat')
            lng = message.get('lng')
            if lat and lng:
                await self.redis.update_user_location(user_id, lat, lng)
                
                # Broadcast location update
                await self.redis.publish_delivery_update(f"location_updates:{user_id}", {
                    "user_id": user_id,
                    "lat": lat,
                    "lng": lng,
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        elif message_type == 'ping':
            # Heartbeat/keepalive
            await self.manager.send_personal_message({
                "type": "pong",
                "timestamp": datetime.utcnow().isoformat()
            }, user_id)
        
        elif message_type == 'get_status':
            # Client requesting current status
            await self._send_current_status(user_id)
    
    async def _send_current_status(self, user_id: int):
        """Send current user status via WebSocket"""
        try:
            # Get active deliveries
            active_deliveries = await self.redis.get_active_deliveries(user_id)
            
            # Get current location
            location = await self.redis.get_user_location(user_id)
            
            # Get today's metrics
            metrics = await self.redis.get_user_metrics(user_id)
            
            status_data = {
                "type": "status_update",
                "data": {
                    "active_deliveries_count": len(active_deliveries) if active_deliveries else 0,
                    "current_location": location,
                    "metrics": metrics,
                    "subscriptions": list(self.manager.subscriptions.get(user_id, set()))
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.manager.send_personal_message(status_data, user_id)
            
        except Exception as e:
            logger.error(f"Error sending status to user {user_id}: {e}")

# Notification service for sending real-time updates
class NotificationService:
    def __init__(self):
        self.redis = RedisService()
        self.manager = manager
    
    async def notify_delivery_status_change(self, order_id: str, user_id: int, old_status: str, new_status: str, notes: str = None):
        """Notify about delivery status change"""
        notification = {
            "type": "delivery_status_changed",
            "order_id": order_id,
            "user_id": user_id,
            "old_status": old_status,
            "new_status": new_status,
            "notes": notes,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Send via Redis pub/sub
        await self.redis.publish_delivery_update(order_id, notification)
        
        # Send directly via WebSocket if user is connected
        await self.manager.send_personal_message(notification, user_id)
    
    async def notify_new_delivery_assignment(self, user_id: int, delivery_data: dict):
        """Notify about new delivery assignment"""
        notification = {
            "type": "new_delivery_assigned",
            "delivery": delivery_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.manager.send_personal_message(notification, user_id)
    
    async def notify_emergency_alert(self, user_ids: List[int], alert_message: str, alert_type: str = "emergency"):
        """Send emergency alert to multiple users"""
        notification = {
            "type": "emergency_alert",
            "alert_type": alert_type,
            "message": alert_message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        for user_id in user_ids:
            await self.manager.send_personal_message(notification, user_id)
    
    async def notify_system_maintenance(self, message: str, scheduled_time: str = None):
        """Notify all connected users about system maintenance"""
        notification = {
            "type": "system_maintenance",
            "message": message,
            "scheduled_time": scheduled_time,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Broadcast to all connected users
        for user_id in self.manager.active_connections.keys():
            await self.manager.send_personal_message(notification, user_id)