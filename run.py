#!/usr/bin/env python3
"""
Brewery Manager - Run Script
Start the web interface for brewery management
"""

import os
import sys

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load .env file for environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed

from web.app import app, ws_manager
from utils.performance import init_connection_pool, optimize_database

if __name__ == "__main__":
    # Get configuration from environment variables
    debug = os.environ.get("FLASK_DEBUG", "true").lower() == "true"
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", "5001"))
    
    # Initialize performance optimizations
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'brewery.db')
    init_connection_pool(db_path, pool_size=5)
    optimize_database(db_path)
    
    print("=" * 50)
    print("🍺 Brewery Manager - Vietnam")
    print("=" * 50)
    print(f"Starting web server with WebSocket support...")
    print(f"Open your browser and go to: http://localhost:{port}")
    print(f"Debug mode: {debug}")
    print(f"Connection pool: 5 connections")
    print(f"WAL mode: Enabled")
    print("Press Ctrl+C to stop the server")
    print("=" * 50)
    ws_manager.socketio.run(app, debug=debug, host=host, port=port, allow_unsafe_werkzeug=True)
