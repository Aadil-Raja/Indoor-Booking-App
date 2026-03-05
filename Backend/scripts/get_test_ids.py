"""
Helper script to get user IDs for chatbot testing.

This script queries the management database and displays user IDs
that can be used for testing the chatbot.

Usage:
    python Backend/scripts/get_test_ids.py
"""

import sys
from pathlib import Path

# Add Backend to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

# Load environment variables
env_path = backend_dir / "apps" / "management" / ".env"
load_dotenv(env_path)

def get_test_ids():
    """Get user IDs for testing."""
    
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found in environment")
        print(f"   Looking for .env at: {env_path}")
        return
    
    # Create engine for main database
    engine = create_engine(database_url)
    
    print("\n" + "="*80)
    print("CHATBOT TEST IDS")
    print("="*80 + "\n")
    
    with engine.connect() as conn:
        # Get all users with their roles
        print("📋 USERS:")
        print("-" * 80)
        result = conn.execute(text("""
            SELECT 
                u.id,
                u.email,
                u.role,
                u.is_active,
                op.id as owner_profile_id,
                op.business_name
            FROM users u
            LEFT JOIN owner_profiles op ON u.id = op.user_id
            ORDER BY u.role, u.email
        """))
        
        users = result.fetchall()
        
        if not users:
            print("❌ No users found in database!")
            print("\nCreate users first:")
            print("  1. Go to http://localhost:5173/auth")
            print("  2. Sign up as owner and customer")
            print("  3. Run this script again")
            return
        
        owners = []
        customers = []
        
        for user in users:
            user_id, email, role, is_active, owner_profile_id, business_name = user
            
            status = "✅" if is_active else "⚠️"
            
            if role == 'owner':
                owners.append({
                    'id': user_id,
                    'email': email,
                    'profile_id': owner_profile_id,
                    'business_name': business_name,
                    'status': status
                })
            else:
                customers.append({
                    'id': user_id,
                    'email': email,
                    'role': role,
                    'status': status
                })
        
        # Display owners
        if owners:
            print("\n🏢 OWNERS:")
            for owner in owners:
                print(f"\n  {owner['status']} Email: {owner['email']}")
                print(f"     User ID: {owner['id']}")
                if owner['profile_id']:
                    print(f"     Profile ID: {owner['profile_id']}")
                    print(f"     Business: {owner['business_name']}")
                else:
                    print(f"     ⚠️  No owner profile created yet!")
        
        # Display customers
        if customers:
            print("\n\n👤 CUSTOMERS:")
            for customer in customers:
                print(f"\n  {customer['status']} Email: {customer['email']}")
                print(f"     User ID: {customer['id']}")
                print(f"     Role: {customer['role']}")
        
        # Get properties for owners
        print("\n\n" + "="*80)
        print("📍 PROPERTIES:")
        print("-" * 80)
        
        result = conn.execute(text("""
            SELECT 
                p.id,
                p.name,
                p.owner_profile_id,
                op.user_id as owner_user_id,
                u.email as owner_email,
                COUNT(c.id) as court_count
            FROM properties p
            JOIN owner_profiles op ON p.owner_profile_id = op.id
            JOIN users u ON op.user_id = u.id
            LEFT JOIN courts c ON p.id = c.property_id
            GROUP BY p.id, p.name, p.owner_profile_id, op.user_id, u.email
            ORDER BY p.name
        """))
        
        properties = result.fetchall()
        
        if not properties:
            print("\n❌ No properties found!")
            print("\nCreate a property:")
            print("  1. Login as owner at http://localhost:5173/auth")
            print("  2. Complete owner profile")
            print("  3. Create a property")
            print("  4. Add courts to the property")
        else:
            for prop in properties:
                prop_id, name, profile_id, owner_user_id, owner_email, court_count = prop
                print(f"\n  📍 {name}")
                print(f"     Property ID: {prop_id}")
                print(f"     Owner: {owner_email}")
                print(f"     Owner User ID: {owner_user_id}")
                print(f"     Courts: {court_count}")
        
        # Get courts
        print("\n\n" + "="*80)
        print("🎾 COURTS:")
        print("-" * 80)
        
        result = conn.execute(text("""
            SELECT 
                c.id,
                c.name,
                c.sport_type,
                c.hourly_rate,
                p.name as property_name,
                u.id as owner_user_id,
                u.email as owner_email
            FROM courts c
            JOIN properties p ON c.property_id = p.id
            JOIN owner_profiles op ON p.owner_profile_id = op.id
            JOIN users u ON op.user_id = u.id
            ORDER BY p.name, c.name
        """))
        
        courts = result.fetchall()
        
        if not courts:
            print("\n❌ No courts found!")
            print("\nAdd courts to your property:")
            print("  1. Login as owner")
            print("  2. Go to Properties")
            print("  3. Click on a property")
            print("  4. Add courts")
        else:
            for court in courts:
                court_id, name, sport_type, rate, prop_name, owner_id, owner_email = court
                print(f"\n  🎾 {name} ({sport_type})")
                print(f"     Court ID: {court_id}")
                print(f"     Property: {prop_name}")
                print(f"     Rate: ${rate}/hour")
                print(f"     Owner: {owner_email} ({owner_id})")
    
    # Display test instructions
    print("\n\n" + "="*80)
    print("🧪 TESTING INSTRUCTIONS:")
    print("="*80)
    print("\n1. Go to: http://localhost:5173/chatbot-test")
    print("\n2. Enter:")
    print("   - User ID (Customer): Copy a customer user ID from above")
    print("   - Owner ID: Copy an owner user ID from above")
    print("\n3. Click 'Start Chat'")
    print("\n4. Try these messages:")
    print("   - 'Hello'")
    print("   - 'I want to book a tennis court'")
    print("   - 'Show me available facilities'")
    print("   - 'What sports do you have?'")
    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    try:
        get_test_ids()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure:")
        print("  1. Management database is running")
        print("  2. DATABASE_URL is configured in Backend/apps/management/.env")
        print("  3. You have run migrations")
