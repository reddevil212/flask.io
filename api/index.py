import os
import yt_dlp
import tempfile
import requests
from flask import Flask, jsonify, request
from werkzeug.utils import secure_filename
from flask_lambda import FlaskLambda

app = FlaskLambda(__name__)

# Configure a temporary directory for storing uploaded files
TEMP_DIR = tempfile.mkdtemp()

# Default cookies file URL if no cookies file or cookies URL is provided
DEFAULT_COOKIES_URL = "https://raw.githubusercontent.com/reddevil212/jks/refs/heads/main/cookies.txt"

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
                    return format['url']

            return None  # No valid audio stream found

        except Exception as e:
            print(f"Error during extraction: {str(e)}")  # Debugging output
            return None

# Route to fetch the audio download URL for multiple URLs
@app.route('/get_audio', methods=['POST'])
def get_audio():
    print("Received request to fetch audio.")
    if request.is_json:
        # Parse JSON data
        data = request.get_json()
        video_urls = data.get('urls', [])
        cookies_url = data.get('cookies_url', None)
        print(f"Received video URLs from JSON: {video_urls}")
    else:
        video_urls = request.form.getlist('urls[]')
        cookies_url = request.form.get('cookies_url', None)
        print(f"Received video URLs from form: {video_urls}")

    if not video_urls:
        print("Error: No YouTube URLs provided.")
        return jsonify({'error': 'No YouTube URLs provided'}), 400

    cookies_file_path = None
    cookies_file = request.files.get('cookies.txt')

    if cookies_file:
        cookies_file_path = os.path.join(TEMP_DIR, secure_filename(cookies_file.filename))
        cookies_file.save(cookies_file_path)
        print(f"Successfully uploaded cookie file: {cookies_file.filename}")
    elif cookies_url:
        cookies_file_path = os.path.join(TEMP_DIR, 'cookies.txt')
        result = download_cookies_from_url(cookies_url, cookies_file_path)
        if isinstance(result, dict) and 'error' in result:
            return jsonify(result), 400
    else:
        cookies_file_path = os.path.join(TEMP_DIR, 'cookies.txt')
        print(f"Using default cookies file URL: {DEFAULT_COOKIES_URL}")
        result = download_cookies_from_url(DEFAULT_COOKIES_URL, cookies_file_path)
        if isinstance(result, dict) and 'error' in result:
            return jsonify(result), 400

    if cookies_file_path:
        try:
            with open(cookies_file_path, 'r') as f:
                cookies_content = f.read()
                print(f"Content of cookies file ({cookies_file_path}):\n{cookies_content}")
        except Exception as e:
            print(f"Error reading cookies file: {str(e)}")

    invalid_urls = []
    valid_urls = []
    
    for url in video_urls:
        if not is_valid_youtube_url(url):
            invalid_urls.append(url)
        else:
            valid_urls.append(url)

    if invalid_urls:
        print(f"Error: Invalid YouTube URLs: {invalid_urls}")
        return jsonify({'error': 'Invalid YouTube URLs', 'invalid_urls': invalid_urls}), 400

    urls_data = []
    for idx, video_url in enumerate(valid_urls, 1):
        try:
            audio_url = get_audio_url_from_json(video_url, cookies_file_path)
            if audio_url:
                urls_data.append({
                    'value': idx,
                    'audio_url': audio_url
                })
            else:
                urls_data.append({
                    'value': idx,
                    'audio_url': 'Audio stream not found'
                })
        except Exception as e:
            print(f"Error during audio URL extraction for {video_url}: {str(e)}")
            urls_data.append({
                'value': idx,
                'audio_url': f"Error: {str(e)}"
            })

    return jsonify({'urls': urls_data})

@app.route('/', methods=['GET'])
def health_check():
    try:
        print("Health check request received.")
        return jsonify({"status": "success", "message": "The API is up and running!"}), 200
    except Exception as e:
        print(f"Health check failed: {str(e)}")
        return jsonify({"status": "fail", "message": f"Health check failed: {str(e)}"}), 503

