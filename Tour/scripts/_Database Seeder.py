
from csv import reader
from sqlite3 import Connection
from random import randint
from time import time

#Init
time_gap = 30*24*60*60
current_time = time()
steamid = 76561198071195301

#Open database, wipe everything out.
db = Connection("mvm_titanium_tank_tour_progress.sq3")
db.execute("CREATE TABLE IF NOT EXISTS WaveCredits (Steam64 Text, TimeStamp Int, MissionIndex Int, WaveNumber Int)")
db.execute("DELETE FROM WaveCredits")

#Open CSV file, load data in:
wave_counts = list()
with open("Tour Information.csv") as f:
    for x in reader(f):
        if x[0].startswith("mvm_"):
            wave_counts.append(int(x[2]))

#Seed database:
for (x,y) in enumerate(wave_counts):
    for z in range(1, y+1):
        if randint(0, 1):
            timer = current_time + int(randint(-1*time_gap, time_gap))
            db.execute("INSERT INTO WaveCredits (Steam64, TimeStamp, MissionIndex, WaveNumber) VALUES (?, ?, ?, ?)", (str(steamid), timer, x, z))
            

#Commit and exit:
db.commit()
db.close()

