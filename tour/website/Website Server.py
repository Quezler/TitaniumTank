
#Titanium Tank Tour Progress Website Server
#Allows players to check up on their Titanium Tank Tour progress.

"""
=============================================================================
Titanium Tank Tour Progress Website Server
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

#Imports
from csv import reader
from gzip import compress as gzip_compress
from http.server import SimpleHTTPRequestHandler, HTTPServer
from json import JSONDecoder
from os import getcwd, sep
from os.path import getmtime
from socketserver import ThreadingMixIn, TCPServer
from sqlite3 import Connection
from threading import Thread
from time import sleep, strftime, localtime, time
from urllib.parse import urlparse, parse_qs, urlencode
from urllib.request import urlopen





#####################################################
#####################################################
#####################################################

#The website server itself:

class TourProgressWebsite(SimpleHTTPRequestHandler):

#Called every time a GET request is made.
#
#For our purposes, get requests are made by:
#
#- Clients visiting the tour website and serving HTML to them.
#- Clients' javascript requesting raw data in CSV format.
#- Servers requesting client tour progress in VDF (keyvalues) format.

    def do_GET(self):

        #Wrap the whole request in a try/except so that the client doing something stupid
        #will not crash the whole server down (which will break our web server permanently).
        try:
            self.process_get_request()
        except Exception as e:
            print("Error in GET:", e)





#Called when a POST request is made.
#
#For our purposes, POST requests are made by:
#- MvM servers reporting their server information (requires TT API key).
#- Clients submitting a steam profile link to check progress (no API key).

    def do_POST(self):

        #Wrap the whole request in a try/except so that the client doing something stupid
        #will not crash the whole server down (which will break our web server permanently).
        try:
            self.process_post_request()
        except Exception as e:
            print("Error in POST:", e)





#####################################################


#Called when a client performs a GET request.

    def process_get_request(self):

        #Check rate limit. Don't allow clients to interact with the server
        #if they make way too many requests to it. No legitimate user should
        #ever hit the rate limit, but just to be safe, impose a check anyway.
        if self.exceeded_rate_limit():
            return None

        #Check if the browser requesting the data supports gzipped compressed content:
        self.supports_gzip = self.check_gzip_support()

        #For sanity, make the path all lowercase and remove any trailing slashes:
        relative_path = self.path.strip("/").lower()

        #Split it along the slashes:
        path_split = relative_path.split("/")

        #The first section must be "titaniumtank" or else send 404:
        if path_split[0] != "titaniumtank":
            self.serve_page(404)
            return None

        #If it's only one element long, then serve the main page:
        path_length = len(path_split)
        if path_length == 1:
            self.serve_page(200, "main")
            return None

        #The second section determines what data we serve.
        resource = path_split[1]

        #Based on the string, determine where we go.

        #Global tour information:
        if resource == "global":
            self.serve_page(200, "global")
            return None

        #Tour server information: 
        if resource == "servers":
            self.serve_page(200, "servers")
            return None

        #Tour information requested by SRCDS:
        if resource == "vdf":
            self.serve_vdf_data()
            return None

        #If a CSV file is requested, then that requires careful and special treatment.
        #The client's javascript requests CSV files to render these pages.
        if resource.endswith(".csv"):
            self.serve_csv_data(resource)
            return None

        #If it's a number, then it's an individual tour progress page. Assume it's a steam64 ID.
        #The client will do a GET request for a csv file with the steam ID for the player's data.
        try:
            steam64 = int(resource)
            self.serve_page(200, "individual")
            return None
        except:
            pass

        #For everything else, send 404 error:
        self.serve_page(404)





#####################################################


#Serves a CSV data to the client.
#Javascript issues a GET request for CSV files to display data on the client's browser.

    def serve_csv_data(self, csv_filename):

        #Based on the csv filename, determine what we serve back.

        #Global data:
        if csv_filename == "global.csv":
            (raw, compressed) = master.global_data_csv
            data = compressed if self.supports_gzip else raw

        #Server data:
        elif csv_filename == "servers.csv":
            data = self.generate_server_csv()

        #Player data:
        else:

            #The steam ID is a 64-bit number. Try converting it to an integer first:
            try:
                steam64 = int(csv_filename.replace(".csv", ""))

            #If it fails, serve a 404 error:
            except:
                self.serve_page(404)
                return None

            #Grab the data for this player's tour progress:
            data = self.generate_player_csv(steam64)


        #Serve the CSV data to the client:
        self.serve_data(data)





#Generates a CSV file of server data to send to the client.

    def generate_server_csv(self):

        #The first row is the current unix time:
        t = int(time())
        csv_list = [str(t)]

        #Add subsequent servers to it:
        server_dict = master.server_info_dict
        for x in server_dict:

            #If the server hasn't reported an update for over a minute now, assume it went offline.
            #Only include servers that have reported data sometime within the past minute.
            data = server_dict[x]
            if (t - data[-1]) < 60:
                csv_list.append(create_csv_row(data))

        #Join all the rows by newlines and make a binary string:
        csv_raw = "\n".join(csv_list).encode()

        #Based on whether the client accepts gzip encoding or not,
        #determine whether we should compress this data or not:
        return gzip_compress(csv_raw) if self.supports_gzip else csv_raw





#Generates a CSV file of player data to send to the client.

    def generate_player_csv(self, steam64):

        #The first row contains the server timestamp, total wave credits (39), and total maximum waves (7).
        p = master                              #One global lookup
        max_waves = p.max_waves
        first_row = create_csv_row((int(time()), p.total_credits, max_waves))

        #Put this in a list:
        csv_list = [first_row]

        #Per mission tuple in this player's tour dictionary:
        for x in p.tour_progress_dict.get(steam64, ()):

            #This is the row that becomes the CSV file string.
            #None's become empty strings, timestamps stay the same:
            new_row = ["" if y is None else y for y in x]

            #Pad it with -1's for missions that have less than the maximum number of waves:
            padding = max_waves - len(x)
            new_row.extend((-1,)*padding)

            #Compile it into a CSV row string and put it into the csv list:
            csv_list.append(create_csv_row(new_row))


        #Join all the rows by newlines and make a binary string:
        csv_raw = "\n".join(csv_list).encode()

        #Based on whether the client accepts gzip encoding or not,
        #determine whether we should compress this data or not:
        return gzip_compress(csv_raw) if self.supports_gzip else csv_raw





#####################################################


#Serves a VDF file to the client.
#SRCDS issues a GET request for VDF files to display tour data on the client's game.

    def serve_vdf_data(self):

        #The parameters for this GET request are encoded into the URL:
        (steam64, mission_index) = self.load_get_parameters()

        #If the mission index is unspecified, generate the global tour keyvalue string:
        if mission_index is None:
            data = self.build_full_tour_kv(steam64)

        #Otherwise, only return the bitflags for just that mission:
        else:
            data = self.build_mission_kv(steam64, mission_index)


        #Based on whether the client accepts gzip encoding or not,
        #determine whether we should compress this data or not:
        raw_data = data.encode()
        payload = gzip_compress(raw_data) if self.supports_gzip else raw_data

        #Then serve it to the client:
        self.serve_data(payload)





#Returns a tuple of the GET parameters passed to this link:

    def load_get_parameters(self):

        #Parse the URL first:
        parse_result = urlparse(self.path)

        #Then parse the result of the query string:
        params_dict = parse_qs(parse_result.query)

        #Get the steam ID in first: (the player who completed the wave)
        steam64 = params_dict.get("steam64")
        if steam64 is None:
            return (None, None)

        steam64 = int(steam64[0])

        #Get the mission index: (the mission they completed the wave on)
        mission_index = params_dict.get("mission")
        if mission_index is not None:
            mission_index = int(mission_index[0])

        #Construct everything and return the tuple:
        return steam64, mission_index





#Builds the full keyvalues tree of this steam ID's data:

    def build_full_tour_kv(self, steam64):

        #If this steam ID doesn't exist in the progress dictionary, return an empty keyvalue file:
        tour_info = master.tour_progress_dict.get(steam64)
        if tour_info is None:
            return '"tour"\n{\n}'

        #Start off with the key header:
        kv = ['"tour"\n{']

        #Per mission tuple:
        for (x,y) in enumerate(tour_info):

            #Get the bitflag of wave completions for this mission:
            bitflags = self.get_mission_completion_bitflags(y)

            #Put the mission in followed by the bitflag of wave completions:
            kv.append('"{}" "{}"'.format(x, bitflags))

        #Then close the keyvalue file:
        kv.append("}")

        #Join the data and return it:
        return "\n".join(kv)





#Builds a keyvalue of just one mission's data:

    def build_mission_kv(self, steam64, mission_index):

        #If this steam ID doesn't exist in the progress dictionary, return an empty keyvalue file:
        tour_info = master.tour_progress_dict.get(steam64)
        if tour_info is None:
            return '"mission"\n{\n}'

        #Otherwise, use the mission index to get the mission tuple of interest:
        mission_tuple = tour_info[mission_index]

        #Compute the bitflags for this mission tuple:
        bitflags = self.get_mission_completion_bitflags(mission_tuple)

        #Generate and return the keyvalue string:
        return '"mission"\n{\n"%d"\t"%d"\n}' % (mission_index, bitflags)





#Given a timestamp tuple representing a mission's wave credits, return a bitflag consisting
#of the mission's wave credits. This is used to build keyvalue files to send back to SRCDS.

    def get_mission_completion_bitflags(self, mission_tuple):

        #Store the completion bitflag for this mission here:
        bitflags = 0

        #Per wave in the mission:
        for (x,y) in enumerate(mission_tuple, start=1):

            #If there is a timestamp specified, then set the appropriate bit on the bitflag:
            if y is not None:
                bitflags |= 1 << x

        #Done
        return bitflags





#####################################################


#Called when a client performs a POST request.

    def process_post_request(self):

        #Check rate limit.
        if self.exceeded_rate_limit():
            return None

        #Check if the browser requesting the data supports gzipped compressed content:
        self.supports_gzip = self.check_gzip_support()

        #Grab the data size:
        content_len = int(self.headers['content-length'])

        #If it's over 255 chars, cap it to 255. (So that people don't put 1 GB of shit in there.)
        if content_len > 255:
            content_len = 255

        #Read in the post body data for the specified number of bytes:
        post_body = self.rfile.read(content_len)

        #Parse the post parameters into a dictionary:
        params_dict = parse_qs(post_body.decode())

        #There are 2 POST requests that can be made here:
        #
        #- One of them is made by SRCDS, which is made once every few seconds.
        #These requests are used to keep the server information table up-to-date.
        #
        #These requests have a key parameter since they require the TT API key.
        #Otherwise, random POST requests from the internet can mess up the server page.
        if "key" in params_dict:
            try:
                self.handle_server_info_report(params_dict)
            except:
                return None

        #- Another is made by the client when they enter a steam profile link.
        #This request is used to redirect the client to the appropriate webpage.
        #
        #These requests have a steam URL parameter as set on the webpage itself.
        elif "steamurl" in params_dict:
            try:
                if not self.handle_steam_url_request(params_dict):      #If the URL is found to be bad, force an exception
                    raise
            except:
                self.serve_page(200, False)





#Called when a SRCDS instance (a tour server) reports its server information to here.
#
#Note: We do not need to do any try/except here since the entire function is wrapped around one.

    def handle_server_info_report(self, params_dict):

        #Grab the IP address of the client:
        client_ip = self.client_address[0]

        #For some reason, depending on the network, we get a local IP address, even if the client
        #sent the POST request to the public IP address. Here's one crappy workaround to this:
        if client_ip.startswith("192.") or client_ip.endswith("0.1"):
            try:
                client_ip = self.headers["Host"].split(":")[0]
            except:
                pass
		
        #Cache the master object locally:
        p = master

        #If this IP is banned from making POST requests with a web API key, drop the request.
        #This prevents outsiders from trying to brute force guess the API key.
        if client_ip in p.banned_post_ips:
            return None

        #First, check the key that was passed to here.
        #
        #If a bad key was passed in, permanently ban that IP address. This means someone is
        #trying to inject their server into the main server information page.
        #
        #Nobody except authorized tour servers have any reason to make a POST request with
        #a Titanium Tank API key.
        key = params_dict["key"][0]
        if key != p.tt_api_key:
            p.banned_post_ips.add(client_ip)
            p.ip_requests_count[client_ip] = 9001
            return None

        #Grab all the other data:
        server_number = params_dict["number"][0]
        mission_index = params_dict["mission"][0]
        wave_number   = params_dict["wave"][0]
        round_state   = params_dict["roundstate"][0]
        defenders     = params_dict["defenders"][0]
        connecting    = params_dict["connecting"][0]
        is_passworded = params_dict["haspassword"][0]
        port_number   = params_dict["port"][0]

        #Get the total number of waves for this mission:
        total_waves = p.tour_maps_list[int(mission_index)][1]

        #Place all this into the global server information dictionary:
        p.server_info_dict[server_number] = (server_number, is_passworded, mission_index, defenders,
                                             connecting, wave_number, total_waves, round_state,
                                             client_ip, port_number, int(time()))

        #Decrement this IP's rate limit request from the dictionary.
        #Valid server information reports are not subject to the rate limitation.
        p.ip_requests_count[client_ip] -= 1





#Called when a client enters a steam profile link into the text box to look up tour progress.
#
#Note: We do not need to do any try/except here since the entire function is wrapped around one.
#An error page is sent back if the client enter a bad steam URL into the box.

    def handle_steam_url_request(self, params_dict):

        #Try getting the steam profile link out:
        steamlink = params_dict.get("steamurl")[0]

        #Break it apart along the slashes:
        split_url = steamlink.lower().split("/")

        #Find the index for where the "steamcommunity.com" string is located:
        string_idx = split_url.index("steamcommunity.com")
        if string_idx == -1:
            return False

        #The next index points to either "profiles" or "url". The index after that is the parameter.
        string = split_url[string_idx + 1]
        param  = split_url[string_idx + 2]

        #If the string is "profiles", then the parameter is the steam ID itself. Best case.
        if string == "profiles":
            steam64 = param

        #If the string is "id", then we need to resolve the vanity url:
        #This is a lot slower than the above since we need to make a steam web API call, but oh well.
        elif string == "id":
            steam64 = self.resolve_vanity_url(param)

        #Otherwise, this url is invalid:
        else:
            return False

        #Using the steam ID, redirect the client to the proper tour progress page:
        self.send_response(301)
        self.send_header('Location', '/TitaniumTank/{}'.format(steam64))
        self.end_headers()

        #Return true to denote success (avoid triggering the exception handler):
        return True





#Resolves a custom steam profile vanity URL to a steam64 ID.

    def resolve_vanity_url(self, vanity_url):

        #Reference: https://lab.xpaw.me/steam_api_documentation.html#ISteamUser_ResolveVanityURL_v1

        #Create the GET parameters and build the full API url:
        params = urlencode({'key':master.steam_api_key, 'vanityurl': vanity_url})
        url = "https://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/?" + params

        #Open the response and read it in:
        with urlopen(url) as f:
            data = f.read().decode()

        #Parse the resulting json:
        json_parser = JSONDecoder()
        root = json_parser.decode(data)

        #Grab the response node:
        response_node = root["response"]

        #If the API call was a success, return the steam ID:
        if response_node["success"] == 1:
            return int(response_node["steamid"])

        #Otherwise, raise an exception and abort the call stack.
        raise





#####################################################


#Returns true if a client has hit the server rate limit, false otherwise.

    def exceeded_rate_limit(self):

        #Grab client IP address:
        client_ip = self.client_address[0]

        #Clients are allowed to make a maximum of 60 requests to the server in a minute.
        #This normalizes to 1 request per second, but burst requests are supported.

        #Get the number of requests they have made so far:
        ip_dict = master.ip_requests_count
        if client_ip not in ip_dict:
            ip_dict[client_ip] = 0
        requests_count = ip_dict[client_ip]

        #If they have hit 60 already, return true since they did hit the rate limit.
        #They will have to try again between 1-60 seconds later, depending on the current system time.
        if requests_count > 60:
            return True

        #Otherwise, mark this client as making a request:
        ip_dict[client_ip] += 1





#Serves a page to the client.

    def serve_page(self, http_code, html_key=None):

        #Set the HTTP code:
        self.send_response(http_code)

        #If gzip is supported, set that header as well:
        if self.supports_gzip:
            self.send_header("Content-Encoding", "gzip")

        #We're done with headers:
        self.end_headers()

        #Grab the page we are to serve to the client:
        (raw, compressed) = master.html_pages[html_key]

        #And serve it:
        self.wfile.write(compressed if self.supports_gzip else raw)





#Serves data to the client:
#
#Note: Due to caching mechanisms we have, this function assumes the payload is
#gzipped already if the client supports gzipped data. It will not gzip on its own!

    def serve_data(self, data):

        #Set the HTTP code (always 200):
        self.send_response(200)

        #If gzip is supported, set that header as well:
        if self.supports_gzip:
            self.send_header("Content-Encoding", "gzip")

        #We're done with headers:
        self.end_headers()
        
        #Send it to the client:
        self.wfile.write(data)





#Returns true if the requesting web browser supports gzip data, false otherwise.

    def check_gzip_support(self):

        #Check for the accept-encoding header:
        accepted_encoding = self.headers.get("Accept-Encoding")
        if accepted_encoding is None:
            return False

        #Check if gzip is one of the accepted encodings:
        return "gzip" in accepted_encoding.lower()





#####################################################
#####################################################
#####################################################


#Makes the HTTP server threaded.

class ThreadedHTTPServer(ThreadingMixIn, TCPServer):
    """Handle requests in a separate thread."""
    pass





#####################################################
#####################################################
#####################################################

#Main class
#This class holds the tour progress data and loads HTML.

class potato(object):

#Init

    def __init__(self):

        #From the CSV files we need:
        #
        #- Steam web API key
        self.steam_api_key = None

        #- TT web API key
        self.tt_api_key = None

        #- Tour maps list:
        self.tour_maps_list = list()

        #Grab the steam API key first.
        #There are two API keys in there. Get the one that is NOT linked to the Titanium Tank medal.
        #
        #That way, if we happen to reach the Steam API rate limit (which is 100k requests...)
        #then the dummy API key is banned, not the medal API key.
        with open("../data/Steam API.csv") as f:
            for x in reader(f):
                if x[0].lower() == "general":
                    self.steam_api_key = x[1]

        #Grab the TT web API key and build the tour list:
        with open("../data/Tour Information.csv") as f:
            for x in reader(f):
                cell = x[0].lower()
                if cell == "apikey":
                    self.tt_api_key = x[1]
                elif cell.startswith("mvm_"):
                    self.tour_maps_list.append((x[0], int(x[2])))

        #A null tour tuple. This represents a blank tour with no progress made on it.
        #While we build the null tuple, also compute the total number of wave credits in this tour.
        self.null_tuple = list()
        self.total_credits = 0
        for (x,y) in self.tour_maps_list:
            self.total_credits += y
            self.null_tuple.append((None,)*y)

        #...actually make it into a tuple:
        self.null_tuple = tuple(self.null_tuple)

        #Cache the maximum number of waves any single mission has:
        self.max_waves = max(self.tour_maps_list, key=lambda j: j[1])[1]

        #Now init the tour database:

        #Create the database file:
        self.db_path = "../data/mvm_titanium_tank_tour_progress.sq3"
        self.db = Connection(self.db_path, check_same_thread=False)

        #Create the tour progress table. This contains ALL players' tour data.
        self.db.execute("CREATE TABLE IF NOT EXISTS WaveCredits (Steam64 Text, TimeStamp Int, MissionIndex Int, WaveNumber Int)")

        #Commit the query:
        self.db.commit()

        #Hold the database file's modification time stamp here.
        #We will check if the file was updated, and if so, refresh our tour data dictionary cache:
        self.mod_time = 0

        #Store the rowid of the most-recent loaded database entry.
        #This allows us to not have to load previously-cached data from the dictionary.
        self.row_id = 0

        #The big tour dictionary:
        self.tour_progress_dict = dict()

        #The dictionary that holds the tour server information:
        self.server_info_dict = dict()

        #IP address rate limit dictionary.
        #This gets dumped out once a minute, but is otherwise used to prevent a single IP address
        #from making too many GET/POST requests to this web server.
        self.ip_requests_count = dict()

        #Set of banned IP addresses.
        #Use this to drop invalid POST requests that attempt to pass a fake TT API key.
        self.banned_post_ips = set()

        #The csv data containing the global tour statistics:
        self.global_data_csv = (bytes(), bytes())

        #For one of the global stats graphs, we want to keep track of the total number
        #of wave credits given each day, including duplicates.
        self.wave_credits_earned_per_day = dict()

        #Preload all the HTML webpages from the html folder into a dictionary.
        #
        #This will allow us to serve webpages to the client quickly without hammering the file system,
        #which allows us to skip some I/O overhead.
        #
        #The javascript, css, and images are served from GitHub so that we can easily update them
        #with a GitHub commit without having to restart this web server.
        self.html_pages =  {
                                "main":       self.load_html_page("main.html"),
                                "global":     self.load_html_page("global.html"),
                                "individual": self.load_html_page("individual.html"),
                                "servers":    self.load_html_page("servers.html"),
                                None:         self.load_html_page("404.html"),
                                False:        self.load_html_page("badprofile.html"),
                            }





#Given a HTML file name, load it, compress it down, and return it to the caller.
#These HTML files are cached globally for a quick web server response time.

    def load_html_page(self, filename):

        #We can trim whitespace from the HTML file, so let's do that:
        cleaned_html = list()
        with open(getcwd() + sep + "html" + sep + filename, mode="r", encoding="UTF-8") as f:
            for x in f:
                cleaned_html.append(x.strip())

        #Join the strings together, and then gzip the payload:
        html_str  = "".join(cleaned_html).encode()
        html_gzip = gzip_compress(html_str)

        #Both of these will be stored in a dictionary for quick lookup on the web server.
        return html_str, html_gzip





#Runs once a second on a worker thread.

    def mainloop(self):

        #For forever:
        while True:

            #Crash handler safety: Wrap the whole thing on a try/except:
            try:
                self.run()
            except Exception as e:
                print("Database thread error: ", e)

            #Wait 1 second before checking again:
            sleep(1)





#Called once every second as a watchdog for the database:

    def run(self):

        #If it's time to dump the rate limit IP addresses dictionary, do it.
        #The rate limit resets once every minute.
        if int(time()) % 60 == 0:
            self.ip_requests_count.clear()

        #Check if the database file was modified. If not, then don't do anything:
        mod_time = getmtime(self.db_path)
        if mod_time == self.mod_time:
            return None

        #Cache the new modification timestamp:
        self.mod_time = mod_time

        #Grab everything from the database, including the row ID, and cache it into the tour dictionary:
        for x in self.db.execute("SELECT rowid, Steam64, TimeStamp, MissionIndex, WaveNumber FROM WaveCredits WHERE rowid > ?", (self.row_id,)):

            #Break up the row's contents:
            (rowid, steam64, timestamp, mission_index, wave_number) = x

            #Cache the row ID:
            self.row_id = rowid

            #Insert this database row to the dictionary:
            self.cache_player_wave_credit(int(steam64), timestamp, mission_index, wave_number)


        #Then build the big csv data for the global statistics chart.
        #
        #The client does a GET request to this server asking for the data, so instead of generating the data while the client
        #is making their request (which can potentially be expensive), let's generate it right here so that we can shove it
        #to the client immediately when they ask for it. This means we can compile it once and serve it to infinite clients.
        #
        #The one downside is we compile this data even if nobody ever asks for it, but the generation is usually done at a
        #moment that nobody is accessing the tour site so the performance hit should be unnoticeable.
        self.build_global_chart_csv()





#Inserts a wave credit into the tour progress dictionary for the given player:

    def cache_player_wave_credit(self, steam64, timestamp, mission_index, wave_number):

        #Using the timestamp of this wave credit, increments the total wave credits awarded per day dictionary:
        stamp = localtime(timestamp)
        key = (stamp.tm_mon, stamp.tm_mday)
        d = self.wave_credits_earned_per_day
        d[key] = d.get(key, 0) + 1

        #If this steam ID doesn't have anything for it already, put the null tuple in it:
        if steam64 not in self.tour_progress_dict:
            self.tour_progress_dict[steam64] = self.null_tuple

        #Then grab the tour tuple out of there:
        tour_tuple = self.tour_progress_dict[steam64]

        #Grab this mission's tour tuple out:
        mission_tuple = tour_tuple[mission_index]

        #If there's already a timestamp at the given tuple index, that means the player already has this wave credit.
        #Leave it alone - don't modify it.
        index = wave_number - 1                         #wave numbers are 1-based on Sourcemod and the medal server but 0-based here, so do wave_number - 1
        if mission_tuple[index] is not None:
            return None

        #Insert the timestamp into it:
        mission_tuple = self.modify_tuple(mission_tuple, index, timestamp)      

        #Then insert the new tuple back into the tour tuple:
        tour_tuple = self.modify_tuple(tour_tuple, mission_index, mission_tuple)

        #And put it back into the dictionary:
        self.tour_progress_dict[steam64] = tour_tuple





#"Modifies" a tuple. This is faster than turning a tuple to a list, mutating it, and then reverting it back.
#
#We use tuples as storage since they have a smaller memory footprint than lists do. We rarely modify these
#containers - they are primarily read-only, so using a list to store them is wasteful in RAM when a tuple
#does what we want (for the most part) with a smaller memory footprint.

    modify_tuple = lambda self, this, index, value: this[:index] + (value,) + this[index+1:]





#Builds the CSV data that the client uses to display global tour statistics:

    def build_global_chart_csv(self):

        #Grab the null tuple and turn it into a bunch of lists. Replace the None with 0's as well.
        #We will use this to count how many wave credits have been earned per mission across all players.
        #This is used to generate the line graph in quadrant 2 (wave credits vs wave number for each map).
        mission_counter = [[0]*len(x) for x in self.null_tuple]

        #Use this list to count the number of players that have earned a set number of wave credits.
        #This is used to generate the line graph in quadrant 1 (players vs wave credits count).
        credits_counter = [0]*self.total_credits

        #Use these two lists to count how many players have participated and completed each mission in the tour:
        total_missions = len(self.null_tuple)
        participants_counter = [0]*total_missions
        completionists_counter = [0]*total_missions

        #Keep track of how many players received a medal:
        medal_recepients = 0

        #In this dictionary, pair each date (Month & Day) with the number of new players who participated in the tour that day:
        timestamp_participated_dict = dict()

        #For this dictionary, similar as the previous one, but store the number of people who *finished* the tour on each day:
        timestamp_completed_dict = dict()

        #Count the number of new players who have played at least 1 wave on each map, for each day.
        #This is mostly for the map makers to see how many new players have played on their maps.
        #
        #The map index is used to index into this list. Init it with all empty dictionaries:
        map_index_date_participant_counter = [dict() for x in range(total_missions)]

        #Similarly, count the number of players who have beaten each map, on each day:
        map_index_date_completist_counter = [dict() for x in range(total_missions)]

        #Count the number of UNIQUE wave credits awarded on each day.
        unique_wave_credits_awarded_dict = dict()

        #Per tour tuple: (Per player's tour progress)
        for t in self.tour_progress_dict.values():

            #Keep a count of how many wave credits this player has earned:
            wave_credits_earned = 0

            #In this list, store the timestamps of ALL the wave credits they have earned:
            timestamp_all_list = list()

            #Keep track of whether the player has completed the tour or not.
            #Assume they haven't unless otherwise proven.
            tour_completion_bool_list = [False]*total_missions

            #Per mission in the tour tuple:
            for (x,y) in enumerate(t):

                #Did this player complete the mission in full?
                #Assume yes unless otherwise told. (There needs to be a single None in the tuple for this to become false.)
                completed_mission = True

                #Did this player participate in this mission by completing at least one wave in full?
                #Assume no unless otherwise told. (There needs to be at least 1 entry that's not None for this to become true.)
                participated_mission = False

                #In this list, store the timestamps of all the wave credits they earned for this mission.
                #We will use this to count the number of unique players who have played on each map, over time.
                timestamp_mission_list = list()

                #Per wave in the mission:
                for (i,j) in enumerate(y):

                    #If this value is set to None, that means they didn't earn a wave credit for this wave.
                    #This also means they didn't complete the mission, so set that boolean to false:
                    if j is None:
                        completed_mission = False
                        continue

                    #Raise the mission counter: (the total wave credits earned per wave, per map)
                    mission_counter[x][i] += 1

                    #Raise the number of wave credits this player has earned:
                    wave_credits_earned += 1

                    #Put this timestamp in both timestamp lists:
                    timestamp_all_list.append(j)
                    timestamp_mission_list.append(j)

                    #This player has completed at least one wave in this mission, so set the participation boolean to true:
                    participated_mission = True

                    #Form a timestamp and increment the awarded wave credits dictionary.
                    stamp = localtime(j)
                    key = (stamp.tm_mon, stamp.tm_mday)
                    unique_wave_credits_awarded_dict[key] = unique_wave_credits_awarded_dict.get(key, 0) + 1
                    

                #If the player participated in this mission, raise the participation counter for this mission:
                if participated_mission:
                    participants_counter[x] += 1

                #Do the same for completionists:
                if completed_mission:
                    completionists_counter[x] += 1

                #Put the mission completion boolean into the tour completion boolean list:
                tour_completion_bool_list[x] = completed_mission

                #If the mission timestamp list is empty, grind the next iteration:
                if len(timestamp_mission_list) == 0:
                    continue

                #Get the smallest timestamp (the first time this player completed a wave on this map), and form a date tuple:
                stamp = localtime(min(timestamp_mission_list))
                key = (stamp.tm_mon, stamp.tm_mday)

                #And increment the counter for the appropriate date, for the appropriate map:
                date_counter_dict = map_index_date_participant_counter[x]
                date_counter_dict[key] = date_counter_dict.get(key, 0) + 1

                #If they beat the mission, then do the same for the biggest timestamp, but store it in the completist list dictionary:
                if completed_mission:
                    stamp = localtime(max(timestamp_mission_list))
                    key = (stamp.tm_mon, stamp.tm_mday)
                    date_counter_dict = map_index_date_completist_counter[x]
                    date_counter_dict[key] = date_counter_dict.get(key, 0) + 1


            #Increment the global credits counter based on the number of wave credits this player has:
            if wave_credits_earned != 0:
                credits_counter[wave_credits_earned-1] += 1

            #If this player has completed all the missions, raise the medal recepients counter:
            if False not in tour_completion_bool_list:
                medal_recepients += 1

            #Find the smallest timestamp. That's the time they participated in the tour.
            #Increment that date by 1, since that's when this player participated in the tour:
            stamp = localtime(min(timestamp_all_list))
            key = (stamp.tm_mon, stamp.tm_mday)
            timestamp_participated_dict[key] = timestamp_participated_dict.get(key, 0) + 1
            
            #If the player beat the tour, do the same thing as above, but use the largest
            #timestamp and increment the completed players dictionary instead.
            if len(timestamp_all_list) >= self.total_credits:
                stamp = localtime(max(timestamp_all_list))
                key = (stamp.tm_mon, stamp.tm_mday)
                timestamp_completed_dict[key] = timestamp_completed_dict.get(key, 0) + 1


        #The last thing to compile data for is the global statistics table.

        #We can get total tour participants from the length of the dictionary:
        tour_participants = len(self.tour_progress_dict)

        #Total medals is given by the medal_recepients variable.

        #Total wave credits awarded is given by the row ID.

        #Total unique wave credits can be obtained by summing the awarded wave credits by date dictionary:
        global_credits_acquired = sum(unique_wave_credits_awarded_dict.values())

        #Total missions participated and completed can be found by summing the participants and completionists arrays accordingly:
        total_participated_missions = sum(participants_counter)
        total_completed_missions = sum(completionists_counter)

        ##########################################################

        #Now we build the CSV data to transmit to clients.
        csv_data = list()

        #The mission counter list is transposed. Javascript expects the columns as maps and the wave numbers as rows,
        #but the counter list has it backwards. We need to modify the counter list first.
        #
        #First, all the lists need to be the same length.

        #First, find what's the length of the longest list in there:
        longest_list_len = len(max(mission_counter, key=len))

        #Then per list in the mission counter:
        for x in mission_counter:

            #Append enough -1's to the end of the list until it reaches the length of the longest list.
            #This will make all the lists the same length in the counter list.
            remaining_entries = longest_list_len - len(x)
            x.extend((-1,)*remaining_entries)


        #Put the mission counter first into the csv data list:
        for x in zip(*mission_counter):
            csv_data.append(create_csv_row(x))

        #Add an = as a delimiter:
        csv_data.append("=")

        #Then put the player wave credits counter in next.
        #
        #Delete the last value from the list because that's the total medal recepients, which we don't want
        #to include, or else it will skew the chart horribly.
        del credits_counter[len(credits_counter) - 1]
        csv_data.append(create_csv_row(credits_counter))

        #Add an = as a delimiter:
        csv_data.append("=")

        #Participants and completionists counters go next:
        csv_data.append(create_csv_row(participants_counter))
        csv_data.append(create_csv_row(completionists_counter))

        #Add an = as a delimiter:
        csv_data.append("=")

        #This section is the biggest grindfest in the global statistics computation.
        #For each date, compute the local and cumulative sum of the relevant data sections.

        #Because the keys to this dictionary are all dates, sort the wave credits awarded dictionary by date:
        #Because everything ultimately is measured by wave credit and/or its timestamp, it is safe to use the keys of this dictionary.
        date_keys = tuple(sorted(unique_wave_credits_awarded_dict))

        #Using the participants counter dictionary for each map and each date, compute the cumulative sum of participants on each map on each date:
        cumulative_map_date_participants_counts = [self.compute_successive_sum_dict(x, date_keys) for x in map_index_date_participant_counter]

        #Do the same thing with the completists counter dictionary as well:
        cumulative_map_date_completists_counts  = [self.compute_successive_sum_dict(x, date_keys) for x in map_index_date_completist_counter]

        #Now, compute the *grand total* number of missions each player has completed and participated in on each day.
        #These are NOT stacked dictionaries, but these are the sum of all missions participated/completed across all maps.
        new_mission_completists = dict()            #Completed
        new_mission_participants = dict()           #Participated

        #Loop across every date tuple:
        for x in date_keys:

            #Total missions played by all participants:
            for y in map_index_date_participant_counter:
                new_mission_participants[x] = new_mission_participants.get(x, 0) + y.get(x, 0)

            #Total missions completed by all participants (completists):
            for y in map_index_date_completist_counter:
                new_mission_completists[x] = new_mission_completists.get(x, 0) + y.get(x, 0)


        #Now we need to generate the CSV data with all this data in it.
        #
        #Put all the dictionaries we have created in a single list:
        dictionary_list =   cumulative_map_date_participants_counts + cumulative_map_date_completists_counts + [timestamp_participated_dict, timestamp_completed_dict,
                            new_mission_participants, new_mission_completists, unique_wave_credits_awarded_dict, self.wave_credits_earned_per_day]
        
        #Using that dictionary list, generate the CSV rows for each dictionary in it.
        #Loop across each date key:
        for x in date_keys:

            #Put the key in the row first. Flatten it out into (as) a list, since this is a CSV file.
            row_data = list(x)

            #Then for each dictionary, grab the value for this date from it, and put the value into the row list. Default to 0 if not found.
            for y in dictionary_list:
                row_data.append(y.get(x, 0))

            #Then build a CSV string and put it into the big CSV data list:
            csv_data.append(create_csv_row(row_data))


        #Add an = as a delimiter:
        csv_data.append("=")

        #The statistics table information go last:
        global_str = create_csv_row((tour_participants, medal_recepients, self.row_id, global_credits_acquired, total_participated_missions, total_completed_missions))
        csv_data.append(global_str)

        #Then build the full CSV file and cache it:
        #That way, we don't have to go through this whole grind every time someone requests global tour information.
        csv_raw = "\n".join(csv_data).encode()
        csv_gzip = gzip_compress(csv_raw)
        self.global_data_csv = (csv_raw, csv_gzip)





#Given a dictionary containing data for each date, return a dictionary that contains
#the successive sum of the data leading up to each date ("stack the dictionary").

    def compute_successive_sum_dict(self, dates_dict, date_keys):

        #In this dictionary, store the cumulative sum of the data for each date:
        stacked_dict = dict()

        #Per date key, from day 1 up to today:
        for (x,y) in enumerate(date_keys):

            #If the cumulative sum dictionary is empty, then init the sum at 0:
            if not len(stacked_dict):
                previous_sum = 0

            #Otherwise, grab the sum of the PREVIOUS day:
            else:
                previous_key = date_keys[x-1]
                previous_sum = stacked_dict.get(previous_key, 0)

            #Add the previous sum to this sum and put it in the stacked dictionary:
            stacked_dict[y] = previous_sum + dates_dict.get(y, 0)

        #Done
        return stacked_dict





#####################################################
#####################################################
#####################################################

#Given an iterable of numbers, return a comma-delimited string of all those numbers joined together:
create_csv_row = lambda data: ",".join(str(x) for x in data)                        #Use a generator so that we don't have to construct a list, only to destroy it immediately after





#Create the main class and run the database thread:
master = potato()
Thread(target=master.mainloop).start()

#Run the HTTP server:
handler = ThreadedHTTPServer(("", 27000), TourProgressWebsite)
print("Serving tour progress website at port 27000")
handler.serve_forever()




