import os
import yt_dlp
from flask import Flask, jsonify, request
from flask_cors import CORS
from ytmusicapi import YTMusic
import socket
import tempfile
from google.cloud import storage
import base64
import chromedriver_autoinstaller
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
import time

app = Flask(__name__)
CORS(app)

# Initialize YTMusic API
ytmusic = YTMusic()

# Ensure ChromeDriver is installed
chromedriver_autoinstaller.install()

# Decode the service account key from the environment variable
encoded_key = os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY')
if encoded_key is None:
    raise ValueError("FIREBASE_SERVICE_ACCOUNT_KEY environment variable is not set")

decoded_key = base64.b64decode(encoded_key)
temp_dir = tempfile.mkdtemp()
temp_file_path = os.path.join(temp_dir, 'service-account-key.json')
with open(temp_file_path, 'wb') as f:
    f.write(decoded_key)

# Set the GOOGLE_APPLICATION_CREDENTIALS environment variable to the path of the decoded key file
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_file_path
bucket_name = 'quizwapp.appspot.com'


def download_cookies_file():
    """Download cookies.txt file from Firebase Storage."""
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob('cookies.txt')
    if blob.exists():
        temp_cookies_path = os.path.join(temp_dir, 'cookies.txt')
        blob.download_to_filename(temp_cookies_path)
        return temp_cookies_path
    else:
        raise FileNotFoundError("Cookies file not found in Firebase Storage.")


def save_cookies_to_file(email, password, cookies_filename="cookies.txt"):
    """Programmatically login to YouTube using Selenium and save cookies to a file."""
    # Set up Chrome options for Selenium
    options = Options()
    options.add_argument("--headless")  # Run headlessly (without opening the browser)
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    # Set up WebDriver (Chrome)
    driver = webdriver.Chrome(service=Service(), options=options)

    # Go to YouTube login page
    driver.get("https://accounts.google.com/ServiceLogin?service=youtube")
    
    # Find the email input and fill it
    email_elem = driver.find_element(By.ID, "identifierId")
    email_elem.send_keys(email)
    email_elem.send_keys(Keys.RETURN)
    time.sleep(2)  # Wait for the password field to appear
    
    # Find the password input and fill it
    password_elem = driver.find_element(By.NAME, "password")
    password_elem.send_keys(password)
    password_elem.send_keys(Keys.RETURN)
    
    time.sleep(5)  # Wait for login to complete

    # After login, extract cookies
    cookies = driver.get_cookies()

    # Save cookies to a file in the format yt-dlp expects
    with open(cookies_filename, "w") as f:
        for cookie in cookies:
            f.write(f"{cookie['name']}={cookie['value']}; domain={cookie['domain']}\n")

    driver.quit()
    print(f"Cookies saved to {cookies_filename}")


# Helper function to validate YouTube URL
def is_valid_youtube_url(url):
    return 'youtube.com' in url or 'youtu.be' in url


def get_best_audio_stream_url(video_url, cookie_file_path):
    """Use yt-dlp to extract the best audio stream from a YouTube video."""
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
            'cookiefile': cookie_file_path  # Pass the cookies file here
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


@app.route('/get_audio', methods=['GET'])
def get_audio_stream_url():
    video_url = request.args.get('url')

    if not video_url:
        return jsonify({'error': 'No video URL provided'}), 400

    # Validate the YouTube URL
    if not is_valid_youtube_url(video_url):
        return jsonify({'error': 'Invalid YouTube URL'}), 400

    # Get the email and password from the request (or environment variables)
    email = os.getenv("YOUTUBE_EMAIL")
    password = os.getenv("YOUTUBE_PASSWORD")

    if not email or not password:
        return jsonify({"error": "YouTube login credentials not set."}), 400

    # Save cookies if not already downloaded
    cookies_path = os.path.join(temp_dir, 'cookies.txt')

    if not os.path.exists(cookies_path):
        save_cookies_to_file(email, password, cookies_path)

    # Get the best audio stream URL for the video
    stream_url = get_best_audio_stream_url(video_url, cookies_path)
    
    if "error" in stream_url:
        return jsonify(stream_url), 400

    return jsonify({'stream_url': stream_url})


@app.route('/', methods=['GET'])
def health_check():
    try:
        return jsonify({"status": "success", "message": "The API is up and running!"}), 200
    except Exception as e:
        return jsonify({"status": "fail", "message": f"Health check failed: {str(e)}"}), 503


# Example usage for other routes like '/search', '/get_artist', etc.
# (rest of your code remains the same)

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
