#!/usr/bin/env python3
"""
Create default portal design if none exists
"""
import sys
sys.path.insert(0, '/opt/ntc-wifi/backend')

from app.database import SessionLocal
from app.models.portal_design import PortalDesign

def create_default_portal_design():
    db = SessionLocal()
    
    try:
        # Check if any portal design exists
        existing = db.query(PortalDesign).first()
        
        if existing:
            print(f"✓ Portal design already exists: {existing.template_name}")
            return
        
        # Create default portal design
        default_design = PortalDesign(
            template_name="Default",
            welcome_title="Welcome to NTC Public WiFi",
            welcome_text="Please register to connect to free WiFi",
            terms_text="<p>By using this service, you agree to our terms and conditions.</p>",
            terms_checkbox_text="I accept the terms and conditions",
            footer_text="© 2025 NTC Public WiFi",
            primary_color="#1890ff",
            secondary_color="#ffffff",
            accent_color="#52c41a",
            text_color="#000000",
            background_color="#f0f2f5",
            layout_type="centered",
            show_logo=False,
            show_background=False,
            is_active=True,
            updated_by=1  # Assumes superadmin has id=1
        )
        
        db.add(default_design)
        db.commit()
        db.refresh(default_design)
        
        print(f"✓ Created default portal design (ID: {default_design.id})")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_default_portal_design()
