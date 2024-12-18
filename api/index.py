import os
import yt_dlp
from flask import Flask, jsonify, request
from werkzeug.utils import secure_filename
import tempfile
import requests

app = Flask(__name__)

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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
