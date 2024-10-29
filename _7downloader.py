from _0sources import *
from _1app import *
from _2meilisearch import *
from _4hlsseg import *
from _5admin import *
from _6loginandreg import *

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
