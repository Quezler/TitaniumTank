
/**
 * Test real-time medal drops on the medal server by simulating wave credit reports.
 * This plugin just spams POST requests randomly once every 100 ms to simulate earning wave credits.
 **/


/**
 * Includes
 **/

#include <sourcemod>
#include <SteamWorks>

#pragma semicolon 1
#pragma newdecls required


/**
 * Globals
 **/

// Set TT API key and use the steam ID of the person who's in charge of distributing the medals.
static const char g_SteamID[] = "76561198071195301";
static const char g_AuthKey[] = "todo_insertlegitserverkeyhere";

// This is basically Tour Information.csv, sort of.
static const int g_WaveNumbers[] = {6, 7, 7, 6, 7, 6};

// Handle to the backup CSV file:
File g_BackupCSV;





/**
 * Functions
 **/


// Called on plugin start.

public void OnPluginStart()
{
	// Open the backup CSV file in APPEND mode:
	g_BackupCSV = OpenFile("_tour_progress.csv", "a");
	
	// Create a timer that runs once every 100 ms to spam a POST request:
	CreateTimer(0.1, TTDebug_SpamPostRequest, _, TIMER_REPEAT);
}





// Called once every 100 ms:

public Action TTDebug_SpamPostRequest(Handle timer)
{
	// Pick a random mission:
	int RandomMissionIdx = GetRandomInt(1, sizeof(g_WaveNumbers)) - 1;		// Indices are 0-based, so have to subtract the output by 1
	
	// Pick a random wave for this mission:
	int RandomWave = GetRandomInt(1, g_WaveNumbers[RandomMissionIdx]);
	
	// Get the current time stamp:
	int Time = GetTime();
	
	// Turn them into strings:
	char MissionIdxStr[16], WaveStr[16], TimeStr[16];
	IntToString(RandomMissionIdx, MissionIdxStr, sizeof(MissionIdxStr));
	IntToString(RandomWave, WaveStr, sizeof(WaveStr));
	IntToString(Time, TimeStr, sizeof(TimeStr));
	
	// Then send it to the medal server:
	TTDebug_RecordClientTourProgress(MissionIdxStr, TimeStr, WaveStr);
}





// Called when we want to record a client's tour progress.
// This is called from the timer loop, although if we're genuinely crazy we can call this in OnGameFrame too.

stock void TTDebug_RecordClientTourProgress(const char[] MissionIndexStr, const char[] TimeStampStr, const char[] WaveStr)
{
	// The medal server is running on a port that's not open to the world wide web.
	// We can use localhost to directly connect to it from here, while preventing other community servers from interacting with it.
	// Unfortunately, this locks the medal to our servers only, but it prevents other servers from cheating the medal.
	Handle PostRequest = SteamWorks_CreateHTTPRequest(k_EHTTPMethodPOST, "http://localhost:65432/");
	
	// Even though the tour server is inaccessible outside of localhost, to be safe, pass the unique key to the POST request:
	// THIS IS NOT OUR STEAM WEB API KEY! This is a key as authentication between our MvM servers and the tour progress server.
	SteamWorks_SetHTTPRequestGetOrPostParameter(PostRequest, "key", g_AuthKey);
	
	// Pass the steam ID of the client who completed the wave:
	SteamWorks_SetHTTPRequestGetOrPostParameter(PostRequest, "steam64", g_SteamID);

	// Pass the time that this wave was completed at.
	SteamWorks_SetHTTPRequestGetOrPostParameter(PostRequest, "timestamp", TimeStampStr);

	// Pass the ID of the mission:
	SteamWorks_SetHTTPRequestGetOrPostParameter(PostRequest, "mission", MissionIndexStr);
	
	// Pass the wave number:
	SteamWorks_SetHTTPRequestGetOrPostParameter(PostRequest, "wave", WaveStr);
	
	// Send the request to the tour server.
	SteamWorks_SendHTTPRequest(PostRequest);
	
	// Then write it to the CSV file as an insurance backup record:
	g_BackupCSV.WriteLine("%s,%s,%s,%s", g_SteamID, TimeStampStr, MissionIndexStr, WaveStr);
	
	// Clean up:
	delete PostRequest;
	
	// Log to console for the lulz:
	LogMessage("Sent POST for Mission '%s' Wave '%s'", MissionIndexStr, WaveStr);
}




