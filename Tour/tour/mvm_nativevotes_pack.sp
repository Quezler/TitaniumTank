
/**
 * =============================================================================
 * Titanium Tank Tour Vote Restart Wave Plugin
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

// Adds a command, !vote_wave_restart, to allow players to vote to restart the current wave.
// 
// Useful in emergency situations if a map breaks or if people just want to try the wave again.
// 
// Requires https://github.com/powerlord/sourcemod-nativevotes

/**
 * Includes
 **/

#include <sourcemod>
#include <sdktools>

#include <nativevotes>
#include <subnativevotes>





/**
 * Plugin Info
 **/


// Plugin information

public Plugin myinfo =
{
	name        = "Vote To Restart Wave",
	author      = "Benoist3012",
	description = "Adds a command that allows players to vote to restart the current wave.",
	version     = "1.0.0",
	url         = "http://www.sourcemod.net"
};





/**
 * Functions
 **/


// Called on plugin start.

public void OnPluginStart()
{
	RegConsoleCmd("sm_vote_restart_wave", 	Command_VoteWaveRestart);
	RegConsoleCmd("sm_fuck_go_back", 		Command_VoteWaveRestart);				// Requested by JugadorXEl
	RegConsoleCmd("sm_restart", 			Command_VoteWaveRestart);
	SubNativeVotes_Initialize();
}





// Called when someone runs the restart wave command:

public Action Command_VoteWaveRestart(int iClient, int iArgs)
{
	// Check cooldown
	if (!NativeVotes_IsNewVoteAllowed())
	{
		int seconds = NativeVotes_CheckVoteDelay();
		PrintCenterText(iClient, "Vote is not allowed for %d more seconds.", seconds);
		PrintToChat(iClient, "\x081BFFFFFF[TT] This vote cannot be called for \x08FFFF00FF%d \x081BFFFFFFmore seconds.", seconds);
		return Plugin_Handled;
	}
	
	// Check if a vote is in progress
	if (NativeVotes_IsVoteInProgress())
	{
		PrintCenterText(iClient, "A vote is already in progress.");
		PrintToChat(iClient, "\x081BFFFFFF[TT] A vote is already in progress.");
		return Plugin_Handled;
	}
	
	// Cannot vote to restart wave if the wave isn't even running!
	if (GameRules_GetRoundState() != RoundState_RoundRunning)
	{
		PrintCenterText(iClient, "This vote can only be called during a wave.");
		PrintToChat(iClient, "\x081BFFFFFF[TT] This vote can only be called during a wave.");
		return Plugin_Handled;
	}
	
	// Create the vote
	Handle hVote = NativeVotes_Create(NativeVotes_RestartWave, NativeVotesType_Custom_YesNo);
	
	SubNativeVotes_InitializeVote(iClient);
	NativeVotes_SetInitiator(hVote, iClient);
	NativeVotes_SetDetails(hVote, "Should the wave be restarted?");			// Tweak the wording so it doesn't sound similar to "Restart game?" which is mission restart.
	PrintToChatAll("\x081BFFFFFF[TT] \x08FFFF00FF%N \x081BFFFFFFcalled a vote to restart the current wave.", iClient);
	
	NativeVotes_DisplayToAll(hVote, 20);
	return Plugin_Handled;
}





// Called after a vote takes place.

public int NativeVotes_RestartWave(Handle hVote, MenuAction action, int param1,int param2)
{
	switch (action)
	{
		case MenuAction_End:
		{
			delete hVote;
		}
		
		case MenuAction_VoteCancel:
		{
			if (param1 == VoteCancel_NoVotes)
			{
				NativeVotes_DisplayFail(hVote, NativeVotesFail_NotEnoughVotes);
			}
			else
			{
				NativeVotes_DisplayFail(hVote, NativeVotesFail_Generic);
			}
		}
		case MenuAction_VoteEnd:
		{
			//Collect the yes/no votes and pick the winner!
			int iResult = SubNativeVotes_PickWinnerYesNo();
			if (iResult == NATIVEVOTES_VOTE_YES)
			{
				NativeVotes_DisplayPass(hVote, "Restarting wave...");
				PrintToChatAll("\x081BFFFFFF[TT] Restarting wave...");
				ForceWaveRestart();
			}
			else if (iResult == NATIVEVOTES_VOTE_NO)
				NativeVotes_DisplayFail(hVote, NativeVotesFail_Loses);
			else
				NativeVotes_DisplayFail(hVote, NativeVotesFail_NotEnoughVotes);
		}
	}
}





// Forces the BLU team to win and makes the wave restart.

stock void ForceWaveRestart()
{
	// Typically firing boss_deploy_relay will do the job.
	int iEnt = -1;
	char RelayName[64];
	while ((iEnt = FindEntityByClassname(iEnt, "logic_relay")) != -1)
	{
		GetEntPropString(iEnt, Prop_Data, "m_iName", RelayName, sizeof(RelayName));
		if (StrEqual(RelayName, "boss_deploy_relay"))
		{
			AcceptEntityInput(iEnt, "Trigger");		// Equal to: ent_fire boss_deploy_relay Trigger
			return;
		}
	}
	
	// If that didn't work, find the game_round_win entity:
	iEnt = FindEntityByClassname(-1, "game_round_win");
	if (iEnt == -1)
		iEnt = CreateEntityByName("game_round_win");
	
	// Set the team to be BLU:
	SetVariantInt(3);
	AcceptEntityInput(iEnt, "SetTeam");
	
	// Force BLU victory:
	AcceptEntityInput(iEnt, "RoundWin");
}




