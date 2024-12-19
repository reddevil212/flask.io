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

# Configure a temporary directory for storing uploaded files
TEMP_DIR = tempfile.mkdtemp()

# Helper function to validate YouTube URL
def is_valid_youtube_url(url):
    print(f"Validating YouTube URL: {url}")
    return 'youtube.com' in url or 'youtu.be' in url

# Helper function to download the cookies file from a URL
def download_cookies_from_url(url, download_path):
    print(f"Attempting to download cookies from URL: {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad responses
        with open(download_path, 'wb') as f:
            f.write(response.content)
        
        print(f"Successfully downloaded cookies to: {download_path}")
        return download_path
    except requests.exceptions.RequestException as e:
        print(f"Error downloading cookies file from URL: {str(e)}")
        return {"error": f"Failed to download cookies from URL: {str(e)}"}

# Function to get the best audio URL from a YouTube video
def get_audio_url_from_json(video_url, cookies_file_path):
    print(f"Fetching audio URL for video: {video_url}")
    
    ydl_opts = {
        'format': 'bestaudio',  # Focus on the best available audio format
        'noplaylist': True,     # Disable playlist downloads
        'quiet': False,         # Set verbosity to True for debugging
        'cookiefile': cookies_file_path,  # Include cookies if provided
        'forcejson': True,      # Request JSON format response
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            # Extract video info (without downloading)
            info_dict = ydl.extract_info(video_url, download=False)
           

            # Iterate over formats to find the first audio-only stream
            for format in info_dict['formats']:
               
                # Find the first format with audio and no video codec
                if format['acodec'] == 'opus' and format['vcodec'] == 'none' and format.get('url'):
                    # Return the audio URL
                   
                    return format['url']

            return None  # No valid audio stream found

        except Exception as e:
            print(f"Error during extraction: {str(e)}")  # Debugging output
            return None

# Route to fetch the audio download URL
@app.route('/get_audio', methods=['POST'])
def get_audio():
    print("Received request to fetch audio.")
    # Extracting the video URL and cookies file (or URL)
    video_url = request.form.get('url')
    cookies_file = request.files.get('cookies.txt')
    cookies_url = request.form.get('cookies_url')

    # Step 1: Validate the video URL
    if not video_url:
        print("Error: No video URL provided.")
        return jsonify({'error': 'No video URL provided'}), 400
    print(f"Received YouTube URL: {video_url}")

    # Step 2: Handling cookies - either from file upload or URL
    cookies_file_path = None
    if cookies_file:
        cookies_file_path = os.path.join(TEMP_DIR, secure_filename(cookies_file.filename))
        cookies_file.save(cookies_file_path)
        print(f"Successfully uploaded cookie file: {cookies_file.filename}")
        print(f"Cookie file saved to: {cookies_file_path}")
    elif cookies_url:
        cookies_file_path = os.path.join(TEMP_DIR, 'cookies.txt')
        result = download_cookies_from_url(cookies_url, cookies_file_path)
        if isinstance(result, dict) and 'error' in result:
            return jsonify(result), 400

    # Log the content of the cookies file if it exists
    if cookies_file_path:
        try:
            with open(cookies_file_path, 'r') as f:
                cookies_content = f.read()
                print(f"Content of cookies file ({cookies_file_path}):\n{cookies_content}")
        except Exception as e:
            print(f"Error reading cookies file: {str(e)}")

    # Step 3: Validate the YouTube URL
    if not is_valid_youtube_url(video_url):
        print(f"Error: Invalid YouTube URL: {video_url}")
        return jsonify({'error': 'Invalid YouTube URL'}), 400

    try:
        # Step 4: Fetch the best audio URL
        audio_url = get_audio_url_from_json(video_url, cookies_file_path)
        
        if audio_url:
            print(f"Successfully fetched audio URL for video: {video_url}")
            return jsonify({'audio_url': audio_url})  # Return the audio URL if found
        else:
            print(f"Error: Audio stream not found for video: {video_url}")
            return jsonify({'error': 'Audio stream not found for this video'}), 404  # Error if no audio found
    except Exception as e:
        print(f"Error during audio URL extraction: {str(e)}")
        return jsonify({'error': str(e)}), 500  # Return an error message for any exception

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
