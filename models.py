from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, JSON, Numeric
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    phone = Column(String(15))
    full_name = Column(String(100))
    employee_id = Column(String(20))
    vehicle_type = Column(String(20))
    current_location_lat = Column(Numeric(10, 8))
    current_location_lng = Column(Numeric(11, 8))
    status = Column(String(20), default='available')
    password_hash = Column(String(255))  # Added for authentication
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    deliveries = relationship("Delivery", back_populates="user")
    conversations = relationship("Conversation", back_populates="user")
    preferences = relationship("UserPreferences", back_populates="user", uselist=False)

class Delivery(Base):
    __tablename__ = "deliveries"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    order_id = Column(String(50), unique=True, nullable=False)
    customer_name = Column(String(100))
    customer_phone = Column(String(15))
    pickup_address = Column(Text)
    pickup_lat = Column(Numeric(10, 8))
    pickup_lng = Column(Numeric(11, 8))
    delivery_address = Column(Text)
    delivery_lat = Column(Numeric(10, 8))
    delivery_lng = Column(Numeric(11, 8))
    status = Column(String(20), default='assigned')
    priority = Column(String(10), default='normal')
    estimated_delivery_time = Column(DateTime)
    actual_delivery_time = Column(DateTime)
    special_instructions = Column(Text)
    package_type = Column(String(50))
    cod_amount = Column(Numeric(10, 2), default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="deliveries")
    logs = relationship("DeliveryLog", back_populates="delivery")

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    session_id = Column(String(50))
    user_message = Column(Text, nullable=False)
    bot_response = Column(Text, nullable=False)
    query_type = Column(String(50))
    context_data = Column(Text)  # Store as JSON string for SQLite compatibility
    response_time_ms = Column(Integer)
    satisfaction_rating = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="conversations")

class KnowledgeBase(Base):
    __tablename__ = "knowledge_base"
    
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50))
    title = Column(String(200))
    content = Column(Text)
    keywords = Column(Text)
    priority = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DeliveryLog(Base):
    __tablename__ = "delivery_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    delivery_id = Column(Integer, ForeignKey("deliveries.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    status_from = Column(String(20))
    status_to = Column(String(20))
    notes = Column(Text)
    location_lat = Column(Numeric(10, 8))
    location_lng = Column(Numeric(11, 8))
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    delivery = relationship("Delivery", back_populates="logs")

class UserPreferences(Base):
    __tablename__ = "user_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    preferred_language = Column(String(10), default='en')
    voice_enabled = Column(Boolean, default=False)
    notification_settings = Column(Text)  # Store as JSON string
    route_preferences = Column(Text)  # Store as JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="preferences")

class UserMetrics(Base):
    __tablename__ = "user_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(String(10))  # YYYY-MM-DD format
    deliveries_completed = Column(Integer, default=0)
    deliveries_failed = Column(Integer, default=0)
    total_distance_km = Column(Numeric(8, 2), default=0)
    total_earnings = Column(Numeric(10, 2), default=0)
    average_delivery_time_minutes = Column(Integer, default=0)
    customer_rating = Column(Numeric(3, 2), default=0)
    created_at = Column(DateTime, default=datetime.utcnow)