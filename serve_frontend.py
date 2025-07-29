#!/usr/bin/env python3
"""
Simple HTTP server to serve the frontend files
"""
import http.server
import socketserver
import os
import webbrowser
from pathlib import Path

class FrontendHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(Path(__file__).parent / "frontend"), **kwargs)
    
    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        super().end_headers()

def main():
    PORT = 3000
    
    print("🚀 Starting Delivery Chatbot Frontend Server")
    print("=" * 50)
    print(f"📱 Frontend URL: http://localhost:{PORT}")
    print(f"🔧 Backend URL: http://localhost:8000")
    print("=" * 50)
    print("Make sure your backend is running on port 8000!")
    print("Press Ctrl+C to stop the server")
    print("=" * 50)
    
    try:
        with socketserver.TCPServer(("", PORT), FrontendHandler) as httpd:
            print(f"✅ Server started successfully on port {PORT}")
            
            # Auto-open browser
            try:
                webbrowser.open(f'http://localhost:{PORT}')
                print("🌐 Opening browser automatically...")
            except:
                print("💡 Please open http://localhost:3000 in your browser")
            
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ Port {PORT} is already in use")
            print("Try stopping other servers or use a different port")
        else:
            print(f"❌ Server error: {e}")

if __name__ == "__main__":
    main()