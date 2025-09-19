"""
数据库初始化脚本，用于初始化数据库结构和导入数据
"""
import sqlite3
import pandas as pd
import re
import os

# --- Configuration ---
# Build paths relative to this script file
SCRIPT_DIR = os.path.dirname(__file__)
DB_FILE = os.path.join(SCRIPT_DIR, 'vehicle_data_optimized.db')
DATA_DIR = os.path.join(SCRIPT_DIR, '..', 'temp/')


# --- Optimized Database Schema ---
TABLES = {
    'departments': """
        CREATE TABLE IF NOT EXISTS departments (
            department_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    """,
    'violation_types': """
        CREATE TABLE IF NOT EXISTS violation_types (
            violation_type_id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL UNIQUE
        )
    """,
    'service_providers': """
        CREATE TABLE IF NOT EXISTS service_providers (
            provider_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    """,
    'vehicles': """
        CREATE TABLE IF NOT EXISTS vehicles (
            vehicle_id INTEGER PRIMARY KEY,
            plate_number TEXT NOT NULL UNIQUE,
            department_id INTEGER,
            manager TEXT,
            brand_model TEXT,
            displacement REAL,
            capacity INTEGER,
            registration_date DATE,
            purchase_price NUMERIC(10, 2),
            notes TEXT,
            photo_url TEXT,
            FOREIGN KEY (department_id) REFERENCES departments (department_id)
        )
    """,
    'violations': """
        CREATE TABLE IF NOT EXISTS violations (
            violation_id INTEGER PRIMARY KEY,
            plate_number TEXT,
            violation_time DATETIME,
            violation_location TEXT,
            violation_type_id INTEGER,
            FOREIGN KEY (plate_number) REFERENCES vehicles (plate_number),
            FOREIGN KEY (violation_type_id) REFERENCES violation_types (violation_type_id)
        )
    """,
    'maintenance': """
        CREATE TABLE IF NOT EXISTS maintenance (
            maintenance_id INTEGER PRIMARY KEY AUTOINCREMENT,
            plate_number TEXT,
            order_number TEXT,
            provider_id INTEGER,
            request_time DATETIME,
            delivery_time DATETIME,
            current_mileage INTEGER,
            last_maintenance_mileage INTEGER,
            service_details TEXT,
            maintenance_cost NUMERIC(10, 2),
            FOREIGN KEY (plate_number) REFERENCES vehicles (plate_number),
            FOREIGN KEY (provider_id) REFERENCES service_providers (provider_id)
        )
    """,
    'monthly_fuel_summary': """
        CREATE TABLE IF NOT EXISTS monthly_fuel_summary (
            summary_id INTEGER PRIMARY KEY AUTOINCREMENT,
            plate_number TEXT,
            year INTEGER,
            month INTEGER,
            total_fuel_cost NUMERIC(10, 2),
            total_fuel_amount DECIMAL(10, 2),
            start_month_mileage INTEGER,
            end_month_mileage INTEGER,
            distance_driven INTEGER,
            avg_consumption_per_100km DECIMAL(10, 2),
            card_number TEXT,
            notes TEXT,
            FOREIGN KEY (plate_number) REFERENCES vehicles (plate_number)
        )
    """
}

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_vehicles_plate_number ON vehicles (plate_number);",
    "CREATE INDEX IF NOT EXISTS idx_violations_plate_number ON violations (plate_number);",
    "CREATE INDEX IF NOT EXISTS idx_violations_time ON violations (violation_time);",
    "CREATE INDEX IF NOT EXISTS idx_maintenance_plate_number ON maintenance (plate_number);",
    "CREATE INDEX IF NOT EXISTS idx_fuel_summary_plate_year_month ON monthly_fuel_summary (plate_number, year, month);"
]

def setup_database():
    """Create database, tables, and indexes without deleting the file."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    print("--- Setting up database ---")

    # Clear existing data from tables to ensure a fresh import
    table_names = list(TABLES.keys())
    # Drop tables in reverse order of creation to respect foreign key constraints
    for table_name in reversed(table_names):
        cursor.execute(f"DROP TABLE IF EXISTS {table_name};")
    print(" - Cleared existing tables.")

    print(" - Creating tables...")
    for table_name, create_sql in TABLES.items():
        cursor.execute(create_sql)
    print(f" - Tables created.")
    
    print(" - Creating indexes...")
    for index_sql in INDEXES:
        cursor.execute(index_sql)
    print(" - Indexes created.")

    conn.commit()
    conn.close()
    print("--- Database setup complete ---\n")


def import_data():
    """Main function to import all data based on the optimized schema."""
    conn = sqlite3.connect(DB_FILE)
    
    try:
        # --- Step 1: Populate Dictionary Tables and Create Mappings ---
        print("\n--- Step 1: Populating Dictionary Tables ---")
        
        # Departments
        df_vehicles_raw = pd.read_csv(os.path.join(DATA_DIR, '1-车辆基本信息.csv'), encoding='utf-8')
        departments = pd.DataFrame(df_vehicles_raw.iloc[:, 1].unique(), columns=['name'])
        departments.to_sql('departments', conn, if_exists='append', index=False)
        print(f" - Populated 'departments' with {len(departments)} unique records.")
        df_dep_map = pd.read_sql('SELECT * FROM departments', conn)
        dep_map = pd.Series(df_dep_map.department_id.values, index=df_dep_map.name).to_dict()

        # Violation Types
        df_violations_raw = pd.read_csv(os.path.join(DATA_DIR, '2-车辆违章数据（1-6月份）_汇总表.csv'), encoding='utf-8')
        violation_types = pd.DataFrame(df_violations_raw.iloc[:, 5].unique(), columns=['description'])
        violation_types.to_sql('violation_types', conn, if_exists='append', index=False)
        print(f" - Populated 'violation_types' with {len(violation_types)} unique records.")
        df_vt_map = pd.read_sql('SELECT * FROM violation_types', conn)
        vt_map = pd.Series(df_vt_map.violation_type_id.values, index=df_vt_map.description).to_dict()

        # Service Providers
        df_maint_raw = pd.read_csv(os.path.join(DATA_DIR, '3-车辆维保数据_3-维修保养明细.csv'), encoding='utf-8')
        providers = pd.DataFrame(df_maint_raw.iloc[:, 1].unique(), columns=['name'])
        providers.to_sql('service_providers', conn, if_exists='append', index=False)
        print(f" - Populated 'service_providers' with {len(providers)} unique records.")
        df_sp_map = pd.read_sql('SELECT * FROM service_providers', conn)
        sp_map = pd.Series(df_sp_map.provider_id.values, index=df_sp_map.name).to_dict()

        # --- Step 2: Import Business Data using Mappings ---
        print("\n--- Step 2: Importing Business Data ---")
        
        # Vehicles
        df_vehicles_raw.columns = [
            'vehicle_id', 'department_name', 'plate_number', 'manager', 'brand_1',
            'brand_2', 'displacement', 'capacity', 'registration_date_str',
            'purchase_price', 'age', 'notes'
        ]
        df_vehicles_raw['plate_number'] = df_vehicles_raw['plate_number'].str.strip()
        df_vehicles_raw['brand_model'] = df_vehicles_raw['brand_1'].fillna('') + df_vehicles_raw['brand_2'].fillna('')
        
        def parse_date(date_str):
            if pd.isna(date_str): return None
            match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', str(date_str))
            return f"{match.groups()[0]}-{int(match.groups()[1]):02d}-{int(match.groups()[2]):02d}" if match else None
            
        df_vehicles_raw['registration_date'] = df_vehicles_raw['registration_date_str'].apply(parse_date)
        df_vehicles_raw['department_id'] = df_vehicles_raw['department_name'].map(dep_map)
        
        df_vehicles_to_db = df_vehicles_raw[['vehicle_id', 'plate_number', 'department_id', 'manager', 'brand_model', 'displacement', 'capacity', 'registration_date', 'purchase_price', 'notes']]
        df_vehicles_to_db.to_sql('vehicles', conn, if_exists='append', index=False)
        print(f" - Imported {len(df_vehicles_to_db)} records into 'vehicles'.")

        # Violations
        df_violations_raw.columns = ['violation_id', 'plate_number', 'department', 'violation_time', 'violation_location', 'violation_type_desc']
        df_violations_raw['plate_number'] = df_violations_raw['plate_number'].str.strip()
        df_violations_raw['violation_type_id'] = df_violations_raw['violation_type_desc'].map(vt_map)
        
        df_violations_to_db = df_violations_raw[['violation_id', 'plate_number', 'violation_time', 'violation_location', 'violation_type_id']]
        df_violations_to_db.to_sql('violations', conn, if_exists='append', index=False)
        print(f" - Imported {len(df_violations_to_db)} records into 'violations'.")

        # Maintenance
        df_maint_raw.columns = [
            'maintenance_id_old', 'provider_name', 'plate_number', 'order_number',
            'request_time', 'delivery_time', 'current_mileage',
            'last_maintenance_date', 'last_maintenance_mileage',
            'service_details', 'maintenance_cost'
        ]
        df_maint_raw['provider_id'] = df_maint_raw['provider_name'].map(sp_map)
        
        df_maint_to_db = df_maint_raw[['plate_number', 'order_number', 'provider_id', 'request_time', 'delivery_time', 'current_mileage', 'last_maintenance_mileage', 'service_details', 'maintenance_cost']]
        df_maint_to_db.to_sql('maintenance', conn, if_exists='append', index=False)
        print(f" - Imported {len(df_maint_to_db)} records into 'maintenance'.")

        conn.commit()
        print("\n--- Data Import Successful ---")

    except Exception as e:
        conn.rollback()
        print(f"\nAn error occurred: {e}")
    finally:
        conn.close()

def import_fuel_summary(conn):
    """Imports and transforms the monthly fuel summary data."""
    print(" - Importing fuel summary data...")
    file_path = os.path.join(DATA_DIR, '4-油耗数据.csv')
    try:
        # Define dtypes at read time to prevent type inference issues
        df = pd.read_csv(file_path, encoding='utf-8', keep_default_na=False, na_values=[''])
        
        # --- Data Cleaning and Transformation using iloc (integer-location based indexing) ---
        # This approach is robust against variations in column header names (e.g., spaces)
        
        # Get a dictionary of original column names by index for later renaming
        original_columns = {i: name for i, name in enumerate(df.columns)}

        # 1. Clean up numeric columns first using their index
        df.iloc[:, 8] = pd.to_numeric(df.iloc[:, 8], errors='coerce').fillna(0).astype(int)   # 里 程数
        df.iloc[:, 6] = pd.to_numeric(df.iloc[:, 6], errors='coerce').fillna(0).astype(int)   # 月初公里数
        df.iloc[:, 7] = pd.to_numeric(df.iloc[:, 7], errors='coerce').fillna(0).astype(int)   # 月末公里数
        df.iloc[:, 4] = pd.to_numeric(df.iloc[:, 4], errors='coerce').fillna(0)             # 加油金额
        df.iloc[:, 5] = pd.to_numeric(df.iloc[:, 5], errors='coerce').fillna(0)             # 加油数量
        df.iloc[:, 9] = pd.to_numeric(df.iloc[:, 9], errors='coerce').fillna(0)             # 百公里油耗
            
        # 2. Extract year and month
        # (修正) 根据刚才的检查，月份信息在第12列 (索引为11), 而不是 "备注" 列
        df['month'] = df[original_columns.get(11)].str.extract(r'(\d+)月') # Unnamed: 11 列
        df['month'] = pd.to_numeric(df['month'], errors='coerce').fillna(0).astype(int)
        df['year'] = 2025

        # 3. Now, rename the columns to English names for the database
        column_map = {
            original_columns.get(1): 'plate_number',
            original_columns.get(3): 'card_number',
            original_columns.get(4): 'total_fuel_cost',
            original_columns.get(5): 'total_fuel_amount',
            original_columns.get(6): 'start_month_mileage',
            original_columns.get(7): 'end_month_mileage',
            original_columns.get(8): 'distance_driven',
            original_columns.get(9): 'avg_consumption_per_100km',
            original_columns.get(10): 'notes'
        }
        df.rename(columns=column_map, inplace=True)
        
        # --- Prepare final DataFrame for SQL import ---
        df_to_db = df[[
            'plate_number', 'year', 'month', 'total_fuel_cost', 'total_fuel_amount',
            'start_month_mileage', 'end_month_mileage', 'distance_driven',
            'avg_consumption_per_100km', 'card_number', 'notes'
        ]]

        df_to_db.to_sql('monthly_fuel_summary', conn, if_exists='append', index=False)
        print(f" - Imported {len(df_to_db)} records into 'monthly_fuel_summary'.")
        return True
    except FileNotFoundError:
        print(f" - Fuel summary file not found: {file_path}")
        return False
    except Exception as e:
        print(f" - An error occurred during fuel summary import: {e}")
        return False


def main():
    setup_database()
    
    conn = sqlite3.connect(DB_FILE)
    try:
        import_dictionary_data(conn)
        import_business_data(conn)
        import_fuel_summary(conn)
        conn.commit()
    except Exception as e:
        print(f"A critical error occurred: {e}")
        conn.rollback()
    finally:
        conn.close()
    
    print("\n--- Full Data Import Process Finished ---")

# We refactor the original import_data into two more focused functions
def import_dictionary_data(conn):
    """Populates the dictionary tables and returns mapping dictionaries."""
    print("\n--- Step 1: Populating Dictionary Tables ---")
    
    # Departments
    df_vehicles_raw = pd.read_csv(os.path.join(DATA_DIR, '1-车辆基本信息.csv'), encoding='utf-8')
    departments = pd.DataFrame(df_vehicles_raw.iloc[:, 1].unique(), columns=['name'])
    departments.to_sql('departments', conn, if_exists='append', index=False)
    print(f" - Populated 'departments' with {len(departments)} unique records.")
   
    # Violation Types
    df_violations_raw = pd.read_csv(os.path.join(DATA_DIR, '2-车辆违章数据（1-6月份）_汇总表.csv'), encoding='utf-8')
    violation_types = pd.DataFrame(df_violations_raw.iloc[:, 5].unique(), columns=['description'])
    violation_types.to_sql('violation_types', conn, if_exists='append', index=False)
    print(f" - Populated 'violation_types' with {len(violation_types)} unique records.")

    # Service Providers
    df_maint_raw = pd.read_csv(os.path.join(DATA_DIR, '3-车辆维保数据_3-维修保养明细.csv'), encoding='utf-8')
    providers = pd.DataFrame(df_maint_raw.iloc[:, 1].unique(), columns=['name'])
    providers.to_sql('service_providers', conn, if_exists='append', index=False)
    print(f" - Populated 'service_providers' with {len(providers)} unique records.")

def import_business_data(conn):
    """Imports the main business data tables using mappings from dictionary tables."""
    print("\n--- Step 2: Importing Business Data ---")

    # Create Mappings
    df_dep_map = pd.read_sql('SELECT * FROM departments', conn)
    dep_map = pd.Series(df_dep_map.department_id.values, index=df_dep_map.name).to_dict()
    df_vt_map = pd.read_sql('SELECT * FROM violation_types', conn)
    vt_map = pd.Series(df_vt_map.violation_type_id.values, index=df_vt_map.description).to_dict()
    df_sp_map = pd.read_sql('SELECT * FROM service_providers', conn)
    sp_map = pd.Series(df_sp_map.provider_id.values, index=df_sp_map.name).to_dict()
    
    # Import Vehicles
    df_vehicles_raw = pd.read_csv(os.path.join(DATA_DIR, '1-车辆基本信息.csv'), encoding='utf-8')
    df_vehicles_raw.columns = [
        'vehicle_id', 'department_name', 'plate_number', 'manager', 'brand_1',
        'brand_2', 'displacement', 'capacity', 'registration_date_str',
        'purchase_price', 'age', 'notes'
    ]
    df_vehicles_raw['plate_number'] = df_vehicles_raw['plate_number'].str.strip()
    df_vehicles_raw['brand_model'] = df_vehicles_raw['brand_1'].fillna('') + df_vehicles_raw['brand_2'].fillna('')
    def parse_date(date_str):
        if pd.isna(date_str): return None
        match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', str(date_str))
        return f"{match.groups()[0]}-{int(match.groups()[1]):02d}-{int(match.groups()[2]):02d}" if match else None
    df_vehicles_raw['registration_date'] = df_vehicles_raw['registration_date_str'].apply(parse_date)
    df_vehicles_raw['department_id'] = df_vehicles_raw['department_name'].map(dep_map)
    df_vehicles_to_db = df_vehicles_raw[['vehicle_id', 'plate_number', 'department_id', 'manager', 'brand_model', 'displacement', 'capacity', 'registration_date', 'purchase_price', 'notes']]
    df_vehicles_to_db.to_sql('vehicles', conn, if_exists='append', index=False)
    print(f" - Imported {len(df_vehicles_to_db)} records into 'vehicles'.")

    # Import Violations
    df_violations_raw = pd.read_csv(os.path.join(DATA_DIR, '2-车辆违章数据（1-6月份）_汇总表.csv'), encoding='utf-8')
    df_violations_raw.columns = ['violation_id', 'plate_number', 'department', 'violation_time', 'violation_location', 'violation_type_desc']
    df_violations_raw['plate_number'] = df_violations_raw['plate_number'].str.strip()
    df_violations_raw['violation_type_id'] = df_violations_raw['violation_type_desc'].map(vt_map)
    df_violations_to_db = df_violations_raw[['violation_id', 'plate_number', 'violation_time', 'violation_location', 'violation_type_id']]
    df_violations_to_db.to_sql('violations', conn, if_exists='append', index=False)
    print(f" - Imported {len(df_violations_to_db)} records into 'violations'.")

    # Import Maintenance
    df_maint_raw = pd.read_csv(os.path.join(DATA_DIR, '3-车辆维保数据_3-维修保养明细.csv'), encoding='utf-8')
    df_maint_raw.columns = [
        'maintenance_id_old', 'provider_name', 'plate_number', 'order_number',
        'request_time', 'delivery_time', 'current_mileage',
        'last_maintenance_date', 'last_maintenance_mileage',
        'service_details', 'maintenance_cost'
    ]
    df_maint_raw['provider_id'] = df_maint_raw['provider_name'].map(sp_map)
    df_maint_to_db = df_maint_raw[['plate_number', 'order_number', 'provider_id', 'request_time', 'delivery_time', 'current_mileage', 'last_maintenance_mileage', 'service_details', 'maintenance_cost']]
    df_maint_to_db.to_sql('maintenance', conn, if_exists='append', index=False)
    print(f" - Imported {len(df_maint_to_db)} records into 'maintenance'.")


if __name__ == '__main__':
    main()
