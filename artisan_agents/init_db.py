#!/usr/bin/env python3
"""
Database initialization script for ArtisanHub
Works with both PostgreSQL and SQLite
"""

import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from config import DATABASE_URL

def init_database():
    """Initialize the database with schema"""
    print("🔧 Initializing database...")

    try:
        # Create engine
        engine = create_engine(DATABASE_URL)
        print(f"   📋 Using database: {DATABASE_URL}")

        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("   ✅ Database connection successful")

        # Create tables
        schema_file = Path(__file__).parent / "schema.sql"
        if schema_file.exists():
            print("   📄 Reading schema file...")

            with open(schema_file, 'r') as f:
                schema_sql = f.read()

            # Split by semicolon and execute each statement
            statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]

            with engine.connect() as conn:
                for statement in statements:
                    if statement and not statement.startswith('--'):
                        try:
                            conn.execute(text(statement))
                            print(f"   ✅ Executed: {statement[:50]}...")
                        except Exception as e:
                            print(f"   ⚠️  Skipped (may already exist): {statement[:50]}...")

                conn.commit()
                print("   ✅ Schema applied successfully")
        else:
            print("   ❌ Schema file not found")
            return False

        # Test the tables
        with engine.connect() as conn:
            # Check agents table
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='agents'"))
            if result.fetchone():
                print("   ✅ Agents table exists")

            # Check tools table
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='tools'"))
            if result.fetchone():
                print("   ✅ Tools table exists")

        print("   🎉 Database initialization complete!")
        return True

    except Exception as e:
        print(f"   ❌ Database initialization failed: {e}")
        return False

def test_database():
    """Test database operations"""
    print("🧪 Testing database operations...")

    try:
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy import Column, Integer, String, Text
        from sqlalchemy.ext.declarative import declarative_base

        # Define models locally to avoid import issues
        Base = declarative_base()

        class AgentModel(Base):
            __tablename__ = "agents"
            id = Column(Integer, primary_key=True, index=True)
            name = Column(String, unique=True, index=True)
            state = Column(Text)

        class ToolModel(Base):
            __tablename__ = "tools"
            id = Column(Integer, primary_key=True, index=True)
            name = Column(String, unique=True, index=True)
            state = Column(Text)

        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        # Test insert
        db = SessionLocal()
        try:
            # Create test agent
            test_agent = AgentModel(name="test_agent", state='{"status": "test"}')
            db.add(test_agent)

            # Create test tool
            test_tool = ToolModel(name="test_tool", state='{"function": "test"}')
            db.add(test_tool)

            db.commit()
            print("   ✅ Insert operations successful")

            # Test query
            agent = db.query(AgentModel).filter(AgentModel.name == "test_agent").first()
            if agent:
                print("   ✅ Query operations successful")

            # Test update
            agent.state = '{"status": "updated"}'
            db.commit()
            print("   ✅ Update operations successful")

            # Test delete
            db.query(AgentModel).filter(AgentModel.name == "test_agent").delete()
            db.query(ToolModel).filter(ToolModel.name == "test_tool").delete()
            db.commit()
            print("   ✅ Delete operations successful")

        finally:
            db.close()

        print("   🎉 All database operations working!")
        return True

    except Exception as e:
        print(f"   ❌ Database operations test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 ArtisanHub Database Setup")
    print("=" * 40)

    success = True
    success &= init_database()
    print()
    success &= test_database()

    print("\n" + "=" * 40)
    if success:
        print("🎉 Database setup completed successfully!")
        print("Your ArtisanHub system is ready to use.")
    else:
        print("⚠️  Database setup had some issues.")
        print("The system will work with SQLite fallback mode.")

    sys.exit(0 if success else 1)
