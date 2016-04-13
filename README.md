## Item Catalog
This is a Flask web application that enables users to create and customize restaurant
menu pages. Users can log in with Facebook or Google+ accounts to post, edit, and delete
their own restaurants and menu items. Some of the languages and technologies used to
create this app are Python, Flask, SQLAlchemy, SQL, Bootstrap, Oauth, JSON, Vagrant, 
and VirtualBox.

### Included files:
* pg_config.sh and Vagrantfile - Vagrant configuration files
* .vagrant - Vagrant vm files
* database_setup.py - database models
* lotsofmenus2.py - contains example restaurants and menu items
* project.py - the project web server
* client_secrets.json - Google+ API keys
* fb_client_secrets - Facebook API keys
* static - images and css
* templates - HTML views

### Instructions:
This app requires [Vagrant](https://www.vagrantup.com/) and
[VirtualBox](https://www.virtualbox.org/wiki/Downloads) to run.

Clone the FSND-P3_Item-Catalog repository to your local machine. Open a
GitBash in the repository and enter the command $ vagrant up. When vagrant
has finished starting up, enter the command $ vagrant ssh, and then
$ cd /vagrant.

To run the application, enter $ python project.py. The application
will start at loaclhost:5000. Go to this address, or to
localhost:5000/restaurants, in a browser window to use the application.
To stop the server and return to the vagrant command line press
Ctrl+C (Command+C) in the GitBash window.

##### Using the Application:
Logging in (button at the top right corner of the front page) with either
a Google+ or Facebook account will allow you to create and edit Restaurants
and Menu Items. By default, the first account you log in with will be
able to edit the sample restaurants and menu items. After this initial
login, only the creator of a restaurant will be able to edit it.
