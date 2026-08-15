from machine import I2C, Pin # type: ignore
import time
import network # type: ignore
import urequests
from creds import ssid, password, fronius_ip  # Import credentials from creds.py
from PiicoDev_SSD1306 import * # type: ignore

# configuration
# ssid = 'your_SSID'  # Replace with your Wi-Fi SSID
# password = 'your_PASSWORD'  # Replace with your Wi-Fi password
fronius_ip = '192.168.1.17'  # Replace with your Fronius inverter IP address

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
i2cdisplay = I2C(0, scl=Pin(lcd["scl"]), sda=Pin(lcd["sda"]), freq=100000)
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