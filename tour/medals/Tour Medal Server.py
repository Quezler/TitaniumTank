
#Titanium Tank Tour Progress Tracking Medal Server
#
#Records player progress from the Titanium Tank Tour to a master database.
#Drops the medal real-time to players who successfully complete the tour.

"""
=============================================================================
Titanium Tank Tour Progress Tracking Medal Server
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
from json import JSONDecoder
from socketserver import ThreadingMixIn, TCPServer
from sqlite3 import Connection
from threading import Thread
from time import time, sleep
from urllib.parse import urlencode, parse_qs
from urllib.request import Request, urlopen




#####################################################
#####################################################
#####################################################


#The web server itself.
#This server accepts wave credit reports from the MvM servers to record tour progress.
#
#To note: This server is NOT open to the world wide web. Only localhost and machines on
#the same LAN network as this server can send POST requests to it. This prevents other
#community servers or outsiders from interacting with this server.

class TourProgressHandler(SimpleHTTPRequestHandler):

#Called every time a POST request is sent to this server.
#
#POST requests are sent every time an MvM server reports that a player completed a wave in full.
#This is the only way to record player progress into the tour database.

    def do_POST(self):

        #To avoid crashing the whole thread, wrap the entire thing around a try/except.
        #Nothing should crash, but just to be safe...
        try:
            self.handle_post_data()
        except Exception as e:
            print("Medal server POST error:", e)





#Called every time a POST request is sent to this server.

    def handle_post_data(self):

        #No matter what, send HTTP code 200 to the request.
        self.send_response(200)
        self.end_headers()

        #Determine how much data we need to read in. Cap it at 1024 bytes as a sanity limit:
        content_len = int(self.headers['content-length'])
        if content_len > 1024:
            content_len = 1024

        #Read in this data:
        post_body = self.rfile.read(content_len)

        #Parse the parameters into a dictionary:
        params_dict = parse_qs(post_body.decode())

        #Check the key and see if we should accept or reject this request.
        #
        #The server is sitting behind a firewall with no open ports, so only LAN (localhost)
        #connections can be made to it, but just to be safe, check for an auth key anyway.
        if not self.is_valid_request(params_dict):
            return None

        #Build a data tuple out of the POST parameters data:
        data_tuple = self.load_post_parameters(params_dict)

        #If it failed, don't do anything:
        if data_tuple is None:
            return None

        #Push the tuple to the database thread and let it process that data.
        #That way, we can handle more POST requests from the tour servers, and avoid race conditions.
        master.post_requests_queue.append(data_tuple)

        #SRCDS doesn't expect any data back, so don't return any data back.





#Returns true if the given HTTP POST request is valid and authorized, false otherwise:

    def is_valid_request(self, params_dict):

        #Grab the key parameter:
        key = params_dict.get("key")

        #If it's null, return false:
        if key is None or len(key) == 0:
            return False

        #Otherwise, get the value in it and check if it matches:
        value = key[0]
        return value == master.tt_api_key





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





#####################################################
#####################################################
#####################################################


#Dummy class used to make the server threaded.

class ThreadedHTTPServer(ThreadingMixIn, TCPServer):
    """Handle requests in a separate thread."""
    pass





#####################################################
#####################################################
#####################################################


#Main class.
#This class owns and manages the tour progress data for all players of the tour.
#It also drops the medal immediately on a player's inventory if they complete the tour.

class potato(object):

#Init the database. Do it on the current working directory itself.

    def __init__(self):

        #Create the database:
        self.db = Connection("../data/mvm_titanium_tank_tour_progress.sq3", check_same_thread=False)

        #Create the tour progress table and the medal recepients tables.
        #The first table stores all the individual wave credits.
        #The second table stores the recepients of the participant medal.
        self.db.execute("CREATE TABLE IF NOT EXISTS WaveCredits (Steam64 Text, TimeStamp Int, MissionIndex Int, WaveNumber Int)")    #Steam64 needs to be text since Sourcepawn can't hold 64-bit numbers as ints - only as strings
        self.db.execute("CREATE TABLE IF NOT EXISTS MedalOwners (Steam64 Text, TimeStamp Int)")

        #Commit the query:
        self.db.commit()

        #Open a text file *in APPEND mode* and hold onto its handle forever.
        #We'll write steam IDs of medal recepients to it as a backup, in addition to the database records.
        self.f = open("../data/_Medal Recepients.txt", mode="a", encoding="UTF-8")

        #From the config CSV files, load important tour and medal information:
        (self.promoid, self.steam_api_key, self.tt_api_key, self.completed_tour_tuple) = self.load_tour_information()

        #For optimal performance (and also as extra security), cache the tour data into a big dictionary.
        #This allows us to check if a player has completed the tour or not, without having to query the database every time.
        #
        #Test suite: Ran this with 5 million players simulation, the RAM usage didn't make a dent on the
        #server, so we should be good even though this is not scalable to infinity. (Can easily revert to
        #a scalable but slower approach if it ends up being an issue.)
        self.progress_dictionary = dict()       #To win a medal, your steam ID must be fully packed with all the required completion flags.

        #In this set, store the steam IDs of players who have received the medal.
        #This acts as a sanity check to prevent the medal distributor from giving people multiple medals.
        self.medal_recepients = set()

        #Blank tuple to use when initializing a player's tour progress in the progress dictionary:
        #Each index in the tuple represents a mission's progress, and each number is a bitflag of the completed waves.
        self.blank_tour_tuple = (0, 0, 0, 0, 0, 0)

        #Since the HTTP server is threaded (1 thread per request), we cannot directly insert
        #the wave credits into the database and the dictionary in here, or else that's asking
        #for a huge headache of race conditions and bugs. For a server that determines if
        #someone gets an in-game item drop, that's something we want to completely avoid.
        #
        #The HTTP server will shove POST requests in this list, and then the worker thread that
        #runs on this class will grind the queue down if there's any pending request data.
        #
        #This solves the thread safety issue while also allowing the HTTP server to still
        #accept POST requests without any speed or throttling limitations.
        self.post_requests_queue = list()

        #Init the medal recepients set with steam IDs of people who received the medal:
        for x in self.db.execute("SELECT Steam64 FROM MedalOwners"):
            self.medal_recepients.add(int(x[0]))

        #Init the progress dictionary with the database's contents:
        for x in self.db.execute("SELECT Steam64, TimeStamp, MissionIndex, WaveNumber FROM WaveCredits"):
            self.insert_client_wave_credit(*x)





#Loads vital tour information from the config CSV files.

    def load_tour_information(self):

        #Open the steam API file and read in the medal promo ID and web API key:
        promoid = None
        steam_api_key = None
        with open("../data/Steam API.csv", mode="r", encoding="UTF-8") as f:
            for x in reader(f):
                cell = x[0].strip().lower()
                if cell == "medal":
                    steam_api_key = x[1]
                elif cell == "promoid":
                    promoid = x[1]

        #These cannot be set to None:
        if promoid is None:
            raise ValueError("Medal promoID not found!")
        if steam_api_key is None:
            raise ValueError("Steam API key not found!")

        #Open the tour CSV file, grab the TT API key and build a completed tour tuple:
        tt_api_key = None
        completed_tour = list()
        with open("../data/Tour Information.csv", mode="r", encoding="UTF-8") as f:

            #Per row, grab the first cell and make it all lowercase:
            for x in reader(f):
                cell = x[0].strip().lower()

                #Skip commented rows:
                if cell.startswith("//"):
                    continue

                #If this is the API key, then store it:
                if cell == "apikey":
                    tt_api_key = x[1]
                    continue

                #Otherwise, treat this as a map entry.
                #Build the bitflag string for its mission:
                flags = 0
                for y in range(1, int(x[2])+1):
                    flags |= 1 << y

                #Put the bitflag into the completed tour list:
                completed_tour.append(flags)

        #The TT API key must be set:
        if tt_api_key is None:
            raise ValueError("TT API key not found!")

        #Return everything in one swoop to the constructor:
        return promoid, steam_api_key, tt_api_key, tuple(completed_tour)





#Runs once every second to process POST requests.
#This is ran on a separate worker thread.

    def mainloop(self):

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
            self.db.execute("INSERT INTO WaveCredits (Steam64, TimeStamp, MissionIndex, WaveNumber) VALUES (?,?,?,?)", (str(steam64), timestamp, mission_index, wave_number))

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

        #Check if the player has completed the tour. If so, drop the medal on their inventory.
        #This is how we feature a real-time medal drop for tour completion:
        self.check_tour_completion(steam64)





#Checks if a client has completed the tour:

    def check_tour_completion(self, steam64):

        #If this player has received the medal already, there's no need to check for anything:
        if steam64 in self.medal_recepients:
            return None

        #Grab their tour tuple, and check if it contains all the correct bitflags:
        if self.progress_dictionary[steam64] != self.completed_tour_tuple:
            return None

        #If they don't have the medal, but they have completed the tour, then give them the medal.
        #Or at least, try giving the medal:
        verdict = self.grant_medal_to_user(self.steam_api_key, self.promoid, steam64)

        #If it failed, exit. Try giving them the medal again another time.
        #Upon closing The Titanium Tank Tour, run this server one last time to ensure all eligible participants receive the medal.
        if not verdict:
            return None

        #If the medal drop succeeded, put the player's steam ID into the medal owners table so we don't give them a medal again:
        self.db.execute("INSERT INTO MedalOwners (Steam64, TimeStamp) VALUES (?,?)", (str(steam64), int(time())))

        print("Gave medal to:", steam64)

        #Put their steam ID into the set as well (which is 1:1 to the database table):
        self.medal_recepients.add(steam64)

        #Save the database entry immediately:
        self.db.commit()

        #Write their steam ID to the text file:
        self.f.write(str(steam64) + "\n")
        self.f.flush()





#Given a steam web API key, a medal promoID, and a steam64 ID, give the community medal to that user.
#Return True if the medal was successfully distributed, false on failure.
#
#Note: This function can be recycled for future medal distribution scripts.
#Make sure to copy the necessary import statements from the top (urllib & json).

    def grant_medal_to_user(self, api_key, promoid, steam64):

        #Because shit can hit the fan at any point (because Valve),
        #wrap the whole operation around a try/except.
        try:
            return self.send_medal_post_request(api_key, promoid, steam64) #nothing blew up

        #Something blew up, return False for failure:
        except:
            return False





#Sends a post request to the steam API to give a community medal to a steam user:
#This entire function is wrapped around a try/except so don't bother error-checking anything here.

    def send_medal_post_request(self, api_key, promoid, steam64):

        #Pack the given parameters into a dictionary.
        post_fields = {"key":api_key, "promoid":promoid, "steamid":str(steam64)}

        #Encode them:
        encoded_post_fields = urlencode(post_fields).encode()

        #Create the POST request to send to the steam API / item server.
        request = Request("https://api.steampowered.com/ITFPromos_440/GrantItem/v1/", encoded_post_fields)

        #Send the request and read the response:
        response = urlopen(request)
        data = response.read().decode()

        #Parse the returned string into json:
        json_parser = JSONDecoder()
        root = json_parser.decode(data)

        #Grab the result node:
        result = root["result"]

        #Check that the status is 1:
        return result["status"] == 1





#####################################################
#####################################################
#####################################################


#Because this program gives medals to TF2 players, place a safeguard in case it is accidentally ran:
if input("Enter 1337 to start this server:\t").strip() != "1337":
    print("Aborted.")
    raise SystemExit





#Start the progress class. Make sure its mainloop runs on a worker thread:
master = potato()
Thread(target=master.mainloop).start()





#Start the HTTP server:
handler = ThreadedHTTPServer(("", 65432), TourProgressHandler)      #You MUST use a port that's not open to the internet
print("Starting Titanium Tank Medal Server...")
handler.serve_forever()




