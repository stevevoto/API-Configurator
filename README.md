# API-Configurator
# README: Mist Configuration Automation via API

## Overview

This **Python 3** script automates configuration tasks in **Mist** (Juniper Mist) through its **MIST API**.  
This app supports creating:

- **Applications/Services**  
- **Networks**  
- **Sites**  
- **Hub Profiles (device profiles)**  
- **WAN Edge templates**

Each resource is stored in a separate JSON file (e.g., `net-*.json`, `hub-*.json`, etc.).  
The script reads these files, **converts Python booleans to string values** where necessary (`"true"/"false"`) before **POST**ing them, and then **submits** each to the Mist API under your Org.

---

## Key Features

1. **Token & Org ID From File**  
   - This file reads your personal **API token** and **Org ID** from a text file (`Token-Org.txt`), preventing the need to hard-code credentials.

2. **Automatic JSON File Discovery**  
   - Looks for JSON files in the current directory named with a prefix, e.g.:
     - `app-*.json` for **Applications**  
     - `net-*.json` for **Networks**  
     - `site-*.json` for **Sites**  
     - `hub-*.json` for **Hub Profiles**  
     - `wan-*.json` for **WAN Edges**  
   - Loads each matching file and merges them into a list.

3. **Boolean Conversion**  
   - Automatically transforms **Python booleans** (parsed from standard JSON `true/false`) into string booleans (`"true"/"false"`) before posting to the Mist API.

4. **Endpoints**  
   - Applications (services) → `POST /api/v1/orgs/{org_id}/services`  
   - Networks (networks) → `POST /api/v1/orgs/{org_id}/networks`  
   - Sites (sites) → `POST /api/v1/orgs/{org_id}/sites`  
   - Hub Profiles → `POST /api/v1/orgs/{org_id}/deviceprofiles`  
   - WAN Edges → `POST /api/v1/orgs/{org_id}/gatewaytemplates`

5. **WAN Edge Name Increment**  
   - If a WAN Edge “name” is already taken, the script increments it (`myEdge → myEdge-2 → myEdge-3`, etc.) until successful.

6. **Debug Output**  
   - Prints the payload (in JSON) before each **POST**.  
   - Prints the response code and body for troubleshooting.

---

## Prerequisites

- **Python 3** installed (e.g. Python 3.7+).
- A **Mist API token** with necessary permissions (Org Admin or similar).
- An **Org ID** that the token has permission to manage.
- A file named **`Token-Org.txt`** containing:
  ```makefile
  token=<YOUR_API_TOKEN>
  org_id=<YOUR_ORG_ID>
