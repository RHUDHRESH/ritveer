#!/usr/bin/env python3
"""
Simple test script for FastAPI application
"""

import sys
from pathlib import Path

def test_fastapi():
    """Test FastAPI application components"""
    print("🔍 Testing FastAPI components...")

    try:
        # Test FastAPI import
        import fastapi
        print(f"   ✅ FastAPI {fastapi.__version__}")

        # Test uvicorn import
        import uvicorn
        print(f"   ✅ Uvicorn {uvicorn.__version__}")

        # Test static files import
        from fastapi.staticfiles import StaticFiles
        print("   ✅ StaticFiles available")

        # Test responses import
        from fastapi.responses import FileResponse
        print("   ✅ FileResponse available")

        # Test if we can create a basic FastAPI app
        app = fastapi.FastAPI()
        print("   ✅ FastAPI app creation successful")

        return True

    except Exception as e:
        print(f"   ❌ FastAPI test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_fastapi()
    if success:
        print("🎉 FastAPI components are working correctly!")
    else:
        print("❌ FastAPI test failed!")
        sys.exit(1)
