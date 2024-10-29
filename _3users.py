#############################################################
########################### Users ###########################
#############################################################

from _0sources import *
from _1app import *
from _4hlsseg import *
from _5admin import *
from _6loginandreg import *

@login_manager.user_loader
def load_user(user_id):
    # Fetch the user from the database using the user_id
    user_record = fetch_user_from_database(user_id)  # You need to implement this function
    # Create a User object using the username and password from the user_record
    if user_record is None:
        return None
    user = User(user_record['username'], user_record['password'])
    return user