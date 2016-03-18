import os
from flask import Flask, render_template, request, redirect, url_for,\
    flash, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Restaurant, Base, MenuItem, User
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests
from werkzeug import secure_filename

app = Flask(__name__)

# Reads the client id for the Google API
CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Restaurant Menu Application"

# Specifies the location for uploaded files, and the allowed file types for
# uploads
UPLOAD_FOLDER = 'static/images/'
ALLOWED_EXTENSIONS = set(['PNG', 'png', 'JPG', 'jpg', 'JPEG', 'jpeg', 'GIF',
                          'gif'])
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Connect to Database and create database session
engine = create_engine('sqlite:///restaurantmenu.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()


# Create anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state)


# Log in user through facebook
@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
    print "access token received %s " % access_token

    # Reads the app id and secret from the Facebook JSON file and passes them
    # as parameters to the Facebook OAuth URL
    app_id = json.loads(open('fb_client_secrets.json', 'r').read())[
        'web']['app_id']
    app_secret = json.loads(
        open('fb_client_secrets.json', 'r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type=' \
          'fb_exchange_token&client_id=%s&client_secret=%s' \
          '&fb_exchange_token=%s' % (app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    # Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v2.4/me"
    # strip expire tag from access token
    token = result.split("&")[0]

    url = 'https://graph.facebook.com/v2.4/me?%s&fields=name,id,email' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    # print "url sent for API access:%s"% url
    # print "API JSON result: %s" % result
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    # The token must be stored in the login_session in order to properly
    # logout, let's strip out the information before the equals sign in
    # our token
    stored_token = token.split("=")[1]
    login_session['access_token'] = stored_token

    # Get user picture
    url = 'https://graph.facebook.com/v2.4/me/picture?%s&redirect=0&' \
          'height=200&width=200' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    login_session['picture'] = data["data"]["url"]

    # see if user exists
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += '" style = "width: 300px; height: 300px;border-radius: 150px;' \
              '-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '

    flash("Now logged in as %s" % login_session['username'])
    return output


# Log out user through facebook
@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s'\
          % (facebook_id, access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    return "You have been logged out"


# Log in user through Goggle+
@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already '
                                            'connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    # ADD PROVIDER TO LOGIN SESSION
    login_session['provider'] = 'google'

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(data["email"])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<head><title>Logging In</title>' \
              '<link rel="stylesheet" href="http://maxcdn.bootstrapcdn.com/' \
              'bootstrap/3.3.5/css/bootstrap.min.css"><script src="https://' \
              'ajax.googleapis.com/ajax/libs/jquery/1.11.3/jquery.min.js">' \
              '</script><script src="http://maxcdn.bootstrapcdn.com/' \
              'bootstrap/3.3.5/js/bootstrap.min.js"></script><link rel=' \
              '"stylesheet" type="text/css" href="\static\styles.css"></head>'
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += '" style = "width: 300px; height: 300px;border-radius: 150px;' \
              '-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("Logged in as %s" % login_session['username'])
    print "done!"
    return output

    # DISCONNECT - Revoke a current user's token and reset their login_session


# Log out user through Google+
@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user.
    credentials = login_session.get('credentials')
    if credentials is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = credentials
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' %access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] != '200':
        # For whatever reason, the given token was invalid.
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# general disconnect function that routes to either gdisconnect or
# fbdisconnect and takes care of extra attributes of login session
@app.route('/disconnect')
def disconnect():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['gplus_id']
            del login_session['credentials']
        if login_session['provider'] == 'facebook':
            fbdisconnect()
            del login_session['facebook_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        flash("You have successfully been logged out.")
        return redirect(url_for('allRestaurants'))
    else:
        flash("You were not logged in")
        return redirect(url_for('allRestaurants'))


# Home page of app. If the user is not logged in they are routed to
# the public version of the site.
@app.route('/')
@app.route('/restaurants/')
def allRestaurants():
    restaurants = session.query(Restaurant).all()
    if 'username' not in login_session:
        return render_template('publicrestaurants.html',
                               restaurants=restaurants)
    else:
        user_id = login_session['user_id']
        return render_template('restaurants.html', restaurants=restaurants,
                               user_id=user_id, session=login_session)


# The create-a-restaurant page. If the user is not logged in,
# they are routed to the log in screen.
@app.route('/restaurant/new/', methods=['GET', 'POST'])
def newRestaurant():
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        restaurant = Restaurant(name=request.form['name'],
                                user_id=login_session['user_id'])
        session.add(restaurant)
        session.commit()
        flash("New Restaurant Created")
        return redirect(url_for('allRestaurants'))
    else:
        return render_template('newrestaurant.html')


# The edit restaurant page. Again requires the user to be logged in.
@app.route('/restaurant/<int:restaurant_id>/edit', methods=['GET', 'POST'])
def editRestaurant(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    else:
        if login_session['user_id'] != restaurant.user_id:
            return "<script>(function() {alert('You are not authorized to" \
                   " edit this restaurant.');})();</script>"
    if request.method == 'POST':
        restaurant.name = request.form['name']
        session.add(restaurant)
        session.commit()
        flash("Restaurant Successfully Edited")
        return redirect(url_for('allRestaurants'))
    else:
        return render_template('editrestaurant.html', restaurant=restaurant,
                               restaurant_id=restaurant_id)


# The delete restaurant page. Again requires the user to be logged in.
@app.route('/restaurant/<int:restaurant_id>/delete', methods=['GET', 'POST'])
def deleteRestaurant(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    else:
        if login_session['user_id'] != restaurant.user_id:
            return "<script>(function() {alert('You are not authorized to " \
                   "delete this restaurant.');})();</script>"
    if request.method == 'POST':
        session.delete(restaurant)
        session.commit()
        flash("Restaurant Successfully Deleted")
        return redirect(url_for('allRestaurants'))
    else:
        return render_template('deleterestaurant.html', restaurant=restaurant,
                               restaurant_id=restaurant_id)

# Menu page. If the user is not logged in or is not the creator
# of the restaurant, they see the public version of the page.
@app.route('/restaurant/<int:restaurant_id>/')
def restaurantMenu(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    items = session.query(MenuItem).filter_by(restaurant_id=restaurant.id)
    courses = ['Appetizer', 'Entree', 'Dessert', 'Beverage']
    # Creates a list of the courses offered by this restaurant
    courses_organized = []
    for course in courses:
        for i in items:
            if course == i.course:
                courses_organized.append(course)
                break
    if 'username' not in login_session:
        return render_template('publicmenu.html', restaurant=restaurant,
                               items=items, courses=courses_organized,
                               session=login_session)
    else:
        if restaurant.user_id == login_session['user_id']:
            return render_template('menu.html', restaurant=restaurant,
                                   items=items, courses=courses_organized,
                                   session=login_session)
        else:
            return render_template('publicmenu.html', restaurant=restaurant,
                                   items=items, courses=courses_organized,
                                   session=login_session)


# The create menu item page. Login required. Allows for the upload
# of images.
@app.route('/restaurant/<int:restaurant_id>/new/', methods=['GET', 'POST'])
def newMenuItem(restaurant_id):
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        image_file = request.files['image']
        filename = ''
        # Checks if the uploaded file is one of the allowed types (an image
        # or gif) and if it passes, saves it to the upload folder.
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            # saves the file if the file does not already
            # exist in the upload folder
            if not os.path.isfile(file_path):
                image_file.save(file_path)
        item = MenuItem(name=request.form['name'],
                        description=request.form['description'],
                        price=request.form['price'],
                        course=request.form['course'], 
                        image=filename,
                        restaurant_id=restaurant_id,
                        user_id=login_session['user_id'])
        session.add(item)
        session.commit()
        flash("New Menu Item Created")
        return redirect(url_for('restaurantMenu',
                                restaurant_id=restaurant_id))
    else:
        return render_template('newmenuitem.html',
                               restaurant_id=restaurant_id)


# Edit menu item page. Login required. User can add, 
# remove, or change the image for the menu item.
@app.route('/restaurant/<int:restaurant_id>/<int:menu_id>/edit/',
           methods=['GET', 'POST'])
def editMenuItem(restaurant_id, menu_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    else:
        if login_session['user_id'] != restaurant.user_id:
            return "<script>(function() {alert('You are not authorized to" \
                   " edit this menu item.');})();</script>"
    all_items = session.query(MenuItem).all()
    item = session.query(MenuItem).filter_by(id=menu_id).one()
    if request.method == 'POST':
        image_file = request.files['image']
        image_delete = request.form['image_delete']
        filename = item.image
        # Checks if the image is used by other menu items. For each item with
        # the image name in its table, the count goes up by one.
        count = 0
        for i in all_items:
            if i.image == filename:
                count += 1
                if count == 2:
                    break
        if image_file and allowed_file(image_file.filename):
            # if the file is not used by other menu items (count<2) and 
            # the name of the uploaded file is not the same as the name 
            # of the item's current image and there is a current image,
            # delete it.
            if count < 2 and not image_file == filename and os.path.isfile\
                        (os.path.join(app.config['UPLOAD_FOLDER'], filename)):
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            # The filename is then changed to the name of the
            # upload and appended to the path to the upload folder.
            filename = secure_filename(image_file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            # if a file with the same name does not exist in the upload
            # folder, save the uploaded file
            if not os.path.isfile(file_path):
                image_file.save(file_path)
        # If the count is two or greater, the file will not be deleted.
        # Instead, the filename in the menu item table will be changed
        # to empty string.
        if image_delete:
            if count < 2 and os.path.isfile(os.path.join
                                    (app.config['UPLOAD_FOLDER'], filename)):
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            filename = ''
        item.name = request.form['name']
        item.description = request.form['description']
        item.price = request.form['price']
        item.course = request.form['course']
        item.image = filename
        session.add(item)
        session.commit()
        flash("Menu Item Successfully Edited")
        return redirect(url_for('restaurantMenu',
                                restaurant_id=restaurant_id))
    else:
        return render_template('editmenuitem.html', item=item,
                               restaurant_id=restaurant_id, menu_id=menu_id)


# Delete menu item page. Login required.
@app.route('/restaurant/<int:restaurant_id>/<int:menu_id>/delete/',
           methods=['GET', 'POST'])
def deleteMenuItem(restaurant_id, menu_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    else:
        if login_session['user_id'] != restaurant.user_id:
            return "<script>(function() {alert('You are not authorized" \
                   " to delete this menu item.');})();</script>"
    all_items = session.query(MenuItem).all()
    item = session.query(MenuItem).filter_by(id=menu_id).one()
    if request.method == 'POST':
        count = 0
        filename = item.image
        for i in all_items:
            if i.image == filename:
                count += 1
                if count == 2:
                    break
        # if no other menu item uses this file, delete it.
        if count < 2 and os.path.isfile(os.path.join
                                (app.config['UPLOAD_FOLDER'], filename)):
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        session.delete(item)
        session.commit()
        flash("Menu Item Successfully Deleted")
        return redirect(url_for('restaurantMenu',
                                restaurant_id=restaurant_id))
    else:
        return render_template('deletemenuitem.html', item=item,
                               restaurant_id=restaurant_id, menu_id=menu_id)


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


# add new user to the User model. Takes username, email, and picture.
def createUser(login_session):
    newUser = User(name=login_session['username'],
                   email=login_session['email'],
                   picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


# check if uploaded file type is in the allowed extension list
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


#Making an API Endpoint (GET Request)
@app.route('/restaurants/JSON')
def restaurantsJSON():
    restaurants = session.query(Restaurant).all()
    return jsonify(Restaurants=[restaurant.serialize for
                                restaurant in restaurants])


@app.route('/restaurant/<int:restaurant_id>/menu/JSON')
def restaurantMenuJSON(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    items = session.query(MenuItem).filter_by(
        restaurant_id=restaurant.id).all()
    return jsonify(MenuItems=[i.serialize for i in items])


@app.route('/restaurant/<int:restaurant_id>/menu/<int:menu_id>/JSON')
def restaurantMenuItemJSON(restaurant_id, menu_id):
    item = session.query(MenuItem).filter_by(id=menu_id).one()
    return jsonify(MenuItems=[item.serialize])


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
