from machine import SoftI2C, Pin
import time
import network
import urequests

# configuration
ssid = 'your_SSID'  # Replace with your Wi-Fi SSID
password = 'your_PASSWORD'  # Replace with your Wi-Fi password
fronius_ip = 'fronius_ip'  # Replace with your Fronius inverter IP address

scl = 9
sda = 8
lcd_address = 0x3E
# used functions 

def send_cmd(cmd):
    i2c.writeto(lcd_address, bytes([0x80, cmd]))

def send_data(data):
    i2c.writeto(lcd_address, bytes([0x40, data]))

def write_display(line1, line2): 
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

while not wlan.isconnected(): # blocks execution until the device is connected to Wi-Fi
    time.sleep(1)