#!/usr/bin/env python
"""Test script to check if Django app can start without errors"""

import os
import sys
import django
from django.conf import settings

# Add the project directory to Python path
sys.path.insert(0, '/app')

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

try:
    # Setup Django
    django.setup()
    print("✅ Django setup successful")
    
    # Test basic imports
    from api.views import health_check, kaynscan_search
    print("✅ API views import successful")
    
    from api.sites.kaynscan import search
    print("✅ Kaynscan scraper import successful")
    
    # Test database connection
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    print("✅ Database connection successful")
    
    print("\n🎉 All tests passed! Application should start correctly.")
    
except Exception as e:
    print(f"❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
