import os
import yt_dlp
from flask import Flask, jsonify, request
from flask_cors import CORS
from ytmusicapi import YTMusic
import socket
import tempfile
from google.cloud import storage
import base64

app = Flask(__name__)
CORS(app)

# Initialize YTMusic API
ytmusic = YTMusic()

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
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob('cookies.txt')
    if blob.exists():
        temp_cookies_path = os.path.join(temp_dir, 'cookies.txt')
        blob.download_to_filename(temp_cookies_path)
        return temp_cookies_path
    else:
        raise FileNotFoundError("Cookies file not found in Firebase Storage.")

# Helper function to validate YouTube URL
def is_valid_youtube_url(url):
    return 'youtube.com' in url or 'youtu.be' in url

def get_best_audio_stream_url(video_url, cookies_file="cookies.txt"):
    try:
        ydl_opts = {
            'format': 'bestaudio',  # Only focus on the best audio stream
            'quiet': True,  # Suppress unnecessary output
            'cookiefile': cookies_file  # Pass the cookies file here
        }
        
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

# Hardcoded cookies in Netscape format
cookies = [
    {"domain":".youtube.com","expirationDate":1734526886.894304,"hostOnly":False,"httpOnly":True,"name":"GPS","path":"/","sameSite":"unspecified","secure":True,"session":False,"storeId":"0","value":"1","index":0,"isSearch":False},
    {"domain":".youtube.com","expirationDate":1769085102.271839,"hostOnly":False,"httpOnly":False,"name":"PREF","path":"/","sameSite":"unspecified","secure":True,"session":False,"storeId":"0","value":"f4=4000000&f6=40000000&tz=Asia.Calcutta","index":1,"isSearch":False},
    {"domain":".youtube.com","expirationDate":1769085098.838486,"hostOnly":False,"httpOnly":False,"name":"__Secure-3PAPISID","path":"/","sameSite":"no_restriction","secure":True,"session":False,"storeId":"0","value":"kG43TEGYufQQV6BM/AvDsRwDpcMmTY6SFE","index":2,"isSearch":False},
    {"domain":".youtube.com","expirationDate":1769085098.838542,"hostOnly":False,"httpOnly":True,"name":"__Secure-3PSID","path":"/","sameSite":"no_restriction","secure":True,"session":False,"storeId":"0","value":"g.a000rQibbKU8xdz7QAq4vZ-hNfBtNbjPrdz0HsgddwAwYLfPlReoce38VEJigGN7H3knSuzYPAACgYKAfASARASFQHGX2Mi48iAwFHwC0uedcj1ItumXhoVAUF8yKpvk7hAMeicLZw44GFiBt910076","index":3,"isSearch":False},
    {"domain":".youtube.com","expirationDate":1766061098.838295,"hostOnly":False,"httpOnly":True,"name":"__Secure-1PSIDTS","path":"/","sameSite":"unspecified","secure":True,"session":False,"storeId":"0","value":"sidts-CjIB7wV3sUGhHA3IBZ5PuLhI9VhMSz58_HDkHM25vhYjJI1JGskV7p2Pa1YzYO4jA7I6UBAA","index":4,"isSearch":False},
    {"domain":".youtube.com","expirationDate":1766061098.838379,"hostOnly":False,"httpOnly":True,"name":"__Secure-3PSIDTS","path":"/","sameSite":"no_restriction","secure":True,"session":False,"storeId":"0","value":"sidts-CjIB7wV3sUGhHA3IBZ5PuLhI9VhMSz58_HDkHM25vhYjJI1JGskV7p2Pa1YzYO4jA7I6UBAA","index":5,"isSearch":False},
    {"domain":".youtube.com","expirationDate":1769085098.838406,"hostOnly":False,"httpOnly":True,"name":"HSID","path":"/","sameSite":"unspecified","secure":False,"session":False,"storeId":"0","value":"AIajAszhd75vkK95i","index":6,"isSearch":False},
    {"domain":".youtube.com","expirationDate":1769085098.838422,"hostOnly":False,"httpOnly":True,"name":"SSID","path":"/","sameSite":"unspecified","secure":True,"session":False,"storeId":"0","value":"AQFTeGhvemPJIXJFg","index":7,"isSearch":False},
    {"domain":".youtube.com","expirationDate":1769085098.838435,"hostOnly":False,"httpOnly":False,"name":"APISID","path":"/","sameSite":"unspecified","secure":False,"session":False,"storeId":"0","value":"37QRA-JfxC45Upi4/AcE26FTOcfkn2Vsfv","index":8,"isSearch":False},
    {"domain":".youtube.com","expirationDate":1769085098.838452,"hostOnly":False,"httpOnly":False,"name":"SAPISID","path":"/","sameSite":"unspecified","secure":True,"session":False,"storeId":"0","value":"kG43TEGYufQQV6BM/AvDsRwDpcMmTY6SFE","index":9,"isSearch":False},
    {"domain":".youtube.com","expirationDate":1769085098.838469,"hostOnly":False,"httpOnly":False,"name":"__Secure-1PAPISID","path":"/","sameSite":"unspecified","secure":True,"session":False,"storeId":"0","value":"kG43TEGYufQQV6BM/AvDsRwDpcMmTY6SFE","index":10,"isSearch":False},
    {"domain":".youtube.com","expirationDate":1769085098.838507,"hostOnly":False,"httpOnly":False,"name":"SID","path":"/","sameSite":"unspecified","secure":False,"session":False,"storeId":"0","value":"g.a000rQibbKU8xdz7QAq4vZ-hNfBtNbjPrdz0HsgddwAwYLfPlReoOD7WLH8OoefI3-ksd-IBpwACgYKAa4SARASFQHGX2MiW9qvB7aIe_jKPPjDFe75wBoVAUF8yKrt9acjKr88_qVZbOsN_aZ00076","index":11,"isSearch":False},
    {"domain":".youtube.com","expirationDate":1769085098.838526,"hostOnly":False,"httpOnly":True,"name":"__Secure-1PSID","path":"/","sameSite":"unspecified","secure":True,"session":False,"storeId":"0","value":"g.a000rQibbKU8xdz7QAq4vZ-hNfBtNbjPrdz0HsgddwAwYLfPlReo0Y8-BtzMcBxCUsezVKF1cwACgYKAQMSARASFQHGX2Mi7NPCejmyVHAalDUvNXax8RoVAUF8yKqtgg_fQL-VIaF7uZ9ylgqZ0076","index":12,"isSearch":False},
    {"domain":".youtube.com","expirationDate":1769085099.167323,"hostOnly":False,"httpOnly":True,"name":"LOGIN_INFO","path":"/","sameSite":"no_restriction","secure":True,"session":False,"storeId":"0","value":"AFmmF2swRAIgQWZmb6nN8VYUgCaizc6wHaphkaGIrn6XTMA4zxcqh34CIHcsglzsTMzUz4YqxQ6cTfz1juLinWolVNSwsmFgHc3y:QUQ3MjNmeUVQaDZRSmxnaDRJdWZSNm9VRlhIR0s2NTVVUUlNMWJlZEl5U1Q5aDZVRTl1X2V4ZndKNDk1cmJ1VUdlNTRsSEJackpsLWVzeW93SXNESFBSU0MtVnhIeXdRNW4ydC1hS3pLOF9wWWF2WHVVTnRjM0phNVJBbVp5akxRdFlwSGE5ck9MRHlTZDM2TnBybWFqRDNnaHE3Q0ppT2dn","index":13,"isSearch":False},
    {"domain":".youtube.com","expirationDate":1734525702,"hostOnly":False,"httpOnly":False,"name":"CONSISTENCY","path":"/","sameSite":"unspecified","secure":True,"session":False,"storeId":"0","value":"AKreu9sAIs9c2HpWIWFv633eJcRwtRdiIM4MhgNogbpkuarMe_Il0v3vRvqfXDKl2aV4SVC0MmpNkV62N36gzGQrLEb3e0Xt_efWKh9VQGrVHIv3jEl9iEuw8R0nxSyNttnDdejuooJWk4Ojx1nyES-Z","index":14,"isSearch":False},
    {"domain":".youtube.com","expirationDate":1766061105.284411,"hostOnly":False,"httpOnly":False,"name":"SIDCC","path":"/","sameSite":"unspecified","secure":False,"session":False,"storeId":"0","value":"AKEyXzVnovRPKLIQirxA7VLgvWUvIIWBLSqlzJmbU95O9aGFZk5X7XPnNwZ0zPS9ZPaVn_-eIlqWBpsf5iiFf2Ryzww9qXlgB0RxU7q3ac9pLsDPjxXr6VfTRRSoBoVD0uytGg8VZ9l9nrd_0Fg_Ye8bXM","index":15,"isSearch":False}
]


def write_cookies_netscape_format(cookies, filename="cookies.txt"):
    with open(filename, "w") as f:
        f.write("# Netscape HTTP Cookie File\n")
        
        for cookie in cookies:
            domain = cookie.get('domain', '')
            secure = 'TRUE' if cookie.get('secure', False) else 'FALSE'
            path = cookie.get('path', '/')
            expiration = str(int(cookie.get('expirationDate', 0)))
            name = cookie.get('name', '')
            value = cookie.get('value', '')
            httpOnly = 'TRUE' if cookie.get('httpOnly', False) else 'FALSE'
            
            line = f"{domain}\tTRUE\t{path}\t{secure}\t{expiration}\t{name}\t{value}\n"
            f.write(line)
    
    print(f"Cookies have been written to {filename}")

# Write the cookies to a file
write_cookies_netscape_format(cookies)

@app.route('/get_audio', methods=['GET'])
def get_audio_stream_url():
    video_url = request.args.get('url')

    if not video_url:
        return jsonify({'error': 'No video URL provided'}), 400

    # Validate the YouTube URL
    if not is_valid_youtube_url(video_url):
        return jsonify({'error': 'Invalid YouTube URL'}), 400

    # Get the best audio stream URL for the video
    stream_url = get_best_audio_stream_url(video_url)
    
    if "error" in stream_url:
        return jsonify(stream_url), 400

    return jsonify({'stream_url': stream_url})

@app.route('/', methods=['GET'])
def health_check():
    try:
        return jsonify({"status": "success", "message": "The API is up and running!"}), 200
    except Exception as e:
        return jsonify({"status": "fail", "message": f"Health check failed: {str(e)}"}), 503

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

@app.route('/artists/<string:artist_id>/albums', methods=['GET'])
def get_artist_albums(artist_id):
    results = ytmusic.get_artist_albums(artist_id)
    return jsonify(results)

@app.route('/albums/<string:album_id>', methods=['GET'])
def get_album(album_id):
    results = ytmusic.get_album(album_id)
    return jsonify(results)

@app.route('/albums/<string:album_id>/browse_id', methods=['GET'])
def get_album_browse_id(album_id):
    results = ytmusic.get_album_browse_id(album_id)
    return jsonify(results)

@app.route('/songs/<string:song_id>', methods=['GET'])
def get_song(song_id):
    results = ytmusic.get_song(song_id)
    return jsonify(results)

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
        app.run(debug=True, host='0.0.0.0', port=port)
    else:
        print("No available port found.")
