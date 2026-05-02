import sqlite3

DB_NAME = "eni_reper.db"

def check_keys():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    print("\n--- [ ACTIVE KEYS ] ---")
    cursor.execute("SELECT key, status FROM keys WHERE status = 'active'")
    rows = cursor.fetchall()
    if not rows:
        print("No active keys found.")
    for row in rows:
        print(f"Key: {row[0]} | Status: {row[1]}")
        
    print("\n--- [ ALL KEYS ] ---")
    cursor.execute("SELECT * FROM keys")
    rows = cursor.fetchall()
    for row in rows:
        print(row)
        
    conn.close()

if __name__ == "__main__":
    check_keys()
