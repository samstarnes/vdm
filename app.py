import platform; print(platform.python_version())
import os
import re
import sys
import glob
import math
import time
import json
import magic
import redis
import shutil
import pymongo
import hashlib
import logging
import zipfile
import requests
import threading
import subprocess
import validators
import meilisearch
import flask_login
import urllib.request
from PIL import Image
from flask_sse import sse
from threading import Lock
from datetime import datetime
from dotenv import load_dotenv
from json import JSONDecodeError
from pymongo import MongoClient
from meilisearch import Client
from urllib.parse import urlparse
from urllib.parse import quote, unquote
from bson.objectid import ObjectId
from werkzeug.urls import url_encode
from flask import Flask, request, render_template, session, redirect, url_for, send_from_directory, Response, json, g, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required

# Lots of configuration, touch nothing here
# Everything below can be modifed within the .env file
# Start of .env
load_dotenv()
meili_master_key = os.getenv('MEILI_MASTER_KEY')
secret_key = os.getenv('SECRET_KEY')
docker_ytdl = os.getenv('DOCKER_YTDL')
docker_ytdldb = os.getenv('DOCKER_YTDLDB')
docker_ytdlmeili = os.getenv('DOCKER_YTDLMEILI')
docker_ytdlredis = os.getenv('DOCKER_YTDLREDIS')
docker_port_ytdl = os.getenv('DOCKER_PORT_YTDL')
docker_port_ytdldb = os.getenv('DOCKER_PORT_YTDLDB')
docker_port_ytdlredis = os.getenv('DOCKER_PORT_YTDLREDIS')
docker_port_ytdlmeili = os.getenv('DOCKER_PORT_YTDLMEILI')
meilisearch_url = f'http://meilisearch:7700'
# End of .env
app = Flask(__name__, static_folder='static')
r = redis.Redis(host=f'{docker_ytdlredis}', port=6379, db=0)  # adjust these parameters to your Redis configuration
app.register_blueprint(sse, url_prefix='/stream')
app.config["REDIS_URL"] = "redis://redis:6379"
# Set system default path to /app
os.environ['PATH'] += os.pathsep + '/app'
# Set up logging
logging.basicConfig(filename='app.log', filemode='w', datefmt='%Y-%m-%d %H:%M:%S', format='%(asctime)s - %(levelname)-8s %(message)s', level=logging.INFO)
app.logger.addHandler(logging.StreamHandler(sys.stdout))

    # logging.debug() 
    # logging.info()
    # logging.warning()
    # logging.error()
    # logging.critical()

# Things left to add

# High Priority
# - customizable items ordered by duration, size, download date (ID), posted date
# - configurable public item automatic deletion, cookie file, themes

# Low Priority
# - calender filter for searching between dates
# - multi-user login
# - filter function
# - normal vs reverse order

# Completed
# - create video player page (pull data with _id as URL) ✅ 
# - grab thumbnails for various downloads such as reddit ✅ 
# - append IDs to filenames so no overwriting is possible ✅
# - design new file structure ✅
# - connect mongodb ✅
# - grab thumbnails ✅
# - sanitize URLs for useless cookies for global mongoDB pool ✅
# - Stylize home page ✅
# - Progress bar ✅
# - customizable number of items displayed (kinda) ✅
# - search function ✅

bdir = os.path.dirname(os.path.realpath(__file__))
app.secret_key = secret_key
# Create a lock
lock = Lock()
# Create mongoDB connection
client = MongoClient(f'mongodb://{docker_ytdldb}:27017/') ################################################################
db = client['yt-dlp']
# Create a new collection for the downloaded files
collection = db['downloads']
# Create a new collection for the global pool
global_pool = db['global_pool']
# Create meilisearch connection
meili_client = Client(f'http://{docker_ytdlmeili}:{docker_port_ytdlmeili}', meili_master_key)  ################################################################
# meili_url for reverse proxy
meiliproxy = f'http://{docker_ytdlmeili}:7700'
# Create a directory for the executables if it doesn't exist
os.makedirs('/app', exist_ok=True)
# Download yt-dlp
urllib.request.urlretrieve('https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp', '/app/yt-dlp')
logging.info('Retrieving YT-DLP')
# Make yt-dlp executable
os.chmod('/app/yt-dlp', 0o755)
logging.info('Setting permissions to 0755')
# Download and extract ffmpeg
urllib.request.urlretrieve('https://github.com/ffbinaries/ffbinaries-prebuilt/releases/download/v4.4.1/ffmpeg-4.4.1-linux-64.zip', '/app/ffmpeg-4.4.1-linux-64.zip')
with zipfile.ZipFile('/app/ffmpeg-4.4.1-linux-64.zip', 'r') as zip_ref:
    zip_ref.extractall('/app')
    logging.info('Exacting ffmpeg')
os.remove('/app/ffmpeg-4.4.1-linux-64.zip')
logging.info('Removing old ffmpeg zip')
# Make ffmpeg executable
os.chmod('/app/ffmpeg', 0o755)
logging.info('Setting permissions to 0755')
# Download and extract ffprobe
urllib.request.urlretrieve('https://github.com/ffbinaries/ffbinaries-prebuilt/releases/download/v4.4.1/ffprobe-4.4.1-linux-64.zip', '/app/ffprobe-4.4.1-linux-64.zip')
logging.info('Retrieving ffprobe')
with zipfile.ZipFile('/app/ffprobe-4.4.1-linux-64.zip', 'r') as zip_ref:
    zip_ref.extractall('/app')
    logging.info('Extracting ffprobe')
os.remove('/app/ffprobe-4.4.1-linux-64.zip')
logging.info('Removing ffprobe zip')
# Make ffprobe executable
os.chmod('/app/ffprobe', 0o755)
logging.info('Setting permissions to 0755')
# Set cookies file path variable, default is main directory /app 
defcookiesfp = 'cookies.txt'
# video extensions global
VIDEO_EXTENSIONS = ['mp4', 'mkv', 'webm', 'flv', 'mov', 'avi', 'wmv']
# Set up Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)

def get_meilisearch_public_key():
    url = f'{meilisearch_url}/keys'
    headers = {'Authorization': f'Bearer {meili_master_key}'}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        keys = response.json().get('results', [])
        for key in keys:
            if key.get('description') == 'Use it to search from the frontend':
                return key.get('key')
    return None

# meilisearch additions ####################################################################################
def process_and_add_to_meilisearch():
    logging.info('MeiliSearch: Fetching unprocessed from MongoDB')
    print("Fetching unprocessed items from MongoDB...")
    total_items = collection.count_documents({
    "$or": [
        {"processed": False},
        {"processed": {"$exists": False}}
    ]
    })
    processed_count = 0
    # Calculate the number of batches
    unprocessed_items = collection.find({"processed": {"$ne": True}})
    docs_to_add = []
    for video_info in unprocessed_items:
        print("Processing items:", video_info['id'])
        logging.info('MeiliSearch: Processing %s', video_info['id'])
        meili_title = video_info.get('title', '')
        meili_dateposted = video_info.get('date_posted', '')
        meili_archivedate = video_info.get('archive_date', '')
        if isinstance(meili_archivedate, datetime):
            meili_archivedate = meili_archivedate.isoformat()
        meili_user = video_info.get('user', '')
        meili_url = video_info.get('video_url', '')
        # Preparing the document for MeiliSearch
        doc = {
            'id': video_info['index'],
            'primaryKey': video_info['id'],
            'title': meili_title,
            'date_posted': meili_dateposted,
            'archive_date': meili_archivedate,
            'user': meili_user,
            'video_url': meili_url,
        }
        print(doc)
        mheaders = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {meili_master_key}'
        }
        add_documents_endpoint = f'{meiliproxy}/indexes/yt-dlp_index/documents'
        mresponse = requests.post(add_documents_endpoint, headers=mheaders, data=json.dumps([doc]))
        if mresponse.status_code == 202:
            print('Documents added successfully:', mresponse.json())
        else:
            print('Failed to add documents', mresponse.content)
        # Mark the document as processed in MongoDB
        collection.update_one({'id': video_info['id']}, {'$set': {'processed': True}})
        # Add the batch of document to MeiliSearch
        # meili_client.index('yt-dlp_index').add_documents(doc)
        processed_count += 1
        percentage_completed = (processed_count / total_items) * 100
        print(f"MeiliSearch Progress: {percentage_completed:.2f}% of {processed_count}/{total_items}")
        print(f"Title: {doc['title']}, VideoURL: {doc['video_url']}")

# Run the check periodically for updating meilisearch ####################################################################################
# while True: # disabled for now but will be in a loop ###################################################################################
process_and_add_to_meilisearch() ####################################################################################
#    time.sleep(3600)  # Sleep & loop

@app.route('/search', methods=['POST'])
def search():
    # Get the query from the frontend
    srchdata = request.json
    query = srchdata.get('query', '')
    # Prepare the MeiliSearch request
    srchurl = f'{meiliproxy}/indexes/yt-dlp_index/search'
    srchheaders = {
        'Authorization': f'Bearer {meili_master_key}'
    }
    payload = {
        'q': query
    }
    # Send the request to MeiliSearch
    srchresponse = requests.post(srchurl, headers=srchheaders, json=payload)
    # Return the results to the frontend
    return jsonify(srchresponse.json())

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

@app.route('/meili', defaults={'path', ''}, methods=['GET', 'PUT', 'POST', 'DELETE'])
@app.route('/meili/<path:path>', methods=['GET', 'POST', 'DELETE'])
def proxy_to_meili(path):
    # Forward the request to MeiliSearch
    resp = requests.request(
        method=request.method,
        url=f"{meiliproxy}/{path}",
        headers={key: value for (key, value) in request.headers if key != 'Host'},
        data=request.get_data(),
        params=request.args,
        cookies=request.cookies,
        allow_redirects=False)
    # Return the response from MeiliSearch
    excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
    headers = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]
    response = Response(resp.content, resp.status_code, headers)
    return response

@app.route('/videos/<video_id>')
def video_page(video_id):
    # Fetch the video data from MongoDB using the provided ID
    video = collection.find_one({"id": video_id})
    if not video:
        return "Video not found", 404
    # Pass the video data to the template
    return render_template('video.html', video=video, bdir=bdir)

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
        # hash the password before storing it.
        if not username or not password:
            return 'Invalid username or password', 400
        # Store the username and password
        session['username'] = username
        session['password'] = password
        return redirect(url_for('home')) # redirect to the home page after registration
    else:
        return render_template('register.html')

    #############################################################
    #################### Fetch User from DB #####################

def fetch_user_from_database(username):
    # Connect to your MongoDB client
    client = MongoClient(f'mongodb://{docker_ytdldb}:27017/')
    # Select your database
    db = client['yt-dlp']
    # Select your collection (table)
    users = db['users']
    # Query for the user with the given username
    user_record = users.find_one({'username': username})
    # Return the user record
    return user_record

    #############################################################
    ##################### Update Statistics #####################

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
    logging.info('Step 07: Incrementing total_downloads by 1')
    domain = urlparse(url).netloc
    if domain not in stats['domains']:
        stats['domains'][domain] = 0
    stats['domains'][domain] += 1
    with open(stats_file, 'w') as f:
        json.dump(stats, f)
    logging.info('Step 07: Dumping stats from update_statistics')
    return stats['total_downloads'], stats['domains'][domain]

    #############################################################
    ##################### Sanitize Filename #####################

def sanitize_filename(filename, max_length=200):
    invalid_chars = '\“\”!*()[].\'%&@$/<>:"/\\|?*#;^%~`,'
    for char in invalid_chars:
        filename = filename.replace(char, '_') # remove illegal characters
        filename = re.sub(' +', ' ', filename) # remove consecutive spaces
    # Truncate and hash the filename if it's too long
    if len(filename) > max_length:
        filename_hash = hashlib.md5(filename.encode()).hexdigest()
        filename = filename[:max_length - len(filename_hash)] # + filename_hash
    logging.info('Returning filename from sanitize_filename: %s', filename)
    return filename

    #############################################################
    ###################### Video Resolution #####################
    
def get_video_resolution(filename):
    logging.info('Step 14: Processing filename: %s', filename)
    ffprobepath = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'ffprobe')
    command = [
        ffprobepath,
        '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries',
        'stream=width,height', '-of', 'csv=s=x:p=0',
        filename
    ]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, err = process.communicate()
    if err:
        logging.error('ffprobe error: %s', err.decode('utf-8'))
    return output.decode('utf-8').strip()

    #############################################################
    ####################### Video Duration ######################
		
def get_video_duration(filename):
    logging.info(f'Step 13: Processing filename: %s', filename)
    ffprobepath = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'ffprobe')
    command = [
        ffprobepath,
        '-v', 'error',
        '-show_entries',
        'format=duration', '-of', 'json',
        filename
    ]
    logging.info('Step 13: Running subprocess.Popen for get_video_duration')
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, err = process.communicate()
    if err:
        logging.error('Step 13: ffprobe error: %s', err)
    output_json = json.loads(output) 
    duration_str = output_json['format']['duration']
    try:
        duration = float(duration_str)
        logging.info(f'Step 13: duration variable set from float(): %s', duration)
    except ValueError:
        logging.error(f"Step 13: Invalid duration: {duration_str}")
        return None
    return duration

    #############################################################
    ###################### Video Format #########################

def get_video_format(filepath):
    mime = magic.Magic(mime=True)
    file_type = mime.from_file(filepath)
    # Map MIME types to file extensions
    mime_to_extension = {
        'video/webm': 'webm',
        'video/mp4': 'mp4',
        'video/quicktime': 'mov',
        'video/x-msvideo': 'avi',
        'video/x-matroska': 'mkv',
        # ... add other mappings as needed
    }
    logging.info('Step 13: get_video_format() function')
    return mime_to_extension.get(file_type)

    #############################################################
    ###################### Video Extension ######################

def get_video_extension(directory, output):
    # List all files that start with the output name
    files = glob.glob(f"{directory}/videos/{output}.*")
    # If there are any files that match
    if files:
        # Get the first file
        file = files[0]
        # Determine the video format
        vformat = get_video_format(file)
        if vformat:
            logging.info(f'Step 13: P1: Video format {vformat}')
            return vformat
        else:
            # If unable to determine format, fall back to file extension
            vextension = os.path.splitext(file)[1]
            logging.info(f'Step 13: P2: Video format {vextension}')
            return vextension.lstrip('.')
    else:
        return None

    #############################################################
    ####################### Image Check #########################

def is_image_corrupted(image_path):
    try:
        img = Image.open(image_path)
        img.verify()  # verify that it is, in fact an image
        return False
    except (IOError, SyntaxError) as e:
        return True

    #############################################################
    ################### Get IMG Format w/ PIL ###################

def get_image_format_using_pil(filepath):
    try:
        with Image.open(filepath) as img:
            format = img.format.lower()
            if format == "jpeg":
                return "jpg"
            return format
    except Exception as e:
        logging.error(f"Error determining format for {filepath}: {e}")
        return "jpg" # returning jpg instead of None to continue the process

    #############################################################
    ##################### Extract Thumbnail #####################

def extract_thumbnail(video_path, thumbnail_path):
    logging.info(f'Function: extract_thumbnail():: video_path: {video_path} :: thumbnail_path: {thumbnail_path}')
    command = [
        'ffmpeg',
        '-y',
        '-i', video_path,
        '-ss', '00:00:01',
        '-vframes', '1',
        thumbnail_path
    ]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        logging.info(f'Step 10: extract_thumbnail: stderr:\n{stderr.decode()}')
        raise subprocess.CalledProcessError(process.returncode, command)

    #############################################################
    ##################### Format Duration #######################

def format_duration(seconds):
    parts = []
    units = [("d", 60*60*24), ("h", 60*60), ("m", 60), ("s", 1)]
    for unit, div in units:
        amount, seconds = divmod(seconds, div)
        if amount > 0:
            # Check if amount is an integer
            if amount.is_integer():
                # If it's an integer, format it without a decimal point
                parts.append(f"{int(amount)}{unit}")
            else:
                # If it's a decimal, format it with a decimal point
                parts.append(f"{amount:.1f}{unit}")
    return "".join(parts)

    #############################################################
    ###################### Get File Size ########################

def get_file_size(file_path):
    time.sleep(3)
    return os.path.getsize(file_path)

    #############################################################
    ##################### URL en/decoding #######################

@app.template_filter('url_encode')
def url_encode(s):
    return quote(s)

@app.template_filter('url_decode')
def url_decode(s):
    return unquote(s)

    #############################################################
    ###################### Convert Sizes ########################

def convert_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    size_bytes = int(size_bytes)  # Convert size_bytes to an integer
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "%s %s" % (s, size_name[i])

    #############################################################
    ###################### Route /stream ########################

@app.route('/stream')
def stream():
    def event_stream():
        while True:
            # Get the progress updates from Redis
            progperc = r.get('progress')
            progtotal = r.get('total')
            progspeed = r.get('speed')
            progeta = r.get('eta')
            # Create a dictionary with the progress data
            progress_data = {
                "progress": progperc.decode() if progperc else None,
                "total": progtotal.decode() if progtotal else None,
                "speed": progspeed.decode() if progspeed else None,
                "eta": progeta.decode() if progeta else None
            }
            # Convert the dictionary to a JSON string and yield it as a Server-Sent Event
            yield f"data: {json.dumps(progress_data)}\n\n"
            time.sleep(1)
    return Response(event_stream(), mimetype="text/event-stream")

    #############################################################
    ###################### Route /videos ########################

@app.route('/videos')
def videos():
    p = int(request.args.get('p', 1))
    ipp = int(request.args.get('ipp', 20))
    offset = (p - 1) * ipp
    videos = collection.find().skip(offset).limit(ipp)
    total_videos = collection.count_documents({})
    return render_template('videos.html', videos=videos, p=p, ipp=ipp, total_videos=total_videos)

    #############################################################
    ###################### Parse Progress #######################

def parse_progress(poutput):
    # Log the output for debugging purposes
    logging.info(f'Step 07: parse_progress(poutput) = {poutput}')
    # Parse the JSON string
    try:
        progress_info = json.loads(poutput)
        # Extract the progress percentage and remove the '%' symbol
        progperc = progress_info.get('progress percentage')
        if progperc is not None:
            progperc = float(progperc.strip('%'))
            # Extract the total progress
            progtotal = progress_info.get('progress total')
            # Extract the speed
            progspeed = progress_info.get('speed')
            # Extract the ETA
            progeta = progress_info.get('ETA')
            return progperc, progtotal, progspeed, progeta
    except JSONDecodeError:
        logging.error(f"Step 07: parse_progress() Failed to parse JSON from poutput: {poutput}")
        return None, None, None, None

def download(url, args, cutout, output_base):
    #############################################################
    # Step 01 ###################################################
    #############################################################
    logging.info('Step 01: Checking if URL is in global mongodb pool...')
    # Check if the URL already exists in the global pool
    existing_video = global_pool.find_one({'video_url': url})
    if existing_video is not None:
        # If the URL exists, return a warning message and halt the download
        return None, f"Download failed for URL {url}. Error: Video URL already exists in global pool"

    #############################################################
    # Step 02 ###################################################
    #############################################################
    logging.info('Step 02: Grab yt-dlp and ffprobe paths, validate URLs')
    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.realpath(__file__))
    # Construct the full path to yt-dlp
    yt_dlp_path = os.path.join(script_dir, 'yt-dlp')
    ffprobe_path = os.path.join(script_dir, 'ffprobe')
    if not validators.url(url):
        return 'Invalid URL', 400

    #############################################################
    # Step 03 ###################################################
    #############################################################
    logging.info('Step 03: Grab video title')
    # Run yt-dlp to get video title
    with lock:
        ddir = os.getcwd()
        logging.info(f"ddir: {ddir}")
        info_command = [
            yt_dlp_path,
            '-f', 'bestvideo+bestaudio/best',
            '--skip-download',
            '--print-json',
            '--cookies', 'cookies.txt',
            url
        ]
        info_process = subprocess.Popen(info_command, stdout=subprocess.PIPE, text=True)
        info_result, err = info_process.communicate()
    try:
        info = json.loads(info_result)
        logging.info('Step 03: Set info variable in Step 3')
    except json.JSONDecodeError:
        print('yt-dlp output is not valid JSON:', info_result)
        logging.error(f'Step 03: Failed to download:` {url}')
        return None, f"Download failed for URL {url}. Error: Invalid JSON output from yt-dlp"

    #############################################################
    # Step 04 ###################################################
    #############################################################
    logging.info('Step 04: Sanitize title and output as variable')
    # Use the video title as the output name if no output name was provided
    if isinstance(info, dict) and 'title' in info:
        display_title = info['title']
        logging.info('Step 04: P1')
    else:
        display_title = "Title not found"
        logging.info('Step 04: P2')
    if not output_base:
        output = sanitize_filename(info['title'])
        fulltitle = output
        output = sanitize_filename(info['title']) + "_" + info['id']
        logging.info('Step 04: Set output variable')
        logging.info('Step 04: P3')
    else:
        output = sanitize_filename(output_base) # custom output names from form
        fulltitle = output
        output = sanitize_filename(output_base) + "_" + info['id'] # custom output names from form
        logging.warning('Step 04: Setting output to output_base')
        logging.info('Step 04: P4')

    #############################################################
    # Step 05 ###################################################
    #############################################################
    logging.info('Step 05: Determining directory (public,private)')
    # Determine the directory to save the video based on whether the user is logged in
    if flask_login.current_user.is_authenticated:
        directory = f'data/private/{flask_login.current_user.username}'
        g.directory = f'data/private/{flask_login.current_user.username}'
        logging.info('Step 05: Set directory variable, username:', flask_login.current_user.username)
    else:
        directory = 'data/public'
        g.directory = 'data/public'
        logging.info('Step 05: Set directory variable to data/public')

    #############################################################
    # Step 06 ###################################################
    #############################################################
    logging.info('Step 07: Download video with yt-dlp')
    # Run yt-dlp to download the video (1/3 files)
    # Set Command 1 for Progress/DL of video
    progresscmd = [
        yt_dlp_path,
        '-f', 'bestvideo+bestaudio/best',
        '-o', f'{directory}/videos/{output}.%(ext)s',
        '--cookies', 'cookies.txt',
        '--newline',
        '--progress-template', '{ "progress percentage":"%(progress._percent_str)s","progress total":"%(progress._total_bytes_str)s","speed":"%(progress._speed_str)s","ETA":"%(progress._eta_str)s" }',
        '--force-overwrites',
        url
    ]
    logging.info('Step 07: Set progresscmd')
    if args and args[0] != '':
        progresscmd.extend(args)
    progresscutout = request.form['cutout'].split('-')
    if len(progresscutout) == 2:  # Only add progresscutout args if two values are provided
        progresscutout_args = f'"-ss {progresscutout[0]} -to {progresscutout[1]}"'
        progresscmd.extend(['--postprocessor-args', progresscutout_args])
    # Set Command 2 for DL of JSON object
    jsoncmd = [
        yt_dlp_path,
        '-f', 'bestvideo+bestaudio/best',
        '-o', f'{directory}/videos/{output}.%(ext)s',
        '--print-json',
        '--cookies', 'cookies.txt',
        '--skip-download',
        '--force-overwrites',
        url
    ]
    logging.info('Step 07: Set jsoncmd')
    if args and args[0] != '':
        jsoncmd.extend(args)
    jsoncutout = request.form['cutout'].split('-')
    if len(jsoncutout) == 2:  # Only add jsoncutout args if two values are provided
        jsoncutout_args = f'"-ss {jsoncutout[0]} -to {jsoncutout[1]}"'
        jsoncmd.extend(['--postprocessor-args', jsoncutout_args])
    with lock:
        try:
            #############################################################
            ##################### DL/Progress/Video #####################
            #############################################################
            progressres = subprocess.Popen(progresscmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            actual_extension = None  # Initialize the variable outside the loop
            with open(f'{directory}/json/{output}_progress.json', 'w') as progress_file:  # Open the JSON file and the progress file # Open the JSON file
                while True:
                    poutput = progressres.stdout.readline()
                    # progressres.stdout.flush()
                    if poutput == '' and progressres.poll() is not None:
                        break
                    if poutput:
                        downloaded_file_line = [line for line in poutput.split('\n') if '[download] Destination:' in line]
                        if downloaded_file_line:
                            downloaded_file = downloaded_file_line[0].split()[-1]
                            potential_extension = os.path.splitext(downloaded_file)[1].lstrip('.')
                            if potential_extension in VIDEO_EXTENSIONS:
                                actual_extension = potential_extension
                                video_path = f'{directory}/videos/{output}.{actual_extension}'
                        progperc, progtotal, progspeed, progeta = parse_progress(poutput.strip())
                        if progperc is not None:
                            logging.info(f'Step 07: SSE-Event: {progperc} {progtotal} {progspeed} {progeta}')
                            # using redis to publish progress reports to client
                            sse.publish({
                                "progress": progperc,
                                "total": progtotal,
                                "speed": progspeed,
                                "eta": progeta
                            }, type='download_progress')
                            # Save JSON output to a file (2/3 files)
                            # progress_file.write(poutput)  # Write the output to the JSON file
                    rc = progressres.poll()
            logging.info(f'Step 07: Writing output to JSON - 2/3 files (json)')
            #############################################################
            ######################### DL/JSON ###########################
            #############################################################
            jsonres = subprocess.Popen(jsoncmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            with open(f'{directory}/json/{output}.json', 'w') as json_file: # Open the JSON file
                while True:
                    poutput = jsonres.stdout.readline()
                    # progressres.stdout.flush()
                    if poutput == '' and jsonres.poll() is not None:
                        break
                    if poutput:
                        # Save JSON output to a file (2/3 files)
                        logging.info(f'Step 07: Writing output to JSON - 2/3 files (json)')
                        # logging.info(f'Step 07: poutput = {poutput}')
                        json_file.write(poutput)  # Write the output to the JSON file
        except subprocess.CalledProcessError as e:
            logging.error(f"Step 07: Download failed with error: {e}")
            download_process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            jsonres, err = download_process.communicate()
            if download_process.returncode != 0:
                logging.info(f"Step 07: From subprocess.Popen: {err}")
            return f"Step 07: Download failed with error: {e}", 500
    print(f"S07E: {jsonres.stderr}")
    json_output_filename = f'{directory}/json/{output}.json'

    #############################################################
    # Step 07 ###################################################
    #############################################################
    logging.info('Step 08: 1/3 Increasing download number in update_statistics')
    # Increase download number 
    download_number = update_statistics(url)[0]

    #############################################################
    # Step 08 ###################################################
    #############################################################
    logging.info('Step 10: 3/3 Download thumbnail to file')
    # Run yt-dlp to download the thumbnail (3/3 files)
    tmbs = [
        yt_dlp_path,
        '--skip-download',
        '--write-thumbnail',
        '-o', f'{directory}/thumbnails/{output}',
        '--cookies', 'cookies.txt',
        url
    ]
    with lock:
        download_process = subprocess.Popen(tmbs, stdout=subprocess.PIPE, text=True)
        result, err = download_process.communicate()
        logging.info('Step 10: Downloading thumbnail')
    time.sleep(3)
    logging.info(f'Step 10: output for tmb13 P1: {output}')
    # List all files that start with the output name
    files = glob.glob(f'{directory}/thumbnails/{output}*')
    # If there are any files that match
    if files:
        # Get the first file
        file = files[0]
        logging.info(f'Step 10: list of files: {file}')
        extension = get_image_format_using_pil(file)
        logging.info(f'Step 10: extension: {extension}')
    else:
        extension = None
        logging.info(f'Step 10: error: output for tmb13 P2: {output}')
    thumbnail_path = f'{file}'
    if is_image_corrupted(thumbnail_path):
        logging.info('Step 10: Thumbnail is corrupted, extracting a new one from the video')
        time.sleep(5)
        # vextension = get_video_extension(directory, output)
        logging.info(f'Step 10: video_path: {video_path}')
        logging.info(f'Step 10: output: {output}')
        logging.info(f'Step 10: extension: {extension}')
        extract_thumbnail(video_path, thumbnail_path)

    #############################################################
    # Step 09 ###################################################
    #############################################################
        # Load the JSON data
    try:
        with open(json_output_filename, 'r') as f:
            logging.info('Step 11: Setting data variable')
            data = json.load(f)
    except json.JSONDecodeError:
        logging.error(f"Step 11: Failed to load JSON data from {json_output_filename}. File content might be empty or not properly formatted.")
        data = None

    #############################################################
    # Step 10 ###################################################
    #############################################################

    try:
        tfilesize = get_file_size(data["_filename"])
        logging.info('Step 11: trying to grab filesize from file')
    except:
        tfilesize = 0

    #############################################################
    # Step 11 ###################################################
    #############################################################
    # Set the default filename to grab the aspect_ratio/resolution
    fnprobe = data['_filename']
    # Set filename first as this is most important
    # This does NOT set {bdir} as that is not a valid location under /app
    filename = data["_filename"]
    logging.info(f'Step 13: {get_video_duration(fnprobe)}')
    video_info = {
        'index': download_number,
        'id': data.get('id', "unknown"),
        'title': display_title, # previously set
        'date_posted': data.get('upload_date', "unknown"),
        'archive_date': datetime.now(), # BSON datetime object, date-based queries
        'user': data.get("uploader", "unknown"),
        'video_url': data.get('webpage_url', "unknown"),
        'length': format_duration(get_video_duration(fnprobe)),
        'filename': f'{bdir}{filename}',
        'thumbnail': f'{bdir}{directory}/thumbnails/{sanitize_filename(output)}.{extension}',
        'tmbfp': f'{file}', # set from image extraction way above
        'json_file': f'{bdir}{directory}/json/{sanitize_filename(output)}.json',
        'file_size_bytes': tfilesize,
        'file_size_readable': "unknown",
        'resolution': "unknown",
        'aspect_ratio': "unknown"
    }
    logging.info('Step 13: Displaying video_info[] data')
    logging.info('vInfo: index: %s', video_info['index'])
    logging.info('vInfo: id: %s', video_info['id'])
    logging.info('vInfo: title: %s', video_info['title'])
    logging.info('vInfo: date_posted: %s', video_info['date_posted'])
    logging.info('vInfo: archive_date: %s', video_info['archive_date'])
    logging.info('vInfo: user: %s', video_info['user'])
    logging.info('vInfo: video_url: %s', video_info['video_url'])
    logging.info('vInfo: length: %s', video_info['length'])
    logging.info('vInfo: filename: %s', video_info['filename'])
    logging.info('vInfo: file_size_bytes:  %s', video_info['file_size_bytes'])
    logging.info('vInfo: file_size_readable: unknown')
    logging.info('vInfo: resolution0: unknown')
    logging.info('vInfo: aspect_ratio0: unknown')
    logging.info('vInfo: thumbnail: "%s"', video_info['thumbnail'])
    logging.info('vInfo: tmbfp: "%s"', video_info['tmbfp'].replace('data/', '', 1))

    #############################################################
    # Step 12 ###################################################
    #############################################################
    logging.info('Step 14: Grab filename from JSON, get resolution and aspect ratio with ffprobe')
    # Get the filename of the downloaded file from the JSON output
    downloaded_video_filename = video_info['filename']
    # After the download is complete, get the actual resolution of the downloaded video
    actual_resolution = get_video_resolution(fnprobe)
    logging.info('Step 14: Set actual_resolution from get_video_resolution function using downloaded_video_filename')
    # Update the 'resolution' field in the video_info dictionary
    if (actual_resolution):
        video_info['resolution'] = actual_resolution
    else:
        video_info['resolution'] = "unknown"
    logging.info('vInfo: resolution1: "%s"', video_info['resolution'])
    # Update the 'aspect ratio' field in the video_info dictionary
    for format in data['formats']:
        vcodec = format.get('vcodec', 'none')
        acodec = format.get('acodec', 'none')
        if vcodec != 'none' and acodec != 'none':  # Exclude audio-only or video-only formats
            if actual_resolution and 'x' in actual_resolution:
                width, height = map(int, actual_resolution.split('x'))
                aspect_ratio = width / height
                video_info['aspect_ratio'] = aspect_ratio
                logging.info('Step 14: P1: Attempting setting video_info[] for aspect_ratio searching for vcodec and acodec')
            else:
                video_info['aspect_ratio'] = "unknown"
                logging.info('Step 14: P2: No aspect ratio found because actual_resolution is not valid')
        else:
            if actual_resolution and 'x' in actual_resolution:
                width, height = map(int, actual_resolution.split('x'))
                aspect_ratio = width / height
                video_info['aspect_ratio'] = aspect_ratio
                logging.info('Step 14: P3: Attempting setting video_info[] for aspect_ratio with actual_resolution math')
            else:
                video_info['aspect_ratio'] = "unknown"
                logging.info('Step 14: P4: No aspect ratio found because actual_resolution is not valid')
    print(f"Aspect ratio: {video_info['aspect_ratio']}")
    logging.info('vInfo: aspect ratio1: "%s"', video_info['aspect_ratio'])

    # Update file size into readable format
    file_size_readable = convert_size(video_info['file_size_bytes'])
    video_info['file_size_readable'] = file_size_readable
    logging.info('Step 14: Adding file_size_readable to video_info[]')

    #############################################################
    # Step 13 ###################################################
    #############################################################
    logging.info('Step 15: Add video URL to global mongodb pool')
    # Add the video URL and download path to the global pool
    global_pool.insert_one({'video_url': url, 'download_path': video_info['filename']})
    logging.info('Step 15: mongoDB: adding the video URL to the global pool')

    #############################################################
    # Step 14 ###################################################
    #############################################################
    logging.info('Step 16: Insert video_info[] data into collection in mongodb database')
    # Add the video_info data into the mongodb
    collection.insert_one(video_info)
    logging.info('Step 16: Adding video_info[] to collection')
		
    process_and_add_to_meilisearch()

    #############################################################
    # Step 15 ###################################################
    #############################################################
    # Write the extracted information to a new file
    extracted_info_filename = f'{directory}/json/{output}_info.json'
    logging.info('Step 17: Setting extracted_info_filename variable to output_info.json')
    # Ensure the directory exists
    os.makedirs(os.path.dirname(extracted_info_filename), exist_ok=True)
    try:
        print(f"Writing to file {extracted_info_filename}")  # Debugging print statement
        with open(extracted_info_filename, 'w') as f:
            json.dump(video_info, f, indent=4, cls=DateTimeEncoder)
            logging.info('Step 17: Dumping video_info[] json to file ')
        print(f"Successfully wrote to file {extracted_info_filename}")  # Debugging print statement
        logging.info('Step 17: Wrote to extracted_info_filename new data')
        os.remove(json_output_filename) # disable this for debug for original json data
        logging.info('Step 17: Removing old JSON data')

    #############################################################
    # Step 16 ###################################################
    #############################################################
    except Exception as e:
        print(f"Error writing to file {extracted_info_filename}: {e}")
        logging.info(f'Step 18: remove original JSON: %s', json_output_filename)
        os.remove(json_output_filename) # disable this for debug for original json data

    #############################################################
    # Step 17 ###################################################
    #############################################################
    logging.info('Step 19: "Return"')
    return info, err

@app.route('/download', methods=['POST'])
def download_videos():
    # Determine the directory to save the videos to based on the username
    username = session.get('user_id')  # Use the get method to avoid a KeyError
    if 'user_id' in session:
        username = session['user_id']
    else:
        username = 'public'  # default value if user is not logged in
    urls = [url.strip() for url in request.form['url'].split('\n')]
    args = request.form['args'].split(' ')
    # Get the path to the cookies file from the form
    cookies_file_path = request.form.get('cookies_file', '')
    # If no cookies file was provided, use the default cookies file
    defcookiesfp = 'cookies.txt'
    if not cookies_file_path:
        cookiesfp = defcookiesfp
    args.extend(['--cookies', cookiesfp])
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

#def delete_old_files():
#    while True:
#        now = time.time()
#        for folder in ['/app/data/public/videos', '/app/data/public/json', '/app/data/public/thumbnails']:
#            for filename in os.listdir(folder):
#                file_path = os.path.join(folder, filename)
#                if os.path.isfile(file_path) and os.path.getmtime(file_path) < now - 7 * 86400:
#                    os.remove(file_path)
#        time.sleep(3600)

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
        logging.info(f'Delete_video() function, deleting %s:', video['download_path'])

# Start the file deletion thread
#threading.Thread(target=delete_old_files).start()

@app.route('/data/<path:filename>')
def serve_data(filename):
    filename = filename.replace('data/', '', 1)
    return send_from_directory('data', filename)

@app.route('/')
def home():
    # Get the current page number and number of items per page from the query parameters
    p = request.args.get('p', default=1, type=int)
    ipp = request.args.get('ipp', default=20, type=int)
    offset = (p - 1) * ipp
    # Calculate the total number of videos
    total_videos = collection.count_documents({}) 
    # Calculate the total number of pages
    total_pages = (total_videos + ipp - 1) // ipp
    # Query MongoDB to get the video data
    # videos = list(collection.find())
    videos = list(collection.find({}).skip(offset).limit(ipp))
    # Modify the tmbfp attribute by removing "data/" prefix and replace special characters
    for video in videos:
        video['tmbfp'] = video['tmbfp'].replace("data/", "", 1)
        video['tmbfp'] = video['tmbfp'].replace('(', '%28').replace(')', '%29').replace('\\', '%5C')
        video['tmbfp'] = unquote(video['tmbfp'])
    # Pass the video data to the template
    directory = getattr(g, 'directory', None)
    search_api_key = get_meilisearch_public_key()
    return render_template('index.html', videos=videos, p=p, total_pages=total_pages, ipp=ipp, bdir=bdir, directory=directory, meilisearch_url=meilisearch_url, search_api_key=search_api_key)

if __name__ == '__main__':
    app.debug = False
    app.run(host='0.0.0.0', threaded=True)
