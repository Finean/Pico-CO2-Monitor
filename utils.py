import json
import machine
import ntptime
import network
import os
import time

rtc = machine.RTC()
connection = None

VER = "1.0 - 30th November 2025"
NET_SSID = "ExampleSSID"
NET_PSK = "ExamplePSK"


def network_connect(SSID, PSK):
    global connection
    # Enable the Wireless
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    # Number of attempts to make before timeout
    max_wait = 10

    # Sets the Wireless LED pulsing and attempts to connect to your local network
    wlan.config(pm=0xa11140)  # Turn WiFi power saving off for some slow APs
    wlan.connect(SSID, PSK)

    while max_wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        max_wait -= 1
        print("Attempting to connect...")
        time.sleep(1)
    if wlan.status() != 3:
        print("Connection error")
        return(False)
    else:
        print("Connected to ", SSID)
        connection = SSID
        return(True)
        
    
def sync_time():
    global time_string
    global connection
    if connection is None:
        print("No network connection, unable to sync NTC time")
        return False
    try:
        ntptime.settime()
    except OSError:
        print("Unable to contact NTP server")
        return False
    
    print("Time synced with NTP server")
    current_t = rtc.datetime()
    return True
    
#Config functions
std_colours = ["WHITE", "BLACK", "RED", "GREEN", "BLUE", "YELLOW"]
invert = {"BLACK":"WHITE", "WHITE":"BLACK"}
#Default config
config = {"24hr":True,
          "graph_max_time": 10,
          "graph_axes": True,
          "graph_show_pts": True,
          "graph":True,
          "graph_padding": 100,
          "ntc_upd": True,
          "celsius": "C",
          "font_colour": "WHITE",
          "bg_colour": "BLACK",
          "axis_colour": "WHITE",
          "line_colour": "WHITE",
          "max_colour": "RED",
          "min_colour": "GREEN",
          "leading_zeros": True}

setting_names = {"24hr":"Use 24 hour time format",
          "graph_max_time": "Max age of data used on graph (mins)",
          "graph_axes": "Show graph axes",
          "graph_show_pts": "Show min/max values on graph",
          "graph":"Show graph",
          "graph_padding": "Graph y axis padding",
          "ntc_upd": "Sync time with NTC server on boot",
          "celsius": "Temperature unit",
          "font_colour": "Font colour",
          "bg_colour": "Background colour",
          "axis_colour": "Graph axis colour",
          "line_colour": "Graph line colour",
          "max_colour": "Graph max value colour",
          "min_colour": "Graph min value colour",
          "leading_zeros": "Show leading zeroes on readout"}

setting_values = {"24hr": [True, False],
          "graph_max_time":[5, 10, 15, 20, 25, 30, 40, 50, 60, 120, 240],
          "graph_axes": [True, False],
          "graph_show_pts": [True, False],
          "graph": [True, False],
          "graph_padding": [0, 50, 100, 200, 300],
          "ntc_upd": [True, False],
          "celsius": ["C", "F"],
          "font_colour": std_colours,
          "bg_colour": ["BLACK", "WHITE"],
          "axis_colour": std_colours,
          "line_colour": std_colours,
          "max_colour": std_colours,
          "min_colour": std_colours,
          "leading_zeros": [True, False]}

pages = (
        ("24hr", "celsius", "leading_zeros", "ntc_upd", "font_colour", "bg_colour"),
        ("graph", "graph_axes", "graph_show_pts", "graph_max_time", "graph_padding", "axis_colour", "line_colour", "max_colour", "min_colour"),
        (f"Version: {VER}", f"SSID: {NET_SSID}", f"PSK: {NET_PSK}", "Display: 320x240", "Programmed by a goblin who should have just", "used C++ or Rust", "Made with Micropython")
        )


def file_exists(filename):
    try:
        return (os.stat(filename)[0] & 0x4000) == 0
    except OSError:
        return False


def new_cfg():
    global config
    save_cfg(config)
    print("New config saved")

    
def load_cfg():
    global config
    cfg_data = json.loads(open("/config.json", "r").read())
    if type(cfg_data) is dict:
        config = cfg_data
    else:
        print("config.json not a dict type")
        
        
def save_cfg(data):
    with open("/config.json", "w") as f:
        f.write(json.dumps(data))
        f.flush()
      
      
def update_cfg(field, value):
    global config
    try:
        #Avoid colour conflicts
        if field == "font_colour" and value == config["bg_colour"]:
            config["bg_colour"] = invert[value]
        if field == "bg_colour":
            for j in ("font_colour", "axis_colour", "line_colour", "max_colour", "min_colour"):
                if value == config[j]:
                    config[j] = invert[value]
        
        config[field] = value
        save_cfg(config)
    except:
        print("Error updating config")
    
    
if file_exists("/config.json"):
    load_cfg()
    print("Config loaded from config.json")
else:
    new_cfg()
    print("Using default config, saved to config.json")
    
if config["bg_colour"] == config["font_colour"]:
    print("Colour conflict, reverting to default")
    update_cfg("bg_colour", "BLACK")
    update_cfg("font_colour", "WHITE")