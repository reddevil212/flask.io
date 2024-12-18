import os
import requests  # <-- Add this import statement for the requests library
import tempfile
import re
from flask import Flask, jsonify, request
from flask_cors import CORS
from ytmusicapi import YTMusic
import yt_dlp
import socket

app = Flask(__name__)
CORS(app)
# Initialize YTMusic API
ytmusic = YTMusic()

# Function to validate if the URL is a valid YouTube URL
def is_valid_youtube_url(url):
    youtube_regex = (
        r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
        r'(watch\?v=|embed/|v/|.+/videoseries\?v=)[a-zA-Z0-9_-]{11}')
    return re.match(youtube_regex, url) is not None

# A helper function to get the best stream URL
def get_best_stream_url(video_url, cookie_url=None):
    try:
        # Initialize cookie file path
        cookie_file_path = None
        
        # Check if cookie_url is provided
        if cookie_url:
            cookie_file_path = '/tmp/cookies.txt'  # Temporary location for the cookies file
            
            # Try to download the cookies file
            response = requests.get(cookie_url)
            
            if response.status_code == 200:
                # Save the cookies file locally
                with open(cookie_file_path, 'wb') as f:
                    f.write(response.content)
                print(f"Cookies file saved to {cookie_file_path}")  # Debug statement
            else:
                return {"error": f"Failed to download cookies file. HTTP Status: {response.status_code}"}
        
        # Check if cookie_file_path was set (cookies were downloaded)
        if not cookie_file_path:
            return {"error": "No cookie file path available, cookie_url might be missing or invalid"}

        # Setup yt-dlp options
        ydl_opts = {
            'format': 'bestaudio/best',  # Choose the best audio or video stream
            'quiet': True,  # Suppress unnecessary output
            'extractor_args': {
                'youtube': {
                    'noplaylist': True  # Disable playlist extraction
                }
            },
            'cookiefile': cookie_file_path  # Pass the downloaded cookie file here
        }

        # Use yt-dlp to extract video info
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=False)

            if 'formats' not in info_dict or not info_dict['formats']:
                raise ValueError("No formats found for this video.")

            # Get the URL of the best stream
            for format in info_dict['formats']:
                if format.get('acodec') != 'none' and format.get('url'):
                    return format['url']

            raise ValueError("No suitable stream found for this video.")

    except Exception as e:
        return {"error": str(e)}

@app.route('/get_stream_url', methods=['GET'])
def get_stream_url():
    video_url = request.args.get('url')
    
    if not video_url:
        return jsonify({'error': 'No video URL provided'}), 400

    # Validate the YouTube URL
    if not is_valid_youtube_url(video_url):
        return jsonify({'error': 'Invalid YouTube URL'}), 400

    # Get the best stream URL for the video
    stream_url = get_best_stream_url(video_url)
    
    if "http" not in stream_url:
        return jsonify({'error': stream_url}), 400  # Error message from yt-dlp

    return jsonify({'stream_url': stream_url})

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
