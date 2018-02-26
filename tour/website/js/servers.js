
/**
 * =============================================================================
 * Titanium Tank Tour Servers Webpage
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

// Roundstate enum:
const g_RoundState = ["Init", "Waiting", "Start Game", "Preround", "In-Wave", "Wave Lost", "Restart", "Stalemate", "Game Won", "Bonus", "Setup"];

// Map names:
const g_MapNames =  ["Dockyard", "Downtown", "Powerplant", "Steep", "Teien", "Waterfront"];





// Once the document fully finishes loading, call our main function.
document.addEventListener('DOMContentLoaded', get_server_data);





// Called after the browser loads the page.

function get_server_data()
{
	// Perform a GET request for the server data:
	http_get_async("http://"  + get_server_ip_address() + "/TitaniumTank/servers.csv", build_server_table);
}





// Called after the tour progress server sends the player tour progress data:

function build_server_table(csv_data)
{
	// Split the data along newlines to get the rows first:
	var rows = csv_data.trim().split("\n");
	
	// The first row is the time stamp of the current time on the server.
	var server_time = Number(rows[0]);
	
	// Take the rest of the rows and *sort* them by player count and map name.
	// This will display the servers list in a format that is beneficial to all players.
	var sorted_server_data = sort_server_data(rows);
	
	// From the server's timestamp, get the current timestamp and determine by how many seconds we have to offset
	// the server's timestamps by to display the time stamps at the client's time zone:
	var current_time = Math.floor(Date.now()/1000);
	var time_zone_difference = current_time - server_time;
	
	// Init the table:
	var table = ['<table class="server_main_table">\
				<tr><th><img src="https://hydrogen-mvm.github.io/TitaniumTank/img/lock.png"/></th>\
				<th>Server Name</th>\
				<th>Current Map</th>\
				<th>Players</th>\
				<th>Wave</th>\
				<th>Round Status</th>\
				<th>Link</th>\
				<th>Last updated</th></tr>'];
	
	// Per row:
	for (var i = 0; i < sorted_server_data.length; i++)
	{
		// Grab the row object:
		var row = sorted_server_data[i];
		
		// Extract the values:
		var server_number 		= row[0];
		var is_passworded 		= row[1];
		var map_index 	  		= row[2];
		var connected_players	= row[3];
		var connecting_players	= row[4];
		var wave_number 		= row[5];
		var total_waves 		= row[6];
		var roundstate_enum 	= row[7];
		var server_ip 			= row[8];
		var server_port 		= row[9];
		var last_updated_time 	= row[10]
		
		// First column is if the server is password protected or not:
		if (is_passworded === 1)
		{
			table.push('<tr><td><p style="text-align:center;"><img src="https://hydrogen-mvm.github.io/TitaniumTank/img/lock.png"/></p></td>');
		}
		else
		{
			table.push('<tr><td></td>');
		}

		// Second piece of data is the server name:
		table.push('<td><p style="text-align:center;">Titanium Tank Server #' + server_number + '</p></td>');
		
		// Third is the map name:
		table.push('<td><p style="text-align:center;"><font color="#00FFFF">' + g_MapNames[map_index] + '</font></p></td>');
		
		// Next up is the players connected count.
		
		// If the server has 6 players connected or connecting to it, make the player color text green.
		// Otherwise, make it yellow, so that at-a-glance players can see which servers are vacant.
		var total_players = connected_players + connecting_players;
		var color_string;
		if (total_players === 0)
			color_string = "#F8A5A9";	// Empty server = red
		else if (total_players >= 6)
			color_string = "#00FF00";	// Full server = green
		else
			color_string = "#FFFF00";	// Partially full server = yellow.
		
		// If we have players CONNECTING then use the [+x] box to denote who is connecting.
		// Don't lump them into the total player count until they join RED, since other people can still get in until there are 6 RED players.
		if (connecting_players > 0)
		{
			table.push('<td><p style="text-align:center;"><font color="{0}">{1} / 6 [+{2}]</font></p></td>'.format(color_string, connected_players, connecting_players));			
		}
		else
		{
			table.push('<td><p style="text-align:center;"><font color="{0}">{1} / 6</font></p></td>'.format(color_string, connected_players));
		}
		
		// Next two is for the wave number:
		table.push('<td><p style="text-align:center;">{0} / {1}</td>'.format(wave_number, total_waves));
		
		// The round status:
		table.push('<td><p style="text-align:center;">' + g_RoundState[roundstate_enum] + '</p></td>');

		// IP address to connect to the server.
		table.push('<td><p style="text-align:center;"><a href="steam://connect/' + "{0}:{1}".format(server_ip, server_port) + '"><font color="#FFFF00">Connect</font></a></p></td>');
		
		// Updated string.
		// Convert the server's time into the user's time:
		var local_time = last_updated_time + time_zone_difference;
		
		// Grab the time string (not the date string):
		var d = new Date(local_time*1000);
		var time_str = d.toLocaleTimeString();
		
		// Grab the number of seconds between now and then 
		var seconds_ago = current_time - local_time;
		
		// Add it to the table and close the row:
		table.push('<td><p style="text-align:center;">' + time_str + '<br/>(' + String(seconds_ago) + ' sec ago)</p></td></tr>');
	}
	
	// Close the table:
	table.push("</table>");
	
	// Insert it into the page:
	document.getElementById('server_table').innerHTML = table.join("");
	
	// Insert the current timestamp as the last-queried time into the page:
	var d = new Date();
	document.getElementById('server_last_update_time').innerHTML = '<p style="text-align:center;"><i>Server info last queried on</i><br/><b>' + d.toLocaleDateString() + ' ' +  d.toLocaleTimeString() + '</b></p>'
}





// Sorts the given server data by player count and 

function sort_server_data(rows)
{
	// First, group the data into 3 places:
	var full_servers = [];		// Full servers
	var empty_servers = [];		// Empty servers
	var partial_servers = [];	// Partially filled servers
	var locked_servers = [];	// Locked servers
	
	// Per row in the data set:
	for (var i = 1; i < rows.length; i++)
	{
		// Split the data up:
		var split_data = rows[i].split(",");
		
		// Convert relevant values into integers:
		split_data[1] = Number(split_data[1]);		// Is passworded
		split_data[2] = Number(split_data[2]);		// Map number
		split_data[3] = Number(split_data[3]);		// ConnectED players
		split_data[4] = Number(split_data[4]);		// ConnectING players
		split_data[5] = Number(split_data[5]);		// Wave number
		split_data[10] = Number(split_data[10]);	// Last updated timestamp
		
		// If the server is locked, then put the server information in the locked array and move on.
		if (split_data[1] === 1)
		{
			locked_servers.push(split_data);
			continue;
		}
		
		// Grab the total number of players:
		var total_players = split_data[3] + split_data[4];
		
		// Based on this value, put the entire row in the appropriate array:
		if (total_players >= 6)
			full_servers.push(split_data);
		else if (total_players === 0)
			empty_servers.push(split_data);
		else
			partial_servers.push(split_data);
	}
	
	// Now sort each array based on the number of players, map name, and wave number.
	full_servers.sort(server_sort_callback);
	empty_servers.sort(server_sort_callback);
	partial_servers.sort(server_sort_callback);
	locked_servers.sort(server_sort_callback);
	
	// Merge all the arrays together:
	var everything = partial_servers.concat(empty_servers).concat(full_servers).concat(locked_servers);
	return everything;
}





// Sorts the given array of server information.
// Return 1 if x > y, -1 if x < y, 0 if x = y.

function server_sort_callback(row1, row2)
{
	// Compare player numbers first:
	var totalplayers_1 = row1[3] + row1[4];
	var totalplayers_2 = row2[3] + row2[4];
	
	if (totalplayers_1 > totalplayers_2)		// Sort in reverse order (high->low)
		return -1;
	if (totalplayers_2 > totalplayers_1)
		return 1;
	
	// Otherwise, compare by wave number.
	if (row1[5] > row2[5])						// Sort in reverse order (high->low)
		return -1;
	if (row2[5] > row1[5])
		return 1;
	
	// They both are equal.
	return 0;
}




