"""
Machinery for launching the wsgi server 
"""
from gevent import monkey
from gevent.wsgi import WSGIServer
from noodles.utils.mailer import MailMan
monkey.patch_all()

# Gevent-socketio lib
from noodles.websockserver import server
from noodles.http import Request, Response, Error500
from noodles.dispatcher import Dispatcher
from noodles.middleware import AppMiddlewares
from config import URL_RESOLVER, CONTROLLERS, MIDDLEWARES, DEBUG

import logging
import traceback
import sys

from gevent import pywsgi
from noodles.geventwebsocket.handler import WebSocketHandler

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

resolver = __import__(URL_RESOLVER, globals(), locals())

# Create an dispatcher instance
dispatcher = Dispatcher(mapper=resolver.get_map(), controllers=CONTROLLERS)

# Load all midllewares for application
app_middlewares = AppMiddlewares(MIDDLEWARES)


# Our start point WSGI application
def noodlesapp(env, start_response):
    # Get request object
    request = Request(env)
    #print "Try to handle url_path '%s'" % request.path
    # Get callable object with routine method to handle request
    callable_obj = dispatcher.get_callable(request)
    if not callable_obj:
        # May be here an error,raise exception
        raise Exception('Can\'t find callable for this url path')
    # Callable function must return Respone object
    for middleware in app_middlewares:
        callable_obj = middleware(callable_obj) # Hardcoded use of HTTP Session middleware
    try:
        response = callable_obj()
        return response(env, start_response)
    # Capture traceback here and send it if debug mode
    except Exception as e:
        f = logging.Formatter()
        traceback = f.formatException(sys.exc_info())
        # Don't remove this print
        print traceback # Show traceback in console
        if DEBUG:            
            response = Error500(e, traceback)
        else:
            response = Error500()
            MailMan.mail_send(MailMan(),e.__repr__(), traceback)
        return response(env, start_response)


# Start server function, you may specify port number here
def startapp():
    try:
        from config import PORT, SERVER_LOGTYPE
    except ImportError:
        PORT = 8088 # By defaultl 8088 debug port
    print 'Start server on %i...' % int(PORT)
    if SERVER_LOGTYPE == 'supress':
        import StringIO
        s = StringIO.StringIO()
    else:
        s = SERVER_LOGTYPE
    server.WebSocketServer(('', int(PORT)), noodlesapp, log=s).serve_forever()