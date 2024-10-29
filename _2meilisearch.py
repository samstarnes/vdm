#############################################################
######################## MeiliSearch ########################
#############################################################

from _0sources import *
from _1app import *

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