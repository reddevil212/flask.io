import yt_dlp
from flask import Flask, request, jsonify
import tempfile
import os
import requests
from werkzeug.utils import secure_filename
import ytmusicapi  # Importing ytmusicapi

app = Flask(__name__)

# Initialize the YTMusic API client
ytmusic = ytmusicapi.YTMusic()  # Assuming 'headers_auth.json' is available

# Temporary directory for storing uploaded files
TEMP_DIR = tempfile.mkdtemp()

# Helper function to download cookies from a URL
def download_cookies_from_url(url, download_path):
    try:
        # Download the cookies file from the URL
        print(f"[DEBUG] Downloading cookies from: {url}")
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad responses
        with open(download_path, 'wb') as f:
            f.write(response.content)
        print(f"[DEBUG] Cookies saved to: {download_path}")
        return download_path
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to download cookies: {str(e)}")
        return {"error": f"Failed to download cookies from URL: {str(e)}"}

# Function to extract M3U8 URL or the best available stream URL
def get_stream_url(yt_url, cookies_file_path=None):
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': False,
        'quiet': True,  # Disable output
        'forcejson': True,  # Get metadata in JSON format
    }

    if cookies_file_path:
        ydl_opts['cookiefile'] = cookies_file_path  # Use cookies if provided

    try:
        print(f"[DEBUG] Extracting stream URL for: {yt_url}")
        if cookies_file_path:
            print(f"[DEBUG] Using cookies from: {cookies_file_path}")
        else:
            print("[DEBUG] No cookies provided.")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print("[DEBUG] Calling yt-dlp to extract info...")
            info_dict = ydl.extract_info(yt_url, download=False)

            print(f"[DEBUG] Extracted info: {info_dict}")

            if 'formats' in info_dict:
                for format in info_dict['formats']:
                    print(f"[DEBUG] Available format: {format}")
                    if format.get('format_id') and 'm3u8' in format.get('url', ''):
                        print(f"[DEBUG] Found M3U8 stream URL: {format['url']}")
                        return format['url']

            print("[DEBUG] No M3U8 stream URL found.")
            return None
    except Exception as e:
        print(f"[ERROR] Failed to get stream URL: {e}")
        return str(e)

@app.route('/stream_url', methods=['POST'])
def stream_url():
    # Extract the 'url' parameter from form data
    yt_url = request.form.get('url', '')
    cookies_file = request.files.get('cookies.txt')  # Get uploaded cookies file
    cookies_url = request.form.get('cookies_url')  # Get cookies URL from form data

    print(f"[DEBUG] Received request for URL: {yt_url}")
    if cookies_file:
        print(f"[DEBUG] Received cookies file: {cookies_file.filename}")
    if cookies_url:
        print(f"[DEBUG] Received cookies URL: {cookies_url}")

    if not yt_url:
        return jsonify({'error': 'YouTube URL is required'}), 400

    # Handle cookies - either uploaded or downloaded
    cookies_file_path = None
    if cookies_file:
        # Save the cookies file temporarily
        cookies_file_path = os.path.join(TEMP_DIR, secure_filename(cookies_file.filename))
        cookies_file.save(cookies_file_path)
        print(f"[DEBUG] Saved cookies file to: {cookies_file_path}")
    elif cookies_url:
        cookies_file_path = os.path.join(TEMP_DIR, 'cookies.txt')
        result = download_cookies_from_url(cookies_url, cookies_file_path)
        if isinstance(result, dict) and 'error' in result:
            return jsonify(result), 400

    # Get the stream URL (M3U8 URL or the best available stream URL)
    print(f"[DEBUG] Calling get_stream_url with cookies: {cookies_file_path}")
    stream_url = get_stream_url(yt_url, cookies_file_path)

    if stream_url:
        print(f"[DEBUG] Returning stream URL: {stream_url}")
        return jsonify({'stream_url': stream_url}), 200
    else:
        print("[DEBUG] No stream URL found or failed to fetch URL")
        return jsonify({'error': 'Stream URL not found or failed to fetch URL'}), 400

@app.route('/', methods=['GET'])
def health_check():
    try:
        return jsonify({"status": "success", "message": "The API is up and running!"}), 200
    except Exception as e:
        return jsonify({"status": "fail", "message": f"Health check failed: {str(e)}"}), 503


@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query')
    if not query:
        return jsonify({'error': 'Query parameter is required'}), 400

    try:
        search_results = ytmusic.search(query)
        return jsonify(search_results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Add missing endpoints for search suggestions, artist and album info
@app.route('/search_suggestions', methods=['GET'])
def search_suggestions():
    query = request.args.get('query')
    if not query:
        return jsonify({'error': 'Query parameter is required'}), 400

    try:
        suggestions = ytmusic.search(query, filter='suggestions')
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

@app.route('/get_artist_albums', methods=['GET'])
def get_artist_albums():
    artist_id = request.args.get('artistId')
    if not artist_id:
        return jsonify({'error': 'Artist ID parameter is required'}), 400

    try:
        artist_albums = ytmusic.get_artist_albums(artist_id)
        return jsonify(artist_albums)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_album', methods=['GET'])
def get_album():
    album_id = request.args.get('albumId')
    if not album_id:
        return jsonify({'error': 'Album ID parameter is required'}), 400

    try:
        album_info = ytmusic.get_album(album_id)
        return jsonify(album_info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_album_browse_id', methods=['GET'])
def get_album_browse_id():
    album_id = request.args.get('albumId')
    if not album_id:
        return jsonify({'error': 'Album ID parameter is required'}), 400

    try:
        browse_id = ytmusic.get_album_browse_id(album_id)
        return jsonify({'browseId': browse_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_user', methods=['GET'])
def get_user():
    try:
        user_info = ytmusic.get_user()
        return jsonify(user_info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_user_playlists', methods=['GET'])
def get_user_playlists():
    try:
        playlists = ytmusic.get_library_playlists()
        return jsonify(playlists)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_song', methods=['GET'])
def get_song():
    song_id = request.args.get('songId')
    if not song_id:
        return jsonify({'error': 'Song ID parameter is required'}), 400

    try:
        song_info = ytmusic.get_song(song_id)
        return jsonify(song_info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_song_related', methods=['GET'])
def get_song_related():
    video_id = request.args.get('videoId')
    if not video_id:
        return jsonify({'error': 'Video ID parameter is required'}), 400

    try:
        related_songs = ytmusic.get_related(videoId=video_id)
        return jsonify(related_songs)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_lyrics', methods=['GET'])
def get_lyrics():
    video_id = request.args.get('videoId')
    if not video_id:
        return jsonify({'error': 'Video ID parameter is required'}), 400

    try:
        lyrics = ytmusic.get_lyrics(videoId=video_id)
        return jsonify({'lyrics': lyrics})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
