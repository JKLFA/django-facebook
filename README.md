Facebook integration with your Django website
=============================================

Installation:
------------
Simply add ``django_facebook`` to your INSTALLED_APPS and configure
the following settings:

    FACEBOOK_APP_ID = ''
    FACEBOOK_API_KEY = ''
    FACEBOOK_SECRET_KEY = ''

    # Custom settings
    FACEBOOK_PREPOPULATE_USER_DATA = False
    FACEBOOK_EXTENDED_PERMISSIONS = []  # Ex: ['email', 'user_birthday']
    FACEBOOK_FIRST_LOGIN_REDIRECT = None  # Ex: '/welcome'
    
    # Optionally for debugging
    FACEBOOK_DEBUG_COOKIE = ''
    FACEBOOK_DEBUG_TOKEN = ''


Settings:
--------

* ``FACEBOOK_PREPOPULATE_USER_DATA``

  * Fill in ``user.email``, ``user.first_name``, and ``user.last_name`` with Facebook data
  * Save other information from the Graph API to ``user.fb_profile``:
     1. ``uid``
     2. ``name``
     3. ``first_name``
     4. ``last_name``
     5. ``link`` (URL for the user's profile page)
     6. ``birthday``
     7. ``hometown``
     8. ``bio``
     9. ``gender``
     10. ``updated_time`` (last time the user's profile was updated

Templates:
---------
A few helpers for using the Javascript SDK can be enabled by adding
this to your base template in the ``<head>`` section:

    {% load facebook %}
    {% facebook_init %}
      {% block facebook_code %}{% endblock %}
    {% endfacebook %}

And this should be added just before your ``</html>`` tag:

    {% facebook_load %}
    
The ``facebook_load`` template tag inserts the code required to
asynchronously load the facebook javascript SDK. The ``facebook_init``
tag calls ``FB.init`` with your configured application settings. It is
best to put your facebook related javascript into the ``facebook_code``
region so that it can be called by the asynchronous handler.

You may find the ``facebook_perms`` tag useful, which takes the setting
in FACEBOOK_EXTENDED_PERMISSIONS and prints the extended permissions out
in a comma-separated list.

    <fb:login-button show-faces="false" width="200" max-rows="1"
      perms="{% facebook_perms %}"></fb:login-button>


A helpful debugging page to view the status of your facebook login can
be enabled by adding this to your url configuration:

    (r'^facebook_debug/', direct_to_template, {'template':'facebook_debug.html'}),  


Once this is in place you are ready to start with the facebook javascript SDK!

This module also provides all of the tools necessary for working with facebook
on the backend:


Middleware:
----------
This provides seamless access to the Facebook Graph via request object.

If a user accesses your site with a valid facebook cookie, your views
will have access to request.facebook.graph and you can begin querying
the graph immediately. For example, to get the users friends:

    def friends(request):
      if request.facebook:
        friends = request.facebook.graph.get_connections('me', 'friends')
        
To use the middleware, simply add this to your MIDDLEWARE_CLASSES:
    'django_facebook.middleware.FacebookMiddleware'


``FacebookDebugCookieMiddleware`` allows you to set a cookie in your settings
file and use this to simulate facebook logins offline.

``FacebookDebugTokenMiddleware`` allows you to set a uid and access_token to
force facebook graph availability.


Authentication:
--------------
This provides seamless integration with the Django user system.

If a user accesses your site with a valid facebook cookie, a user
account is automatically created or retrieved based on the facebook UID.

To use the backend, add this to your AUTHENTICATION_BACKENDS:
    'django_facebook.auth.FacebookBackend'

Don't forget to include the default backend if you want to use standard
logins for users as well:
    'django.contrib.auth.backends.ModelBackend'

If you would like to redirect the user to a welcome page or similar on the
first time they log in, use the ``FACEBOOK_FIRST_LOGIN_REDIRECT`` setting:
    FACEBOOK_FIRST_LOGIN_REDIRECT = None  # Ex: '/welcome'


Signals:
-------
Django provides a signals infrastructure to allow decoupled applications to get
notified when actions occur elsewhere in the framework.

The following signals are sent on Facebook actions:

* ``fb_user_login``

  Sent every time a user accesses a page while logged in to your site with Facebook.  Sent no more than once every 10 seconds.

* ``fb_user_registration``

  Sent the first time a Facebook user logs in.  A new ``django.contrib.auth`` ``User`` is created as a result, with username of their Facebook id.


Decorators:
----------
``@facebook_required`` is a decorator which ensures the user is currently
logged in with facebook and has access to the facebook graph. It is a replacement
for ``@login_required`` if you are not using the facebook authentication backend.
