import yt_dlp
from flask import Flask, request, jsonify
import tempfile
import os
import requests
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Temporary directory for storing uploaded files
TEMP_DIR = tempfile.mkdtemp()

# Helper function to download cookies from a URL
def download_cookies_from_url(url, download_path):
    try:
        # Download the cookies file from the URL
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad responses
        with open(download_path, 'wb') as f:
            f.write(response.content)
        return download_path
    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to download cookies from URL: {str(e)}"}

# Function to extract M3U8 URL or the best available stream URL
def get_stream_url(yt_url, cookies_file_path=None):
    ydl_opts = {
        'format': 'bestaudio/best',  # Choose the best format (video or audio)
        'noplaylist': False,  # Disable playlist downloads
        'quiet': True,  # Suppress output to keep it clean
        'forcejson': True  # Get metadata in JSON format
    }

    if cookies_file_path:
        ydl_opts['cookiefile'] = cookies_file_path  # Use cookies if provided

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(yt_url, download=False)

            # Debugging: print the available formats
            print("Available formats:", info_dict.get('formats', 'No formats found'))

            # Check if 'formats' key exists in the response
            if 'formats' in info_dict:
                # Iterate over the available formats
                for format in info_dict['formats']:
                    # Debugging: print format details
                    print("Format:", format)

                    # If 'url' is an M3U8 playlist (HLS), return it
                    if format.get('format_id') and 'm3u8' in format.get('url', ''):
                        return format['url']

            return None  # Return None if no M3U8 URL is found
    except Exception as e:
        return str(e)

@app.route('/stream_url', methods=['POST'])
def stream_url():
    # Extract the 'url' parameter from form data
    yt_url = request.form.get('url', '')
    cookies_file = request.files.get('cookies.txt')  # Get uploaded cookies file
    cookies_url = request.form.get('cookies_url')  # Get cookies URL from form data

    if not yt_url:
        return jsonify({'error': 'YouTube URL is required'}), 400

    # Handle cookies - either uploaded or downloaded
    cookies_file_path = None
    if cookies_file:
        # Save the cookies file temporarily
        cookies_file_path = os.path.join(TEMP_DIR, secure_filename(cookies_file.filename))
        cookies_file.save(cookies_file_path)
    elif cookies_url:
        cookies_file_path = os.path.join(TEMP_DIR, 'cookies.txt')
        result = download_cookies_from_url(cookies_url, cookies_file_path)
        if isinstance(result, dict) and 'error' in result:
            return jsonify(result), 400

    # Get the stream URL (M3U8 URL or the best available stream URL)
    stream_url = get_stream_url(yt_url, cookies_file_path)

    if stream_url:
        return jsonify({'stream_url': stream_url}), 200
    else:
        return jsonify({'error': 'Stream URL not found or failed to fetch URL'}), 400

if __name__ == '__main__':
    app.run(debug=True)
