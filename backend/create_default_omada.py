"""
Script to create default Omada configuration
"""
from app.database import SessionLocal
from app.models.omada_config import OmadaConfig
from app.utils.helpers import encrypt_password

def create_default_omada():
    db = SessionLocal()
    
    try:
        # Check if omada config exists
        existing_config = db.query(OmadaConfig).first()
        if not existing_config:
            print("Creating default Omada configuration...")
            
            # Encrypt default password
            encrypted_password = encrypt_password("admin")
            
            default_config = OmadaConfig(
                config_name="Default Omada",
                controller_url="https://localhost:8043",
                controller_id="",
                username="admin",
                password_encrypted=encrypted_password,
                site_id="Default",
                site_name="Default Site",
                auth_type="voucher",
                redirect_url="http://localhost",
                session_timeout=3600,
                idle_timeout=600,
                daily_time_limit=7200,
                max_daily_sessions=3,
                bandwidth_limit_up=10240,
                bandwidth_limit_down=10240,
                enable_rate_limiting=False,
                rate_limit_up=0,
                rate_limit_down=0,
                daily_data_limit=0,
                session_data_limit=0,
                enable_mac_filtering=False,
                is_active=True,
                updated_by=1
            )
            
            db.add(default_config)
            db.commit()
            print("✅ Default Omada configuration created")
        else:
            print("Omada configuration already exists")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_default_omada()
