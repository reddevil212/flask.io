import os
import requests  # <-- Add this import statement for the requests library
import tempfile
from flask import Flask, jsonify, request
from flask_cors import CORS
from ytmusicapi import YTMusic
import yt_dlp
import socket

app = Flask(__name__)
CORS(app)
# Initialize YTMusic API
ytmusic = YTMusic()

def get_download_url(url, cookies_file):
    """Extract the best audio download URL from the YouTube video URL with cookies."""
    try:
        # yt-dlp options to get only the best audio format available
        ydl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'cookiefile': cookies_file  # Use the cookies file for authentication
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            audio_url = info.get('url')

            if not audio_url:
                raise Exception("No audio URL found.")

            return {
                "title": info.get('title'),
                "download_url": audio_url
            }
    except Exception as e:
        return {"error": str(e)}

@app.route('/download_url', methods=['POST'])
def download_url():
    """Handle the request to get the audio download URL."""
    url = request.form.get('url')

    # Fetch the cookies file URL from the environment variable or use a static URL
    cookies_url = os.getenv('COOKIES_URL', 'https://ki0dyxketspblp5x.public.blob.vercel-storage.com/cookies-9Sc6jE0VEn9Hk1Cn2lq2u1v7cU2lDf.txt')

    if not url:
        return jsonify({"error": "URL is required"}), 400

    if not cookies_url:
        return jsonify({"error": "Cookies file URL is required from the environment variable"}), 400

    # Fetch the cookies file from the URL
    try:
        response = requests.get(cookies_url)  # Fetch the cookies file
        response.raise_for_status()  # Will raise an error for bad status codes
        cookies_data = response.text
    except requests.RequestException as e:
        return jsonify({"error": f"Failed to fetch cookies file: {str(e)}"}), 500

    # Create a temporary file for cookies data
    try:
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            cookies_file_path = temp_file.name  # Get the path to the temporary file
            temp_file.write(cookies_data.encode())  # Write cookies data to the temp file

        # Call the function to get the download URL
        res = get_download_url(url, cookies_file_path)

        # Clean up: Remove the temporary file after use
        os.remove(cookies_file_path)

        if "error" in res:
            return jsonify(res), 500
        else:
            return jsonify(res), 200
    except Exception as e:
        return jsonify({"error": f"Failed to handle cookies file: {str(e)}"}), 500


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
