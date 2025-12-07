"""
Meru Deliveries - Flask Application
A food delivery web application with Flask backend and PyMySQL database connection.
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_mail import Mail, Message
import pymysql
from functools import wraps
import os
from datetime import datetime, time, timedelta
import re
import json
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import uuid
import requests
import base64

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Change this to a secure secret key in production

# Email Configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'denzkimathi@gmail.com'
app.config['MAIL_PASSWORD'] = 'wler unom gnaz lvlu'
app.config['MAIL_DEFAULT_SENDER'] = 'noreply@kwetudeliveries.com'

# Support Contact Information
SUPPORT_EMAIL = 'support@kwetudeliveries.com'
SUPPORT_PHONE = '+254 795606115'
COMPANY_NAME = 'KWETU DELIVERIES'

# M-Pesa API Configuration
MPESA_CONSUMER_KEY = os.getenv('MPESA_CONSUMER_KEY', 'RJWju7h6uSGnyVe9CzXsNVUZxHKpWeCBCTGp1fF29oCdzuhb')
MPESA_CONSUMER_SECRET = os.getenv('MPESA_CONSUMER_SECRET', 'F42bkZlWj8122pUgryB7ZulHrDautuRGyF3HzLlPdiTK2bGpAOxj4TFeg4qtQLbf')
MPESA_PASSKEY = os.getenv('MPESA_PASSKEY', 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919')
MPESA_ENVIRONMENT = os.getenv('MPESA_ENVIRONMENT', 'sandbox')  # 'sandbox' or 'production'

# M-Pesa Sandbox Test Credentials
MPESA_SANDBOX_PAYBILL = '174379'  # Test Paybill number for sandbox
MPESA_SANDBOX_TILL = '174379'     # Test Till number for sandbox

# M-Pesa API URLs
if MPESA_ENVIRONMENT == 'production':
    MPESA_BASE_URL = 'https://api.safaricom.co.ke'
else:
    MPESA_BASE_URL = 'https://sandbox.safaricom.co.ke'

# File Upload Configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize Mail
mail = Mail(app)

# Create upload directories
os.makedirs(os.path.join(UPLOAD_FOLDER, 'profiles'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'documents'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'items'), exist_ok=True)

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',  # Update with your MySQL password
    'database': None,  # Will be set after database creation
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

DATABASE_NAME = 'MERU_DELIVERIES'

def get_db_connection(use_database=True):
    """Create and return a database connection."""
    try:
        config = DB_CONFIG.copy()
        if not use_database:
            config['database'] = None
        elif use_database and config['database'] is None:
            config['database'] = DATABASE_NAME
        connection = pymysql.connect(**config)
        return connection
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def database_exists():
    """Check if the database exists."""
    connection = get_db_connection(use_database=False)
    if not connection:
        return False
    try:
        with connection.cursor() as cursor:
            cursor.execute("SHOW DATABASES LIKE %s", (DATABASE_NAME,))
            result = cursor.fetchone()
            return result is not None
    except Exception as e:
        print(f"Error checking database existence: {e}")
        return False
    finally:
        connection.close()

def create_database():
    """Create the database if it doesn't exist."""
    if database_exists():
        print(f"Database '{DATABASE_NAME}' already exists.")
        return True
    
    connection = get_db_connection(use_database=False)
    if not connection:
        print("Failed to connect to MySQL server.")
        return False
    
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DATABASE_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            connection.commit()
            print(f"Database '{DATABASE_NAME}' created successfully.")
            DB_CONFIG['database'] = DATABASE_NAME
            return True
    except Exception as e:
        print(f"Error creating database: {e}")
        return False
    finally:
        connection.close()

def table_exists(table_name):
    """Check if a table exists in the database."""
    connection = get_db_connection()
    if not connection:
        return False
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM information_schema.tables 
                WHERE table_schema = %s AND table_name = %s
            """, (DATABASE_NAME, table_name))
            result = cursor.fetchone()
            return result['count'] > 0
    except Exception as e:
        print(f"Error checking table existence: {e}")
        return False
    finally:
        connection.close()

def get_table_columns(table_name):
    """Get all column names for a table."""
    connection = get_db_connection()
    if not connection:
        return []
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"DESCRIBE {table_name}")
            columns = cursor.fetchall()
            return [col['Field'] for col in columns]
    except Exception as e:
        print(f"Error getting table columns: {e}")
        return []
    finally:
        connection.close()

def column_exists(table_name, column_name):
    """Check if a column exists in a table."""
    columns = get_table_columns(table_name)
    return column_name in columns

def add_missing_columns():
    """Add missing columns to existing tables."""
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        with connection.cursor() as cursor:
            # Check and add columns to employees table
            if table_exists('employees'):
                employees_columns = {
                    'email': ("ALTER TABLE employees ADD COLUMN email VARCHAR(100)", "ALTER TABLE employees ADD UNIQUE KEY idx_email (email)"),
                    'phone': "ALTER TABLE employees ADD COLUMN phone VARCHAR(20)",
                    'login_code': ("ALTER TABLE employees ADD COLUMN login_code VARCHAR(4)", "ALTER TABLE employees ADD UNIQUE KEY idx_login_code (login_code)"),
                    'password': "ALTER TABLE employees ADD COLUMN password VARCHAR(255)",
                    'profile_picture': "ALTER TABLE employees ADD COLUMN profile_picture VARCHAR(255)",
                    'id_document': "ALTER TABLE employees MODIFY COLUMN id_document TEXT",
                    'kwetu_employee_role': "ALTER TABLE employees ADD COLUMN kwetu_employee_role ENUM('KWETU_EMPLOYEE', 'KWETU_ADMIN', 'KWETU_MANAGER', 'KWETU_CASHIER', 'KWETU_SALES', 'KWETU_RIDER', 'KWETU_CUSTOMERCARE', 'KWETU_TECHNICIAN', 'KWETU_IT_SUPPORT') DEFAULT 'KWETU_EMPLOYEE'",
                    'status': "ALTER TABLE employees ADD COLUMN status ENUM('waiting_approval', 'approved', 'rejected', 'active', 'suspended', 'banned') DEFAULT 'waiting_approval'",
                    'created_at': "ALTER TABLE employees ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                    'updated_at': "ALTER TABLE employees ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"
                }
                
                existing_columns = get_table_columns('employees')
                for col_name, alter_sql in employees_columns.items():
                    if col_name not in existing_columns:
                        print(f"Adding column '{col_name}' to employees table...")
                        try:
                            if isinstance(alter_sql, tuple):
                                # Handle columns that need UNIQUE constraint
                                cursor.execute(alter_sql[0])
                                connection.commit()
                                try:
                                    cursor.execute(alter_sql[1])
                                    connection.commit()
                                except:
                                    pass  # Index might already exist
                            else:
                                cursor.execute(alter_sql)
                                connection.commit()
                            print(f"Column '{col_name}' added successfully.")
                            migration_name = f"add_column_employees_{col_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                            record_migration(migration_name, f"Added column {col_name} to employees table")
                        except Exception as e:
                            print(f"Error adding column '{col_name}': {e}")
                    elif col_name == 'id_document' and 'id_document' in existing_columns:
                        # Check if it needs to be modified to TEXT
                        try:
                            cursor.execute("ALTER TABLE employees MODIFY COLUMN id_document TEXT")
                            connection.commit()
                            print(f"Modified column 'id_document' to TEXT.")
                        except Exception as e:
                            print(f"Error modifying column 'id_document': {e}")
                
                # Add index for kwetu_employee_role if column exists
                existing_columns = get_table_columns('employees')
                if 'kwetu_employee_role' in existing_columns:
                    try:
                        cursor.execute("SHOW INDEX FROM employees WHERE Key_name = 'idx_kwetu_employee_role'")
                        if not cursor.fetchone():
                            cursor.execute("CREATE INDEX idx_kwetu_employee_role ON employees(kwetu_employee_role)")
                            connection.commit()
                            print("Added index idx_kwetu_employee_role to employees table.")
                    except Exception as e:
                        print(f"Error adding index idx_kwetu_employee_role: {e}")
                
                # Add index for category if column exists in shops table
                existing_columns = get_table_columns('shops')
                if 'category' in existing_columns:
                    try:
                        cursor.execute("SHOW INDEX FROM shops WHERE Key_name = 'idx_category'")
                        if not cursor.fetchone():
                            cursor.execute("CREATE INDEX idx_category ON shops(category)")
                            connection.commit()
                            print("Added index idx_category to shops table.")
                    except Exception as e:
                        print(f"Error adding index idx_category: {e}")
                
                # Update status ENUM for employees table if column exists
                existing_columns = get_table_columns('employees')
                if 'status' in existing_columns:
                    try:
                        # Check current ENUM values
                        cursor.execute("SHOW COLUMNS FROM employees WHERE Field = 'status'")
                        column_info = cursor.fetchone()
                        if column_info:
                            current_type = column_info['Type']
                            # Check if new values are missing
                            if 'active' not in current_type or 'suspended' not in current_type or 'banned' not in current_type:
                                cursor.execute("ALTER TABLE employees MODIFY COLUMN status ENUM('waiting_approval', 'approved', 'rejected', 'active', 'suspended', 'banned') DEFAULT 'waiting_approval'")
                                connection.commit()
                                print("Updated employees status ENUM to include active, suspended, banned.")
                                migration_name = f"update_employees_status_enum_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                                record_migration(migration_name, "Updated employees status ENUM to include active, suspended, banned")
                    except Exception as e:
                        print(f"Error updating employees status ENUM: {e}")
                
                # Update status ENUM for shops table if column exists
                existing_columns = get_table_columns('shops')
                if 'status' in existing_columns:
                    try:
                        # Check current ENUM values
                        cursor.execute("SHOW COLUMNS FROM shops WHERE Field = 'status'")
                        column_info = cursor.fetchone()
                        if column_info:
                            current_type = column_info['Type']
                            # Check if new values are missing
                            if 'open' not in current_type or 'suspended' not in current_type or 'banned' not in current_type or 'closed' not in current_type:
                                cursor.execute("ALTER TABLE shops MODIFY COLUMN status ENUM('waiting_approval', 'approved', 'rejected', 'open', 'suspended', 'banned', 'closed') DEFAULT 'waiting_approval'")
                                connection.commit()
                                print("Updated shops status ENUM to include open, suspended, banned, closed.")
                                migration_name = f"update_shops_status_enum_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                                record_migration(migration_name, "Updated shops status ENUM to include open, suspended, banned, closed")
                    except Exception as e:
                        print(f"Error updating shops status ENUM: {e}")
            
            # Check and add columns to shops table
            if table_exists('shops'):
                shops_columns = {
                    'email': ("ALTER TABLE shops ADD COLUMN email VARCHAR(100)", "ALTER TABLE shops ADD UNIQUE KEY idx_email (email)"),
                    'category': "ALTER TABLE shops ADD COLUMN category VARCHAR(100)",
                    'phone': "ALTER TABLE shops ADD COLUMN phone VARCHAR(20)",
                    'login_code': ("ALTER TABLE shops ADD COLUMN login_code VARCHAR(6)", "ALTER TABLE shops ADD UNIQUE KEY idx_login_code (login_code)"),
                    'password': "ALTER TABLE shops ADD COLUMN password VARCHAR(255)",
                    'profile_image': "ALTER TABLE shops ADD COLUMN profile_image VARCHAR(255)",
                    'business_document': "ALTER TABLE shops ADD COLUMN business_document VARCHAR(255)",
                    'location_name': "ALTER TABLE shops ADD COLUMN location_name VARCHAR(255)",
                    'longitude': "ALTER TABLE shops ADD COLUMN longitude DECIMAL(10, 8)",
                    'latitude': "ALTER TABLE shops ADD COLUMN latitude DECIMAL(10, 8)",
                    'status': "ALTER TABLE shops ADD COLUMN status ENUM('waiting_approval', 'approved', 'rejected', 'open', 'suspended', 'banned', 'closed') DEFAULT 'waiting_approval'",
                    'delivery_mode': "ALTER TABLE shops ADD COLUMN delivery_mode TINYINT(1) DEFAULT 0",
                    'created_at': "ALTER TABLE shops ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                    'updated_at': "ALTER TABLE shops ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"
                }
                
                existing_columns = get_table_columns('shops')
                for col_name, alter_sql in shops_columns.items():
                    if col_name not in existing_columns:
                        print(f"Adding column '{col_name}' to shops table...")
                        try:
                            if isinstance(alter_sql, tuple):
                                # Handle columns that need UNIQUE constraint
                                cursor.execute(alter_sql[0])
                                connection.commit()
                                try:
                                    cursor.execute(alter_sql[1])
                                    connection.commit()
                                except:
                                    pass  # Index might already exist
                            else:
                                cursor.execute(alter_sql)
                                connection.commit()
                            print(f"Column '{col_name}' added successfully.")
                            migration_name = f"add_column_shops_{col_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                            record_migration(migration_name, f"Added column {col_name} to shops table")
                        except Exception as e:
                            print(f"Error adding column '{col_name}': {e}")
                            import traceback
                            traceback.print_exc()
                
                # Check if delivery_mode exists and needs to be converted from ENUM to TINYINT
                existing_columns = get_table_columns('shops')
                if 'delivery_mode' in existing_columns:
                    try:
                        # Check current column type
                        cursor.execute("SHOW COLUMNS FROM shops WHERE Field = 'delivery_mode'")
                        column_info = cursor.fetchone()
                        if column_info:
                            current_type = column_info['Type']
                            # If it's an ENUM, convert it to TINYINT(1)
                            if 'ENUM' in current_type.upper():
                                # First, convert existing values: 'items_with_delivery' -> 0, 'delivery_only' -> 1
                                cursor.execute("UPDATE shops SET delivery_mode = CASE WHEN delivery_mode = 'delivery_only' THEN 1 ELSE 0 END")
                                connection.commit()
                                # Then alter the column type
                                cursor.execute("ALTER TABLE shops MODIFY COLUMN delivery_mode TINYINT(1) DEFAULT 0")
                                connection.commit()
                                print("Converted delivery_mode from ENUM to TINYINT(1)")
                                migration_name = f"convert_delivery_mode_to_tinyint_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                                record_migration(migration_name, "Converted delivery_mode from ENUM to TINYINT(1)")
                    except Exception as e:
                        print(f"Error converting delivery_mode column: {e}")
            
            # Check and add payment columns to shops table
            if table_exists('shops'):
                existing_columns = get_table_columns('shops')
                shop_payment_columns = {
                    'payments_to_shop': "ALTER TABLE shops ADD COLUMN payments_to_shop TINYINT(1) DEFAULT 0",
                    'payment_method': "ALTER TABLE shops ADD COLUMN payment_method ENUM('cash', 'mpesa', 'bank', 'cash_mpesa', 'cash_bank', 'mpesa_bank', 'all') DEFAULT 'cash'",
                    'mpesa_type': "ALTER TABLE shops ADD COLUMN mpesa_type ENUM('paybill', 'buy_goods') DEFAULT 'paybill'",
                    'mpesa_paybill_business_number': "ALTER TABLE shops ADD COLUMN mpesa_paybill_business_number VARCHAR(20)",
                    'mpesa_paybill_account': "ALTER TABLE shops ADD COLUMN mpesa_paybill_account VARCHAR(50)",
                    'mpesa_buy_goods_till': "ALTER TABLE shops ADD COLUMN mpesa_buy_goods_till VARCHAR(20)",
                    'bank_merchant_account': "ALTER TABLE shops ADD COLUMN bank_merchant_account VARCHAR(100)"
                }
                
                for col_name, alter_sql in shop_payment_columns.items():
                    if col_name not in existing_columns:
                        try:
                            print(f"Adding column '{col_name}' to shops table...")
                            cursor.execute(alter_sql)
                            connection.commit()
                            print(f"Column '{col_name}' added successfully.")
                            migration_name = f"add_column_shops_{col_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                            record_migration(migration_name, f"Added column {col_name} to shops table")
                        except Exception as e:
                            print(f"Error adding column '{col_name}': {e}")
                            import traceback
                            traceback.print_exc()
            
            # Check and add missing columns to orders table
            if table_exists('orders'):
                existing_columns = get_table_columns('orders')
                orders_columns = {
                    'customer_id': "ALTER TABLE orders ADD COLUMN customer_id INT",
                    'order_type': "ALTER TABLE orders ADD COLUMN order_type VARCHAR(50)",
                    'status': "ALTER TABLE orders ADD COLUMN status ENUM('pending', 'confirmed', 'preparing', 'ready', 'out_for_delivery', 'delivered', 'cancelled', 'PACKED', 'PROCESSING', 'PENDING') DEFAULT 'pending'",
                    'total_amount': "ALTER TABLE orders ADD COLUMN total_amount DECIMAL(10, 2) DEFAULT 0.00",
                'cancellation_reason': "ALTER TABLE orders ADD COLUMN cancellation_reason VARCHAR(255) DEFAULT NULL",
                'pickup_code': "ALTER TABLE orders ADD COLUMN pickup_code VARCHAR(4) DEFAULT NULL",
                'rider_name': "ALTER TABLE orders ADD COLUMN rider_name VARCHAR(100) DEFAULT NULL",
                'rider_phone': "ALTER TABLE orders ADD COLUMN rider_phone VARCHAR(20) DEFAULT NULL",
                'drop_order_status': "ALTER TABLE orders DROP COLUMN IF EXISTS order_status"
                }
                
                for col_name, alter_sql in orders_columns.items():
                    if col_name not in existing_columns:
                        try:
                            print(f"Adding column '{col_name}' to orders table...")
                            cursor.execute(alter_sql)
                            connection.commit()
                            print(f"Column '{col_name}' added successfully.")
                            migration_name = f"add_column_orders_{col_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                            record_migration(migration_name, f"Added column {col_name} to orders table")
                        except Exception as e:
                            error_msg = str(e).lower()
                            if 'duplicate' not in error_msg and 'already exists' not in error_msg:
                                print(f"Error adding column '{col_name}': {e}")
                                import traceback
                                traceback.print_exc()
                            else:
                                print(f"Column '{col_name}' already exists, skipping...")
            
            # Check and add missing columns to delivery_details table
            if table_exists('delivery_details'):
                existing_columns = get_table_columns('delivery_details')
                delivery_columns = {
                    'shop_latitude': "ALTER TABLE delivery_details ADD COLUMN shop_latitude DECIMAL(10, 8)",
                    'shop_longitude': "ALTER TABLE delivery_details ADD COLUMN shop_longitude DECIMAL(10, 8)"
                }
                
                for col_name, alter_sql in delivery_columns.items():
                    if col_name not in existing_columns:
                        try:
                            print(f"Adding column '{col_name}' to delivery_details table...")
                            cursor.execute(alter_sql)
                            connection.commit()
                            print(f"Column '{col_name}' added successfully.")
                        except Exception as e:
                            error_msg = str(e).lower()
                            if 'duplicate' not in error_msg:
                                print(f"Error adding column '{col_name}': {e}")
            
            # Check and modify order_items table to make item_id nullable for package deliveries
            if table_exists('order_items'):
                try:
                    # Check if item_id is NOT NULL
                    cursor.execute("SHOW COLUMNS FROM order_items WHERE Field = 'item_id'")
                    item_id_col = cursor.fetchone()
                    if item_id_col and 'NO' in item_id_col.get('Null', ''):
                        # Make item_id nullable to support package deliveries
                        cursor.execute("ALTER TABLE order_items MODIFY COLUMN item_id INT NULL")
                        connection.commit()
                        print("Modified order_items.item_id to allow NULL for package deliveries.")
                        migration_name = f"modify_order_items_item_id_nullable_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        record_migration(migration_name, "Modified order_items.item_id to allow NULL")
                except Exception as e:
                    error_msg = str(e).lower()
                    if 'duplicate' not in error_msg and 'already exists' not in error_msg:
                        print(f"Error modifying order_items.item_id: {e}")
            
            return True
    except Exception as e:
        print(f"Error adding missing columns: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        connection.close()

def create_migrations_table():
    """Create the migrations table to track database changes."""
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS migrations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    migration_name VARCHAR(255) UNIQUE NOT NULL,
                    description TEXT,
                    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_migration_name (migration_name)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            connection.commit()
            print("Migrations table created/verified successfully.")
            return True
    except Exception as e:
        print(f"Error creating migrations table: {e}")
        return False
    finally:
        connection.close()

def migration_exists(migration_name):
    """Check if a migration has already been executed."""
    connection = get_db_connection()
    if not connection:
        return False
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM migrations WHERE migration_name = %s", (migration_name,))
            result = cursor.fetchone()
            return result['count'] > 0
    except Exception as e:
        print(f"Error checking migration: {e}")
        return False
    finally:
        connection.close()

def record_migration(migration_name, description=""):
    """Record that a migration has been executed."""
    connection = get_db_connection()
    if not connection:
        return False
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO migrations (migration_name, description) 
                VALUES (%s, %s)
            """, (migration_name, description))
            connection.commit()
            print(f"Migration '{migration_name}' recorded successfully.")
            return True
    except Exception as e:
        print(f"Error recording migration: {e}")
        return False
    finally:
        connection.close()

def init_tables():
    """Initialize all database tables with detailed checking."""
    connection = get_db_connection()
    if not connection:
        print("Failed to connect to database.")
        return False
    
    try:
        with connection.cursor() as cursor:
            # Define all tables and their schemas
            tables = {
                'delivery_settings': """
                    CREATE TABLE IF NOT EXISTS delivery_settings (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        minimum_fee INT NOT NULL DEFAULT 150,
                        weather_fee DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                        priority_percentage DECIMAL(5, 2) NOT NULL DEFAULT 0.00,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """,
                'delivery_distance_tiers': """
                    CREATE TABLE IF NOT EXISTS delivery_distance_tiers (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        start_km DECIMAL(10, 2) NOT NULL,
                        end_km DECIMAL(10, 2) NOT NULL,
                        price_per_km DECIMAL(10, 2) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_start_km (start_km),
                        INDEX idx_end_km (end_km)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """,
                'delivery_weight_tiers': """
                    CREATE TABLE IF NOT EXISTS delivery_weight_tiers (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        min_kg DECIMAL(10, 2) NOT NULL,
                        max_kg DECIMAL(10, 2) NOT NULL,
                        fee_amount DECIMAL(10, 2) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_min_kg (min_kg),
                        INDEX idx_max_kg (max_kg)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """,
                'delivery_peak_hours': """
                    CREATE TABLE IF NOT EXISTS delivery_peak_hours (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        start_time TIME NOT NULL,
                        end_time TIME NOT NULL,
                        percentage_increase DECIMAL(5, 2) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_start_time (start_time),
                        INDEX idx_end_time (end_time)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """,
                'delivery_night_hours': """
                    CREATE TABLE IF NOT EXISTS delivery_night_hours (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        start_time TIME NOT NULL,
                        end_time TIME NOT NULL,
                        night_percentage DECIMAL(5, 2) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_start_time (start_time),
                        INDEX idx_end_time (end_time)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """,
                'shop_order_settings': """
                    CREATE TABLE IF NOT EXISTS shop_order_settings (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        shop_id INT NOT NULL UNIQUE,
                        auto_confirm_order TINYINT(1) DEFAULT 0,
                        order_processing_time INT NOT NULL DEFAULT 30,
                        max_daily_orders INT DEFAULT NULL,
                        allow_scheduled_orders TINYINT(1) DEFAULT 0,
                        custom_delay_message TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE,
                        INDEX idx_shop_id (shop_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """,
                'shop_peak_hours': """
                    CREATE TABLE IF NOT EXISTS shop_peak_hours (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        shop_id INT NOT NULL,
                        start_time TIME NOT NULL,
                        end_time TIME NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE,
                        INDEX idx_shop_id (shop_id),
                        INDEX idx_start_time (start_time),
                        INDEX idx_end_time (end_time)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """,
                'payment_settings': """
                    CREATE TABLE IF NOT EXISTS payment_settings (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        payments_to_shops TINYINT(1) DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """,
                'company_payment_accounts': """
                    CREATE TABLE IF NOT EXISTS company_payment_accounts (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        allow_cash_on_delivery TINYINT(1) DEFAULT 1,
                        allow_mpesa TINYINT(1) DEFAULT 1,
                        allow_bank_card TINYINT(1) DEFAULT 0,
                        mpesa_type ENUM('paybill', 'buy_goods') DEFAULT 'paybill',
                        mpesa_paybill_business_number VARCHAR(20),
                        mpesa_paybill_account VARCHAR(50),
                        mpesa_buy_goods_till VARCHAR(20),
                        bank_merchant_account VARCHAR(100),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """,
                'shop_payment_accounts': """
                    CREATE TABLE IF NOT EXISTS shop_payment_accounts (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        shop_id INT NOT NULL UNIQUE,
                        payments_to_shop TINYINT(1) DEFAULT 0,
                        allow_cash_on_delivery TINYINT(1) DEFAULT 1,
                        allow_mpesa TINYINT(1) DEFAULT 1,
                        allow_bank_card TINYINT(1) DEFAULT 0,
                        mpesa_type ENUM('paybill', 'buy_goods') DEFAULT 'paybill',
                        mpesa_paybill_business_number VARCHAR(20),
                        mpesa_paybill_account VARCHAR(50),
                        mpesa_buy_goods_till VARCHAR(20),
                        bank_merchant_account VARCHAR(100),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE,
                        INDEX idx_shop_id (shop_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """,
                'stk_push_requests': """
                    CREATE TABLE IF NOT EXISTS stk_push_requests (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        order_id INT NOT NULL,
                        checkout_request_id VARCHAR(100) UNIQUE NOT NULL,
                        phone_number VARCHAR(20) NOT NULL,
                        amount DECIMAL(10, 2) NOT NULL,
                        status ENUM('pending', 'completed', 'failed', 'cancelled') DEFAULT 'pending',
                        mpesa_receipt_number VARCHAR(50),
                        transaction_date VARCHAR(20),
                        result_code VARCHAR(10),
                        result_desc TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_order_id (order_id),
                        INDEX idx_checkout_request_id (checkout_request_id),
                        INDEX idx_status (status),
                        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """,
                'customers': """
                    CREATE TABLE IF NOT EXISTS customers (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR(100) NOT NULL,
                        phone VARCHAR(20) NOT NULL,
                        email VARCHAR(100),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_phone (phone),
                        INDEX idx_email (email)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """,
                'employees': """
                    CREATE TABLE IF NOT EXISTS employees (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        full_name VARCHAR(100) NOT NULL,
                        email VARCHAR(100) UNIQUE NOT NULL,
                        phone VARCHAR(20) NOT NULL,
                        login_code VARCHAR(4) UNIQUE NOT NULL,
                        password VARCHAR(255) NOT NULL,
                        profile_picture VARCHAR(255),
                        id_document TEXT,
                        kwetu_employee_role ENUM('KWETU_EMPLOYEE', 'KWETU_ADMIN', 'KWETU_MANAGER', 'KWETU_CASHIER', 'KWETU_SALES', 'KWETU_RIDER', 'KWETU_CUSTOMERCARE', 'KWETU_TECHNICIAN', 'KWETU_IT_SUPPORT') DEFAULT 'KWETU_EMPLOYEE',
                        status ENUM('waiting_approval', 'approved', 'rejected', 'active', 'suspended', 'banned') DEFAULT 'waiting_approval',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_email (email),
                        INDEX idx_login_code (login_code),
                        INDEX idx_status (status),
                        INDEX idx_kwetu_employee_role (kwetu_employee_role)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """,
                'shops': """
                    CREATE TABLE IF NOT EXISTS shops (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR(100) NOT NULL,
                        category VARCHAR(100),
                        email VARCHAR(100) UNIQUE NOT NULL,
                        phone VARCHAR(20) NOT NULL,
                        login_code VARCHAR(6) UNIQUE NOT NULL,
                        password VARCHAR(255) NOT NULL,
                        profile_image VARCHAR(255),
                        business_document VARCHAR(255),
                        location_name VARCHAR(255),
                        longitude DECIMAL(10, 8),
                        latitude DECIMAL(10, 8),
                        description TEXT,
                        rating DECIMAL(3,2) DEFAULT 0.00,
                        delivery_time VARCHAR(20),
                        status ENUM('waiting_approval', 'approved', 'rejected', 'open', 'suspended', 'banned', 'closed') DEFAULT 'waiting_approval',
                        delivery_mode TINYINT(1) DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_email (email),
                        INDEX idx_login_code (login_code),
                        INDEX idx_status (status),
                        INDEX idx_rating (rating),
                        INDEX idx_category (category)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """,
                'orders': """
                    CREATE TABLE IF NOT EXISTS orders (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        order_number VARCHAR(20) UNIQUE NOT NULL,
                        shop_id INT NOT NULL,
                        customer_name VARCHAR(100),
                        customer_phone VARCHAR(20),
                        customer_email VARCHAR(100),
                        subtotal DECIMAL(10, 2) NOT NULL,
                        delivery_fee DECIMAL(10, 2) DEFAULT 0.00,
                        tax DECIMAL(10, 2) DEFAULT 0.00,
                        discount DECIMAL(10, 2) DEFAULT 0.00,
                        total DECIMAL(10, 2) NOT NULL,
                        payment_method ENUM('mpesa', 'cash_on_delivery', 'card', 'wallet') DEFAULT 'cash_on_delivery',
                        payment_status ENUM('pending', 'paid', 'failed', 'refunded') DEFAULT 'pending',
                        promo_code VARCHAR(50),
                        notes TEXT,
                        contactless_delivery TINYINT(1) DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_order_number (order_number),
                        INDEX idx_shop_id (shop_id),
                        INDEX idx_customer_phone (customer_phone),
                        INDEX idx_payment_status (payment_status),
                        INDEX idx_created_at (created_at),
                        FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """,
                'order_items': """
                    CREATE TABLE IF NOT EXISTS order_items (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        order_id INT NOT NULL,
                        item_id INT NULL,
                        item_name VARCHAR(255) NOT NULL,
                        item_image VARCHAR(255),
                        quantity INT NOT NULL DEFAULT 1,
                        unit_price DECIMAL(10, 2) NOT NULL,
                        discount_price DECIMAL(10, 2) NULL,
                        subtotal DECIMAL(10, 2) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_order_id (order_id),
                        INDEX idx_item_id (item_id),
                        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                        FOREIGN KEY (item_id) REFERENCES shop_items(id) ON DELETE SET NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """,
                'delivery': """
                    CREATE TABLE IF NOT EXISTS delivery (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        order_id INT NOT NULL,
                        delivery_address TEXT NOT NULL,
                        delivery_latitude DECIMAL(10, 8),
                        delivery_longitude DECIMAL(10, 8),
                        shop_latitude DECIMAL(10, 8),
                        shop_longitude DECIMAL(10, 8),
                        distance_km DECIMAL(8, 2),
                        estimated_time_minutes INT,
                        rider_id INT NULL,
                        delivery_status ENUM('pending', 'assigned', 'picked_up', 'in_transit', 'delivered', 'failed') DEFAULT 'pending',
                        delivered_at TIMESTAMP NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_order_id (order_id),
                        INDEX idx_rider_id (rider_id),
                        INDEX idx_delivery_status (delivery_status),
                        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                        FOREIGN KEY (rider_id) REFERENCES employees(id) ON DELETE SET NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """,
                'delivery_details': """
                    CREATE TABLE IF NOT EXISTS delivery_details (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        order_id INT NOT NULL,
                        delivery_location_name VARCHAR(255) NOT NULL,
                        delivery_latitude DECIMAL(10, 8) NOT NULL,
                        delivery_longitude DECIMAL(10, 8) NOT NULL,
                        shop_latitude DECIMAL(10, 8),
                        shop_longitude DECIMAL(10, 8),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_order_id (order_id),
                        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            }
            
            # Create each table and verify
            for table_name, create_sql in tables.items():
                if not table_exists(table_name):
                    print(f"Creating table '{table_name}'...")
                    cursor.execute(create_sql)
                    connection.commit()
                    print(f"Table '{table_name}' created successfully.")
                    
                    # Record migration
                    migration_name = f"create_table_{table_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    record_migration(migration_name, f"Created table: {table_name}")
                else:
                    print(f"Table '{table_name}' already exists. Verifying structure...")
                    # Verify table structure (check for key columns)
                    columns = get_table_columns(table_name)
                    print(f"Table '{table_name}' has {len(columns)} columns: {', '.join(columns)}")
            
            connection.commit()
            
            # Add missing columns to existing tables
            print("Checking for missing columns in existing tables...")
            add_missing_columns()
            
            print("All tables initialized and verified successfully.")
            return True
            
    except Exception as e:
        print(f"Error initializing tables: {e}")
        return False
    finally:
        connection.close()

def init_db():
    """Complete database initialization process."""
    print("=" * 50)
    print("Initializing MERU_DELIVERIES Database")
    print("=" * 50)
    
    # Step 1: Create database if it doesn't exist
    if not create_database():
        print("Failed to create database.")
        return False
    
    # Step 2: Update config to use the database
    DB_CONFIG['database'] = DATABASE_NAME
    
    # Step 3: Create migrations table first
    if not create_migrations_table():
        print("Failed to create migrations table.")
        return False
    
    # Step 4: Initialize all tables
    if not init_tables():
        print("Failed to initialize tables.")
        return False
    
    print("=" * 50)
    print("Database initialization completed successfully!")
    print("=" * 50)
    return True

# Helper Functions
def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file, subfolder):
    """Save uploaded file and return the path."""
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        folder_path = os.path.join(app.config['UPLOAD_FOLDER'], subfolder)
        os.makedirs(folder_path, exist_ok=True)
        filepath = os.path.join(folder_path, unique_filename)
        file.save(filepath)
        return f"{subfolder}/{unique_filename}"
    return None

def save_multiple_files(files, subfolder):
    """Save multiple uploaded files and return JSON array of paths."""
    saved_files = []
    if files:
        for file in files:
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4()}_{filename}"
                folder_path = os.path.join(app.config['UPLOAD_FOLDER'], subfolder)
                os.makedirs(folder_path, exist_ok=True)
                filepath = os.path.join(folder_path, unique_filename)
                file.save(filepath)
                saved_files.append(f"{subfolder}/{unique_filename}")
    return saved_files

def validate_password(password):
    """Validate password strength (medium to strong)."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one number (digit)"
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character"
    return True, "Password is valid"

def validate_phone(phone):
    """Validate phone number starts with 07 or 01."""
    phone = phone.strip()
    if phone.startswith('07') or phone.startswith('01'):
        if len(phone) == 10 and phone.isdigit():
            return True, phone
    return False, "Phone number must start with 07 or 01 and be 10 digits"

def send_shop_status_email(email, shop_name, status):
    """Send email to shop about status update (approved or rejected)."""
    try:
        if status == 'open':
            subject = f'🎉 Congratulations! Your Shop Has Been Approved - {COMPANY_NAME}'
            body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #004E89 0%, #1A6BA3 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
                    .success-icon {{ font-size: 48px; margin-bottom: 20px; }}
                    .button {{ display: inline-block; padding: 12px 30px; background: #004E89; color: white; text-decoration: none; border-radius: 5px; margin-top: 20px; }}
                    .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🎉 Congratulations!</h1>
                    </div>
                    <div class="content">
                        <div style="text-align: center;">
                            <div class="success-icon">✅</div>
                        </div>
                        <h2>Your Shop Has Been Approved!</h2>
                        <p>Dear <strong>{shop_name}</strong>,</p>
                        <p>We are delighted to inform you that your shop registration has been <strong>approved</strong> and your shop is now <strong>active</strong> on {COMPANY_NAME}!</p>
                        <p>You can now:</p>
                        <ul>
                            <li>Start receiving orders from customers</li>
                            <li>Manage your shop profile and products</li>
                            <li>Access your shop dashboard</li>
                            <li>Begin serving customers through our platform</li>
                        </ul>
                        <p>Welcome to the {COMPANY_NAME} family! We're excited to have you on board.</p>
                        <p>If you have any questions or need assistance, please don't hesitate to contact our support team.</p>
                        <div style="text-align: center;">
                            <a href="https://kwetudeliveries.com" class="button">Visit Your Dashboard</a>
                        </div>
                        <p>Best regards,<br><strong>The {COMPANY_NAME} Team</strong></p>
                    </div>
                    <div class="footer">
                        <p>This is an automated email. Please do not reply to this message.</p>
                        <p>For support, contact: {SUPPORT_EMAIL} or {SUPPORT_PHONE}</p>
                    </div>
                </div>
            </body>
            </html>
            """
        elif status == 'rejected':
            subject = f'Shop Registration Update - {COMPANY_NAME}'
            body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
                    .warning-icon {{ font-size: 48px; margin-bottom: 20px; }}
                    .button {{ display: inline-block; padding: 12px 30px; background: #dc2626; color: white; text-decoration: none; border-radius: 5px; margin-top: 20px; }}
                    .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Registration Update</h1>
                    </div>
                    <div class="content">
                        <div style="text-align: center;">
                            <div class="warning-icon">⚠️</div>
                        </div>
                        <h2>Shop Registration Status Update</h2>
                        <p>Dear <strong>{shop_name}</strong>,</p>
                        <p>We regret to inform you that your shop registration has been <strong>rejected</strong> at this time.</p>
                        <p>This decision may have been made due to:</p>
                        <ul>
                            <li>Incomplete or unclear documentation</li>
                            <li>Information that doesn't meet our requirements</li>
                            <li>Issues with the provided business documents</li>
                        </ul>
                        <p><strong>What you can do:</strong></p>
                        <ul>
                            <li>Review your submitted information and documents</li>
                            <li>Ensure all required documents are clear and valid</li>
                            <li>Contact our support team for more information</li>
                            <li>You may reapply with corrected information</li>
                        </ul>
                        <p>If you believe this is an error or have questions about this decision, please contact our support team. We're here to help.</p>
                        <div style="text-align: center;">
                            <a href="mailto:{SUPPORT_EMAIL}" class="button">Contact Support</a>
                        </div>
                        <p>Best regards,<br><strong>The {COMPANY_NAME} Team</strong></p>
                    </div>
                    <div class="footer">
                        <p>This is an automated email. Please do not reply to this message.</p>
                        <p>For support, contact: {SUPPORT_EMAIL} or {SUPPORT_PHONE}</p>
                    </div>
                </div>
            </body>
            </html>
            """
        else:
            return False
        
        msg = Message(
            subject=subject,
            recipients=[email],
            html=body
        )
        mail.send(msg)
        print(f"Status update email sent to {email} for shop {shop_name} with status {status}")
        return True
    except Exception as e:
        print(f"Error sending status update email: {e}")
        import traceback
        traceback.print_exc()
        return False

def send_approval_email(email, name, user_type):
    """Send approval waiting email."""
    try:
        msg = Message(
            subject=f'Account Registration - {COMPANY_NAME}',
            recipients=[email],
            html=f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <div style="background: linear-gradient(to right, #FF6B35, #004E89); padding: 20px; text-align: center; border-radius: 10px 10px 0 0;">
                        <h1 style="color: white; margin: 0;">{COMPANY_NAME}</h1>
                    </div>
                    <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
                        <h2 style="color: #004E89;">Thank You for Registering!</h2>
                        <p>Dear {name},</p>
                        <p>We have received your {user_type} account registration request. Your details are currently under review.</p>
                        <p>Please be patient as we verify your information. We will notify you once your account has been approved.</p>
                        <p>If you have any questions, please contact us at:</p>
                        <ul>
                            <li>Email: {SUPPORT_EMAIL}</li>
                            <li>Phone: {SUPPORT_PHONE}</li>
                        </ul>
                        <p>Thank you for choosing {COMPANY_NAME}!</p>
                        <p style="margin-top: 30px; color: #666; font-size: 12px;">
                            This is an automated message. Please do not reply to this email.
                        </p>
                    </div>
                </div>
            </body>
            </html>
            """
        )
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def check_code_availability(code, code_type):
    """Check if login code is available."""
    if not code or not code_type:
        print(f"Invalid parameters: code={code}, code_type={code_type}")
        return False
    
    connection = get_db_connection()
    if not connection:
        print("Failed to get database connection")
        return False
    
    try:
        with connection.cursor() as cursor:
            if code_type == 'employee':
                cursor.execute("SELECT COUNT(*) as count FROM employees WHERE login_code = %s", (code,))
            elif code_type == 'shop':
                cursor.execute("SELECT COUNT(*) as count FROM shops WHERE login_code = %s", (code,))
            else:
                print(f"Invalid code_type: {code_type}")
                return False
            
            result = cursor.fetchone()
            count = result['count'] if result else 0
            is_available = count == 0
            print(f"Code availability check: code={code}, type={code_type}, count={count}, available={is_available}")
            return is_available
    except Exception as e:
        print(f"Error checking code availability: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        connection.close()

# API Routes
@app.route('/api/check-code', methods=['POST'])
def check_code():
    """Check if login code is available."""
    try:
        data = request.json
        if not data:
            return jsonify({'available': False, 'message': 'Invalid request - no data'}), 400
        
        code = data.get('code', '').strip()
        code_type = data.get('type', '').strip().lower()  # 'employee' or 'shop'
        
        print(f"API check-code called: code={code}, type={code_type}")
        
        if not code:
            return jsonify({'available': False, 'message': 'Code is required'}), 400
        
        if code_type not in ['employee', 'shop']:
            return jsonify({'available': False, 'message': 'Invalid code type. Must be "employee" or "shop"'}), 400
        
        # Validate code length
        if code_type == 'employee' and len(code) != 4:
            return jsonify({'available': False, 'message': 'Employee code must be 4 digits'}), 400
        elif code_type == 'shop' and len(code) != 6:
            return jsonify({'available': False, 'message': 'Shop code must be 6 digits'}), 400
        
        # Validate code is numeric
        if not code.isdigit():
            return jsonify({'available': False, 'message': 'Code must contain only digits'}), 400
        
        available = check_code_availability(code, code_type)
        return jsonify({
            'available': available,
            'message': 'Code available' if available else 'Code already taken'
        })
    except Exception as e:
        print(f"Error in check_code API: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'available': False, 'message': f'Error checking code: {str(e)}'}), 500

@app.route('/api/login/employee', methods=['POST'])
def login_employee():
    """Handle employee login."""
    try:
        data = request.get_json()
        login_code = data.get('code', '').strip()
        password = data.get('password', '')
        
        if not login_code or not password:
            return jsonify({'success': False, 'message': 'Login code and password are required'}), 400
        
        # Validate login code format
        if len(login_code) != 4 or not login_code.isdigit():
            return jsonify({'success': False, 'message': 'Invalid login code format'}), 400
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection error'}), 500
        
        try:
            with connection.cursor() as cursor:
                # Get employee by login code
                cursor.execute("""
                    SELECT id, full_name, email, login_code, password, kwetu_employee_role, status
                    FROM employees
                    WHERE login_code = %s
                """, (login_code,))
                employee = cursor.fetchone()
                
                if not employee:
                    return jsonify({'success': False, 'message': 'Invalid login code or password'}), 401
                
                # Check password
                if not check_password_hash(employee['password'], password):
                    return jsonify({'success': False, 'message': 'Invalid login code or password'}), 401
                
                # Check if employee status is 'active'
                if employee['status'] != 'active':
                    status_messages = {
                        'waiting_approval': 'Your account is pending approval. Please wait for admin approval.',
                        'approved': 'Your account has been approved but is not yet active. Please contact admin.',
                        'rejected': 'Your account has been rejected. Please contact support.',
                        'suspended': 'Your account has been suspended. Please contact support.',
                        'banned': 'Your account has been banned. Please contact support.'
                    }
                    message = status_messages.get(employee['status'], 'Your account is not active. Please contact support.')
                    return jsonify({'success': False, 'message': message}), 403
                
                # Check if employee has been assigned a role (not just default KWETU_EMPLOYEE)
                # Actually, let's allow all roles including KWETU_EMPLOYEE since that's a valid role
                # The requirement says "have been assigned a role (not in waiting approval)" which we already checked
                role = employee['kwetu_employee_role']
                
                # Get profile picture if available
                cursor.execute("SELECT profile_picture FROM employees WHERE id = %s", (employee['id'],))
                profile_data = cursor.fetchone()
                profile_picture = profile_data['profile_picture'] if profile_data and profile_data.get('profile_picture') else None
                
                # Set session data
                session['employee_id'] = employee['id']
                session['employee_name'] = employee['full_name']
                session['employee_email'] = employee['email']
                session['employee_role'] = role
                session['login_code'] = employee['login_code']
                session['employee_profile_picture'] = profile_picture
                session['logged_in'] = True
                session['user_type'] = 'employee'
                
                # Determine redirect URL based on role
                role_routes = {
                    'KWETU_ADMIN': '/dashboard/admin',
                    'KWETU_MANAGER': '/dashboard/manager',
                    'KWETU_CASHIER': '/dashboard/cashier',
                    'KWETU_SALES': '/dashboard/sales',
                    'KWETU_RIDER': '/dashboard/rider',
                    'KWETU_CUSTOMERCARE': '/dashboard/customercare',
                    'KWETU_TECHNICIAN': '/dashboard/technician',
                    'KWETU_IT_SUPPORT': '/dashboard/it-support',
                    'KWETU_EMPLOYEE': '/dashboard/employee'
                }
                
                redirect_url = role_routes.get(role, '/dashboard/employee')
                
                return jsonify({
                    'success': True,
                    'message': 'Login successful!',
                    'redirect_url': redirect_url,
                    'role': role,
                    'employee_name': employee['full_name']
                })
        except Exception as e:
            print(f"Error in login_employee: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'message': 'Login failed. Please try again.'}), 500
        finally:
            connection.close()
            
    except Exception as e:
        print(f"Error in login_employee: {e}")
        return jsonify({'success': False, 'message': 'An error occurred'}), 500

@app.route('/api/login/shop', methods=['POST'])
def login_shop():
    """Handle shop login with validation and status check."""
    try:
        data = request.get_json()
        login_code = data.get('code', '').strip()
        password = data.get('password', '')
        
        # Validate inputs are provided
        if not login_code:
            return jsonify({'success': False, 'message': 'Login code is required'}), 400
        
        if not password:
            return jsonify({'success': False, 'message': 'Password is required'}), 400
        
        # Validate login code format (must be 6 digits)
        if len(login_code) != 6:
            return jsonify({'success': False, 'message': 'Login code must be exactly 6 digits'}), 400
        
        if not login_code.isdigit():
            return jsonify({'success': False, 'message': 'Login code must contain only numbers'}), 400
        
        # Validate password is not empty
        if len(password) < 1:
            return jsonify({'success': False, 'message': 'Password cannot be empty'}), 400
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection error'}), 500
        
        try:
            with connection.cursor() as cursor:
                # Get shop by login code
                cursor.execute("""
                    SELECT id, name, email, login_code, password, status
                    FROM shops
                    WHERE login_code = %s
                """, (login_code,))
                shop = cursor.fetchone()
                
                if not shop:
                    return jsonify({'success': False, 'message': 'Invalid login code or password'}), 401
                
                # Check password
                if not check_password_hash(shop['password'], password):
                    return jsonify({'success': False, 'message': 'Invalid login code or password'}), 401
                
                # Check if shop status allows login
                # Allow login for 'open' and 'closed' statuses
                # Block login for other statuses (waiting_approval, approved, rejected, suspended, banned)
                if shop['status'] not in ['open', 'closed']:
                    status_messages = {
                        'waiting_approval': 'Your shop account is pending approval. Please wait for admin approval before logging in.',
                        'approved': 'Your shop account has been approved but is not yet active. Please contact support.',
                        'rejected': 'Your shop registration has been rejected. Please contact support for more information.',
                        'suspended': 'Your shop account has been suspended. Please contact support.',
                        'banned': 'Your shop account has been banned. Please contact support.'
                    }
                    message = status_messages.get(shop['status'], f'Your shop account status is {shop["status"].replace("_", " ").title()}. Please contact support.')
                    return jsonify({
                        'success': False,
                        'message': message
                    }), 403
                
                # Set session
                session['logged_in'] = True
                session['user_type'] = 'shop'
                session['shop_id'] = shop['id']
                session['shop_name'] = shop['name']
                session['shop_email'] = shop['email']
                session['login_code'] = shop['login_code']
                
                return jsonify({
                    'success': True,
                    'message': 'Login successful!',
                    'redirect_url': '/dashboard/shop'
                })
        except Exception as e:
            print(f"Error during shop login: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'message': 'Login failed. Please try again.'}), 500
        finally:
            connection.close()
    except Exception as e:
        print(f"Error in login_shop: {e}")
        return jsonify({'success': False, 'message': 'An error occurred'}), 500

@app.route('/api/signup/employee', methods=['POST'])
def signup_employee():
    """Handle employee sign-up."""
    try:
        # Get form data
        full_name = request.form.get('full_name', '').strip().upper()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        login_code = request.form.get('login_code', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        # Check terms acceptance - handle both 'true' value and checkbox 'on' state
        terms_accepted = request.form.get('terms_accepted')
        terms_accepted = terms_accepted in ['true', 'on', True, '1', 'yes']
        
        # Validate required fields
        if not all([full_name, email, phone, login_code, password, confirm_password]):
            return jsonify({'success': False, 'message': 'All fields are required'}), 400
        
        # Validate phone
        phone_valid, phone_msg = validate_phone(phone)
        if not phone_valid:
            return jsonify({'success': False, 'message': phone_msg}), 400
        
        # Validate login code
        if len(login_code) != 4 or not login_code.isdigit():
            return jsonify({'success': False, 'message': 'Login code must be 4 digits'}), 400
        
        # Check code availability - final verification before saving
        print(f"Final code check before employee registration: code={login_code}")
        code_available = check_code_availability(login_code, 'employee')
        if not code_available:
            return jsonify({'success': False, 'message': 'Login code already taken. Please choose a different code.'}), 400
        
        # Validate password
        password_valid, password_msg = validate_password(password)
        if not password_valid:
            return jsonify({'success': False, 'message': password_msg}), 400
        
        # Check password match
        if password != confirm_password:
            return jsonify({'success': False, 'message': 'Passwords do not match'}), 400
        
        # Check terms acceptance
        if not terms_accepted:
            return jsonify({'success': False, 'message': 'You must accept the terms and conditions'}), 400
        
        # Handle file uploads
        profile_picture = None
        id_documents = []
        
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file.filename:
                profile_picture = save_uploaded_file(file, 'profiles')
                if not profile_picture:
                    return jsonify({'success': False, 'message': 'Invalid profile picture format'}), 400
        
        # Handle ID documents (front and back as separate inputs)
        id_document_front = None
        id_document_back = None
        
        if 'id_document_front' in request.files:
            file = request.files['id_document_front']
            if file.filename:
                id_document_front = save_uploaded_file(file, 'documents')
                if not id_document_front:
                    return jsonify({'success': False, 'message': 'Invalid ID document front image format'}), 400
        
        if 'id_document_back' in request.files:
            file = request.files['id_document_back']
            if file.filename:
                id_document_back = save_uploaded_file(file, 'documents')
                if not id_document_back:
                    return jsonify({'success': False, 'message': 'Invalid ID document back image format'}), 400
        
        if not profile_picture:
            return jsonify({'success': False, 'message': 'Profile picture is required'}), 400
        
        if not id_document_front or not id_document_back:
            return jsonify({'success': False, 'message': 'Both front and back images of ID document are required'}), 400
        
        # Convert to JSON array for database storage
        id_documents = [id_document_front, id_document_back]
        id_document_json = json.dumps(id_documents)
        
        # Save to database
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection error'}), 500
        
        try:
            with connection.cursor() as cursor:
                hashed_password = generate_password_hash(password)
                cursor.execute("""
                    INSERT INTO employees (full_name, email, phone, login_code, password, profile_picture, id_document, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'waiting_approval')
                """, (full_name, email, phone, login_code, hashed_password, profile_picture, id_document_json))
                connection.commit()
                
                # Send email
                send_approval_email(email, full_name, 'Employee')
                
                return jsonify({
                    'success': True,
                    'message': 'Registration successful! Please wait for approval. Check your email for confirmation.'
                })
        except pymysql.IntegrityError as e:
            if 'email' in str(e):
                return jsonify({'success': False, 'message': 'Email already registered'}), 400
            return jsonify({'success': False, 'message': 'Registration failed. Please try again.'}), 400
        except Exception as e:
            print(f"Error: {e}")
            return jsonify({'success': False, 'message': 'Registration failed. Please try again.'}), 500
        finally:
            connection.close()
            
    except Exception as e:
        print(f"Error in signup_employee: {e}")
        return jsonify({'success': False, 'message': 'An error occurred'}), 500

@app.route('/api/signup/shop', methods=['POST'])
def signup_shop():
    """Handle shop sign-up."""
    try:
        # Get form data
        shop_name = request.form.get('shop_name', '').strip().upper()
        category = request.form.get('category', '').strip().upper()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        login_code = request.form.get('login_code', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        location_name = request.form.get('location_name', '').strip()
        longitude = request.form.get('longitude', '').strip()
        latitude = request.form.get('latitude', '').strip()
        # Check terms acceptance - handle both 'true' value and checkbox 'on' state
        terms_accepted = request.form.get('terms_accepted')
        terms_accepted = terms_accepted in ['true', 'on', True, '1', 'yes']
        
        # Validate required fields
        if not all([shop_name, category, email, phone, login_code, password, confirm_password]):
            return jsonify({'success': False, 'message': 'All fields are required'}), 400
        
        # Validate phone
        phone_valid, phone_msg = validate_phone(phone)
        if not phone_valid:
            return jsonify({'success': False, 'message': phone_msg}), 400
        
        # Validate login code
        if len(login_code) != 6 or not login_code.isdigit():
            return jsonify({'success': False, 'message': 'Login code must be 6 digits'}), 400
        
        # Check code availability - final verification before saving
        print(f"Final code check before shop registration: code={login_code}")
        code_available = check_code_availability(login_code, 'shop')
        if not code_available:
            return jsonify({'success': False, 'message': 'Login code already taken. Please choose a different code.'}), 400
        
        # Validate password
        password_valid, password_msg = validate_password(password)
        if not password_valid:
            return jsonify({'success': False, 'message': password_msg}), 400
        
        # Check password match
        if password != confirm_password:
            return jsonify({'success': False, 'message': 'Passwords do not match'}), 400
        
        # Validate location
        if not location_name:
            return jsonify({'success': False, 'message': 'Location name is required'}), 400
        
        if not longitude or not latitude:
            return jsonify({'success': False, 'message': 'Location coordinates are required'}), 400
        
        try:
            longitude = float(longitude)
            latitude = float(latitude)
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid location coordinates'}), 400
        
        # Check terms acceptance
        if not terms_accepted:
            return jsonify({'success': False, 'message': 'You must accept the terms and conditions'}), 400
        
        # Handle file uploads
        profile_image = None
        business_document = None
        
        if 'profile_image' in request.files:
            file = request.files['profile_image']
            if file.filename:
                profile_image = save_uploaded_file(file, 'profiles')
                if not profile_image:
                    return jsonify({'success': False, 'message': 'Invalid profile image format'}), 400
        
        if 'business_document' in request.files:
            file = request.files['business_document']
            if file.filename:
                business_document = save_uploaded_file(file, 'documents')
                if not business_document:
                    return jsonify({'success': False, 'message': 'Invalid document format'}), 400
        
        if not profile_image or not business_document:
            return jsonify({'success': False, 'message': 'Profile image and business document are required'}), 400
        
        # Save to database
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection error'}), 500
        
        try:
            with connection.cursor() as cursor:
                hashed_password = generate_password_hash(password)
                cursor.execute("""
                    INSERT INTO shops (name, category, email, phone, login_code, password, profile_image, business_document, 
                                    location_name, longitude, latitude, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'waiting_approval')
                """, (shop_name, category, email, phone, login_code, hashed_password, profile_image, business_document,
                      location_name, longitude, latitude))
                connection.commit()
                
                # Send email
                send_approval_email(email, shop_name, 'Shop')
                
                return jsonify({
                    'success': True,
                    'message': 'Registration successful! Please wait for approval. Check your email for confirmation.'
                })
        except pymysql.IntegrityError as e:
            if 'email' in str(e):
                return jsonify({'success': False, 'message': 'Email already registered'}), 400
            return jsonify({'success': False, 'message': 'Registration failed. Please try again.'}), 400
        except Exception as e:
            print(f"Error: {e}")
            return jsonify({'success': False, 'message': 'Registration failed. Please try again.'}), 500
        finally:
            connection.close()
            
    except Exception as e:
        print(f"Error in signup_shop: {e}")
        return jsonify({'success': False, 'message': 'An error occurred'}), 500

@app.route('/api/logout', methods=['POST', 'GET'])
def logout():
    """Handle user logout."""
    session.clear()
    return redirect('/')

@app.route('/dashboard/admin/shop-management')
def admin_shop_management():
    """Admin shop management page - fetches all shop details."""
    # Check if employee is logged in (not shop session)
    if not session.get('logged_in') or session.get('user_type') != 'employee':
        # Redirect to login if not logged in
        return redirect('/')
    
    # Verify user is admin employee
    if session.get('employee_role') != 'KWETU_ADMIN':
        # Redirect to their role dashboard if not admin
        role_url_map = {
            'KWETU_ADMIN': 'admin',
            'KWETU_MANAGER': 'manager',
            'KWETU_CASHIER': 'cashier',
            'KWETU_SALES': 'sales',
            'KWETU_RIDER': 'rider',
            'KWETU_CUSTOMERCARE': 'customercare',
            'KWETU_TECHNICIAN': 'technician',
            'KWETU_IT_SUPPORT': 'it-support',
            'KWETU_EMPLOYEE': 'employee'
        }
        user_role = session.get('employee_role', 'KWETU_EMPLOYEE')
        correct_url = role_url_map.get(user_role, 'employee')
        return redirect(url_for('dashboard', role=correct_url))
    
    # Fetch all shops from database (no shop session needed - just fetch shop data)
    connection = get_db_connection()
    shops = []
    error = None
    
    if connection:
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, name, category, email, phone, login_code, profile_image, 
                           business_document, location_name, status, rating, delivery_mode, created_at, updated_at
                    FROM shops
                    ORDER BY created_at DESC
                """)
                shops = cursor.fetchall()
        except Exception as e:
            print(f"Error fetching shops: {e}")
            error = 'Error loading shops'
        finally:
            connection.close()
    else:
        error = 'Database connection error'
    
    return render_template('shop_management.html', shops=shops, error=error)

@app.route('/dashboard/admin/settings')
def admin_settings():
    """Admin settings page with links to different settings sections."""
    # Check if employee is logged in
    if not session.get('logged_in') or session.get('user_type') != 'employee':
        return redirect('/')
    
    # Verify user is admin employee
    if session.get('employee_role') != 'KWETU_ADMIN':
        # Redirect to their role dashboard if not admin
        role_url_map = {
            'KWETU_ADMIN': 'admin',
            'KWETU_MANAGER': 'manager',
            'KWETU_CASHIER': 'cashier',
            'KWETU_SALES': 'sales',
            'KWETU_RIDER': 'rider',
            'KWETU_CUSTOMERCARE': 'customercare',
            'KWETU_TECHNICIAN': 'technician',
            'KWETU_IT_SUPPORT': 'it-support',
            'KWETU_EMPLOYEE': 'employee'
        }
        user_role = session.get('employee_role', 'KWETU_EMPLOYEE')
        correct_url = role_url_map.get(user_role, 'employee')
        return redirect(url_for('dashboard', role=correct_url))
    
    return render_template('admin_settings.html', is_settings_page=True)

@app.route('/dashboard/admin/shop/<int:shop_id>')
def view_shop(shop_id):
    """View shop details page."""
    if not session.get('logged_in') or session.get('user_type') != 'employee':
        return redirect('/')
    
    if session.get('employee_role') != 'KWETU_ADMIN':
        return redirect('/')
    
    connection = get_db_connection()
    shop = None
    error = None
    
    if connection:
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, name, category, email, phone, login_code, profile_image, 
                           business_document, location_name, longitude, latitude, 
                           status, rating, created_at, updated_at
                    FROM shops
                    WHERE id = %s
                """, (shop_id,))
                shop = cursor.fetchone()
                
                if not shop:
                    error = 'Shop not found'
        except Exception as e:
            print(f"Error fetching shop: {e}")
            error = 'Error loading shop details'
        finally:
            connection.close()
    else:
        error = 'Database connection error'
    
    return render_template('view_shop.html', shop=shop, error=error)

@app.route('/api/admin/shop/<int:shop_id>')
def get_shop_details(shop_id):
    """Get shop details for editing."""
    if not session.get('logged_in') or session.get('user_type') != 'employee':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    if session.get('employee_role') != 'KWETU_ADMIN':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, name, category, email, phone, login_code, profile_image, 
                       business_document, location_name, longitude, latitude, 
                       status, rating, delivery_mode, created_at, updated_at
                FROM shops
                WHERE id = %s
            """, (shop_id,))
            shop = cursor.fetchone()
            
            if not shop:
                return jsonify({'success': False, 'message': 'Shop not found'}), 404
            
            # Convert datetime objects to strings
            shop_data = dict(shop)
            if shop_data.get('created_at'):
                shop_data['created_at'] = shop_data['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            if shop_data.get('updated_at'):
                shop_data['updated_at'] = shop_data['updated_at'].strftime('%Y-%m-%d %H:%M:%S')
            
            return jsonify({'success': True, 'shop': shop_data})
    except Exception as e:
        print(f"Error fetching shop details: {e}")
        return jsonify({'success': False, 'message': 'Error loading shop details'}), 500
    finally:
        connection.close()

@app.route('/api/admin/shop/<int:shop_id>/update', methods=['POST'])
def update_shop(shop_id):
    """Update shop details."""
    if not session.get('logged_in') or session.get('user_type') != 'employee':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    if session.get('employee_role') != 'KWETU_ADMIN':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        name = data.get('name', '').strip().upper()
        category = data.get('category', '').strip().upper()
        email = data.get('email', '').strip().lower()
        phone = data.get('phone', '').strip()
        location_name = data.get('location_name', '').strip()
        status = data.get('status', '').strip()
        
        # Validate required fields
        if not all([name, category, email, phone]):
            return jsonify({'success': False, 'message': 'Name, category, email, and phone are required'}), 400
        
        # Validate phone
        phone_valid, phone_msg = validate_phone(phone)
        if not phone_valid:
            return jsonify({'success': False, 'message': phone_msg}), 400
        
        # Validate status
        valid_statuses = ['waiting_approval', 'approved', 'rejected', 'open', 'suspended', 'banned', 'closed']
        if status and status not in valid_statuses:
            return jsonify({'success': False, 'message': 'Invalid status'}), 400
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection error'}), 500
        
        try:
            with connection.cursor() as cursor:
                # Check if email is being changed and if it's already taken
                cursor.execute("SELECT email FROM shops WHERE id = %s", (shop_id,))
                current_shop = cursor.fetchone()
                if not current_shop:
                    return jsonify({'success': False, 'message': 'Shop not found'}), 404
                
                if email != current_shop['email']:
                    cursor.execute("SELECT id FROM shops WHERE email = %s AND id != %s", (email, shop_id))
                    if cursor.fetchone():
                        return jsonify({'success': False, 'message': 'Email already registered'}), 400
                
                # Build update query
                updates = []
                values = []
                
                updates.append("name = %s")
                values.append(name)
                updates.append("category = %s")
                values.append(category)
                updates.append("email = %s")
                values.append(email)
                updates.append("phone = %s")
                values.append(phone)
                
                if location_name:
                    updates.append("location_name = %s")
                    values.append(location_name)
                
                if status:
                    updates.append("status = %s")
                    values.append(status)
                
                values.append(shop_id)
                
                update_query = f"""
                    UPDATE shops 
                    SET {', '.join(updates)}
                    WHERE id = %s
                """
                
                cursor.execute(update_query, values)
                connection.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Shop updated successfully!'
                })
        except pymysql.IntegrityError as e:
            if 'email' in str(e):
                return jsonify({'success': False, 'message': 'Email already registered'}), 400
            return jsonify({'success': False, 'message': 'Update failed. Please try again.'}), 400
        except Exception as e:
            print(f"Error updating shop: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'message': 'Update failed. Please try again.'}), 500
        finally:
            connection.close()
            
    except Exception as e:
        print(f"Error in update_shop: {e}")
        return jsonify({'success': False, 'message': 'An error occurred'}), 500

@app.route('/api/admin/shop/<int:shop_id>/update-status', methods=['POST'])
def update_shop_status(shop_id):
    """Update shop status only."""
    if not session.get('logged_in') or session.get('user_type') != 'employee':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    if session.get('employee_role') != 'KWETU_ADMIN':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        status = data.get('status', '').strip()
        
        # Validate status
        valid_statuses = ['waiting_approval', 'approved', 'rejected', 'open', 'suspended', 'banned', 'closed']
        if not status or status not in valid_statuses:
            return jsonify({'success': False, 'message': 'Invalid status'}), 400
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection error'}), 500
        
        try:
            with connection.cursor() as cursor:
                # Check if shop exists and get shop details
                cursor.execute("SELECT id, name, email FROM shops WHERE id = %s", (shop_id,))
                shop = cursor.fetchone()
                if not shop:
                    return jsonify({'success': False, 'message': 'Shop not found'}), 404
                
                # Get current status to check if it's changing
                cursor.execute("SELECT status FROM shops WHERE id = %s", (shop_id,))
                current_shop = cursor.fetchone()
                old_status = current_shop['status'] if current_shop else None
                
                # Update status
                cursor.execute("UPDATE shops SET status = %s WHERE id = %s", (status, shop_id))
                connection.commit()
                
                # Send email notification if status changed to 'open' (approved) or 'rejected'
                if old_status != status and status in ['open', 'rejected']:
                    try:
                        send_shop_status_email(shop['email'], shop['name'], status)
                    except Exception as email_error:
                        print(f"Error sending status email: {email_error}")
                        # Don't fail the request if email fails
                
                status_display = 'Active (Approved)' if status == 'open' else 'Rejected'
                return jsonify({
                    'success': True,
                    'message': f'Shop status updated to {status_display} successfully! Email notification sent.'
                })
        except Exception as e:
            print(f"Error updating shop status: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'message': 'Failed to update status'}), 500
        finally:
            connection.close()
            
    except Exception as e:
        print(f"Error in update_shop_status: {e}")
        return jsonify({'success': False, 'message': 'An error occurred'}), 500

@app.route('/api/admin/payment/shops', methods=['GET'])
def get_payment_shops():
    """Get all shops whose status is not 'waiting_approval' for payment settings."""
    if not session.get('logged_in') or session.get('user_type') != 'employee':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    if session.get('employee_role') != 'KWETU_ADMIN':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, name, category, email, phone, status, rating, 
                       location_name, created_at, profile_image,
                       COALESCE(payments_to_shop, 0) as payments_to_shop,
                       payment_method, mpesa_type, mpesa_paybill_business_number,
                       mpesa_paybill_account, mpesa_buy_goods_till, bank_merchant_account
                FROM shops
                WHERE status != 'waiting_approval'
                ORDER BY 
                    CASE status
                        WHEN 'open' THEN 1
                        WHEN 'closed' THEN 2
                        WHEN 'approved' THEN 3
                        WHEN 'rejected' THEN 4
                        WHEN 'suspended' THEN 5
                        WHEN 'banned' THEN 6
                        ELSE 7
                    END,
                    name ASC
            """)
            shops = cursor.fetchall()
            
            # Convert to list of dicts
            shops_list = []
            for shop in shops:
                shop_dict = dict(shop)
                # Format created_at if it exists
                if shop_dict.get('created_at'):
                    if isinstance(shop_dict['created_at'], datetime):
                        shop_dict['created_at'] = shop_dict['created_at'].strftime('%Y-%m-%d %H:%M:%S')
                shops_list.append(shop_dict)
            
            return jsonify({
                'success': True,
                'shops': shops_list,
                'count': len(shops_list)
            })
    except Exception as e:
        print(f"Error fetching payment shops: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Error fetching shops'}), 500
    finally:
        connection.close()

@app.route('/api/admin/payment/settings', methods=['GET'])
def get_payment_settings():
    """Get payment settings."""
    if not session.get('logged_in') or session.get('user_type') != 'employee':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    if session.get('employee_role') != 'KWETU_ADMIN':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT payments_to_shops FROM payment_settings ORDER BY id DESC LIMIT 1")
            settings = cursor.fetchone()
            
            return jsonify({
                'success': True,
                'settings': {
                    'payments_to_shops': settings['payments_to_shops'] if settings else False
                }
            })
    except Exception as e:
        print(f"Error fetching payment settings: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Error fetching settings'}), 500
    finally:
        connection.close()

@app.route('/api/admin/payment/settings', methods=['POST'])
def update_payment_settings():
    """Update payment settings."""
    if not session.get('logged_in') or session.get('user_type') != 'employee':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    if session.get('employee_role') != 'KWETU_ADMIN':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    data = request.get_json()
    payments_to_shops = bool(data.get('payments_to_shops', False))
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    
    try:
        with connection.cursor() as cursor:
            # Check if settings exist
            cursor.execute("SELECT id FROM payment_settings ORDER BY id DESC LIMIT 1")
            existing = cursor.fetchone()
            
            if existing:
                cursor.execute("""
                    UPDATE payment_settings 
                    SET payments_to_shops = %s
                    WHERE id = %s
                """, (payments_to_shops, existing['id']))
            else:
                cursor.execute("""
                    INSERT INTO payment_settings (payments_to_shops)
                    VALUES (%s)
                """, (payments_to_shops,))
            
            connection.commit()
            return jsonify({'success': True, 'message': 'Payment settings updated successfully'})
    except Exception as e:
        connection.rollback()
        print(f"Error updating payment settings: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Error updating settings'}), 500
    finally:
        connection.close()

@app.route('/api/admin/payment/company-accounts', methods=['GET'])
def get_company_payment_accounts():
    """Get company payment accounts."""
    if not session.get('logged_in') or session.get('user_type') != 'employee':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    if session.get('employee_role') != 'KWETU_ADMIN':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT allow_cash_on_delivery, allow_mpesa, allow_bank_card, mpesa_type,
                       mpesa_paybill_business_number, mpesa_paybill_account, 
                       mpesa_buy_goods_till, bank_merchant_account
                FROM company_payment_accounts
                ORDER BY id DESC LIMIT 1
            """)
            settings = cursor.fetchone()
            
            return jsonify({
                'success': True,
                'settings': settings or {
                    'allow_cash_on_delivery': True,
                    'allow_mpesa': True,
                    'allow_bank_card': False,
                    'mpesa_type': 'paybill',
                    'mpesa_paybill_business_number': '',
                    'mpesa_paybill_account': '',
                    'mpesa_buy_goods_till': '',
                    'bank_merchant_account': ''
                }
            })
    except Exception as e:
        print(f"Error fetching company payment accounts: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Error fetching settings'}), 500
    finally:
        connection.close()

@app.route('/api/admin/payment/company-accounts', methods=['POST'])
def save_company_payment_accounts():
    """Save company payment accounts."""
    if not session.get('logged_in') or session.get('user_type') != 'employee':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    if session.get('employee_role') != 'KWETU_ADMIN':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    data = request.get_json()
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM company_payment_accounts ORDER BY id DESC LIMIT 1")
            existing = cursor.fetchone()
            
            if existing:
                cursor.execute("""
                    UPDATE company_payment_accounts 
                    SET allow_cash_on_delivery = %s, allow_mpesa = %s, allow_bank_card = %s,
                        mpesa_type = %s, mpesa_paybill_business_number = %s, 
                        mpesa_paybill_account = %s, mpesa_buy_goods_till = %s,
                        bank_merchant_account = %s
                    WHERE id = %s
                """, (
                    data.get('allow_cash_on_delivery', True),
                    data.get('allow_mpesa', True),
                    data.get('allow_bank_card', False),
                    data.get('mpesa_type', 'paybill'),
                    data.get('mpesa_paybill_business_number', ''),
                    data.get('mpesa_paybill_account', ''),
                    data.get('mpesa_buy_goods_till', ''),
                    data.get('bank_merchant_account', ''),
                    existing['id']
                ))
            else:
                cursor.execute("""
                    INSERT INTO company_payment_accounts 
                    (allow_cash_on_delivery, allow_mpesa, allow_bank_card, mpesa_type,
                     mpesa_paybill_business_number, mpesa_paybill_account, 
                     mpesa_buy_goods_till, bank_merchant_account)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    data.get('allow_cash_on_delivery', True),
                    data.get('allow_mpesa', True),
                    data.get('allow_bank_card', False),
                    data.get('mpesa_type', 'paybill'),
                    data.get('mpesa_paybill_business_number', ''),
                    data.get('mpesa_paybill_account', ''),
                    data.get('mpesa_buy_goods_till', ''),
                    data.get('bank_merchant_account', '')
                ))
            
            connection.commit()
            return jsonify({'success': True, 'message': 'Company payment settings saved successfully'})
    except Exception as e:
        connection.rollback()
        print(f"Error saving company payment accounts: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Error saving settings'}), 500
    finally:
        connection.close()

@app.route('/api/shop/payment-methods', methods=['GET'])
def get_shop_payment_methods():
    """Get allowed payment methods for the logged-in shop."""
    if not session.get('logged_in') or session.get('user_type') != 'shop':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    shop_id = session.get('shop_id')
    if not shop_id:
        return jsonify({'success': False, 'message': 'Shop not found in session'}), 404
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    
    try:
        with connection.cursor() as cursor:
            # Get shop payment settings
            cursor.execute("""
                SELECT payments_to_shop, payment_method, mpesa_type,
                       mpesa_paybill_business_number, mpesa_paybill_account, 
                       mpesa_buy_goods_till, bank_merchant_account
                FROM shops
                WHERE id = %s
            """, (shop_id,))
            shop = cursor.fetchone()
            
            if not shop:
                return jsonify({'success': False, 'message': 'Shop not found'}), 404
            
            payments_to_shop = bool(shop.get('payments_to_shop', 0))
            
            if payments_to_shop:
                # Use shop's payment methods
                payment_method = shop.get('payment_method', 'cash') or 'cash'
                allow_cash = 'cash' in payment_method or payment_method == 'all'
                allow_mpesa = 'mpesa' in payment_method or payment_method == 'all'
                allow_bank = 'bank' in payment_method or payment_method == 'all'
                
                return jsonify({
                    'success': True,
                    'payment_destination': 'shop',
                    'payment_methods': {
                        'cash_on_delivery': allow_cash,
                        'mpesa': allow_mpesa,
                        'bank_card': allow_bank
                    },
                    'mpesa_settings': {
                        'type': shop.get('mpesa_type', 'paybill') or 'paybill',
                        'paybill_business_number': shop.get('mpesa_paybill_business_number', '') or '',
                        'paybill_account': shop.get('mpesa_paybill_account', '') or '',
                        'buy_goods_till': shop.get('mpesa_buy_goods_till', '') or ''
                    },
                    'bank_settings': {
                        'merchant_account': shop.get('bank_merchant_account', '') or ''
                    }
                })
            else:
                # Use company payment methods
                cursor.execute("""
                    SELECT allow_cash_on_delivery, allow_mpesa, allow_bank_card, mpesa_type,
                           mpesa_paybill_business_number, mpesa_paybill_account, 
                           mpesa_buy_goods_till, bank_merchant_account
                    FROM company_payment_accounts
                    ORDER BY id DESC LIMIT 1
                """)
                company = cursor.fetchone()
                
                if not company:
                    # Default company settings
                    return jsonify({
                        'success': True,
                        'payment_destination': 'company',
                        'payment_methods': {
                            'cash_on_delivery': True,
                            'mpesa': True,
                            'bank_card': False
                        },
                        'mpesa_settings': {
                            'type': 'paybill',
                            'paybill_business_number': '',
                            'paybill_account': '',
                            'buy_goods_till': ''
                        },
                        'bank_settings': {
                            'merchant_account': ''
                        }
                    })
                
                return jsonify({
                    'success': True,
                    'payment_destination': 'company',
                    'payment_methods': {
                        'cash_on_delivery': bool(company.get('allow_cash_on_delivery', 1)),
                        'mpesa': bool(company.get('allow_mpesa', 1)),
                        'bank_card': bool(company.get('allow_bank_card', 0))
                    },
                    'mpesa_settings': {
                        'type': company.get('mpesa_type', 'paybill') or 'paybill',
                        'paybill_business_number': company.get('mpesa_paybill_business_number', '') or '',
                        'paybill_account': company.get('mpesa_paybill_account', '') or '',
                        'buy_goods_till': company.get('mpesa_buy_goods_till', '') or ''
                    },
                    'bank_settings': {
                        'merchant_account': company.get('bank_merchant_account', '') or ''
                    }
                })
    except Exception as e:
        print(f"Error fetching shop payment methods: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Error fetching payment methods'}), 500
    finally:
        connection.close()

@app.route('/api/admin/payment/shop-accounts/<int:shop_id>', methods=['GET'])
def get_shop_payment_accounts(shop_id):
    """Get shop payment accounts from shops table."""
    # Debug session info
    print(f"Session check - logged_in: {session.get('logged_in')}, user_type: {session.get('user_type')}, employee_role: {session.get('employee_role')}")
    
    if not session.get('logged_in') or session.get('user_type') != 'employee':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    if session.get('employee_role') != 'KWETU_ADMIN':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT payments_to_shop, payment_method, mpesa_type,
                       mpesa_paybill_business_number, mpesa_paybill_account, 
                       mpesa_buy_goods_till, bank_merchant_account
                FROM shops
                WHERE id = %s
            """, (shop_id,))
            shop = cursor.fetchone()
            
            if not shop:
                return jsonify({'success': False, 'message': 'Shop not found'}), 404
            
            # Convert payment_method to individual flags for UI
            payment_method = shop.get('payment_method', 'cash') or 'cash'
            allow_cash = 'cash' in payment_method or payment_method == 'all'
            allow_mpesa = 'mpesa' in payment_method or payment_method == 'all'
            allow_bank = 'bank' in payment_method or payment_method == 'all'
            
            return jsonify({
                'success': True,
                'settings': {
                    'payments_to_shop': bool(shop.get('payments_to_shop', 0)),
                    'payment_method': payment_method,
                    'allow_cash_on_delivery': allow_cash,
                    'allow_mpesa': allow_mpesa,
                    'allow_bank_card': allow_bank,
                    'mpesa_type': shop.get('mpesa_type', 'paybill') or 'paybill',
                    'mpesa_paybill_business_number': shop.get('mpesa_paybill_business_number', '') or '',
                    'mpesa_paybill_account': shop.get('mpesa_paybill_account', '') or '',
                    'mpesa_buy_goods_till': shop.get('mpesa_buy_goods_till', '') or '',
                    'bank_merchant_account': shop.get('bank_merchant_account', '') or ''
                }
            })
    except Exception as e:
        print(f"Error fetching shop payment accounts: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Error fetching settings'}), 500
    finally:
        connection.close()

@app.route('/api/admin/payment/shop-accounts/<int:shop_id>', methods=['POST'])
def save_shop_payment_accounts(shop_id):
    """Save shop payment accounts to shops table."""
    if not session.get('logged_in') or session.get('user_type') != 'employee':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    if session.get('employee_role') != 'KWETU_ADMIN':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    data = request.get_json()
    print(f"=== SAVE SHOP PAYMENT ACCOUNTS ===")
    print(f"Shop ID: {shop_id}")
    print(f"Request data: {data}")
    print(f"Data type: {type(data)}")
    print(f"Data keys: {list(data.keys()) if data else 'None'}")
    
    if not data:
        print("ERROR: No data received in request")
        return jsonify({'success': False, 'message': 'No data provided'}), 400
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    
    try:
        with connection.cursor() as cursor:
            # Check if shop exists
            cursor.execute("SELECT id FROM shops WHERE id = %s", (shop_id,))
            if not cursor.fetchone():
                return jsonify({'success': False, 'message': 'Shop not found'}), 404
            
            # Convert payments_to_shop to proper boolean
            payments_to_shop_value = data.get('payments_to_shop', False)
            if isinstance(payments_to_shop_value, str):
                payments_to_shop = payments_to_shop_value.lower() in ('true', '1', 'yes')
            else:
                payments_to_shop = bool(payments_to_shop_value)
            
            # Check if this is a quick toggle (only payments_to_shop in request)
            # Get all keys in the request
            all_keys = list(data.keys())
            payments_to_shop_key_present = 'payments_to_shop' in all_keys
            
            # Filter out payments_to_shop and check if other keys have meaningful values
            # A key has a meaningful value if it's not None, empty string, False, empty list, or empty dict
            other_keys_with_values = []
            for k in all_keys:
                if k != 'payments_to_shop':
                    value = data.get(k)
                    # Check if value is meaningful (not None, '', False, [], {})
                    if value not in (None, '', False, [], {}):
                        other_keys_with_values.append(k)
            
            print(f"Shop {shop_id} toggle update - payments_to_shop: {payments_to_shop}")
            print(f"All keys in request: {all_keys}")
            print(f"Other keys with meaningful values: {other_keys_with_values}")
            print(f"Has payments_to_shop key: {payments_to_shop_key_present}")
            
            # If only payments_to_shop is in the request (or other keys don't have meaningful values), do quick toggle
            is_quick_toggle = payments_to_shop_key_present and len(other_keys_with_values) == 0
            
            if is_quick_toggle:
                # Quick toggle - only update payments_to_shop
                print(f"✓ Quick toggle detected for shop {shop_id}: setting payments_to_shop = {payments_to_shop}")
                try:
                    cursor.execute("""
                        UPDATE shops 
                        SET payments_to_shop = %s
                        WHERE id = %s
                    """, (1 if payments_to_shop else 0, shop_id))
                    rows_affected = cursor.rowcount
                    print(f"✓ SQL executed, rows affected: {rows_affected}")
                    
                    if rows_affected == 0:
                        print(f"⚠ WARNING: No rows updated! Shop {shop_id} may not exist.")
                        return jsonify({'success': False, 'message': f'Shop {shop_id} not found or no changes made'}), 404
                    
                    connection.commit()
                    print(f"✓ Successfully updated shop {shop_id} payments_to_shop to {payments_to_shop}")
                    print(f"✓ Database commit successful")
                    
                    # Verify the update
                    cursor.execute("SELECT payments_to_shop FROM shops WHERE id = %s", (shop_id,))
                    verify_result = cursor.fetchone()
                    if verify_result:
                        print(f"✓ Verification: payments_to_shop in DB = {verify_result['payments_to_shop']}")
                    
                    return jsonify({'success': True, 'message': 'Shop payment destination updated successfully'})
                except Exception as e:
                    connection.rollback()
                    print(f"✗ ERROR in quick toggle update: {e}")
                    import traceback
                    traceback.print_exc()
                    return jsonify({'success': False, 'message': f'Database error: {str(e)}'}), 500
            else:
                print(f"⚠ Not a quick toggle - proceeding with full update")
                print(f"  payments_to_shop_key_present: {payments_to_shop_key_present}")
                print(f"  other_keys_with_values: {other_keys_with_values}")
            
            # Full update - determine payment_method from individual toggles
            allow_cash = data.get('allow_cash_on_delivery', True)
            allow_mpesa = data.get('allow_mpesa', True)
            allow_bank = data.get('allow_bank_card', False)
            
            payment_methods = []
            if allow_cash:
                payment_methods.append('cash')
            if allow_mpesa:
                payment_methods.append('mpesa')
            if allow_bank:
                payment_methods.append('bank')
            
            if len(payment_methods) == 3:
                payment_method = 'all'
            elif len(payment_methods) == 2:
                payment_method = '_'.join(payment_methods)
            elif len(payment_methods) == 1:
                payment_method = payment_methods[0]
            else:
                payment_method = 'cash'  # Default to cash if nothing selected
            
            # Full update - update all payment fields
            cursor.execute("""
                UPDATE shops 
                SET payments_to_shop = %s, payment_method = %s, mpesa_type = %s,
                    mpesa_paybill_business_number = %s, mpesa_paybill_account = %s,
                    mpesa_buy_goods_till = %s, bank_merchant_account = %s
                WHERE id = %s
            """, (
                1 if payments_to_shop else 0,
                payment_method,
                data.get('mpesa_type', 'paybill'),
                data.get('mpesa_paybill_business_number', '') if allow_mpesa else '',
                data.get('mpesa_paybill_account', '') if allow_mpesa else '',
                data.get('mpesa_buy_goods_till', '') if allow_mpesa else '',
                data.get('bank_merchant_account', '') if allow_bank else '',
                shop_id
            ))
            
            connection.commit()
            return jsonify({'success': True, 'message': 'Shop payment settings saved successfully'})
    except Exception as e:
        connection.rollback()
        print(f"Error saving shop payment accounts: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Error saving settings'}), 500
    finally:
        connection.close()

@app.route('/api/admin/shop/<int:shop_id>/toggle-delivery', methods=['POST'])
def toggle_shop_delivery(shop_id):
    """Toggle shop delivery mode (items vs delivery only)."""
    if not session.get('logged_in') or session.get('user_type') != 'employee':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    if session.get('employee_role') != 'KWETU_ADMIN':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    
    try:
        with connection.cursor() as cursor:
            # Check if shop exists and get current delivery_mode
            cursor.execute("SELECT id, status, delivery_mode FROM shops WHERE id = %s", (shop_id,))
            shop = cursor.fetchone()
            
            if not shop:
                return jsonify({'success': False, 'message': 'Shop not found'}), 404
            
            # Toggle delivery mode (0 = items_with_delivery, 1 = delivery_only)
            current_mode = shop.get('delivery_mode', 0)
            new_mode = 1 if current_mode == 0 else 0
            
            # Update the delivery mode
            cursor.execute("UPDATE shops SET delivery_mode = %s WHERE id = %s", (new_mode, shop_id))
            connection.commit()
            
            mode_label = 'Delivery Only' if new_mode == 1 else 'Items with Delivery'
            return jsonify({
                'success': True,
                'message': f'Delivery mode updated to {mode_label}',
                'delivery_mode': new_mode
            })
    except Exception as e:
        print(f"Error toggling shop delivery: {e}")
        return jsonify({'success': False, 'message': 'Error toggling delivery mode'}), 500
    finally:
        connection.close()

@app.route('/api/shop/search-customers', methods=['GET'])
def search_customers():
    """Search customers by name or phone number."""
    if not session.get('logged_in') or session.get('user_type') != 'shop':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    search_query = request.args.get('q', '').strip()
    if not search_query or len(search_query) < 2:
        return jsonify({'success': True, 'customers': []})
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    
    try:
        with connection.cursor() as cursor:
            # Search by name or phone (case-insensitive, partial match)
            cursor.execute("""
                SELECT id, name, phone, email
                FROM customers
                WHERE name LIKE %s OR phone LIKE %s
                ORDER BY 
                    CASE 
                        WHEN name LIKE %s THEN 1
                        WHEN phone LIKE %s THEN 2
                        ELSE 3
                    END,
                    name ASC
                LIMIT 10
            """, (
                f'%{search_query}%',
                f'%{search_query}%',
                f'{search_query}%',  # Exact start match gets priority
                f'{search_query}%'
            ))
            
            customers = cursor.fetchall()
            
            # Convert to list of dicts
            customers_list = []
            for customer in customers:
                customers_list.append({
                    'id': customer['id'],
                    'name': customer['name'],
                    'phone': customer['phone'],
                    'email': customer.get('email', '')
                })
            
            return jsonify({
                'success': True,
                'customers': customers_list
            })
    except Exception as e:
        print(f"Error searching customers: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Error searching customers'}), 500
    finally:
        connection.close()

@app.route('/api/shop/package-delivery', methods=['POST'])
def create_package_delivery():
    """Create a package delivery order."""
    if not session.get('logged_in') or session.get('user_type') != 'shop':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    shop_id = session.get('shop_id')
    if not shop_id:
        return jsonify({'success': False, 'message': 'Shop not found'}), 404
    
    try:
        # Handle both JSON and form-data (for file uploads)
        if request.content_type and 'multipart/form-data' in request.content_type:
            # Form data with file upload
            client_name = request.form.get('client_name', '').strip().upper()
            client_phone = request.form.get('client_phone', '').strip().upper()
            package_id = request.form.get('package_id', '').strip().upper()
            latitude = request.form.get('latitude', '').strip()
            longitude = request.form.get('longitude', '').strip()
            location_name = request.form.get('location_name', '').strip().upper()
            distance_km = request.form.get('distance_km', '').strip()
            weight_kg = request.form.get('weight_kg', '').strip() or None
            tip = request.form.get('tip', '').strip() or None
            delivery_time = request.form.get('delivery_time', '').strip() or None
            is_priority = request.form.get('is_priority', 'false').lower() == 'true'
            is_weather = request.form.get('is_weather', 'false').lower() == 'true'
            payment_method = request.form.get('payment_method', 'cash_on_delivery')
            total_amount = request.form.get('total_amount', '').strip() or None
            if total_amount:
                try:
                    total_amount = float(total_amount)
                except ValueError:
                    total_amount = None
            
            # Handle package image upload
            package_image_path = None
            if 'package_image' in request.files:
                image_file = request.files['package_image']
                if image_file and image_file.filename:
                    package_image_path = save_uploaded_file(image_file, 'items')
        else:
            # JSON data (for STK Push or other JSON requests)
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'No data provided'}), 400
            
            client_name = data.get('client_name', '').strip().upper()
            client_phone = data.get('client_phone', '').strip().upper()
            package_id = data.get('package_id', '').strip().upper()
            latitude = data.get('latitude', '').strip()
            longitude = data.get('longitude', '').strip()
            location_name = data.get('location_name', '').strip().upper()
            distance_km = data.get('distance_km', '').strip()
            weight_kg = data.get('weight_kg', '').strip() or None
            tip = data.get('tip', '').strip() or None
            delivery_time = data.get('delivery_time', '').strip() or None
            is_priority = data.get('is_priority', False)
            is_weather = data.get('is_weather', False)
            payment_method = data.get('payment_method', 'cash_on_delivery')
            total_amount = data.get('total_amount')
            if total_amount:
                try:
                    total_amount = float(total_amount)
                except (ValueError, TypeError):
                    total_amount = None
            package_image_path = None
        
        # Validate required fields
        if not all([client_name, client_phone, package_id, latitude, longitude, location_name]):
            return jsonify({'success': False, 'message': 'All fields are required'}), 400
        
        # Validate coordinates
        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid coordinates'}), 400
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection error'}), 500
        
        try:
            with connection.cursor() as cursor:
                # Get shop location for distance calculation
                cursor.execute("SELECT latitude, longitude FROM shops WHERE id = %s", (shop_id,))
                shop = cursor.fetchone()
                if not shop:
                    return jsonify({'success': False, 'message': 'Shop not found'}), 404
                
                # 1. Insert or get customer
                cursor.execute("""
                    SELECT id FROM customers 
                    WHERE phone = %s
                """, (client_phone,))
                customer = cursor.fetchone()
                
                if customer:
                    customer_id = customer['id']
                    # Update customer name if different
                    cursor.execute("""
                        UPDATE customers SET name = %s WHERE id = %s
                    """, (client_name, customer_id))
                else:
                    cursor.execute("""
                        INSERT INTO customers (name, phone, created_at)
                        VALUES (%s, %s, NOW())
                    """, (client_name, client_phone))
                    customer_id = cursor.lastrowid
                
                # 2. Generate unique order number
                import random
                from datetime import datetime
                
                def generate_order_number():
                    """Generate a unique order number in format: ORD-YYYYMMDD-HHMMSS-XXXX"""
                    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
                    random_suffix = f"{random.randint(1000, 9999)}"
                    order_number = f"ORD-{timestamp}-{random_suffix}"
                    
                    # Check if order number exists, regenerate if needed (max 10 attempts)
                    attempts = 0
                    while attempts < 10:
                        cursor.execute("SELECT id FROM orders WHERE order_number = %s", (order_number,))
                        if not cursor.fetchone():
                            break
                        random_suffix = f"{random.randint(1000, 9999)}"
                        order_number = f"ORD-{timestamp}-{random_suffix}"
                        attempts += 1
                    
                    return order_number
                
                order_number = generate_order_number()
                
                # 3. Create order with PACKAGE DELIVERY type and pending status
                # Always use status column (not order_status) and set to 'pending'
                existing_cols = get_table_columns('orders')
                has_status_col = 'status' in existing_cols if existing_cols else False
                has_delivery_fee = 'delivery_fee' in existing_cols if existing_cols else False
                
                # Use total_amount from form, default to 0.00 if not provided
                delivery_total = total_amount if total_amount is not None else 0.00
                
                # Debug: Print detected columns
                print(f"DEBUG: Existing columns: {existing_cols}")
                print(f"DEBUG: has_status_col: {has_status_col}, has_delivery_fee: {has_delivery_fee}")
                print(f"DEBUG: total_amount from form: {total_amount}, using: {delivery_total}")
                
                # Check if order_number column exists, if not add it
                try:
                    if has_status_col:
                        # Use status column and set to 'pending'
                        if 'customer_id' in existing_cols and 'order_type' in existing_cols and 'total_amount' in existing_cols:
                            if has_delivery_fee:
                                cursor.execute("""
                                    INSERT INTO orders (shop_id, customer_id, order_type, status, total_amount, delivery_fee, order_number, created_at)
                                    VALUES (%s, %s, 'PACKAGE DELIVERY', 'pending', %s, %s, %s, NOW())
                                """, (shop_id, customer_id, delivery_total, delivery_total, order_number))
                            else:
                                cursor.execute("""
                                    INSERT INTO orders (shop_id, customer_id, order_type, status, total_amount, order_number, created_at)
                                    VALUES (%s, %s, 'PACKAGE DELIVERY', 'pending', %s, %s, NOW())
                                """, (shop_id, customer_id, delivery_total, order_number))
                        elif 'customer_id' in existing_cols and 'order_type' in existing_cols:
                            if has_delivery_fee:
                                cursor.execute("""
                                    INSERT INTO orders (shop_id, customer_id, order_type, status, total, delivery_fee, order_number, created_at)
                                    VALUES (%s, %s, 'PACKAGE DELIVERY', 'pending', %s, %s, %s, NOW())
                                """, (shop_id, customer_id, delivery_total, delivery_total, order_number))
                            else:
                                cursor.execute("""
                                    INSERT INTO orders (shop_id, customer_id, order_type, status, total, order_number, created_at)
                                    VALUES (%s, %s, 'PACKAGE DELIVERY', 'pending', %s, %s, NOW())
                                """, (shop_id, customer_id, delivery_total, order_number))
                        else:
                            if has_delivery_fee:
                                cursor.execute("""
                                    INSERT INTO orders (shop_id, customer_name, customer_phone, order_type, status, total, delivery_fee, order_number, created_at)
                                    VALUES (%s, %s, %s, 'PACKAGE DELIVERY', 'pending', %s, %s, %s, NOW())
                                """, (shop_id, client_name, client_phone, delivery_total, delivery_total, order_number))
                            else:
                                cursor.execute("""
                                    INSERT INTO orders (shop_id, customer_name, customer_phone, order_type, status, total, order_number, created_at)
                                    VALUES (%s, %s, %s, 'PACKAGE DELIVERY', 'pending', %s, %s, NOW())
                                """, (shop_id, client_name, client_phone, delivery_total, order_number))
                    else:
                        # No status column, use default (shouldn't happen but handle it)
                        print("WARNING: No status column found!")
                        if 'customer_id' in existing_cols and 'order_type' in existing_cols and 'total_amount' in existing_cols:
                            if has_delivery_fee:
                                cursor.execute("""
                                    INSERT INTO orders (shop_id, customer_id, order_type, total_amount, delivery_fee, order_number, created_at)
                                    VALUES (%s, %s, 'PACKAGE DELIVERY', %s, %s, %s, NOW())
                                """, (shop_id, customer_id, delivery_total, delivery_total, order_number))
                            else:
                                cursor.execute("""
                                    INSERT INTO orders (shop_id, customer_id, order_type, total_amount, order_number, created_at)
                                    VALUES (%s, %s, 'PACKAGE DELIVERY', %s, %s, NOW())
                                """, (shop_id, customer_id, delivery_total, order_number))
                        else:
                            cursor.execute("""
                                INSERT INTO orders (shop_id, customer_id, order_type, total_amount, order_number, created_at)
                                VALUES (%s, %s, 'PACKAGE DELIVERY', 0.00, %s, NOW())
                            """, (shop_id, customer_id, order_number))
                except Exception as e:
                    # If order_number column doesn't exist, add it and retry
                    error_msg = str(e).lower()
                    if 'order_number' in error_msg or 'unknown column' in error_msg:
                        try:
                            cursor.execute("ALTER TABLE orders ADD COLUMN order_number VARCHAR(50) UNIQUE")
                            connection.commit()
                            if has_status_col:
                                # Use status column and set to 'pending'
                                if 'customer_id' in existing_cols and 'order_type' in existing_cols and 'total_amount' in existing_cols:
                                    if has_delivery_fee:
                                        cursor.execute("""
                                            INSERT INTO orders (shop_id, customer_id, order_type, status, total_amount, delivery_fee, order_number, created_at)
                                            VALUES (%s, %s, 'PACKAGE DELIVERY', 'pending', %s, %s, %s, NOW())
                                        """, (shop_id, customer_id, delivery_total, delivery_total, order_number))
                                    else:
                                        cursor.execute("""
                                            INSERT INTO orders (shop_id, customer_id, order_type, status, total_amount, order_number, created_at)
                                            VALUES (%s, %s, 'PACKAGE DELIVERY', 'pending', %s, %s, NOW())
                                        """, (shop_id, customer_id, delivery_total, order_number))
                                elif 'customer_id' in existing_cols and 'order_type' in existing_cols:
                                    if has_delivery_fee:
                                        cursor.execute("""
                                            INSERT INTO orders (shop_id, customer_id, order_type, status, total, delivery_fee, order_number, created_at)
                                            VALUES (%s, %s, 'PACKAGE DELIVERY', 'pending', %s, %s, %s, NOW())
                                        """, (shop_id, customer_id, delivery_total, delivery_total, order_number))
                                    else:
                                        cursor.execute("""
                                            INSERT INTO orders (shop_id, customer_id, order_type, status, total, order_number, created_at)
                                            VALUES (%s, %s, 'PACKAGE DELIVERY', 'pending', %s, %s, NOW())
                                        """, (shop_id, customer_id, delivery_total, order_number))
                                else:
                                    if has_delivery_fee:
                                        cursor.execute("""
                                            INSERT INTO orders (shop_id, customer_name, customer_phone, order_type, status, total, delivery_fee, order_number, created_at)
                                            VALUES (%s, %s, %s, 'PACKAGE DELIVERY', 'pending', %s, %s, %s, NOW())
                                        """, (shop_id, client_name, client_phone, delivery_total, delivery_total, order_number))
                                    else:
                                        cursor.execute("""
                                            INSERT INTO orders (shop_id, customer_name, customer_phone, order_type, status, total, order_number, created_at)
                                            VALUES (%s, %s, %s, 'PACKAGE DELIVERY', 'pending', %s, %s, NOW())
                                        """, (shop_id, client_name, client_phone, delivery_total, order_number))
                            else:
                                cursor.execute("""
                                    INSERT INTO orders (shop_id, customer_id, order_type, total_amount, order_number, created_at)
                                    VALUES (%s, %s, 'PACKAGE DELIVERY', 0.00, %s, NOW())
                                """, (shop_id, customer_id, order_number))
                        except Exception as alter_error:
                            # If column already exists or other error, try without order_number
                            print(f"Error adding order_number column: {alter_error}")
                            if has_status_col:
                                # Use status column and set to 'pending'
                                if 'customer_id' in existing_cols and 'order_type' in existing_cols and 'total_amount' in existing_cols:
                                    if has_delivery_fee:
                                        cursor.execute("""
                                            INSERT INTO orders (shop_id, customer_id, order_type, status, total_amount, delivery_fee, created_at)
                                            VALUES (%s, %s, 'PACKAGE DELIVERY', 'pending', %s, %s, NOW())
                                        """, (shop_id, customer_id, delivery_total, delivery_total))
                                    else:
                                        cursor.execute("""
                                            INSERT INTO orders (shop_id, customer_id, order_type, status, total_amount, created_at)
                                            VALUES (%s, %s, 'PACKAGE DELIVERY', 'pending', %s, NOW())
                                        """, (shop_id, customer_id, delivery_total))
                                elif 'customer_id' in existing_cols and 'order_type' in existing_cols:
                                    if has_delivery_fee:
                                        cursor.execute("""
                                            INSERT INTO orders (shop_id, customer_id, order_type, status, total, delivery_fee, created_at)
                                            VALUES (%s, %s, 'PACKAGE DELIVERY', 'pending', %s, %s, NOW())
                                        """, (shop_id, customer_id, delivery_total, delivery_total))
                                    else:
                                        cursor.execute("""
                                            INSERT INTO orders (shop_id, customer_id, order_type, status, total, created_at)
                                            VALUES (%s, %s, 'PACKAGE DELIVERY', 'pending', %s, NOW())
                                        """, (shop_id, customer_id, delivery_total))
                                else:
                                    if has_delivery_fee:
                                        cursor.execute("""
                                            INSERT INTO orders (shop_id, customer_name, customer_phone, order_type, status, total, delivery_fee, created_at)
                                            VALUES (%s, %s, %s, 'PACKAGE DELIVERY', 'pending', %s, %s, NOW())
                                        """, (shop_id, client_name, client_phone, delivery_total, delivery_total))
                                    else:
                                        cursor.execute("""
                                            INSERT INTO orders (shop_id, customer_name, customer_phone, order_type, status, total, created_at)
                                            VALUES (%s, %s, %s, 'PACKAGE DELIVERY', 'pending', %s, NOW())
                                        """, (shop_id, client_name, client_phone, delivery_total))
                            else:
                                cursor.execute("""
                                    INSERT INTO orders (shop_id, customer_id, order_type, total_amount, created_at)
                                    VALUES (%s, %s, 'PACKAGE DELIVERY', 0.00, NOW())
                                """, (shop_id, customer_id))
                            order_number = None
                    else:
                        raise
                
                order_id = cursor.lastrowid
                
                # 4. Insert package as order item - check table structure
                try:
                    existing_cols = get_table_columns('order_items')
                    if existing_cols:
                        if 'item_id' in existing_cols and 'unit_price' in existing_cols and 'subtotal' in existing_cols:
                            # Check if item_id is nullable
                            cursor.execute("SHOW COLUMNS FROM order_items WHERE Field = 'item_id'")
                            item_id_col = cursor.fetchone()
                            if 'item_image' in existing_cols:
                                # Include item_image if column exists
                                if item_id_col and 'YES' in item_id_col.get('Null', ''):
                                    cursor.execute("""
                                        INSERT INTO order_items (order_id, item_id, item_name, item_image, quantity, unit_price, subtotal, created_at)
                                        VALUES (%s, NULL, %s, %s, 1, 0.00, 0.00, NOW())
                                    """, (order_id, f'PACKAGE: {package_id}', package_image_path))
                                else:
                                    cursor.execute("""
                                        INSERT INTO order_items (order_id, item_id, item_name, item_image, quantity, unit_price, subtotal, created_at)
                                        VALUES (%s, 0, %s, %s, 1, 0.00, 0.00, NOW())
                                    """, (order_id, f'PACKAGE: {package_id}', package_image_path))
                            else:
                                # No item_image column
                                if item_id_col and 'YES' in item_id_col.get('Null', ''):
                                    cursor.execute("""
                                        INSERT INTO order_items (order_id, item_id, item_name, quantity, unit_price, subtotal, created_at)
                                        VALUES (%s, NULL, %s, 1, 0.00, 0.00, NOW())
                                    """, (order_id, f'PACKAGE: {package_id}'))
                                else:
                                    cursor.execute("""
                                        INSERT INTO order_items (order_id, item_id, item_name, quantity, unit_price, subtotal, created_at)
                                        VALUES (%s, 0, %s, 1, 0.00, 0.00, NOW())
                                    """, (order_id, f'PACKAGE: {package_id}'))
                        elif 'price' in existing_cols:
                            if 'item_image' in existing_cols:
                                cursor.execute("""
                                    INSERT INTO order_items (order_id, item_name, item_image, quantity, price, created_at)
                                    VALUES (%s, %s, %s, 1, 0.00, NOW())
                                """, (order_id, f'PACKAGE: {package_id}', package_image_path))
                            else:
                                cursor.execute("""
                                    INSERT INTO order_items (order_id, item_name, quantity, price, created_at)
                                    VALUES (%s, %s, 1, 0.00, NOW())
                                """, (order_id, f'PACKAGE: {package_id}'))
                        else:
                            if 'item_image' in existing_cols:
                                cursor.execute("""
                                    INSERT INTO order_items (order_id, item_name, item_image, quantity, created_at)
                                    VALUES (%s, %s, %s, 1, NOW())
                                """, (order_id, f'PACKAGE: {package_id}', package_image_path))
                            else:
                                cursor.execute("""
                                    INSERT INTO order_items (order_id, item_name, quantity, created_at)
                                    VALUES (%s, %s, 1, NOW())
                                """, (order_id, f'PACKAGE: {package_id}'))
                except Exception as e:
                    print(f"Note: Could not insert order item: {e}")
                    pass
                
                # 5. Insert delivery details
                cursor.execute("""
                    INSERT INTO delivery_details (order_id, delivery_location_name, delivery_latitude, delivery_longitude, shop_latitude, shop_longitude, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                """, (order_id, location_name, latitude, longitude, shop['latitude'], shop['longitude']))
                
                connection.commit()
                
                return jsonify({
                    'success': True,
                    'message': f'Package delivery created successfully! Order Number: {order_number}',
                    'order_id': order_id,
                    'order_number': order_number
                })
        except Exception as e:
            connection.rollback()
            print(f"Error creating package delivery: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'message': 'Failed to create delivery'}), 500
        finally:
            connection.close()
            
    except Exception as e:
        print(f"Error in create_package_delivery: {e}")
        return jsonify({'success': False, 'message': 'An error occurred'}), 500

@app.route('/api/shop/stk-push', methods=['POST'])
def initiate_stk_push():
    """Initiate M-Pesa STK Push payment."""
    if not session.get('logged_in') or session.get('user_type') != 'shop':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    shop_id = session.get('shop_id')
    if not shop_id:
        return jsonify({'success': False, 'message': 'Shop not found'}), 404
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        phone_number = data.get('phone_number', '').strip()
        amount = data.get('amount', 0)
        
        # Validate phone number
        if not phone_number:
            return jsonify({'success': False, 'message': 'Phone number is required'}), 400
        
        # Validate amount
        try:
            amount = float(amount)
            if amount <= 0:
                return jsonify({'success': False, 'message': 'Amount must be greater than 0'}), 400
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'Invalid amount'}), 400
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection error'}), 500
        
        try:
            with connection.cursor() as cursor:
                # STEP 1: Create order first (before payment)
                # Get shop location
                cursor.execute("SELECT latitude, longitude FROM shops WHERE id = %s", (shop_id,))
                shop_location = cursor.fetchone()
                if not shop_location:
                    return jsonify({'success': False, 'message': 'Shop not found'}), 404
                
                # Get order data from request
                client_name = data.get('client_name', '').strip().upper()
                client_phone = data.get('client_phone', '').strip().upper()
                package_id = data.get('package_id', '').strip().upper()
                latitude = data.get('latitude', '').strip()
                longitude = data.get('longitude', '').strip()
                location_name = data.get('location_name', '').strip().upper()
                package_image_path = data.get('package_image_path', None)  # Optional image path
                
                # Validate required fields for order creation
                if not all([client_name, client_phone, package_id, latitude, longitude, location_name]):
                    return jsonify({'success': False, 'message': 'All order fields are required'}), 400
                
                # Ensure customers table exists
                try:
                    cursor.execute("SELECT 1 FROM customers LIMIT 1")
                except:
                    # Table doesn't exist, create it
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS customers (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            name VARCHAR(100) NOT NULL,
                            phone VARCHAR(20) NOT NULL,
                            email VARCHAR(100),
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                            INDEX idx_phone (phone),
                            INDEX idx_email (email)
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """)
                    connection.commit()
                
                # Insert or get customer
                cursor.execute("SELECT id FROM customers WHERE phone = %s", (client_phone,))
                customer = cursor.fetchone()
                if customer:
                    customer_id = customer['id']
                    cursor.execute("UPDATE customers SET name = %s WHERE id = %s", (client_name, customer_id))
                else:
                    cursor.execute("INSERT INTO customers (name, phone, created_at) VALUES (%s, %s, NOW())", (client_name, client_phone))
                    customer_id = cursor.lastrowid
                
                # Generate order number
                import random
                from datetime import datetime
                timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
                random_suffix = f"{random.randint(1000, 9999)}"
                order_number = f"ORD-{timestamp}-{random_suffix}"
                
                # Check if order number exists
                attempts = 0
                while attempts < 10:
                    cursor.execute("SELECT id FROM orders WHERE order_number = %s", (order_number,))
                    if not cursor.fetchone():
                        break
                    random_suffix = f"{random.randint(1000, 9999)}"
                    order_number = f"ORD-{timestamp}-{random_suffix}"
                    attempts += 1
                
                # Create order with pending payment
                # Check which columns exist and use appropriate INSERT statement
                existing_order_columns = get_table_columns('orders')
                
                # Build INSERT statement based on available columns
                # Check which status column exists - use status column
                has_status_col = 'status' in existing_order_columns if existing_order_columns else False
                
                # Debug: Print detected columns
                print(f"DEBUG STK: Existing columns: {existing_order_columns}")
                print(f"DEBUG STK: has_status_col: {has_status_col}")
                
                # Use status column
                if 'customer_id' in existing_order_columns and 'order_type' in existing_order_columns and has_status_col and 'total_amount' in existing_order_columns:
                    # Use new columns with status column
                    cursor.execute("""
                        INSERT INTO orders (shop_id, customer_id, order_type, status, total_amount, order_number, 
                                          payment_method, payment_status, created_at)
                        VALUES (%s, %s, 'PACKAGE DELIVERY', 'pending', %s, %s, 'mpesa', 'pending', NOW())
                    """, (shop_id, customer_id, amount, order_number))
                elif 'customer_id' in existing_order_columns and 'order_type' in existing_order_columns and has_status_col:
                    # Use total instead of total_amount, with status column
                    cursor.execute("""
                        INSERT INTO orders (shop_id, customer_id, order_type, status, total, order_number, 
                                          payment_method, payment_status, created_at)
                        VALUES (%s, %s, 'PACKAGE DELIVERY', 'pending', %s, %s, 'mpesa', 'pending', NOW())
                    """, (shop_id, customer_id, amount, order_number))
                elif 'order_type' in existing_order_columns and has_status_col:
                    # Use customer_name/phone instead of customer_id, with status column
                    cursor.execute("""
                        INSERT INTO orders (shop_id, customer_name, customer_phone, order_type, status, total, order_number, 
                                          payment_method, payment_status, created_at)
                        VALUES (%s, %s, %s, 'PACKAGE DELIVERY', 'pending', %s, %s, 'mpesa', 'pending', NOW())
                    """, (shop_id, client_name, client_phone, amount, order_number))
                else:
                    # Use basic columns only
                    cursor.execute("""
                        INSERT INTO orders (shop_id, customer_name, customer_phone, total, order_number, 
                                          payment_method, payment_status, created_at)
                        VALUES (%s, %s, %s, %s, %s, 'mpesa', 'pending', NOW())
                    """, (shop_id, client_name, client_phone, amount, order_number))
                
                order_id = cursor.lastrowid
                
                # Insert package as order item
                # Check if order_items table exists and what columns it has
                try:
                    existing_cols = get_table_columns('order_items')
                    if existing_cols:
                        if 'item_id' in existing_cols and 'unit_price' in existing_cols and 'subtotal' in existing_cols:
                            # Use full schema with item_id (set to 0 or NULL if nullable)
                            if 'item_id' in existing_cols:
                                # Check if item_id is nullable
                                cursor.execute("SHOW COLUMNS FROM order_items WHERE Field = 'item_id'")
                                item_id_col = cursor.fetchone()
                                if 'item_image' in existing_cols:
                                    # Include item_image if column exists
                                    if item_id_col and 'YES' in item_id_col.get('Null', ''):
                                        cursor.execute("""
                                            INSERT INTO order_items (order_id, item_id, item_name, item_image, quantity, unit_price, subtotal, created_at)
                                            VALUES (%s, NULL, %s, %s, 1, %s, %s, NOW())
                                        """, (order_id, f'PACKAGE: {package_id}', package_image_path, amount, amount))
                                    else:
                                        cursor.execute("""
                                            INSERT INTO order_items (order_id, item_id, item_name, item_image, quantity, unit_price, subtotal, created_at)
                                            VALUES (%s, 0, %s, %s, 1, %s, %s, NOW())
                                        """, (order_id, f'PACKAGE: {package_id}', package_image_path, amount, amount))
                                else:
                                    # No item_image column
                                    if item_id_col and 'YES' in item_id_col.get('Null', ''):
                                        cursor.execute("""
                                            INSERT INTO order_items (order_id, item_id, item_name, quantity, unit_price, subtotal, created_at)
                                            VALUES (%s, NULL, %s, 1, %s, %s, NOW())
                                        """, (order_id, f'PACKAGE: {package_id}', amount, amount))
                                    else:
                                        cursor.execute("""
                                            INSERT INTO order_items (order_id, item_id, item_name, quantity, unit_price, subtotal, created_at)
                                            VALUES (%s, 0, %s, 1, %s, %s, NOW())
                                        """, (order_id, f'PACKAGE: {package_id}', amount, amount))
                            else:
                                # No item_id column
                                if 'item_image' in existing_cols:
                                    cursor.execute("""
                                        INSERT INTO order_items (order_id, item_name, item_image, quantity, unit_price, subtotal, created_at)
                                        VALUES (%s, %s, %s, 1, %s, %s, NOW())
                                    """, (order_id, f'PACKAGE: {package_id}', package_image_path, amount, amount))
                                else:
                                    cursor.execute("""
                                        INSERT INTO order_items (order_id, item_name, quantity, unit_price, subtotal, created_at)
                                        VALUES (%s, %s, 1, %s, %s, NOW())
                                    """, (order_id, f'PACKAGE: {package_id}', amount, amount))
                        elif 'price' in existing_cols:
                            # Use price column if it exists
                            cursor.execute("""
                                INSERT INTO order_items (order_id, item_name, quantity, price, created_at)
                                VALUES (%s, %s, 1, %s, NOW())
                            """, (order_id, f'PACKAGE: {package_id}', amount))
                        else:
                            # Minimal insert
                            cursor.execute("""
                                INSERT INTO order_items (order_id, item_name, quantity, created_at)
                                VALUES (%s, %s, 1, NOW())
                            """, (order_id, f'PACKAGE: {package_id}'))
                except Exception as e:
                    # Table doesn't exist or error, skip order_items insert
                    print(f"Note: Could not insert order item: {e}")
                    pass
                
                # Insert delivery details
                try:
                    cursor.execute("""
                        INSERT INTO delivery_details (order_id, delivery_location_name, delivery_latitude, 
                                                     delivery_longitude, shop_latitude, shop_longitude, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    """, (order_id, location_name, latitude, longitude, shop_location['latitude'], shop_location['longitude']))
                except Exception as e:
                    # If table doesn't exist, create it
                    if 'doesn\'t exist' in str(e).lower() or '1146' in str(e):
                        print(f"Creating delivery_details table...")
                        cursor.execute("""
                            CREATE TABLE IF NOT EXISTS delivery_details (
                                id INT AUTO_INCREMENT PRIMARY KEY,
                                order_id INT NOT NULL,
                                delivery_location_name VARCHAR(255) NOT NULL,
                                delivery_latitude DECIMAL(10, 8) NOT NULL,
                                delivery_longitude DECIMAL(10, 8) NOT NULL,
                                shop_latitude DECIMAL(10, 8),
                                shop_longitude DECIMAL(10, 8),
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                                INDEX idx_order_id (order_id),
                                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
                            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                        """)
                        connection.commit()
                        # Retry insert
                        cursor.execute("""
                            INSERT INTO delivery_details (order_id, delivery_location_name, delivery_latitude, 
                                                         delivery_longitude, shop_latitude, shop_longitude, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, NOW())
                        """, (order_id, location_name, latitude, longitude, shop_location['latitude'], shop_location['longitude']))
                    else:
                        print(f"Error inserting delivery details: {e}")
                        pass  # Continue anyway
                
                connection.commit()
                
                # STEP 2: Now initiate STK Push payment
                # Get shop payment settings
                cursor.execute("""
                    SELECT payments_to_shop, mpesa_type, mpesa_paybill_business_number, 
                           mpesa_paybill_account, mpesa_buy_goods_till
                    FROM shops
                    WHERE id = %s
                """, (shop_id,))
                shop_payment = cursor.fetchone()
                
                if not shop_payment:
                    connection.rollback()
                    return jsonify({'success': False, 'message': 'Shop payment settings not found'}), 404
                
                # Determine if using shop or company payment accounts
                payments_to_shop = shop_payment.get('payments_to_shop', 0)
                
                if payments_to_shop:
                    # Use shop's payment settings
                    mpesa_type = shop_payment.get('mpesa_type', 'paybill')
                    if mpesa_type == 'paybill':
                        business_number = shop_payment.get('mpesa_paybill_business_number', '')
                        account_number = shop_payment.get('mpesa_paybill_account', '')
                    else:
                        business_number = shop_payment.get('mpesa_buy_goods_till', '')
                        account_number = ''
                else:
                    # Use company payment settings
                    cursor.execute("""
                        SELECT mpesa_type, mpesa_paybill_business_number, 
                               mpesa_paybill_account, mpesa_buy_goods_till
                        FROM company_payment_accounts
                        ORDER BY id DESC LIMIT 1
                    """)
                    company_settings = cursor.fetchone()
                    
                    if not company_settings:
                        connection.rollback()
                        return jsonify({'success': False, 'message': 'Company payment settings not configured'}), 400
                    
                    mpesa_type = company_settings.get('mpesa_type', 'paybill')
                    if mpesa_type == 'paybill':
                        business_number = company_settings.get('mpesa_paybill_business_number', '')
                        account_number = company_settings.get('mpesa_paybill_account', '')
                    else:
                        business_number = company_settings.get('mpesa_buy_goods_till', '')
                        account_number = ''
                
                # Validate paybill/till number is configured
                if not business_number:
                    connection.rollback()
                    return jsonify({
                        'success': False, 
                        'message': f'{"Shop" if payments_to_shop else "Company"} payment settings not configured. Please configure M-Pesa Paybill/Till number in settings.'
                    }), 400
                
                # M-Pesa STK Push API implementation
                # For sandbox testing, use test shortcode regardless of what's in database
                if MPESA_ENVIRONMENT == 'sandbox':
                    if mpesa_type == 'paybill':
                        MPESA_SHORTCODE = MPESA_SANDBOX_PAYBILL
                    else:
                        MPESA_SHORTCODE = MPESA_SANDBOX_TILL
                    print(f"Sandbox mode: Using test shortcode {MPESA_SHORTCODE} (ignoring database value: {business_number})")
                else:
                    MPESA_SHORTCODE = business_number  # Use actual paybill/till from database in production
                
                # Validate shortcode format (should be numeric, 5-7 digits)
                if not MPESA_SHORTCODE or not MPESA_SHORTCODE.isdigit() or len(MPESA_SHORTCODE) < 5:
                    return jsonify({
                        'success': False,
                        'message': f'Invalid Paybill/Till number: {MPESA_SHORTCODE}. Please configure a valid M-Pesa business number in payment settings.'
                    }), 400
                
                # Simple callback URL - use production URL or environment variable
                callback_url = os.getenv('MPESA_CALLBACK_URL', 'https://kwetudeliveries.com/api/shop/stk-callback')
                
                try:
                    # Step 1: Get access token from M-Pesa OAuth API
                    auth_url = f'{MPESA_BASE_URL}/oauth/v1/generate?grant_type=client_credentials'
                    auth_response = requests.get(
                        auth_url,
                        auth=(MPESA_CONSUMER_KEY, MPESA_CONSUMER_SECRET),
                        timeout=10
                    )
                    
                    if auth_response.status_code != 200:
                        print(f"M-Pesa Auth Error: {auth_response.status_code} - {auth_response.text}")
                        return jsonify({
                            'success': False,
                            'message': 'Failed to authenticate with M-Pesa API. Please check your credentials.'
                        }), 500
                    
                    auth_data = auth_response.json()
                    if 'access_token' not in auth_data:
                        print(f"M-Pesa Auth Response: {auth_data}")
                        return jsonify({
                            'success': False,
                            'message': 'Failed to get access token from M-Pesa API.'
                        }), 500
                    
                    access_token = auth_data['access_token']
                    
                    # Step 2: Generate password (base64 encoded timestamp + passkey)
                    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                    password_string = f"{MPESA_SHORTCODE}{MPESA_PASSKEY}{timestamp}"
                    password = base64.b64encode(password_string.encode()).decode()
                    
                    # Step 3: Prepare STK Push request
                    stk_url = f'{MPESA_BASE_URL}/mpesa/stkpush/v1/processrequest'
                    headers = {
                        'Authorization': f'Bearer {access_token}',
                        'Content-Type': 'application/json'
                    }
                    
                    # Determine transaction type based on mpesa_type
                    transaction_type = 'CustomerPayBillOnline' if mpesa_type == 'paybill' else 'CustomerBuyGoodsOnline'
                    
                    payload = {
                        'BusinessShortCode': MPESA_SHORTCODE,
                        'Password': password,
                        'Timestamp': timestamp,
                        'TransactionType': transaction_type,
                        'Amount': int(amount),
                        'PartyA': phone_number,
                        'PartyB': MPESA_SHORTCODE,
                        'PhoneNumber': phone_number,
                        'CallBackURL': callback_url,
                        'AccountReference': account_number or f'ORD-{order_number}',
                        'TransactionDesc': f'Package Delivery - {package_id}'
                    }
                    
                    print(f"STK Push Request - Shortcode: {MPESA_SHORTCODE}, Type: {transaction_type}, Amount: {amount}, Phone: {phone_number}")
                    
                    # Step 4: Make STK Push request
                    stk_response = requests.post(stk_url, json=payload, headers=headers, timeout=30)
                    
                    if stk_response.status_code != 200:
                        error_text = stk_response.text
                        print(f"M-Pesa STK Push Error: {stk_response.status_code} - {error_text}")
                        try:
                            error_data = stk_response.json()
                            error_message = error_data.get('errorMessage', error_data.get('error', error_text))
                        except:
                            error_message = error_text
                        return jsonify({
                            'success': False,
                            'message': f'Failed to initiate STK Push: {error_message}'
                        }), 500
                    
                    result = stk_response.json()
                    
                    # Check response code
                    response_code = result.get('ResponseCode', '')
                    if response_code == '0':
                        checkout_request_id = result.get('CheckoutRequestID', '')
                        customer_message = result.get('CustomerMessage', 'STK Push initiated successfully')
                        
                        # Save STK Push request to database
                        try:
                            cursor.execute("""
                                INSERT INTO stk_push_requests (order_id, checkout_request_id, phone_number, amount, status, created_at)
                                VALUES (%s, %s, %s, %s, 'pending', NOW())
                            """, (order_id, checkout_request_id, phone_number, amount))
                            connection.commit()
                        except Exception as e:
                            print(f"Error saving STK Push request: {e}")
                            # Continue anyway - order is created
                        
                        return jsonify({
                            'success': True,
                            'message': customer_message,
                            'checkout_request_id': checkout_request_id,
                            'order_id': order_id,
                            'order_number': order_number
                        })
                    else:
                        # Payment initiation failed - mark order as failed
                        try:
                            # Update order - check which status column exists
                            existing_cols = get_table_columns('orders')
                            if 'status' in existing_cols:
                                cursor.execute("""
                                    UPDATE orders SET payment_status = 'failed', status = 'cancelled' WHERE id = %s
                                """, (order_id,))
                            # Status column is handled separately
                            else:
                                cursor.execute("""
                                    UPDATE orders SET payment_status = 'failed' WHERE id = %s
                                """, (order_id,))
                            connection.commit()
                        except:
                            pass
                        
                        error_message = result.get('CustomerMessage', result.get('errorMessage', 'Failed to initiate STK Push'))
                        return jsonify({
                            'success': False,
                            'message': error_message,
                            'order_id': order_id
                        }), 400
                        
                except requests.exceptions.RequestException as e:
                    print(f"M-Pesa API Request Error: {e}")
                    return jsonify({
                        'success': False,
                        'message': f'Network error connecting to M-Pesa API: {str(e)}'
                    }), 500
                except Exception as e:
                    print(f"M-Pesa STK Push Error: {e}")
                    import traceback
                    traceback.print_exc()
                    return jsonify({
                        'success': False,
                        'message': f'Error initiating STK Push: {str(e)}'
                    }), 500
                
        except Exception as e:
            connection.rollback()
            print(f"Error initiating STK Push: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'message': 'Failed to initiate STK Push'}), 500
        finally:
            connection.close()
            
    except Exception as e:
        print(f"Error in initiate_stk_push: {e}")
        return jsonify({'success': False, 'message': 'An error occurred'}), 500

@app.route('/api/shop/stk-callback', methods=['POST'])
def stk_push_callback():
    """Handle M-Pesa STK Push callback."""
    try:
        # Log raw request data for debugging
        raw_data = request.get_data(as_text=True)
        print(f"=== M-Pesa STK Push Callback Received ===")
        print(f"Raw data: {raw_data}")
        print(f"Content-Type: {request.content_type}")
        
        data = request.get_json()
        if not data:
            print("Warning: No JSON data received in callback")
            return jsonify({'ResultCode': 0, 'ResultDesc': 'Accepted'}), 200
        
        print(f"Parsed JSON: {data}")
        
        # Extract callback data - handle different M-Pesa callback formats
        body = data.get('Body', data)  # Some callbacks send data directly
        stk_callback = body.get('stkCallback', body)  # Fallback to body if stkCallback doesn't exist
        
        # Handle both string and integer result codes
        result_code_raw = stk_callback.get('ResultCode', '')
        result_code = int(result_code_raw) if result_code_raw else -1
        result_desc = stk_callback.get('ResultDesc', '')
        merchant_request_id = stk_callback.get('MerchantRequestID', '')
        checkout_request_id = stk_callback.get('CheckoutRequestID', '')
        customer_message = stk_callback.get('CustomerMessage', '')
        callback_metadata = stk_callback.get('CallbackMetadata', {})
        items = callback_metadata.get('Item', [])
        
        # Extract transaction details
        transaction_data = {}
        for item in items:
            if isinstance(item, dict):
                transaction_data[item.get('Name', '')] = item.get('Value', '')
        
        mpesa_receipt_number = transaction_data.get('MpesaReceiptNumber', '')
        transaction_date = transaction_data.get('TransactionDate', '')
        phone_number = transaction_data.get('PhoneNumber', '')
        amount = transaction_data.get('Amount', 0)
        
        # Build comprehensive message from M-Pesa
        # ResultDesc contains the main message, CustomerMessage may have additional info
        mpesa_message = result_desc
        if customer_message and customer_message != result_desc:
            mpesa_message = f"{result_desc}. {customer_message}"
        
        print(f"=== M-Pesa Payment Notification ===")
        print(f"Result Code: {result_code}")
        print(f"Result Description: {result_desc}")
        print(f"Customer Message: {customer_message}")
        print(f"Full Message: {mpesa_message}")
        print(f"CheckoutRequestID: {checkout_request_id}")
        print(f"MerchantRequestID: {merchant_request_id}")
        print(f"Phone Number: {phone_number}")
        print(f"Amount: {amount}")
        print(f"Receipt Number: {mpesa_receipt_number}")
        print(f"Transaction Date: {transaction_date}")
        
        connection = get_db_connection()
        if connection:
            try:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, order_id FROM stk_push_requests 
                        WHERE checkout_request_id = %s
                    """, (checkout_request_id,))
                    stk_request = cursor.fetchone()
                    
                    if stk_request:
                        order_id = stk_request['order_id']
                        print(f"Found STK request for order_id: {order_id}")
                        
                        if result_code == 0:
                            print(f"✓ Payment SUCCESS for order {order_id}")
                            # Payment successful - store full message and update phone number if provided
                            success_message = mpesa_message or result_desc or "Payment completed successfully"
                            # Update phone number if provided in callback (may be more accurate)
                            if phone_number:
                                cursor.execute("""
                                    UPDATE stk_push_requests 
                                    SET status = 'completed', mpesa_receipt_number = %s, 
                                        transaction_date = %s, result_code = %s, result_desc = %s,
                                        phone_number = %s, updated_at = NOW()
                                    WHERE checkout_request_id = %s
                                """, (mpesa_receipt_number, transaction_date, str(result_code), success_message, phone_number, checkout_request_id))
                            else:
                                cursor.execute("""
                                    UPDATE stk_push_requests 
                                    SET status = 'completed', mpesa_receipt_number = %s, 
                                        transaction_date = %s, result_code = %s, result_desc = %s,
                                        updated_at = NOW()
                                    WHERE checkout_request_id = %s
                                """, (mpesa_receipt_number, transaction_date, str(result_code), success_message, checkout_request_id))
                            
                            # Update order - check which status column exists
                            # For package deliveries, keep status as 'PROCESSING'/'preparing' (rider just picks and delivers)
                            # For other orders, update to 'confirmed'
                            existing_cols = get_table_columns('orders')
                            
                            # Check if this is a package delivery order
                            cursor.execute("SELECT order_type FROM orders WHERE id = %s", (order_id,))
                            order_info = cursor.fetchone()
                            is_package_delivery = order_info and order_info.get('order_type') == 'PACKAGE DELIVERY'
                            
                            if 'status' in existing_cols:
                                if is_package_delivery:
                                    # Package deliveries stay as PROCESSING - rider just picks and delivers
                                    cursor.execute("""
                                        UPDATE orders 
                                        SET payment_status = 'paid', status = 'PROCESSING', updated_at = NOW()
                                        WHERE id = %s
                                    """, (order_id,))
                                else:
                                    # Regular orders go to confirmed after payment
                                    cursor.execute("""
                                        UPDATE orders 
                                        SET payment_status = 'paid', status = 'confirmed', updated_at = NOW()
                                        WHERE id = %s
                                    """, (order_id,))
                            # Status column is handled separately
                            else:
                                cursor.execute("""
                                    UPDATE orders 
                                    SET payment_status = 'paid', updated_at = NOW()
                                    WHERE id = %s
                                """, (order_id,))
                            
                            print(f"✓ Order {order_id} payment completed! Receipt: {mpesa_receipt_number}")
                            connection.commit()
                            print(f"✓ Database updated successfully for order {order_id}")
                        else:
                            # Payment failed - store full failure message with reason
                            print(f"✗ Payment FAILED for order {order_id}. Code: {result_code}, Desc: {result_desc}")
                            failure_message = mpesa_message or result_desc or f"Payment failed with code {result_code}"
                            # Update phone number if provided in callback
                            if phone_number:
                                cursor.execute("""
                                    UPDATE stk_push_requests 
                                    SET status = 'failed', result_code = %s, result_desc = %s, 
                                        phone_number = %s, updated_at = NOW()
                                    WHERE checkout_request_id = %s
                                """, (str(result_code), failure_message, phone_number, checkout_request_id))
                            else:
                                cursor.execute("""
                                    UPDATE stk_push_requests 
                                    SET status = 'failed', result_code = %s, result_desc = %s, updated_at = NOW()
                                    WHERE checkout_request_id = %s
                                """, (str(result_code), failure_message, checkout_request_id))
                            
                            # Update order - check which status column exists
                            existing_cols = get_table_columns('orders')
                            if 'status' in existing_cols:
                                cursor.execute("""
                                    UPDATE orders 
                                    SET payment_status = 'failed', status = 'cancelled', updated_at = NOW()
                                    WHERE id = %s
                                """, (order_id,))
                            # Status column is handled separately
                            else:
                                cursor.execute("""
                                    UPDATE orders 
                                    SET payment_status = 'failed', updated_at = NOW()
                                    WHERE id = %s
                                """, (order_id,))
                            
                            print(f"✗ Order {order_id} payment failed: {result_desc}")
                        
                        connection.commit()
            except Exception as e:
                connection.rollback()
                print(f"Error updating order from callback: {e}")
                import traceback
                traceback.print_exc()
            finally:
                connection.close()
        
        # Always return success to M-Pesa (they expect 200 OK)
        return jsonify({
            'ResultCode': 0,
            'ResultDesc': 'Callback received successfully'
        }), 200
        
    except Exception as e:
        print(f"Error processing STK Push callback: {e}")
        import traceback
        traceback.print_exc()
        # Still return success to M-Pesa
        return jsonify({
            'ResultCode': 0,
            'ResultDesc': 'Callback received'
        }), 200

@app.route('/api/shop/stk-status/<checkout_request_id>', methods=['GET'])
def check_stk_status(checkout_request_id):
    """Check STK Push payment status."""
    if not session.get('logged_in') or session.get('user_type') != 'shop':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    
    try:
        with connection.cursor() as cursor:
            # Check which status column exists in orders table
            existing_cols = get_table_columns('orders')
            if 'status' in existing_cols:
                status_col = 'o.status'
            # Use status column only
            if 'status' in existing_cols:
                status_col = 'o.status'
            else:
                status_col = "NULL"
            
            cursor.execute(f"""
                SELECT sr.status, sr.result_code, sr.result_desc, sr.mpesa_receipt_number,
                       sr.phone_number, sr.amount,
                       o.id as order_id, o.order_number, o.payment_status, {status_col} as status
                FROM stk_push_requests sr
                JOIN orders o ON sr.order_id = o.id
                WHERE sr.checkout_request_id = %s
            """, (checkout_request_id,))
            
            result = cursor.fetchone()
            
            if not result:
                return jsonify({
                    'success': False,
                    'message': 'Payment request not found'
                }), 404
            
            status = result['status']
            payment_status = result['payment_status']
            
            if status == 'completed' and payment_status == 'paid':
                # Success message from M-Pesa
                success_message = result['result_desc'] or 'Payment completed successfully!'
                return jsonify({
                    'success': True,
                    'status': 'completed',
                    'message': success_message,
                    'order_id': result['order_id'],
                    'order_number': result['order_number'],
                    'receipt_number': result['mpesa_receipt_number'],
                    'phone_number': result.get('phone_number', ''),
                    'amount': float(result.get('amount', 0)) if result.get('amount') else 0
                })
            elif status == 'failed':
                # Failure message with reason from M-Pesa
                failure_reason = result['result_desc'] or 'Payment failed. Please try again.'
                return jsonify({
                    'success': False,
                    'status': 'failed',
                    'message': failure_reason,
                    'reason': failure_reason,
                    'result_code': result.get('result_code', ''),
                    'order_id': result['order_id'],
                    'phone_number': result.get('phone_number', ''),
                    'amount': float(result.get('amount', 0)) if result.get('amount') else 0
                })
            else:
                return jsonify({
                    'success': True,
                    'status': 'pending',
                    'message': 'Waiting for payment confirmation...',
                    'order_id': result['order_id']
                })
    except Exception as e:
        print(f"Error checking STK status: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Error checking payment status'}), 500
    finally:
        connection.close()

# ==================== DELIVERY SETTINGS API ====================

def convert_time_to_string(time_obj):
    """Convert time/timedelta object to HH:MM string format."""
    if time_obj is None:
        return ''
    if isinstance(time_obj, str):
        # Already a string, return as is (might be HH:MM:SS, convert to HH:MM)
        return time_obj[:5] if len(time_obj) >= 5 else time_obj
    elif isinstance(time_obj, (time, datetime)):
        return time_obj.strftime('%H:%M')
    elif isinstance(time_obj, timedelta):
        # Convert timedelta to time string
        total_seconds = int(time_obj.total_seconds())
        hours = (total_seconds // 3600) % 24
        minutes = (total_seconds % 3600) // 60
        return f"{hours:02d}:{minutes:02d}"
    else:
        return str(time_obj)[:5] if len(str(time_obj)) >= 5 else str(time_obj)

def calculate_delivery_cost(distance_km, weight_kg=0, is_weather=False, is_priority=False, tip=0, delivery_time=None):
    """
    Calculate delivery cost using the formula:
    DeliveryCost = BaseCost + WeatherFee + NightFee + WeightFee + PriorityFee + Tip
    
    Where:
    - BaseCost = max(minimum_fee, distance_km * price_per_km_from_tiers)
    - WeightFee = fee from matching weight tier
    - PriorityFee = base_cost * (priority_percentage / 100)
    """
    connection = get_db_connection()
    if not connection:
        return None
    
    try:
        with connection.cursor() as cursor:
            # Get main delivery settings
            cursor.execute("SELECT * FROM delivery_settings ORDER BY id DESC LIMIT 1")
            settings = cursor.fetchone()
            
            if not settings:
                # Default values if no settings exist
                minimum_fee = 150.00
                weather_fee = 0.00
                priority_percentage = 0.00
            else:
                minimum_fee = float(settings['minimum_fee'])
                weather_fee = float(settings['weather_fee'])
                priority_percentage = float(settings['priority_percentage'])
            
            # Get price per km from distance tiers
            cursor.execute("""
                SELECT price_per_km 
                FROM delivery_distance_tiers 
                WHERE start_km <= %s AND end_km >= %s
                ORDER BY start_km ASC
                LIMIT 1
            """, (distance_km, distance_km))
            
            tier = cursor.fetchone()
            if tier:
                price_per_km = float(tier['price_per_km'])
            else:
                # Default price if no tier matches
                price_per_km = 10.00
            
            # Calculate base cost
            base_cost = max(minimum_fee, distance_km * price_per_km)
            
            # Get weight fee
            weight_fee = 0.00
            if weight_kg > 0:
                cursor.execute("""
                    SELECT fee_amount 
                    FROM delivery_weight_tiers 
                    WHERE min_kg <= %s AND max_kg >= %s
                    ORDER BY min_kg ASC
                    LIMIT 1
                """, (weight_kg, weight_kg))
                weight_tier = cursor.fetchone()
                if weight_tier:
                    weight_fee = float(weight_tier['fee_amount'])
            
            # Calculate priority fee
            priority_fee = base_cost * (priority_percentage / 100) if is_priority else 0.00
            
            # Calculate peak fee (check if delivery_time falls in any peak hour range)
            peak_fee = 0.00
            if delivery_time:
                from datetime import datetime, time
                try:
                    if isinstance(delivery_time, str):
                        delivery_time_obj = datetime.strptime(delivery_time, '%H:%M').time()
                    else:
                        delivery_time_obj = delivery_time if isinstance(delivery_time, time) else delivery_time.time()
                    
                    cursor.execute("SELECT * FROM delivery_peak_hours")
                    peak_hours = cursor.fetchall()
                    
                    for peak in peak_hours:
                        peak_start = peak['start_time'] if isinstance(peak['start_time'], time) else datetime.strptime(str(peak['start_time']), '%H:%M:%S').time()
                        peak_end = peak['end_time'] if isinstance(peak['end_time'], time) else datetime.strptime(str(peak['end_time']), '%H:%M:%S').time()
                        peak_percentage = float(peak['percentage_increase'])
                        
                        # Handle time ranges that cross midnight
                        if peak_start <= peak_end:
                            # Normal range (e.g., 09:00 to 17:00)
                            if peak_start <= delivery_time_obj <= peak_end:
                                peak_fee = base_cost * (peak_percentage / 100)
                                break
                        else:
                            # Range crosses midnight (e.g., 22:00 to 06:00)
                            if delivery_time_obj >= peak_start or delivery_time_obj <= peak_end:
                                peak_fee = base_cost * (peak_percentage / 100)
                                break
                except Exception as e:
                    print(f"Error calculating peak fee: {e}")
            
            # Calculate night fee (check if delivery_time falls in night hour range)
            night_fee = 0.00
            if delivery_time:
                try:
                    if isinstance(delivery_time, str):
                        delivery_time_obj = datetime.strptime(delivery_time, '%H:%M').time()
                    else:
                        delivery_time_obj = delivery_time if isinstance(delivery_time, time) else delivery_time.time()
                    
                    cursor.execute("SELECT * FROM delivery_night_hours")
                    night_hours = cursor.fetchall()
                    
                    for night in night_hours:
                        night_start = night['start_time'] if isinstance(night['start_time'], time) else datetime.strptime(str(night['start_time']), '%H:%M:%S').time()
                        night_end = night['end_time'] if isinstance(night['end_time'], time) else datetime.strptime(str(night['end_time']), '%H:%M:%S').time()
                        night_percentage = float(night['night_percentage'])
                        
                        # Handle time ranges that cross midnight
                        if night_start <= night_end:
                            # Normal range
                            if night_start <= delivery_time_obj <= night_end:
                                night_fee = base_cost * (night_percentage / 100)
                                break
                        else:
                            # Range crosses midnight
                            if delivery_time_obj >= night_start or delivery_time_obj <= night_end:
                                night_fee = base_cost * (night_percentage / 100)
                                break
                except Exception as e:
                    print(f"Error calculating night fee: {e}")
            
            # Calculate total
            total = (
                base_cost +
                (weather_fee if is_weather else 0) +
                weight_fee +
                priority_fee +
                peak_fee +
                night_fee +
                tip
            )
            
            return {
                'base_cost': round(base_cost, 2),
                'weather_fee': round(weather_fee if is_weather else 0, 2),
                'weight_fee': round(weight_fee, 2),
                'priority_fee': round(priority_fee, 2),
                'peak_fee': round(peak_fee, 2),
                'night_fee': round(night_fee, 2),
                'tip': round(tip, 2),
                'total': round(total, 2)
            }
    except Exception as e:
        print(f"Error calculating delivery cost: {e}")
        return None
    finally:
        connection.close()

@app.route('/api/admin/delivery-settings', methods=['GET'])
def get_delivery_settings():
    """Get delivery settings."""
    if not session.get('logged_in') or session.get('user_type') != 'employee':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    if session.get('employee_role') != 'KWETU_ADMIN':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    
    try:
        with connection.cursor() as cursor:
            # Get main settings
            cursor.execute("SELECT * FROM delivery_settings ORDER BY id DESC LIMIT 1")
            settings = cursor.fetchone()
            
            # Get distance tiers
            cursor.execute("SELECT * FROM delivery_distance_tiers ORDER BY start_km ASC")
            distance_tiers = cursor.fetchall()
            
            # Get weight tiers
            cursor.execute("SELECT * FROM delivery_weight_tiers ORDER BY min_kg ASC")
            weight_tiers = cursor.fetchall()
            
            # Get peak hours
            cursor.execute("SELECT * FROM delivery_peak_hours ORDER BY start_time ASC")
            peak_hours_raw = cursor.fetchall()
            
            # Get night hours
            cursor.execute("SELECT * FROM delivery_night_hours ORDER BY start_time ASC")
            night_hours_raw = cursor.fetchall()
            
            # Process peak hours
            peak_hours = []
            for peak in peak_hours_raw:
                peak_dict = dict(peak)
                peak_dict['start_time'] = convert_time_to_string(peak_dict.get('start_time'))
                peak_dict['end_time'] = convert_time_to_string(peak_dict.get('end_time'))
                peak_hours.append(peak_dict)
            
            # Process night hours
            night_hours = []
            for night in night_hours_raw:
                night_dict = dict(night)
                night_dict['start_time'] = convert_time_to_string(night_dict.get('start_time'))
                night_dict['end_time'] = convert_time_to_string(night_dict.get('end_time'))
                night_hours.append(night_dict)
            
            return jsonify({
                'success': True,
                'settings': settings or {
                    'minimum_fee': 150.00,
                    'weather_fee': 0.00,
                    'priority_percentage': 0.00
                },
                'distance_tiers': distance_tiers or [],
                'weight_tiers': weight_tiers or [],
                'peak_hours': peak_hours or [],
                'night_hours': night_hours or []
            })
    except Exception as e:
        print(f"Error fetching delivery settings: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Error fetching settings'}), 500
    finally:
        connection.close()

@app.route('/api/admin/delivery-settings', methods=['POST'])
def update_delivery_settings():
    """Update delivery settings."""
    if not session.get('logged_in') or session.get('user_type') != 'employee':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    if session.get('employee_role') != 'KWETU_ADMIN':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    data = request.get_json()
    minimum_fee = int(data.get('minimum_fee', 150))
    weather_fee = float(data.get('weather_fee', 0.00))
    priority_percentage = float(data.get('priority_percentage', 0.00))
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    
    try:
        with connection.cursor() as cursor:
            # Check if settings exist
            cursor.execute("SELECT id FROM delivery_settings ORDER BY id DESC LIMIT 1")
            existing = cursor.fetchone()
            
            if existing:
                cursor.execute("""
                    UPDATE delivery_settings 
                    SET minimum_fee = %s, weather_fee = %s, priority_percentage = %s
                    WHERE id = %s
                """, (minimum_fee, weather_fee, priority_percentage, existing['id']))
            else:
                cursor.execute("""
                    INSERT INTO delivery_settings (minimum_fee, weather_fee, priority_percentage)
                    VALUES (%s, %s, %s)
                """, (minimum_fee, weather_fee, priority_percentage))
            
            connection.commit()
            return jsonify({'success': True, 'message': 'Settings updated successfully'})
    except Exception as e:
        print(f"Error updating delivery settings: {e}")
        return jsonify({'success': False, 'message': 'Error updating settings'}), 500
    finally:
        connection.close()

@app.route('/api/admin/delivery-settings/distance-tiers', methods=['GET'])
def get_distance_tiers():
    """Get distance tiers."""
    if not session.get('logged_in') or session.get('user_type') != 'employee':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    if session.get('employee_role') != 'KWETU_ADMIN':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM delivery_distance_tiers ORDER BY start_km ASC")
            tiers = cursor.fetchall()
            return jsonify({'success': True, 'tiers': tiers})
    except Exception as e:
        print(f"Error fetching distance tiers: {e}")
        return jsonify({'success': False, 'message': 'Error fetching tiers'}), 500
    finally:
        connection.close()

def validate_distance_tier(start_km, end_km, exclude_id=None):
    """Validate that distance tier doesn't overlap with existing tiers."""
    connection = get_db_connection()
    if not connection:
        return False, 'Database connection error'
    
    try:
        with connection.cursor() as cursor:
            if start_km >= end_km:
                return False, 'Start KM must be less than End KM'
            
            # Check for overlaps (allow adjacent tiers where one tier's end equals another's start)
            # Overlap occurs when ranges actually overlap, not just touch
            if exclude_id:
                cursor.execute("""
                    SELECT id FROM delivery_distance_tiers 
                    WHERE id != %s AND (
                        (start_km < %s AND end_km > %s) OR
                        (start_km < %s AND end_km > %s) OR
                        (start_km >= %s AND end_km <= %s)
                    )
                """, (exclude_id, start_km, start_km, end_km, end_km, start_km, end_km))
            else:
                cursor.execute("""
                    SELECT id FROM delivery_distance_tiers 
                    WHERE (
                        (start_km < %s AND end_km > %s) OR
                        (start_km < %s AND end_km > %s) OR
                        (start_km >= %s AND end_km <= %s)
                    )
                """, (start_km, start_km, end_km, end_km, start_km, end_km))
            
            overlapping = cursor.fetchone()
            if overlapping:
                return False, 'This tier overlaps with an existing tier'
            
            return True, 'Valid'
    except Exception as e:
        print(f"Error validating distance tier: {e}")
        return False, str(e)
    finally:
        connection.close()

@app.route('/api/admin/delivery-settings/distance-tiers', methods=['POST'])
def add_distance_tier():
    """Add a distance tier."""
    if not session.get('logged_in') or session.get('user_type') != 'employee':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    if session.get('employee_role') != 'KWETU_ADMIN':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    data = request.get_json()
    start_km = float(data.get('start_km', 0))
    end_km = float(data.get('end_km', 0))
    price_per_km = float(data.get('price_per_km', 0))
    
    # Validate
    is_valid, message = validate_distance_tier(start_km, end_km)
    if not is_valid:
        return jsonify({'success': False, 'message': message}), 400
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO delivery_distance_tiers (start_km, end_km, price_per_km)
                VALUES (%s, %s, %s)
            """, (start_km, end_km, price_per_km))
            connection.commit()
            return jsonify({'success': True, 'message': 'Distance tier added successfully'})
    except Exception as e:
        print(f"Error adding distance tier: {e}")
        return jsonify({'success': False, 'message': 'Error adding tier'}), 500
    finally:
        connection.close()

@app.route('/api/admin/delivery-settings/distance-tiers/<int:tier_id>', methods=['PUT'])
def update_distance_tier(tier_id):
    """Update a distance tier."""
    if not session.get('logged_in') or session.get('user_type') != 'employee':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    if session.get('employee_role') != 'KWETU_ADMIN':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    data = request.get_json()
    start_km = float(data.get('start_km', 0))
    end_km = float(data.get('end_km', 0))
    price_per_km = float(data.get('price_per_km', 0))
    
    # Validate
    is_valid, message = validate_distance_tier(start_km, end_km, tier_id)
    if not is_valid:
        return jsonify({'success': False, 'message': message}), 400
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE delivery_distance_tiers 
                SET start_km = %s, end_km = %s, price_per_km = %s
                WHERE id = %s
            """, (start_km, end_km, price_per_km, tier_id))
            connection.commit()
            return jsonify({'success': True, 'message': 'Distance tier updated successfully'})
    except Exception as e:
        print(f"Error updating distance tier: {e}")
        return jsonify({'success': False, 'message': 'Error updating tier'}), 500
    finally:
        connection.close()

@app.route('/api/admin/delivery-settings/distance-tiers/<int:tier_id>', methods=['DELETE'])
def delete_distance_tier(tier_id):
    """Delete a distance tier."""
    if not session.get('logged_in') or session.get('user_type') != 'employee':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    if session.get('employee_role') != 'KWETU_ADMIN':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM delivery_distance_tiers WHERE id = %s", (tier_id,))
            connection.commit()
            return jsonify({'success': True, 'message': 'Distance tier deleted successfully'})
    except Exception as e:
        print(f"Error deleting distance tier: {e}")
        return jsonify({'success': False, 'message': 'Error deleting tier'}), 500
    finally:
        connection.close()

@app.route('/api/admin/delivery-settings/weight-tiers', methods=['GET'])
def get_weight_tiers():
    """Get weight tiers."""
    if not session.get('logged_in') or session.get('user_type') != 'employee':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    if session.get('employee_role') != 'KWETU_ADMIN':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM delivery_weight_tiers ORDER BY min_kg ASC")
            tiers = cursor.fetchall()
            return jsonify({'success': True, 'tiers': tiers})
    except Exception as e:
        print(f"Error fetching weight tiers: {e}")
        return jsonify({'success': False, 'message': 'Error fetching tiers'}), 500
    finally:
        connection.close()

def validate_weight_tier(min_kg, max_kg, exclude_id=None):
    """Validate that weight tier doesn't overlap with existing tiers."""
    connection = get_db_connection()
    if not connection:
        return False, 'Database connection error'
    
    try:
        with connection.cursor() as cursor:
            if min_kg >= max_kg:
                return False, 'Min KG must be less than Max KG'
            
            # Check for overlaps (allow adjacent tiers where one tier's end equals another's start)
            # Overlap occurs when ranges actually overlap, not just touch
            if exclude_id:
                cursor.execute("""
                    SELECT id FROM delivery_weight_tiers 
                    WHERE id != %s AND (
                        (min_kg < %s AND max_kg > %s) OR
                        (min_kg < %s AND max_kg > %s) OR
                        (min_kg >= %s AND max_kg <= %s)
                    )
                """, (exclude_id, min_kg, min_kg, max_kg, max_kg, min_kg, max_kg))
            else:
                cursor.execute("""
                    SELECT id FROM delivery_weight_tiers 
                    WHERE (
                        (min_kg < %s AND max_kg > %s) OR
                        (min_kg < %s AND max_kg > %s) OR
                        (min_kg >= %s AND max_kg <= %s)
                    )
                """, (min_kg, min_kg, max_kg, max_kg, min_kg, max_kg))
            
            overlapping = cursor.fetchone()
            if overlapping:
                return False, 'This tier overlaps with an existing tier'
            
            return True, 'Valid'
    except Exception as e:
        print(f"Error validating weight tier: {e}")
        return False, str(e)
    finally:
        connection.close()

@app.route('/api/admin/delivery-settings/weight-tiers', methods=['POST'])
def add_weight_tier():
    """Add a weight tier."""
    if not session.get('logged_in') or session.get('user_type') != 'employee':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    if session.get('employee_role') != 'KWETU_ADMIN':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    data = request.get_json()
    min_kg = float(data.get('min_kg', 0))
    max_kg = float(data.get('max_kg', 0))
    fee_amount = float(data.get('fee_amount', 0))
    
    # Validate
    is_valid, message = validate_weight_tier(min_kg, max_kg)
    if not is_valid:
        return jsonify({'success': False, 'message': message}), 400
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO delivery_weight_tiers (min_kg, max_kg, fee_amount)
                VALUES (%s, %s, %s)
            """, (min_kg, max_kg, fee_amount))
            connection.commit()
            return jsonify({'success': True, 'message': 'Weight tier added successfully'})
    except Exception as e:
        print(f"Error adding weight tier: {e}")
        return jsonify({'success': False, 'message': 'Error adding tier'}), 500
    finally:
        connection.close()

@app.route('/api/admin/delivery-settings/weight-tiers/<int:tier_id>', methods=['PUT'])
def update_weight_tier(tier_id):
    """Update a weight tier."""
    if not session.get('logged_in') or session.get('user_type') != 'employee':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    if session.get('employee_role') != 'KWETU_ADMIN':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    data = request.get_json()
    min_kg = float(data.get('min_kg', 0))
    max_kg = float(data.get('max_kg', 0))
    fee_amount = float(data.get('fee_amount', 0))
    
    # Validate
    is_valid, message = validate_weight_tier(min_kg, max_kg, tier_id)
    if not is_valid:
        return jsonify({'success': False, 'message': message}), 400
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE delivery_weight_tiers 
                SET min_kg = %s, max_kg = %s, fee_amount = %s
                WHERE id = %s
            """, (min_kg, max_kg, fee_amount, tier_id))
            connection.commit()
            return jsonify({'success': True, 'message': 'Weight tier updated successfully'})
    except Exception as e:
        print(f"Error updating weight tier: {e}")
        return jsonify({'success': False, 'message': 'Error updating tier'}), 500
    finally:
        connection.close()

@app.route('/api/admin/delivery-settings/weight-tiers/<int:tier_id>', methods=['DELETE'])
def delete_weight_tier(tier_id):
    """Delete a weight tier."""
    if not session.get('logged_in') or session.get('user_type') != 'employee':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    if session.get('employee_role') != 'KWETU_ADMIN':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM delivery_weight_tiers WHERE id = %s", (tier_id,))
            connection.commit()
            return jsonify({'success': True, 'message': 'Weight tier deleted successfully'})
    except Exception as e:
        print(f"Error deleting weight tier: {e}")
        return jsonify({'success': False, 'message': 'Error deleting tier'}), 500
    finally:
        connection.close()

# Peak Hours API
@app.route('/api/admin/delivery-settings/peak-hours', methods=['GET'])
def get_peak_hours():
    """Get peak hours."""
    if not session.get('logged_in') or session.get('user_type') != 'employee':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    if session.get('employee_role') != 'KWETU_ADMIN':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM delivery_peak_hours ORDER BY start_time ASC")
            peak_hours_raw = cursor.fetchall()
            
            # Convert time fields to strings
            peak_hours = []
            for peak in peak_hours_raw:
                peak_dict = dict(peak)
                peak_dict['start_time'] = convert_time_to_string(peak_dict.get('start_time'))
                peak_dict['end_time'] = convert_time_to_string(peak_dict.get('end_time'))
                peak_hours.append(peak_dict)
            
            return jsonify({'success': True, 'peak_hours': peak_hours})
    except Exception as e:
        print(f"Error fetching peak hours: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Error fetching peak hours'}), 500
    finally:
        connection.close()

def validate_time_range(start_time, end_time, exclude_id=None, table='delivery_peak_hours'):
    """Validate that time range doesn't overlap with existing ranges."""
    connection = get_db_connection()
    if not connection:
        return False, 'Database connection error'
    
    try:
        with connection.cursor() as cursor:
            from datetime import datetime, time
            
            start = datetime.strptime(start_time, '%H:%M').time()
            end = datetime.strptime(end_time, '%H:%M').time()
            
            # Allow ranges that cross midnight (start > end) or normal ranges (start < end)
            # Only reject if start == end (zero-length range)
            if start == end:
                return False, 'Start time cannot equal End time'
            
            # Get all existing ranges
            if exclude_id:
                cursor.execute(f"SELECT id, start_time, end_time FROM {table} WHERE id != %s", (exclude_id,))
            else:
                cursor.execute(f"SELECT id, start_time, end_time FROM {table}")
            
            existing_ranges = cursor.fetchall()
            
            for existing_range in existing_ranges:
                existing_id = existing_range['id']
                existing_start_str = str(existing_range['start_time'])
                existing_end_str = str(existing_range['end_time'])
                
                # Parse existing times
                if ':' in existing_start_str:
                    existing_start = datetime.strptime(existing_start_str.split('.')[0], '%H:%M:%S').time() if '.' in existing_start_str else datetime.strptime(existing_start_str, '%H:%M:%S').time()
                else:
                    existing_start = datetime.strptime(existing_start_str, '%H:%M').time()
                
                if ':' in existing_end_str:
                    existing_end = datetime.strptime(existing_end_str.split('.')[0], '%H:%M:%S').time() if '.' in existing_end_str else datetime.strptime(existing_end_str, '%H:%M:%S').time()
                else:
                    existing_end = datetime.strptime(existing_end_str, '%H:%M').time()
                
                # Check for overlap
                # Case 1: Both ranges are normal (don't cross midnight)
                if start <= end and existing_start <= existing_end:
                    if not (end <= existing_start or start >= existing_end):
                        return False, 'This time range overlaps with an existing range'
                
                # Case 2: New range crosses midnight, existing doesn't
                elif start > end and existing_start <= existing_end:
                    if not (end <= existing_start and start >= existing_end):
                        return False, 'This time range overlaps with an existing range'
                
                # Case 3: Existing range crosses midnight, new doesn't
                elif start <= end and existing_start > existing_end:
                    if not (end <= existing_start and start >= existing_end):
                        return False, 'This time range overlaps with an existing range'
                
                # Case 4: Both ranges cross midnight
                elif start > end and existing_start > existing_end:
                    # Both cross midnight, they always overlap
                    return False, 'This time range overlaps with an existing range'
            
            return True, 'Valid'
    except Exception as e:
        print(f"Error validating time range: {e}")
        import traceback
        traceback.print_exc()
        return False, str(e)
    finally:
        connection.close()

@app.route('/api/admin/delivery-settings/peak-hours', methods=['POST'])
def add_peak_hour():
    """Add a peak hour range."""
    if not session.get('logged_in') or session.get('user_type') != 'employee':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    if session.get('employee_role') != 'KWETU_ADMIN':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    data = request.get_json()
    start_time = data.get('start_time', '')
    end_time = data.get('end_time', '')
    percentage_increase = float(data.get('percentage_increase', 0))
    
    # Validate
    is_valid, message = validate_time_range(start_time, end_time, table='delivery_peak_hours')
    if not is_valid:
        return jsonify({'success': False, 'message': message}), 400
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO delivery_peak_hours (start_time, end_time, percentage_increase)
                VALUES (%s, %s, %s)
            """, (start_time, end_time, percentage_increase))
            connection.commit()
            return jsonify({'success': True, 'message': 'Peak hour range added successfully'})
    except Exception as e:
        print(f"Error adding peak hour: {e}")
        return jsonify({'success': False, 'message': 'Error adding peak hour range'}), 500
    finally:
        connection.close()

@app.route('/api/admin/delivery-settings/peak-hours/<int:hour_id>', methods=['PUT'])
def update_peak_hour(hour_id):
    """Update a peak hour range."""
    if not session.get('logged_in') or session.get('user_type') != 'employee':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    if session.get('employee_role') != 'KWETU_ADMIN':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    data = request.get_json()
    start_time = data.get('start_time', '')
    end_time = data.get('end_time', '')
    percentage_increase = float(data.get('percentage_increase', 0))
    
    # Validate
    is_valid, message = validate_time_range(start_time, end_time, hour_id, 'delivery_peak_hours')
    if not is_valid:
        return jsonify({'success': False, 'message': message}), 400
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE delivery_peak_hours 
                SET start_time = %s, end_time = %s, percentage_increase = %s
                WHERE id = %s
            """, (start_time, end_time, percentage_increase, hour_id))
            connection.commit()
            return jsonify({'success': True, 'message': 'Peak hour range updated successfully'})
    except Exception as e:
        print(f"Error updating peak hour: {e}")
        return jsonify({'success': False, 'message': 'Error updating peak hour range'}), 500
    finally:
        connection.close()

@app.route('/api/admin/delivery-settings/peak-hours/<int:hour_id>', methods=['DELETE'])
def delete_peak_hour(hour_id):
    """Delete a peak hour range."""
    if not session.get('logged_in') or session.get('user_type') != 'employee':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    if session.get('employee_role') != 'KWETU_ADMIN':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM delivery_peak_hours WHERE id = %s", (hour_id,))
            connection.commit()
            return jsonify({'success': True, 'message': 'Peak hour range deleted successfully'})
    except Exception as e:
        print(f"Error deleting peak hour: {e}")
        return jsonify({'success': False, 'message': 'Error deleting peak hour range'}), 500
    finally:
        connection.close()

# Night Hours API
@app.route('/api/admin/delivery-settings/night-hours', methods=['GET'])
def get_night_hours():
    """Get night hours."""
    if not session.get('logged_in') or session.get('user_type') != 'employee':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    if session.get('employee_role') != 'KWETU_ADMIN':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM delivery_night_hours ORDER BY start_time ASC")
            night_hours_raw = cursor.fetchall()
            
            # Convert time fields to strings
            night_hours = []
            for night in night_hours_raw:
                night_dict = dict(night)
                night_dict['start_time'] = convert_time_to_string(night_dict.get('start_time'))
                night_dict['end_time'] = convert_time_to_string(night_dict.get('end_time'))
                night_hours.append(night_dict)
            
            return jsonify({'success': True, 'night_hours': night_hours})
    except Exception as e:
        print(f"Error fetching night hours: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Error fetching night hours'}), 500
    finally:
        connection.close()

@app.route('/api/admin/delivery-settings/night-hours', methods=['POST'])
def add_night_hour():
    """Add a night hour range."""
    if not session.get('logged_in') or session.get('user_type') != 'employee':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    if session.get('employee_role') != 'KWETU_ADMIN':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    data = request.get_json()
    start_time = data.get('start_time', '')
    end_time = data.get('end_time', '')
    night_percentage = float(data.get('night_percentage', 0))
    
    # Validate
    is_valid, message = validate_time_range(start_time, end_time, table='delivery_night_hours')
    if not is_valid:
        return jsonify({'success': False, 'message': message}), 400
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO delivery_night_hours (start_time, end_time, night_percentage)
                VALUES (%s, %s, %s)
            """, (start_time, end_time, night_percentage))
            connection.commit()
            return jsonify({'success': True, 'message': 'Night hour range added successfully'})
    except Exception as e:
        print(f"Error adding night hour: {e}")
        return jsonify({'success': False, 'message': 'Error adding night hour range'}), 500
    finally:
        connection.close()

@app.route('/api/admin/delivery-settings/night-hours/<int:hour_id>', methods=['PUT'])
def update_night_hour(hour_id):
    """Update a night hour range."""
    if not session.get('logged_in') or session.get('user_type') != 'employee':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    if session.get('employee_role') != 'KWETU_ADMIN':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    data = request.get_json()
    start_time = data.get('start_time', '')
    end_time = data.get('end_time', '')
    night_percentage = float(data.get('night_percentage', 0))
    
    # Validate
    is_valid, message = validate_time_range(start_time, end_time, hour_id, 'delivery_night_hours')
    if not is_valid:
        return jsonify({'success': False, 'message': message}), 400
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE delivery_night_hours 
                SET start_time = %s, end_time = %s, night_percentage = %s
                WHERE id = %s
            """, (start_time, end_time, night_percentage, hour_id))
            connection.commit()
            return jsonify({'success': True, 'message': 'Night hour range updated successfully'})
    except Exception as e:
        print(f"Error updating night hour: {e}")
        return jsonify({'success': False, 'message': 'Error updating night hour range'}), 500
    finally:
        connection.close()

@app.route('/api/admin/delivery-settings/night-hours/<int:hour_id>', methods=['DELETE'])
def delete_night_hour(hour_id):
    """Delete a night hour range."""
    if not session.get('logged_in') or session.get('user_type') != 'employee':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    if session.get('employee_role') != 'KWETU_ADMIN':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM delivery_night_hours WHERE id = %s", (hour_id,))
            connection.commit()
            return jsonify({'success': True, 'message': 'Night hour range deleted successfully'})
    except Exception as e:
        print(f"Error deleting night hour: {e}")
        return jsonify({'success': False, 'message': 'Error deleting night hour range'}), 500
    finally:
        connection.close()

@app.route('/api/admin/delivery-settings/calculate', methods=['POST'])
def calculate_delivery_cost_api():
    """Calculate delivery cost using the formula."""
    data = request.get_json()
    
    # Distance is required
    distance_km = data.get('distance_km')
    if distance_km is None or distance_km == '':
        return jsonify({'success': False, 'message': 'Distance is required'}), 400
    
    try:
        distance_km = float(distance_km)
        if distance_km <= 0:
            return jsonify({'success': False, 'message': 'Distance must be greater than 0'}), 400
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Invalid distance value'}), 400
    
    # Weight is optional (default to 0)
    weight_kg = 0
    if data.get('weight_kg') is not None and data.get('weight_kg') != '':
        try:
            weight_kg = float(data.get('weight_kg', 0))
            if weight_kg < 0:
                weight_kg = 0
        except (ValueError, TypeError):
            weight_kg = 0
    
    # Tip is optional (default to 0)
    tip = 0
    if data.get('tip') is not None and data.get('tip') != '':
        try:
            tip = float(data.get('tip', 0))
            if tip < 0:
                tip = 0
        except (ValueError, TypeError):
            tip = 0
    
    # Delivery time defaults to current time if not provided
    delivery_time = data.get('delivery_time')
    if not delivery_time or delivery_time == '':
        from datetime import datetime
        delivery_time = datetime.now().strftime('%H:%M')
    
    is_weather = data.get('is_weather', False)
    is_priority = data.get('is_priority', False)
    
    result = calculate_delivery_cost(distance_km, weight_kg, is_weather, is_priority, tip, delivery_time)
    
    if result:
        return jsonify({'success': True, 'cost': result})
    else:
        return jsonify({'success': False, 'message': 'Error calculating cost'}), 500

@app.route('/dashboard/shop/items')
def shop_items():
    """Shop items management page."""
    if not session.get('logged_in') or session.get('user_type') != 'shop':
        return redirect('/')
    
    shop_id = session.get('shop_id')
    if not shop_id:
        return redirect('/')
    
    connection = get_db_connection()
    shop = None
    if connection:
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, name, category, email, phone, login_code, profile_image, 
                           status, rating, created_at
                    FROM shops
                    WHERE id = %s
                """, (shop_id,))
                shop = cursor.fetchone()
        except Exception as e:
            print(f"Error fetching shop: {e}")
        finally:
            connection.close()
    
    if not shop:
        session.clear()
        return redirect('/')
    
    return render_template('shop_items.html', shop=shop)

@app.route('/api/shop/items/register', methods=['POST'])
def register_shop_item():
    """Register a new shop item."""
    if not session.get('logged_in') or session.get('user_type') != 'shop':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    shop_id = session.get('shop_id')
    if not shop_id:
        return jsonify({'success': False, 'message': 'Shop ID not found in session'}), 400

    try:
        # Get form data
        category = request.form.get('category', '').strip().upper()
        item_name = request.form.get('item_name', '').strip().upper()
        description = request.form.get('description', '').strip().upper()
        price = request.form.get('price', '').strip()
        discount_price = request.form.get('discount_price', '').strip() or None

        # Validate required fields
        if not all([category, item_name, description, price]):
            return jsonify({'success': False, 'message': 'All required fields must be filled'}), 400

        # Validate price
        try:
            price = float(price)
            if price < 0:
                return jsonify({'success': False, 'message': 'Price must be a positive number'}), 400
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid price format'}), 400

        # Validate discount price if provided
        if discount_price:
            try:
                discount_price = float(discount_price)
                if discount_price < 0:
                    return jsonify({'success': False, 'message': 'Discount price must be a positive number'}), 400
                if discount_price >= price:
                    return jsonify({'success': False, 'message': 'Discount price must be less than regular price'}), 400
            except ValueError:
                return jsonify({'success': False, 'message': 'Invalid discount price format'}), 400

        # Handle image upload
        item_image = None
        if 'item_image' in request.files:
            file = request.files['item_image']
            if file.filename:
                # Validate file type
                allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
                file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
                if file_ext not in allowed_extensions:
                    return jsonify({'success': False, 'message': 'Invalid image format. Allowed: PNG, JPG, JPEG, GIF, WEBP'}), 400

                # Save file
                item_image = save_uploaded_file(file, 'items')
                if not item_image:
                    return jsonify({'success': False, 'message': 'Failed to upload image'}), 400
            else:
                return jsonify({'success': False, 'message': 'Item image is required'}), 400
        else:
            return jsonify({'success': False, 'message': 'Item image is required'}), 400

        # Check if shop_items table exists, create if not
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection error'}), 500

        try:
            with connection.cursor() as cursor:
                # Check if table exists
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM information_schema.tables
                    WHERE table_schema = DATABASE()
                    AND table_name = 'shop_items'
                """)
                table_exists = cursor.fetchone()['count'] > 0

                if not table_exists:
                    # Create shop_items table
                    cursor.execute("""
                        CREATE TABLE shop_items (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            shop_id INT NOT NULL,
                            category VARCHAR(100) NOT NULL,
                            item_name VARCHAR(255) NOT NULL,
                            description TEXT,
                            price DECIMAL(10, 2) NOT NULL,
                            discount_price DECIMAL(10, 2) NULL,
                            item_image VARCHAR(255),
                            status ENUM('active', 'inactive', 'out_of_stock') DEFAULT 'active',
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                            INDEX idx_shop_id (shop_id),
                            INDEX idx_category (category),
                            INDEX idx_status (status),
                            FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """)
                    connection.commit()

                # Insert item
                cursor.execute("""
                    INSERT INTO shop_items (shop_id, category, item_name, description, price, discount_price, item_image, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'active')
                """, (shop_id, category, item_name, description, price, discount_price, item_image))
                connection.commit()

                return jsonify({
                    'success': True,
                    'message': 'Item registered successfully!'
                })
        except pymysql.IntegrityError as e:
            connection.rollback()
            print(f"Integrity error: {e}")
            return jsonify({'success': False, 'message': 'Failed to register item. Please try again.'}), 400
        except Exception as e:
            connection.rollback()
            print(f"Error registering item: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'message': 'Failed to register item. Please try again.'}), 500
        finally:
            connection.close()
    except Exception as e:
        print(f"Error in register_shop_item: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'An error occurred'}), 500

@app.route('/dashboard/shop/items/management')
def shop_items_management():
    """Shop items management page - displays all registered items."""
    if not session.get('logged_in') or session.get('user_type') != 'shop':
        return redirect('/')

    shop_id = session.get('shop_id')
    if not shop_id:
        return redirect('/')

    connection = get_db_connection()
    shop = None
    items = []
    error = None

    if connection:
        try:
            with connection.cursor() as cursor:
                # Fetch shop details
                cursor.execute("""
                    SELECT id, name, category, email, phone, login_code, profile_image, 
                           status, rating, created_at
                    FROM shops
                    WHERE id = %s
                """, (shop_id,))
                shop = cursor.fetchone()

                if shop:
                    # Fetch all items for this shop
                    cursor.execute("""
                        SELECT id, category, item_name, description, price, discount_price, 
                               item_image, status, created_at, updated_at
                        FROM shop_items
                        WHERE shop_id = %s
                        ORDER BY created_at DESC
                    """, (shop_id,))
                    items = cursor.fetchall()
        except Exception as e:
            print(f"Error fetching items: {e}")
            import traceback
            traceback.print_exc()
            error = 'Error loading items'
        finally:
            connection.close()
    else:
        error = 'Database connection error'

    if not shop:
        session.clear()
        return redirect('/')

    return render_template('shop_items_management.html', shop=shop, items=items, error=error)

@app.route('/api/shop/items/<int:item_id>', methods=['GET'])
def get_shop_item(item_id):
    """Get shop item details for editing."""
    if not session.get('logged_in') or session.get('user_type') != 'shop':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    shop_id = session.get('shop_id')
    if not shop_id:
        return jsonify({'success': False, 'message': 'Shop ID not found in session'}), 400

    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, category, item_name, description, price, discount_price, item_image, status
                FROM shop_items
                WHERE id = %s AND shop_id = %s
            """, (item_id, shop_id))
            item = cursor.fetchone()

            if not item:
                return jsonify({'success': False, 'message': 'Item not found'}), 404

            return jsonify({
                'success': True,
                'item': {
                    'id': item['id'],
                    'category': item['category'],
                    'item_name': item['item_name'],
                    'description': item['description'],
                    'price': float(item['price']),
                    'discount_price': float(item['discount_price']) if item['discount_price'] else None,
                    'item_image': item['item_image'],
                    'status': item['status']
                }
            })
    except Exception as e:
        print(f"Error fetching item: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Error fetching item'}), 500
    finally:
        connection.close()

@app.route('/api/shop/items/<int:item_id>', methods=['PUT'])
def update_shop_item(item_id):
    """Update shop item details."""
    if not session.get('logged_in') or session.get('user_type') != 'shop':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    shop_id = session.get('shop_id')
    if not shop_id:
        return jsonify({'success': False, 'message': 'Shop ID not found in session'}), 400

    try:
        # Get form data
        category = request.form.get('category', '').strip().upper()
        item_name = request.form.get('item_name', '').strip().upper()
        description = request.form.get('description', '').strip().upper()
        price = request.form.get('price', '').strip()
        discount_price = request.form.get('discount_price', '').strip() or None

        # Validate required fields
        if not all([category, item_name, description, price]):
            return jsonify({'success': False, 'message': 'All required fields must be filled'}), 400

        # Validate price
        try:
            price = float(price)
            if price < 0:
                return jsonify({'success': False, 'message': 'Price must be a positive number'}), 400
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid price format'}), 400

        # Validate discount price if provided
        if discount_price:
            try:
                discount_price = float(discount_price)
                if discount_price < 0:
                    return jsonify({'success': False, 'message': 'Discount price must be a positive number'}), 400
                if discount_price >= price:
                    return jsonify({'success': False, 'message': 'Discount price must be less than regular price'}), 400
            except ValueError:
                return jsonify({'success': False, 'message': 'Invalid discount price format'}), 400

        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection error'}), 500

        try:
            with connection.cursor() as cursor:
                # Check if item belongs to shop
                cursor.execute("SELECT id, item_image FROM shop_items WHERE id = %s AND shop_id = %s", (item_id, shop_id))
                existing_item = cursor.fetchone()
                
                if not existing_item:
                    return jsonify({'success': False, 'message': 'Item not found'}), 404

                # Handle image upload if new image provided
                item_image = existing_item['item_image']
                if 'item_image' in request.files:
                    file = request.files['item_image']
                    if file.filename:
                        # Validate file type
                        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
                        file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
                        if file_ext not in allowed_extensions:
                            return jsonify({'success': False, 'message': 'Invalid image format. Allowed: PNG, JPG, JPEG, GIF, WEBP'}), 400

                        # Save new file
                        item_image = save_uploaded_file(file, 'items')
                        if not item_image:
                            return jsonify({'success': False, 'message': 'Failed to upload image'}), 400

                # Update item
                cursor.execute("""
                    UPDATE shop_items
                    SET category = %s, item_name = %s, description = %s, price = %s, 
                        discount_price = %s, item_image = %s, updated_at = NOW()
                    WHERE id = %s AND shop_id = %s
                """, (category, item_name, description, price, discount_price, item_image, item_id, shop_id))
                connection.commit()

                return jsonify({
                    'success': True,
                    'message': 'Item updated successfully!'
                })
        except Exception as e:
            connection.rollback()
            print(f"Error updating item: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'message': 'Failed to update item'}), 500
        finally:
            connection.close()
    except Exception as e:
        print(f"Error in update_shop_item: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'An error occurred'}), 500

@app.route('/api/shop/items/<int:item_id>', methods=['DELETE'])
def delete_shop_item(item_id):
    """Delete a shop item."""
    if not session.get('logged_in') or session.get('user_type') != 'shop':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    shop_id = session.get('shop_id')
    if not shop_id:
        return jsonify({'success': False, 'message': 'Shop ID not found in session'}), 400

    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500

    try:
        with connection.cursor() as cursor:
            # Check if item belongs to shop
            cursor.execute("SELECT id FROM shop_items WHERE id = %s AND shop_id = %s", (item_id, shop_id))
            item = cursor.fetchone()
            
            if not item:
                return jsonify({'success': False, 'message': 'Item not found'}), 404

            # Delete item
            cursor.execute("DELETE FROM shop_items WHERE id = %s AND shop_id = %s", (item_id, shop_id))
            connection.commit()

            return jsonify({
                'success': True,
                'message': 'Item deleted successfully!'
            })
    except Exception as e:
        connection.rollback()
        print(f"Error deleting item: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Failed to delete item'}), 500
    finally:
        connection.close()

@app.route('/api/shop/items/<int:item_id>/toggle-status', methods=['POST'])
def toggle_item_status(item_id):
    """Toggle item status (active/inactive/out_of_stock)."""
    if not session.get('logged_in') or session.get('user_type') != 'shop':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    shop_id = session.get('shop_id')
    if not shop_id:
        return jsonify({'success': False, 'message': 'Shop ID not found in session'}), 400

    try:
        data = request.get_json()
        new_status = data.get('status', '').strip().lower()

        if new_status not in ['active', 'inactive', 'out_of_stock']:
            return jsonify({'success': False, 'message': 'Invalid status'}), 400

        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection error'}), 500

        try:
            with connection.cursor() as cursor:
                # Check if item belongs to shop
                cursor.execute("SELECT id, status FROM shop_items WHERE id = %s AND shop_id = %s", (item_id, shop_id))
                item = cursor.fetchone()
                
                if not item:
                    return jsonify({'success': False, 'message': 'Item not found'}), 404

                # Update status
                cursor.execute("""
                    UPDATE shop_items
                    SET status = %s, updated_at = NOW()
                    WHERE id = %s AND shop_id = %s
                """, (new_status, item_id, shop_id))
                connection.commit()

                return jsonify({
                    'success': True,
                    'message': f'Item status updated to {new_status}',
                    'status': new_status
                })
        except Exception as e:
            connection.rollback()
            print(f"Error updating status: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'message': 'Failed to update status'}), 500
        finally:
            connection.close()
    except Exception as e:
        print(f"Error in toggle_item_status: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'An error occurred'}), 500

@app.route('/dashboard/shop/items/settings')
def shop_items_settings():
    """Shop items settings page."""
    if not session.get('logged_in') or session.get('user_type') != 'shop':
        return redirect('/')

    shop_id = session.get('shop_id')
    if not shop_id:
        return redirect('/')

    connection = get_db_connection()
    shop = None
    if connection:
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, name, category, email, phone, login_code, profile_image, 
                           status, rating, created_at
                    FROM shops
                    WHERE id = %s
                """, (shop_id,))
                shop = cursor.fetchone()
        except Exception as e:
            print(f"Error fetching shop: {e}")
        finally:
            connection.close()

    if not shop:
        session.clear()
        return redirect('/')

    return render_template('shop_items_settings.html', shop=shop)

@app.route('/dashboard/shop/settings')
def shop_settings():
    """Shop settings page."""
    if not session.get('logged_in') or session.get('user_type') != 'shop':
        return redirect('/')

    shop_id = session.get('shop_id')
    if not shop_id:
        return redirect('/')

    connection = get_db_connection()
    shop = None
    if connection:
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, name, category, email, phone, login_code, profile_image, 
                           status, rating, created_at, location_name, longitude, latitude
                    FROM shops
                    WHERE id = %s
                """, (shop_id,))
                shop = cursor.fetchone()
        except Exception as e:
            print(f"Error fetching shop: {e}")
        finally:
            connection.close()

    if not shop:
        session.clear()
        return redirect('/')

    return render_template('shop_settings.html', shop=shop)

# Shop Order Settings API
@app.route('/api/shop/order-settings', methods=['GET'])
def get_shop_order_settings():
    """Get shop order settings."""
    if not session.get('logged_in') or session.get('user_type') != 'shop':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    shop_id = session.get('shop_id')
    if not shop_id:
        return jsonify({'success': False, 'message': 'Shop not found'}), 404
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    
    try:
        with connection.cursor() as cursor:
            # Get order settings
            cursor.execute("""
                SELECT auto_confirm_order, order_processing_time, max_daily_orders, 
                       allow_scheduled_orders, custom_delay_message
                FROM shop_order_settings
                WHERE shop_id = %s
            """, (shop_id,))
            settings = cursor.fetchone()
            
            # Get peak hours
            cursor.execute("""
                SELECT id, start_time, end_time
                FROM shop_peak_hours
                WHERE shop_id = %s
                ORDER BY start_time ASC
            """, (shop_id,))
            peak_hours = cursor.fetchall()
            
            # Convert time fields to strings
            peak_hours_list = []
            for peak in peak_hours:
                peak_dict = dict(peak)
                peak_dict['start_time'] = convert_time_to_string(peak_dict.get('start_time'))
                peak_dict['end_time'] = convert_time_to_string(peak_dict.get('end_time'))
                peak_hours_list.append(peak_dict)
            
            # Convert settings to dict if it exists, otherwise use defaults
            if settings:
                settings_dict = {
                    'auto_confirm_order': bool(settings.get('auto_confirm_order', 0)),
                    'order_processing_time': int(settings.get('order_processing_time', 30)),
                    'max_daily_orders': settings.get('max_daily_orders'),
                    'allow_scheduled_orders': bool(settings.get('allow_scheduled_orders', 0)),
                    'custom_delay_message': settings.get('custom_delay_message') or 'Orders placed now may take longer due to high demand'
                }
            else:
                settings_dict = {
                    'auto_confirm_order': False,
                    'order_processing_time': 30,
                    'max_daily_orders': None,
                    'allow_scheduled_orders': False,
                    'custom_delay_message': 'Orders placed now may take longer due to high demand'
                }
            
            return jsonify({
                'success': True,
                'settings': settings_dict,
                'peak_hours': peak_hours_list
            })
    except Exception as e:
        print(f"Error fetching shop order settings: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Error fetching settings'}), 500
    finally:
        connection.close()

@app.route('/api/shop/order-settings', methods=['POST'])
def save_shop_order_settings():
    """Save shop order settings."""
    if not session.get('logged_in') or session.get('user_type') != 'shop':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    shop_id = session.get('shop_id')
    if not shop_id:
        return jsonify({'success': False, 'message': 'Shop not found'}), 404
    
    data = request.get_json()
    auto_confirm = data.get('auto_confirm_order', False)
    processing_time = int(data.get('order_processing_time', 30))
    max_daily = data.get('max_daily_orders')
    allow_scheduled = data.get('allow_scheduled_orders', False)
    delay_message = data.get('custom_delay_message', '')
    peak_hours = data.get('peak_hours', [])
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    
    try:
        with connection.cursor() as cursor:
            # Check if settings exist
            cursor.execute("SELECT id FROM shop_order_settings WHERE shop_id = %s", (shop_id,))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing settings
                cursor.execute("""
                    UPDATE shop_order_settings 
                    SET auto_confirm_order = %s,
                        order_processing_time = %s,
                        max_daily_orders = %s,
                        allow_scheduled_orders = %s,
                        custom_delay_message = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE shop_id = %s
                """, (auto_confirm, processing_time, max_daily, allow_scheduled, delay_message, shop_id))
            else:
                # Insert new settings
                cursor.execute("""
                    INSERT INTO shop_order_settings 
                    (shop_id, auto_confirm_order, order_processing_time, max_daily_orders, 
                     allow_scheduled_orders, custom_delay_message)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (shop_id, auto_confirm, processing_time, max_daily, allow_scheduled, delay_message))
            
            # Delete existing peak hours
            cursor.execute("DELETE FROM shop_peak_hours WHERE shop_id = %s", (shop_id,))
            
            # Insert new peak hours
            for peak in peak_hours:
                start_time = peak.get('start_time', '')
                end_time = peak.get('end_time', '')
                if start_time and end_time:
                    cursor.execute("""
                        INSERT INTO shop_peak_hours (shop_id, start_time, end_time)
                        VALUES (%s, %s, %s)
                    """, (shop_id, start_time, end_time))
            
            connection.commit()
            return jsonify({'success': True, 'message': 'Order settings saved successfully'})
    except Exception as e:
        connection.rollback()
        print(f"Error saving shop order settings: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Error saving settings'}), 500
    finally:
        connection.close()

@app.route('/dashboard/shop')
def shop_dashboard():
    """Shop dashboard page."""
    if not session.get('logged_in') or session.get('user_type') != 'shop':
        return redirect('/')
    
    # Get shop details
    shop_id = session.get('shop_id')
    if not shop_id:
        return redirect('/')
    
    connection = get_db_connection()
    shop = None
    orders = []
    error = None
    
    if connection:
        try:
            with connection.cursor() as cursor:
                # Get shop details
                cursor.execute("""
                    SELECT id, name, category, email, phone, login_code, profile_image, 
                           status, rating, created_at, latitude, longitude, location_name
                    FROM shops
                    WHERE id = %s
                """, (shop_id,))
                shop = cursor.fetchone()
                
                # Get all orders for this shop
                # Check which columns exist in orders table
                existing_cols = get_table_columns('orders')
                has_order_type = 'order_type' in existing_cols if existing_cols else False
                has_status = 'status' in existing_cols if existing_cols else False
                has_customer_id = 'customer_id' in existing_cols if existing_cols else False
                has_total_amount = 'total_amount' in existing_cols if existing_cols else False
                
                # Check if pickup_code and rider columns exist
                has_pickup_code = 'pickup_code' in existing_cols if existing_cols else False
                has_rider_name = 'rider_name' in existing_cols if existing_cols else False
                has_rider_phone = 'rider_phone' in existing_cols if existing_cols else False
                
                # Build query based on available columns
                if has_order_type and has_customer_id:
                    # New schema with order_type and customer_id
                    if has_status:
                        rider_fields = ""
                        if has_rider_name and has_rider_phone:
                            rider_fields = ", o.rider_name, o.rider_phone"
                        elif has_rider_name:
                            rider_fields = ", o.rider_name"
                        elif has_rider_phone:
                            rider_fields = ", o.rider_phone"
                        
                        pickup_field = ", o.pickup_code" if has_pickup_code else ""
                        
                        cursor.execute(f"""
                            SELECT o.id, o.order_number, o.order_type, o.status, o.total_amount as total,
                                   o.payment_method, o.payment_status, o.created_at{pickup_field}{rider_fields},
                                   c.name as customer_name, c.phone as customer_phone,
                                   oi.item_name, oi.quantity, oi.item_image
                            FROM orders o
                            LEFT JOIN customers c ON o.customer_id = c.id
                            LEFT JOIN order_items oi ON o.id = oi.order_id
                            WHERE o.shop_id = %s
                            ORDER BY o.created_at DESC
                            LIMIT 100
                        """, (shop_id,))
                    else:
                        rider_fields = ""
                        if has_rider_name and has_rider_phone:
                            rider_fields = ", o.rider_name, o.rider_phone"
                        elif has_rider_name:
                            rider_fields = ", o.rider_name"
                        elif has_rider_phone:
                            rider_fields = ", o.rider_phone"
                        
                        pickup_field = ", o.pickup_code" if has_pickup_code else ""
                        
                        cursor.execute(f"""
                            SELECT o.id, o.order_number, o.order_type, o.total_amount as total,
                                   o.payment_method, o.payment_status, o.created_at{pickup_field}{rider_fields},
                                   c.name as customer_name, c.phone as customer_phone,
                                   oi.item_name, oi.quantity, oi.item_image
                            FROM orders o
                            LEFT JOIN customers c ON o.customer_id = c.id
                            LEFT JOIN order_items oi ON o.id = oi.order_id
                            WHERE o.shop_id = %s
                            ORDER BY o.created_at DESC
                            LIMIT 100
                        """, (shop_id,))
                else:
                    # Old schema without order_type
                        rider_fields = ""
                        if has_rider_name and has_rider_phone:
                            rider_fields = ", o.rider_name, o.rider_phone"
                        elif has_rider_name:
                            rider_fields = ", o.rider_name"
                        elif has_rider_phone:
                            rider_fields = ", o.rider_phone"
                        
                        pickup_field = ", o.pickup_code" if has_pickup_code else ""
                        
                        cursor.execute(f"""
                            SELECT o.id, o.order_number, o.total,
                                   o.payment_method, o.payment_status, o.created_at{pickup_field}{rider_fields},
                                   o.customer_name, o.customer_phone,
                                   oi.item_name, oi.quantity, oi.item_image
                            FROM orders o
                            LEFT JOIN order_items oi ON o.id = oi.order_id
                            WHERE o.shop_id = %s
                            ORDER BY o.created_at DESC
                            LIMIT 100
                        """, (shop_id,))
                
                raw_orders = cursor.fetchall()
                
                # Get subtotal and delivery_fee columns if they exist
                existing_cols = get_table_columns('orders')
                has_subtotal = 'subtotal' in existing_cols if existing_cols else False
                has_delivery_fee = 'delivery_fee' in existing_cols if existing_cols else False
                
                # Group orders by order_id (since order_items creates multiple rows per order)
                orders_dict = {}
                for row in raw_orders:
                    order_id = row['id']
                    if order_id not in orders_dict:
                        # Calculate total without delivery cost
                        total_amount = float(row.get('total', 0) or row.get('total_amount', 0) or 0)
                        if has_subtotal and row.get('subtotal'):
                            total_amount = float(row.get('subtotal', 0))
                        elif has_delivery_fee and row.get('delivery_fee'):
                            total_amount = total_amount - float(row.get('delivery_fee', 0))
                        
                        orders_dict[order_id] = {
                            'id': order_id,
                            'order_number': row.get('order_number', f'ORD-{order_id}'),
                            'order_type': row.get('order_type', 'REGULAR'),
                            'status': row.get('status', 'pending'),
                            'total': total_amount,
                            'payment_method': row.get('payment_method', 'cash_on_delivery'),
                            'payment_status': row.get('payment_status', 'pending'),
                            'created_at': row.get('created_at'),
                            'customer_name': row.get('customer_name') or 'N/A',
                            'customer_phone': row.get('customer_phone') or 'N/A',
                            'pickup_code': row.get('pickup_code'),
                            'rider_name': row.get('rider_name'),
                            'rider_phone': row.get('rider_phone'),
                            'order_items': []  # Changed from 'items' to 'order_items' to avoid conflict with dict.items() method
                        }
                    
                    # Add item if exists
                    if row.get('item_name'):
                        orders_dict[order_id]['order_items'].append({
                            'name': row['item_name'],
                            'quantity': row.get('quantity', 1),
                            'image': row.get('item_image')
                        })
                
                orders = list(orders_dict.values())
                
                # Check if auto-confirm is enabled and auto-accept pending orders
                cursor.execute("""
                    SELECT auto_confirm_order
                    FROM shop_order_settings
                    WHERE shop_id = %s
                """, (shop_id,))
                settings = cursor.fetchone()
                auto_confirm_enabled = settings and settings.get('auto_confirm_order', 0) == 1
                
                if auto_confirm_enabled:
                    # Get all pending orders for this shop and update them to preparing
                    if has_status:
                        cursor.execute("""
                            UPDATE orders 
                            SET status = 'preparing', updated_at = NOW()
                            WHERE shop_id = %s AND status = 'pending'
                        """, (shop_id,))
                    if has_status:
                        connection.commit()
                        # Re-fetch and re-process orders to get updated statuses
                        # Re-check columns for the re-fetch
                        existing_cols = get_table_columns('orders')
                        has_rider_name = 'rider_name' in existing_cols if existing_cols else False
                        has_rider_phone = 'rider_phone' in existing_cols if existing_cols else False
                        
                        if has_order_type and has_customer_id:
                            if has_status:
                                rider_fields = ""
                                if has_rider_name and has_rider_phone:
                                    rider_fields = ", o.rider_name, o.rider_phone"
                                elif has_rider_name:
                                    rider_fields = ", o.rider_name"
                                elif has_rider_phone:
                                    rider_fields = ", o.rider_phone"
                                
                                pickup_field = ", o.pickup_code" if has_pickup_code else ""
                                
                                cursor.execute(f"""
                                    SELECT o.id, o.order_number, o.order_type, o.status, o.total_amount as total,
                                           o.payment_method, o.payment_status, o.created_at{pickup_field}{rider_fields},
                                           c.name as customer_name, c.phone as customer_phone,
                                           oi.item_name, oi.quantity, oi.item_image
                                    FROM orders o
                                    LEFT JOIN customers c ON o.customer_id = c.id
                                    LEFT JOIN order_items oi ON o.id = oi.order_id
                                    WHERE o.shop_id = %s
                                    ORDER BY o.created_at DESC
                                    LIMIT 100
                                """, (shop_id,))
                            else:
                                rider_fields = ""
                                if has_rider_name and has_rider_phone:
                                    rider_fields = ", o.rider_name, o.rider_phone"
                                elif has_rider_name:
                                    rider_fields = ", o.rider_name"
                                elif has_rider_phone:
                                    rider_fields = ", o.rider_phone"
                                
                                pickup_field = ", o.pickup_code" if has_pickup_code else ""
                                
                                cursor.execute(f"""
                                    SELECT o.id, o.order_number, o.order_type, o.total_amount as total,
                                           o.payment_method, o.payment_status, o.created_at{pickup_field}{rider_fields},
                                           c.name as customer_name, c.phone as customer_phone,
                                           oi.item_name, oi.quantity, oi.item_image
                                    FROM orders o
                                    LEFT JOIN customers c ON o.customer_id = c.id
                                    LEFT JOIN order_items oi ON o.id = oi.order_id
                                    WHERE o.shop_id = %s
                                    ORDER BY o.created_at DESC
                                    LIMIT 100
                                """, (shop_id,))
                        else:
                            rider_fields = ""
                            if has_rider_name and has_rider_phone:
                                rider_fields = ", o.rider_name, o.rider_phone"
                            elif has_rider_name:
                                rider_fields = ", o.rider_name"
                            elif has_rider_phone:
                                rider_fields = ", o.rider_phone"
                            
                            pickup_field = ", o.pickup_code" if has_pickup_code else ""
                            
                            cursor.execute(f"""
                                SELECT o.id, o.order_number, o.total,
                                       o.payment_method, o.payment_status, o.created_at{pickup_field}{rider_fields},
                                       o.customer_name, o.customer_phone,
                                       oi.item_name, oi.quantity, oi.item_image
                                FROM orders o
                                LEFT JOIN order_items oi ON o.id = oi.order_id
                                WHERE o.shop_id = %s
                                ORDER BY o.created_at DESC
                                LIMIT 100
                            """, (shop_id,))
                        
                        raw_orders = cursor.fetchall()
                        
                        # Re-group orders with updated statuses
                        orders_dict = {}
                        for row in raw_orders:
                            order_id = row['id']
                            if order_id not in orders_dict:
                                total_amount = float(row.get('total', 0) or row.get('total_amount', 0) or 0)
                                if has_subtotal and row.get('subtotal'):
                                    total_amount = float(row.get('subtotal', 0))
                                elif has_delivery_fee and row.get('delivery_fee'):
                                    total_amount = total_amount - float(row.get('delivery_fee', 0))
                                
                                orders_dict[order_id] = {
                                    'id': order_id,
                                    'order_number': row.get('order_number', f'ORD-{order_id}'),
                                    'order_type': row.get('order_type', 'REGULAR'),
                                    'status': row.get('status', 'pending'),
                                    'total': total_amount,
                                    'payment_method': row.get('payment_method', 'cash_on_delivery'),
                                    'payment_status': row.get('payment_status', 'pending'),
                                    'created_at': row.get('created_at'),
                                    'customer_name': row.get('customer_name') or 'N/A',
                                    'customer_phone': row.get('customer_phone') or 'N/A',
                                    'pickup_code': row.get('pickup_code'),
                                    'rider_name': row.get('rider_name'),
                                    'rider_phone': row.get('rider_phone'),
                                    'order_items': []
                                }
                            
                            if row.get('item_name'):
                                orders_dict[order_id]['order_items'].append({
                                    'name': row['item_name'],
                                    'quantity': row.get('quantity', 1),
                                    'image': row.get('item_image')
                                })
                        
                        orders = list(orders_dict.values())
                
        except Exception as e:
            print(f"Error fetching shop/orders: {e}")
            import traceback
            traceback.print_exc()
            error = 'Error loading orders'
        finally:
            connection.close()
    else:
        error = 'Database connection error'
    
    if not shop:
        session.clear()
        return redirect('/')
    
    return render_template('shop_dashboard.html', shop=shop, orders=orders, error=error)

@app.route('/api/shop/order-details/<int:order_id>', methods=['GET'])
def get_order_details(order_id):
    """Get detailed order information including items."""
    if not session.get('logged_in') or session.get('user_type') != 'shop':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    shop_id = session.get('shop_id')
    if not shop_id:
        return jsonify({'success': False, 'message': 'Shop not found'}), 404
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    
    try:
        with connection.cursor() as cursor:
            # Check which columns exist
            existing_cols = get_table_columns('orders')
            has_order_type = 'order_type' in existing_cols if existing_cols else False
            has_status = 'status' in existing_cols if existing_cols else False
            has_customer_id = 'customer_id' in existing_cols if existing_cols else False
            has_total_amount = 'total_amount' in existing_cols if existing_cols else False
            has_pickup_code = 'pickup_code' in existing_cols if existing_cols else False
            has_rider_name = 'rider_name' in existing_cols if existing_cols else False
            has_rider_phone = 'rider_phone' in existing_cols if existing_cols else False
            
            # Build query based on available columns
            if has_order_type and has_customer_id:
                rider_fields = ""
                if has_rider_name and has_rider_phone:
                    rider_fields = ", o.rider_name, o.rider_phone"
                elif has_rider_name:
                    rider_fields = ", o.rider_name"
                elif has_rider_phone:
                    rider_fields = ", o.rider_phone"
                
                pickup_field = ", o.pickup_code" if has_pickup_code else ""
                
                if has_status:
                    cursor.execute(f"""
                        SELECT o.id, o.order_number, o.order_type, o.status, o.total_amount as total,
                               o.payment_method, o.payment_status, o.created_at{pickup_field}{rider_fields},
                               c.name as customer_name, c.phone as customer_phone
                        FROM orders o
                        LEFT JOIN customers c ON o.customer_id = c.id
                        WHERE o.id = %s AND o.shop_id = %s
                    """, (order_id, shop_id))
                else:
                    cursor.execute(f"""
                        SELECT o.id, o.order_number, o.order_type, o.total_amount as total,
                               o.payment_method, o.payment_status, o.created_at{pickup_field}{rider_fields},
                               c.name as customer_name, c.phone as customer_phone
                        FROM orders o
                        LEFT JOIN customers c ON o.customer_id = c.id
                        WHERE o.id = %s AND o.shop_id = %s
                    """, (order_id, shop_id))
            else:
                rider_fields = ""
                if has_rider_name and has_rider_phone:
                    rider_fields = ", o.rider_name, o.rider_phone"
                elif has_rider_name:
                    rider_fields = ", o.rider_name"
                elif has_rider_phone:
                    rider_fields = ", o.rider_phone"
                
                pickup_field = ", o.pickup_code" if has_pickup_code else ""
                
                cursor.execute(f"""
                    SELECT o.id, o.order_number, o.total,
                           o.payment_method, o.payment_status, o.created_at{pickup_field}{rider_fields},
                           o.customer_name, o.customer_phone
                    FROM orders o
                    WHERE o.id = %s AND o.shop_id = %s
                """, (order_id, shop_id))
            
            order = cursor.fetchone()
            if not order:
                return jsonify({'success': False, 'message': 'Order not found'}), 404
            
            # Get order items
            cursor.execute("""
                SELECT item_name, quantity, item_image
                FROM order_items
                WHERE order_id = %s
            """, (order_id,))
            items = cursor.fetchall()
            
            # Calculate total without delivery cost
            existing_cols = get_table_columns('orders')
            has_subtotal = 'subtotal' in existing_cols if existing_cols else False
            has_delivery_fee = 'delivery_fee' in existing_cols if existing_cols else False
            
            total_amount = float(order.get('total', 0) or order.get('total_amount', 0) or 0)
            if has_subtotal and order.get('subtotal'):
                total_amount = float(order.get('subtotal', 0))
            elif has_delivery_fee and order.get('delivery_fee'):
                total_amount = total_amount - float(order.get('delivery_fee', 0))
            
            # Convert to dict format
            order_dict = {
                'id': order['id'],
                'order_number': order.get('order_number', f'ORD-{order["id"]}'),
                'order_type': order.get('order_type', 'REGULAR'),
                'status': order.get('status', 'pending'),
                'total': total_amount,
                'payment_method': order.get('payment_method', 'cash_on_delivery'),
                'payment_status': order.get('payment_status', 'pending'),
                'created_at': order.get('created_at').isoformat() if order.get('created_at') else None,
                'customer_name': order.get('customer_name') or 'N/A',
                'customer_phone': order.get('customer_phone') or 'N/A',
                'pickup_code': order.get('pickup_code'),
                'rider_name': order.get('rider_name'),
                'rider_phone': order.get('rider_phone'),
                'order_items': []
            }
            
            for item in items:
                order_dict['order_items'].append({
                    'name': item.get('item_name', 'Item'),
                    'quantity': item.get('quantity', 1),
                    'image': item.get('item_image')
                })
            
            return jsonify({
                'success': True,
                'order': order_dict
            })
    except Exception as e:
        print(f"Error fetching order details: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Error fetching order details'}), 500
    finally:
        connection.close()

@app.route('/api/shop/order/<int:order_id>/update-status', methods=['POST'])
def update_order_status(order_id):
    """Update order status to preparing."""
    if not session.get('logged_in') or session.get('user_type') != 'shop':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    shop_id = session.get('shop_id')
    if not shop_id:
        return jsonify({'success': False, 'message': 'Shop not found'}), 404
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    
    try:
        with connection.cursor() as cursor:
            # Check if order belongs to shop
            cursor.execute("SELECT id, status FROM orders WHERE id = %s AND shop_id = %s", (order_id, shop_id))
            order = cursor.fetchone()
            if not order:
                return jsonify({'success': False, 'message': 'Order not found'}), 404
            
            # Check which status column exists
            existing_cols = get_table_columns('orders')
            has_status = 'status' in existing_cols if existing_cols else False
            
            # Update status to preparing
            if has_status:
                cursor.execute("""
                    UPDATE orders 
                    SET status = 'preparing', updated_at = NOW()
                    WHERE id = %s AND shop_id = %s
                """, (order_id, shop_id))
            else:
                return jsonify({'success': False, 'message': 'Status column not found'}), 500
            
            connection.commit()
            
            return jsonify({
                'success': True,
                'message': 'Order status updated to preparing',
                'status': 'preparing'
            })
    except Exception as e:
        connection.rollback()
        print(f"Error updating order status: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Error updating order status'}), 500
    finally:
        connection.close()

@app.route('/api/shop/order/<int:order_id>/reject', methods=['POST'])
def reject_order(order_id):
    """Reject order and set status to cancelled with reason."""
    if not session.get('logged_in') or session.get('user_type') != 'shop':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    shop_id = session.get('shop_id')
    if not shop_id:
        return jsonify({'success': False, 'message': 'Shop not found'}), 404
    
    data = request.get_json()
    if not data or not data.get('reason'):
        return jsonify({'success': False, 'message': 'Cancellation reason is required'}), 400
    
    cancellation_reason = data.get('reason', '').strip()
    if not cancellation_reason:
        return jsonify({'success': False, 'message': 'Cancellation reason cannot be empty'}), 400
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    
    try:
        with connection.cursor() as cursor:
            # Check if order belongs to shop
            cursor.execute("SELECT id, status FROM orders WHERE id = %s AND shop_id = %s", (order_id, shop_id))
            order = cursor.fetchone()
            if not order:
                return jsonify({'success': False, 'message': 'Order not found'}), 404
            
            # Check which status column exists
            existing_cols = get_table_columns('orders')
            has_status = 'status' in existing_cols if existing_cols else False
            has_cancellation_reason = 'cancellation_reason' in existing_cols if existing_cols else False
            
            # Update status to cancelled
            if has_status and has_cancellation_reason:
                cursor.execute("""
                    UPDATE orders 
                    SET status = 'cancelled', cancellation_reason = %s, updated_at = NOW()
                    WHERE id = %s AND shop_id = %s
                """, (cancellation_reason, order_id, shop_id))
            elif has_status:
                cursor.execute("""
                    UPDATE orders 
                    SET status = 'cancelled', updated_at = NOW()
                    WHERE id = %s AND shop_id = %s
                """, (order_id, shop_id))
            else:
                return jsonify({'success': False, 'message': 'Status column not found'}), 500
            
            connection.commit()
            
            return jsonify({
                'success': True,
                'message': 'Order has been rejected and cancelled',
                'status': 'cancelled'
            })
    except Exception as e:
        connection.rollback()
        print(f"Error rejecting order: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Error rejecting order'}), 500
    finally:
        connection.close()

@app.route('/api/shop/order/<int:order_id>/pack', methods=['POST'])
def pack_order(order_id):
    """Pack order and set status to ready with pickup code."""
    if not session.get('logged_in') or session.get('user_type') != 'shop':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    shop_id = session.get('shop_id')
    if not shop_id:
        return jsonify({'success': False, 'message': 'Shop not found'}), 404
    
    import random
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    
    try:
        with connection.cursor() as cursor:
            # Check if order belongs to shop
            cursor.execute("SELECT id, status FROM orders WHERE id = %s AND shop_id = %s", (order_id, shop_id))
            order = cursor.fetchone()
            if not order:
                return jsonify({'success': False, 'message': 'Order not found'}), 404
            
            # Check which status column exists
            existing_cols = get_table_columns('orders')
            has_status = 'status' in existing_cols if existing_cols else False
            has_pickup_code = 'pickup_code' in existing_cols if existing_cols else False
            
            # Generate random 4-digit code
            pickup_code = f"{random.randint(1000, 9999)}"
            
            # Update status to ready and set pickup code
            if has_status and has_pickup_code:
                cursor.execute("""
                    UPDATE orders 
                    SET status = 'ready', pickup_code = %s, updated_at = NOW()
                    WHERE id = %s AND shop_id = %s
                """, (pickup_code, order_id, shop_id))
            elif has_status:
                cursor.execute("""
                    UPDATE orders 
                    SET status = 'ready', updated_at = NOW()
                    WHERE id = %s AND shop_id = %s
                """, (order_id, shop_id))
            else:
                return jsonify({'success': False, 'message': 'Status column not found'}), 500
            
            connection.commit()
            
            return jsonify({
                'success': True,
                'message': 'Order packed successfully',
                'status': 'ready',
                'pickup_code': pickup_code if has_pickup_code else None
            })
    except Exception as e:
        connection.rollback()
        print(f"Error packing order: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Error packing order'}), 500
    finally:
        connection.close()

@app.route('/api/shop/order/<int:order_id>/cancel', methods=['POST'])
def cancel_order(order_id):
    """Cancel order and set status to cancelled with reason."""
    if not session.get('logged_in') or session.get('user_type') != 'shop':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    shop_id = session.get('shop_id')
    if not shop_id:
        return jsonify({'success': False, 'message': 'Shop not found'}), 404
    
    data = request.get_json()
    if not data or not data.get('reason'):
        return jsonify({'success': False, 'message': 'Cancellation reason is required'}), 400
    
    cancellation_reason = data.get('reason', '').strip()
    if not cancellation_reason:
        return jsonify({'success': False, 'message': 'Cancellation reason cannot be empty'}), 400
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    
    try:
        with connection.cursor() as cursor:
            # Check if order belongs to shop
            cursor.execute("SELECT id, status FROM orders WHERE id = %s AND shop_id = %s", (order_id, shop_id))
            order = cursor.fetchone()
            if not order:
                return jsonify({'success': False, 'message': 'Order not found'}), 404
            
            # Check which status column exists
            existing_cols = get_table_columns('orders')
            has_status = 'status' in existing_cols if existing_cols else False
            has_cancellation_reason = 'cancellation_reason' in existing_cols if existing_cols else False
            
            # Update status to cancelled
            if has_status and has_cancellation_reason:
                cursor.execute("""
                    UPDATE orders 
                    SET status = 'cancelled', cancellation_reason = %s, updated_at = NOW()
                    WHERE id = %s AND shop_id = %s
                """, (cancellation_reason, order_id, shop_id))
            elif has_status:
                cursor.execute("""
                    UPDATE orders 
                    SET status = 'cancelled', updated_at = NOW()
                    WHERE id = %s AND shop_id = %s
                """, (order_id, shop_id))
            else:
                return jsonify({'success': False, 'message': 'Status column not found'}), 500
            
            connection.commit()
            
            return jsonify({
                'success': True,
                'message': 'Order has been cancelled',
                'status': 'cancelled'
            })
    except Exception as e:
        connection.rollback()
        print(f"Error cancelling order: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Error cancelling order'}), 500
    finally:
        connection.close()

@app.route('/dashboard/<role>')
def dashboard(role):
    """Role-based dashboard pages."""
    if not session.get('logged_in') or session.get('user_type') != 'employee':
        return redirect('/')
    
    # Verify user has access to this role dashboard
    user_role = session.get('employee_role', '')
    role_map = {
        'admin': 'KWETU_ADMIN',
        'manager': 'KWETU_MANAGER',
        'cashier': 'KWETU_CASHIER',
        'sales': 'KWETU_SALES',
        'rider': 'KWETU_RIDER',
        'customercare': 'KWETU_CUSTOMERCARE',
        'technician': 'KWETU_TECHNICIAN',
        'it-support': 'KWETU_IT_SUPPORT',
        'employee': 'KWETU_EMPLOYEE'
    }
    
    expected_role = role_map.get(role.lower())
    if expected_role and user_role != expected_role:
        # Redirect to their actual role dashboard
        role_url_map = {
            'KWETU_ADMIN': 'admin',
            'KWETU_MANAGER': 'manager',
            'KWETU_CASHIER': 'cashier',
            'KWETU_SALES': 'sales',
            'KWETU_RIDER': 'rider',
            'KWETU_CUSTOMERCARE': 'customercare',
            'KWETU_TECHNICIAN': 'technician',
            'KWETU_IT_SUPPORT': 'it-support',
            'KWETU_EMPLOYEE': 'employee'
        }
        correct_url = role_url_map.get(user_role, 'employee')
        return redirect(url_for('dashboard', role=correct_url))
    
    return render_template('dashboard.html', role=role, user_role=user_role)

@app.route('/dashboard/profile')
def profile():
    """Employee profile page."""
    if not session.get('logged_in') or session.get('user_type') != 'employee':
        return redirect('/')
    
    employee_id = session.get('employee_id')
    if not employee_id:
        return redirect('/')
    
    connection = get_db_connection()
    if not connection:
        return render_template('profile.html', employee=None, error='Database connection error')
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, full_name, email, phone, login_code, profile_picture, 
                       kwetu_employee_role, status, created_at
                FROM employees
                WHERE id = %s
            """, (employee_id,))
            employee = cursor.fetchone()
            
            if not employee:
                return redirect('/')
            
            return render_template('profile.html', employee=employee)
    except Exception as e:
        print(f"Error fetching employee profile: {e}")
        return render_template('profile.html', employee=None, error='Error loading profile')
    finally:
        connection.close()

@app.route('/api/profile/update', methods=['POST'])
def update_profile():
    """Update employee profile."""
    if not session.get('logged_in') or session.get('user_type') != 'employee':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    employee_id = session.get('employee_id')
    if not employee_id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        # Handle both JSON and form data
        if request.is_json:
            data = request.get_json()
            full_name = data.get('full_name', '').strip().upper()
            email = data.get('email', '').strip().lower()
            phone = data.get('phone', '').strip()
            current_password = data.get('current_password', '')
            new_password = data.get('new_password', '')
            confirm_password = data.get('confirm_password', '')
        else:
            full_name = request.form.get('full_name', '').strip().upper()
            email = request.form.get('email', '').strip().lower()
            phone = request.form.get('phone', '').strip()
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')
        
        # Validate required fields
        if not all([full_name, email, phone]):
            return jsonify({'success': False, 'message': 'Name, email, and phone are required'}), 400
        
        # Validate phone
        phone_valid, phone_msg = validate_phone(phone)
        if not phone_valid:
            return jsonify({'success': False, 'message': phone_msg}), 400
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Database connection error'}), 500
        
        try:
            with connection.cursor() as cursor:
                # Get current employee data
                cursor.execute("""
                    SELECT email, phone, password FROM employees WHERE id = %s
                """, (employee_id,))
                current_data = cursor.fetchone()
                
                if not current_data:
                    return jsonify({'success': False, 'message': 'Employee not found'}), 404
                
                # Check if email is being changed and if it's already taken
                if email != current_data['email']:
                    cursor.execute("SELECT id FROM employees WHERE email = %s AND id != %s", (email, employee_id))
                    if cursor.fetchone():
                        return jsonify({'success': False, 'message': 'Email already registered'}), 400
                
                # Handle password change if provided
                update_password = False
                if new_password:
                    if not current_password:
                        return jsonify({'success': False, 'message': 'Current password is required to change password'}), 400
                    
                    # Verify current password
                    if not check_password_hash(current_data['password'], current_password):
                        return jsonify({'success': False, 'message': 'Current password is incorrect'}), 400
                    
                    # Validate new password
                    password_valid, password_msg = validate_password(new_password)
                    if not password_valid:
                        return jsonify({'success': False, 'message': password_msg}), 400
                    
                    # Check password match
                    if new_password != confirm_password:
                        return jsonify({'success': False, 'message': 'New passwords do not match'}), 400
                    
                    update_password = True
                
                # Handle profile picture upload
                profile_picture = None
                if 'profile_picture' in request.files:
                    file = request.files['profile_picture']
                    if file.filename:
                        profile_picture = save_uploaded_file(file, 'profiles')
                        if not profile_picture:
                            return jsonify({'success': False, 'message': 'Invalid profile picture format'}), 400
                
                # Build update query
                updates = []
                values = []
                
                updates.append("full_name = %s")
                values.append(full_name)
                
                updates.append("email = %s")
                values.append(email)
                
                updates.append("phone = %s")
                values.append(phone)
                
                if update_password:
                    hashed_password = generate_password_hash(new_password)
                    updates.append("password = %s")
                    values.append(hashed_password)
                
                if profile_picture:
                    updates.append("profile_picture = %s")
                    values.append(profile_picture)
                
                values.append(employee_id)
                
                # Update employee
                update_query = f"""
                    UPDATE employees 
                    SET {', '.join(updates)}
                    WHERE id = %s
                """
                
                cursor.execute(update_query, values)
                connection.commit()
                
                # Update session
                session['employee_name'] = full_name
                session['employee_email'] = email
                if profile_picture:
                    session['employee_profile_picture'] = profile_picture
                
                return jsonify({
                    'success': True,
                    'message': 'Profile updated successfully!'
                })
        except pymysql.IntegrityError as e:
            if 'email' in str(e):
                return jsonify({'success': False, 'message': 'Email already registered'}), 400
            return jsonify({'success': False, 'message': 'Update failed. Please try again.'}), 400
        except Exception as e:
            print(f"Error updating profile: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'message': 'Update failed. Please try again.'}), 500
        finally:
            connection.close()
            
    except Exception as e:
        print(f"Error in update_profile: {e}")
        return jsonify({'success': False, 'message': 'An error occurred'}), 500

@app.route('/dashboard/settings')
def settings():
    """Employee settings page."""
    if not session.get('logged_in') or session.get('user_type') != 'employee':
        return redirect('/')
    
    return render_template('settings.html')

# Routes
@app.route('/shop/<int:shop_id>')
def view_public_shop(shop_id):
    """Public shop viewing page."""
    connection = get_db_connection()
    shop = None
    items_by_category = {}
    error = None
    
    if connection:
        try:
            with connection.cursor() as cursor:
                # Fetch shop details including delivery_mode
                cursor.execute("""
                    SELECT id, name, category, email, phone, profile_image, 
                           location_name, longitude, latitude, 
                           status, rating, delivery_mode, created_at
                    FROM shops
                    WHERE id = %s AND (status = 'open' OR status = 'closed' OR status = 'waiting_approval')
                """, (shop_id,))
                shop = cursor.fetchone()
                
                if not shop:
                    error = 'Shop not found or not available'
                else:
                    # Only fetch items if delivery_mode is 0 (items with delivery)
                    delivery_mode = shop.get('delivery_mode', 0)
                    if delivery_mode == 0:
                        # Fetch shop items grouped by category
                        cursor.execute("""
                            SELECT id, category, item_name, description, price, discount_price, 
                                   item_image, status
                            FROM shop_items
                            WHERE shop_id = %s AND status = 'active'
                            ORDER BY category, item_name
                        """, (shop_id,))
                        items = cursor.fetchall()
                        
                        # Group items by category
                        for item in items:
                            category = item.get('category') or 'UNCATEGORIZED'
                            if category not in items_by_category:
                                items_by_category[category] = []
                            items_by_category[category].append(item)
        except Exception as e:
            print(f"Error fetching shop: {e}")
            import traceback
            traceback.print_exc()
            error = 'Error loading shop details'
        finally:
            connection.close()
    else:
        error = 'Database connection error'
    
    if error:
        return render_template('shop_view.html', error=error, shop=None)
    
    return render_template('shop_view.html', shop=shop, items_by_category=items_by_category, error=None)

@app.route('/')
def index():
    """Home page."""
    connection = get_db_connection()
    shops_by_category = {}
    if connection:
        try:
            with connection.cursor() as cursor:
                # Fetch shops with status 'open', 'closed', or 'waiting_approval'
                cursor.execute("""
                    SELECT id, name, category, profile_image, status, rating, location_name
                    FROM shops
                    WHERE status = 'open' OR status = 'closed' OR status = 'waiting_approval'
                    ORDER BY category, 
                             CASE 
                                 WHEN status = 'open' THEN 1
                                 WHEN status = 'closed' THEN 2
                                 WHEN status = 'waiting_approval' THEN 3
                             END,
                             rating DESC
                """)
                shops = cursor.fetchall()
                
                # Group shops by category
                for shop in shops:
                    category = shop.get('category') or 'UNCATEGORIZED'
                    if category not in shops_by_category:
                        shops_by_category[category] = []
                    shops_by_category[category].append(shop)
        except Exception as e:
            print(f"Error fetching shops: {e}")
        finally:
            connection.close()
    return render_template('index.html', shops_by_category=shops_by_category)

# Cart and Checkout Routes
@app.route('/api/orders/create', methods=['POST'])
def create_order():
    """Create a new order."""
    data = request.get_json()
    connection = get_db_connection()
    
    if not connection:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    
    try:
        with connection.cursor() as cursor:
            # Generate unique order number
            import random
            import string
            order_number = 'ORD' + ''.join(random.choices(string.digits, k=10))
            
            # Check if order number exists (unlikely but check anyway)
            cursor.execute("SELECT id FROM orders WHERE order_number = %s", (order_number,))
            while cursor.fetchone():
                order_number = 'ORD' + ''.join(random.choices(string.digits, k=10))
                cursor.execute("SELECT id FROM orders WHERE order_number = %s", (order_number,))
            
            # Create order
            cursor.execute("""
                INSERT INTO orders (order_number, shop_id, customer_name, customer_phone, customer_email,
                                  subtotal, delivery_fee, tax, discount, total, payment_method,
                                  promo_code, notes, contactless_delivery)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                order_number,
                data.get('shop_id'),
                data.get('customer_name'),
                data.get('customer_phone'),
                data.get('customer_email'),
                data.get('subtotal', 0),
                data.get('delivery_fee', 0),
                data.get('tax', 0),
                data.get('discount', 0),
                data.get('total', 0),
                data.get('payment_method', 'cash_on_delivery'),
                data.get('promo_code'),
                data.get('notes'),
                data.get('contactless_delivery', 0)
            ))
            
            order_id = cursor.lastrowid
            
            # Add order items
            items = data.get('items', [])
            for item in items:
                cursor.execute("""
                    INSERT INTO order_items (order_id, item_id, item_name, item_image, quantity,
                                           unit_price, discount_price, subtotal)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    order_id,
                    item.get('item_id'),
                    item.get('item_name'),
                    item.get('item_image'),
                    item.get('quantity', 1),
                    item.get('unit_price', 0),
                    item.get('discount_price'),
                    item.get('subtotal', 0)
                ))
            
            # Add delivery information
            if data.get('delivery_address'):
                cursor.execute("""
                    INSERT INTO delivery (order_id, delivery_address, delivery_latitude, delivery_longitude,
                                       shop_latitude, shop_longitude, distance_km, estimated_time_minutes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    order_id,
                    data.get('delivery_address'),
                    data.get('delivery_latitude'),
                    data.get('delivery_longitude'),
                    data.get('shop_latitude'),
                    data.get('shop_longitude'),
                    data.get('distance_km'),
                    data.get('estimated_time_minutes')
                ))
            
            connection.commit()
            
            return jsonify({
                'success': True,
                'order_id': order_id,
                'order_number': order_number,
                'message': 'Order created successfully'
            })
    except Exception as e:
        connection.rollback()
        print(f"Error creating order: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Error creating order'}), 500
    finally:
        connection.close()

@app.route('/order/<order_number>')
def order_receipt(order_number):
    """Order receipt page."""
    connection = get_db_connection()
    order = None
    order_items = []
    delivery_info = None
    
    if connection:
        try:
            with connection.cursor() as cursor:
                # Get order
                cursor.execute("""
                    SELECT o.*, s.name as shop_name, s.phone as shop_phone, s.location_name as shop_location
                    FROM orders o
                    JOIN shops s ON o.shop_id = s.id
                    WHERE o.order_number = %s
                """, (order_number,))
                order = cursor.fetchone()
                
                if order:
                    # Get order items
                    cursor.execute("""
                        SELECT * FROM order_items
                        WHERE order_id = %s
                    """, (order['id'],))
                    order_items = cursor.fetchall()
                    
                    # Get delivery info
                    cursor.execute("""
                        SELECT * FROM delivery
                        WHERE order_id = %s
                    """, (order['id'],))
                    delivery_info = cursor.fetchone()
        except Exception as e:
            print(f"Error fetching order: {e}")
        finally:
            connection.close()
    
    if not order:
        return render_template('order_receipt.html', error='Order not found', order=None)
    
    return render_template('order_receipt.html', order=order, order_items=order_items, delivery_info=delivery_info)

@app.route('/api/distance/calculate', methods=['POST'])
def calculate_distance():
    """Calculate distance and time using Google Distance Matrix API."""
    data = request.get_json()
    
    origin_lat = data.get('origin_lat')
    origin_lng = data.get('origin_lng')
    dest_lat = data.get('dest_lat')
    dest_lng = data.get('dest_lng')
    
    if not all([origin_lat, origin_lng, dest_lat, dest_lng]):
        return jsonify({'success': False, 'message': 'Missing coordinates'}), 400
    
    # Calculate approximate distance using Haversine formula
    import math
    
    def haversine_distance(lat1, lon1, lat2, lon2):
        R = 6371  # Earth radius in km
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        return R * c
    
    distance_km = round(haversine_distance(float(origin_lat), float(origin_lng), float(dest_lat), float(dest_lng)), 2)
    
    # Estimate time (rough calculation: 30 km/h average speed)
    estimated_minutes = int((distance_km / 30) * 60)
    estimated_minutes = max(10, min(estimated_minutes, 60))  # Between 10-60 minutes
    
    return jsonify({
        'success': True,
        'distance_km': distance_km,
        'estimated_time_minutes': estimated_minutes,
        'estimated_time_range': f"{estimated_minutes - 2}-{estimated_minutes + 2}"
    })

# Initialize database and run app
if __name__ == '__main__':
    # Initialize database first
    init_db()
    # Then run the Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)
