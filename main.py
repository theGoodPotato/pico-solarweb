from machine import I2C, Pin # type: ignore
import time
import network # type: ignore
import urequests
from creds import ssid, password  # Import credentials from creds.py
from PiicoDev_SSD1306 import * # type: ignore

# configuration
# ssid = 'your_SSID'  # Replace with your Wi-Fi SSID
# password = 'your_PASSWORD'  # Replace with your Wi-Fi password
fronius_ip = 'http://192.168.1.17'  # Replace with your Fronius inverter IP address
inverter_num = 1  # Replace with your inverter number (usually 1)

lcd = {
    "scl": 9,
    "sda": 8,
    "lcd_address": 0x3E
}

piicodev = {
    "sda": 8,
    "scl": 9,
    "lcd_address": 0x3C
}

# used functions and code
i2cdisplay = I2C(0, scl=Pin(lcd["scl"]), sda=Pin(lcd["sda"]), freq=400000)
piicodevdisplay = create_PiicoDev_SSD1306(bus=0, freq=400000,scl=Pin(piicodev["scl"]), sda=Pin(piicodev["sda"])) # type: ignore

def send_cmd(cmd):
    i2cdisplay.writeto(lcd["lcd_address"], bytes([0x80, cmd]))

def send_data(data):
    i2cdisplay.writeto(lcd["lcd_address"], bytes([0x40, data]))

def write_lcd_display(line1, line2): 
    send_cmd(0x01)  # Clear display
    time.sleep_ms(5)
    send_cmd(0x80)  # Move to line 1
    for char in line1:
        send_data(ord(char))
    send_cmd(0xC0)  # Move to line 2
    for char in line2:
        send_data(ord(char))

def get(url): 
    response = None
    data = None
    usable = False
    try:
        # 1. Send the GET request
        response = urequests.get(url)
        
        # 2. Parse the response as JSON (returns a Python dictionary)
        if response.status_code == 200:
            data = response.json()
        else:
            print(f"Error: Received status code {response.status_code}")
            data = None
    except Exception as e:
        print("An error occurred:", e)
        data = None

    else: 
        print(data)
        usable = True

    finally:
        # 4. Always close the response object to free up socket memory
        if response and hasattr(response, 'close'):
            response.close()

    return [usable, data]

# startup tasks startup and clearing the display, connecting to wifi
for c in [0x38, 0x08, 0x01, 0x06, 0x0C]:
    send_cmd(c)
    time.sleep_ms(5)

# connect to Wi-Fi

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, password)

write_lcd_display("Connecting Wi-Fi", ssid)
piicodevdisplay.fill(0)
piicodevdisplay.text("Connecting Wi-Fi", 0,0, 1)
piicodevdisplay.text(ssid, 0,10, 1)
piicodevdisplay.show()

while not wlan.isconnected(): # blocks execution until the device is connected to Wi-Fi
    time.sleep(1)

write_lcd_display("Wi-Fi Connected", wlan.ifconfig()[0])  # Display the IP address
piicodevdisplay.fill(0)
piicodevdisplay.text("Wi-Fi Connected", 0,0, 1)
piicodevdisplay.text(wlan.ifconfig()[0], 0,10, 1)
piicodevdisplay.show()

# pinging section
data = get(fronius_ip + '/solar_api/v1/GetPowerFlowRealtimeData.fcgi')
if data[0] and data[1] is not None and data[1].get('Body', {}).get('Data', {}).get('Version', 0) == "12": 
    site_data = data[1].get('Body', {}).get('Data', {}).get('Site', {})

    dataToDisplay = {
        "autonomy": site_data.get('rel_Autonomy', 0),
        "power": site_data.get('P_PV', 0),
        "grid": site_data.get('P_Grid', 0),
        "load": site_data.get('P_Load', 0),
        "selfConsumption": site_data.get('rel_SelfConsumption', 0)
    }
    for key, value in dataToDisplay.items(): 
        write_lcd_display(str(key), str(value))
        time.sleep(2)
    write_lcd_display("Data Retrieved", "Successfully")