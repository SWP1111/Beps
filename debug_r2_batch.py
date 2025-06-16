#!/usr/bin/env python3
"""
Debug script to test R2 batch check functionality
"""

import sys
import os
sys.path.append('BepsApi/Backend/API')

from models import ContentRelPages, ContentRelPageDetails
from services.r2_storage_service import R2StorageService
from blueprints.contents.r2_utils import generate_r2_object_key, check_r2_object_exists
from app import create_app

def test_r2_batch_check():
    """Test the R2 batch check functionality"""
    
    app = create_app()
    
    with app.app_context():
        print("🔍 Testing R2 batch check functionality...")
        
        # Get some sample pages
        pages = ContentRelPages.query.filter_by(is_deleted=False).limit(5).all()
        
        if not pages:
            print("❌ No pages found in database")
            return
        
        print(f"📄 Found {len(pages)} pages to test:")
        
        for page in pages:
            print(f"\n--- Page ID: {page.id} ---")
            print(f"Name: {page.name}")
            print(f"Object ID: {page.object_id}")
            
            # Test the check_r2_content_exists method
            try:
                r2_exists = page.check_r2_content_exists()
                print(f"R2 exists (method): {r2_exists}")
                
                # Test the service directly
                service_result = R2StorageService.check_page_content_exists(
                    page_id=page.id,
                    page_name=page.name,
                    page_object_id=page.object_id,
                    updated_at=page.updated_at,
                    use_cache=False
                )
                print(f"R2 exists (service): {service_result}")
                
                # Test object key generation
                if page.name:
                    filename = page.name if any(page.name.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.pdf']) else f"{page.name}.png"
                    object_key = generate_r2_object_key(page.id, filename, is_page_detail=False)
                    print(f"Generated object key: {object_key}")
                    
                    # Test direct R2 check
                    direct_check = check_r2_object_exists(object_key)
                    print(f"Direct R2 check: {direct_check}")
                
            except Exception as e:
                print(f"❌ Error testing page {page.id}: {str(e)}")
        
        # Test page details
        print("\n" + "="*50)
        print("Testing Page Details...")
        
        details = ContentRelPageDetails.query.filter_by(is_deleted=False).limit(3).all()
        
        if not details:
            print("❌ No page details found in database")
            return
        
        print(f"📄 Found {len(details)} page details to test:")
        
        for detail in details:
            print(f"\n--- Page Detail ID: {detail.id} ---")
            print(f"Name: {detail.name}")
            print(f"Object ID: {detail.object_id}")
            print(f"Page ID: {detail.page_id}")
            
            try:
                r2_exists = detail.check_r2_content_exists()
                print(f"R2 exists (method): {r2_exists}")
                
                # Test the service directly
                service_result = R2StorageService.check_page_detail_content_exists(
                    detail_id=detail.id,
                    detail_name=detail.name,
                    detail_object_id=detail.object_id,
                    updated_at=detail.updated_at,
                    use_cache=False
                )
                print(f"R2 exists (service): {service_result}")
                
                # Test object key generation
                if detail.name:
                    filename = detail.name if any(detail.name.endswith(ext) for ext in ['.pdf', '.webm', '.mp4', '.avi', '.mov', '.wmv', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx']) else f"{detail.name}.pdf"
                    object_key = generate_r2_object_key(detail.id, filename, is_page_detail=True)
                    print(f"Generated object key: {object_key}")
                    
                    # Test direct R2 check
                    direct_check = check_r2_object_exists(object_key)
                    print(f"Direct R2 check: {direct_check}")
                
            except Exception as e:
                print(f"❌ Error testing page detail {detail.id}: {str(e)}")

if __name__ == "__main__":
    test_r2_batch_check() 