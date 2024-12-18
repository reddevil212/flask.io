import yt_dlp
import base64
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
        print(f"[DEBUG] Downloading cookies from: {url}")
        response = requests.get(url)
        response.raise_for_status()
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
        'cookiefile': cookies_file_path,  # Use cookies if provided
        'logger': yt_dlp.logger.getLogger()
    }

    try:
        print(f"[DEBUG] Extracting stream URL for: {yt_url}")
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
    except yt_dlp.utils.DownloadError as e:
        print(f"[ERROR] yt-dlp DownloadError: {e}")
        return str(e)
    except Exception as e:
        print(f"[ERROR] General error: {e}")
        return str(e)

@app.route('/stream_url', methods=['POST'])
def stream_url():
    try:
        # Extract the 'url' parameter and base64-encoded cookies file from form data
        data = request.get_json()
        yt_url = data.get('url')
        cookies_file_base64 = data.get('cookies_file_base64')

        if not yt_url:
            return jsonify({'error': 'YouTube URL is required'}), 400

        if not cookies_file_base64:
            return jsonify({'error': 'Cookies file is required'}), 400

        # Decode the base64-encoded cookies file and save it
        cookies_file_path = os.path.join(TEMP_DIR, 'cookies.txt')
        with open(cookies_file_path, 'wb') as f:
            f.write(base64.b64decode(cookies_file_base64))

        # Proceed with the existing logic to get the stream URL
        stream_url = get_stream_url(yt_url, cookies_file_path)
        
        if stream_url:
            return jsonify({'stream_url': stream_url}), 200
        else:
            return jsonify({'error': 'Stream URL not found or failed to fetch URL'}), 400
    except Exception as e:
        print(f"[ERROR] Exception in stream_url endpoint: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/', methods=['GET'])
def health_check():
    try:
        return jsonify({"status": "success", "message": "The API is up and running!"}), 200
    except Exception as e:
        return jsonify({"status": "fail", "message": f"Health check failed: {str(e)}"}), 503

# Add more endpoints as required

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
