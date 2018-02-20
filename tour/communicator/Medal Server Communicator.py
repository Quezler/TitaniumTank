
#The official medal server (which drops the medal into player backpacks) is bound to a port not open to the internet.
#This is so that outsiders cannot cheat the medal by spamming POST requests to the medal server to illicitly award wave credits.
#
#However, one downside to that is that ONLY MvM servers on the same machine (or more correctly, LAN, if the firewall
#allows for access to that port on the medal server's operating system) can interact with the medal server. Nothing else can.
#
#In the event we are able to host tour servers on other machines, we need a way to allow them to communicate
#to the medal server securely. This program acts as a divide between the internet and the medal server, allowing
#other authorized servers on the internet to report the tour data to the medal server.
#
#The requirement is that only dedicated servers with access to the underlying operating system can host tour servers,
#since the server must have Python 3 installed on it. Servers running on GSPs or on most VPSes are not acceptable.

#Imports
from base64 import b16encode, b16decode
from csv import reader
from hashlib import sha512
from http.server import SimpleHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn, TCPServer
from urllib.parse import urlencode, parse_qs
from urllib.request import Request, urlopen
from sys import argv

#We need a third party module for AES encryption. Fortunately, it runs right out of the box with no installation.
#
#Get it from here: https://github.com/ricmoo/pyaes
#and drag the pyaes folder to the same working directory as this program.
import pyaes





#####################################################
#####################################################
#####################################################

#Acts as a fake medal server on a server running authorized tour servers.

class DummyMedalServerFake(SimpleHTTPRequestHandler):

#Called every time a POST request is sent to this server.
#POST requests are sent every time an MvM server reports that a player completed a wave in full.
#
#The server thinks that it's reporting to the real medal server, but it's not. We have to detour the request.

    def do_POST(self):

        #Send code 200 no matter what.
        self.send_response(200)
        self.end_headers()

        #To avoid crashing the whole thread, wrap the entire thing around a try/except.
        #Nothing should crash, but just to be safe...
        try:
            self.handle_post_data()
        except Exception as e:
            print("Dummy medal server POST error:", e)





#Called every time a POST request is sent to this server.

    def handle_post_data(self):

        #Determine how much data we need to read in. Cap it at 1024 bytes as a sanity limit:
        content_len = int(self.headers['content-length'])
        if content_len > 1024:
            content_len = 1024

        #Read in this data:
        post_body = self.rfile.read(content_len)

        #Parse the parameters into a dictionary:
        params_dict = parse_qs(post_body.decode())

        #Check the key and see if we should accept or reject this request.
        #
        #The server is sitting behind a firewall with no open ports, so only LAN (localhost)
        #connections can be made to it, but just to be safe, check for an auth key anyway.
        if not self.is_valid_request(params_dict):
            return None

        #Build a data tuple out of the POST parameters data:
        data_tuple = self.load_post_parameters(params_dict)

        #If it failed, don't do anything:
        if data_tuple is None:
            return None

        #Convert it into a list of strings:
        data_list = [str(x) for x in data_tuple]

        #Pack the TT API key in that list as well, so the receiving server can validate the authenticity of this wave credit:
        data_list.append(tt_api_key)

        #Join it into a single string delimiated by commas, like as if it's a CSV file:
        raw_data = ",".join(data_list)

        #Sending plaintext data over the internet is retarded, it's so best to encrypt the whole string first before transmission.
        #Use AES encryption to encrypt the string. The key is known to both the client and the server, so we can easily decode it.
        encrypted_data = self.encrypt_string(raw_data)

        #Because the encrypted data contains crazy byte strings, we can't directly transmit it over HTTP POST or else it will come
        #off as botched on the other side. Use base 16 encoding to encode the encrypted data so we can transmit it over HTTP POST:
        b16_encrypted = b16encode(encrypted_data)

        #Find the SHA512 hash of this data, to ensure the raw data was not modified during transmission across the internet:
        hash_value = sha512(b16_encrypted).hexdigest()

        #Then send a POST request to the dummy medal server with these two pieces of data.
        #The dummy medal server does not return a response so don't look for one.
        
        #Pack the given parameters into a dictionary.
        post_fields = {"data":b16_encrypted, "hash":hash_value}
        encoded_post_fields = urlencode(post_fields).encode()

        #Create the POST request to send to the dummy medal server and send it:
        request = Request("http://73.233.9.103:27001", encoded_post_fields)
        urlopen(request)





#Returns true if the given HTTP POST request is valid and authorized, false otherwise:

    def is_valid_request(self, params_dict):

        #Grab the key parameter:
        key = params_dict.get("key")

        #If it's null, return false:
        if key is None or len(key) == 0:
            return False

        #Otherwise, get the value in it and check if it matches:
        value = key[0]
        return value == tt_api_key





#Parses the post parameters into a data tuple.

    def load_post_parameters(self, params_dict):

        #Get the steam ID in first: (the player who completed the wave)
        steamid = params_dict.get("steam64")
        if steamid is None:
            return None

        #Get the timestamp next: (the time they completed this wave at)
        timestamp = params_dict.get("timestamp")
        if timestamp is None:
            return None

        #Get the mission index: (the mission they completed the wave on)
        mission_index = params_dict.get("mission")
        if mission_index is None:
            return None

        #Lastly, grab the wave number:
        wave_number = params_dict.get("wave")
        if wave_number is None:
            return None

        #Construct everything and return the tuple:
        try:
            return (int(steamid[0]), int(timestamp[0]), int(mission_index[0]), int(wave_number[0]))
        except:
            return None





#Encrypts the given string using AES encryption.
#Taken from the example code from the github repository.

    def encrypt_string(self, raw_data):
        counter = pyaes.Counter(initial_value=aes_init)
        aes = pyaes.AESModeOfOperationCTR(aes_key, counter=counter)
        return aes.encrypt(raw_data)





#####################################################
#####################################################
#####################################################


#This class should ONLY run on the same machine as the real medal server does.
#It accepts incoming wave credit requests from the internet, unpacks the data, and reports it to the real medal server.

class DummyMedalServerReceive(SimpleHTTPRequestHandler):

#Called every time a POST request is sent to this server.
#POST requests are sent every time an MvM server reports that a player completed a wave in full.
#
#The server thinks that it's reporting to the real medal server, but it's not. We have to detour the request.

    def do_POST(self):

        #Send code 200 no matter what.
        self.send_response(200)
        self.end_headers()

        #To avoid crashing the whole thread, wrap the entire thing around a try/except.
        #Nothing should crash, but just to be safe...
        try:
            self.handle_post_data()
        except Exception as e:
            print("Dummy medal server POST error:", e)





#Called every time a POST request is sent to this server.

    def handle_post_data(self):

        self.send_response(200)
        self.end_headers()

        #Determine how much data we need to read in. Cap it at 4096 bytes as a sanity limit:
        content_len = int(self.headers['content-length'])
        if content_len > 4096:
            content_len = 4096

        #Read in this data:
        post_body = self.rfile.read(content_len)

        #Parse the parameters into a dictionary:
        params_dict = parse_qs(post_body.decode())

        #Grab the two relevant pieces of data:
        b16_encrypted = params_dict["data"][0].encode()     #needs to be a byte string
        hash_value = params_dict["hash"][0]

        #Check the hash of the data; make sure it was not tampered with in the middle:
        if sha512(b16_encrypted).hexdigest() != hash_value:
            return None

        #Decrypt the base16-encoded string first:
        encrypted_data = b16decode(b16_encrypted)

        #Then decrypt the AES-encrypted data:
        string_data = self.decrypt_string(encrypted_data)

        #Split it along the commas to grab the individual pieces:
        (steamid, timestamp, mission_index, wave_number, tt_key) = string_data.split(",")

        #Check the TT API key validity:
        if tt_key != tt_api_key:
            return None

        #Then send a POST request to the real medal server using this data.
        
        #Pack the given parameters into a dictionary.
        post_fields = {"key":tt_key, "steam64":steamid, "timestamp":timestamp, "mission":mission_index, "wave":wave_number}
        encoded_post_fields = urlencode(post_fields).encode()

        #Create the POST request to send to the *real* medal server and send it:
        request = Request("http://localhost:65432", encoded_post_fields)
        urlopen(request)





#Decrypts the given string using AES encryption.
#Taken from the example code from the github repository.

    def decrypt_string(self, raw_data):
        counter = pyaes.Counter(initial_value=aes_init)
        aes = pyaes.AESModeOfOperationCTR(aes_key, counter=counter)
        return aes.decrypt(raw_data).decode()





#####################################################
#####################################################
#####################################################


#Dummy class used to make the server threaded.

class ThreadedHTTPServer(ThreadingMixIn, TCPServer):
    """Handle requests in a separate thread."""
    pass





#####################################################
#####################################################
#####################################################

#Since this program can be used to act as both a client and a server, we use the command line argument to determine
#hich version to run. Make sure that there IS in fact a command line argument provided:
if len(argv) == 1:
    print("Use '-fake' to run the fake medal server, '-receive' to accept incoming wave credit requests.")
    raise SystemExit





#Unlike the real medal server, there's no master class here (we don't really need one).
#We do need the TT API key and the AES key for our operations, so grab that data from the file system:

def get_key_from_csv(csv_file, key):
    with open(csv_file, mode="r") as f:
        for x in reader(f):
            if x[0].lower() == key:
                return x[1]

tt_api_key =   get_key_from_csv("../Tour Information.csv", "apikey")
aes_key =      get_key_from_csv("../AES Key.csv", "aes").encode()           #Needs to be bytes string
aes_init = int(get_key_from_csv("../AES Key.csv", "init"))                  #Needs to be an integer

#Make sure the keys are valid:
if tt_api_key is None or aes_key is None:
    print("Missing TT API key and/or AES key. Exiting...")
    raise SystemExit





#Figure out which handler we should use:
arg = argv[1].lower()
if arg == "-fake":
    handler = ThreadedHTTPServer(("", 65432), DummyMedalServerFake)
    print("Starting fake medal server on port 65432...")
elif arg == "-receive":
    handler = ThreadedHTTPServer(("", 27001), DummyMedalServerReceive)
    print("Starting recepient server on port 27001...")
else:
    print("Invalid command line argument: {}. Use '-fake' to run the fake medal server, '-receive' to accept incoming wave credit requests.".format(arg))
    raise SystemExit





#Run the proper HTTP server:
handler.serve_forever()




