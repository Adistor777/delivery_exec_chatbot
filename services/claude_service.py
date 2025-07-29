import httpx
import os
import json
from typing import Dict, Optional
from dotenv import load_dotenv
import traceback

load_dotenv()

class ClaudeService:
    def __init__(self):
        self.api_key = os.getenv('CLAUDE_API_KEY')
        self.base_url = "https://api.anthropic.com/v1/messages"
        self.model = os.getenv('CLAUDE_MODEL', 'claude-3-sonnet-20240229')
        self.max_tokens = int(os.getenv('CLAUDE_MAX_TOKENS', '1000'))
        
        # DEBUG: Print initialization info
        print(f"🔍 DEBUG: Initializing ClaudeService")
        print(f"🔍 DEBUG: API Key present: {bool(self.api_key)}")
        print(f"🔍 DEBUG: API Key length: {len(self.api_key) if self.api_key else 0}")
        print(f"🔍 DEBUG: API Key starts with: {self.api_key[:10] if self.api_key else 'None'}...")
        print(f"🔍 DEBUG: Model: {self.model}")
        print(f"🔍 DEBUG: Max tokens: {self.max_tokens}")
        
        if not self.api_key:
            print("❌ ERROR: CLAUDE_API_KEY environment variable is required")
            raise ValueError("CLAUDE_API_KEY environment variable is required")
    
    async def process_query(self, user_message: str, context: Dict = None) -> Dict:
        """Process delivery executive query with Claude API"""
        
        print(f"🔍 DEBUG: Starting query processing")
        print(f"🔍 DEBUG: User message: {user_message[:50]}...")
        print(f"🔍 DEBUG: Context provided: {bool(context)}")
        
        # Enhanced system prompt for delivery context
        system_prompt = """You are a helpful assistant specifically designed for delivery executives (drivers, couriers, and field agents). 
        
        You provide concise, practical, and actionable answers for:
        - Route optimization and navigation queries
        - Delivery procedures and company policies
        - Customer communication assistance
        - Emergency protocols and safety procedures
        - Performance tracking and earnings questions
        - Technical support for delivery apps and GPS issues
        
        Guidelines:
        - Keep responses brief and actionable (2-3 sentences max for simple queries)
        - Use professional but friendly tone
        - Prioritize safety and company policies
        - Provide step-by-step instructions when needed
        - Ask clarifying questions if the query is ambiguous
        - If you don't know something specific to their company, acknowledge it and suggest contacting their supervisor
        
        Current context: You're helping a delivery executive during their work shift."""
        
        # Add context information to the user message if available
        if context:
            context_info = self._format_context(context)
            enhanced_message = f"Context: {context_info}\n\nQuery: {user_message}"
        else:
            enhanced_message = user_message
        
        print(f"🔍 DEBUG: Enhanced message length: {len(enhanced_message)}")
        
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": system_prompt,
            "messages": [{"role": "user", "content": enhanced_message}]
        }
        
        print(f"🔍 DEBUG: Payload prepared")
        print(f"🔍 DEBUG: Headers prepared (API key masked)")
        
        try:
            print(f"🔍 DEBUG: Making API request to {self.base_url}")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.base_url, headers=headers, json=payload)
                
                print(f"🔍 DEBUG: Response status code: {response.status_code}")
                print(f"🔍 DEBUG: Response headers: {dict(response.headers)}")
                
                if response.status_code != 200:
                    print(f"❌ ERROR: HTTP {response.status_code}")
                    print(f"❌ ERROR: Response text: {response.text}")
                
                response.raise_for_status()
                
                result = response.json()
                print(f"🔍 DEBUG: Response received successfully")
                print(f"🔍 DEBUG: Response type: {type(result)}")
                print(f"🔍 DEBUG: Response keys: {result.keys() if isinstance(result, dict) else 'Not a dict'}")
                
                return result
                
        except httpx.HTTPError as e:
            print(f"❌ HTTP Error: {str(e)}")
            print(f"❌ Error type: {type(e)}")
            print(f"❌ Full traceback:")
            traceback.print_exc()
            return {
                "content": [{
                    "text": "I'm sorry, I'm having trouble connecting to my AI service right now. Please try again in a moment or contact your supervisor for immediate assistance."
                }]
            }
        except Exception as e:
            print(f"❌ Unexpected error: {str(e)}")
            print(f"❌ Error type: {type(e)}")
            print(f"❌ Full traceback:")
            traceback.print_exc()
            return {
                "content": [{
                    "text": "I encountered an unexpected error. Please try rephrasing your question or contact technical support."
                }]
            }
    
    def _format_context(self, context: Dict) -> str:
        """Format context information for Claude"""
        context_parts = []
        
        if context.get('user_info'):
            user_info = context['user_info']
            if user_info.get('vehicle_type'):
                context_parts.append(f"Vehicle: {user_info['vehicle_type']}")
            if user_info.get('employee_id'):
                context_parts.append(f"Employee ID: {user_info['employee_id']}")
        
        if context.get('active_deliveries'):
            active_count = len(context['active_deliveries'])
            context_parts.append(f"Active deliveries: {active_count}")
            
            # Add details about urgent deliveries
            urgent_deliveries = [d for d in context['active_deliveries'] if d.get('priority') == 'urgent']
            if urgent_deliveries:
                context_parts.append(f"Urgent deliveries: {len(urgent_deliveries)}")
        
        if context.get('current_location'):
            location = context['current_location']
            if isinstance(location, dict):
                context_parts.append(f"Current location: {location.get('address', 'GPS coordinates available')}")
            else:
                context_parts.append(f"Current location: {location}")
        
        if context.get('user_preferences'):
            prefs = context['user_preferences']
            if prefs.get('preferred_language') and prefs.get('preferred_language') != 'en':
                context_parts.append(f"Preferred language: {prefs['preferred_language']}")
            if prefs.get('route_preferences'):
                route_prefs = prefs['route_preferences']
                if isinstance(route_prefs, str):
                    try:
                        route_prefs = json.loads(route_prefs)
                    except:
                        route_prefs = {}
                
                pref_details = []
                if route_prefs.get('avoid_highways'):
                    pref_details.append("avoid highways")
                if route_prefs.get('avoid_tolls'):
                    pref_details.append("avoid tolls")
                if pref_details:
                    context_parts.append(f"Route preferences: {', '.join(pref_details)}")
        
        if context.get('recent_queries'):
            recent_types = [q.get('query_type') for q in context['recent_queries'] if q.get('query_type')]
            if recent_types:
                context_parts.append(f"Recent query types: {', '.join(set(recent_types))}")
        
        if context.get('knowledge_base'):
            context_parts.append("Relevant company policies available")
        
        return "; ".join(context_parts) if context_parts else "No specific context available"
    
    def get_query_suggestions(self, query_type: str) -> list:
        """Generate helpful suggestions based on query type"""
        suggestions_map = {
            'route': [
                'Get traffic update for current route',
                'Find alternative route avoiding highways',
                'Check fastest route to next delivery',
                'Navigate to nearest gas station',
                'Find parking near delivery location'
            ],
            'customer_comm': [
                'Generate delay notification message',
                'Create delivery attempt message',
                'Get professional response template',
                'Draft apology for late delivery',
                'Compose pickup confirmation text'
            ],
            'policy': [
                'View complete delivery procedures',
                'Check package handling guidelines',
                'Review emergency protocols',
                'Read customer service policies',
                'Check refund and return procedures'
            ],
            'emergency': [
                'Call emergency hotline immediately',
                'Report vehicle breakdown',
                'Get nearest service center',
                'Contact roadside assistance',
                'Report accident or incident'
            ],
            'performance': [
                'View today\'s delivery stats',
                'Check weekly earnings summary',
                'See customer rating details',
                'Review completion metrics',
                'Check bonus eligibility'
            ],
            'technical': [
                'Restart GPS navigation',
                'Check app connectivity',
                'Contact technical support',
                'Clear app cache',
                'Update delivery app'
            ],
            'general': [
                'Check active deliveries',
                'Update current location',
                'View pending notifications',
                'Check today\'s schedule',
                'Review delivery instructions'
            ]
        }
        return suggestions_map.get(query_type, suggestions_map['general'])
    
    def classify_query_intent(self, message: str) -> Dict[str, float]:
        """Classify query intent with confidence scores"""
        message_lower = message.lower()
        intent_scores = {
            'route': 0.0,
            'customer_comm': 0.0,
            'policy': 0.0,
            'emergency': 0.0,
            'performance': 0.0,
            'technical': 0.0,
            'general': 0.1  # baseline score
        }
        
        # Route and navigation keywords
        route_keywords = ['route', 'navigation', 'direction', 'traffic', 'gps', 'map', 'fastest', 'avoid', 'highway', 'toll', 'gas', 'parking']
        intent_scores['route'] = sum(0.2 for word in route_keywords if word in message_lower)
        
        # Customer communication keywords
        customer_keywords = ['customer', 'call', 'message', 'contact', 'phone', 'text', 'notify', 'inform', 'delay', 'late', 'apology']
        intent_scores['customer_comm'] = sum(0.2 for word in customer_keywords if word in message_lower)
        
        # Policy keywords
        policy_keywords = ['policy', 'procedure', 'rule', 'protocol', 'guidelines', 'what should i do', 'how to', 'process', 'allowed']
        intent_scores['policy'] = sum(0.15 for word in policy_keywords if word in message_lower)
        
        # Emergency keywords
        emergency_keywords = ['emergency', 'accident', 'breakdown', 'help', 'urgent', 'problem', 'stuck', 'issue', 'trouble', 'danger']
        intent_scores['emergency'] = sum(0.3 for word in emergency_keywords if word in message_lower)
        
        # Performance keywords
        performance_keywords = ['earning', 'performance', 'metric', 'rating', 'stats', 'income', 'money', 'pay', 'salary', 'bonus']
        intent_scores['performance'] = sum(0.2 for word in performance_keywords if word in message_lower)
        
        # Technical keywords
        technical_keywords = ['app', 'technical', 'bug', 'error', 'not working', 'crash', 'login', 'sync', 'update', 'cache']
        intent_scores['technical'] = sum(0.2 for word in technical_keywords if word in message_lower)
        
        # Normalize scores
        max_score = max(intent_scores.values())
        if max_score > 0:
            for intent in intent_scores:
                intent_scores[intent] = min(1.0, intent_scores[intent] / max_score)
        
        return intent_scores
    
    def get_contextual_suggestions(self, context: Dict) -> list:
        """Generate contextual suggestions based on user's current state"""
        suggestions = []
        
        if context.get('active_deliveries'):
            active_deliveries = context['active_deliveries']
            
            # Check for urgent deliveries
            urgent_count = sum(1 for d in active_deliveries if d.get('priority') == 'urgent')
            if urgent_count > 0:
                suggestions.append(f"Handle {urgent_count} urgent deliveries")
            
            # Check for specific delivery types
            cod_deliveries = sum(1 for d in active_deliveries if d.get('special_instructions', '').lower().find('cod') != -1)
            if cod_deliveries > 0:
                suggestions.append("Review COD delivery procedures")
            
            # General delivery management
            suggestions.extend([
                "Get route optimization for all deliveries",
                "Update delivery status",
                "Contact customer about ETA"
            ])
        
        # Add performance-related suggestions
        suggestions.extend([
            "Check today's performance metrics",
            "View earnings summary",
            "Report any issues or delays"
        ])
        
        return suggestions[:5]  # Return top 5 suggestions