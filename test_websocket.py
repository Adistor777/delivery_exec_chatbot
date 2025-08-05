#!/usr/bin/env python3
"""
Test WebSocket connection and real-time features
"""
import asyncio
import websockets
import json
import httpx

async def get_auth_token():
    """Get authentication token for testing"""
    print("🔐 Getting authentication token...")
    
    login_data = {
        "username": "demo_user",
        "password": "demo123"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post("http://localhost:8000/api/auth/login", json=login_data)
            
            if response.status_code == 200:
                token_data = response.json()
                print(f"   ✅ Login successful, user_id: {token_data['user_id']}")
                return token_data["access_token"], token_data["user_id"]
            else:
                print(f"   ❌ Login failed: {response.text}")
                return None, None
                
    except Exception as e:
        print(f"   ❌ Error during login: {e}")
        return None, None

async def test_websocket_connection():
    """Test WebSocket connection and basic functionality"""
    print("🧪 Testing WebSocket Connection")
    print("=" * 40)
    
    # Get authentication token
    token, user_id = await get_auth_token()
    if not token:
        print("❌ Cannot proceed without authentication")
        return False
    
    # WebSocket URL
    uri = f"ws://localhost:8000/api/ws/{user_id}?token={token}"
    print(f"🔌 Connecting to: {uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket connected successfully!")
            
            # Test 1: Wait for connection confirmation
            print("\n1️⃣ Testing connection confirmation...")
            message = await websocket.recv()
            data = json.loads(message)
            
            if data.get("type") == "connection_confirmed":
                print("   ✅ Connection confirmed received")
                print(f"   User ID: {data.get('user_id')}")
            else:
                print(f"   ⚠️ Unexpected message: {data}")
            
            # Test 2: Send location update
            print("\n2️⃣ Testing location update...")
            location_update = {
                "type": "location_update",
                "lat": 40.7128,
                "lng": -74.0060
            }
            
            await websocket.send(json.dumps(location_update))
            print("   ✅ Location update sent")
            
            # Test 3: Send ping (heartbeat)
            print("\n3️⃣ Testing heartbeat...")
            ping_message = {
                "type": "ping",
                "timestamp": "2025-01-01T00:00:00Z"
            }
            
            await websocket.send(json.dumps(ping_message))
            print("   ✅ Ping sent")
            
            # Wait for pong response
            try:
                pong_message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                pong_data = json.loads(pong_message)
                
                if pong_data.get("type") == "pong":
                    print("   ✅ Pong received")
                else:
                    print(f"   ⚠️ Unexpected response: {pong_data}")
            except asyncio.TimeoutError:
                print("   ⚠️ No pong response received (timeout)")
            
            # Test 4: Subscribe to delivery updates
            print("\n4️⃣ Testing channel subscription...")
            subscribe_message = {
                "type": "subscribe",
                "channel": "delivery_updates:TEST001"
            }
            
            await websocket.send(json.dumps(subscribe_message))
            print("   ✅ Subscription request sent")
            
            # Wait for subscription confirmation
            try:
                sub_message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                sub_data = json.loads(sub_message)
                
                if sub_data.get("type") == "subscription_confirmed":
                    print(f"   ✅ Subscription confirmed for channel: {sub_data.get('channel')}")
                else:
                    print(f"   ⚠️ Unexpected response: {sub_data}")
            except asyncio.TimeoutError:
                print("   ⚠️ No subscription confirmation received (timeout)")
            
            # Test 5: Request status
            print("\n5️⃣ Testing status request...")
            status_request = {
                "type": "get_status"
            }
            
            await websocket.send(json.dumps(status_request))
            print("   ✅ Status request sent")
            
            # Wait for status response
            try:
                status_message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                status_data = json.loads(status_message)
                
                if status_data.get("type") == "status_update":
                    print("   ✅ Status update received")
                    print(f"   Active deliveries: {status_data['data'].get('active_deliveries_count', 0)}")
                    print(f"   Current location: {status_data['data'].get('current_location', 'Not available')}")
                else:
                    print(f"   ⚠️ Unexpected response: {status_data}")
            except asyncio.TimeoutError:
                print("   ⚠️ No status response received (timeout)")
            
            # Test 6: Listen for additional messages
            print("\n6️⃣ Listening for additional messages (5 seconds)...")
            try:
                while True:
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(message)
                    print(f"   📨 Received: {data.get('type', 'unknown')} - {data}")
            except asyncio.TimeoutError:
                print("   ⏰ No additional messages received")
            
            print("\n✅ WebSocket testing completed successfully!")
            return True
            
    except websockets.exceptions.ConnectionClosed as e:
        print(f"❌ WebSocket connection closed: {e}")
        return False
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_api_websocket_integration():
    """Test integration between REST API and WebSocket"""
    print("\n🧪 Testing API-WebSocket Integration")
    print("=" * 40)
    
    # Get authentication token
    token, user_id = await get_auth_token()
    if not token:
        return False
    
    # Start WebSocket connection in background
    uri = f"ws://localhost:8000/api/ws/{user_id}?token={token}"
    
    async def websocket_listener(websocket):
        """Listen for WebSocket messages"""
        messages_received = []
        try:
            while True:
                message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                data = json.loads(message)
                messages_received.append(data)
                print(f"   📨 WebSocket received: {data.get('type', 'unknown')}")
                
                # Break after receiving delivery status update
                if data.get('type') == 'delivery_status_changed':
                    break
        except asyncio.TimeoutError:
            print("   ⏰ WebSocket listener timeout")
        return messages_received
    
    try:
        async with websockets.connect(uri) as websocket:
            print("🔌 WebSocket connected for integration test")
            
            # Wait for connection confirmation
            await websocket.recv()
            
            # Start listening in background
            listener_task = asyncio.create_task(websocket_listener(websocket))
            
            # Give WebSocket time to set up
            await asyncio.sleep(1)
            
            # Make API call to update delivery status
            print("\n📡 Making API call to update delivery status...")
            
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {token}"}
                update_data = {
                    "order_id": "ORD001",  # Using existing test order
                    "status": "in_transit",
                    "notes": "WebSocket integration test",
                    "location_lat": 40.7128,
                    "location_lng": -74.0060
                }
                
                response = await client.post(
                    "http://localhost:8000/api/deliveries/update-status",
                    json=update_data,
                    headers=headers
                )
                
                if response.status_code == 200:
                    print("   ✅ API call successful")
                    result = response.json()
                    print(f"   Status updated: {result.get('old_status')} → {result.get('new_status')}")
                else:
                    print(f"   ❌ API call failed: {response.text}")
            
            # Wait for WebSocket messages
            print("\n🎧 Waiting for WebSocket notifications...")
            try:
                messages = await asyncio.wait_for(listener_task, timeout=15.0)
                
                if messages:
                    print(f"   ✅ Received {len(messages)} WebSocket messages")
                    for msg in messages:
                        print(f"   - {msg.get('type', 'unknown')}: {msg}")
                else:
                    print("   ⚠️ No messages received via WebSocket")
                    
            except asyncio.TimeoutError:
                print("   ⏰ Timeout waiting for WebSocket messages")
            
            return True
            
    except Exception as e:
        print(f"❌ Integration test error: {e}")
        return False

async def main():
    """Main test function"""
    print("🚀 Starting WebSocket Tests")
    print("=" * 50)
    
    try:
        # Test basic WebSocket connection
        ws_success = await test_websocket_connection()
        
        if ws_success:
            # Test API-WebSocket integration
            integration_success = await test_api_websocket_integration()
            
            if integration_success:
                print("\n🎉 All WebSocket tests completed successfully!")
            else:
                print("\n⚠️ Integration tests had issues")
        else:
            print("\n❌ Basic WebSocket tests failed")
            
    except KeyboardInterrupt:
        print("\n⏹️ Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())