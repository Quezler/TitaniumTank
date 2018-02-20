
/**
 * =============================================================================
 * Titanium Tank Tour Tour Progress Website
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


// Stolen from https://stackoverflow.com/a/4033310
// Executes a threaded HTTP GET request and passes the response data to a callback function.

function http_get_async(theUrl, callback)
{
    var xmlHttp = new XMLHttpRequest();
    xmlHttp.onreadystatechange = function()
	{ 
        if (xmlHttp.readyState == 4 && xmlHttp.status == 200)
            callback(xmlHttp.responseText);
    }
    xmlHttp.open("GET", theUrl, true); // true for asynchronous
    xmlHttp.send(null);
}





// Returns the IP address of the server website.
// If the server ever changes location, the GET requests to the csv files will still work fine.

function get_server_ip_address()
{
	// Grab the current URL of this page and split along the /:
	var url = window.location.href.split("/");
	
	// The array looks like:
	// 
	// ["http:", "", "73.233.9.103:27000", "TitaniumTank", "Servers"]
	// ["https:", "", "hydrogen-mvm.github.io", "TitaniumTank", "Servers"]
	// 
	// Some of these pages are also hosted using GitHub pages (as a backup),
	// so if this page is on GitHub Pages, then return the server IP (which we hard-code in).
	return (url[2] === "hydrogen-mvm.github.io") ? "73.233.9.103:27000" :  url[2];
}





// Stolen from https://coderwall.com/p/flonoa/simple-string-format-in-javascript
// This gives javascript strings a format operator similar to Python's str.format

String.prototype.format = function()
{
	a = this;
	for (k in arguments)
	{
		a = a.replace("{" + k + "}", arguments[k]);
	}
	return a;
}




