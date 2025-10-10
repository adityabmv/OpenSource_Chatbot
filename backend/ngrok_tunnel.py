#!/usr/bin/env python3
"""
Ngrok tunnel script for exposing local backend to Firebase frontend
"""
import time
from pyngrok import ngrok

def start_ngrok_tunnel(port=8000):
    """Start ngrok tunnel for the specified port"""
    print("🚀 Starting ngrok tunnel for port 8000...")

    # Kill any existing tunnels
    ngrok.kill()

    # Start new tunnel
    tunnel = ngrok.connect(port, "http")
    public_url = tunnel.public_url

    print("✅ Ngrok tunnel established!")
    print(f"🌐 Public URL: {public_url}")
    print(f"🔗 Local backend: http://localhost:{port}")
    print("📱 Firebase frontend can now connect to this URL")
    print("\n📋 Next steps:")
    print("1. Copy this URL: " + public_url)
    print("2. Update your Firebase frontend environment variable")
    print("3. Redeploy frontend with new API URL")
    print("\n⚠️  Keep this script running to maintain the tunnel!")

    # Keep the tunnel alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Closing ngrok tunnel...")
        ngrok.kill()
        print("✅ Tunnel closed")

if __name__ == "__main__":
    start_ngrok_tunnel()