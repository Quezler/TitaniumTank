

from sqlite3 import Connection

db = Connection("mvm_titanium_tank_tour_progress.sq3")
db.execute("CREATE TABLE IF NOT EXISTS WaveCredits (Steam64 Text, TimeStamp Int, MissionIndex Int, WaveNumber Int)")

for x in db.execute("SELECT TimeStamp, MissionIndex, WaveNumber FROM WaveCredits WHERE Steam64 = '76561198071195301'"):
    print(x)
    



