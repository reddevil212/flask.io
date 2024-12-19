from flask import Flask, jsonify, request
import yt_dlp
import os
import tempfile
import requests
from werkzeug.utils import secure_filename
from vercel_flask import VercelFlask

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

# Function to get the best audio URL from a YouTube video
def get_audio_url_from_json(video_url, cookies_file_path):
    ydl_opts = {
        'format': 'bestaudio',
        'noplaylist': True,
        'quiet': False,
        'cookiefile': cookies_file_path,
        'forcejson': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info_dict = ydl.extract_info(video_url, download=False)
            for format in info_dict['formats']:
                if format['acodec'] == 'opus' and format['vcodec'] == 'none' and format.get('url'):
                    return format['url']
            return None
        except Exception as e:
            return None

@app.route('/get_audio', methods=['POST'])
def get_audio():
    video_url = request.form.get('url')
    cookies_file = request.files.get('cookies.txt')
    cookies_url = request.form.get('cookies_url')

    if not video_url:
        return jsonify({'error': 'No video URL provided'}), 400

    cookies_file_path = None
    if cookies_file:
        cookies_file_path = os.path.join(TEMP_DIR, secure_filename(cookies_file.filename))
        cookies_file.save(cookies_file_path)
    elif cookies_url:
        cookies_file_path = os.path.join(TEMP_DIR, 'cookies.txt')
        result = download_cookies_from_url(cookies_url, cookies_file_path)
        if isinstance(result, dict) and 'error' in result:
            return jsonify(result), 400

    if not is_valid_youtube_url(video_url):
        return jsonify({'error': 'Invalid YouTube URL'}), 400

    try:
        audio_url = get_audio_url_from_json(video_url, cookies_file_path)
        if audio_url:
            return jsonify({'audio_url': audio_url})
        else:
            return jsonify({'error': 'Audio stream not found for this video'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Health check endpoint to ensure the server is running
@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "success", "message": "The API is up and running!"}), 200

# Use VercelFlask to wrap the Flask app for serverless deployment
vercel_app = VercelFlask(app)
