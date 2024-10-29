#############################################################
############## HLS Segments / Queue and convert #############
#############################################################

from _0sources import *
from _1app import *

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
