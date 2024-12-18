import os
import yt_dlp
from flask import Flask, jsonify, request
from flask_cors import CORS
from ytmusicapi import YTMusic
import socket
import tempfile
from google.cloud import storage
import base64

app = Flask(__name__)
CORS(app)

# Initialize YTMusic API
ytmusic = YTMusic()

# Configure a temporary directory for storing uploaded files
TEMP_DIR = tempfile.mkdtemp()

# Helper function to validate YouTube URL
def is_valid_youtube_url(url):
    return 'youtube.com' in url or 'youtu.be' in url

# Helper function to download the cookies file from a URL
def download_cookies_from_url(url, download_path):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad responses
        with open(download_path, 'wb') as f:
            f.write(response.content)
        return download_path
    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to download cookies from URL: {str(e)}"}

def get_best_audio_stream_url(video_url, cookies_file_path):
    try:
        # Setup yt-dlp options with the cookies file
        ydl_opts = {
            'format': 'bestaudio',  # Only focus on the best audio stream
            'quiet': True,  # Suppress unnecessary output
            'extractor_args': {
                'youtube': {
                    'noplaylist': True  # Disable playlist extraction
                }
            },
            'cookiefile': cookies_file_path  # Pass the cookies file here
        }

        # Use yt-dlp to extract video info
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=False)

            if 'formats' not in info_dict or not info_dict['formats']:
                raise ValueError("No formats found for this video.")

            # Get the URL of the best audio stream
            for format in info_dict['formats']:
                if format.get('acodec') != 'none' and format.get('url'):
                    return format['url']

            raise ValueError("No suitable audio stream found for this video.")

    except Exception as e:
        return {"error": str(e)}

@app.route('/get_audio', methods=['POST'])
def get_audio_stream_url():
    video_url = request.form.get('url')
    cookies_file = request.files.get('cookies.txt')
    cookies_url = request.form.get('cookies_url')

    if not video_url:
        return jsonify({'error': 'No video URL provided'}), 400

    if not cookies_file and not cookies_url:
        return jsonify({'error': 'No cookies.txt file or cookies_url provided'}), 400

    # Check if we need to download the cookies.txt from URL or save the uploaded file
    cookies_file_path = None
    if cookies_file:
        # Save the cookies.txt file temporarily
        cookies_file_path = os.path.join(TEMP_DIR, secure_filename(cookies_file.filename))
        cookies_file.save(cookies_file_path)
    elif cookies_url:
        # Download the cookies.txt file from the provided URL
        cookies_file_path = os.path.join(TEMP_DIR, 'cookies.txt')
        result = download_cookies_from_url(cookies_url, cookies_file_path)
        if isinstance(result, dict) and 'error' in result:
            return jsonify(result), 400

    # Validate the YouTube URL
    if not is_valid_youtube_url(video_url):
        return jsonify({'error': 'Invalid YouTube URL'}), 400

    # Get the best audio stream URL for the video
    stream_url = get_best_audio_stream_url(video_url, cookies_file_path)
    
    if "error" in stream_url:
        return jsonify(stream_url), 400

    return jsonify({'stream_url': stream_url})

@app.route('/', methods=['GET'])
def health_check():
    try:
        return jsonify({"status": "success", "message": "The API is up and running!"}), 200
    except Exception as e:
        return jsonify({"status": "fail", "message": f"Health check failed: {str(e)}"}), 503

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

@app.route('/artists/<string:artist_id>/albums', methods=['GET'])
def get_artist_albums(artist_id):
    results = ytmusic.get_artist_albums(artist_id)
    return jsonify(results)

@app.route('/albums/<string:album_id>', methods=['GET'])
def get_album(album_id):
    results = ytmusic.get_album(album_id)
    return jsonify(results)

@app.route('/albums/<string:album_id>/browse_id', methods=['GET'])
def get_album_browse_id(album_id):
    results = ytmusic.get_album_browse_id(album_id)
    return jsonify(results)

@app.route('/songs/<string:song_id>', methods=['GET'])
def get_song(song_id):
    results = ytmusic.get_song(song_id)
    return jsonify(results)

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
        app.run(debug=True, host='0.0.0.0', port=port)
    else:
        print("No available port found.")
