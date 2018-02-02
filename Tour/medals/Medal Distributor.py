
#Drops the Titanium Tank Participant Medal to the inventories (backpacks) of all eligible participants.

"""
=============================================================================
Titanium Tank Medal Distribution Script
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
from sqlite3 import Connection
from urllib.parse import urlencode
from urllib.request import Request, urlopen





#Credentials to drop the medal on players' inventories.
#The steam web API key (which must be given permission by Eric Smith) and promo ID (given by Eric Smith) are required.
STEAM_WEB_API_KEY = ""
ITEM_PROMO_ID = 1234





#Main class

class potato(object):

#Init:

    def __init__(self):

        #Build a list containing the bitflags of all completed waves in each mission.
        #This is basically a list containing the bitflags of a "completed tour".
        self.completed_tour_list = self.read_tour_data()

        #Build a list of a blank tour progress. We will clone this list and use it to build
        #a player's tour progress from the wave credits they earned (which is in the database).
        self.blank_tour_progress = [0]*len(self.completed_tour_list)

        #Open the tour progress database:
        self.db = Connection("mvm_titanium_tank_tour_progress.sq3")

        #Not necessary, but do it to prevent errors:
        self.db.execute("CREATE TABLE IF NOT EXISTS WaveCredits (Steam64 Text, TimeStamp Int, MissionIndex Int, WaveNumber Int)")    #Steam64 needs to be text since Sourcepawn can't hold 64-bit numbers as ints - only as strings
        self.db.commit()





#Reads in the tour information CSV file and builds a completed tour bitflags list:
#We will compare every player's tour bitflags list to this one to check if they truly completed the tour.

    def read_tour_data(self):
        
        #Open the missions file and build a list of all the mission bitflags of a complete tour:
        completed_tour = list()
        f = open("Tour Information.csv", mode="r", encoding="UTF-8")

        #Per row on the CSV file:
        for row in reader(f):

            #Skip non-mvm map rows:
            if not row[0].startswith("mvm_"):
                continue

            #Grab the total number of waves:
            wave_count = int(row[2])

            #Build the bitflags string.
            #The tour server sets bitflags from 1 << 1 to 1 << n where n is the total waves in a mission.
            #So loop from 1 to n, not 0 to n - 1 (which is the default:
            flags = 0
            for x in range(1, wave_count+1):
                flags |= 1 << x

            #Place the bitflags in the tour list.
            #The flags are in the correct order since the mission index is dependent on the order the mission is listed in the CSV file.
            completed_tour.append(flags)

        #Clean up and exit:
        f.close()
        return completed_tour





#Runs the whole operation:

    def run(self):

        #Grab a list of all the steam IDs of people who successfully completed the tour.
        tour_completionists_steamids = self.get_tour_completionists()

        #Grab a list of all the steam IDs of people who participated in the contest and weren't DQ'd (disqualified) from judging:
        contest_participants_steamids = self.get_contest_participants()

        #Grab a list of all the steam IDs of the winners of the contest:
        contest_winners_steamids = self.get_contest_winners()

        #Merge all of those together:
        medal_recepients = tour_completionists_steamids + contest_participants_steamids + contest_winners_steamids

        #Then for each steam ID, send a HTTP POST request to the steam web API to drop the Titanium Tank Participant Medal into their backpack:
        for steamid in medal_recepients:

            #Build a dictionary containing the post request fields:
            post_fields = {"key":STEAM_WEB_API_KEY, "promoid":ITEM_PROMO_ID, "steamid":steamid}

            #Encode them:
            encoded_post_fields = urlencode(post_fields).encode()

            #Then send the request:
            request = Request("https://api.steampowered.com/ITFPromos_440/GrantItem/v1/", encoded_post_fields)
            try:
                response = urlopen(request)
                print("[{}] Successfully sent medal POST request for: {}".format(response.code, steamid))
            except Exception as e:
                print("Failed to send medal POST request for: {} (reason: {})".format(steamid, e))

        #Done
        print("Done")
            




#Returns a list of steam IDs of people who successfully completed the tour.

    def get_tour_completionists(self):

        #In this list, place the steam IDs of people who completed the tour:
        tour_completionists = list()

        #First, grab ALL the steam IDs of people who participated in the tour:
        steamids = self.db.execute("SELECT DISTINCT Steam64 FROM WaveCredits").fetchall()

        #Per row:
        for row in steamids:

            #Get the steam ID out:
            steamid = row[0]

            #Create a blank tour progress list for this player to start with:
            tour_progress = self.blank_tour_progress.copy()

            #Query for all their wave credits:
            wave_credits = self.db.execute("SELECT MissionIndex, WaveNumber FROM WaveCredits WHERE Steam64 = ?", row)

            #Per wave credit, set the proper bitflag on the tour progress list:
            for (mission_index, wave_number) in wave_credits:
                tour_progress[mission_index] |= 1 << wave_number

            #Compare this list to the completed tour list, and if it matches, add the steam ID to the completionists list:
            if tour_progress == self.completed_tour_list:
                tour_completionists.append(steamid)

        #Done
        return tour_completionists





#Returns a list of steam IDs of people who participated in the contest by submitting a thoughtful, functioning mission:

    def get_contest_participants(self):

        #Store the steam64 IDs of contest participants in this list:
        contest_participants = list()

        #Open the Contest Participants.csv file:
        f = open("Contest Participants.csv", mode="r", encoding="UTF-8")

        #Per row in the CSV file:
        for row in reader(f):

            #If the first cell in the row has a comment symbol, ignore the whole row.
            #DQ'd participants, headers, and comments are ignored.
            cell = row[0]
            if cell.startswith("//"):
                continue

            #The 2nd cell has the steam ID in it, but remove the * and any whitespace.
            #The * was added so that if the csv file was opened and resaved by Excel, the steam IDs aren't numerically truncated.
            steamid = row[1].strip("*").strip()
            contest_participants.append(steamid)

        #Done
        f.close()
        return contest_participants





#Returns a list of steam IDs of the contest winners:

    def get_contest_winners(self):

        #Store the steam64 IDs of contest winners in this list:
        contest_winners = list()

        #Open the Contest Winners.csv file:
        f = open("Contest Winners.csv", mode="r", encoding="UTF-8")

        #Per row in the CSV file:
        for row in reader(f):

            #If the first cell in the row has a comment symbol, ignore the whole row.
            cell = row[0]
            if cell.startswith("//"):
                continue

            #Otherwise, extract the steam ID out:
            steamid = row[0].strip("*").strip()
            contest_winners.append(steamid)

        #Done
        f.close()
        return contest_winners








#Run this program.
if __name__ == "__main__":
    obj = potato()
    obj.run()
