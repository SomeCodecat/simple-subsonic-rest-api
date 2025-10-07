from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import hashlib
import random
import string
import os

SUBSONIC_URL = os.environ.get("SUBSONIC_URL")
SUBSONIC_USERNAME = os.environ.get("SUBSONIC_USERNAME")
SUBSONIC_PASSWORD = os.environ.get("SUBSONIC_PASSWORD")
SUBSONIC_PROXY_API_KEY = os.environ.get("SUBSONIC_PROXY_API_KEY")
CACHE_TIMEOUT = int(os.environ.get("CACHE_TIMEOUT_SECONDS", 900))

LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = 8000

if not all([SUBSONIC_URL, SUBSONIC_USERNAME, SUBSONIC_PASSWORD, SUBSONIC_PROXY_API_KEY]):
    raise ValueError("Error: Ensure SUBSONIC_URL, SUBSONIC_USERNAME, SUBSONIC_PASSWORD, and SUBSONIC_PROXY_API_KEY are set.")

config = {
    "CACHE_TYPE": "SimpleCache",
    "CACHE_DEFAULT_TIMEOUT": CACHE_TIMEOUT
}

app = Flask(__name__)
app.config.from_mapping(config)
CORS(app)
cache = Cache(app)

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if request.headers.get('X-Api-Key') and request.headers.get('X-Api-Key') == SUBSONIC_PROXY_API_KEY:
            return f(*args, **kwargs)
        else:
            app.logger.warning(f"Unauthorized access attempt from {client_ip}")
            return jsonify({"error": "Unauthorized"}), 401
    return decorated_function

def subsonic_request(endpoint, extra_params=None):
    salt = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(6))
    token = hashlib.md5((SUBSONIC_PASSWORD + salt).encode('utf-8')).hexdigest()
    params = {"u": SUBSONIC_USERNAME, "t": token, "s": salt, "v": "1.16.1", "c": "glance-proxy", "f": "json"}
    if extra_params:
        params.update(extra_params)
    
    url_to_call = f"{SUBSONIC_URL}/rest/{endpoint}"
    app.logger.info(f"Proxy is calling Subsonic API: {url_to_call}")

    try:
        response = requests.get(url_to_call, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if data.get('subsonic-response', {}).get('status') == 'failed':
            error_msg = data.get('subsonic-response', {}).get('error', {}).get('message', 'Unknown API error')
            app.logger.error(f"Subsonic API returned a failure status: {error_msg}")
            return None
        
        app.logger.info(f"Successfully received data from endpoint: {endpoint}")
        return data.get('subsonic-response', {})
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error connecting to Subsonic server at {SUBSONIC_URL}: {e}")
        return None

@app.route('/config')
@require_api_key
def get_config():
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    app.logger.info(f"Request for /config from {client_ip}")
    return jsonify({'baseUrl': SUBSONIC_URL})

@app.route('/artists')
@require_api_key
@cache.cached()
def get_artist_list():
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    app.logger.info(f"Request for /artists from {client_ip} (cache miss)")
    artists_data = subsonic_request("getArtists")
    artist_list = []
    if artists_data and 'artists' in artists_data and 'index' in artists_data['artists']:
        for index in artists_data['artists']['index']:
            for artist in index.get('artist', []):
                artist_list.append({'id': artist.get('id'), 'name': artist.get('name', 'Unknown Artist')})
    return jsonify(sorted(artist_list, key=lambda item: str(item.get('name', '')).lower()))

@app.route('/albums')
@require_api_key
@cache.cached()
def get_album_list():
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    app.logger.info(f"Request for /albums from {client_ip} (cache miss)")
    album_data = subsonic_request("getAlbumList2", extra_params={"type": "alphabeticalByName", "size": "10000"})
    album_list = []
    if album_data and 'albumList2' in album_data and 'album' in album_data['albumList2']:
        for album in album_data['albumList2']['album']:
            album_list.append({
                'id': album.get('id'), 'name': album.get('name', 'Unknown Album'),
                'artistId': album.get('artistId'), 'artistName': album.get('artist', '')
            })
    return jsonify(sorted(album_list, key=lambda item: str(item.get('name', '')).lower()))

@app.route('/songs')
@require_api_key
@cache.cached()
def get_song_list():
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    app.logger.info(f"Request for /songs from {client_ip} (cache miss)")
    song_data = subsonic_request("getRandomSongs", extra_params={"size": "10000"})
    song_list = []
    if song_data and 'randomSongs' in song_data and 'song' in song_data['randomSongs']:
        for song in song_data['randomSongs']['song']:
            song_list.append({
                'name': song.get('title', 'Unknown Song'), 'albumId': song.get('albumId'),
                'context': song.get('album', '')
            })
    return jsonify(sorted(song_list, key=lambda item: str(item.get('name', '')).lower()))

@app.route('/stats')
@require_api_key
@cache.cached()
def get_stats():
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    app.logger.info(f"Request for /stats from {client_ip} (cache miss)")
    stats = {"artistCount": 0, "albumCount": 0, "songCount": 0}
    artists_data = subsonic_request("getArtists")
    if artists_data and 'artists' in artists_data and 'index' in artists_data['artists']:
        stats['artistCount'] = sum(len(index.get('artist', [])) for index in artists_data['artists']['index'])
    album_list_data = subsonic_request("getAlbumList2", extra_params={"type": "alphabeticalByName", "size": "10000"})
    if album_list_data and 'albumList2' in album_list_data and 'album' in album_list_data['albumList2']:
        stats['albumCount'] = len(album_list_data['albumList2']['album'])
    scan_status_data = subsonic_request("getScanStatus")
    if scan_status_data and 'scanStatus' in scan_status_data:
        stats['songCount'] = scan_status_data['scanStatus'].get('count', 0)
    return jsonify(stats)

if __name__ == '__main__':
    app.run(host=LISTEN_HOST, port=8000)