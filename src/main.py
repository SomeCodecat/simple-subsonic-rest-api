from flask import Flask, jsonify
from flask_cors import CORS
import requests
import hashlib
import random
import string
import os

NAVIDROME_URL = os.environ.get("NAVIDROME_URL")
USERNAME = os.environ.get("NAVIDROME_USERNAME")
API_KEY = os.environ.get("NAVIDROME_API_KEY")

LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = 9876

if not all([NAVIDROME_URL, USERNAME, API_KEY]):
    raise ValueError("Error: Ensure NAVIDROME_URL, NAVIDROME_USERNAME, and NAVIDROME_API_KEY are set.")

app = Flask(__name__)
CORS(app)

def subsonic_request(endpoint, extra_params=None):
    salt = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(6))
    token = hashlib.md5((API_KEY + salt).encode('utf-8')).hexdigest()
    params = {"u": USERNAME, "t": token, "s": salt, "v": "1.16.1", "c": "glance-proxy", "f": "json"}
    if extra_params:
        params.update(extra_params)
    try:
        response = requests.get(f"{NAVIDROME_URL}/rest/{endpoint}", params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        if data.get('subsonic-response', {}).get('status') == 'failed': return None
        return data.get('subsonic-response', {})
    except requests.exceptions.RequestException: return None

@app.route('/config')
def get_config():
    return jsonify({'baseUrl': NAVIDROME_URL})

@app.route('/artists')
def get_artist_list():
    artists_data = subsonic_request("getArtists")
    artist_list = []
    if artists_data and 'artists' in artists_data and 'index' in artists_data['artists']:
        for index in artists_data['artists']['index']:
            for artist in index.get('artist', []):
                artist_list.append({'id': artist.get('id'), 'name': artist.get('name', 'Unknown Artist')})
    return jsonify(sorted(artist_list, key=lambda x: str(x.get('name', '')).lower()))

@app.route('/albums')
def get_album_list():
    album_data = subsonic_request("getAlbumList2", extra_params={"type": "alphabeticalByName", "size": "10000"})
    album_list = []
    if album_data and 'albumList2' in album_data and 'album' in album_data['albumList2']:
        for album in album_data['albumList2']['album']:
            album_list.append({
                'id': album.get('id'), 'name': album.get('name', 'Unknown Album'),
                'artistId': album.get('artistId'), 'artistName': album.get('artist', '')
            })
    return jsonify(sorted(album_list, key=lambda x: str(x.get('name', '')).lower()))

@app.route('/songs')
def get_song_list():
    song_data = subsonic_request("getRandomSongs", extra_params={"size": "10000"})
    song_list = []
    if song_data and 'randomSongs' in song_data and 'song' in song_data['randomSongs']:
        for song in song_data['randomSongs']['song']:
            song_list.append({
                'name': song.get('title', 'Unknown Song'), 'albumId': song.get('albumId'),
                'context': song.get('album', '')
            })
    return jsonify(sorted(song_list, key=lambda x: str(x.get('name', '')).lower()))

@app.route('/stats')
def get_stats():
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
    app.run(host=LISTEN_HOST, port=LISTEN_PORT)