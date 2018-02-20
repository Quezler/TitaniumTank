
#Drops the Titanium Tank Participant Medal to the inventories (backpacks) of all contest participants.
#This does not cover the people who completed the tour. The medal server is responsible for that.

"""
=============================================================================
Titanium Tank Contest Medal Distribution Program
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
from json import JSONDecoder
from urllib.parse import urlencode
from urllib.request import Request, urlopen





#Main class

class potato(object):

#Init:

    def __init__(self):

        #Grab the steam web API key and medal promoid:
        self.web_api_key = None
        self.promoid = None
        with open("../data/Steam API.csv", mode="r", encoding="UTF-8") as f:
            for x in reader(f):
                cell = x[0].strip().lower()
                if cell == "medal":
                    self.web_api_key = x[1]
                elif cell == "promoid":
                    self.promoid = x[1]

        #These cannot remain as None:
        if self.web_api_key is None:
            raise RuntimeError("Missing Steam Web API key")
        if self.promoid is None:
            raise RuntimeError("Missing medal promoID")





#Runs the whole operation:

    def run(self):

        #In this list, store all the steam profile links of medal recepients.
        medal_recepients_urls = list()

        #Open the participants CSV file and slam all the steam profile links into the list:
        with open("../data/Contest Participants.csv", mode="r", encoding="UTF-8") as f:
            for x in reader(f):
                if not x[0].strip().startswith("//"):
                    medal_recepients_urls.append(x[5])

        #Open the winners CSV file and slam all the steam profile links into the list as well.
        #There will be some dupes since the winners are also contest participants - this is intentional.
        with open("../data/Contest Winners.csv", mode="r", encoding="UTF-8") as f:
            for x in reader(f):
                if not x[0].strip().startswith("//"):
                    medal_recepients_urls.append(x[4])


        #Now all these URLs need to be converted into steam IDs.
        #Loop across each steam URL:
        steam64 = list()
        abort = False
        for x in medal_recepients_urls:

            #Grab the steam ID of this profile link:
            steamid = self.get_steam_id_from_profile(x)

            #If None is returned, log that it's a bad URL:
            if steamid is None:
                print("Unable to obtain steam ID for:", x)
                abort = True

            #Otherwise, put the steam ID into the list:
            else:
                steam64.append(steamid)


        #If one of the URLs didn't resolve to a steam ID, halt the program.
        #Otherwise, people who deserve a medal won't receive them.
        if abort:
            print("Aborting execution due to invalid profile links.")
            return None


        #Avoid accidental re-runs of this program: Get user confirmation that they really want to proceed:
        if input("Enter 1337 to confirm distribution:\t").strip() != "1337":
            print("Aborting medal distribution.")
            return None


        #Per steam ID:
        for x in steam64:

            #Attempt to give out the medal:
            verdict = self.grant_medal_to_user(self.web_api_key, self.promoid, x)

            #Print the appropriate message to the console:
            steamurl = "http://steamcommunity.com/profiles/" + str(x)
            if verdict:
                print("Successfully distributed medal to:", steamurl)
            else:
                print("Failed to distribute medal to:", steamurl)

        #Done
        print("Done")





#Given a steam profile link, return the steam64 ID of this user:

    def get_steam_id_from_profile(self, profile_link):

        #Remove extraneous slashes first, and then split along them:
        split_url = profile_link.strip("/").split("/")

        #The last element is either a steam ID (yay) or a custom steam url (boo).
        param = split_url[-1]
        
        #If it's a steam ID, then return that value and call it a day:
        if split_url[-2] == "profiles":
            return param

        #Otherwise, treat it as a custom URL. We need to resolve it via the steam API.

        #Create the GET parameters and build the full API call to resolve the vanity URL:
        params = urlencode({'key':self.web_api_key, 'vanityurl': param})
        url = "https://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/?" + params

        #Open the response and read it in:
        try:
            with urlopen(url) as f:
                data = f.read().decode()
        except:
            return None

        #Parse the resulting json:
        json_parser = JSONDecoder()
        root = json_parser.decode(data)

        #Grab the response node:
        response_node = root["response"]

        #If the API call was a success, return the steam ID:
        if response_node["success"] == 1:
            return response_node["steamid"]

        #Otherwise, return None to denote failure:
        return None





#Given a steam web API key, a medal promoID, and a steam64 ID, give the community medal to that user.
#Return True if the medal was successfully distributed, false on failure.
#
#Note: This function can be recycled for future medal distribution scripts.
#Make sure to copy the necessary import statements from the top (urllib & json).

    def grant_medal_to_user(self, api_key, promoid, steam64):

        #Because shit can hit the fan at any point (because Valve),
        #wrap the whole operation around a try/except.
        try:
            self.send_medal_post_request(api_key, promoid, steam64)
            return True             #Nothing blew up

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





#Run this program.
if __name__ == "__main__":
    obj = potato()
    obj.run()
