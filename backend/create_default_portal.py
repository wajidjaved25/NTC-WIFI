"""
Script to create default portal design and settings
"""
from app.database import SessionLocal
from app.models.portal_design import PortalDesign
from app.models.portal_settings import PortalSettings

def create_default_portal():
    db = SessionLocal()
    
    try:
        # Check if portal design exists
        existing_design = db.query(PortalDesign).first()
        if not existing_design:
            print("Creating default portal design...")
            
            default_design = PortalDesign(
                template_name="Default Portal",
                primary_color="#1890ff",
                secondary_color="#52c41a",
                accent_color="#52c41a",
                background_color="#ffffff",
                text_color="#000000",
                background_type="color",
                welcome_title="Welcome to NTC Public WiFi",
                welcome_text="Please login to access free WiFi",
                terms_text="<p>By using this service, you agree to our terms and conditions.</p>",
                terms_checkbox_text="I accept the terms and conditions",
                footer_text="© 2024 NTC. All rights reserved.",
                layout_type="centered",
                is_active=True,
                updated_by=1
            )
            
            db.add(default_design)
            db.commit()
            print("✅ Default portal design created")
        else:
            print("Portal design already exists")
        
        # Check if portal settings exist
        existing_settings = db.query(PortalSettings).first()
        if not existing_settings:
            print("Creating default portal settings...")
            
            settings = [
                PortalSettings(
                    setting_key="portal_domain",
                    setting_value="localhost",
                    description="Portal domain name",
                    updated_by=1
                ),
                PortalSettings(
                    setting_key="portal_url",
                    setting_value="http://localhost/captive-portal",
                    description="Portal URL",
                    updated_by=1
                ),
                PortalSettings(
                    setting_key="session_timeout",
                    setting_value="3600",
                    description="Session timeout in seconds",
                    updated_by=1
                )
            ]
            
            for setting in settings:
                db.add(setting)
            
            db.commit()
            print("✅ Default portal settings created")
        else:
            print("Portal settings already exist")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_default_portal()
