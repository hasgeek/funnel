HasGeek Funnel -- beta
======================

Code for HasGeek's Funnel at http://funnel.hasgeek.com/

You are welcome to contribute a patch or use this code to run your own funnel
under the terms of the BSD license, specified in LICENSE.txt.

Steps of configuring development instance
-----------------------------------------

1. This code runs on `Python`_ with the `Flask`_ microframework. You will need a
   bunch of requirements that can be installed with::

        $ pip install -r requirements.txt

   If you want to build an instance which allows you to run bunch of tests then
   additionally install below requirements with the `requirements.txt` mentioned
   earlier::

        $ pip install -r test_requirements.txt

2. Copy `instance/settings-sample.py` to `instance/development.py` using below
   command::

        $ cp instance/settings-sample.py instance/development.py

3. You have to register your application with HasGeek for required
   authentication. Follow
   [this](https://github.com/hasgeek/funnel/wiki/Register-client-application-with-Hasgeek)
   guidelines for registering your application with Hasgeek.

4. After successfully registering your application, update
   **LASTUSER_CLIENT_ID** and **LASTUSER_CLIENT_SECRET** parameters at your
   `instance/development.py` file with below credentials obtained from
   https://auth.hasgeek.com.
   
   For example abtained **Client access key** is 
   `IpdA1NGuSri5E2ceVbCkcw` and **Client secret** is
   `uIWeb_2NQgeMeuU2HaRnZQBPstoRQUSnKyL5GpSEMpvw` then updated values in
   your `instance/development.py` should look like below::

        LASTUSER_CLIENT_ID = 'IpdA1NGuSri5E2ceVbCkcw'
        LASTUSER_CLIENT_SECRET = 'uIWeb_2NQgeMeuU2HaRnZQBPstoRQUSnKyL5GpSEMpvw'

5. You may also want to setup the database with::

        $ python manage.py createdb

6. Start the server with below command::

        $ python runserver.py

   WSGI is recommended for production. Enable ``mod_wsgi`` in Apache and make
   a ``VirtualHost`` with::

        WSGIScriptAlias / /path/to/website.wsgi

.. _Python: http://python.org/
.. _Flask: http://flask.pocoo.org/
.. _lastuser: https://github.com/hasgeek/lastuser
