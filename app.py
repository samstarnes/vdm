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
import inspect
import difflib
import pymongo
import hashlib
import logging
import zipfile
import tempfile
import requests
import functools
import threading
import subprocess
import validators
import meilisearch
import flask_login
import urllib.request
from PIL import Image
from queue import Queue
from flask_sse import sse
from threading import Lock
from threading import Thread
from datetime import datetime
from dotenv import load_dotenv
from json import JSONDecodeError
from pymongo import MongoClient
from meilisearch import Client
from subprocess import TimeoutExpired
from urllib.parse import urlparse
from urllib.parse import quote, unquote
from bson.objectid import ObjectId
from werkzeug.urls import url_encode
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from flask import Flask, request, render_template, session, redirect, url_for, send_file, send_from_directory, make_response, Response, json, g, jsonify, abort, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required

# Print current working directory
print("Current Working Directory:", os.getcwd())

# Print files in /app directory
print("Files in /app directory:", os.listdir('/app'))

# Lots of configuration, touch nothing here
# Any docker_* variable can be modifed within the .env file
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
docker_max_concurrent_conversions = int(os.getenv('MAX_CONCURRENT_CONVERSIONS', '1'))
docker_max_workers = int(os.getenv('MAX_WORKERS', '1'))
docker_mainpath = os.getenv('MAINPATH')
# End of .env
conversion_queue = Queue(maxsize=docker_max_workers) # Initialize the queue
ongoing_conversions = {} # This dictionary tracks ongoing conversions to prevent duplicate tasks
conversion_lock = Lock() # Thread locking
ffmpeg_lock = Lock() # Dedicated conversion lock for ffmpeg execution
meilisearch_url = f'http://meilisearch:7700'
pagedisplaylimit = os.getenv('PAGENUMDISPLAYLIMIT')
UPLOAD_FOLDER = 'uploads' # For uploading backups back to mongodb
ALLOWED_EXTENSIONS = {'zip'} # For uploading backups back to mongodb
app = Flask(__name__, static_folder='static')
r = redis.Redis(host=f'{docker_ytdlredis}', port=6379, db=0)  # adjust these parameters to your Redis configuration
app.register_blueprint(sse, url_prefix='/stream')
app.config["REDIS_URL"] = "redis://redis:6379"
app.config['PREFERRED_URL_SCHEME'] = 'https'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
os.environ['PATH'] += os.pathsep + '/app' # Set system default path to /app
logging.basicConfig(filename='app.log', filemode='w', datefmt='%Y-%m-%d %H:%M:%S', format='%(asctime)s - %(levelname)-8s %(message)s', level=logging.INFO) # Set up logging
logger = logging.getLogger(__name__)
app.logger.addHandler(logging.StreamHandler(sys.stdout))
bdir = os.path.dirname(os.path.realpath(__file__)) # Base directory where this application is located
HLS_FILES_DIR = os.path.join(bdir, 'data', 'hls/') # HLS variables and dictionaries
ongoing_conversions = {}
app.secret_key = secret_key # app secret
lock = Lock() # Create a lock
client = MongoClient(f'mongodb://{docker_ytdldb}:27017/') # Create mongoDB connection
db = client['yt-dlp']
collection = db['downloads']    # Create a new collection for downloads,
global_pool = db['global_pool'] #                             global_pool,
admin_settings = db['settings'] #                             and settings
meili_client = Client(f'http://{docker_ytdlmeili}:{docker_port_ytdlmeili}', meili_master_key) # Create meilisearch connection
meiliproxy = f'http://{docker_ytdlmeili}:7700' # meili_url for reverse proxy
admsettings = { # Set default admin config options for admin panel
    'volumes': ["/app"],
    'strategy': "roundrobin", # or highwatermark
    'lastUsedVolumeIndex': "0",
    'theme': "dark",
    'sortby': "download_date",
    'itemsperpage': 20,
    'pagenumdisplaylimit': 15,
    'maxconcurrentconversions': 0
}

def log_with_line_no(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Get the caller's frame
        frame = inspect.currentframe().f_back
        line_no = frame.f_lineno
        # Append line number to the message
        if 'extra' in kwargs:
            kwargs['extra']['line_no'] = line_no
        else:
            kwargs['extra'] = {'line_no': line_no}
        return func(*args, **kwargs)
    return wrapper
    
# Enhance the logger functions
logging.info = log_with_line_no(logging.info)
logging.debug = log_with_line_no(logging.debug)
logging.warning = log_with_line_no(logging.warning)
logging.error = log_with_line_no(logging.error)
logging.critical = log_with_line_no(logging.critical)

def printline(*args, **kwargs):
    frame = inspect.currentframe().f_back
    line_number = frame.f_lineno
    print(f"Line {line_number}:", *args, **kwargs)

def set_default_settings():
    current_settings = admin_settings.find_one({})
    if not current_settings:
        admin_settings.insert_one(admsettings)
    else:
        # Check for each key in admsettings if it exists in current_settings
        updates = {key: value for key, value in admsettings.items() if key not in current_settings}
        if updates:
            # If there are keys missing in current_settings, update the document
            admin_settings.update_one({}, {'$set': updates})
set_default_settings()
def get_selected_volumes():
    settings_document = admin_settings.find_one({}, {'volumes': 1, '_id': 0})
    if settings_document:
        return settings_document.get('volumes', [])
    return []
selected_volumes = get_selected_volumes()
defcookiesfp = 'cookies.txt' # Set cookies file path variable, default is main directory /app 
VIDEO_EXTENSIONS = ['mp4', 'mkv', 'webm', 'flv', 'mov', 'avi', 'wmv'] # video extensions global


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

os.makedirs('/app', exist_ok=True) # Create a directory for the executables if it doesn't exist
urllib.request.urlretrieve('https://github.com/yt-dlp/yt-dlp-nightly-builds/releases/latest/download/yt-dlp', '/app/yt-dlp') # Download yt-dlp
os.chmod('/app/yt-dlp', 0o755) # Make yt-dlp executable
urllib.request.urlretrieve('https://github.com/ffbinaries/ffbinaries-prebuilt/releases/download/v4.4.1/ffmpeg-4.4.1-linux-64.zip', '/app/ffmpeg-4.4.1-linux-64.zip') # Download and extract ffmpeg
with zipfile.ZipFile('/app/ffmpeg-4.4.1-linux-64.zip', 'r') as zip_ref:
    zip_ref.extractall('/app')
os.remove('/app/ffmpeg-4.4.1-linux-64.zip')
os.chmod('/app/ffmpeg', 0o755) # Make ffmpeg executable
urllib.request.urlretrieve('https://github.com/ffbinaries/ffbinaries-prebuilt/releases/download/v4.4.1/ffprobe-4.4.1-linux-64.zip', '/app/ffprobe-4.4.1-linux-64.zip') # Download and extract ffprobe
with zipfile.ZipFile('/app/ffprobe-4.4.1-linux-64.zip', 'r') as zip_ref:
    zip_ref.extractall('/app')
os.remove('/app/ffprobe-4.4.1-linux-64.zip')
os.chmod('/app/ffprobe', 0o755) # Make ffprobe executable
login_manager = LoginManager() # Set up Flask-Login
login_manager.init_app(app)

def monitor_system():
    while True:
        # Log the current conversion queue size
        logging.info(f"HLS: Current conversion queue size: {conversion_queue.qsize()}")
        # add extra shit to monitor
        time.sleep(60)

#############################################################
######################## MeiliSearch ########################
#############################################################

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

def ensure_meilisearch_index(index_name):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {meili_master_key}'
    }
    get_indexes_endpoint = f'{meiliproxy}/indexes'
    response = requests.get(get_indexes_endpoint, headers=headers)
    
    if response.status_code != 200:
        logging.error(f'Failed to fetch indexes: {response.content}')
        return False
    try:
        indexes_response = response.json()
        indexes = indexes_response.get('results', [])
        logging.info(f'Fetched indexes: {indexes}')
        index_names = [index['uid'] for index in indexes]
    except Exception as e:
        logging.error(f'Error parsing indexes: {e}')
        return False

    if index_name not in index_names:
        logging.info(f'Index "{index_name}" not found. Creating it...')
        create_index_endpoint = f'{meiliproxy}/indexes'
        create_index_data = {
            'uid': index_name,
            'primaryKey': 'id'
        }
        create_response = requests.post(create_index_endpoint, headers=headers, data=json.dumps(create_index_data))
        if create_response.status_code == 201:
            logging.info(f'Index "{index_name}" created successfully.')
            return True
        else:
            logging.error(f'Failed to create index: {create_response.content}')
            return False
    else:
        logging.info(f'Index "{index_name}" already exists.')
        return True

def clear_meilisearch_index(index_name):
    try:
        logging.info(f'Clearing MeiliSearch index: {index_name}')
        headers = {
            'Authorization': f'Bearer {meili_master_key}'
        }
        delete_endpoint = f'{meiliproxy}/indexes/{index_name}'
        response = requests.delete(delete_endpoint, headers=headers)
        if response.status_code == 204:
            logging.info(f'Successfully cleared the index: {index_name}')
            return True
        else:
            logging.error(f'Failed to clear the index: {index_name}. Response: {response.content}')
            return False
    except Exception as e:
        logging.error(f'An error occurred while clearing the MeiliSearch index: {e}')
        return False

def reset_processed_status_in_mongodb():
    try:
        logging.info('Resetting processed status for all MongoDB entries...')
        result = collection.update_many({}, {'$set': {'processed': False}})
        logging.info(f'Successfully reset processed status for {result.modified_count} items.')
        return True
    except Exception as e:
        logging.error(f'An error occurred while resetting processed status: {e}')
        return False

def reindex_meilisearch_data():
    try:
        logging.info('Reindexing MeiliSearch data...')
        # Fetch all items for reindexing
        unprocessed_items = collection.find({})
        documents = []
        for video_info in unprocessed_items:
            doc = {
                'id': video_info['index'],
                'primaryKey': video_info['id'],
                'title': video_info.get('title', ''),
                'date_posted': video_info.get('date_posted', ''),
                'archive_date': video_info.get('archive_date', '').isoformat() if isinstance(video_info.get('archive_date'), datetime) else video_info.get('archive_date', ''),
                'user': video_info.get('user', ''),
                'video_url': video_info.get('video_url', ''),
                'tmbfp': video_info.get('tmbfp', '')
            }
            documents.append(doc)
        mheaders = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {meili_master_key}'
        }
        add_documents_endpoint = f'{meiliproxy}/indexes/{index_name}/documents'
        mresponse = requests.post(add_documents_endpoint, headers=mheaders, data=json.dumps(documents))
        if mresponse.status_code == 202:
            logging.info('Documents reindexed successfully.')
            # Update MongoDB to set 'processed' to True
            for video_info in unprocessed_items:
                collection.update_one({'id': video_info['id']}, {'$set': {'processed': True}})
                processed_count += 1
                percentage_completed = (processed_count / total_items) * 100
            logging.info(f"MeiliSearch Progress: {percentage_completed:.2f}% of {processed_count}/{total_items}")
        else:
            logging.error(f'Failed to reindex documents: {mresponse.content}')
            logging.error(f'If MDB_CORRUPTED: If you are trying to use an NFS mount as meili data storage, it will not work')
    except Exception as e:
        logging.error(f'An error occurred during reindexing: {e}')
        logging.error(f'If MDB_CORRUPTED: If you are trying to use an NFS mount as meili data storage, it will not work')

def handle_mdb_corrupted_error():
    logging.error('Handling MDB_CORRUPTED error. Attempting to clear and reindex MeiliSearch.')
    index_name = 'yt-dlp_index'
    # Step 1: Clear the MeiliSearch index
    if clear_meilisearch_index(index_name):
        # Step 2: Reset 'processed' status in MongoDB
        if reset_processed_status_in_mongodb():
            # Step 3: Reindex the data
            reindex_meilisearch_data()
        else:
            logging.error('Failed to reset processed status in MongoDB. Aborting reindexing.')
    else:
        logging.error('Failed to clear the MeiliSearch index. Aborting reindexing.')

def process_and_add_to_meilisearch():
    logging.info('MeiliSearch: Fetching unprocessed items from MongoDB')
    total_items = collection.count_documents({
        "processed": {"$ne": True}
    })
    logging.info(f'MeiliSearch: total_items = {total_items}')
    processed_count = 0
    if total_items == 0:
        logging.info("No unprocessed items found in the database.")
        return
    index_name = 'yt-dlp_index'
    if not ensure_meilisearch_index(index_name):
        logging.error(f'Failed to ensure the index "{index_name}" exists.')
        return
    unprocessed_items = collection.find({"processed": {"$ne": True}})
    for video_info in unprocessed_items:
        try:
            logging.info(f"Current video_info data: {video_info}")
            video_index = video_info.get('index')
            video_id = video_info.get('id')
            if video_index is not None:
                logging.info(f"process_and_add_to_meilisearch: Video Index: {video_index}")
            else:
                logging.info("process_and_add_to_meilisearch: Video Index is missing or null")
            if video_id is not None:
                logging.info(f"process_and_add_to_meilisearch: Video Id: {video_id}")
            else:
                logging.info("process_and_add_to_meilisearch: Video Id is missing or null")
            meili_title = video_info.get('title', '')
            meili_dateposted = video_info.get('date_posted', '')
            meili_archivedate = video_info.get('archive_date', '')
            if isinstance(meili_archivedate, datetime):
                meili_archivedate = meili_archivedate.isoformat()
            meili_user = video_info.get('user', '')
            meili_url = video_info.get('video_url', '')
            meili_tmbfp = video_info.get('tmbfp', '')
            doc = {  # Preparing the document for MeiliSearch
                'id': video_info['index'],
                'primaryKey': video_info['id'],
                'title': meili_title,
                'date_posted': meili_dateposted,
                'archive_date': meili_archivedate,
                'user': meili_user,
                'video_url': meili_url,
                'tmbfp': meili_tmbfp
            }
            logging.info(f'Document to add to MeiliSearch: {doc}')
            mheaders = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {meili_master_key}'
            }
            add_documents_endpoint = f'{meiliproxy}/indexes/{index_name}/documents'
            mresponse = requests.post(add_documents_endpoint, headers=mheaders, data=json.dumps([doc]))
            if mresponse.status_code == 202:
                logging.info(f'Documents added successfully: {mresponse.json()}')
                # Mark the document as processed in MongoDB
                collection.update_one({'id': video_info['id']}, {'$set': {'processed': True}})
                processed_count += 1
                percentage_completed = (processed_count / total_items) * 100
                logging.info(f"MeiliSearch Progress: {percentage_completed:.2f}% of {processed_count}/{total_items}")
            else:
                logging.error(f'Failed to add documents: {mresponse.content}')
                if b'MDB_CORRUPTED' in mresponse.content:
                    logging.error(f'MDB_CORRUPTED error encountered. Details: {mresponse.content}')
                    # Handle the MDB_CORRUPTED error
                    handle_mdb_corrupted_error()
                    break  # Stop processing further to handle corruption
                continue
        except KeyError as e:
            logging.error(f"Key error: {str(e)} - some required video information is missing")
            logging.info(f"Failed video_info: {video_info}")
        except Exception as e:
            logging.error(f"An error occurred: {str(e)}")
            logging.info(f"An error occurred: {str(e)}")

def meilisearch_bg_process(): 
    while True: 
        process_and_add_to_meilisearch()
        time.sleep(1800)

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

#############################################################
########################### Users ###########################
#############################################################

@login_manager.user_loader
def load_user(user_id):
    # Fetch the user from the database using the user_id
    user_record = fetch_user_from_database(user_id)  # You need to implement this function
    # Create a User object using the username and password from the user_record
    if user_record is None:
        return None
    user = User(user_record['username'], user_record['password'])
    return user

#############################################################
############## HLS Segments / Queue and convert #############
#############################################################

def convert_to_hls(video_id, input_filepath, max_retries=3):
    logging.info('HLS: 01')
    output_dir = os.path.join(HLS_FILES_DIR, video_id)
    os.makedirs(output_dir, exist_ok=True)
    output_playlist = os.path.join(output_dir, f"{video_id}.m3u8")
    logging.info('Convert_to_HLS: %s', f"{output_playlist}")
    logging.info(f"HLS: 02")
    printline(f'{input_filepath}')
    printline(f'{output_playlist}')
    command = [
        "ffmpeg",
        "-i", input_filepath,
        "-c:v", "libx264",
        "-c:a", "aac",
        "-start_number", "0",
        "-hls_time", "10",
        "-hls_list_size", "0",
        "-f", "hls",
        output_playlist
    ]
    retries = 0
    while retries <= max_retries:
        try:
            with ffmpeg_lock:
                # Attempt to run ffmpeg with a timeout
                logging.info(f"HLS: 03 Starting ffmpeg version for {video_id}")
                subprocess.run(command, check=True, timeout=3600)
                logging.info(f"HLS: 03 ffmpeg command for video_id {video_id} completed successfully.")
                break # Break out of the loop if unsuccessful
        except TimeoutExpired:
            logging.info(f"HLS: 03.0 ffmpeg command for video_id {video_id} timed out. Attempt {retries + 1} of {max_retries}.")
            retries += 1
        except Exception as e:
            logging.info(f"HLS: 03.1 ffmpeg command for video_id {video_id} failed with error {e}")
            break

def conversion_worker():
    while True:
        video_id, input_filepath = conversion_queue.get()
        logging.info(f"HLS: 06")
        logging.info(f"HLS: 06.0 Worker started processing task for video_id {video_id}")
        try:
            with conversion_lock:  # Acquire lock
                if video_id not in ongoing_conversions:
                    ongoing_conversions[video_id] = True
                    logging.info(f"HLS: 07")
            # Perform conversion outside the lock to not block other operations
            logging.info(f"HLS: 06.1 Worker started processing task for video_id {video_id}")
            logging.info(f"HLS: 08.0 convert_to_hls() started")
            convert_to_hls(video_id, input_filepath)
            logging.info(f"HLS: 08.1 convert_to_hls() complete")
        except Exception as e:
            logging.info(f"HLS 08.2 Conversion failed for {video_id} with error {e}")
        finally:
            with conversion_lock:  # Acquire lock again to update dictionary
                logging.info(f"HLS: 09.0")
                ongoing_conversions.pop(video_id, None)
                logging.info(f"HLS: 09.1")
            logging.info(f"HLS: 10.0")
            conversion_queue.task_done()
            logging.info(f"HLS: 10.1")
            logging.info(f'HLS: 10.2 Task masked as finished for video_id: {video_id}')

def initialize_workers():
    num_workers = max(1, docker_max_workers)
    logging.info(f"HLS: 11 Initializing {num_workers} worker threads.")
    for _ in range(num_workers):
        logging.info(f"HLS: 11.1 Starting a new worker thread")
        worker = threading.Thread(target=conversion_worker, daemon=True)
        logging.info(f"HLS: 11.2 Configured threading worker")
        worker.start()
        logging.info(f"HLS: 11.3 Worker started")

initialize_workers()

def async_convert_to_hls(video_id, input_filepath):
    with conversion_lock:  # Acquire lock to check and update dictionary
        if video_id in ongoing_conversions:
            printline(f"Conversion for video_id {video_id} is already in progress.")
            return
    # Add the task to the queue without holding the lock to avoid blocking
    logging.info(f'HLS: 13.1 Adding to conversion queue video_id: {video_id}')
    conversion_queue.put((video_id, input_filepath))
    logging.info(f'HLS: 13.2 Task added to conversion queue video_id: {video_id}')

@app.route('/serve_hls/<video_id>/<filename>')
def serve_hls_segment(video_id, filename):
    return send_from_directory(os.path.join(HLS_FILES_DIR, video_id), filename)

@app.route('/serve_hls/<video_id>/<path:filename>')
def serve_hls(video_id, filename):
    logging.info('Serving HLS segment for video_id: %s, filename: %s', video_id, filename)
    # Determine the full path to the requested file within the video_id directory
    file_path = os.path.join(HLS_FILES_DIR, video_id, filename)
    # Check if the requested file exists
    if not os.path.exists(file_path):
        logging.info('Error serving HLS segment for video_id: %s, filename: %s', video_id, filename)
        abort(404, description="File not found")
    # Serve the requested file
    return send_from_directory(os.path.join(HLS_FILES_DIR, video_id), filename)

# Delivers /videos/ID video page for a single video (player)
@app.route('/videos/<video_id>')
def video_page(video_id):
    # Fetch the video data from MongoDB using the provided ID
    video = collection.find_one({"id": video_id})
    logging.info('Loading video page for video_id: %s', video_id)
    if not video:
        return "Video not found", 404
    # Fix data to pass to videos.html for <meta> tags
    video['filename'] = video['filename'].replace(docker_mainpath, '/app/')
    video['filename'] = video['filename'].replace('/appdata/public/', '/app/data/public/')
    video['filename'] = video['filename'].replace('/app/data/', 'data/')
    video['tmbfp'] = video['tmbfp'].replace('/data/data/public/', '/data/public/')
    # Construct the HLS playlist path
    hls_playlist_path = os.path.join(HLS_FILES_DIR, video_id, f'{video_id}.m3u8')
    # Check if the HLS playlist exists and is ready
    if os.path.exists(hls_playlist_path):
        # HLS playlist exists, render the video page directly
        playlist_url = url_for('serve_hls', video_id=video_id, filename=f'{video_id}.m3u8', _external=True)
        logging.info('Serving video.html with HLS playlist URL')
        return render_template('video.html', video_id=video_id, video=video, bdir=bdir, hls_playlist=playlist_url)
    else:
        # HLS playlist does not exist, initiate conversion if not already in progress
        with conversion_lock:
            if video_id not in ongoing_conversions:
                ongoing_conversions[video_id] = True
                try:
                    conversion_queue.put((video_id, video['filename']))
                    logging.info(f'HLS: 22.1 Conversion initiated for video_id {video_id}, {video["filename"]}')
                    printline(f"Conversion initiated for video_id {video_id}, {video['filename']}.")
                except Queue.Full:
                    logging.info(f"HLS: 22.2 Conversion queue is full. Cannot add task for video_id {video_id}")
            else:
                logging.info(f"HLS: 22.3 Conversion for video_id {video_id} is already in progress or queued")
        # Render a loading page while conversion is in progress
        # Note: The loading page should periodically check for conversion completion.
        logging.info(f'HLS: 23.4 video_page app route: choosing loading.html')
        return render_template('loading.html', video_id=video_id, video=video, bdir=bdir)

@app.route('/check_hls/<video_id>')
def check_hls(video_id):
    logging.info(f"HLS: 24 Check_hls start")
    hls_playlist_path = os.path.join(HLS_FILES_DIR, video_id, f'{video_id}.m3u8')
    if os.path.exists(hls_playlist_path):
        # Construct the relative URL path for the playlist (removes /app)
        playlist_url = url_for('serve_hls', video_id=video_id, filename=f'{video_id}.m3u8', _external=True)
        return jsonify({'status': 'ready', 'playlist': playlist_url})
        logging.info(f'check_hls: playlist is ready')
        logging.info(f"HLS: 25 Check_hls is READY")
    else:
        logging.info(f"HLS: 26 Check_hls processing")
        logging.info(f'check_hls: playlist is processing')
        return jsonify({'status': 'processing'})

@app.route('/player')
def player():
    filename = request.args.get('filename')
    if not filename:
        return "Filename not provided", 400
    filename = filename.replace('data/', '', 1)
    # Determine the content type based on the file extension
    file_extension = filename.split('.')[-1].lower()
    content_type = "video/mp4" if file_extension == "mp4" else "video/webm"
    # Pass both filename and content_type to the player.html template
    return render_template('player.html', filename=filename, content_type=content_type)

#############################################################
######################### Admin Page ########################
#############################################################

def get_directory_structure(startpath, excluded_dirs=None):
    """
    Recursively fetches the directory structure, excluding specified directories.
    :param startpath: The base directory path to start the search from.
    :param excluded_dirs: A list of directory names to exclude from the structure.
    :return: A nested dictionary representing the folder structure of startpath.
    """
    if excluded_dirs is None:
        excluded_dirs = ['bin', 'boot', 'dev', 'etc', 'home', 'lib', 'lib64', 'media', 'opt', 'proc', 'root', 'run', 'sbin', 'srv', 'sys', 'tmp', 'usr', 'var']
    tree = {}
    for root, dirs, files in os.walk(startpath, topdown=True):
        # Exclude specified directories
        dirs[:] = [d for d in dirs if d not in excluded_dirs]
        # Trim the part of the path that precedes the base directory
        trimmed_path = root[len(startpath):].lstrip(os.path.sep)
        subtree = tree
        # Recursively navigate down the dictionary and add new dictionaries for subdirectories
        for part in trimmed_path.split(os.path.sep):
            subtree = subtree.setdefault(part, {})
        subtree["_files"] = files  # Optionally store files in the "_files" key, or ignore if not needed
    return tree

def update_document_paths(newpathprefix, dry_run=True):
# Define the old path prefix that will be replaced
    oldpathprefix = docker_mainpath
    # Fetch all documents that need their paths updated
    documents = global_pool.find({"download_path": {"$regex": oldpathprefix}})
    # Counter for how many paths would be updated (for dry run reporting)
    update_count = 0
    for doc in documents:
        old_path = doc["download_path"] # Extract the current download_path
        # Generate the new download_path by replacing the old prefix with the new one
        new_path = old_path.replace(oldpathprefix, newpathprefix)
        if dry_run: # If dry run, just print what would be done
            printline(f"Dry run: Would update from {old_path} to {new_path}")
        else: # If not a dry run, perform the update in the database
            # collection.update_one({"_id": doc["_id"]}, {"$set": {"download_path": new_path}})
            printline(f"Updated {doc['_id']} path to {new_path}")
        update_count += 1
    if dry_run:
        printline(f"Dry run complete: {update_count} paths would be updated.")
    else:
        printline(f"Update complete: {update_count} paths updated.")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/restore_all', methods=['GET', 'POST'])
def restore_all():
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            zip_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(zip_path)
            # Extract the zip file
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(app.config['UPLOAD_FOLDER'])
            # Restore the data from the extracted files
            for collection_name in os.listdir(app.config['UPLOAD_FOLDER']):
                collection_path = os.path.join(app.config['UPLOAD_FOLDER'], collection_name)
                if os.path.isfile(collection_path) and collection_name.endswith('.json'):
                    with open(collection_path, 'r') as file:
                        data = json.load(file)
                        collection_name = collection_name.rsplit('.', 1)[0]  # Remove .json extension
                        collection = db[collection_name]
                        collection.delete_many({})  # Clear existing data
                        collection.insert_many(data)
            flash('Restore completed successfully')
            return redirect(url_for('admin_page'))

@app.route('/backup_all')
def backup_all():
    with tempfile.TemporaryDirectory() as tmp_backup_dir:
        for collection_name in db.list_collection_names():
            collection = db[collection_name]
            if collection_name == 'downloads':
                # For the downloads collection, keep the '_id' field
                data = list(collection.find({}))
            else:
                # For other collections, exclude the '_id' field
                data = list(collection.find({}, {'_id': False}))
            for item in data:
                # Convert ObjectId to string for the downloads collection
                if collection_name == 'downloads':
                    item['_id'] = str(item['_id'])
            backup_path = os.path.join(tmp_backup_dir, f'{collection_name}.json')
            with open(backup_path, 'w') as file:
                json.dump(data, file, indent=4)
        final_backup_dir = 'backups'
        if not os.path.exists(final_backup_dir):
            os.makedirs(final_backup_dir)
        zip_filename = 'mongodb_backup.zip'
        zip_path = os.path.join(final_backup_dir, zip_filename)
        shutil.make_archive(base_name=zip_path, format='zip', root_dir=tmp_backup_dir)
    return send_file(f'{zip_path}.zip', as_attachment=True, download_name=zip_filename)

def get_volume_usages(volumes):
    volume_usages = []
    for volume in volumes:
        volume_path = volume if volume.startswith("/") else f"/{volume}"
        try:
            total, used, free = shutil.disk_usage(volume_path)
            volume_usages.append({
                'path': volume_path,
                'free_gb': round(free / (1024**3), 2),  # Convert bytes to GB
                'total_gb': round(total / (1024**3), 2)  # Convert bytes to GB
            })
        except Exception as e:
            printline(f"Error retrieving disk usage for {volume_path}: {e}")
    return volume_usages

def get_next_volume():
    # Fetch the current settings
    settings_doc = admin_settings.find_one()
    volumes = settings_doc.get("volumes", [])
    current_strategy = admin_settings_doc.get("strategy", "round_robin")
    last_used_index = admin_settings_doc.get("lastUsedVolumeIndex", 0)
    # Ensure the strategy is round_robin before proceeding
    if current_strategy != "round_robin" or not volumes:
        # Handle the case where the strategy is not round_robin or no volumes are defined
        raise ValueError("Strategy is not round_robin or no volumes defined")
    # Calculate the next index based on round_robin strategy
    next_index = (last_used_index + 1) % len(volumes)
    # Update the last used volume index in MongoDB
    printline(f'Updating admin settings with {next_index} to "lastUsedVolumeIndex"')
    # admin_settings.update_one({}, {'$set': {'lastUsedVolumeIndex': next_index}})
    # Return the next volume path
    return volumes[next_index]

def get_last_used_volume_index():
    settings_document = admin_settings.find_one({}, {'lastUsedVolumeIndex': 1, '_id': 0})
    if settings_document and 'lastUsedVolumeIndex' in settings_document:
        return settings_document['lastUsedVolumeIndex']
    else:
        return -1

def set_last_used_volume_index(index):
    printline(f'Updating admin settings with {index} to "lastUsedVolumeIndex"')
    admin_settings.update_one({}, {'$set': {'lastUsedVolumeIndex': index}}, upsert=True)

def find_best_matching_file(directory, base_name):
    # Step 1: Construct a pattern to find files that start with the base_name, regardless of their extension.
    pattern = f"{base_name}"
    # Step 2: Use glob to find files matching the pattern.
    files = glob.glob(pattern)
    printline(f"Pattern {pattern}, Files: {files}")
    # Step 3: Ensure 'file_bases' is defined by extracting the base part (without extension) of each file found.
    file_bases = [os.path.splitext(os.path.basename(f))[0] for f in files]
    # Step 4: Use 'file_bases' in 'difflib.get_close_matches' to find the best match.
    best_matches = difflib.get_close_matches(base_name, file_bases, n=1, cutoff=0.8)
    # Step 5: If a match is found, return the corresponding full path from the 'files' list.
    if best_matches:
        best_match_base = best_matches[0]
        for f in files:
            if os.path.splitext(os.path.basename(f))[0] == best_match_base:
                return f # Return the full path of the matched file
    return None # If no match is found, return None

def prepare_files_to_move():
    files_to_move = []
    cursor = global_pool.find({})
    for doc in cursor:
        video_path = doc['download_path']
        printline(f"video_path: {video_path}")
        base_filename = os.path.basename(video_path)
        printline(f"base_filename: {base_filename}")
        base_name, _ = os.path.splitext(base_filename)
        printline(f"base_name: {base_name}")
        thumbnail_directory = video_path.replace('/videos/', '/thumbnails/').replace(base_filename, f"{base_name}")
        printline(f"thumbnail_directory: {thumbnail_directory}")
        thumbnail_path = find_best_matching_file(thumbnail_directory, base_name)
        json_path = video_path.replace('/videos/', '/json/').replace(base_filename, f"{base_name}.json")
        if thumbnail_path:
            files_to_move.append({
                'video': video_path,
                'thumbnail': thumbnail_path,
                'json': json_path
            })
    return files_to_move
    
def move_data(files_to_move):
    volumes = get_selected_volumes()
    last_used_index = int(get_last_used_volume_index())
    for file_group in files_to_move:
        last_used_index = (last_used_index + 1) % len(volumes)
        new_volume_base_path = os.path.join('/mnt/', volumes[last_used_index], 'docker/anomaly-ytdlp/data')
        for file_type, file_path in file_group.items():
            target_subdir = {'video': 'public/videos', 'thumbnail': 'public/thumbnails', 'json': 'public/json'}[file_type]
            new_file_path = os.path.join(new_volume_base_path, target_subdir, os.path.basename(file_path))
            printline(f'Moving {os.path.basename(file_path)} to {new_file_path}')
            # shutil.move(file_path, new_file_path)
    set_last_used_volume_index(last_used_index)

@app.route("/test-move-data", methods=["POST"])
def test_move_data():
    printline("Received test move data request")
    files_to_move = prepare_files_to_move()
    move_data(files_to_move)
    return jsonify({'message': 'Move data test initiated'})

@app.route("/save-settings", methods=["POST"])
def save_settings():
    settings_data = request.json
    # Update the settings in the settings collection
    admin_settings.update_one(
        {},
        {'$set': settings_data}, 
        upsert=True
    )
    return jsonify({"message": "Settings updated successfully"})

@app.route('/admin69420847', methods=['GET', 'POST'])
def admin_page():
    directory_structure = get_directory_structure("/")
    # Load statistics.json data
    with open('statistics.json', 'r') as file:
        statistics = json.load(file)
    set_default_settings() # Ensure default settings are set
    selected_volumes = get_selected_volumes()
    volume_usages = get_volume_usages(selected_volumes)
    if request.method == 'POST':
        newpathprefix = request.form.get('newPath')
        dry_run = 'dryRun' in request.form
        update_document_paths(newpathprefix, dry_run)
        updated_settings = admin_settings.find_one({})
        return render_template('admin.html', volume_usages=volume_usages, selected_volumes=selected_volumes, statistics=statistics, settings=updated_settings, update_success=True, dry_run=dry_run, newpathprefix=newpathprefix, bdir=bdir, docker_port_ytdl=docker_port_ytdl, docker_port_ytdldb=docker_port_ytdldb, docker_port_ytdlredis=docker_port_ytdlredis, docker_port_ytdlmeili=docker_port_ytdlmeili, directory_structure=directory_structure)
    # Variables like bdir, docker_port_ytdl, etc., should be defined or fetched before passing to the template
    updated_settings = admin_settings.find_one({})
    return render_template('admin.html', volume_usages=volume_usages, selected_volumes=selected_volumes, statistics=statistics, settings=updated_settings, bdir=bdir, docker_port_ytdl=docker_port_ytdl, docker_port_ytdldb=docker_port_ytdldb, docker_port_ytdlredis=docker_port_ytdlredis, docker_port_ytdlmeili=docker_port_ytdlmeili, directory_structure=directory_structure)

#############################################################
#################### Login & Registration ###################
#############################################################

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

def sanitize_filename(filename, max_length=180):
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
    files = glob.glob(f"{intpath}/videos/{output}.*")
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
        img.verify()  # verify that it is, in fact, an image
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

# Delivers /videos for the pages
@app.route('/videos')
def videos():
    p = int(request.args.get('p', 1))
    ipp = int(request.args.get('ipp', 20))
    # Configurable number of page links to display or default to 10
    page_display_limit = int(pagedisplaylimit) if pagedisplaylimit is not None else 10
    total_videos = collection.count_documents({})
    total_pages = (total_videos + ipp - 1) // ipp
    # Redirect to page 1 if the page number is less than 1
    if p < 1:
        return redirect(url_for('index', p=1, ipp=ipp))
    # Redirect to the last page if the page number is greater than total_pages
    if p > total_pages:
        return redirect(url_for('index', p=total_pages, ipp=ipp))
    offset = (p - 1) * ipp
    videos = collection.find().skip(offset).limit(ipp)
    return render_template('videos.html', videos=videos, p=p, ipp=ipp, total_videos=total_videos, total_pages=total_pages, page_display_limit=page_display_limit)

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

def clean_and_load_json(filename):
    error_patterns = [
        r"WARNING: \[generic\] Falling back on generic information extractor",
        r"WARNING: \[youtube\] HTTP Error 400: Bad Request\. Retrying \(\d+/\d+\)",
        r"WARNING: \[youtube\] YouTube said: ERROR - Precondition check failed\.",
        r"WARNING: \[youtube\] Unable to download API page: HTTP Error 400: Bad Request",
        r"WARNING: \[youtube\] Unable to download webpage: HTTPSConnectionPool\(host='www\.youtube\.com', port=443\): Read timed out\.",
        r"ERROR: ",
        r"\[download\] Got error: ",
        r"ERROR: fragment \d+ not found, unable to continue",
        r"WARNING: \[youtube\] Skipping player responses from android clients",
        r"WARNING: \[TikTok\] Expecting value in '': line 1 column 1",
        r"WARNING: \[TikTok\] \d+: Failed to parse JSON",
        r"ERROR: \[generic\] '298\+140' is not a valid URL."
    ]
    def should_include_line(line):
        for pattern in error_patterns:
            if re.search(pattern, line):
                return False
        return True
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            content = file.read()
            # Filter out lines based on error patterns
            filtered_lines = [line for line in content.splitlines() if should_include_line(line)]
            content = '\n'.join(filtered_lines)
            # Remove common unwanted outputs that may appear before the JSON
            start_index = content.find('{')
            end_index = content.rfind('}') + 1
            if start_index == -1 or end_index == -1:
                raise ValueError("Valid JSON object not found in the file.")
            # Extract the actual JSON part
            json_str = content[start_index:end_index]
            data = json.loads(json_str)
            return data
    except json.JSONDecodeError as e:
        print(f"JSON decode error in file {filename}: {e}")
        return None
    except Exception as e:
        print(f"An error occurred while processing the file {filename}: {e}")
        return None

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
            '--yes-playlist',
            '--windows-filenames', # Force filenames to be Windows-compatible
            '--trim-filenames 50', # Limit the filename length (excluding extension) to the specified number of characters
            url
        ]
        info_process = subprocess.Popen(info_command, stdout=subprocess.PIPE, text=True)
        info_result, err = info_process.communicate()

    try:
        if not info_result:
            logging.error(f"yt-dlp returned an empty result for URL {url}. stderr: {err}")
            return None, f"Download failed for URL {url}. Error: Empty result received from yt-dlp"
        info_list = [json.loads(line) for line in info_result.splitlines() if line.strip()]
        if not info_list:
            logging.error(f"No valid video info found for URL {url}")
            return None, f"Download failed for URL {url}. Error: No valid video information found"
        info = json.loads(info_result)
        logging.info('Step 03: Set info variable in Step 3')
    except json.JSONDecodeError as e:
        logging.error(f'Step 03: Failed to download:` {url}')
        logging.error(f"Step 03: yt-dlp output is invalid JSON: {info_result}")
        logging.error(f"Step 03: JSON decoding error: {str(e)}")
        return None, f"Download failed for URL {url}. Error: Invalid JSON output from yt-dlp"
    except ValueError as e:
        logging.error(f"Step 03: {str(e)}")
        return None, f"Download failed for URL {url}. Error: {str(e)}"
    except Exception as e:
        logging.error(f"Step 03: Unexpected error: {str(e)}")
        return None, f"Download failed for URL {url}. Error: {str(e)}"

    for index, info in enumerate(info_list):
        #############################################################
        # Step 04 ###################################################
        #############################################################
        logging.info(f'Step 04: Sanitize title and output as variable for video {index + 1}')
        # Use the video title as the output name if no output name was provided
        if isinstance(info, dict) and 'title' in info:
            display_title = info['title']
            logging.info('Step 04: P1')
        else:
            display_title = f"Title not found for video {index + 1}"
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
            output = sanitize_filename(output_base) + f"_{index + 1}_" + info['id'] # custom output names from form
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
            directory = os.path.join(docker_mainpath, 'data/public')
            g.directory = directory
            logging.info('Step 05: Set directory variable to data/public')

        #############################################################
        # Step 06 ###################################################
        #############################################################
        logging.info('Step 07: Download video with yt-dlp')
        # Run yt-dlp to download the video (1/3 files)
        # Set Command 1 for Progress/DL of video
        intpath = '/app/data/public'
        progresscmd = [
            yt_dlp_path,
            '-f', 'bestvideo+bestaudio/best',
            '-o', f'{intpath}/videos/{output}.%(ext)s',
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
        printline(f"Step 07: ytdlp output path: {intpath}/videos/{output}.EXT")
        printline(f"Step 07: ytdlp output variable: {output}")
        jsoncmd = [
            yt_dlp_path,
            '-f', 'bestvideo+bestaudio/best',
            '-o', f'{intpath}/videos/{output}.%(ext)s',
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
                with open(f"{intpath}/json/{output}_progress.json", 'w') as progress_file:  # Open the JSON file and the progress file # Open the JSON file
                    while True:
                        poutput = progressres.stdout.readline()
                        # progressres.stdout.flush()
                        if poutput == '' and progressres.poll() is not None:
                            break
                        if poutput:
                            if "Skipping player responses from android clients" in poutput:
                                continue # skip this iteration and don't process this line
                            downloaded_file_line = [line for line in poutput.split('\n') if '[download] Destination:' in line]
                            if downloaded_file_line:
                                downloaded_file = downloaded_file_line[0].split()[-1]
                                potential_extension = os.path.splitext(downloaded_file)[1].lstrip('.')
                                if potential_extension in VIDEO_EXTENSIONS:
                                    actual_extension = potential_extension
                                    video_path = f'{intpath}/videos/{output}.{actual_extension}'
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
                with open(f'{intpath}/json/{output}.json', 'w') as json_file: # Open the JSON file
                    while True:
                        poutput = jsonres.stdout.readline()
                        # progressres.stdout.flush()
                        if poutput == '' and jsonres.poll() is not None:
                            break
                        if poutput:
                            # Directly write to the file without filtering as we will use the cleaning function later
                            json_file.write(poutput)
                try:
                    # Clean the JSON file using the provided function
                    data = clean_and_load_json(f'{intpath}/json/{output}.json')
                    if data is None:
                        logging.info(f"Failed to load clean JSON data from {intpath}/json/{output}.json")
                        return None, f"Download failed for URL {url}. Error: Cleaned JSON data is invalid"
                    # Save cleaned JSON to the same path
                    with open(f'{intpath}/json/{output}.json', 'w') as json_file:
                        json.dump(data, json_file, indent=4)
                        logging.info(f'Step 07: Writing output to JSON - 2/3 files (json)')
                    logging.info(f"Filtered and cleaned JSON saved to {intpath}/json/{output}.json")
                    printline(f"json_output_filename: {intpath}/json/{output}.json")
                    logging.info(f"json_output_filename: {intpath}/json/{output}.json")
                except Exception as e:
                    logging.error(f"An error occurred while processing the JSON file {intpath}/json/{output}.json: {e}")
                    printline(f"S07E: {jsonres.stderr}")
                    return None, f"Download failed for URL {url}. Error: Processing cleaned JSON failed"
            except subprocess.CalledProcessError as e:
                logging.error(f"Step 07: Download failed with error: {e}")
                download_process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                jsonres, err = download_process.communicate()
                if download_process.returncode != 0:
                    logging.info(f"Step 07: From subprocess.Popen: {err}")
                return f"Step 07: Download failed with error: {e}", 500
        printline(f"S07E: {jsonres.stderr}")
        json_output_filename = f'{intpath}/json/{output}.json'
        printline(f"json_output_filename: {json_output_filename}")
        logging.info(f"json_output_filename: {json_output_filename}")

        #############################################################
        # Step 08 ###################################################
        #############################################################
        logging.info('Step 08: 1/3 Increasing download number in update_statistics')
        # Increase download number 
        download_number = update_statistics(url)[0]

        #############################################################
        # Step 09 ###################################################
        #############################################################
        logging.info('Step 09: 3/3 Download thumbnail to file')
        # Run yt-dlp to download the thumbnail (3/3 files)
        tmbs = [
            yt_dlp_path,
            '--skip-download',
            '--write-thumbnail',
            '-o', f'{intpath}/thumbnails/{output}',
            '--cookies', 'cookies.txt',
            url
        ]
        with lock:
            download_process = subprocess.Popen(tmbs, stdout=subprocess.PIPE, text=True)
            result, err = download_process.communicate()
            logging.info('Step 09: Downloading thumbnail')
        time.sleep(3)
        logging.info(f'Step 09: output for tmb13 P1: {output}')
        # List all files that start with the output name
        files = glob.glob(f'{intpath}/thumbnails/{output}*')
        # If there are any files that match
        if files:
            # Get the first file
            file = files[0]
            logging.info(f'Step 09: list of files: {file}')
            extension = get_image_format_using_pil(file)
            logging.info(f'Step 09: extension: {extension}')
        else:
            extension = None
            logging.info(f'Step 09: error: output for tmb13 P2: {output}')
        thumbnail_path = f'{file}'
        if is_image_corrupted(thumbnail_path):
            logging.info('Step 09: Thumbnail is corrupted, extracting a new one from the video')
            time.sleep(5)
            # vextension = get_video_extension(directory, output)
            logging.info(f'Step 09: video_path: {video_path}')
            logging.info(f'Step 09: output: {output}')
            logging.info(f'Step 09: extension: {extension}')
            extract_thumbnail(video_path, thumbnail_path)

        #############################################################
        # Step 10 ###################################################
        #############################################################
            # Load the JSON data
        try:
            with open(json_output_filename, 'r') as f:
                logging.info('Step 10: Setting data variable')
                data = json.load(f)
        except json.JSONDecodeError:
            logging.error(f"Step 10: Failed to load JSON data from {json_output_filename}. File content might be empty or not properly formatted.")
            data = None

        #############################################################
        # Step 11 ###################################################
        #############################################################

        try:
            tfilesize = get_file_size(data["_filename"])
            logging.info('Step 11: trying to grab filesize from file')
        except:
            tfilesize = 0

        #############################################################
        # Step 12 ###################################################
        #############################################################
        # Set the default filename to grab the aspect_ratio/resolution
        fnprobe = data['_filename']
        # Set filename first as this is most important
        # This does NOT set {bdir} as that is not a valid location under /app
        filename = data["_filename"]
        logging.info(f'Step 12: {get_video_duration(fnprobe)}')
        video_info = {
            'index': download_number,
            'id': data.get('id', "unknown"),
            'title': display_title, # previously set
            'date_posted': data.get('upload_date', "unknown"),
            'archive_date': datetime.now(), # BSON datetime object, date-based queries
            'user': data.get("uploader", "unknown"),
            'video_url': data.get('webpage_url', "unknown"),
            'length': format_duration(get_video_duration(fnprobe)),
            'filename': f'{filename}',
            'thumbnail': f'{directory}/thumbnails/{sanitize_filename(output)}.{extension}',
            'tmbfp': f'{file.replace("/app/", "")}', # set from image extraction way above
            'json_file': f'{directory}/json/{sanitize_filename(output)}.json',
            'file_size_bytes': tfilesize,
            'file_size_readable': "unknown",
            'resolution': "unknown",
            'aspect_ratio': "unknown"
        }
        logging.info('Step 12: Displaying video_info[] data')
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
        logging.info('vInfo: tmbfp: "%s"', video_info['tmbfp'].replace('/app/', '', 1))

        #############################################################
        # Step 12 ###################################################
        #############################################################
        logging.info('Step 14: Grab filename from JSON, get resolution and aspect ratio with ffprobe')
        # Get the filename of the downloaded file from the JSON output
        # downloaded_video_filename = video_info['filename']
        downloaded_video_filename = fnprobe
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
        printline(f"Aspect ratio: {video_info['aspect_ratio']}")
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
        

        #############################################################
        # Step 15 ###################################################
        #############################################################
        # Write the extracted information to a new file
        extracted_info_filename = f'{intpath}/json/{output}_info.json'
        logging.info('Step 17: Setting extracted_info_filename variable to output_info.json')
        # Ensure the directory exists
        os.makedirs(os.path.dirname(extracted_info_filename), exist_ok=True)
        try:
            printline(f"Writing to file {extracted_info_filename}")  # Debugging print statement
            with open(extracted_info_filename, 'w') as f:
                json.dump(video_info, f, indent=4, cls=DateTimeEncoder)
                logging.info('Step 17: Dumping video_info[] json to file ')
            printline(f"Successfully wrote to file {extracted_info_filename}")  # Debugging print statement
            logging.info('Step 17: Wrote to extracted_info_filename new data')
            os.remove(json_output_filename) # disable this for debug for original json data
            logging.info('Step 17: Removing old JSON data')

        #############################################################
        # Step 16 ###################################################
        #############################################################
        except Exception as e:
            printline(f"Error writing to file {extracted_info_filename}: {e}")
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
        printline('Starting download for URL:', url)
        info, error = download(url, args, cutout, output_base)  # Get the info and error from the download function
        if error:
            errors.append(error)
        printline('Download finished for URL:', url)
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

# used for embed information, video.html
@app.route('/data/<path:filename>')
def serve_data(filename):
    printline(f"serve_data route: {filename}")
    logging.info(f"serve_data route before: {filename}")
    filename = filename.replace('data/', '', 1)
    logging.info(f"serve_data route after: {filename}")
    #printline(f"serve_data route after edit: {filename}")
    return send_from_directory('data', filename)

@app.route('/', endpoint='index')
def home():
    logging.info('Home page loaded')
    # Get the current page number and number of items per page from the query parameters
    p = request.args.get('p', default=1, type=int)
    ipp = request.args.get('ipp', default=20, type=int)
    # Configurable number of page links to display or default to 10
    page_display_limit = int(pagedisplaylimit) if pagedisplaylimit is not None else 10
    # Calculate the total number of videos
    total_videos = collection.count_documents({})
    logger.info(f"Total videos in the collection: {total_videos}") # this is just debug material, will be removed
    # Calculate the total number of pages
    total_pages = (total_videos + ipp - 1) // ipp
    # Handle cases with no items in the database
    if total_videos == 0:
        total_pages = 1
    # Redirect to page 1 if the page number is less than 1
    if p < 1:
        logger.info(f"Page number {p} is less than 1, redirecting to page 1")
        return redirect(url_for('index', p=1, ipp=ipp))
    # Redirect to the last page if the page number is greater than total_pages
    if p > total_pages:
        logger.info(f"Page number {p} is greater than total pages {total_pages}, redirecting to the last page")
        return redirect(url_for('index', p=total_pages, ipp=ipp))
    offset = (p - 1) * ipp
    # Query MongoDB to get the video data
    videos = list(collection.find({}).skip(offset).limit(ipp))
    logger.info(f"Retrieved {len(videos)} videos for page {p}")
    # Modify the tmbfp attribute by removing "data/" prefix and replace special characters
    for video in videos:
        video['tmbfp'] = video['tmbfp'].replace('data/', '', 1) # removes the single data/ path so it works for the thumbnail, do not remove
        video['tmbfp'] = video['tmbfp'].replace('(', '%28').replace(')', '%29').replace('\\', '%5C') # replaces parentheses for url encoding
        video['tmbfp'] = unquote(video['tmbfp']) # may be possible to remove at this point
    # Pass the video data to the template
    directory = getattr(g, 'directory', None)
    search_api_key = get_meilisearch_public_key()
    return render_template('index.html', videos=videos, p=p, total_pages=total_pages, ipp=ipp, page_display_limit=page_display_limit, bdir=bdir, directory=directory, meilisearch_url=meilisearch_url, search_api_key=search_api_key)

if __name__ == '__main__':
    logging.info('Main started')
    # Start the monitoring thread
    monitoring_thread = Thread(target=monitor_system, daemon=True)
    monitoring_thread.start()
    # Start the background MeiliSearch update thread
    meilibgprocess_thread = threading.Thread(target=meilisearch_bg_process, daemon=True)
    meilibgprocess_thread.start()
    app.debug = False
    app.run(host='0.0.0.0', threaded=True)
