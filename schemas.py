from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
from decimal import Decimal

# Chat related schemas
class ChatRequest(BaseModel):
    message: str
    context: Optional[Dict] = None

class ChatResponse(BaseModel):
    response: str
    query_type: str
    response_time_ms: int
    suggestions: Optional[List[str]] = None

# User authentication schemas
class UserLoginRequest(BaseModel):
    username: str
    password: str

class UserLoginResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    username: str

class UserRegistrationRequest(BaseModel):
    username: str
    email: str
    password: str
    full_name: str
    phone: Optional[str] = None
    employee_id: Optional[str] = None
    vehicle_type: Optional[str] = "bike"

# Delivery related schemas
class DeliveryStatusRequest(BaseModel):
    order_id: str
    status: str
    notes: Optional[str] = None
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None

class DeliveryResponse(BaseModel):
    id: int
    order_id: str
    customer_name: Optional[str]
    customer_phone: Optional[str]
    pickup_address: Optional[str]
    delivery_address: Optional[str]
    status: str
    priority: str
    estimated_delivery_time: Optional[datetime]
    special_instructions: Optional[str]
    package_type: Optional[str]
    cod_amount: Optional[Decimal]
    created_at: datetime

    class Config:
        from_attributes = True

# Knowledge base schemas
class KnowledgeSearchRequest(BaseModel):
    query: str
    category: Optional[str] = None

class KnowledgeBaseResponse(BaseModel):
    id: int
    category: str
    title: str
    content: str
    priority: int
    
    class Config:
        from_attributes = True

# User preferences schemas
class UserPreferencesRequest(BaseModel):
    preferred_language: Optional[str] = "en"
    voice_enabled: Optional[bool] = False
    notification_settings: Optional[Dict] = None
    route_preferences: Optional[Dict] = None

class UserPreferencesResponse(BaseModel):
    id: int
    user_id: int
    preferred_language: str
    voice_enabled: bool
    notification_settings: Optional[str]
    route_preferences: Optional[str]
    
    class Config:
        from_attributes = True

# User info schemas
class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    phone: Optional[str]
    employee_id: Optional[str]
    vehicle_type: Optional[str]
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# Metrics schemas
class UserMetricsResponse(BaseModel):
    date: str
    deliveries_completed: int
    deliveries_failed: int
    total_distance_km: Optional[Decimal]
    total_earnings: Optional[Decimal]
    average_delivery_time_minutes: int
    customer_rating: Optional[Decimal]
    
    class Config:
        from_attributes = True