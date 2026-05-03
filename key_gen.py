import os
import uuid
import argparse
import sys

VAULT_PATH = "api/auth_vault.py"

def generate_key(operator_id="Clean"):
    """Generates a new Retri key and adds it to the local Identity Vault."""
    new_key = f"Retri-{uuid.uuid4().hex[:8].upper()}-{uuid.uuid4().hex[:8].upper()}"
    
    if not os.path.exists(VAULT_PATH):
        print(f"[-] Error: {VAULT_PATH} not found. Ensure you are in the repository root.")
        return

    try:
        with open(VAULT_PATH, "r") as f:
            lines = f.readlines()

        # Find the VALID_KEYS dictionary and insert the new key
        new_lines = []
        found_dict = False
        inserted = False
        
        for line in lines:
            new_lines.append(line)
            if "VALID_KEYS = {" in line:
                found_dict = True
            if found_dict and not inserted and "}" in line:
                # Insert before the closing brace
                new_lines.insert(-1, f'    "{new_key}": {{"operator_id": "{operator_id}", "status": "active"}},\n')
                inserted = True

        if not inserted:
            print("[-] Error: Could not find VALID_KEYS dictionary in vault file.")
            return

        with open(VAULT_PATH, "w") as f:
            f.writelines(new_lines)

        print(f"\n[+] BIFROST IDENTITY VAULT UPDATED!")
        print(f"    OPERATOR: {operator_id}")
        print(f"    NEW KEY:  {new_key}")
        print(f"    STATUS:   ACTIVE\n")
        print(f"    [!] Commit and Push to activate this key on the server.\n")

    except Exception as e:
        print(f"[-] Failed to update vault: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BIFROST Identity Vault Key Generator")
    parser.add_argument("-o", "--operator", type=str, default="Clean", help="Operator ID for the key")
    args = parser.parse_args()
    
    generate_key(args.operator)
