from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import os
import json
from typing import List, Optional

# Import local modules
from database import get_db
from models import User, Delivery, KnowledgeBase, UserPreferences
from schemas import (
    ChatRequest, ChatResponse, UserLoginRequest, UserLoginResponse,
    UserRegistrationRequest, DeliveryStatusRequest, DeliveryResponse,
    KnowledgeSearchRequest, KnowledgeBaseResponse, UserPreferencesRequest,
    UserPreferencesResponse, UserResponse
)
from services.claude_service import ClaudeService  # Adjusted import path
from services.auth_service import AuthService
from services.delivery_service import DeliveryService

# Initialize FastAPI app
app = FastAPI(
    title="Delivery Executive Chatbot API",
    description="AI-powered chatbot for delivery executives with route optimization, policy queries, and customer communication assistance",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
auth_service = AuthService()
claude_service = ClaudeService()
security = HTTPBearer()

# Authentication dependency
def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    """Extract and verify user ID from JWT token"""
    user_id = auth_service.get_user_id_from_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Delivery Executive Chatbot API",
        "version": "1.0.0",
        "status": "active",
        "endpoints": {
            "chat": "/api/chat",
            "login": "/api/auth/login",
            "register": "/api/auth/register",
            "deliveries": "/api/deliveries",
            "knowledge": "/api/knowledge/search",
            "docs": "/docs"
        }
    }

# Authentication endpoints
@app.post("/api/auth/register", response_model=UserLoginResponse)
async def register_user(request: UserRegistrationRequest, db: Session = Depends(get_db)):
    """Register a new delivery executive"""
    # Check if user already exists
    existing_user = db.query(User).filter(
        (User.username == request.username) | (User.email == request.email)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered"
        )
    
    # Create new user
    hashed_password = auth_service.hash_password(request.password)
    new_user = User(
        username=request.username,
        email=request.email,
        password_hash=hashed_password,
        full_name=request.full_name,
        phone=request.phone,
        employee_id=request.employee_id,
        vehicle_type=request.vehicle_type
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Create default preferences
    default_preferences = UserPreferences(
        user_id=new_user.id,
        preferred_language='en',
        voice_enabled=False,
        notification_settings='{"push": true, "sms": false, "email": true}',
        route_preferences='{"avoid_highways": false, "avoid_tolls": false, "prefer_shortest": true}'
    )
    db.add(default_preferences)
    db.commit()
    
    # Generate access token
    access_token = auth_service.create_access_token({"user_id": new_user.id})
    
    return UserLoginResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=new_user.id,
        username=new_user.username
    )

@app.post("/api/auth/login", response_model=UserLoginResponse)
async def login_user(request: UserLoginRequest, db: Session = Depends(get_db)):
    """Login delivery executive"""
    user = db.query(User).filter(User.username == request.username).first()
    
    if not user or not auth_service.verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    # Update user status to online
    user.status = 'available'
    user.updated_at = datetime.utcnow()
    db.commit()
    
    # Generate access token
    access_token = auth_service.create_access_token({"user_id": user.id})
    
    return UserLoginResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        username=user.username
    )

# Main chat endpoint
@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Main chat endpoint for delivery executive queries"""
    start_time = datetime.now()
    
    try:
        # Initialize delivery service
        delivery_service = DeliveryService(db)
        
        # Get user context
        user_context = delivery_service.get_user_context(user_id)
        
        # Classify query type
        query_type = delivery_service.classify_query(request.message)
        
        # Search knowledge base for relevant information
        knowledge_results = delivery_service.search_knowledge_base(request.message)
        
        # Add knowledge base context
        if knowledge_results:
            knowledge_context = "\n\nRelevant company information:\n"
            for kb_item in knowledge_results[:2]:  # Include top 2 results
                knowledge_context += f"- {kb_item.title}: {kb_item.content[:200]}...\n"
            enhanced_context = {**user_context, "knowledge_base": knowledge_context}
        else:
            enhanced_context = user_context
        
        # Process with Claude
        claude_response = await claude_service.process_query(
            request.message, 
            {**(request.context or {}), **enhanced_context}
        )
        
        # Calculate response time
        response_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Get suggestions
        suggestions = claude_service.get_query_suggestions(query_type)
        
        # Save conversation
        delivery_service.save_conversation(
            user_id, 
            request.message, 
            claude_response['content'][0]['text'], 
            query_type,
            response_time,
            enhanced_context
        )
        
        return ChatResponse(
            response=claude_response['content'][0]['text'],
            query_type=query_type,
            response_time_ms=response_time,
            suggestions=suggestions
        )
        
    except Exception as e:
        print(f"Chat endpoint error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to process your request. Please try again or contact support."
        )

# Delivery management endpoints
@app.get("/api/deliveries", response_model=List[DeliveryResponse])
async def get_user_deliveries(
    status: Optional[str] = None,
    limit: int = 10,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get deliveries for the authenticated user"""
    delivery_service = DeliveryService(db)
    deliveries = delivery_service.get_user_deliveries(user_id, status, limit)
    return deliveries

@app.post("/api/deliveries/update-status")
async def update_delivery_status(
    request: DeliveryStatusRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Update delivery status"""
    try:
        delivery_service = DeliveryService(db)
        updated_delivery = delivery_service.update_delivery_status(
            user_id=user_id,
            order_id=request.order_id,
            new_status=request.status,
            notes=request.notes,
            location_lat=request.location_lat,
            location_lng=request.location_lng
        )
        
        return {
            "message": f"Delivery {request.order_id} status updated to {request.status}",
            "order_id": request.order_id,
            "new_status": request.status,
            "updated_at": updated_delivery.updated_at
        }
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

# Knowledge base endpoints
@app.post("/api/knowledge/search", response_model=List[KnowledgeBaseResponse])
async def search_knowledge(
    request: KnowledgeSearchRequest,
    db: Session = Depends(get_db)
):
    """Search knowledge base for policies and procedures"""
    delivery_service = DeliveryService(db)
    results = delivery_service.search_knowledge_base(request.query, request.category)
    return results

@app.get("/api/knowledge/categories")
async def get_knowledge_categories(db: Session = Depends(get_db)):
    """Get available knowledge base categories"""
    categories = db.query(KnowledgeBase.category).distinct().all()
    return {"categories": [cat[0] for cat in categories]}

# User management endpoints
@app.get("/api/user/profile", response_model=UserResponse)
async def get_user_profile(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get user profile information"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user

@app.get("/api/user/preferences", response_model=UserPreferencesResponse)
async def get_user_preferences(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get user preferences"""
    preferences = db.query(UserPreferences).filter(UserPreferences.user_id == user_id).first()
    if not preferences:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preferences not found")
    return preferences

@app.post("/api/user/preferences")
async def update_user_preferences(
    request: UserPreferencesRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Update user preferences"""
    preferences = db.query(UserPreferences).filter(UserPreferences.user_id == user_id).first()
    
    if not preferences:
        preferences = UserPreferences(user_id=user_id)
        db.add(preferences)
    
    # Update preferences
    if request.preferred_language:
        preferences.preferred_language = request.preferred_language
    if request.voice_enabled is not None:
        preferences.voice_enabled = request.voice_enabled
    if request.notification_settings:
        preferences.notification_settings = json.dumps(request.notification_settings)
    if request.route_preferences:
        preferences.route_preferences = json.dumps(request.route_preferences)
    
    preferences.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Preferences updated successfully"}

@app.post("/api/user/location")
async def update_user_location(
    latitude: float,
    longitude: float,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Update user's current location"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    user.current_location_lat = latitude
    user.current_location_lng = longitude
    user.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Location updated successfully"}

# Dashboard and analytics endpoints
@app.get("/api/dashboard/summary")
async def get_dashboard_summary(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get dashboard summary for the user"""
    delivery_service = DeliveryService(db)
    
    # Get active deliveries count
    active_deliveries = delivery_service.get_user_deliveries(user_id, status='assigned')
    in_transit_deliveries = delivery_service.get_user_deliveries(user_id, status='in_transit')
    
    # Get today's completed deliveries
    today = datetime.now().date()
    completed_today = db.query(Delivery).filter(
        Delivery.user_id == user_id,
        Delivery.status == 'delivered',
        Delivery.actual_delivery_time >= today
    ).count()
    
    return {
        "active_deliveries": len(active_deliveries),
        "in_transit": len(in_transit_deliveries),
        "completed_today": completed_today,
        "suggestions": delivery_service.get_delivery_suggestions(user_id)
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host=os.getenv("HOST", "0.0.0.0"), 
        port=int(os.getenv("PORT", 8000)), 
        reload=os.getenv("DEBUG", "True").lower() == "true"
    )