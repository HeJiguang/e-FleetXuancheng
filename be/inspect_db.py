import sqlite3
import pandas as pd
import os

# (修改) 更新数据库文件的相对路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(SCRIPT_DIR, '..', 'backend', 'data', 'vehicle_data_optimized.db')

def inspect_database():
    """连接到 SQLite 数据库并打印每个表的前5行"""
    print(f"--- Inspecting Database: {DB_FILE} ---\n")
    conn = None  # Initialize conn to None
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Get a list of all tables in the database
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        if not tables:
            print("No tables found in the database.")
            return

        # Loop through the tables and print the first 5 rows
        for table_name in tables:
            table_name = table_name[0]
            print(f"--- Table: {table_name} ---")
            
            try:
                # Use pandas to read and display the data in a clean format
                df = pd.read_sql_query(f"SELECT * FROM {table_name} LIMIT 5", conn)
                if df.empty:
                    print("Table is empty.\n")
                else:
                    print(df.to_string())
                    print("\n")
            except Exception as e:
                print(f"Could not read from table {table_name}. Error: {e}\n")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    inspect_database()
