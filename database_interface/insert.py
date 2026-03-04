import psycopg2
from psycopg2 import sql

# Connection parameters from your docker-compose.yml
DB_CONFIG = {
    "dbname": "database",
    "user": "info_retrieval",
    "password": "password",
    "host": "localhost",  # Since you mapped "5432:5432"
    "port": "5432"
}

def save_to_postgres(data_list):
    conn = None
    try:
        # 1. Connect to the pgdb container
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # 2. Create table (Interface) if it doesn't exist
        cur.execute("""
            CREATE TABLE IF NOT EXISTS scraped_data (
                id SERIAL PRIMARY KEY,
                title TEXT,
                url TEXT UNIQUE,
                content TEXT,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 3. Insert Data
        insert_query = """
            INSERT INTO scraped_data (title, url, content)
            VALUES (%s, %s, %s)
            ON CONFLICT (url) DO NOTHING;
        """
        
        # executemany is much faster for scrapers than looping individual inserts
        cur.executemany(insert_query, data_list)

        # 4. Commit changes
        conn.commit()
        print(f"Successfully inserted {len(data_list)} items.")

        cur.close()
    except Exception as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()