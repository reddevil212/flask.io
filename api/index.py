import os
import json
import yt_dlp
from flask import Flask, jsonify, request
from flask_cors import CORS
from google.cloud import storage
import tempfile
import base64

app = Flask(__name__)
CORS(app)

# Your hardcoded cookies (the ones you provided)
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


# Write the cookies to a cookies.txt file
def write_cookies_to_file(cookies, filename="cookies.txt"):
    with open(filename, "w") as f:
        for cookie in cookies:
            line = f"{cookie['name']}={cookie['value']}; domain={cookie['domain']}; path={cookie['path']}\n"
            f.write(line)
    print("Cookies have been written to cookies.txt")

# Write the cookies to the file
write_cookies_to_file(cookies)

# Helper function to validate YouTube URL
def is_valid_youtube_url(url):
    return 'youtube.com' in url or 'youtu.be' in url

# Function to get the best audio stream URL from YouTube
def get_best_audio_stream_url(video_url, cookies_file="cookies.txt"):
    try:
        # Set up yt-dlp options with the cookies file
        ydl_opts = {
            'format': 'bestaudio',  # Only focus on the best audio stream
            'quiet': True,  # Suppress unnecessary output
            'extractor_args': {
                'youtube': {
                    'noplaylist': True  # Disable playlist extraction
                }
            },
            'cookiefile': cookies_file  # Pass the cookies file here
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

# Endpoint to search for songs, artists, and albums
@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query')
    # Replace the next line with your search logic (e.g., YTMusic API)
    results = []  # Placeholder for the search results
    return jsonify(results)

@app.route('/search_suggestions', methods=['GET'])
def search_suggestions():
    query = request.args.get('query')
    # Replace the next line with your suggestion logic (e.g., YTMusic API)
    suggestions = []  # Placeholder for the suggestions
    return jsonify(suggestions)

@app.route('/get_artist', methods=['GET'])
def get_artist():
    artist_id = request.args.get('artistId')
    if not artist_id:
        return jsonify({'error': 'Artist ID parameter is required'}), 400

    # Replace the next line with your artist retrieval logic (e.g., YTMusic API)
    artist_info = {}  # Placeholder for artist info
    return jsonify(artist_info)

@app.route('/artists/<string:artist_id>/albums', methods=['GET'])
def get_artist_albums(artist_id):
    # Replace the next line with your artist albums logic (e.g., YTMusic API)
    results = []  # Placeholder for artist albums
    return jsonify(results)

@app.route('/albums/<string:album_id>', methods=['GET'])
def get_album(album_id):
    # Replace the next line with your album retrieval logic (e.g., YTMusic API)
    results = {}  # Placeholder for album data
    return jsonify(results)

@app.route('/albums/<string:album_id>/browse_id', methods=['GET'])
def get_album_browse_id(album_id):
    # Replace the next line with your album browse ID retrieval logic (e.g., YTMusic API)
    results = {}  # Placeholder for album browse ID
    return jsonify(results)

@app.route('/songs/<string:song_id>', methods=['GET'])
def get_song(song_id):
    # Replace the next line with your song retrieval logic (e.g., YTMusic API)
    results = {}  # Placeholder for song data
    return jsonify(results)

@app.route('/songs/<string:song_id>/related', methods=['GET'])
def get_song_related(song_id):
    # Replace the next line with your related song retrieval logic (e.g., YTMusic API)
    results = []  # Placeholder for related songs
    return jsonify(results)

if __name__ == '__main__':
    # Find available port and run the server
    port = os.getenv('PORT', 5000)  # Default to 5000 if not set
    print(f"Running on port {port}")
    app.run(debug=True, host='0.0.0.0', port=int(port), use_reloader=False)
