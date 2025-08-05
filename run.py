#!/usr/bin/env python3
"""
Speantag Bakery Expense Tracking System
Startup script
"""

import os
import sys
from app import app

if __name__ == '__main__':
    print("🍞 Starting Speantag Bakery Expense Tracking System...")
    print("📍 Access the application at: http://localhost:5000")
    print("🔄 Press Ctrl+C to stop the server")
    print()
    
    try:
        app.run(debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n👋 Shutting down Speantag Bakery Expense Tracking System...")
        sys.exit(0) 