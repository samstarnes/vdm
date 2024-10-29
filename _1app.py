from _0sources import *
from _2meilisearch import *

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
