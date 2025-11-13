"""
Initialize default data for NTC WiFi Admin Portal
Run this after creating the database
"""
import sys
from create_default_portal import create_default_portal
from create_default_omada import create_default_omada

def main():
    print("=" * 50)
    print("Initializing NTC WiFi Admin Portal")
    print("=" * 50)
    print()
    
    try:
        # Create default portal design
        print("1. Setting up Portal Design...")
        create_default_portal()
        print()
        
        # Create default omada config
        print("2. Setting up Omada Configuration...")
        create_default_omada()
        print()
        
        print("=" * 50)
        print("✅ Initialization completed successfully!")
        print("=" * 50)
        
    except Exception as e:
        print()
        print("=" * 50)
        print(f"❌ Initialization failed: {e}")
        print("=" * 50)
        sys.exit(1)

if __name__ == "__main__":
    main()
