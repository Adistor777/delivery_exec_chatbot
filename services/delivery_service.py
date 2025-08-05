# services/delivery_service.py (Enhanced with Redis)
from sqlalchemy.orm import Session
from models import User, Delivery, UserPreferences, KnowledgeBase, Conversation, DeliveryLog
from services.redis_service import RedisService
from typing import Dict, List, Optional
import json
from datetime import datetime

class DeliveryService:
    def __init__(self, db: Session):
        self.db = db
        self.redis = RedisService()
    
    async def get_user_context(self, user_id: int) -> Dict:
        """Get comprehensive context for a delivery executive with Redis caching"""
        
        # Try to get from cache first
        cached_context = await self.redis.get_conversation_context(user_id)
        if cached_context:
            print(f"🚀 Retrieved context from Redis cache for user {user_id}")
            return cached_context
        
        # If not in cache, build from database
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {}
        
        # Get active deliveries (check cache first)
        active_deliveries = await self.redis.get_active_deliveries(user_id)
        if not active_deliveries:
            deliveries_db = self.db.query(Delivery).filter(
                Delivery.user_id == user_id,
                Delivery.status.in_(['assigned', 'picked_up', 'in_transit'])
            ).all()
            
            active_deliveries = [
                {
                    'order_id': delivery.order_id,
                    'customer_name': delivery.customer_name,
                    'delivery_address': delivery.delivery_address,
                    'status': delivery.status,
                    'priority': delivery.priority,
                    'special_instructions': delivery.special_instructions
                }
                for delivery in deliveries_db
            ]
            # Cache for 10 minutes
            await self.redis.cache_active_deliveries(user_id, active_deliveries)
        
        # Get user preferences
        preferences = self.db.query(UserPreferences).filter(
            UserPreferences.user_id == user_id
        ).first()
        
        # Get recent conversations for context
        recent_conversations = self.db.query(Conversation).filter(
            Conversation.user_id == user_id
        ).order_by(Conversation.created_at.desc()).limit(3).all()
        
        # Get current location from Redis (real-time)
        current_location = await self.redis.get_user_location(user_id)
        
        context = {
            'user_info': {
                'id': user.id,
                'username': user.username,
                'full_name': user.full_name,
                'employee_id': user.employee_id,
                'vehicle_type': user.vehicle_type,
                'status': user.status
            },
            'active_deliveries': active_deliveries,
            'user_preferences': {
                'preferred_language': preferences.preferred_language if preferences else 'en',
                'voice_enabled': preferences.voice_enabled if preferences else False,
                'notification_settings': json.loads(preferences.notification_settings) if preferences and preferences.notification_settings else {},
                'route_preferences': json.loads(preferences.route_preferences) if preferences and preferences.route_preferences else {}
            },
            'recent_queries': [
                {
                    'query_type': conv.query_type,
                    'user_message': conv.user_message[:50] + '...' if len(conv.user_message) > 50 else conv.user_message
                }
                for conv in recent_conversations
            ]
        }
        
        # Add real-time location if available
        if current_location:
            context['current_location'] = current_location
        elif user.current_location_lat and user.current_location_lng:
            context['current_location'] = {
                'lat': float(user.current_location_lat),
                'lng': float(user.current_location_lng)
            }
        
        # Cache the context for 30 minutes
        await self.redis.cache_conversation_context(user_id, context)
        
        return context
    
    def classify_query(self, message: str) -> str:
        """Classify the type of query based on keywords and patterns"""
        message_lower = message.lower()
        
        # Route and navigation related
        route_keywords = ['route', 'navigation', 'direction', 'traffic', 'gps', 'map', 'fastest', 'avoid', 'highway', 'toll']
        if any(word in message_lower for word in route_keywords):
            return 'route'
        
        # Customer communication
        customer_keywords = ['customer', 'call', 'message', 'contact', 'phone', 'text', 'notify', 'inform', 'delay', 'late']
        if any(word in message_lower for word in customer_keywords):
            return 'customer_comm'
        
        # Policy and procedures
        policy_keywords = ['policy', 'procedure', 'rule', 'protocol', 'guidelines', 'what should i do', 'how to', 'process']
        if any(word in message_lower for word in policy_keywords):
            return 'policy'
        
        # Emergency situations
        emergency_keywords = ['emergency', 'accident', 'breakdown', 'help', 'urgent', 'problem', 'stuck', 'issue', 'trouble']
        if any(word in message_lower for word in emergency_keywords):
            return 'emergency'
        
        # Performance and earnings
        performance_keywords = ['earning', 'performance', 'metric', 'rating', 'stats', 'income', 'money', 'pay', 'salary']
        if any(word in message_lower for word in performance_keywords):
            return 'performance'
        
        # Technical support
        technical_keywords = ['app', 'technical', 'bug', 'error', 'not working', 'crash', 'login', 'sync', 'update']
        if any(word in message_lower for word in technical_keywords):
            return 'technical'
        
        return 'general'
    
    async def save_conversation(self, user_id: int, user_message: str, bot_response: str, query_type: str, response_time_ms: int = 0, context_data: Dict = None):
        """Save conversation to database and invalidate cache"""
        conversation = Conversation(
            user_id=user_id,
            user_message=user_message,
            bot_response=bot_response,
            query_type=query_type,
            response_time_ms=response_time_ms,
            context_data=json.dumps(context_data) if context_data else None
        )
        
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        
        # Invalidate context cache since conversation history changed
        await self.redis.delete_cache(f"context:{user_id}")
        
        return conversation
    
    def search_knowledge_base(self, query: str, category: Optional[str] = None, limit: int = 5) -> List[KnowledgeBase]:
        """Search knowledge base for relevant information"""
        kb_query = self.db.query(KnowledgeBase).filter(KnowledgeBase.is_active == True)
        
        if category:
            kb_query = kb_query.filter(KnowledgeBase.category == category)
        
        # Simple keyword search (can be enhanced with full-text search)
        query_lower = query.lower()
        kb_query = kb_query.filter(
            (KnowledgeBase.keywords.contains(query_lower)) |
            (KnowledgeBase.title.contains(query)) |
            (KnowledgeBase.content.contains(query))
        )
        
        results = kb_query.order_by(KnowledgeBase.priority.asc()).limit(limit).all()
        return results
    
    async def update_delivery_status(self, user_id: int, order_id: str, new_status: str, notes: Optional[str] = None, location_lat: Optional[float] = None, location_lng: Optional[float] = None):
        """Update delivery status and log the change with Redis notifications"""
        delivery = self.db.query(Delivery).filter(
            Delivery.order_id == order_id,
            Delivery.user_id == user_id
        ).first()
        
        if not delivery:
            raise ValueError(f"Delivery {order_id} not found for user {user_id}")
        
        old_status = delivery.status
        delivery.status = new_status
        delivery.updated_at = datetime.utcnow()
        
        # Set actual delivery time if delivered
        if new_status == 'delivered':
            delivery.actual_delivery_time = datetime.utcnow()
        
        # Create log entry
        log_entry = DeliveryLog(
            delivery_id=delivery.id,
            user_id=user_id,
            status_from=old_status,
            status_to=new_status,
            notes=notes,
            location_lat=location_lat,
            location_lng=location_lng
        )
        
        self.db.add(log_entry)
        self.db.commit()
        
        # Invalidate cached deliveries and context
        await self.redis.invalidate_user_deliveries(user_id)
        await self.redis.delete_cache(f"context:{user_id}")
        
        # Publish real-time update
        update_data = {
            "order_id": order_id,
            "status": new_status,
            "user_id": user_id,
            "notes": notes,
            "location": {"lat": location_lat, "lng": location_lng} if location_lat and location_lng else None
        }
        await self.redis.publish_delivery_update(order_id, update_data)
        
        return delivery
    
    async def get_user_deliveries(self, user_id: int, status: Optional[str] = None, limit: int = 10) -> List[Delivery]:
        """Get deliveries for a user with caching for active deliveries"""
        
        # For active deliveries, try cache first
        if status in ['assigned', 'picked_up', 'in_transit']:
            cached_deliveries = await self.redis.get_active_deliveries(user_id)
            if cached_deliveries:
                # Filter by specific status if needed
                if status:
                    cached_deliveries = [d for d in cached_deliveries if d.get('status') == status]
                return cached_deliveries[:limit]
        
        # Query database
        query = self.db.query(Delivery).filter(Delivery.user_id == user_id)
        
        if status:
            query = query.filter(Delivery.status == status)
        
        deliveries = query.order_by(Delivery.created_at.desc()).limit(limit).all()
        return deliveries
    
    async def update_user_location(self, user_id: int, lat: float, lng: float):
        """Update user location in Redis and database"""
        # Update in Redis for real-time access
        await self.redis.update_user_location(user_id, lat, lng)
        
        # Update in database for persistence
        user = self.db.query(User).filter(User.id == user_id).first()
        if user:
            user.current_location_lat = lat
            user.current_location_lng = lng
            user.updated_at = datetime.utcnow()
            self.db.commit()
            
            # Invalidate context cache since location changed
            await self.redis.delete_cache(f"context:{user_id}")
    
    async def get_nearby_delivery_executives(self, lat: float, lng: float, radius_km: float = 5) -> List[Dict]:
        """Get nearby delivery executives using Redis geospatial data"""
        return await self.redis.get_nearby_users(lat, lng, radius_km)
    
    async def get_delivery_suggestions(self, user_id: int) -> List[str]:
        """Generate contextual suggestions with caching"""
        
        # Check cache first
        cache_key = f"suggestions:{user_id}"
        cached_suggestions = await self.redis.get_cache(cache_key)
        if cached_suggestions:
            return cached_suggestions
        
        # Get active deliveries count
        active_deliveries = await self.redis.get_active_deliveries(user_id)
        if active_deliveries is None:
            active_count = self.db.query(Delivery).filter(
                Delivery.user_id == user_id,
                Delivery.status.in_(['assigned', 'picked_up', 'in_transit'])
            ).count()
        else:
            active_count = len(active_deliveries)
        
        suggestions = []
        
        if active_count > 0:
            suggestions.extend([
                "Update delivery status",
                "Get optimized route for remaining deliveries",
                "Contact customer about delivery ETA",
                "Report delivery issue or delay"
            ])
        else:
            suggestions.extend([
                "Check for new delivery assignments",
                "View today's performance metrics",
                "Update current location",
                "Check earnings summary"
            ])
        
        # Add general helpful suggestions
        suggestions.extend([
            "Emergency contact information",
            "Company policies and procedures"
        ])
        
        # Cache suggestions for 5 minutes
        await self.redis.set_cache(cache_key, suggestions[:6], 300)
        
        return suggestions[:6]
    
    async def get_performance_metrics(self, user_id: int) -> Dict:
        """Get user performance metrics with Redis caching"""
        
        # Try cache first
        cached_metrics = await self.redis.get_user_metrics(user_id)
        if cached_metrics:
            return cached_metrics
        
        # Calculate from database
        today = datetime.now().date()
        deliveries_today = self.db.query(Delivery).filter(
            Delivery.user_id == user_id,
            Delivery.created_at >= today
        ).all()
        
        completed = [d for d in deliveries_today if d.status == 'delivered']
        failed = [d for d in deliveries_today if d.status == 'failed']
        
        metrics = {
            "date": today.isoformat(),
            "deliveries_completed": len(completed),
            "deliveries_failed": len(failed),
            "total_deliveries": len(deliveries_today),
            "success_rate": (len(completed) / len(deliveries_today) * 100) if deliveries_today else 0,
            "average_delivery_time": self._calculate_avg_delivery_time(completed),
            "total_earnings": sum(d.cod_amount or 0 for d in completed)
        }
        
        # Cache for 1 hour
        await self.redis.cache_user_metrics(user_id, metrics)
        
        return metrics
    
    def _calculate_avg_delivery_time(self, completed_deliveries: List[Delivery]) -> int:
        """Calculate average delivery time in minutes"""
        if not completed_deliveries:
            return 0
        
        total_time = 0
        count = 0
        
        for delivery in completed_deliveries:
            if delivery.actual_delivery_time and delivery.created_at:
                duration = delivery.actual_delivery_time - delivery.created_at
                total_time += duration.total_seconds() / 60  # Convert to minutes
                count += 1
        
        return int(total_time / count) if count > 0 else 0