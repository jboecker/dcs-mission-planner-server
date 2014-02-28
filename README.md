dcs-mission-planner-server
==========================

The server component of the DCS: World Mission Planner

How to run
==========

The "official" server is hosted on a free Heroku instance and expects connection information for a postgres database in the DATABASE_URL environment variable. If that variable is not set, it will use a file instead.

To run it manually, simply execute "python3 server.py <server-port>".

Currently, there is no option in the client to choose a different server. You will need to modify the client to use another server.

Note that to keep the database size below the limit of a free Heroku instance, old instances will be deleted when more than 9000 instances have been created. This number is defined in the MAX_INSTANCES variable in serve.py.

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
