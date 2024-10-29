#############################################################
#################### Login & Registration ###################
#############################################################

from _0sources import *
from _1app import *
from _2meilisearch import *
from _3users import *
from _4hlsseg import *
from _5admin import *
from _6loginandreg import *

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