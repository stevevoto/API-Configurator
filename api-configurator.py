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
# New/Modified Features:
# 1) Reads org_id and token from Token-Org.txt (instead of prompting or hard-coding).
# 2) Reads JSON payloads from local files (app-*.json, net-*.json, site-*.json, hub-*.json, wan-*.json).
# 3) *Optional* conversion of Python booleans to "true"/"false" strings (controlled by CONVERT_BOOLEANS).
# 4) Adds debug prints showing requests and responses.
# 5) Maintains original name-increment logic for WAN edges in case of name conflicts.
#
# Usage:
#   python3 api-configurator.py
#   python3 api-configurator.py --convert-bool (don't use this other than for testing)
###########################

import os
import json
import requests

###########################
# Global Config Toggle
###########################
# Set to True if you want to convert Python True/False to "true"/"false" in the JSON payloads.
# Set to False if you want to keep them as normal JSON booleans.
CONVERT_BOOLEANS = False

# ----------------------
# 1. Read Token and Org ID from Token-Org.txt
# ----------------------
def read_token_org(file_path="Token-Org.txt"):
    """Reads the token and org_id from the specified file (key=value lines)."""
    token = None
    org_id = None

    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('token='):
                token = line.split('=', 1)[1].strip()
            elif line.startswith('org_id='):
                org_id = line.split('=', 1)[1].strip()

    if not token or not org_id:
        raise ValueError("Could not find 'token' or 'org_id' in Token-Org.txt.")
    return token, org_id


# ----------------------
# 2. Recursively Convert Python Booleans to "true"/"false" Strings
# ----------------------
def bools_to_strings(data):
    """
    Recursively walk 'data' (which can be a dict, list, or primitive),
    converting any Python bool True/False to the strings "true" / "false".
    """
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, bool):
                data[k] = "true" if v else "false"
            elif isinstance(v, (dict, list)):
                bools_to_strings(v)
    elif isinstance(data, list):
        for i in range(len(data)):
            if isinstance(data[i], bool):
                data[i] = "true" if data[i] else "false"
            elif isinstance(data[i], (dict, list)):
                bools_to_strings(data[i])
    # If it's neither dict nor list, do nothing (string, int, float, etc.)


# ----------------------
# 3. Read and parse JSON files by prefix
# ----------------------
def read_json_files(prefix):
    """
    Return a list of JSON objects from all matching files: prefix-*.json
    e.g. prefix='app' -> look for app-*.json in current directory
    """
    data_list = []

    for file_name in sorted(os.listdir('.')):
        # Check if file starts with prefix- and ends in .json
        if file_name.lower().startswith(prefix + '-') and file_name.lower().endswith('.json'):
            print(f"[INFO] Found file '{file_name}' for prefix '{prefix}'")
            with open(file_name, 'r') as f:
                raw_text = f.read()
                try:
                    # Parse standard JSON to Python (booleans remain True/False)
                    loaded = json.loads(raw_text)
                except Exception as e:
                    print(f"[ERROR] Could not parse {file_name}: {e}")
                    continue

                # The file might contain either one dict or a list of dicts
                if isinstance(loaded, dict):
                    data_list.append(loaded)
                elif isinstance(loaded, list):
                    data_list.extend(loaded)
                else:
                    print(f"[WARNING] {file_name} has an unsupported JSON structure (not object or list).")

    return data_list


# ----------------------
# 4. Submit JSON data to Mist (POST)
# ----------------------
def submit_json(data_list, org_id, endpoint, token):
    """
    Submits each item in data_list to the specified Mist endpoint via POST.
    For example: endpoint='services' => /api/v1/orgs/{org_id}/services
    """
    base_url = "https://api.mist.com/api/v1"  # or "https://api.ac2.mist.com/api/v1" if EU region
    url = f"{base_url}/orgs/{org_id}/{endpoint}"

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Token {token}'
    }

    for item in data_list:
        # 1) Convert all Python booleans to "true"/"false" strings if enabled
        if CONVERT_BOOLEANS:
            bools_to_strings(item)

        # 2) Debug print
        print(f"\n[DEBUG] Submitting to endpoint={endpoint} URL={url}")
        print(f"[DEBUG] Payload:\n{json.dumps(item, indent=2)}")

        # 3) Post the data
        # Note: We pass 'json.dumps(item)' so that we don't inadvertently reconvert
        #       strings back to booleans if they were converted
        resp = requests.post(url, headers=headers, data=json.dumps(item))
        print(f"[DEBUG] Response code: {resp.status_code}")
        print(f"[DEBUG] Response text: {resp.text}")

        if resp.status_code in (200, 201):
            print(f"[INFO] Successfully created in {endpoint}")
        else:
            print(f"[ERROR] Failed to create in {endpoint}. Status {resp.status_code}")


# ----------------------
# 5. Submit Hub Profile(s) to /deviceprofiles
# ----------------------
def submit_hub_profiles(hub_data, org_id, token):
    """
    Hub profiles are posted to /deviceprofiles instead of /services/networks/sites/etc.
    This replicates the original approach for the 'Hub Profile Section'.
    """
    base_url = "https://api.mist.com/api/v1"  # or "https://api.ac2.mist.com/api/v1" if EU
    url = f"{base_url}/orgs/{org_id}/deviceprofiles"

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Token {token}'
    }

    for item in hub_data:
        # Convert booleans to strings if enabled
        if CONVERT_BOOLEANS:
            bools_to_strings(item)

        print(f"\n[DEBUG] Submitting Hub Profile to: {url}")
        print(f"[DEBUG] Payload:\n{json.dumps(item, indent=2)}")

        resp = requests.post(url, headers=headers, data=json.dumps(item))
        print(f"[DEBUG] Response code: {resp.status_code}")
        print(f"[DEBUG] Response text: {resp.text}")

        if resp.status_code in (200, 201):
            print("[INFO] Hub Profile created successfully.")
        else:
            print(f"[ERROR] Failed to create Hub Profile. {resp.status_code}")


# ----------------------
# 6. Submit WAN Edges (gateway templates) with name-increment logic
# ----------------------
def submit_wan_edges(wan_data, org_id, token):
    """
    This replicates the original 'WAN Edges Section' approach,
    including the name increment logic for potential naming conflicts.
    """
    base_url = "https://api.mist.com/api/v1"  # or "https://api.ac2.mist.com/api/v1" if EU
    url = f"{base_url}/orgs/{org_id}/gatewaytemplates"

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Token {token}'
    }

    for item in wan_data:
        base_name = item.get('name', 'unnamed')
        counter = 1

        while True:
            if counter > 1:
                new_name = f"{base_name}-{counter}"
                item['name'] = new_name

            # Convert booleans to strings if enabled
            if CONVERT_BOOLEANS:
                bools_to_strings(item)

            print(f"\n[DEBUG] Submitting WAN Edge to: {url}")
            print(f"[DEBUG] Payload:\n{json.dumps(item, indent=2)}")

            resp = requests.post(url, headers=headers, data=json.dumps(item))
            print(f"[DEBUG] Response code: {resp.status_code}")
            print(f"[DEBUG] Response text: {resp.text}")

            if resp.status_code in (200, 201):
                print("[INFO] WAN Edge template created successfully.")
                break
            elif resp.status_code == 400:
                detail = resp.json().get("detail", "")
                if "name" in detail.lower():
                    print(f"[WARNING] Name '{item['name']}' is already used. Incrementing name...")
                    counter += 1
                    continue
                else:
                    print(f"[ERROR] 400 error but not a name conflict: {detail}")
                    break
            else:
                print(f"[ERROR] Failed to create WAN Edge. Status {resp.status_code}")
                break


# ----------------------
# Main
# ----------------------
def main():
    # 1. Load token and org_id from Token-Org.txt
    token, org_id = read_token_org("Token-Org.txt")
    print(f"[INFO] Using org_id={org_id}")
    print(f"[INFO] Using token={token[:6]}... (truncated)")

    # 2. Read and submit "Applications" (services)
    services_data = read_json_files('app')
    if services_data:
        submit_json(services_data, org_id, "services", token)
    else:
        print("[INFO] No 'app-*.json' files found; skipping Applications section.")

    # 3. Read and submit "Networks"
    networks_data = read_json_files('net')
    if networks_data:
        submit_json(networks_data, org_id, "networks", token)
    else:
        print("[INFO] No 'net-*.json' files found; skipping Networks section.")

    # 4. Read and submit "Sites"
    sites_data = read_json_files('site')
    if sites_data:
        submit_json(sites_data, org_id, "sites", token)
    else:
        print("[INFO] No 'site-*.json' files found; skipping Sites section.")

    # 5. Read and submit "Hub Profiles"
    hub_data = read_json_files('hub')
    if hub_data:
        submit_hub_profiles(hub_data, org_id, token)
    else:
        print("[INFO] No 'hub-*.json' files found; skipping Hub Profile section.")

    # 6. Read and submit "WAN Edges"
    wan_data = read_json_files('wan')
    if wan_data:
        submit_wan_edges(wan_data, org_id, token)
    else:
        print("[INFO] No 'wan-*.json' files found; skipping WAN Edges section.")


if __name__ == "__main__":
    main()
