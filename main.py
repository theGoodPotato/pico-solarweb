from machine import Pin
import time
import network
import urequests

# configuration
ssid = 'your_SSID'  # Replace with your Wi-Fi SSID
password = 'your_PASSWORD'  # Replace with your Wi-Fi password
fronius_ip = 'fronius_ip'  # Replace with your Fronius inverter IP address
button = Pin(0, Pin.IN, Pin.PULL_UP)  # Button connected

# connect to Wi-Fi

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, password)

while not wlan.isconnected(): # blocks execution until the device is connected to Wi-Fi
    time.sleep(1)

def button_pressed(pin):
    global active
    active = True


button.irq(trigger=Pin.IRQ_FALLING, handler=button_pressed)  # Interrupt on button press

while True: 
    if active: 
        urequest = urequests.get(str(fronius_ip + '/solar_api/GetInverterRealtimeData.cgi'))