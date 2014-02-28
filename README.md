dcs-mission-planner-server
==========================

The server component of the DCS: World Mission Planner

How to run
==========

The "official" server is hosted on a free Heroku instance and expects connection information for a postgres database in the DATABASE_URL environment variable. If that variable is not set, it will use a file instead.

To run it manually, simply execute "python3 server.py <server-port>".

You will need to patch the client to use your server.

License
=======

The airports.kml file was made by kosmos224 and was downloaded from [DCS User Files](http://www.digitalcombatsimulator.com/de/files/379189/), which lists "Freeware - Free version, Unlimited distribution" in the license field.

jQuery (js/jquery-2.1.0.min.js) is under the MIT license (see https://jquery.org/license/ for details).

Everything else is released under the terms of the GNU AGPL license (see AGPL.txt).
