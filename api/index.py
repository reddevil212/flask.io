import os
import yt_dlp
import tempfile
import requests
from flask import Flask, jsonify, request
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configure a temporary directory for storing uploaded files
TEMP_DIR = tempfile.mkdtemp()

# Default cookie URL if none is provided
DEFAULT_COOKIE_URL = 'https://raw.githubusercontent.com/reddevil212/flask-hello-world/refs/heads/main/api/cookies.txt'

# Helper function to validate YouTube URL
def is_valid_youtube_url(url):
    return 'youtube.com' in url or 'youtu.be' in url

# Helper function to download the cookies file from a URL
def download_cookies_from_url(url, download_path):
    print(f"Attempting to download cookies from URL: {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad responses
        with open(download_path, 'wb') as f:
            f.write(response.content)
        
        return download_path
    except requests.exceptions.RequestException as e:
        print(f"Error downloading cookies file from URL: {str(e)}")
        return {"error": f"Failed to download cookies from URL: {str(e)}"}

# Function to get the best audio stream URL for a YouTube video
def get_audio_stream_url(video_url, cookies_file_path):
    # Options for yt-dlp, including cookie file if provided
    ydl_opts = {
        'format': 'bestaudio/best',  # Choose the best audio format
        'extractaudio': True,        # Extract audio only
        'audioquality': 1,           # Set audio quality (1 = best)
        'outtmpl': '%(id)s.%(ext)s',  # File output template (not actually used here)
        'noplaylist': True,          # Don't download playlists
        'quiet': True,               # Suppress unnecessary output
        'cookiefile': cookies_file_path,  # Include cookies if provided
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # Extract video info (without downloading the video)
        info_dict = ydl.extract_info(video_url, download=False)
        
        # Initialize a variable to store the audio stream URL
        audio_stream_url = None

        # Iterate through the formats and find the audio stream
        for format in info_dict['formats']:
            # Only select formats that are audio and streamable
            if 'audio' in format['format']:
                if 'url' in format:
                    audio_stream_url = format['url']  # Get the URL of the audio stream
                    break  # Stop after finding the first valid audio URL

        return audio_stream_url  # Return the stream URL (or None if not found)

# Route to fetch the audio stream URL
@app.route('/get_audio', methods=['POST'])
def get_audio():
    # Extracting the video URL and cookies file (or URL)
    video_url = request.form.get('url')
    cookies_file = request.files.get('cookies.txt')
    cookies_url = request.form.get('cookies_url')

    # Step 1: Validate the video URL
    if not video_url:
        return jsonify({'error': 'No video URL provided'}), 400

    # Step 2: Handling cookies - either from file upload or URL
    cookies_file_path = None

    if cookies_file:
        cookies_file_path = os.path.join(TEMP_DIR, secure_filename(cookies_file.filename))
        cookies_file.save(cookies_file_path)
        print(f"Received cookies file: {cookies_file.filename}")
    elif cookies_url:
        cookies_file_path = os.path.join(TEMP_DIR, 'cookies.txt')
        result = download_cookies_from_url(cookies_url, cookies_file_path)
        if isinstance(result, dict) and 'error' in result:
            return jsonify(result), 400
        print(f"Received cookies URL: {cookies_url}")
    else:
        # If no cookies file or URL is provided, use the default cookies URL
        cookies_file_path = os.path.join(TEMP_DIR, 'cookies.txt')
        result = download_cookies_from_url(DEFAULT_COOKIE_URL, cookies_file_path)
        if isinstance(result, dict) and 'error' in result:
            return jsonify(result), 400
        print(f"No cookies file or URL provided. Using default cookies URL: {DEFAULT_COOKIE_URL}")

    # Step 3: Validate the YouTube URL
    if not is_valid_youtube_url(video_url):
        return jsonify({'error': 'Invalid YouTube URL'}), 400

    try:
        # Step 4: Fetch the best audio stream URL
        audio_stream_url = get_audio_stream_url(video_url, cookies_file_path)
        
        if audio_stream_url:
            return jsonify({'audio_stream_url': audio_stream_url})  # Return the stream URL if found
        else:
            return jsonify({'error': 'Audio stream not found for this video'}), 404  # Error if no audio found
    except Exception as e:
        return jsonify({'error': str(e)}), 500  # Return an error message for any exception

# Health check endpoint to ensure the server is running
@app.route('/', methods=['GET'])
def health_check():
    try:
        return jsonify({"status": "success", "message": "The API is up and running!"}), 200
    except Exception as e:
        return jsonify({"status": "fail", "message": f"Health check failed: {str(e)}"}), 503

# Start the Flask server
if __name__ == '__main__':
    print("Starting Flask server...")
    app.run(debug=True, host='0.0.0.0', port=5000)

