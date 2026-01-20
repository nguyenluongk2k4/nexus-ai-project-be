import sqlite3
import os
import shutil

# Path to chroma.sqlite3
DB_PATH = "../chroma_db/chroma.sqlite3"
TEMP_DB_PATH = "temp_chroma.sqlite3"

def check_active_collection():
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at {DB_PATH}")
        return

    try:
        # Copy to temp file to avoid locks
        shutil.copy2(DB_PATH, TEMP_DB_PATH)
        
        conn = sqlite3.connect(TEMP_DB_PATH)
        cursor = conn.cursor()
        
        print(f"📂 Checking {DB_PATH} (via copy)...")
        
        # Get collections
        cursor.execute("SELECT id, name FROM collections")
        collections = cursor.fetchall()
        
        print("\n✅ Active Collections:")
        with open("active_chroma_id.txt", "w") as f:
            for col_id, name in collections:
                print(f"  - Name: {name}")
                print(f"  - UUID: {col_id}")
                f.write(f"{col_id}\n")
                print(f"  👉 KEEP FOLDER: {col_id}")
            
        conn.close()
        
        # Cleanup
        try:
            os.remove(TEMP_DB_PATH)
        except:
            pass
            
    except Exception as e:
        print(f"❌ Error reading sqlite: {e}")

if __name__ == "__main__":
    check_active_collection()
