#!/usr/bin/env python3
"""
Run script for Research PDF File Renamer

Usage:
    python run.py              # Run in debug mode on port 5000
    python run.py --port 8000  # Run on different port
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.app import app

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Run PDF Renamer server')
    parser.add_argument('--port', type=int, default=5000, help='Port to run on')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--no-debug', action='store_true', help='Disable debug mode')
    args = parser.parse_args()

    print(f"\n{'='*50}")
    print("Research PDF File Renamer Server")
    print(f"{'='*50}")
    print(f"Running on http://{args.host}:{args.port}")
    print(f"Debug mode: {'off' if args.no_debug else 'on'}")
    print(f"{'='*50}\n")

    app.run(
        debug=not args.no_debug,
        host=args.host,
        port=args.port
    )
