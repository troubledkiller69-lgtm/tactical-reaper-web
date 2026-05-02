import os
import uuid
import argparse
from datetime import datetime, timedelta
from supabase import create_client, Client

SUPABASE_URL = "https://smxpzldbxewcgrakaqhn.supabase.co"
SUPABASE_KEY = "sb_publishable_QviDYLWIVjVJl4N01Bqaug_ZgkNHcde"

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"Error initializing Supabase client: {e}")
    exit(1)

def generate_key(hours=24):
    """Generates a new Retri key and inserts it into Supabase."""
    new_key = f"Retri-{uuid.uuid4().hex[:8].upper()}-{uuid.uuid4().hex[:8].upper()}"
    
    data = {
        "key": new_key,
        "duration_hours": hours,
        "status": "active"
    }
    
    try:
        response = supabase.table("keys").insert(data).execute()
        print(f"\n[+] Key Generated Successfully!")
        print(f"    KEY: {new_key}")
        print(f"    DURATION: {hours} hours\n")
    except Exception as e:
        print(f"[-] Failed to insert key to Supabase: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tactical Reaper Key Generator (Cloud)")
    parser.add_argument("-d", "--duration", type=int, default=24, help="Duration of the key in hours (default: 24)")
    args = parser.parse_args()
    
    generate_key(args.duration)
