#!/usr/bin/env python3
"""
Simple test to check R2 credentials and basic functionality
"""

import os
import sys
sys.path.append('BepsApi/Backend/API')

def test_r2_credentials():
    """Test if R2 credentials are available"""
    
    print("🔍 Testing R2 credentials...")
    
    # Check environment variables
    account_id = os.getenv('CLOUDFLARE_ACCOUNT_ID')
    access_key_id = os.getenv('R2_ACCESS_KEY_ID')
    secret_access_key = os.getenv('R2_SECRET_ACCESS_KEY')
    bucket_name = os.getenv('R2_BUCKET_NAME', 'beps-contents')
    
    print(f"CLOUDFLARE_ACCOUNT_ID: {'✅ Set' if account_id else '❌ Missing'}")
    print(f"R2_ACCESS_KEY_ID: {'✅ Set' if access_key_id else '❌ Missing'}")
    print(f"R2_SECRET_ACCESS_KEY: {'✅ Set' if secret_access_key else '❌ Missing'}")
    print(f"R2_BUCKET_NAME: {bucket_name}")
    
    if not all([account_id, access_key_id, secret_access_key]):
        print("❌ Missing required R2 credentials")
        return False
    
    try:
        # Try to create R2 client
        from blueprints.contents.r2_utils import get_r2_client
        
        print("🔧 Creating R2 client...")
        r2_client = get_r2_client()
        print("✅ R2 client created successfully")
        
        # Try to list objects (just to test connection)
        print("🔍 Testing R2 connection...")
        response = r2_client.list_objects_v2(Bucket=bucket_name, MaxKeys=1)
        print(f"✅ R2 connection successful - bucket contains {response.get('KeyCount', 0)} objects (showing max 1)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing R2: {str(e)}")
        return False

def test_simple_object_check():
    """Test checking for a simple object"""
    
    print("\n🔍 Testing simple object check...")
    
    try:
        from blueprints.contents.r2_utils import check_r2_object_exists
        
        # Test with a simple object key
        test_key = "test/nonexistent.png"
        result = check_r2_object_exists(test_key)
        print(f"Test object '{test_key}' exists: {result}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing object check: {str(e)}")
        return False

if __name__ == "__main__":
    print("🧪 R2 Simple Test")
    print("=" * 50)
    
    if test_r2_credentials():
        test_simple_object_check()
    else:
        print("❌ Cannot proceed with object tests due to credential issues") 