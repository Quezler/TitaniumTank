
/**
 * =============================================================================
 * Titanium Tank Tour Global Tour Statistics Webpage
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

// Graph references:
// https://developers.google.com/chart/interactive/docs/ 								- Intro
// https://developers.google.com/chart/interactive/docs/gallery/linechart				- Line graphs
// https://developers.google.com/chart/interactive/docs/gallery/barchart 				- Bar graphs
// https://developers.google.com/chart/interactive/docs/customizing_axes 				- Axes
// https://developers.google.com/chart/interactive/docs/customizing_tooltip_content 	- Tooltips

// Map names.
// These must be in the same order as listed in the Tour Information.csv file on the MvM servers, medal server, and website server.
// The map names do not need to match exactly but the order must be the same.
const g_MapNames =  ["Dockyard", "Downtown", "Powerplant", "Steep", "Teien", "Waterfront"];
const g_MapColors = ['#a349a3', '#22b14c', '#ff7f27', '#b97a57', '#ff0000', '#00a2e8'];





// Init the graph library:
google.charts.load('current', {packages: ['corechart', 'line', 'bar']});

// After the library loads, trigger the whole thing:
google.charts.setOnLoadCallback(download_global_data);





// Called after the Google charts library has been loaded.

function download_global_data()
{
	// Download the raw statistics data from the server:
	http_get_async("http://" + get_server_ip_address() + "/TitaniumTank/global.csv", display_statistics);
}





// Called after the statistics data has been downloaded from the server.

function display_statistics(response)
{
	// Split it along the = to get each section's data:
	var split_data = response.trim().split("=");
	
	// Draw the table first, and get the total number of participants out: (this is in row 6 column 2)
	var total_participants = draw_statistics_table(split_data[4]);
	
	// Draw the wave credits graph per map, per wave: (this is in row 1 column 1)
	draw_map_wave_graph(split_data[0], total_participants);
	
	// Draws the player participation bar graph: (this is in row 1 column 2)
	draw_player_map_participation_graph(split_data[2]);
	
	// Draws graphs that show data versus time (date).
	// The data for 8 graphs are stored in this chunk. This spans from rows 2-5 on both columns.
	draw_time_dependent_data_graphs(split_data[3]);
	
	// Draw the player wave credits graph: (this is in row 6 columns 1)
	draw_player_wave_credits_graph(split_data[1], total_participants);
}





// Generates the statistics table on the page (in quadrant 4).

function draw_statistics_table(csv_data)
{
	// Split the data along commas:
	var split_data = csv_data.split(",");	// In order: Participating players, medal recepients, wave credits awarded, wave credits acquired, participated missions, completed missions
	
	// Now start building the table. Put the header first:
	var table = ['<table style="margin:0;width:100%;height:100%"><tr><th>Statistic</th><th><p style="text-align:center;">Value</p></th></tr>'];
	
	// Put the tour participants first:
	table.push('<tr><td>Tour Participants</td><td><p style="text-align:center;">' + split_data[0] + ' players</p></td></tr>');
	
	// Medal count and percent of participants who completed the tour:
	var percent = Math.floor(Number(split_data[1])*100/Number(split_data[0]));
	table.push('<tr><td>Medals Distributed</td><td><p style="text-align:center;">' + '{0} medals ({1}%)'.format(split_data[1], percent) + '</p></td></tr>');
	
	// Total wave credits awarded by the server:
	table.push('<tr><td>Total Wave Credits</td><td><p style="text-align:center;">' + split_data[2] + ' awarded credits</p></td></tr>');

	// Total wave credits that all the participating players own collectively:
	table.push('<tr><td>Unique Waves Credits</td><td><p style="text-align:center;">' + split_data[3] + ' earned credits</p></td></tr>');

	// Total missions attempted (sum of the number of missions each player has participated in):
	table.push('<tr><td>Total Missions Attempted</td><td><p style="text-align:center;">' + split_data[4] + ' attempted missions</p></td></tr>');

	// Total missions completed (sum of the number of missions each player has completed):
	table.push('<tr><td>Total Missions Completed</td><td><p style="text-align:center;">' + split_data[5] + ' completed missions</p></td></tr>');

	// Duration of the tour (how long it has been active since the tour was first launched):
	var duration_seconds = Math.floor(Date.now()/1000) - 1517517845;					// 1517517845 is when the first wave credit was recorded
	var duration_string = get_time_left_array(duration_seconds);
	table.push('<tr><td>Tour Duration</td><td><p style="text-align:center;">' + duration_string + '</p></td></tr>');
	
	// Tour deadline:
	// TO-DO: Once established, make this a section a countdown.
	table.push('<tr><td>Tour Deadline</td><td><p style="text-align:center;">TBA</p></td></tr>');
	
	// Last updated time. Close the table while we're here.
	var d = new Date();
	var date_string = "{0} {1}".format(d.toLocaleDateString(), d.toLocaleTimeString());
	table.push('<tr><td>Last Updated</td><td><p style="text-align:center;">' + date_string + '</p></td></tr></table>');
	
	// Insert the table HTML into the page:
	document.getElementById('global_table_stats').innerHTML = table.join("");
	
	// Return the total number of participating players to the caller.
	// This is used to generate the map-wave graph (in quadrant 2).
	return Number(split_data[0]);
}





// Given a time in seconds, return the number of days, hours, minutes, and seconds left:

function get_time_left_array(time_in_seconds)
{
	// Days:
	var days = Math.floor(time_in_seconds/86400);
	var days_remainder = time_in_seconds % 86400;
	
	// Hours:
	var hours = Math.floor(days_remainder/3600);
	var hours_remainder = days_remainder % 3600;
	
	// Minutes:
	var minutes = Math.floor(hours_remainder/60);
	var seconds = days_remainder % 60;
	
	// Build a string out of it:
	return "{0} days {1} hours {2} min {3} sec".format(days, hours, minutes, seconds);
}





// Draws a line graph of the wave credits earned on each wave, on each map, by player count.
// This graph is located on quadrant 2 of the page.

function draw_map_wave_graph(csv_data, total_participants) 
{
	// Split the csv string along newlines to break it up by rows:
	var rows = csv_data.trim().split("\n");
	
	// Create the table to store the data in:
	var table = new google.visualization.DataTable();
	
	// Add columns:
	table.addColumn('number', 'Wave');		// Wave Number
	
	// For the map columns, we can loop across the global maps array to add them to the table:
	for (i in g_MapNames)
	{
		table.addColumn('number', g_MapNames[i]);
		table.addColumn({'type': 'string', 'role': 'tooltip', 'p': {'html': true}});
	}
	
	// Then per row in the CSV file:
	for (var i = 0; i < rows.length; i++)
	{
		// Split the row by commas:
		var cells = rows[i].split(",");
		
		// Build an array of the data. Preload it with the wave number (which is i+1).
		var data = [i+1];
		
		// Then loop across the cells (wave credits per map, for this (ith) particular wave number)
		for (var j = 0; j < cells.length; j++)
		{
			// Convert the value into a number:
			var value = Number(cells[j]);
			
			// If the value is -1, put NaN in the array and an empty HTML tooltip string:
			if (value === -1)
			{
				data.push(NaN);
				data.push("");
			}
			
			// Otherwise...
			else
			{
				// Calculate what % of all participating players have this wave credit.
				var ratio = Math.round(value*100/total_participants);
				
				// Build the tooltip string:
				var tooltip_str = create_html_tooltip_mapwavegraph(i, j, value, ratio);
				
				// Put the number and the tooltip string to the data array:
				data.push(value+1);
				data.push(tooltip_str);
			}
		}
		
		// Then add the data row to the graph:
		table.addRow(data);
	}
	
	// Set graph options:
	var options =
	{
		// Graph title
		title: 'Total Earned Wave Credits by Map & Wave',
		
		// Graph title style
		titleTextStyle: {color: '#fff', fontSize: 24},
		
		// x-axis
		hAxis:
		{ 
			title: 'Wave Number',
			textStyle: {color: '#FFF'},
			titleTextStyle: {color: '#fff'},
			baselineColor: "#FFFFFF",
		},
		
		// y-axis
        vAxis:
		{ 
			title: 'Wave Credits', 
			textStyle: {color: '#FFF'},
			titleTextStyle: {color: '#fff'},
			baselineColor: "#FFFFFF",
		},
		
		// Line colors per map
        colors: g_MapColors,
		
		// Use an HTML tooltip for this graph.
		tooltip: { isHtml: true },		
		
		// Sets the graph background to a dark gray so it matches the background image rather well.
		backgroundColor: '#313131',
		
		// Legend tweaks
		legend: {alignment: "center", textStyle: {color: '#fff'}},
		
		// Makes dots appear on each data point:
		pointSize: 3,
    };
	
	// Draw the graph:
	var chart = new google.visualization.LineChart(document.getElementById('graph1'));
	chart.draw(table, options);
}





// Returns a HTML string to use as a tooltip on each data point on the map-waves line graph.

function create_html_tooltip_mapwavegraph(wave_number, map_index, wave_credits, ratio)
{
	return '<p align="center"><font size = "4" color="{0}"><b>{1}</b></font></p>\
		    <p><font size = "3">&nbsp;&nbsp;&nbsp;<b>Wave:</b> {2}<br/>\
		    &nbsp;&nbsp;&nbsp;<b>Credits:</b> {3}&nbsp;&nbsp;&nbsp;<br/>\
		    &nbsp;&nbsp;&nbsp;<b>Ratio:</b> {4}%\
		    &nbsp;&nbsp;&nbsp;</font></p>'.format(g_MapColors[map_index], g_MapNames[map_index], wave_number+1, wave_credits, ratio);
}





// Draws a bar graph of the number of players who have participated and/or completed each mission:

function draw_player_map_participation_graph(csv_data)
{
	// Create the data array first. Preload it with the header:
	var data = [['Map', 'Participants', { role: 'annotation' }, 'Completists', { role: 'annotation' }]];
	
	// Split the csv along the newlines:
	var split_lines = csv_data.trim().split("\n");
	
	// There are two rows. Split both along the commas:
	var mission_participants = split_lines[0].split(",");
	var mission_completists  = split_lines[1].split(",");
	
	// Per map's data:
	for (var i = 0; i < g_MapNames.length; i++)
	{
		// Grab the total participants and completists, and turn them into numbers:
		var participants = Number(mission_participants[i]);
		var completists  = Number(mission_completists[i]);
		
		// Compute the percent participated who completed the tour:
		var percentage = Math.floor(completists*100/participants);
		
		// Push the data into the array, along with the map name:
		data.push([g_MapNames[i], participants, String(participants), completists, "{0} ({1}%)".format(completists, percentage)]);
	}
	
	// Create the table out of the data array:
	var table = new google.visualization.arrayToDataTable(data);
	
	// Set the graph options:
	var materialOptions =
	{
		// Graph title
		title: 'Participants & Completists by Map',

		// Title style
		titleTextStyle: {color: 'white', fontSize: 24},

		// x-axis
		hAxis:
		{
			title: 'Players',
			minValue: 0,
			textStyle:{color: '#FFF'},
			titleTextStyle: {color: '#fff'},
			baselineColor: "#FFFFFF",
		},
		
		// y-axis
		vAxis:
		{
			title: 'Map',
			textStyle:{color: '#FFF'},
			titleTextStyle: {color: '#fff'},
			baselineColor: "#FFFFFF",
		},
		
		// Bar colors
		colors: ['#00a2e8', '#22b14c'],
		
		// Make it a vertical bar graph
		bars: 'vertical',
		
		// Background color
		backgroundColor: '#313131',
		
		// Legend
		legend: {alignment: "center", textStyle: {color: '#fff'}},
	};
	
	// Draw the bar graph:
	var materialChart = new google.visualization.BarChart(document.getElementById('graph2'));
	materialChart.draw(table, materialOptions);
}






// Draws time-dependent data graphs.

function draw_time_dependent_data_graphs(csv_data)
{
	// First, convert all the data into numbers and store them here:
	var data = [];
	
	// Split the CSV file along the newlines:
	var split_data = csv_data.trim().split("\n");
	
	// Per row in the CSV file:
	for (i in split_data)
	{
		// Split the row into cells:
		var split_row = split_data[i].split(",");
		
		// The first two numbers are dates. Preload the numbers row with the date:
		var numbers_row = [new Date(2018, Number(split_row[0])-1, Number(split_row[1]))];
		
		// Then convert the rest of the data into numbers:
		for (var j = 2; j < split_row.length; j++)
			numbers_row.push(Number(split_row[j]));
		
		// Put the numbers row into the data array:
		data.push(numbers_row);
	}
	
	// Create the row 2 graphs: (Participants & Completists cumulative sum per map)
	draw_row_2_graphs(data);
	
	// Create the row 3 graphs: (Unique participants & completists each day & cumulative sum)
	draw_row_3_graphs(data);
	
	// Create the row 4 graphs: (Missions completed & participated each day & cumulative sum)
	draw_row_4_graphs(data);
	
	// Create the row 5 graphs: (Wave credits awarded each day & overtime, both unique & total)
	draw_row_5_graphs(data);
}





// Draws the 2 total participants & total completists graphs over time on row 2 of the page:

function draw_row_2_graphs(data)
{
	// Create the data table for it:
	var table1 = new google.visualization.DataTable(); 			// Total *Participants* Per Map Over Time
	var table2 = new google.visualization.DataTable(); 			// Total *Completists* Per Map Over Time
	
	// The x-axis is a date:
	table1.addColumn('date', 'Date');
	table2.addColumn('date', 'Date');
	
	// There are 6 data points (y-values) for each table:
	for (i in g_MapNames)
	{
		table1.addColumn('number', g_MapNames[i]);
		table2.addColumn('number', g_MapNames[i]);
	}
	
	// Now loop across the data array:
	for (i in data)
	{
		// Grab the row:
		var row = data[i];
		
		// Create 2 data rows (1 per table) and preload the date in them:
		var datarow1 = [row[0]];
		var datarow2 = [row[0]];
		
		// Now put the map data in both:
		for (var j = 1; j < 7; j++)
		{
			datarow1.push(row[j]);
			datarow2.push(row[j+6]);
		}
		
		// Put both into the tables:
		table1.addRow(datarow1);
		table2.addRow(datarow2);
	}
	
	// Create the options object:
	var options =
	{
		// Graph title
		title: 'Total Participants Per Map Over Time',
		
		// Graph title style
		titleTextStyle: {color: '#fff', fontSize: 24},
		
		// x-axis
		hAxis:
		{
			title: 'Date',
			textStyle: {color: '#FFF'},
			titleTextStyle: {color: '#fff'},
			baselineColor: "#FFFFFF",
		},
		
		// y-axis
        vAxis:
		{ 
			title: 'Participant Players', 
			textStyle: {color: '#FFF'},
			titleTextStyle: {color: '#fff'},
			baselineColor: "#FFFFFF",
		},
		
		// Line colors per map (dockyard, downtown, powerplant, steep, teien, waterfront)
		colors: g_MapColors,
		
		// Sets the graph background to a dark gray so it matches the background image rather well.
		backgroundColor: '#313131',
		
		// Legend tweaks
		legend: {alignment: "center", textStyle: {color: '#fff'}},
		
		// Makes dots appear on each data point:
		pointSize: 3,
	};
	
	// Draw the participants graph first:
	var chart1 = new google.visualization.LineChart(document.getElementById('graph3'));
	chart1.draw(table1, options);
	
	// Modify the title on the options array for the completists graph:
	options.title = 'Total Completists Per Map Over Time';
	
	// Then draw that graph:
	var chart2 = new google.visualization.LineChart(document.getElementById('graph4'));
	chart2.draw(table2, options);	
}





// Draws the 2 participants & completists graphs per day & over time on row 3 of the page:

function draw_row_3_graphs(data)
{
	// Create the data table for it:
	var table1 = new google.visualization.DataTable(); 			// Unique Participants & Completists Each Day
	var table2 = new google.visualization.DataTable(); 			// Unique Participants & Completists Over Time
	
	// The x-axis is a date:
	table1.addColumn('date', 'Date');
	table2.addColumn('date', 'Date');
	
	// First table has two numbers on the y-axis:
	table1.addColumn('number', "Participants");
	table1.addColumn('number', "Completists");
	
	// Second table has 2 numbers on the first y-axis, another number on the 2nd y-axis:
	table2.addColumn('number', "Participants");
	table2.addColumn('number', "Completists");
	table2.addColumn('number', "Percent Completed");
	
	// The data we receive contains the total number of unique participants & completists per day,
	// but the second graph requires us to plot the stacked total, not the daily totals.
	//
	// Use these two variables to keep a running total of number of unique players:
	var total_participants = 0;
	var total_completists = 0;
	
	// Now loop across the data array:
	for (i in data)
	{
		// Grab the row and the date:
		var row = data[i];
		var d = row[0];
		
		// Grab the data:
		var participants = row[13];
		var completists  = row[14];
		
		// Put it into the first data table:
		table1.addRow([d, participants, completists]);
		
		// Sum it up on the totals:
		total_participants += participants;
		total_completists += completists;
		
		// Then add the second row:
		table2.addRow([d, total_participants, total_completists, Math.floor(total_completists*100/total_participants)]);
	}
	
	// Options for the first graph:
	var options1 =
	{
		// Graph title
		title: 'Unique Participants & Completists Each Day',
		
		// Graph title style
		titleTextStyle: {color: '#fff', fontSize: 24},
		
		// x-axis
		hAxis:
		{ 
			title: 'Date',
			textStyle: {color: '#FFF'},
			titleTextStyle: {color: '#fff'},
			baselineColor: "#FFFFFF",
		},
		
		// y-axis
        vAxis:
		{ 
			title: 'Players', 
			textStyle: {color: '#FFF'},
			titleTextStyle: {color: '#fff'},
			baselineColor: "#FFFFFF",
		},
		
		// Line color:
		colors: ["#27D884", "#E4D61B"],
		
		// Sets the graph background to a dark gray so it matches the background image rather well.
		backgroundColor: '#313131',
		
		// Legend tweaks
		legend: {alignment: "center", textStyle: {color: '#fff'}},
		
		// Makes dots appear on each data point:
		pointSize: 3,
    };
	
	// Draw the graph:
	var chart1 = new google.visualization.LineChart(document.getElementById('graph5'));
	chart1.draw(table1, options1);
	
	// Graph 2 (Total cumulative participants & completists over time)
	var options2 =
	{
		// Graph title
		title: 'Unique Participants & Completists Over Time',
		
		// Graph title style
		titleTextStyle: {color: '#fff', fontSize: 24},
		
		// x-axis
		hAxis:
		{ 
			title: 'Date',
			textStyle: {color: '#FFF'},
			titleTextStyle: {color: '#fff'},
			baselineColor: "#FFFFFF",
		},
		
        // Gives each series an axis that matches the vAxes number below.
        series:
		{
			0: {targetAxisIndex: 0},
			1: {targetAxisIndex: 0},
			2: {targetAxisIndex: 1},
        },
		
		// Set properties to each axis:
        vAxes:
		{
			0:
			{ 
				title: 'Players', 
				textStyle: {color: '#FFF'},
				titleTextStyle: {color: '#fff'},
				baselineColor: "#FFFFFF",
			},
			1:
			{ 
				title: 'Percent Completed', 
				textStyle: {color: '#FFF'},
				titleTextStyle: {color: '#fff'},
				baselineColor: "#FFFFFF",
			},
        },
		
		// Line colors per data set:
		colors: ["#27D884", "#E4D61B", "#FF8080"],
		
		// Sets the graph background to a dark gray so it matches the background image rather well.
		backgroundColor: '#313131',
		
		// Legend tweaks
		legend: {alignment: "center", textStyle: {color: '#fff'}, position: "bottom"},
		
		// Makes dots appear on each data point:
		pointSize: 3,		
    };
	
	// Draw the graph:
	var chart2 = new google.visualization.LineChart(document.getElementById('graph6'));
	chart2.draw(table2, options2);
}





// Draws the 2 missions participated & completed per day & overtime graphs on row 4 of the page:

function draw_row_4_graphs(data)
{
	// Create the data table for it:
	var table1 = new google.visualization.DataTable(); 			// Missions Completed & Participated Each Day
	var table2 = new google.visualization.DataTable(); 			// Missions Completed & Participated Over Time
	
	// The x-axis is a date:
	table1.addColumn('date', 'Date');
	table2.addColumn('date', 'Date');
	
	// Both have participated & completed y-values:	
	table1.addColumn('number', "Participated");
	table2.addColumn('number', "Participated");

	table1.addColumn('number', "Completed");
	table2.addColumn('number', "Completed");
	
	// The data we receive contains the total number participated & completed per day,
	// but the second graph requires us to plot the stacked total, not the daily totals.
	//
	// Use these two variables to keep a running total of each stat:
	var total_participated = 0;
	var total_completed = 0;
	
	// Now loop across the data array:
	for (i in data)
	{
		// Grab the row and the date:
		var row = data[i];
		var d = row[0];
		
		// Grab the data:
		var participated = row[15];
		var completed  = row[16];
		
		// Put it into the first data table:
		table1.addRow([d, participated, completed]);
		
		// Sum it up on the totals:
		total_participated += participated;
		total_completed += completed;
		
		// Then add the second row:
		table2.addRow([d, total_participated, total_completed]);
	}
	
	// Graph 1 (Missions Completed & Participated Each Day)
	var options =
	{
		// Graph title
		title: 'Missions Completed & Participated Each Day',
		
		// Graph title style
		titleTextStyle: {color: '#fff', fontSize: 24},
		
		// x-axis
		hAxis:
		{ 
			title: 'Date',
			textStyle: {color: '#FFF'},
			titleTextStyle: {color: '#fff'},
			baselineColor: "#FFFFFF",
		},
		
		// y-axis
        vAxis:
		{ 
			title: 'Missions', 
			textStyle: {color: '#FFF'},
			titleTextStyle: {color: '#fff'},
			baselineColor: "#FFFFFF",
		},
		
		// Line color
        colors: ["#00E0E0", "#FF8000"],
				
		// Sets the graph background to a dark gray so it matches the background image rather well.
		backgroundColor: '#313131',
		
		// Legend tweaks
		legend: {alignment: "center", textStyle: {color: '#fff'}},
		
		// Makes dots appear on each data point:
		pointSize: 3,
    };
	
	// Plot it:
	var chart1 = new google.visualization.LineChart(document.getElementById('graph7'));
	chart1.draw(table1, options);
	
	// The second graph uses the same configuration, but different title:
	options.title = 'Missions Completed & Participated Over Time';
	
	// Plot it:
	var chart2 = new google.visualization.LineChart(document.getElementById('graph8'));
	chart2.draw(table2, options);
}





// Draws the 2 wave credits per day & overtime graphs on row 5 of the page:

function draw_row_5_graphs(data)
{
	// Create the data table for it:
	var table1 = new google.visualization.DataTable(); 			// Missions Completed & Participated Each Day
	var table2 = new google.visualization.DataTable(); 			// Missions Completed & Participated Over Time
	
	// The x-axis is a date:
	table1.addColumn('date', 'Date');
	table2.addColumn('date', 'Date');
	
	// Both have total & unique values
	table1.addColumn('number', "Total Credits");
	table2.addColumn('number', "Total Credits");

	table1.addColumn('number', "Unique Credits");
	table2.addColumn('number', "Unique Credits");
	
	// The data we receive contains the total & unique awarded per day,
	// but the second graph requires us to plot the stacked total, not the daily totals.
	//
	// Use these two variables to keep a running total of each stat:
	var total_total = 0;
	var total_unique = 0;
	
	// Now loop across the data array:
	for (i in data)
	{
		// Grab the row and the date:
		var row = data[i];
		var d = row[0];
		
		// Grab the data:
		var unique = row[17];
		var total = row[18];
		
		// Put it into the first data table:
		table1.addRow([d, total, unique]);
		
		// Sum it up on the totals:
		total_total += total;
		total_unique += unique;
		
		// Then add the second row:
		table2.addRow([d, total_total, total_unique]);
	}
	
	// Graph 1 (Total & unique wave credits awarded each day.)
	var options =
	{
		// Graph title
		title: 'Wave Credits Awarded Each Day',
		
		// Graph title style
		titleTextStyle: {color: '#fff', fontSize: 24},
		
		// x-axis
		hAxis:
		{ 
			title: 'Date',
			textStyle: {color: '#FFF'},
			titleTextStyle: {color: '#fff'},
			baselineColor: "#FFFFFF",
		},
		
		// y-axis
        vAxis:
		{ 
			title: 'Wave Credits', 
			textStyle: {color: '#FFF'},
			titleTextStyle: {color: '#fff'},
			baselineColor: "#FFFFFF",
		},
		
		// Line color
        colors: ["#00FF00", "#FFFF00"],
		
		// Sets the graph background to a dark gray so it matches the background image rather well.
		backgroundColor: '#313131',
		
		// Legend tweaks
		legend: {alignment: "center", textStyle: {color: '#fff'}},
		
		// Makes dots appear on each data point:
		pointSize: 3,
    };
	
	
	// Draw it:
	var chart1 = new google.visualization.LineChart(document.getElementById('graph9'));
	chart1.draw(table1, options);
	
	// Options for second graph are identical except for the title:
	options.title = 'Wave Credits Awarded Over Time';
	
	// Now draw that too:
	var chart2 = new google.visualization.LineChart(document.getElementById('graph10'));
	chart2.draw(table2, options);
}





// Draws the graph of number of players who have the specified number of wave credits:

function draw_player_wave_credits_graph(csv_data, total_participants)
{
	// Create the graph:
	var table = new google.visualization.DataTable();
	
	// Add columns:
	table.addColumn('number', 'Wave Credits');		// Wave Credits
	table.addColumn('number', 'Players');			// Players
	table.addColumn({'type': 'string', 'role': 'tooltip', 'p': {'html': true}});		// Tooltip
	
	// Split the csv file by the commas:
	var split_lines = csv_data.trim().split(",");
	
	// Then per row in the CSV file:
	for (var i = 0; i < split_lines.length; i++)
	{
		// Turn the string into an integer:
		var credits = i + 1;
		var value = Number(split_lines[i]);
		
		// Create a HTML tooltip for this data point:
		var percent = Math.floor(value*100/total_participants);
		var tooltip = create_html_tooltip_playercredits(credits, value, percent);
		
		// Add it to the table:
		table.addRow([credits, value, tooltip]);
	}
	
	// Set graph options:
	var options =
	{
		// Title
		title: 'Earned Wave Credits by Players Count',
		
		// Title style
		titleTextStyle: {color: '#fff', fontSize: 24},
		
		// x-axis
		hAxis:
		{
			title: 'Acquired Wave Credits', 
			textStyle:{color: '#FFF'},
			titleTextStyle: {color: '#fff'},
			viewWindow: {min: 0, max:40},
			baselineColor: "#FFFFFF",
		},
		
		// y-axis
        vAxis:
		{
			title: 'Participating Players', 
			textStyle:{color: '#FFF'},
			titleTextStyle: {color: '#fff'},
			baselineColor: "#FFFFFF",
		},
		
		// Line color
        colors: ['#ff97b9'],		// Pinkish
		
		// Use an HTML tooltip.
		tooltip: { isHtml: true },
		
		// Legend tweaks
		legend: {position: "none"},
		
		// Sets the graph background to a dark gray so it matches the background image rather well.
		backgroundColor: '#313131',	
		
		// Makes dots appear on each data point:
		pointSize: 3,
	};
	
	// Draw the graph:
	var chart = new google.visualization.LineChart(document.getElementById('graph11'));
	chart.draw(table, options);
}





// Returns a HTML string to use as a tooltip on each data point on the player wave credits line graph.

function create_html_tooltip_playercredits(wave_credits, players, percent)
{
	return '<p><font size = "3">&nbsp;&nbsp;&nbsp;<b>Credits:</b> {0}<br/>&nbsp;&nbsp;&nbsp;<b>Players:</b> {1}&nbsp;&nbsp;&nbsp;<br/>&nbsp;&nbsp;&nbsp;<b>Ratio:</b> {2}%</font></p>'.format(wave_credits, players, percent);
}




