#!/usr/bin/env python3
"""
Database migration script to add created_at column to memo_data table.
This script adds the created_at column and sets it to the current modified_at value for existing records.
"""

import os
import sys
from sqlalchemy import create_engine, text
from datetime import datetime

# Add the parent directory to the path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from API.config import Config
    
    def run_migration():
        """Execute the migration to add created_at column to memo_data table."""
        
        # Create database engine
        engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
        
        print(f"Starting migration at {datetime.now()}")
        print(f"Database URI: {Config.SQLALCHEMY_DATABASE_URI[:50]}...")
        
        with engine.connect() as connection:
            # Start transaction
            trans = connection.begin()
            
            try:
                # Check if column already exists
                print("Checking if created_at column exists...")
                check_column_sql = """
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'memo_data' AND column_name = 'created_at';
                """
                result = connection.execute(text(check_column_sql))
                if result.fetchone():
                    print("created_at column already exists. Migration skipped.")
                    return
                
                print("Adding created_at column...")
                # Add the created_at column with default value
                add_column_sql = """
                ALTER TABLE memo_data 
                ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
                """
                connection.execute(text(add_column_sql))
                
                print("Updating existing records...")
                # Update existing records to use modified_at as initial created_at value
                update_records_sql = """
                UPDATE memo_data 
                SET created_at = modified_at 
                WHERE created_at IS NULL;
                """
                result = connection.execute(text(update_records_sql))
                print(f"Updated {result.rowcount} existing memo records")
                
                print("Setting column constraints...")
                # Make the column NOT NULL after setting values
                set_not_null_sql = """
                ALTER TABLE memo_data 
                ALTER COLUMN created_at SET NOT NULL;
                """
                connection.execute(text(set_not_null_sql))
                
                print("Adding column comments...")
                # Add comments to document the purpose
                add_comments_sql = """
                COMMENT ON COLUMN memo_data.created_at IS 'Registration date (등록일) - never changes after memo creation';
                COMMENT ON COLUMN memo_data.modified_at IS 'Last modification date - updates when memo is edited or status changed';
                """
                connection.execute(text(add_comments_sql))
                
                # Verify the migration
                print("Verifying migration...")
                verify_sql = """
                SELECT 
                    id,
                    created_at,
                    modified_at,
                    title,
                    status
                FROM memo_data
                ORDER BY id DESC
                LIMIT 5;
                """
                result = connection.execute(text(verify_sql))
                rows = result.fetchall()
                
                print("\nMigration verification (latest 5 records):")
                print("-" * 80)
                for row in rows:
                    print(f"ID: {row[0]}, Created: {row[1]}, Modified: {row[2]}, Title: {row[3][:30]}...")
                
                # Commit transaction
                trans.commit()
                print(f"\nMigration completed successfully at {datetime.now()}")
                
            except Exception as e:
                trans.rollback()
                print(f"Migration failed: {str(e)}")
                raise
                
except ImportError as e:
    print(f"Error importing config: {e}")
    print("Please ensure you're running this script from the correct directory")
    sys.exit(1)

if __name__ == "__main__":
    run_migration()
