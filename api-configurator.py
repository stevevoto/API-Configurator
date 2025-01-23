#!/usr/bin/env python3
###########################
# Mist API Code by Steve Voto (Enhanced)
# ======================================
# This script interfaces with the Mist API to manage various networking components:
#  - Applications/Services
#  - Networks
#  - Sites
#  - Hub profiles
#  - WAN edges
#
# New Features:
# 1) Reads org_id and token from Token-Org.txt.txt (instead of prompting or hard-coding).
# 2) Reads JSON payloads from local files (app-*.json, net-*.json, site-*.json, hub-*.json, wan-*.json).
# 3) Converts true false to string instead of boolean
# 4) Adds debug prints showing requests and responses.
# 5) Maintains original name-increment logic for WAN edges in case of name conflicts.
#
# Usage:
#   python3 api-configurator.py --get    (collect all config files from current org selected)
#   python3 api-configurator.py --post   (push all config files to current org selected)
# ~SV
###########################
#!/usr/bin/env python3
import os
import json
import requests
import argparse
from datetime import datetime

###########################
# Read Token & Org
###########################
def read_token_org(file_path="Token-Org.txt"):
    """Reads API token and org_id from a file."""
    token = None
    org_id = None
    try:
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('token='):
                    token = line.split('=', 1)[1].strip()
                elif line.startswith('org_id='):
                    org_id = line.split('=', 1)[1].strip()
        if not token or not org_id:
            raise ValueError("Token or Org ID missing.")
    except FileNotFoundError:
        print(f"[ERROR] File {file_path} not found.")
        exit(1)
    return token, org_id

###########################
# Create Backup Folder
###########################
def create_backup_folder():
    """Creates a backup folder with a timestamp."""
    folder_name = f"bckup-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}"
    os.makedirs(folder_name, exist_ok=True)
    print(f"[INFO] Created backup folder: {folder_name}")
    return folder_name

###########################
# Store JSON Files
###########################
def store_config_as_json(prefix, item, output_dir, name_key='name'):
    """Saves a JSON object to a file in the backup directory."""
    raw_name = item.get(name_key, 'unnamed')
    filename = f"{prefix}-{raw_name}.json".replace('/', '_').replace('\\', '_')
    file_path = os.path.join(output_dir, filename)
    try:
        with open(file_path, 'w') as f:
            json.dump(item, f, indent=2)
        print(f"[INFO] Wrote {file_path}")
    except Exception as e:
        print(f"[ERROR] Could not write file {file_path}: {e}")

###########################
# Get Data from Mist API
###########################
def get_mist_data(org_id, token, endpoint, limit=1000):
    """Fetches data from the Mist API for the specified endpoint."""
    base_url = "https://api.mist.com/api/v1"
    url = f"{base_url}/orgs/{org_id}/{endpoint}?limit={limit}"
    headers = {'Authorization': f'Token {token}'}
    print(f"[DEBUG] Sending GET request to {url}")
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print(f"[ERROR] Failed to GET {endpoint}, code={resp.status_code}, text={resp.text}")
        return []
    try:
        data = resp.json()
        if isinstance(data, dict) and 'results' in data:
            print(f"[DEBUG] Retrieved {len(data['results'])} items from {endpoint}.")
            return data['results']
        elif isinstance(data, list):
            print(f"[DEBUG] Retrieved {len(data)} items from {endpoint}.")
            return data
        else:
            print(f"[DEBUG] Retrieved 1 item from {endpoint}.")
            return [data]
    except Exception as e:
        print(f"[ERROR] Could not parse JSON from {endpoint}: {e}")
        return []

###########################
# Retrieve and Store Resources
###########################
def retrieve_and_store_services(org_id, token, output_dir):
    services = get_mist_data(org_id, token, "services")
    for svc in services:
        store_config_as_json('app', svc, output_dir)

def retrieve_and_store_networks(org_id, token, output_dir):
    networks = get_mist_data(org_id, token, "networks")
    for net in networks:
        store_config_as_json('net', net, output_dir)

def retrieve_and_store_sites(org_id, token, output_dir):
    sites = get_mist_data(org_id, token, "sites")
    for site in sites:
        store_config_as_json('site', site, output_dir)

def retrieve_and_store_hubs(org_id, token, output_dir):
    base_url = "https://api.mist.com/api/v1"
    url = f"{base_url}/orgs/{org_id}/deviceprofiles?type=gateway"
    headers = {'Authorization': f'Token {token}'}
    print(f"[DEBUG] Sending GET request to {url}")
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print(f"[ERROR] Failed to GET hub profiles, code={resp.status_code}, text={resp.text}")
        return
    try:
        hubs = resp.json()
        if not isinstance(hubs, list):
            print(f"[WARNING] Unexpected response structure for hub profiles: {hubs}")
            return
        for hub in hubs:
            store_config_as_json('hub', hub, output_dir)
    except Exception as e:
        print(f"[ERROR] Could not parse JSON for hub profiles: {e}")

def retrieve_and_store_wan(org_id, token, output_dir):
    wan = get_mist_data(org_id, token, "gatewaytemplates")
    for w in wan:
        store_config_as_json('wan', w, output_dir)

###########################
# Read JSON Files by Prefix
###########################
def read_json_files(prefix):
    """Reads JSON files matching the given prefix."""
    data_list = []
    for file_name in sorted(os.listdir('.')):
        if file_name.lower().startswith(prefix + '-') and file_name.lower().endswith('.json'):
            print(f"[INFO] Found file '{file_name}' for prefix '{prefix}'")
            with open(file_name, 'r') as f:
                try:
                    data = json.load(f)
                    if isinstance(data, list):
                        data_list.extend(data)
                    else:
                        data_list.append(data)
                except json.JSONDecodeError as e:
                    print(f"[ERROR] Skipping invalid file '{file_name}': {e}")
    return data_list

###########################
# Submit JSON to Mist
###########################
def submit_json(data_list, org_id, endpoint, token):
    """Submits JSON data to the Mist API for the specified endpoint."""
    base_url = "https://api.mist.com/api/v1"
    url = f"{base_url}/orgs/{org_id}/{endpoint}"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Token {token}'
    }

    for item in data_list:
        print(f"[INFO] Submitting to {endpoint}: {item.get('name', '(no name)')}")
        resp = requests.post(url, headers=headers, json=item)
        print(f"[DEBUG] Response: {resp.status_code} | {resp.text}")
        if resp.status_code in (200, 201):
            print(f"[INFO] Successfully posted to {endpoint}.")
        else:
            print(f"[ERROR] Failed to post to {endpoint}.")

###########################
# Main Logic
###########################
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--get', action='store_true', help="Retrieve existing config from Mist org")
    parser.add_argument('--post', action='store_true', help="Post JSON configs to Mist org")
    args = parser.parse_args()

    token, org_id = read_token_org("Token-Org.txt")
    print(f"[INFO] Using org_id={org_id}")
    print(f"[INFO] Using token={token[:6]}... (truncated)")

    # -------------------------------------------
    # GET Mode: Retrieve and Store Config
    # -------------------------------------------
    if args.get:
        print("\n[INFO] Retrieving config from Mist...")
        backup_folder = create_backup_folder()  # Create backup folder
        retrieve_and_store_services(org_id, token, backup_folder)
        retrieve_and_store_networks(org_id, token, backup_folder)
        retrieve_and_store_sites(org_id, token, backup_folder)
        retrieve_and_store_hubs(org_id, token, backup_folder)
        retrieve_and_store_wan(org_id, token, backup_folder)

    # -------------------------------------------
    # POST Mode: Validate and Submit Config
    # -------------------------------------------
    if args.post:
        print("\n[INFO] Validating and posting JSON files from the local directory...")
        for prefix, endpoint in [
            ('app', 'services'),
            ('net', 'networks'),
            ('site', 'sites'),
            ('hub', 'deviceprofiles'),
            ('wan', 'gatewaytemplates'),
        ]:
            data_list = read_json_files(prefix)
            if data_list:
                print(f"[INFO] Found {len(data_list)} '{prefix}' JSON file(s) to post.")
                submit_json(data_list, org_id, endpoint, token)
            else:
                print(f"[INFO] No valid '{prefix}' JSON files found in the local directory.")

if __name__ == "__main__":
    main()
