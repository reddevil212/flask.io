import socket
from flask import Flask, jsonify, request
from flask_cors import CORS
from ytmusicapi import YTMusic
import yt_dlp
import base64
import os

app = Flask(__name__)
CORS(app)
# Initialize YTMusic API
ytmusic = YTMusic()

def get_download_url(url):
    try:
        # Retrieve the base64 encoded cookies from the environment variable
        cookies_base64 = os.getenv('YT_COOKIES')
        
        if not cookies_base64:
            raise Exception("Base64 encoded cookies are not found in environment variable.")

        # Decode the base64 string to get the raw cookies
        cookies_string = base64.b64decode(cookies_base64).decode('utf-8')

        # Write the cookies to a temporary cookies.txt file
        cookies_file_path = '/tmp/cookies.txt'  # You can adjust this path as needed
        with open(cookies_file_path, 'w') as f:
            f.write(cookies_string)

        # Set yt-dlp options to use the cookies.txt file
        ydl_opts = {
            'format': 'bestaudio/best',  # Only download the best audio available
            'noplaylist': True,          # Don't process playlists
            'cookiefile': cookies_file_path,  # Use the temporary cookies file
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)  # Extract metadata without downloading
            audio_url = info.get('url')  # Get the audio URL

            if not audio_url:
                raise Exception("No audio URL found.")
            
            return {
                "title": info.get('title'),
                "download_url": audio_url
            }

    except Exception as e:
        return {"error": str(e)}
# Health check endpoint
@app.route('/', methods=['GET'])
def health_check():
    try:
        return jsonify({"status": "success", "message": "The API is up and running!"}), 200
    except Exception as e:
        return jsonify({"status": "fail", "message": f"Health check failed: {str(e)}"}), 503

# Endpoint to search for songs, artists, and albums
@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query')
    results = ytmusic.search(query)
    return jsonify(results)

@app.route('/search_suggestions', methods=['GET'])
def search_suggestions():
    query = request.args.get('query')
    detailed_runs = request.args.get('detailed_runs', default=False, type=lambda x: (x.lower() == 'true'))

    if not query:
        return jsonify({'error': 'Query parameter is required'}), 400

    try:
        suggestions = ytmusic.get_search_suggestions(query, detailed_runs)
        return jsonify(suggestions)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download_url', methods=['POST'])
def download_url():
    """Handle the request to get the audio download URL."""
    data = request.json
    video_url = data.get('url')  # Get the YouTube URL from the POST body

    if not video_url:
        return jsonify({"error": "URL is required"}), 400  # Return error if URL is not provided

    # Call the function to get the download URL
    res = get_download_url(video_url)

    # If there's an error, return it with a 500 status code
    if "error" in res:
        return jsonify(res), 500
    else:
        # Otherwise, return the title and download URL in the response
        return jsonify(res), 200

@app.route('/get_artist', methods=['GET'])
def get_artist():
    artist_id = request.args.get('artistId')
    if not artist_id:
        return jsonify({'error': 'Artist ID parameter is required'}), 400

    try:
        artist_info = ytmusic.get_artist(artist_id)
        return jsonify(artist_info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Endpoint to retrieve artist albums
@app.route('/artists/<string:artist_id>/albums', methods=['GET'])
def get_artist_albums(artist_id):
    results = ytmusic.get_artist_albums(artist_id)
    return jsonify(results)

# Endpoint to retrieve album data
@app.route('/albums/<string:album_id>', methods=['GET'])
def get_album(album_id):
    results = ytmusic.get_album(album_id)
    return jsonify(results)

# Endpoint to retrieve album browse ID
@app.route('/albums/<string:album_id>/browse_id', methods=['GET'])
def get_album_browse_id(album_id):
    results = ytmusic.get_album_browse_id(album_id)
    return jsonify(results)

# Endpoint to retrieve song data
@app.route('/songs/<string:song_id>', methods=['GET'])
def get_song(song_id):
    results = ytmusic.get_song(song_id)
    return jsonify(results)

# Endpoint to retrieve related songs
@app.route('/songs/<string:song_id>/related', methods=['GET'])
def get_song_related(song_id):
    results = ytmusic.get_song_related(song_id)
    return jsonify(results)

def find_available_port(start_port=5000, max_tries=10):
    """Try to find an available port starting from `start_port`."""
    for port in range(start_port, start_port + max_tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('127.0.0.1', port)) != 0:
                return port
    return None

if __name__ == '__main__':
    # Find available port
    port = find_available_port()

    if port:
        print(f"Running on port {port}")
        app.run(debug=True, host='0.0.0.0', port=port, use_reloader=False)
    else:
        print("No available ports found!")
