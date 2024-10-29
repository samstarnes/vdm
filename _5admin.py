#############################################################
######################### Admin Page ########################
#############################################################

from _0sources import *
from _1app import *
from _3users import *
from _4hlsseg import *
from _6loginandreg import *

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
