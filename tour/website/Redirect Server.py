
#Temporary redirect server
#
#Since we're changing the website from port 26999 to port 27000, have
#a dummy server that sits on 26999 so that clients who use the old
#links will get directed to the new location. This is only temporary!

"""
=============================================================================
Titanium Tank Tour Progress Website Redirect Server
Copyright (C) 2018 Potato's MvM Servers.  All rights reserved.
=============================================================================

This program is free software; you can redistribute it and/or modify it under
the terms of the GNU General Public License, version 3.0, as published by the
Free Software Foundation.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from http.server import SimpleHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn, TCPServer





class TourProgressWebsiteRedirector(SimpleHTTPRequestHandler):

    def do_GET(self):
        try:
            self.send_response(301)         #Moved permanently
            self.send_header("Location", "http://73.233.9.103:27000" + self.path)
            self.end_headers()
        except:
            pass





class ThreadedHTTPServer(ThreadingMixIn, TCPServer):
    """Handle requests in a separate thread."""
    pass





handler = ThreadedHTTPServer(("", 26999), TourProgressWebsiteRedirector)
print("Serving redirect server at port 26999")
handler.serve_forever()




