import platform; print(platform.python_version())
import os
import sys
import time
import json
import shutil
import logging
# import glob
import zipfile
import threading
import subprocess
import validators
import flask_login
import urllib.request
# import concurrent.futures
from threading import Lock
# from threading import Timer
from datetime import datetime
from pymongo import MongoClient
from urllib.parse import urlparse
from bson.objectid import ObjectId
from flask import Flask, request, render_template, session, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required
app = Flask(__name__)
# Set system default path to /app
os.environ['PATH'] += os.pathsep + '/app'
logging.basicConfig(level=logging.DEBUG)
app.logger.addHandler(logging.StreamHandler(sys.stdout))

# Things left to add
# - multi-user login 
# - customizable grid format for home page, 5x5, 7x7 etc
# - customizable number of items displayed 
# - search function 
# - filter function 
# - grab thumbnails ✅
# - create video player page 
# - design new file structure ✅
# - connect mongodb ✅

app.secret_key = 'zu7t101tyNVBExIw2FzHx3R4elulSG3qPC1WqpkzSV2CNQG93Rh1FFcat4SMgphw'
# Create a lock
lock = Lock()
client = MongoClient('mongodb://ytdldb:27017/')
db = client['yt-dlp']
# Create a new collection for the downloaded files
collection = db['downloads']
# Create a new collection for the global pool
global_pool = db['global_pool']
# Create a directory for the executables if it doesn't exist
os.makedirs('/app', exist_ok=True)
# Download yt-dlp
urllib.request.urlretrieve('https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp', '/app/yt-dlp')
# Make yt-dlp executable
os.chmod('/app/yt-dlp', 0o755)
# Download and extract ffmpeg
urllib.request.urlretrieve('https://github.com/ffbinaries/ffbinaries-prebuilt/releases/download/v4.4.1/ffmpeg-4.4.1-linux-64.zip', '/app/ffmpeg-4.4.1-linux-64.zip')
with zipfile.ZipFile('/app/ffmpeg-4.4.1-linux-64.zip', 'r') as zip_ref:
    zip_ref.extractall('/app')
os.remove('/app/ffmpeg-4.4.1-linux-64.zip')
# Make ffmpeg executable
os.chmod('/app/ffmpeg', 0o755)
# Download and extract ffprobe
urllib.request.urlretrieve('https://github.com/ffbinaries/ffbinaries-prebuilt/releases/download/v4.4.1/ffprobe-4.4.1-linux-64.zip', '/app/ffprobe-4.4.1-linux-64.zip')
with zipfile.ZipFile('/app/ffprobe-4.4.1-linux-64.zip', 'r') as zip_ref:
    zip_ref.extractall('/app')
os.remove('/app/ffprobe-4.4.1-linux-64.zip')
# Make ffprobe executable
os.chmod('/app/ffprobe', 0o755)

# Set up Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)

class User(UserMixin):
    def __init__(self, username, password):
        self.id = username
        self.username = username
        self.password = password

class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        elif isinstance(o, ObjectId):
            return str(o)  # convert ObjectId to string
        return super(DateTimeEncoder, self).default(o)

@login_manager.user_loader
def load_user(user_id):
    # Fetch the user from the database using the user_id
    user_record = fetch_user_from_database(user_id)  # You need to implement this function
    # Create a User object using the username and password from the user_record
    if user_record is None:
        return None
    user = User(user_record['username'], user_record['password'])
    return user

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Validate the username and password
        user = User()
        user.id = username
        login_user(user)
        session['user_id'] = username  # Set the 'user_id' session variable
        return redirect(url_for('home'))
    else:
        return render_template('login.html') # render a login form

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return 'Logged out'

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Validate the username and password
        # This is a very basic validation. In a real application, you would want to check if the username already exists, and you would want to hash the password before storing it.
        if not username or not password:
            return 'Invalid username or password', 400
        # Store the username and password
        # In a real application, you would want to store this information in a database.
        session['username'] = username
        session['password'] = password
        return redirect(url_for('home')) # redirect to the home page after registration
    else:
        return render_template('register.html')

def fetch_user_from_database(username):
    # Connect to your MongoDB client
    client = MongoClient('mongodb://ytdldb:27017/')
    # Select your database
    db = client['yt-dlp']
    # Select your collection (table)
    users = db['users']
    # Query for the user with the given username
    user_record = users.find_one({'username': username})
    # Return the user record
    return user_record

def update_statistics(url):
    stats_file = 'statistics.json'
    if os.path.exists(stats_file):
        with open(stats_file, 'r') as f:
            if f is None:
                stats = {'total_downloads': 0, 'domains': {}}
            else:
                stats = json.load(f)
    else:
        stats = {'total_downloads': 0, 'domains': {}}
    stats['total_downloads'] += 1
    domain = urlparse(url).netloc
    if domain not in stats['domains']:
        stats['domains'][domain] = 0
    stats['domains'][domain] += 1
    with open(stats_file, 'w') as f:
        json.dump(stats, f)
    return stats['total_downloads'], stats['domains'][domain]

def sanitize_filename(filename):
    invalid_chars = '<>:"/\\|?*#;^%~`'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename

def get_video_resolution(filename):
    # Wait until the file exists and has not been modified for 5 seconds
    while not os.path.exists(filename) or time.time() - os.path.getmtime(filename) < 5:
        time.sleep(1)
    ffprobepath = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'ffprobe')
    command = [ffprobepath, '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'csv=s=x:p=0', filename]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, err = process.communicate()
    print(f"gvr: {err}")
    return output.decode('utf-8').strip()

def download(url, args, cutout, output_base):
    # Step 01 - Check global_pool
    # Step 02 - Grab Directories: script, yt-dlp, ffprobe & validate URL
    # Step 03 - Grab video title
    # Step 04 - Set output as title name for filename
    # Step 05 - Set directory for public/private
    # Step 06 - Ensure max_filename_length is not exceeded
    # Step 07 - Download video to videos folder
    # Step 08 - Increment Download number
    # Step 09 - Download JSON file to JSON folder
    # Step 10 - Save JSON output to file
    # Step 11 - Download the thumbnail to the thumbnails folder
    # Step 12 - Load the JSON file
    # Step 13 - Extract video info from JSON
    # Step 14 - Set video resolution and aspect ratio
    # Step 15 - Add URL and location to global pool
    # Step 16 - Add video info to database
    # Step 17 - Write extracted info to the new finalized _info file
    # Step 18 - Remove original JSON to conserve space
    # Step 19 - Return

    # Step 1
    # Check if the URL already exists in the global pool
    existing_video = global_pool.find_one({'video_url': url})
    if existing_video is not None:
        # If the URL exists, return a warning message and halt the download
        return None, f"Download failed for URL {url}. Error: Video already exists in global pool"

    # Step 2
    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.realpath(__file__))
    # Construct the full path to yt-dlp
    yt_dlp_path = os.path.join(script_dir, 'yt-dlp')
    ffprobe_path = os.path.join(script_dir, 'ffprobe')
    if not validators.url(url):
        return 'Invalid URL', 400

    # Step 3
    # Run yt-dlp to get video title
    with lock:
        info_command = [yt_dlp_path, '-f', 'bestvideo+bestaudio/best', '--skip-download', '--print-json', url]
        info_process = subprocess.Popen(info_command, stdout=subprocess.PIPE, text=True)
        info_result, err = info_process.communicate()
        print(f"S3E: {err}")

    try:
        info = json.loads(info_result)
    except json.JSONDecodeError:
        print('yt-dlp output is not valid JSON:', info_result)
        return None, f"Download failed for URL {url}. Error: Invalid JSON output from yt-dlp"

    # Step 4
    # Use the video title as the output name if no output name was provided
    if not output_base:
        output = sanitize_filename(info['title'])
    else:
        output = output_base

    # Step 5
    # Determine the directory to save the video based on whether the user is logged in
    if flask_login.current_user.is_authenticated:
        directory = f'data/private/{flask_login.current_user.username}'
    else:
        directory = 'data/public'

    # Step 6
    # Ensure filename does not exceed maximum length
    max_filename_length = 255
    # Account for the length of the longest extension (.json)
    max_base_filename_length = max_filename_length - len('.json')
    if len(output) > max_base_filename_length:
        # Truncate filename and add an ellipsis to indicate truncation
        output = output[:max_base_filename_length - 3] + '...'

    # Step 7
    # Run yt-dlp to download the video (1/3 files)
    command = [yt_dlp_path, '-f', 'bestvideo+bestaudio/best', '-o', f'{directory}/videos/{output}.%(ext)s', '--print-json', url]
    if args and args[0] != '':
        command.extend(args)
    cutout = request.form['cutout'].split('-')
    if len(cutout) == 2:  # Only add cutout args if two values are provided
        cutout_args = f'"-ss {cutout[0]} -to {cutout[1]}"'
        command.extend(['--postprocessor-args', cutout_args])
    with lock:
        download_process = subprocess.Popen(command, stdout=subprocess.PIPE, text=True)
        result, err = download_process.communicate()
        print(f"S7E: {err}")
    # Step 8
        # Increase download number 
        download_number = update_statistics(url)[0]
        voutput = f'{directory}/videos/{output}.%(ext)s'
        #current_location = f'{directory}/videos/{output}.json'
        #new_location = f'{directory}/json/{output}.json'
        # Use shutil.move to move the file
        #shutil.move(current_location, new_location)

    # Step 9
    # Run yt-dlp to download the JSON file
    # with lock:
    #    info_command = [yt_dlp_path, '-f', 'bestvideo+bestaudio/best', '--skip-download', '-o', f'{directory}/json/{output}', '--print-json', url]
    #    info_process = subprocess.Popen(info_command, stdout=subprocess.PIPE, text=True)
    #    info_result, _ = info_process.communicate()
    #    print("Output from yt-dlp command:", info_result)

    # Step 10
    # Save JSON output to a file (2/3 files)
    json_output_filename = f'{directory}/json/{sanitize_filename(output)}.json'
		print({json_output_filename})
    # print("File size:", os.path.getsize(json_output_filename))
    with open(json_output_filename, 'w') as json_file:
        json_file.write(result) # info_result

    # Step 11
    # Run yt-dlp to download the thumbnail (3/3 files)
    tmbs = [yt_dlp_path, '--skip-download', '--write-thumbnail', '--convert-thumbnails', 'jpg', '-o', f'{directory}/thumbnails/{output}', url]
    with lock:
        download_process = subprocess.Popen(tmbs, stdout=subprocess.PIPE, text=True)
        result, err = download_process.communicate()
        print(f"S11E: {err}")

    # Step 12
    # Load the JSON data
    #try:
    with open(json_output_filename, 'r') as f:
        # print("Contents of JSON file", f.read())
        # f.seek(0) # Reset the file pointer to the beginning
        data = json.load(f)
            # print(f"Loaded data: {data}")
        #print(f"Loaded data: {data}")
    #except Exception as e:
    #    print(f"Error loading JSON data from {json_output_filename}: as {e}")
    #    data = {}

    # Step 13
            #try:
    print(f"index: {download_number}")
    print(f"id: {data['id']}")
    print(f"title: {data['title']}")
    print(f"date_posted: {data['upload_date']}")
    print(f"archive_date: {datetime.now()}")
    print(f"user: {data['uploader']}")
    print(f"video_url: {data['webpage_url']}")
    print(f"length: {data['duration']}")
    #print(f"filename: {data['_filename']}")
    print(f"resolution: None")
    print(f"aspect_ratio: None")
    print(f"thumbnail: {directory}/thumbnails/{sanitize_filename(output)}.jpg")

    # Extract the information
    #try:
    video_info = {
  	    'index': download_number,
        'id': data.get('id', 'N/A'),
        'title': data.get('title', 'N/A'),
        'date_posted': data.get('upload_date', 'N/A'),
			  'archive_date': datetime.now(), # BSON datetime object, date-based queries
        'user': data.get('uploader', 'N/A'),
        'video_url': data.get('webpage_url', 'N/A'),
        'length': data.get('duration', 'N/A'),
        'filename': data.get('_filename', 'N/A'),
        'resolution': None,
        'aspect_ratio': None,
        'thumbnail': f'{directory}/thumbnails/{sanitize_filename(output)}.jpg'
    }
        # print(f"Extracted video_info: {video_info}")
    #except Exception as e:
    #    print(f"Error extracting video info: {e}")
    #    video_info = {}

    # Step 14
    # Get the filename of the downloaded file from the JSON output
    downloaded_video_filename = voutput # data['_filename']
		# After the download is complete, get the actual resolution of the downloaded video
    actual_resolution = get_video_resolution(downloaded_video_filename)
    # Update the 'resolution' field in the video_info dictionary
    video_info['resolution'] = actual_resolution
    # Update the 'aspect ratio' field in the video_info dictionary
    for format in data['formats']:
        vcodec = format.get('vcodec', 'none')
        acodec = format.get('acodec', 'none')
        if vcodec != 'none' and acodec != 'none':  # Exclude audio-only or video-only formats
            width, height = map(int, actual_resolution.split('x'))
            aspect_ratio = width / height
            video_info['aspect_ratio'] = aspect_ratio
        else:
            if (actual_resolution):
                width, height = map(int, actual_resolution.split('x'))
                aspect_ratio = width / height
                video_info['aspect_ratio'] = aspect_ratio
            else:
                video_info['aspect_ratio'] = "N/A"
    print(f"Aspect ratio: {video_info['aspect_ratio']}")

    # Step 15
    # Add the video URL and download path to the global pool
    global_pool.insert_one({'video_url': url, 'download_path': video_info['filename']}) # f'{directory}/videos/{output}.%(ext)s'}
    # Step 16
    # Add the video_info data into the mongodb
    collection.insert_one(video_info)

    # Step 17
    # Write the extracted information to a new file
    extracted_info_filename = f'{directory}/json/{output}_info.json'
    # Ensure the directory exists
    os.makedirs(os.path.dirname(extracted_info_filename), exist_ok=True)
    try:
        print(f"Writing to file {extracted_info_filename}")  # Debugging print statement
        with open(extracted_info_filename, 'w') as f:
            json.dump(video_info, f, indent=4, cls=DateTimeEncoder)
        print(f"Successfully wrote to file {extracted_info_filename}")  # Debugging print statement
    # with lock: # No longer need the original JSON file - removing this to conserve space
    # Step 18
    #    time.sleep(5)
    except Exception as e:
        print(f"Error writing to file {extracted_info_filename}: {e}")
        # os.remove(json_output_filename)
        # Add additional logging
        print(f"Exception type: {type(e)}")
        print(f"Exception args: {e.args}")
        print(f"Exception: {e}")
    # Step 19
    return info, err # Return the info variable and no error
    print(f"Info: {info}")
    print(f"Error: {err}")

    # Print the output of the yt-dlp command
    # print('yt-dlp result:', result)

@app.route('/download', methods=['POST'])
def download_videos():
    # Determine the directory to save the videos to based on the username
    username = session.get('user_id')  # Use the get method to avoid a KeyError
    if 'user_id' in session:
        username = session['user_id']
    else:
        username = 'public'  # default value if user is not logged in
    # video_dir = f'{directory}/videos/{username}'
    urls = [url.strip() for url in request.form['url'].split('\n')]
    args = request.form['args'].split(' ')
    cutout = request.form['cutout'].split('-')
    output_base = request.form['output']
    errors = []
    for url in urls:
        print('Starting download for URL:', url)
        info, error = download(url, args, cutout, output_base)  # Get the info and error from the download function
        if error:
            errors.append(error)
        print('Download finished for URL:', url)
    if errors:
        return 'Download started. The following errors occurred:\n' + '\n'.join(str(errors))
    else:
        return 'Download started', 200

def delete_old_files():
    while True:
        now = time.time()
        for folder in ['/app/data/public/videos', '/app/data/public/json', '/app/data/public/thumbnails']:
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                if os.path.isfile(file_path) and os.path.getmtime(file_path) < now - 7 * 86400:
                    os.remove(file_path)
        time.sleep(3600)

def delete_video(user, video_id):
    # Remove the video from the user's list of videos
    collection.update_one({'user': user}, {'$pull': {'videos': {'id': video_id}}})

    # If the video is in the global pool and no other users have it in their list, delete the video, JSON, and thumbnail files
    video = global_pool.find_one({'video_id': video_id})
    if video and not collection.find_one({'videos.id': video_id}):
        os.remove(video['download_path'])
        os.remove(video['download_path'].replace('.%(ext)s', '.json'))
        os.remove(video['download_path'].replace('.%(ext)s', '.jpg'))
        global_pool.delete_one({'video_id': video_id})

# Start the file deletion thread
threading.Thread(target=delete_old_files).start()

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0')
