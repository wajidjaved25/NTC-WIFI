"""
Initialize database with default superadmin user
Run this script once to set up the database
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine, Base
from app.models import Admin
from passlib.context import CryptContext

def init_database():
    """Create tables and default admin user"""
    
    print("=" * 60)
    print("NTC WiFi Admin Portal - Database Initialization")
    print("=" * 60)
    
    # Create all tables
    print("\n📦 Creating database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully!")
    except Exception as e:
        print(f"❌ Error creating tables: {str(e)}")
        return
    
    # Create password hasher
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Check if superadmin exists
        existing = db.query(Admin).filter(Admin.username == "superadmin").first()
        
        if not existing:
            # Create superadmin user
            print("\n👤 Creating superadmin user...")
            hashed_password = pwd_context.hash("SuperAdmin@2025")
            
            superadmin = Admin(
                username="superadmin",
                password_hash=hashed_password,
                role="superadmin",
                full_name="System Administrator",
                email="admin@ntc.local",
                requires_otp=False,
                is_active=True
            )
            
            db.add(superadmin)
            db.commit()
            
            print("✅ Superadmin user created successfully!")
            print("\n" + "=" * 60)
            print("LOGIN CREDENTIALS")
            print("=" * 60)
            print("   Username: superadmin")
            print("   Password: SuperAdmin@2025")
            print("=" * 60)
            print("\n🚀 You can now start the backend server:")
            print("   uvicorn app.main:app --reload\n")
        else:
            print("\n⚠️  Superadmin user already exists")
            print("=" * 60)
            print("   Username: superadmin")
            print("   Password: SuperAdmin@2025")
            print("=" * 60)
    
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        db.rollback()
    
    finally:
        db.close()
        print()

if __name__ == "__main__":
    init_database()
