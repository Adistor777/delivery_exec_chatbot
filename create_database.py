import sqlite3
from datetime import datetime, timedelta
import json
from database import engine, Base
from models import User, Delivery, KnowledgeBase, UserPreferences, Conversation, DeliveryLog
from services.auth_service import AuthService

def create_tables():
    """Create all database tables"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully!")

def populate_sample_data():
    """Populate database with sample data for testing"""
    print("Populating sample data...")
    
    conn = sqlite3.connect('delivery_chatbot.db')
    cursor = conn.cursor()
    
    auth_service = AuthService()
    
    # Sample users with hashed passwords
    sample_users = [
        ('john_doe', 'john@deliveryco.com', '+1234567890', 'John Doe', 'EMP001', 'bike', auth_service.hash_password('password123')),
        ('jane_smith', 'jane@deliveryco.com', '+1234567891', 'Jane Smith', 'EMP002', 'car', auth_service.hash_password('password123')),
        ('mike_wilson', 'mike@deliveryco.com', '+1234567892', 'Mike Wilson', 'EMP003', 'van', auth_service.hash_password('password123')),
        ('sarah_johnson', 'sarah@deliveryco.com', '+1234567893', 'Sarah Johnson', 'EMP004', 'bike', auth_service.hash_password('password123')),
        ('demo_user', 'demo@deliveryco.com', '+1234567894', 'Demo User', 'EMP005', 'car', auth_service.hash_password('demo123'))
    ]
    
    cursor.executemany('''
        INSERT INTO users (username, email, phone, full_name, employee_id, vehicle_type, password_hash, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'available')
    ''', sample_users)
    
    # Sample knowledge base entries
    knowledge_entries = [
        ('policy', 'Package Damage Protocol', 
         'If a package is damaged during transit: 1) Take clear photos of the damage immediately 2) Do NOT complete the delivery 3) Contact dispatch via the app or call the hotline 4) Return the package to the hub with proper documentation 5) Fill out an incident report within 2 hours',
         'damage, damaged, broken, package, protocol, incident', 1),
        
        ('procedure', 'Customer Not Available - Standard Process', 
         'When customer is not available for delivery: 1) Ring doorbell/knock and wait 2 minutes 2) Call customer phone number 3) If no response, leave delivery notice with your contact info 4) Mark delivery as "attempted" in the app 5) Schedule redelivery for next business day 6) After 3 failed attempts, return package to hub and contact customer service',
         'customer, not available, absent, redelivery, attempt, notice', 1),
        
        ('procedure', 'Cash on Delivery (COD) Process',
         'For COD deliveries: 1) Confirm exact amount with customer before handing over package 2) Accept only exact cash amount (no change provided) 3) Issue receipt immediately 4) Take photo of cash received 5) Update payment status in app within 5 minutes 6) Deposit cash at designated collection points before end of shift',
         'cod, cash on delivery, payment, money, receipt', 1),
        
        ('faq', 'GPS Not Working - Troubleshooting',
         'If GPS navigation is not working: 1) Check if location services are enabled for the delivery app 2) Restart the app completely 3) Toggle airplane mode on/off to refresh network connection 4) Clear app cache (Android) or force-close app (iOS) 5) Use offline maps feature if available 6) Contact technical support at 1-800-TECH-HELP if issue persists',
         'gps, navigation, maps, technical, location, offline', 2),
        
        ('faq', 'App Login Issues',
         'If you cannot login to the delivery app: 1) Check your internet connection 2) Verify username and password spelling 3) Try "Forgot Password" if needed 4) Clear app cache/data 5) Update app to latest version 6) Restart your phone 7) Contact IT support if problem continues',
         'login, password, app, access, authentication, forgot', 2),
        
        ('emergency', 'Vehicle Breakdown Protocol',
         'In case of vehicle breakdown: 1) Move to a safe location immediately 2) Turn on hazard lights 3) Call emergency hotline: 1-800-EMERGENCY 4) Take photos of vehicle and location 5) Do NOT attempt repairs yourself 6) Arrange alternative transport for urgent deliveries 7) Fill out breakdown report 8) Wait for assistance or further instructions',
         'breakdown, vehicle, emergency, accident, hazard, repair', 1),
        
        ('emergency', 'Accident or Incident Reporting',
         'If involved in an accident: 1) Ensure personal safety first 2) Call 911 if injuries or major damage 3) Do NOT admit fault 4) Take photos of all vehicles, damage, and scene 5) Exchange insurance information 6) Get witness contact details 7) Call company emergency line immediately 8) Do NOT continue deliveries until cleared by supervisor',
         'accident, incident, crash, injury, police, insurance', 1),
        
        ('policy', 'Delivery Time Windows',
         'Standard delivery time windows: Morning (9AM-12PM), Afternoon (12PM-5PM), Evening (5PM-8PM). Always arrive within the promised time window. If running late: 1) Call customer 15 minutes before window expires 2) Provide realistic new ETA 3) Apologize for delay 4) Update status in app with reason for delay',
         'time, window, schedule, late, delay, eta, promise', 2),
        
        ('procedure', 'Special Delivery Instructions',
         'For deliveries with special instructions: 1) Read all instructions carefully before starting route 2) Call customer if instructions are unclear 3) Take photos when requested (e.g., "leave at door") 4) Get signature for high-value items 5) Do NOT enter customer premises unless explicitly safe and appropriate 6) Document any deviations from instructions',
         'special, instructions, signature, photo, door, premises', 2),
        
        ('faq', 'Earnings and Payment Questions',
         'Earnings are calculated based on: Base delivery fee + Distance bonus + Peak time multiplier + Customer tips. Payments are processed weekly on Fridays. Check your earnings in the app under "Performance" tab. For payment issues, contact payroll at payroll@company.com or call 1-800-PAY-HELP',
         'earnings, payment, salary, money, tip, bonus, payroll', 2)
    ]
    
    cursor.executemany('''
        INSERT INTO knowledge_base (category, title, content, keywords, priority)
        VALUES (?, ?, ?, ?, ?)
    ''', knowledge_entries)
    
    # Sample active deliveries
    current_time = datetime.now()
    sample_deliveries = [
        (1, 'ORD001', 'Alice Johnson', '+1234567893', 
         '123 Pickup Plaza, Downtown', 40.7128, -74.0060,
         '456 Delivery Avenue, Uptown', 40.7589, -73.9851,
         'assigned', 'normal', current_time + timedelta(hours=2),
         'Leave at door, ring doorbell twice', 'Electronics', 0),
         
        (2, 'ORD002', 'Bob Brown', '+1234567894',
         '789 Store Road, Mall District', 40.7282, -73.7949,
         '321 Home Street, Suburbs', 40.7505, -73.9934,
         'in_transit', 'urgent', current_time + timedelta(hours=1),
         'Call before delivery, customer works from home', 'Food', 25.50),
         
        (1, 'ORD003', 'Carol Davis', '+1234567895',
         '555 Warehouse Way, Industrial', 40.7200, -74.0100,
         '777 Oak Lane, Residential', 40.7650, -73.9800,
         'picked_up', 'normal', current_time + timedelta(hours=3),
         'Fragile - handle with care', 'Home Goods', 0),
         
        (3, 'ORD004', 'David Wilson', '+1234567896',
         '999 Market Street, Central', 40.7350, -73.9950,
         '111 Pine Avenue, North Side', 40.7700, -73.9700,
         'assigned', 'low', current_time + timedelta(hours=4),
         'Business delivery, ask for receiving dept', 'Office Supplies', 0),
         
        (5, 'ORD005', 'Emma Thompson', '+1234567897',
         '222 Shopping Center, West End', 40.7100, -74.0200,
         '888 Elm Street, East Side', 40.7400, -73.9600,
         'assigned', 'urgent', current_time + timedelta(minutes=45),
         'COD delivery - exact change required', 'Pharmacy', 15.75)
    ]
    
    cursor.executemany('''
        INSERT INTO deliveries (user_id, order_id, customer_name, customer_phone,
                              pickup_address, pickup_lat, pickup_lng,
                              delivery_address, delivery_lat, delivery_lng,
                              status, priority, estimated_delivery_time,
                              special_instructions, package_type, cod_amount)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', sample_deliveries)
    
    # Sample user preferences
    preferences = [
        (1, 'en', True, '{"push": true, "sms": false, "email": true}', '{"avoid_highways": false, "avoid_tolls": true, "prefer_shortest": false}'),
        (2, 'en', False, '{"push": true, "sms": true, "email": false}', '{"avoid_highways": true, "avoid_tolls": false, "prefer_shortest": true}'),
        (3, 'es', True, '{"push": false, "sms": true, "email": true}', '{"avoid_highways": false, "avoid_tolls": false, "prefer_shortest": false}'),
        (4, 'en', True, '{"push": true, "sms": false, "email": true}', '{"avoid_highways": false, "avoid_tolls": true, "prefer_shortest": true}'),
        (5, 'en', False, '{"push": true, "sms": true, "email": true}', '{"avoid_highways": false, "avoid_tolls": false, "prefer_shortest": false}')
    ]
    
    cursor.executemany('''
        INSERT INTO user_preferences (user_id, preferred_language, voice_enabled, 
                                    notification_settings, route_preferences)
        VALUES (?, ?, ?, ?, ?)
    ''', preferences)
    
    # Sample conversation history
    sample_conversations = [
        (1, 'session_001', 'How do I handle a damaged package?', 'If a package is damaged during transit: 1) Take clear photos of the damage immediately 2) Do NOT complete the delivery 3) Contact dispatch via the app...', 'policy', '{}', 1200),
        (2, 'session_002', 'Customer is not answering the door, what should I do?', 'When customer is not available for delivery: 1) Ring doorbell/knock and wait 2 minutes 2) Call customer phone number...', 'procedure', '{}', 800),
        (1, 'session_003', 'Best route to avoid traffic on Highway 101?', 'I can help you find alternative routes to avoid traffic. However, I need your specific destination to provide the best route recommendations...', 'route', '{}', 1500)
    ]
    
    cursor.executemany('''
        INSERT INTO conversations (user_id, session_id, user_message, bot_response, query_type, context_data, response_time_ms)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', sample_conversations)
    
    conn.commit()
    conn.close()
    print("Sample data populated successfully!")

def create_demo_scenario():
    """Create a demo scenario with realistic data"""
    print("Creating demo scenario...")
    
    conn = sqlite3.connect('delivery_chatbot.db')
    cursor = conn.cursor()
    
    # Update demo user location
    cursor.execute('''
        UPDATE users 
        SET current_location_lat = 40.7128, current_location_lng = -74.0060, status = 'busy'
        WHERE username = 'demo_user'
    ''')
    
    conn.commit()
    conn.close()
    print("Demo scenario created!")

def main():
    """Main function to set up the database"""
    print("Setting up Delivery Executive Chatbot Database...")
    print("=" * 50)
    
    try:
        # Create tables
        create_tables()
        
        # Populate with sample data
        populate_sample_data()
        
        # Create demo scenario
        create_demo_scenario()
        
        print("\n" + "=" * 50)
        print("Database setup completed successfully!")
        print("\nDemo Credentials:")
        print("Username: demo_user")
        print("Password: demo123")
        print("\nOther test users:")
        print("john_doe / password123")
        print("jane_smith / password123")
        print("mike_wilson / password123")
        print("sarah_johnson / password123")
        print("\nDatabase file: delivery_chatbot.db")
        print("You can now start the FastAPI server!")
        
    except Exception as e:
        print(f"Error setting up database: {str(e)}")
        raise

if __name__ == "__main__":
    main()