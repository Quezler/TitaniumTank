
/**
 * =============================================================================
 * Titanium Tank Tour Individual Tour Progress Webpage
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

// Map & mission names
const g_TourMissions = [["Dockyard", "Spyware Shipping"],
						["Downtown", "Entertainer's Entourage"],
						["Powerplant", "Power Palliative"],
						["Steep", "Peak Performance"],
						["Teien", "Program Seppuku"],
						["Waterfront", "Watershed Waylay"],
						];


// Once the document fully finishes loading, call our main function.
document.addEventListener('DOMContentLoaded', get_user_data);				// https://stackoverflow.com/a/33722566





// Called after the browser loads the page.

function get_user_data()
{
	// Grab the current URL of this page and split along the /:
	var url = window.location.href.split("/");								//  https://stackoverflow.com/a/1034642
	
	// We want the last element of the URL, which gives us the steam ID of the user to get the tour data of:
	// While we're here, also get the IP address of the web server.
	var steamid = url[url.length - 1];
	var server_ip = url[2];					// From get_server_ip_address()
	
	// Then perform a GET request for that data:
	var user_data_url = "http://{0}/TitaniumTank/{1}.csv".format(server_ip, steamid);
	http_get_async(user_data_url, build_progress_table);
}





// Called after the tour progress server sends the player tour progress data:

function build_progress_table(csv_data)
{
	// Split the data along newlines to get the rows first:
	var rows = csv_data.split("\n");
	
	// The first row contains the server timestamp, the total wave credits available, and most waves a mission has:
	var row1 = rows[0].split(",");
	var server_time = Number(row1[0]);
	var total_credits = Number(row1[1]);
	var max_waves = Number(row1[2]);
	
	// First, the top (big) table needs to be generated.
	var return_data = generate_top_table(rows, server_time, max_waves);
	var earned_credits = return_data[0];
	var credits_array  = return_data[1];
	
	// Next, build the table on the bottom left that displays the most recently acquired wave credits.
	generate_left_table(credits_array);
	
	// Lastly, generate the bottom right table (overall stats).
	generate_right_table(earned_credits, total_credits);
}





// Generates the HTML for the wave credits table (top table).

function generate_top_table(rows, server_time, max_waves)
{
	// From the server's timestamp, get the current timestamp and determine by how many seconds we have to offset
	// the server's timestamps by to display the time stamps at the client's time zone:
	var current_time = Math.floor(Date.now()/1000);
	var time_zone_difference = current_time - server_time;
	
	// Store the number of wave credits this player has earned in here:
	var earned_credits = 0;
	
	// Store all the wave credits earned by the player in this array.
	// We will use this to generate the bottom left corner table in another function.
	var all_wave_credits = [];
	
	// Create the table header first:
	var table = generate_top_table_header(max_waves);
	
	// For each row after that:
	for (var i = 1; i < rows.length; i++)
	{
		// Push a new row tag:
		table.push("<tr>");
		
		// Break it apart along the commas:
		var cells = rows[i].split(",");
		
		// Grab the map & mission name:
		var mission_data = g_TourMissions[i-1];
		var map_name = mission_data[0];
		var mission_name = mission_data[1];
		
		// Push that information to the table as well:
		table.push('<td><font color="#00FFFF"><b>{0}</b></font><br/><font color="#FFFF00"><i>({1})</i></font></td>'.format(map_name, mission_name));
		
		// Per cell:
		for (var j = 0; j < cells.length; j++)
		{
			// Convert it into a number:
			var value = Number(cells[j]);
						
			// If it's a 0, then they are missing that wave credit:
			if (value === 0)
			{
				table.push('<td><p style="text-align:center;"><font color="#F8A5A9">Incomplete</font></p></td>');
			}
			
			// If it's a -1, then the wave doesn't exist:
			else if (value === -1)
			{
				table.push('<td><p style="text-align:center;"><font color="#00FF00">N/A</font></p></td>');
			}
			
			// Otherwise, insert the timestamp into the table.
			else
			{
				// Take the wave credit time stamp, offset it by the time zone difference, and multiply the result by 1000.
				// Javascript uses ms for its unix time but we get the timestamp as seconds.
				var timestamp = (value + time_zone_difference)*1000;
				
				// Make a date string out of it:
				var d = new Date(timestamp);
				var date_string = "{0}<br/>{1}".format(d.toLocaleDateString(), d.toLocaleTimeString());
				
				// Then insert that into the table:
				table.push('<td><p style="text-align:center;"><font color="#00FF00">' + date_string + '</font></p></td>');
				
				// Raise the wave credits counter, since the client earned a wave credit for this wave:
				earned_credits += 1;
				
				// Put this wave credit into the wave credits array:
				all_wave_credits.push([timestamp, i-1, j+1]);
			}
		}

		// Close the table row:
		table.push("</tr>");
	}
	
	// Close the table itself:
	table.push("</table>");
	
	// Insert it into the HTML page:
	document.getElementById('individual_table').innerHTML = table.join("");
	
	// The second table needs the wave credits timestamp array, and the third table needs the total number of earned credits,
	// so return both of that data to the caller so they can be passed to the appropriate table generation functions:
	return [earned_credits, all_wave_credits];
}





// Generates the table header for the top (wave credits) table:

function generate_top_table_header(total_waves)
{
	// Init:
	var table = ['<table class="individual_main_table"><tr><th>Map & Mission</th>'];
	
	// Per wave, add a column:
	for (var i = 1; i <= total_waves; i++)
		table.push("<th>Wave {0}</th>".format(i));
	
	// Close the row tag and return:
	table.push("</tr>");
	return table;
}





// Generates the HTML for the wave credits history table below the bottom left corner of the main wave credits table.

function generate_left_table(credits_array)
{
	// Make a new table array and preload it with the header:
	table = ['<table class="individual_most_recent_credits"><tr><th></th><th>Map</th><th>&nbsp;&nbsp;Wave&nbsp;&nbsp;</th><th>Date Earned</th></tr>'];
	
	// Sort the wave credits array in decreasing time stamp order.
	credits_array.sort(function(a, b){return b[0] - a[0]});					// https://www.w3schools.com/js/js_array_sort.asp
	
	// We only can store 4 records, since the stats table (to be made later) also has 4 rows.
	for (var i = 0; i < 4; i++)
	{
		// If this index is valid, pull the wave credit out:
		if (i < credits_array.length)
		{
			// Grab the data from the wave credit array:
			var wave_credit = credits_array[i];
			var d = new Date(wave_credit[0]);
			var map_index = wave_credit[1];
			var wave_number = wave_credit[2];
			
			// Grab the map name from the map index:
			var map_name = g_TourMissions[map_index][0];
			
			// Build a timestamp string:
			var timestamp = "{0} {1}".format(d.toLocaleDateString(), d.toLocaleTimeString());
			
			// Insert it into the table:
			table.push('<tr><td>' + String(i+1) + '<td><font color="#00FFFF"><b>' + map_name + '</b></td><td><p style="text-align:center;">' + String(wave_number) + '</p></td><td><p style="text-align:center;">' + timestamp + '</p></td></tr>');
		}
		
		// Otherwise, put an empty table row in:
		else
		{
			table.push('<tr><td>' + String(i+1) + '<td></td><td></td><td><p style="text-align:center;"><i>No record</i></p></td></tr>');
		}
	}
	
	// Close the table:
	table.push('</table>');
	
	// Insert it into the page:
	document.getElementById('individual_table_history').innerHTML = table.join("");
}





// Generates the HTML for the statistics table below the bottom right corner of the main wave credits table.

function generate_right_table(earned_credits, total_credits)
{
	// Make a new table array and preload it with the header:
	table = ['<table class="individual_statistics"><tr><th>Statistic</th><th>Value</th></tr>'];
	
	// Grab the current URL of this page and split along the /:
	var url = window.location.href.split("/");
	
	// We want the last element of the URL, which gives us the steam ID of the user to get the tour data of:
	var steamid = url[url.length - 1];
	
	// Steam profile link:
	table.push('<tr><td>Steam User</td><td><p style="text-align:center;"><a href="http://steamcommunity.com/profiles/' + steamid + '/">Profile Page</a></p></td></tr>');
	
	// Total earned wave credits:
	table.push('<tr><td>Total Wave Credits</td><td><p style="text-align:center;">' + String(earned_credits) + ' / ' + String(total_credits) + '</p></td></tr>');
	
	// Tour progress percentage:
	var percent = Math.floor(earned_credits*100/total_credits);
	table.push('<tr><td>Tour Progress</td><td><p style="text-align:center;">' + String(percent) + '%</p></td></tr>');
	
	// Current date:
	var d = new Date();
	var date_string = "{0} {1}".format(d.toLocaleDateString(), d.toLocaleTimeString());
	table.push('<tr><td>Last updated</td><td><p style="text-align:center;">' + date_string + '</p></td></tr></table>'); 			// Also close the table tag while we're here.
	
	// Insert it into the page:
	document.getElementById('individual_table_stats').innerHTML = table.join("");
}




