
#Titanium Tank Tour Progress Tracking Server
#
#Records player progress from the titanium tank tour to a master database.
#
#The database file will later be fed to a medal distribution script to
#award the Titanium Tank Participant Medal to players who complete the tour#
#
#This uses the same license that Sourcemod uses (GNU GPL v3).

"""
=============================================================================
Titanium Tank Tour Progress Tracking Server
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
from http.server import SimpleHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn, TCPServer
from sqlite3 import Connection
from threading import Thread
from time import sleep
from urllib.parse import urlparse, parse_qs





#The web server itself.
#This server sends and accepts requests from the MvM servers regarding tour data.

class TourProgressHandler(SimpleHTTPRequestHandler):

#Called every time a GET request is made on this server.
#GET requests are made every time a client wants to see their tour data.

    def do_GET(self):

        #To avoid crashing the whole thread, wrap the entire thing around a try/except.
        #Nothing should crash, but just to be safe...
        try:
            self.handle_get_data()
        except Exception as e:
            print("GET Error:", e)





#Called everytime a server issues a GET request:

    def handle_get_data(self):

        #Parse the URL first:
        parse_result = urlparse(self.path)

        #Then parse the result of the query string:
        params_dict = parse_qs(parse_result.query)

        #Check the key and see if we should accept or reject this request.
        #
        #The server is sitting behind a firewall with no open ports, so only LAN (localhost)
        #connections can be made to it, but just to be safe, check for an auth key anyway.
        if not self.is_valid_request(params_dict):
            self.send_response(403)
            self.end_headers()
            return None

        #Grab the steam ID and the mission (if specified).
        (steam64, mission_index) = self.load_get_parameters(params_dict)

        #If the steam ID is unspecified, abort for error:
        if steam64 is None:
            self.send_response(400)
            self.end_headers()
            return None
        
        #If the mission is unspecified, then return a keyvalue file of ALL progress:
        if mission_index is None:
            raw_data = self.build_full_tour_kv(steam64)

        #Otherwise, return a keyvalue file of JUST that mission's progress:
        else:
            raw_data = self.build_mission_kv(steam64, mission_index)

        #Encode it and send it back to the caller:
        binary_data = raw_data.encode()
        self.send_response(200)
        self.send_header('Content-type', 'text')
        self.send_header('Content-Length', len(binary_data))
        self.end_headers()
        self.wfile.write(binary_data)





#Builds the full keyvalues tree of this steam ID's data:

    def build_full_tour_kv(self, steam64):

        #If this steam ID doesn't exist in the progress dictionary, return an empty keyvalue file:
        tour_info = master.progress_dictionary.get(steam64)
        if tour_info is None:
            return '"tour"\n{\n}'

        #Build a section of the file:
        kv = ['"tour"\n{']

        #Per mission, bitflag string:
        for x in enumerate(tour_info):

            #Put the mission in, followed by the bitflag of waves:
            kv.append('"{}" "{}"'.format(*x))

        #Then close the keyvalue file:
        kv.append("}")

        #Join the data and return it:
        return "\n".join(kv)





#Builds a keyvalue of just one mission's data:

    def build_mission_kv(self, steam64, mission_index):

        #If this steam ID doesn't exist in the progress dictionary, return an empty keyvalue file:
        tour_info = master.progress_dictionary.get(steam64)
        if tour_info is None:
            return '"mission"\n{\n}'

        #Otherwise, get the bitflags for this mission's waves:
        flags = tour_info[mission_index]

        #Return the keyvalue string:
        return '"mission"\n{\n"%d"\t"%d"\n}' % (mission_index, flags)





#Returns a tuple of the GET parameters:

    def load_get_parameters(self, params_dict):

        #Get the steam ID in first: (the player who completed the wave)
        steamid = params_dict.get("steam64")
        if steamid is None:
            return (None, None)

        steamid = int(steamid[0])

        #Get the mission index: (the mission they completed the wave on)
        mission_index = params_dict.get("mission")
        if mission_index is not None:
            mission_index = int(mission_index[0])

        #Construct everything and return the tuple:
        return steamid, mission_index





#################################################################################################





#Called every time a POST request is sent to this server.
#
#POST requests are sent every time an MvM server reports that a player completed a wave in full.
#This is the input that is used to record progress to the tour database.

    def do_POST(self):

        #To avoid crashing the whole thread, wrap the entire thing around a try/except.
        #Nothing should crash, but just to be safe...
        try:
            self.handle_post_data()
        except Exception as e:
            print("POST Error:", e)





#Called every time a POST request is sent to this server.

    def handle_post_data(self):

        #Read in the POST data:
        content_len = int(self.headers['content-length'])
        post_body = self.rfile.read(content_len)

        #Parse the parameters into a dictionary:
        params_dict = parse_qs(post_body.decode())

        #Check the key and see if we should accept or reject this request.
        #
        #The server is sitting behind a firewall with no open ports, so only LAN (localhost)
        #connections can be made to it, but just to be safe, check for an auth key anyway.
        if not self.is_valid_request(params_dict):
            self.send_response(403)
            self.end_headers()
            return None

        #Build a data tuple out of the POST parameters data:
        data_tuple = self.load_post_parameters(params_dict)

        #If it failed, return nothing:
        if data_tuple is None:
            self.send_response(400)
            self.end_headers()
            return None

        #Push the tuple to the database thread and let it process that data.
        #That way, we can handle more POST requests from the tour servers, and avoid race conditions.
        master.post_requests_queue.append(data_tuple)

        #Send back a response. We want to send the number 1 if the client has this wave credit already,
        #the number 2 if they just got it. This will print the correct message to the client's chat.
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        #Check if they have this wave credit already:
        code = 1 if master.client_has_wave_credit(*data_tuple) else 2

        #Send back the proper number:
        self.wfile.write(str(code).encode())





#Returns true if the given HTTP POST request is valid and authorized, false otherwise:

    def is_valid_request(self, params_dict):

        #Grab the key parameter:
        key = params_dict.get("key")

        #If it's null, return false:
        if key is None or len(key) == 0:
            return False

        #Otherwise, get the value in it and check if it matches:
        value = key[0]
        return value == SERVER_AUTH_KEY





#Parses the post parameters into a data tuple.

    def load_post_parameters(self, params_dict):

        #Get the steam ID in first: (the player who completed the wave)
        steamid = params_dict.get("steam64")
        if steamid is None:
            return None

        #Get the timestamp next: (the time they completed this wave at)
        timestamp = params_dict.get("timestamp")
        if timestamp is None:
            return None

        #Get the mission index: (the mission they completed the wave on)
        mission_index = params_dict.get("mission")
        if mission_index is None:
            return None

        #Lastly, grab the wave number:
        wave_number = params_dict.get("wave")
        if wave_number is None:
            return None

        #Construct everything and return the tuple:
        try:
            return (int(steamid[0]), int(timestamp[0]), int(mission_index[0]), int(wave_number[0]))
        except:
            return None










#Dummy class used to make the server threaded.

class ThreadedHTTPServer(ThreadingMixIn, TCPServer):
    """Handle requests in a separate thread."""
    pass










#Main class.
#This class owns and manages the tour progress data for all players of the tour.

class potato(object):

#Init the database. Do it on the current working directory itself.

    def __init__(self):

        #Create the database:
        self.db = Connection("mvm_titanium_tank_tour_progress.sq3", check_same_thread=False)
        cursor = self.db.cursor()

        #Create the tour progress table. This contains 
        cursor.execute("CREATE TABLE IF NOT EXISTS WaveCredits (Steam64 Text, TimeStamp Int, MissionIndex Int, WaveNumber Int)")    #Steam64 needs to be text since Sourcepawn can't hold 64-bit numbers as ints - only as strings

        #Commit the query:
        cursor.close()
        self.db.commit()

        #For optimal performance (and also as extra security), cache the tour data into a big dictionary.
        #This allows all requests for the tour data to poke at the dictionary, and not hammer the database
        #(and the file system) repeatedly with requests. It keeps this HTTP server fast and optimized.
        #
        #Test suite: Ran this with 5 million players simulation, the RAM usage didn't make a dent on the
        #server, so we should be good even though this is not scalable to infinity. (Can easily revert to
        #scalable but slower approach if it ends up being an issue.)
        self.progress_dictionary = dict()       #To win a medal, your steam ID must be fully packed with all the required completion flags

        #Blank tuple to use when initializing a player's tour progress in the progress dictionary:
        #Each index in the tuple represents a mission's progress, and each number is a bitflag of the completed waves.
        self.blank_tour_tuple = (0, 0, 0, 0, 0, 0)

        #Since the HTTP server is threaded (1 thread per request), we cannot directly insert
        #the wave credits into the database and the dictionary in here, or else that's asking
        #for a huge headache of race conditions and bugs. For a server that determines if
        #someone gets an in-game item drop, that's something we want to completely avoid.
        #
        #The HTTP server will shove POST requests in this list, and then the worker thread that
        #runs on this class will grind the queue down if there's any pending progress data to store.
        #
        #This solves the thread safety issue while also allowing the HTTP server to still
        #accept POST requests without any speed or throttling limitations.
        self.post_requests_queue = list()

        #Init the progress dictionary with the database's contents:
        for row in self.db.execute("SELECT Steam64, TimeStamp, MissionIndex, WaveNumber FROM WaveCredits"):
            self.insert_client_wave_credit(*row)





#Runs once every second to process POST requests.
#This is ran on a separate worker thread.

    def mainloop(self):

        #Create a database cursor that we can use in this thread:
        self.cursor = self.db.cursor()

        #For forever:
        while True:

            #Don't let this thread ever crash - wrap everything around a try/except:
            try:
                self.run()
            except Exception as e:
                print("Database Thread Error:", e)

            #Then wait a second before looping again:
            sleep(1)





#Processes the queue of POST requests:

    def run(self):

        #Since multiple threads hammer the post requests queue, the thread-safe way to
        #handle this is to use a while loop that calls .pop() on that list until it
        #raises IndexError, in which case we abort because then there's nothing left.
        while True:

            #Try yanking out ONE post request:
            try:
                (steam64, timestamp, mission_index, wave_number) = self.post_requests_queue.pop()

            #On failure, exit:
            except IndexError:
                self.db.commit()            #Save all the database transactions
                return None

            #Now we have to record this progress data.

            #First, insert it into the database:
            self.cursor.execute("INSERT INTO WaveCredits (Steam64, TimeStamp, MissionIndex, WaveNumber) VALUES (?,?,?,?)", (str(steam64), timestamp, mission_index, wave_number))

            #Then insert it into the progress dictionary:
            self.insert_client_wave_credit(steam64, timestamp, mission_index, wave_number)





#Inserts a client's wave credit into the progress dictionary:

    def insert_client_wave_credit(self, steam64, timestamp, mission_index, wave_number):

        #First, put the steam ID in the dictionary, if it doesn't exist already:
        steam64 = int(steam64)
        if steam64 not in self.progress_dictionary:
            self.progress_dictionary[steam64] = self.blank_tour_tuple

        #Then grab the tuple out:
        tour_tuple = self.progress_dictionary[steam64]

        #Grab the wave completion bitflags for this mission out:
        bitflags = tour_tuple[mission_index]

        #Insert in this wave credit:
        bitflags |= 1 << wave_number

        #Rebuild the tuple and insert it back into the progress dictionary:
        #(We use tuples instead of lists, since lists use more memory and we don't mutate these THAT much.)
        self.progress_dictionary[steam64] = tour_tuple[:mission_index] + (bitflags,) + tour_tuple[mission_index+1:]




        
#Returns true if the client has the wave credit already, false otherwise.
#
#If they have the wave credit, don't process the POST request.
#Also, do not notify them of a wave credit (to avoid spamming them).

    def client_has_wave_credit(self, steam64, timestamp, mission_index, wave_number):

        #Check if the client's steam ID exists first:
        if steam64 not in self.progress_dictionary:
            return False

        #Then grab the bitflags for that wave from the tour tuple:
        bitflags = self.progress_dictionary[steam64][mission_index]

        #Check if this wave has been completed:
        return bitflags & (1 << wave_number) != 0





#Grab the server authentication key from the CSV file: (This is the same CSV file the tour servers have.)
SERVER_AUTH_KEY = None
with open("Tour Information.csv", mode="r", encoding="UTF-8") as f:
    for line in reader(f):
        if line[0].lower() == "key":
            SERVER_AUTH_KEY = line[1]
            break





#Sanity check:
if SERVER_AUTH_KEY is None:
    raise SystemExit("Missing server authentication key!")





#Start the progress class. Make sure its mainloop runs on a worker thread:
master = potato()
Thread(target=master.mainloop).start()





#Start the HTTP server:
handler = ThreadedHTTPServer(("", 65432), TourProgressHandler)
print("Starting Titanium Tank Tour Tracker server...")
handler.serve_forever()




