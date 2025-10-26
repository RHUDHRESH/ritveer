#!/usr/bin/env python3
"""
Verification script for ArtisanHub setup
Tests all components: Python, Database, Redis, Ollama, FastAPI
"""

import sys
import subprocess
import requests
import json
import time
from pathlib import Path

def check_python():
    """Check Python version and virtual environment"""
    print("🔍 Checking Python...")
    try:
        import sys
        print(f"   ✅ Python {sys.version}")

        # Check if we're in virtual environment
        if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            print("   ✅ Virtual environment active")
        else:
            print("   ⚠️  Not in virtual environment")

        return True
    except Exception as e:
        print(f"   ❌ Python check failed: {e}")
        return False

def check_dependencies():
    """Check if all required packages are installed"""
    print("🔍 Checking Python dependencies...")
    required_packages = [
        'fastapi', 'langgraph', 'sqlalchemy', 'pydantic',
        'httpx', 'uvicorn', 'redis', 'psycopg2'
    ]

    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package}")
            missing_packages.append(package)

    if missing_packages:
        print(f"   ❌ Missing packages: {', '.join(missing_packages)}")
        return False

    print("   ✅ All dependencies installed")
    return True

def check_database():
    """Check database connectivity"""
    print("🔍 Checking database...")
    try:
        from sqlalchemy import create_engine, text
        from config import DATABASE_URL

        print(f"   📋 Database URL: {DATABASE_URL}")

        if DATABASE_URL.startswith("sqlite"):
            print("   ✅ Using SQLite (fallback mode)")
            return True
        elif DATABASE_URL.startswith("postgresql"):
            engine = create_engine(DATABASE_URL)
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                print("   ✅ PostgreSQL connection successful")
                return True
        else:
            print(f"   ❌ Unsupported database URL: {DATABASE_URL}")
            return False

    except Exception as e:
        print(f"   ❌ Database check failed: {e}")
        return False

def check_redis():
    """Check Redis connectivity"""
    print("🔍 Checking Redis...")
    try:
        import redis
        from config import REDIS_URL

        print(f"   📋 Redis URL: {REDIS_URL}")

        r = redis.from_url(REDIS_URL)
        r.ping()
        print("   ✅ Redis connection successful")

        # Test basic operations
        r.set("test_key", "test_value")
        value = r.get("test_key")
        if value == b"test_value":
            print("   ✅ Redis operations working")
            r.delete("test_key")
            return True
        else:
            print("   ❌ Redis operations failed")
            return False

    except Exception as e:
        print(f"   ❌ Redis check failed: {e}")
        return False

def check_ollama():
    """Check Ollama service and models"""
    print("🔍 Checking Ollama...")
    try:
        from config import OLLAMA_BASE_URL

        print(f"   📋 Ollama URL: {OLLAMA_BASE_URL}")

        # Check if Ollama is running
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            print("   ✅ Ollama service running")

            # Check available models
            models_data = response.json()
            if "models" in models_data:
                models = [model["name"] for model in models_data["models"]]
                print(f"   📋 Available models: {', '.join(models)}")

                if models:
                    print("   ✅ Models available")
                    return True
                else:
                    print("   ⚠️  No models available")
                    return False
            else:
                print("   ❌ No models found")
                return False
        else:
            print(f"   ❌ Ollama service not responding: {response.status_code}")
            return False

    except Exception as e:
        print(f"   ❌ Ollama check failed: {e}")
        return False

def check_fastapi():
    """Check FastAPI application"""
    print("🔍 Checking FastAPI application...")
    try:
        # Try to import the FastAPI app
        import sys
        sys.path.append(str(Path(__file__).parent))
        from api import app
        print("   ✅ FastAPI app imported successfully")

        # Check if we can start the server (basic syntax check)
        import uvicorn
        print("   ✅ Uvicorn available")

        return True

    except Exception as e:
        print(f"   ❌ FastAPI check failed: {e}")
        return False

def check_ports():
    """Check if required ports are available"""
    print("🔍 Checking port availability...")
    ports_to_check = [8000, 5432, 6379, 11434]

    import socket
    available_ports = []

    for port in ports_to_check:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            result = sock.connect_ex(('127.0.0.1', port))
            if result == 0:
                print(f"   📋 Port {port}: In use")
            else:
                print(f"   📋 Port {port}: Available")
                available_ports.append(port)
        except Exception:
            print(f"   📋 Port {port}: Available")
            available_ports.append(port)
        finally:
            sock.close()

    return True

def main():
    """Run all checks"""
    print("🚀 ArtisanHub Setup Verification")
    print("=" * 50)

    checks = [
        ("Python & Environment", check_python),
        ("Python Dependencies", check_dependencies),
        ("Database", check_database),
        ("Redis", check_redis),
        ("Ollama", check_ollama),
        ("FastAPI", check_fastapi),
        ("Port Availability", check_ports),
    ]

    results = []
    for check_name, check_func in checks:
        print(f"\n{check_name}:")
        print("-" * 30)
        result = check_func()
        results.append((check_name, result))

    print("\n" + "=" * 50)
    print("📊 SUMMARY:")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for check_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status}: {check_name}")

    print(f"\n🎯 Overall: {passed}/{total} checks passed")

    if passed == total:
        print("🎉 All checks passed! Your ArtisanHub setup is ready.")
        return 0
    else:
        print("⚠️  Some checks failed. Please review the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
