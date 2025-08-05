# services/redis_service.py
import redis
import json
import asyncio
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

class RedisService:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            db=int(os.getenv('REDIS_DB', 0)),
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True
        )
        
        # Test connection
        try:
            self.redis_client.ping()
            print("✅ Redis connection established")
        except redis.ConnectionError:
            print("❌ Redis connection failed - falling back to memory cache")
            self.redis_client = None
    
    async def set_cache(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set cache with TTL"""
        if not self.redis_client:
            return False
            
        try:
            serialized_value = json.dumps(value) if not isinstance(value, str) else value
            return self.redis_client.setex(key, ttl, serialized_value)
        except Exception as e:
            print(f"Redis set error: {e}")
            return False
    
    async def get_cache(self, key: str) -> Optional[Any]:
        """Get cached value"""
        if not self.redis_client:
            return None
            
        try:
            value = self.redis_client.get(key)
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return None
        except Exception as e:
            print(f"Redis get error: {e}")
            return None
    
    async def delete_cache(self, pattern: str) -> int:
        """Delete cache keys matching pattern"""
        if not self.redis_client:
            return 0
            
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            print(f"Redis delete error: {e}")
            return 0
    
    # Session Management
    async def store_user_session(self, user_id: int, session_data: Dict, ttl: int = 3600):
        """Store user session data"""
        session_key = f"session:{user_id}"
        return await self.set_cache(session_key, session_data, ttl)
    
    async def get_user_session(self, user_id: int) -> Optional[Dict]:
        """Get user session data"""
        session_key = f"session:{user_id}"
        return await self.get_cache(session_key)
    
    async def invalidate_user_session(self, user_id: int):
        """Invalidate user session"""
        session_key = f"session:{user_id}"
        return await self.delete_cache(session_key)
    
    # Location Tracking
    async def update_user_location(self, user_id: int, lat: float, lng: float):
        """Update user's current location"""
        location_data = {
            "lat": lat,
            "lng": lng,
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id
        }
        location_key = f"location:{user_id}"
        return await self.set_cache(location_key, location_data, 300)  # 5 min TTL
    
    async def get_user_location(self, user_id: int) -> Optional[Dict]:
        """Get user's current location"""
        location_key = f"location:{user_id}"
        return await self.get_cache(location_key)
    
    # Conversation Context
    async def cache_conversation_context(self, user_id: int, context: Dict):
        """Cache user's conversation context for Claude API"""
        context_key = f"context:{user_id}"
        return await self.set_cache(context_key, context, 1800)  # 30 min TTL
    
    async def get_conversation_context(self, user_id: int) -> Optional[Dict]:
        """Get cached conversation context"""
        context_key = f"context:{user_id}"
        return await self.get_cache(context_key)
    
    # Delivery Status
    async def cache_active_deliveries(self, user_id: int, deliveries: list):
        """Cache user's active deliveries"""
        delivery_key = f"deliveries:{user_id}"
        return await self.set_cache(delivery_key, deliveries, 600)  # 10 min TTL
    
    async def get_active_deliveries(self, user_id: int) -> Optional[list]:
        """Get cached active deliveries"""
        delivery_key = f"deliveries:{user_id}"
        return await self.get_cache(delivery_key)
    
    async def invalidate_user_deliveries(self, user_id: int):
        """Invalidate cached deliveries when status changes"""
        delivery_key = f"deliveries:{user_id}"
        return await self.delete_cache(delivery_key)
    
    # Performance Metrics
    async def cache_user_metrics(self, user_id: int, metrics: Dict):
        """Cache user performance metrics"""
        today = datetime.now().date().isoformat()
        metrics_key = f"metrics:{user_id}:{today}"
        return await self.set_cache(metrics_key, metrics, 3600)  # 1 hour TTL
    
    async def get_user_metrics(self, user_id: int) -> Optional[Dict]:
        """Get cached user metrics"""
        today = datetime.now().date().isoformat()
        metrics_key = f"metrics:{user_id}:{today}"
        return await self.get_cache(metrics_key)
    
    # Real-time Updates via Pub/Sub
    async def publish_delivery_update(self, order_id: str, update_data: Dict):
        """Publish delivery status update"""
        if not self.redis_client:
            return False
            
        try:
            channel = f"delivery_updates:{order_id}"
            message = json.dumps({
                **update_data,
                "timestamp": datetime.utcnow().isoformat()
            })
            return self.redis_client.publish(channel, message)
        except Exception as e:
            print(f"Redis publish error: {e}")
            return False
    
    # Rate Limiting
    async def check_rate_limit(self, user_id: int, action: str, limit: int = 60, window: int = 60) -> bool:
        """Check if user has exceeded rate limit"""
        if not self.redis_client:
            return True  # Allow if Redis unavailable
            
        try:
            key = f"rate_limit:{user_id}:{action}"
            current = self.redis_client.get(key)
            
            if current is None:
                self.redis_client.setex(key, window, 1)
                return True
            elif int(current) < limit:
                self.redis_client.incr(key)
                return True
            else:
                return False
        except Exception as e:
            print(f"Rate limit check error: {e}")
            return True  # Allow on error
    
    # Health Check
    async def health_check(self) -> Dict[str, Any]:
        """Check Redis health"""
        if not self.redis_client:
            return {"status": "disconnected", "error": "Redis client not available"}
        
        try:
            start_time = datetime.utcnow()
            self.redis_client.ping()
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            info = self.redis_client.info()
            return {
                "status": "connected",
                "response_time_ms": response_time,
                "connected_clients": info.get('connected_clients', 0),
                "used_memory_human": info.get('used_memory_human', 'unknown'),
                "redis_version": info.get('redis_version', 'unknown')
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}