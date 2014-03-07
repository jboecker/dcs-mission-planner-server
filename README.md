dcs-mission-planner-server
==========================

The server component of the DCS: World Mission Planner

How to run
==========

The server requires Python 3 and the modules listed in `requirements.txt`.

On Linux, the following commands should get you up and running:
```bash
$ git clone git@github.com:jboecker/dcs-mission-planner-server.git
$ cd dcs-mission-planner-server
$ virtualenv -p python3 venv
$ source venv/bin/activate
$ pip install -r requirements.txt
$ cd src
$ python serve.py 8080
```

On Windows, you may be interested in the following links:
* [Python 3.2 64-bit](http://legacy.python.org/ftp//python/3.2.5/python-3.2.5.amd64.msi)
* [Tornado for Python 3.2 64-bit](http://www.lfd.uci.edu/~gohlke/pythonlibs/gmqofism/tornado-3.2.win-amd64-py3.2.exe)
* [pyproj for Python 3.2 64-bit](https://code.google.com/p/pyproj/downloads/detail?name=pyproj-1.9.2.win-amd64-py3.2.exe&can=2&q=)

Please note that there is no official support for running your own server.

Quick Overview
==============

The server side of the mission planner does not do much. It facilitates communication between the clients and otherwise stays out of the way.

Data is stored in a key-value store. All keys are simple strings, most values are encoded as JSON before saving.

Instances are stored under the key "instance-\<instance_id\>". The key "instance-list" stores a JSON array of all existing instance IDs. The "next_instance_id" key stores the next instance ID to be assigned.

Instances
=========

An instance is represented by a python dictionary. See the handle_create_instance_request method for a list of fields.
The most important field is instance["data"]["objects"]. This is a mapping of object IDs to values and can be thought of as a per-instance key-value store.

Clients connect to the server over a WebSocket.

Connected clients will be notified of any changes to this shared key-value store and can change it with "transaction" requests. A transaction request has a list of preconditions (if this is not a subset of the objects in the key-value store, the transaction fails), a list of (IDs of) objects that should be deleted, and a list of objects that should be updated or created.

License
=======

The airports.kml file was made by kosmos224 and was downloaded from [DCS User Files](http://www.digitalcombatsimulator.com/de/files/379189/), which lists "Freeware - Free version, Unlimited distribution" in the license field.

jQuery (js/jquery-2.1.0.min.js) is under the MIT license (see https://jquery.org/license/ for details).

Everything else is released under the terms of the GNU AGPL license (see AGPL.txt).
