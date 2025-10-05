#!/usr/bin/env python3
from flask import Flask, jsonify
import requests
import hashlib
import random
import string
import os

# --- CONFIGURATION (from environment variables) ---
NAVIDROME_URL = os.environ.get("NAVIDROME_URL")
USERNAME = os.environ.get("NAVIDROME_USERNAME")
API_KEY = os.environ.get("NAVIDROME_API_KEY")

# Settings for this proxy script
LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = 9876
# --------------------------------------------------

if not all([NAVIDROME_URL, USERNAME, API_KEY]):
    raise ValueError("Error: Ensure NAVIDROME_URL, NAVIDROME_USERNAME, and NAVIDROME_API_KEY are set.")

app = Flask(__name__)

def subsonic_request(endpoint, extra_params=None):
    """Handles Subsonic authentication and makes an API request."""
    salt = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(6))
    token = hashlib.md5((API_KEY + salt).encode('utf-8')).hexdigest()

    params = {
        "u": USERNAME, "t": token, "s": salt,
        "v": "1.16.1", "c": "glance-proxy", "f": "json"
    }
    if extra_params:
        params.update(extra_params)

    try:
        response = requests.get(f"{NAVIDROME_URL}/rest/{endpoint}", params=params, timeout=20) # Increased timeout for larger requests
        response.raise_for_status()
        data = response.json()
        if data.get('subsonic-response', {}).get('status') == 'failed':
            print(f"Subsonic API Error on endpoint {endpoint}: {data.get('subsonic-response')}")
            return None
        return data.get('subsonic-response', {})
    except requests.exceptions.RequestException as e:
        print(f"Connection Error: {e}")
        return None

@app.route('/stats')
def get_stats():
    """Endpoint for Glance. Fetches and combines stats."""
    stats = {"artistCount": 0, "albumCount": 0, "songCount": 0}

    # CORRECT WAY: Get album count by fetching the full list and counting them
    album_list_data = subsonic_request("getAlbumList2", extra_params={"type": "alphabeticalByName", "size": "500"})
    if album_list_data and 'albumList2' in album_list_data and 'album' in album_list_data['albumList2']:
        stats['albumCount'] = len(album_list_data['albumList2']['album'])

    # CORRECT WAY: Get song count by fetching a large list of random songs and counting them
    song_list_data = subsonic_request("getRandomSongs", extra_params={"size": "10000"})
    if song_list_data and 'randomSongs' in song_list_data and 'song' in song_list_data['randomSongs']:
        stats['songCount'] = len(song_list_data['randomSongs']['song'])
    
    # This part was already working correctly
    artists_data = subsonic_request("getArtists")
    if artists_data and 'artists' in artists_data and 'index' in artists_data['artists']:
        total_artists = sum(len(index.get('artist', [])) for index in artists_data['artists']['index'])
        stats['artistCount'] = total_artists
        
    # A potential issue with getRandomSongs is that it's capped at 10000. If you have more songs, 
    # it won't be totally accurate. Let's try to get a more accurate number from getScanStatus.
    scan_status_data = subsonic_request("getScanStatus")
    if scan_status_data and 'scanStatus' in scan_status_data and 'count' in scan_status_data['scanStatus']:
        # The 'count' in getScanStatus usually refers to song count
        stats['songCount'] = scan_status_data['scanStatus']['count']

    return jsonify(stats)

if __name__ == '__main__':
    app.run(host=LISTEN_HOST, port=LISTEN_PORT)