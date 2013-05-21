HasGeek Funnel -- beta
======================

Code for HasGeek's Funnel at http://funnel.hasgeek.com/

You are welcome to contribute a patch or use this code to run your own funnel
under the terms of the BSD license, specified in LICENSE.txt.

This code runs on `Python`_ with the `Flask`_ microframework. You will need a
bunch of requirements that can be installed with::

  $ pip install -r requirements.txt

Copy `settings-sample.py` to `settings.py`, edit as necessary, and start the
server with::

  $ python runserver.py

WSGI is recommended for production. Enable ``mod_wsgi`` in Apache and make a
``VirtualHost`` with::

  WSGIScriptAlias / /path/to/website.wsgi

.. _Python: http://python.org/
.. _Flask: http://flask.pocoo.org/
.. _lastuser: https://github.com/hasgeek/lastuser
