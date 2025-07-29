from sqlalchemy.orm import Session
from models import User, Delivery, UserPreferences, KnowledgeBase, Conversation, DeliveryLog
from typing import Dict, List, Optional
import json
from datetime import datetime

class DeliveryService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_context(self, user_id: int) -> Dict:
        """Get comprehensive context for a delivery executive"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {}
        
        # Get active deliveries
        active_deliveries = self.db.query(Delivery).filter(
            Delivery.user_id == user_id,
            Delivery.status.in_(['assigned', 'picked_up', 'in_transit'])
        ).all()
        
        # Get user preferences
        preferences = self.db.query(UserPreferences).filter(
            UserPreferences.user_id == user_id
        ).first()
        
        # Get recent conversations for context
        recent_conversations = self.db.query(Conversation).filter(
            Conversation.user_id == user_id
        ).order_by(Conversation.created_at.desc()).limit(3).all()
        
        context = {
            'user_info': {
                'id': user.id,
                'username': user.username,
                'full_name': user.full_name,
                'employee_id': user.employee_id,
                'vehicle_type': user.vehicle_type,
                'status': user.status
            },
            'active_deliveries': [
                {
                    'order_id': delivery.order_id,
                    'customer_name': delivery.customer_name,
                    'delivery_address': delivery.delivery_address,
                    'status': delivery.status,
                    'priority': delivery.priority,
                    'special_instructions': delivery.special_instructions
                }
                for delivery in active_deliveries
            ],
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
        
        if user.current_location_lat and user.current_location_lng:
            context['current_location'] = {
                'lat': float(user.current_location_lat),
                'lng': float(user.current_location_lng)
            }
        
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
    
    def save_conversation(self, user_id: int, user_message: str, bot_response: str, query_type: str, response_time_ms: int = 0, context_data: Dict = None):
        """Save conversation to database"""
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
    
    def update_delivery_status(self, user_id: int, order_id: str, new_status: str, notes: Optional[str] = None, location_lat: Optional[float] = None, location_lng: Optional[float] = None):
        """Update delivery status and log the change"""
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
        
        return delivery
    
    def get_user_deliveries(self, user_id: int, status: Optional[str] = None, limit: int = 10) -> List[Delivery]:
        """Get deliveries for a user, optionally filtered by status"""
        query = self.db.query(Delivery).filter(Delivery.user_id == user_id)
        
        if status:
            query = query.filter(Delivery.status == status)
        
        deliveries = query.order_by(Delivery.created_at.desc()).limit(limit).all()
        return deliveries
    
    def get_delivery_suggestions(self, user_id: int) -> List[str]:
        """Generate contextual suggestions based on user's current deliveries"""
        active_deliveries = self.db.query(Delivery).filter(
            Delivery.user_id == user_id,
            Delivery.status.in_(['assigned', 'picked_up', 'in_transit'])
        ).count()
        
        suggestions = []
        
        if active_deliveries > 0:
            suggestions.extend([
                "Update delivery status",
                "Get route to next delivery",
                "Contact customer about delay"
            ])
        else:
            suggestions.extend([
                "Check for new deliveries",
                "View today's performance",
                "Update current location"
            ])
        
        # Add general helpful suggestions
        suggestions.extend([
            "Emergency contact information",
            "Company policies and procedures",
            "Technical support"
        ])
        
        return suggestions[:6]  # Return max 6 suggestions