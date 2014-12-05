#! /usr/bin/env python

"""
Temporary Maintenance Server
"""

import cherrypy

def CORS():
    cherrypy.response.headers["Access-Control-Allow-Origin"] = "*"
    cherrypy.response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    cherrypy.response.headers["Access-Control-Allow-Headers"] = "Authorization, origin, content-type, accept"

def start():
    ##### CherryPy ######
    conf = {
        'global': {
            'server.socket_host': '0.0.0.0',
            'server.socket_port': 8000,
            'log.screen': True,
            },
    }

    root = Root()
    cherrypy.request.hooks.attach('before_finalize', CORS)
    cherrypy.quickstart(root, '/', conf)

class Root(object):
    @cherrypy.expose
    def default(self, *args):
        raise cherrypy.HTTPError(503, "The Assembly Service is down for maintenance")

start()
