## Item Catalog
This is a web application that enables users to create and customize	menu pages for multiple restaurants.

### Included files:
* fullstack-nanodegree-vm
	* README.txt
	* vagrant
		* pg_config.sh and Vagrantfile - files necessary for Vagrant to work
		* .vagrant - more necessary Vagrant stuff
		* catalog - contains the relevant files of this	project
			* database_setup.py - database model containing tables for restaurants and menu items
			* lotsofmenus2.py - contains a bunch of example restaurants and menu items
			* project.py - the project web server
			* client_secrets.json - Google+ API info
			* fb_client_secrets - Facebook API info
			* static - images and css
			* templates - HTML views

### Instructions:
Fork the fullstack-nanodegree-vm repository so
that you have a version within your GitHub account. Clone your
version of the fullstack-nanodegree-vm repository to your
local machine.

Navigate to the catalog folder in the repository, open a
GitBash there and enter the command $ vagrant up. When vagrant
has finished starting up, enter the command $ vagrant ssh. Enter
$ cd /vagrant and then $ cd catalog.

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
