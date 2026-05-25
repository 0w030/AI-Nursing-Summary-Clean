import os
from dotenv import load_dotenv
import oracledb

# Initialize oracle client
oracledb.init_oracle_client(lib_dir=r"C:\instantclient_19_30\instantclient_19_30")
load_dotenv()

def check_value_in_tables(search_value="0015755540"):
    try:
        host = os.getenv("DB_HOST")
        port = os.getenv("DB_PORT")
        service_name = os.getenv("DB_NAME")
        user = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")

        dsn = oracledb.makedsn(host, port, service_name=service_name)
        conn = oracledb.connect(user=user, password=password, dsn=dsn)
        cursor = conn.cursor()

        target_tables = ['RECORD', 'RECORD_DETAIL', 'RECORD_VERSION']

        print(f"Searching for '{search_value}' in tables: {target_tables}\n")

        for table_name in target_tables:
            print(f"--- Table: {table_name} ---")
            
            # Get columns of the table
            sql_cols = """
            SELECT column_name, data_type 
            FROM user_tab_columns 
            WHERE table_name = :1
            """
            cursor.execute(sql_cols, [table_name])
            columns = cursor.fetchall()

            if not columns:
                print("Table not found or no columns.")
                continue

            found = False
            for col in columns:
                col_name = col[0]
                col_type = col[1]

                # We only search in string-like columns to avoid type errors
                if col_type in ('VARCHAR2', 'CHAR', 'CLOB', 'NVARCHAR2', 'NCHAR'):
                    query = f"SELECT COUNT(*) FROM {table_name} WHERE {col_name} = :1 OR {col_name} LIKE :2"
                    try:
                        cursor.execute(query, [search_value, f"%{search_value}%"])
                        count = cursor.fetchone()[0]
                        if count > 0:
                            print(f"FOUND {count} match(es) in column: {col_name}")
                            found = True
                    except Exception as inner_e:
                        print(f"Error querying column {col_name}: {inner_e}")
            if not found:
                print("No matches found in this table.")
            print("-" * 50)

        conn.close()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_value_in_tables()
