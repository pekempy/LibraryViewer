# plex_library.py

import os
import requests

def plex_login(config):
    """
    Placeholder for Plex login/connection logic.
    Currently loads base URL and token from config.
    """
    plex_url = config.get("plex", {}).get("url", "").rstrip("/")
    plex_token = config.get("plex", {}).get("token", "")

    if not plex_url or not plex_token:
        raise ValueError("Missing Plex URL or token in config")

    headers = {
        "X-Plex-Token": plex_token,
        "Accept": "application/json"
    }

    print(f"🔐 Ready to connect to Plex at {plex_url}")
    return plex_url, headers


def fetch_plex_items(config):
    """
    Placeholder to fetch items from Plex once logic is implemented.
    """
    plex_url, headers = plex_login(config)

    # Example: list libraries
    response = requests.get(f"{plex_url}/library/sections", headers=headers)
    if response.status_code != 200:
        print(f"❌ Failed to fetch libraries: {response.status_code}")
        return []

    data = response.json()
    print(f"📁 Available Plex Libraries: {data}")
    return data
