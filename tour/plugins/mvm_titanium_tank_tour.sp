
/**
 * =============================================================================
 * Titanium Tank Tour Progress Tracking Plugin
 * Copyright (C) 2018 Potato's MvM Servers.  All rights reserved.
 * =============================================================================
 * 
 * This program is free software; you can redistribute it and/or modify it under
 * the terms of the GNU General Public License, version 3.0, as published by the
 * Free Software Foundation.
 * 
 * This program is distributed in the hope that it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
 * FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
 * 
 * You should have received a copy of the GNU General Public License along with
 * this program.  If not, see <http://www.gnu.org/licenses/>.
 **/

// Records player tour progress on the Titanium Tank Tour.

/**
 * Includes
 **/

#include <sourcemod>
#include <sdktools>

#include <SteamWorks>

#include <tf2_stocks>

#pragma semicolon 1
#pragma newdecls required





/**
 * Globals
 **/


// Globals
bool g_EligiblePlayers[MAXPLAYERS];			// Use this to record who is eligible to earn a wave credit for this tour.
char g_AuthKey[256];						// Authentication key to provide to the tour server for it to honor our progress records.
char g_MapName[64];							// Name of current map
char g_MissionIndexStr[4];					// The mission index, stored as a string
char g_ServerPort[8];						// The server's port number
char g_ServerNumberStr[4];					// Holds the server number (extracted from the hostname cvar).
char g_IsPassworded[4];						// Holds a boolean (as a string) on whether the server is password protected or not.

int g_MaxWaves;								// The most number of waves a mission in this tour has. (Used to print the tour progress table on the client's console.)
int g_ObjRescRef = INVALID_ENT_REFERENCE;	// Entity reference of CTFObjectiveResource (cached for optimization).

// Since the client commands spam a HTTP GET request on the tour server, rate limit the command to once per 30 seconds.
// They do not need to check their tour progress more often than that anyway.
int g_ClientCmdThrottle[MAXPLAYERS];

// Global handles
ArrayList g_MapsList;					// Store each map name in the order set in the csv file so we can map a map name to a mission index.
File g_BackupCSV;						// As a backup in case the tour server shit hits the fan, store the data LOCALLY in a csv file.
StringMap g_MissionWaveCount;			// Stores each map name paired with the number of waves they have.





/**
 * Macros
 **/

// Enable this for troubleshooting.
// #define DEBUG

// Kick message
#define CLIENT_KICK_MESSAGE		"This server is currently full. Please try joining later! Thank you"		// No period since the engine appends one at the end automatically.

// Maximum number of defending MvM players:
#define MAX_MVM_PLAYERS			6

// The number of seconds a client must wait between using plugin commands.
// This helps to protect the tour server from being overloaded with GET requests spam.
#define CLIENT_CMD_COOLDOWN		30





/**
 * Enums
 **/


enum TourDataType
{
	TourData_Invalid = 0,
	TourData_Mission,
	TourData_All
}





/**
 * Plugin Info
 **/


// Plugin information

public Plugin myinfo =
{
	name        = "Titanium Tank Tour Tracker",
	author      = "Hydrogen",
	description = "Records player progress on the Titanium Tank Tour",
	version     = "1.0.0",
	url         = "http://www.sourcemod.net"
};





/**
 * Forwards
 **/


// Called when the plugin is started:

public void OnPluginStart()
{
	// Grab the server's port number. The website server uses this to identify which server is reporting server information.
	GetCommandLineParam("-port", g_ServerPort, sizeof(g_ServerPort), "-1");
	
	// Hook to important events that we can use to track the tour progress:
	HookEvent("mvm_begin_wave", 	TT_OnWaveStart);		// Fired every time a wave starts.
	HookEvent("mvm_wave_complete", 	TT_OnWaveComplete);		// Fired every time a wave finishes.
 	HookEvent("player_team", 		TT_PlayerTeam);			// Fired every time a player changes team.
 	
 	// Initialize global variables from the file system:
 	TT_InitFileSystem();
 	
 	// Debug admin command to troubleshoot the plugin and poke at its namespace:
	#if defined DEBUG
	 	RegAdminCmd("sm_tt_test", 	TT_TestCommand, ADMFLAG_ROOT);
	#endif
 	
 	// Client commands for clients to check their tour progress while in the server.
 	RegConsoleCmd("sm_tt_mission", TT_MissionCommand);		// Displays progress for just that mission.
 	RegConsoleCmd("sm_tt_tour",    TT_TourCommand);			// Displays progress for the whole tour.
  	RegConsoleCmd("sm_tt_url",     TT_UrlCommand);			// Displays a link to the tour website.
  	
  	// Convar change hooks
  	HookConVarChange(FindConVar("hostname"), TT_OnHostnameChange);
  	HookConVarChange(FindConVar("sv_password"), TT_OnPasswordChange);
  	
  	// Create a timer that spins once every 10 seconds to broadcast the server information to the tour website server.
  	// This allows people to easily check for servers that have any slots open:
  	#if defined DEBUG
  		CreateTimer(1.0, TT_ReportServerData, _, TIMER_REPEAT);  	
  	#else
  		CreateTimer(10.0, TT_ReportServerData, _, TIMER_REPEAT);
  	#endif
  	
  	// Init the global strings:
  	strcopy(g_ServerNumberStr, sizeof(g_ServerNumberStr), "-1");		// Will change in the hostname change callback.
  	strcopy(g_IsPassworded, sizeof(g_IsPassworded), "0");				// By default, not passworded.
}





// Called when the map is loaded.

public void OnMapStart()
{
	// Grab the current map:
	GetCurrentMap(g_MapName, sizeof(g_MapName));
	
	// Make it all lowercase:
	for (int i = 0; i < strlen(g_MapName); i++)
		g_MapName[i] = CharToLower(g_MapName[i]);
	
	// Then find the mission index for this map: (Mission index = location in CSV file where the map is at.)
	int MissionIndex = g_MapsList.FindString(g_MapName);
	if (MissionIndex == -1)
		SetFailState("Non-tour map '%s' loaded, Titanium Tank Tour plugin will not run!", g_MapName);
	
	// Turn the mission index into a string and cache it globally, since we use this in a lot of places:
	IntToString(MissionIndex, g_MissionIndexStr, sizeof(g_MissionIndexStr));
}





// Called when a client drops from the server. Set their wave credit eligibility boolean to false:

public void OnClientDisconnect_Post(int iClient)
{
	g_EligiblePlayers[iClient] = false;
	g_ClientCmdThrottle[iClient] = 0;
}





// Called when a client is put into the server. If the server is full, drop them:

public void OnClientPutInServer(int iClient)
{
	if (TT_GetTotalDefendingPlayers() == MAX_MVM_PLAYERS)
		KickClient(iClient, CLIENT_KICK_MESSAGE);
}





// Called when the client passes all the admin checks and is in game.
// Inform them of the server commands available.

public void OnClientPostAdminCheck(int iClient)
{
	// Requested by Octavia
	PrintToChat(iClient, "\x081BFFFFFF[TT] Follow your progress with \x08FFFF00FF!tt_tour \x081BFFFFFFand \x08FFFF00FF!tt_mission \x081BFFFFFFand \x08FFFF00FF!tt_url\x081BFFFFFF. If a wave glitches out, use \x08FFFF00FF!vote_restart_wave\x081BFFFFFF. Enjoy the tour!");
}





// Called when a client tries to join the server.

public bool OnClientConnect(int iClient, char[] RejectMessage, int maxlen)
{
	// For some bizarre reason, bots sometimes trigger this function.
	// Check if this client is a bot. If so, always return true.
	if (IsFakeClient(iClient))
		return true;
	
	// If the server is full, copy the rejection message and return false to drop the client:
	if (TT_GetTotalDefendingPlayers() == MAX_MVM_PLAYERS)
	{
		strcopy(RejectMessage, maxlen, CLIENT_KICK_MESSAGE);
		return false;
	}
	
	// Otherwise, return true to let them in.
	return true;
	
	// NOTE: It is possible for someone to join a server if there are already 6 players connected.
	// This happens if someone joined, got stalled by fastdl or went afk, so that the team can
	// still get a 6th if they don't want to wait for a super slow player to finally connect.
	// 
	// The client can still sit on the server so they can grab all the fastdl contents (so they
	// have the files ready to go the next time they connect on that map), but once they get
	// into the game or pick a class, if there are already 6 players, we drop them from the server.
	// 
	// Players should download and install the tour pack ahead of time to skip the fastdl wait
	// and load into the server as quick as possible.
}





/**
 * Console commands
 **/
 

// Admin debug command. Put whatever in here to troubleshoot the plugin.

#if defined DEBUG

public Action TT_TestCommand(int iClient, int nArgs)
{

}

#endif





// Called when the client wants to see their tour progress on the *current mission*:

public Action TT_MissionCommand(int iClient, int nArgs)
{
	// Check if the client is on cooldown from using these commands.
	// (It has error message reporting built in.)
	if (TT_IsClientOnCooldown(iClient))
		return Plugin_Handled;
	
	// Grab the client's steam ID and this mission's tour index:
	char Steam64[32];
	GetClientAuthId(iClient, AuthId_SteamID64, Steam64, sizeof(Steam64));
	
	// Create a HTTP GET request to the website server to fetch the data for this mission for this client:
	Handle GetRequest = SteamWorks_CreateHTTPRequest(k_EHTTPMethodGET, "http://73.233.9.103:27000/TitaniumTank/VDF/");
	
	// Pass the steam ID of the client who wants their tour progress:
	SteamWorks_SetHTTPRequestGetOrPostParameter(GetRequest, "steam64", Steam64);
	
	// Pass the ID of the mission:
	SteamWorks_SetHTTPRequestGetOrPostParameter(GetRequest, "mission", g_MissionIndexStr);
	
	// Set the callback function to trigger when the request is done:
	SteamWorks_SetHTTPCallbacks(GetRequest, TT_OnGetRequestCompleted);
	
	// Pass the appropriate data to the callback function:
	SteamWorks_SetHTTPRequestContextValue(GetRequest, GetClientUserId(iClient), TourData_Mission);
	
	// Send the request to the tour server.
	SteamWorks_SendHTTPRequest(GetRequest);
	
	// We'll have to finish this up in the callback function:
	return Plugin_Handled;
}





// Called when the client wants to see their *global* tour progress:

public Action TT_TourCommand(int iClient, int nArgs)
{
	// Check if the client is on cooldown from the command:
	if (TT_IsClientOnCooldown(iClient))
		return Plugin_Handled;
	
	// Grab the client's steam ID and this mission's tour index:
	char Steam64[32];
	GetClientAuthId(iClient, AuthId_SteamID64, Steam64, sizeof(Steam64));

	// Create a HTTP GET request to the websiite server to fetch the full tour data:
	Handle GetRequest = SteamWorks_CreateHTTPRequest(k_EHTTPMethodGET, "http://73.233.9.103:27000/TitaniumTank/VDF/");
	
	// Pass the steam ID of the client who wants their tour progress:
	SteamWorks_SetHTTPRequestGetOrPostParameter(GetRequest, "steam64", Steam64);

	// Set the callback function to trigger when the request is done:
	SteamWorks_SetHTTPCallbacks(GetRequest, TT_OnGetRequestCompleted);
	
	// Pass the appropriate data to the callback function:
	SteamWorks_SetHTTPRequestContextValue(GetRequest, GetClientUserId(iClient), TourData_All);
	
	// Send the request to the tour server.
	SteamWorks_SendHTTPRequest(GetRequest);
	
	// Done
	return Plugin_Handled;
}





// Called when the client wants to get a quick URL to their tour website page.

public Action TT_UrlCommand(int iClient, int nArgs)
{
	// Get the client's steam ID:
	char Steam64[32];
	if (!GetClientAuthId(iClient, AuthId_SteamID64, Steam64, sizeof(Steam64)))
	{
		ReplyToCommand(iClient, "[SM] Unable to retrieve your steam ID. Cannot generate progress URL.");
		return Plugin_Handled;
	}
	
	// Build the URL to the tour page and print it to the client:
	ReplyToCommand(iClient, "[TT] Your tour progress can be seen at:\nhttp://73.233.9.103:27000/TitaniumTank/%s", Steam64);
	return Plugin_Handled;
}





/**
 * Command helpers
 **/


// Called when a HTTP GET request is completed.
// This fetches a player's mission progress or global tour data from the tour website server.

public int TT_OnGetRequestCompleted(Handle RequestHandle, bool Failure, bool RequestSuccessful, EHTTPStatusCode StatusCode, int Userid, TourDataType TourType)
{
	// Grab the client index and check validity:
	int iClient = GetClientOfUserId(Userid);
	if (iClient == 0)
		return;
	
	// For some stupid reason, SteamWorks_GetHTTPResponseBodyData doesn't exactly work, so we have to hammer the file system
	// by saving the response data (which is in keyvalues format) to disk, and then load it back in using the keyvalues parser.
	// 
	// (Either that, or SteamWorks_GetHTTPResponseBodyData isn't meant for that purpose... the lack of documentation doesn't help.)
	SteamWorks_WriteHTTPResponseBodyToFile(RequestHandle, "_tour_data.vdf");
	
	// Although SteamWorks requests are threaded and we hammer multiple GET requests at once, because only one thread can ever
	// touch the Sourcepawn VM, there are no race conditions in saving the request data to disk only to load it back in immediately:
	KeyValues kv = new KeyValues("response");
	kv.ImportFromFile("_tour_data.vdf");
	
	// Pass the client index and keyvalue handle to the proper function to display the tour data.
	// 
	// For a mission's progress data, we can print the data one line at a time like how the wave timer works.
	// For the tour's progress data, we need to build a rather large table.
	if (TourType == TourData_Mission)
		TT_PrintMissionProgress(iClient, kv);
	else if (TourType == TourData_All)
		TT_PrintTourProgress(iClient, kv);
	
	// Clean up:
	delete kv;
	delete RequestHandle;
}





// Called when we want to print out a client's progress on a mission:

stock void TT_PrintMissionProgress(int iClient, KeyValues kv)
{
	// Grab the wave completion bitflags of this mission:
	int BitFlags = kv.GetNum(g_MissionIndexStr, 0);
	
	// If the flags are 0, that means no progress has been made:
	if (BitFlags == 0)
	{
		PrintToChat(iClient, "\x081BFFFFFF[TT] You have no recorded progress for this mission.");
		return;
	}
	
	// Get the total number of waves featured in this mission.
	// (Note: Can get this from CTFObjectiveResource, or we can get it from the csv file.)
	int TotalWaves;
	g_MissionWaveCount.GetValue(g_MapName, TotalWaves);
	PrintToChat(iClient, "\x081BFFFFFF[TT] Your progress on %s is shown below:", g_MapName);
	
	// Then loop across those number of waves:
	for (int i = 1; i <= TotalWaves; i++)
	{
		// If they have this wave completed, then use "OK". Otherwise, use "Missing".
		if (BitFlags & 1 << i)
			PrintToChat(iClient, "\x081BFFFFFFWave %d: \x0858ED8CFFOK", i);
		else
			PrintToChat(iClient, "\x081BFFFFFFWave %d: \x08FF8C8CFFMissing", i);
	}	
}





// Called when we want to print out a client's global tour progress.

stock void TT_PrintTourProgress(int iClient, KeyValues kv)
{
	// Build the header to the client first:
	static char Buffer[256];
	strcopy(Buffer, sizeof(Buffer), "Mission:\t\t");
	for (int i = 1; i <= g_MaxWaves; i++)
		Format(Buffer, sizeof(Buffer), "%sW%d\t", Buffer, i);
	
	// Print that out first:
	PrintToChat(iClient, "\x081BFFFFFF[TT] Your tour progress is shown in the console.");
	PrintToConsole(iClient, Buffer);
	
	// Per number of missions:
	char MapName[64], MissionIndexStr[4];
	int TotalMissions = g_MapsList.Length;
	for (int i = 0; i < TotalMissions; i++)
	{
		// Get the map name:
		g_MapsList.GetString(i, MapName, sizeof(MapName));
		
		// Turn the mission index for this mission and turn it into a string:
		IntToString(i, MissionIndexStr, sizeof(MissionIndexStr));
		
		// Grab the bitflags for that mission:
		int BitFlags = kv.GetNum(MissionIndexStr, 0);
		
		// Get the total number of waves featured in this mission.
		int TotalWaves;
		g_MissionWaveCount.GetValue(MapName, TotalWaves);
		
		// Insert the map name in:
		strcopy(Buffer, sizeof(Buffer), MapName);
		int NumTabs = strlen(MapName) > 15 ? 1 : 2;
		for (int j = 0; j < NumTabs; j++)
			StrCat(Buffer, sizeof(Buffer), "\t");
		
		// Build the row body:
		for (int j = 1; j <= TotalWaves; j++)
			if (BitFlags & 1 << j)
				Format(Buffer, sizeof(Buffer), "%sOK\t", Buffer);
			else
				Format(Buffer, sizeof(Buffer), "%s?\t", Buffer);
		
		// And print out the whole row:
		PrintToConsole(iClient, Buffer);
	}
}





/**
 * Cvar hooks
 **/


// Called every time the hostname cvar on the server is changed.
// This should only ever be called once, and on server startup. We want to determine the server number of this server.
// We can get this from the hostname string, which has something like "Server #x" on it. We need the value of x.

public void TT_OnHostnameChange(ConVar CvarHandle, const char[] OldValue, const char[] NewValue)
{
	// Build the server number in this string here:
	char ServerNumber[4]; 			// Not going to host more than 1000 servers....
	
	// Find where the # is. If not found, abort:
	int Idx = FindCharInString(NewValue, '#');
	if (Idx == -1)
		return;
	
	// Move that index up by 1. Now the index should point to a digit value:
	++Idx;
	
	// From that index, up to the full length of the string, only slap in numerical characters:
	int index;
	for (int i = Idx; i < strlen(NewValue); i++)
	{
		// If we find a NON-numerical character, break out:
		if (!IsCharNumeric(NewValue[i]))
			break;
		
		// Otherwise, put it into the string:
		ServerNumber[index] = NewValue[i];
		++index;
	}
	
	// Null-terminate:
	ServerNumber[index] = 0;
	
	// Save it globally:
	strcopy(g_ServerNumberStr, sizeof(g_ServerNumberStr), ServerNumber);
}





// Called everytime the password is changed.

public void TT_OnPasswordChange(ConVar CvarHandle, const char[] OldValue, const char[] NewValue)
{
	// If it is an empty string, set it to 0 (no password).
	if (StrEqual(NewValue, ""))
		strcopy(g_IsPassworded, sizeof(g_IsPassworded), "0");
	
	// Otherwise, set it to 1 (there is a password).
	else
		strcopy(g_IsPassworded, sizeof(g_IsPassworded), "1");
}





/**
 * Event hooks
 **/


// Called when a client joins a team.

public Action TT_PlayerTeam(Event hEvent, const char[] EventName, bool DontBroadcast)
{
	// Grab the client and the team they are switching to:
	int iClient = GetClientOfUserId(hEvent.GetInt("userid"));
	
	// If the client is a bot, ignore it:
	if (IsFakeClient(iClient))
		return;
	
	// Grab the team they are switching to:
	TFTeam Team = view_as<TFTeam>(hEvent.GetInt("team"));
//	TFTeam OldTeam = view_as<TFTeam>(hEvent.GetInt("oldteam"));			// Don't think this is necessary - leaving it in anyway for future reference.

	// If it's spectator, drop the client. Spectators are not allowed.
	if (Team == TFTeam_Spectator)
		KickClient(iClient, CLIENT_KICK_MESSAGE);
}





// Called everytime a wave starts. Init the eligible players array.

public Action TT_OnWaveStart(Event hEvent, const char[] EventName, bool DontBroadcast)
{
	// Check if the team is full:
	bool FullTeam = TT_GetTotalDefendingPlayers() == MAX_MVM_PLAYERS;
	
	// Per client:
	for (int i = 1; i <= MaxClients; i++)
	{
		// Set the eligible players array:
		g_EligiblePlayers[i] = TT_IsValidPlayer(i);
		
		// If we don't have a full team, move on:
		if (!FullTeam)
			continue;
		
		// If this client is not in game or is a bot, skip:
		if (!IsClientInGame(i) || IsFakeClient(i))
			continue;
		
		// If this client is not on team RED, but they are in game (i.e. not stuck on fastdl),
		// sitting on the MOTD or somehow they got into spectator, drop them from the server:
		// 
		// This only happens if we have a full team of players on the server already.
		if (TF2_GetClientTeam(i) != TFTeam_Red)
			KickClient(i, CLIENT_KICK_MESSAGE);
	}
}





// Called when the wave is finished. Check if the players have *rightfully* completed the wave.

public Action TT_OnWaveComplete(Event hEvent, const char[] EventName, bool DontBroadcast)
{
	// Get the wave number and current timestamp:
	int WaveNumber   = TT_GetCurrentWave();
	int TimeStamp    = GetTime();
	
	// Turn them all into strings:
	char WaveNumberStr[4], TimeStampStr[32], Steam64[32];
	IntToString(WaveNumber, WaveNumberStr, 	sizeof(WaveNumberStr));
	IntToString(TimeStamp, 	TimeStampStr, 	sizeof(TimeStampStr));

	// Per client:
	for (int i = 1; i <= MaxClients; i++)
	{
		// Check client validity:
		if (!TT_IsValidPlayer(i))
			continue;

		// If they had their eligibility voided, skip:
		if (!g_EligiblePlayers[i])
			continue;
		
		// Grab the client's steam ID:
		if (!GetClientAuthId(i, AuthId_SteamID64, Steam64, sizeof(Steam64)))		// If it returns false, client isn't authenticated
			continue;
		
		// Send a POST request to the tour server recording the client's progress, and record it in our local csv file.
		TT_RecordClientTourProgress(i, Steam64, TimeStampStr, WaveNumberStr);
	}
}





/**
 * Timer callbacks
 **/


// Called 1 second after server.cfg has been executed.
// Grab the server number from the name of the server and store it globally.

public Action TT_OnConfigsExecutedDelay(Handle timer)
{
	// Sourcemod weirdness: Server name can be retrieved from client index 0 to GetClientName.
	char ServerName[256];
	GetClientName(0, ServerName, sizeof(ServerName));
	
	// Split along the #:
	// Assumption: We're assuming servers are named like Server #1, #2, ... otherwise this will fail badly.
	char SplitStr[2][4];
	ExplodeString(ServerName, "#", SplitStr, sizeof(SplitStr), sizeof(SplitStr[]));
	
	// Try turning this into an integer. If it fails, exit early:
	if (StringToInt(SplitStr[1]) == 0)
	{
		LogError("Warning: Server name '%s' is missing a server number!");
		return;
	}
	
	// Otherwise, store this value globally.
	strcopy(g_ServerNumberStr, sizeof(g_ServerNumberStr), SplitStr[1]);
}





// Called once every 10 seconds.
// 
// Report server data to the tour server so clients can check on the tour servers' status.
// This information is displayed on the server information page on the tour server website.

public Action TT_ReportServerData(Handle timer)
{
	// Get the number of players on RED and number of players connecting:
	int DefendingPlayers, ConnectingPlayers;
	for (int i = 1; i <= MaxClients; i++)
	{
		// Skip non-connected clients and bots:
		if (!IsClientConnected(i) || IsFakeClient(i))
			continue;
		
		// Increment the proper counter:
		if (IsClientInGame(i) && TF2_GetClientTeam(i) == TFTeam_Red)
			++DefendingPlayers;
		else
			++ConnectingPlayers;
	}
	
	// Grab the round status:
	int Status = view_as<int>(GameRules_GetRoundState());
	
	// Get the current wave number:
	int CurrentWave = TT_GetCurrentWave();											// NOTE: This will return 0 if CPopulationManager is not initialized.
	
	// Turn them into strings:
	char DefendingStr[4], ConnectingStr[4], RoundStr[4], WaveStr[4];
	IntToString(DefendingPlayers, DefendingStr, sizeof(DefendingStr));
	IntToString(ConnectingPlayers, ConnectingStr, sizeof(ConnectingStr));
	IntToString(Status, RoundStr, sizeof(RoundStr));
	IntToString(CurrentWave, WaveStr, sizeof(WaveStr));
	
	// Create a HTTP POST request to the tour website server:
	Handle PostRequest = SteamWorks_CreateHTTPRequest(k_EHTTPMethodPOST, "http://73.233.9.103:27000/TitaniumTank/Servers/");
	
	// Pass the Titanium Tank API key to the POST request.
	// This is required, so that the website server knows that this is a legitimate Titanium Tank Tour server.
	SteamWorks_SetHTTPRequestGetOrPostParameter(PostRequest, "key", g_AuthKey);
	
	// Pass the server number:
	SteamWorks_SetHTTPRequestGetOrPostParameter(PostRequest, "number", g_ServerNumberStr);

	// Pass the mission index, wave number, and round state:
	SteamWorks_SetHTTPRequestGetOrPostParameter(PostRequest, "mission", g_MissionIndexStr);
	SteamWorks_SetHTTPRequestGetOrPostParameter(PostRequest, "wave", WaveStr);
	SteamWorks_SetHTTPRequestGetOrPostParameter(PostRequest, "roundstate", RoundStr);

	// Pass the number of defending players and connecting players:
	SteamWorks_SetHTTPRequestGetOrPostParameter(PostRequest, "defenders", DefendingStr);
	SteamWorks_SetHTTPRequestGetOrPostParameter(PostRequest, "connecting", ConnectingStr);
	
	// Pass the password-protected boolean:
	SteamWorks_SetHTTPRequestGetOrPostParameter(PostRequest, "haspassword", g_IsPassworded);

	// Pass the server port number:
	SteamWorks_SetHTTPRequestGetOrPostParameter(PostRequest, "port", g_ServerPort);
	
	// Send the request to the website server:
	SteamWorks_SendHTTPRequest(PostRequest);
	
	// Clean up:
	delete PostRequest;
}





/**
 * Helper stocks
 **/


// Called during plugin start. Load from the input CSV file and open the tour progress file.

stock void TT_InitFileSystem()
{
	// Create our map names adt_array and trie:
	g_MapsList 			= new ArrayList(64);
	g_MissionWaveCount 	= new StringMap();
	
	// Open the input CSV file first:
	File csv = OpenFile("Tour Information.csv", "r");
	if (csv == null)
		SetFailState("Tour information CSV file not found! Plugin will not run!");
	
	// Per file line:
	char FileLine[256], SplitStr[3][128];
	while (csv.ReadLine(FileLine, sizeof(FileLine)))
	{
		// Split the string along the commas:
		ExplodeString(FileLine, ",", SplitStr, sizeof(SplitStr), sizeof(SplitStr[]));
		
		// If the first value is a key then store it globally:
		if (StrEqual(SplitStr[0], "apikey", false))
			strcopy(g_AuthKey, sizeof(g_AuthKey), SplitStr[1]);
		
		// If the name begins with mvm_, then put the map name into the array.
		// Be sure to remove whitespace from the map name and make it completely lowercase.
		else if (StrContains(SplitStr[0], "mvm_", false) == 0)
			TT_AddMapToList(SplitStr[0], SplitStr[2]);
	}
	
	// Close the tour information CSV file (done with it).
	delete csv;
	
	// Trim the auth key string of any whitespace, if any exists:
	TrimString(g_AuthKey);
	
	// Open the local tour progress CSV file and hold on to its handle forever.
	// Open it in append mode so that new writes add to the end of the file.
	g_BackupCSV = OpenFile("_tour_progress.csv", "a");
}





// Returns the wave number of the wave that was just completed.

stock int TT_GetCurrentWave()
{
	// Grab the objective resource entity from the entity reference:
	int CTFObjectiveResource = EntRefToEntIndex(g_ObjRescRef);
	
	// If that failed, find the new entity and cache its reference:
	if (CTFObjectiveResource == INVALID_ENT_REFERENCE)
	{
		CTFObjectiveResource = FindEntityByClassname(-1, "tf_objective_resource");
		g_ObjRescRef = EntIndexToEntRef(CTFObjectiveResource);
	}
	
	// Get the current wave number from the objective resource entity:
	return GetEntProp(CTFObjectiveResource, Prop_Send, "m_nMannVsMachineWaveCount"); 		// this is x in WAVE x/y
}





// Called when we want to record a client's tour progress.

stock void TT_RecordClientTourProgress(int iClient, const char[] Steam64, const char[] TimeStampStr, const char[] WaveStr)
{
	// The medal server is running on a port that's not open to the world wide web.
	// We can use localhost to directly connect to it from here, while preventing other community servers from interacting with it.
	// Unfortunately, this locks the medal to our servers only, but it prevents other servers from cheating the medal.
	Handle PostRequest = SteamWorks_CreateHTTPRequest(k_EHTTPMethodPOST, "http://localhost:65432/");
	
	// Even though the tour server is inaccessible outside of localhost, to be safe, pass the unique key to the POST request:
	// THIS IS NOT OUR STEAM WEB API KEY! This is a key as authentication between our MvM servers and the tour progress server.
	SteamWorks_SetHTTPRequestGetOrPostParameter(PostRequest, "key", g_AuthKey);
	
	// Pass the steam ID of the client who completed the wave:
	SteamWorks_SetHTTPRequestGetOrPostParameter(PostRequest, "steam64", Steam64);

	// Pass the time that this wave was completed at.
	SteamWorks_SetHTTPRequestGetOrPostParameter(PostRequest, "timestamp", TimeStampStr);

	// Pass the ID of the mission:
	SteamWorks_SetHTTPRequestGetOrPostParameter(PostRequest, "mission", g_MissionIndexStr);
	
	// Pass the wave number:
	SteamWorks_SetHTTPRequestGetOrPostParameter(PostRequest, "wave", WaveStr);
	
	// Send the request to the tour server.
	SteamWorks_SendHTTPRequest(PostRequest);
	
	// Then write it to the CSV file as an insurance backup record:
	g_BackupCSV.WriteLine("%s,%s,%s,%s", Steam64, TimeStampStr, g_MissionIndexStr, WaveStr);
	
	// Notify the client:
	PrintToChat(iClient, "\x081BFFFFFF[TT] Your progress on this wave has been recorded.");
	
	// Log to console, just to be safe again:
	LogMessage("%L received a wave credit on mission %s and wave %s.", iClient, g_MissionIndexStr, WaveStr);
	
	// Clean up:
	delete PostRequest;
}





// Returns true if the client is on cooldown from using a command, false otherwise.

stock bool TT_IsClientOnCooldown(int iClient)
{
	// Get the current time right now:
	int CurrentTime = GetTime();
	
	// Subtract it from the cached timestamp to determine if the client is on cooldown:
	int RemainingTime = g_ClientCmdThrottle[iClient] - CurrentTime;
	if (RemainingTime > 0)			// still on cooldown (has to keep waiting more)
	{
		ReplyToCommand(iClient, "[TT] You cannot use this command for %d more seconds.", RemainingTime);
		return true;
	}
	
	// Otherwise, set the cooldown on the client and return false:
	g_ClientCmdThrottle[iClient] = CurrentTime + CLIENT_CMD_COOLDOWN;
	return false;
}





// Adds a map name to the list:

stock void TT_AddMapToList(const char[] MapName, const char[] WaveCount)
{
	// Make the string all lowercase:
	int Length = strlen(MapName);
	char[] LowerMapName = new char[Length];
	for (int i = 0; i < Length; i++)
		LowerMapName[i] = CharToLower(MapName[i]);
	
	// Trim it:
	TrimString(LowerMapName);
	
	// Push it to the array:
	g_MapsList.PushString(LowerMapName);
	
	// Turn the wave string into an integer, and store it
	// globally if it's the mission with the most waves:
	int TotalWaves = StringToInt(WaveCount);
	if (TotalWaves > g_MaxWaves)
		g_MaxWaves = TotalWaves;
	
	// Put this map name and the wave number into the string map:
	g_MissionWaveCount.SetValue(LowerMapName, TotalWaves);
}





// Returns the total number of defending players on RED:

stock int TT_GetTotalDefendingPlayers()
{
	int Players;
	for (int i = 1; i <= MaxClients; i++)
		if (TT_IsValidPlayer(i))
			++Players;
	return Players;
}





// Returns true if the client is a player on team RED, false otherwise.

stock bool TT_IsValidPlayer(int iClient)
{
	// Client not in game (still connecting, not even connected, etc)
	if (!IsClientInGame(iClient))
		return false;
	
	// Bots
	if (IsFakeClient(iClient))
		return false;
	
	// Non-RED players
	if (TF2_GetClientTeam(iClient) != TFTeam_Red)
		return false;
	
	// If we get here, assume valid player.
	return true;
}




