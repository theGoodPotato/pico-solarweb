from machine import I2C, Pin, ADC, reset # type: ignore
import time
import network # type: ignore
import urequests
from creds import ssid, password  # Import credentials from creds.py
from PiicoDev_SSD1306 import * # type: ignore
import time

# configuration
# ssid = 'your_SSID'  # Replace with your Wi-Fi SSID
# password = 'your_PASSWORD'  # Replace with your Wi-Fi password
fronius_ip = 'http://192.168.1.17'  # Replace with your Fronius inverter IP address
delay = 5
interval_to_send = 60
battery_voltage_full = 1.4 * 3 # Replace with your COMBINED battery voltage
battery_voltage_empty = 0 * 3 # Replace with your COMBINED battery voltage when empty

lcd = {
    "scl": 19,
    "sda": 18,
    "lcd_address": 0x3E,
    "processor": 1
}

piicodev = {
    "sda": 8,
    "scl": 9,
    "lcd_address": 0x3C,
}

# used functions and code
i2cdisplay = I2C(lcd["processor"], scl=Pin(lcd["scl"]), sda=Pin(lcd["sda"]), freq=400000)
piicodevdisplay = create_PiicoDev_SSD1306(bus=0, freq=400000,scl=Pin(piicodev["scl"]), sda=Pin(piicodev["sda"])) # type: ignore
cycle = [0]

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

def get_vsys_voltage():
    # 1. Enable VSYS sense line (required for Pico W / Pico 2 W)
    pin25 = Pin(25, Pin.OUT, pull=Pin.PULL_DOWN)
    pin25.high()
    
    # 2. Read ADC channel 3 on GPIO 29
    Pin(29, Pin.IN)
    vsys_adc = ADC(3)
    raw_val = vsys_adc.read_u16()
    
    # 3. Restore GPIO 29 for CYW43 Wi-Fi module
    Pin(29, Pin.ALT, pull=Pin.PULL_DOWN, alt=7)
    
    # Convert raw ADC value to voltage across 1:3 divider
    return (raw_val * 3.3 / 65535) * 3

try: 
    # startup tasks startup and clearing the display, connecting to wifi
    for c in [0x38, 0x08, 0x01, 0x06, 0x0C]:
        send_cmd(c)
        time.sleep_ms(5)

    write_lcd_display("Starting up...", "Please wait")

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
except KeyboardInterrupt:
    try: 
        write_lcd_display("","")
    except: 
        from picozero import pico_led # type: ignore
        pico_led.on()
        time.sleep(delay)
        reset()
except: 
    from picozero import pico_led # type: ignore
    pico_led.on()

# pinging section

try: 
    write_lcd_display("SolarWeb Display", "Stats Fetching")
    time.sleep(delay)
    while True: 
        while not wlan.isconnected():
            write_lcd_display("Wi-Fi Disconnected", "Reconnecting...")
            time.sleep(5)
            wlan.connect(ssid, password)
        write_lcd_display("Current V:" + str(get_vsys_voltage()), "USB Power" if get_vsys_voltage() > 4.65 else "Battery Power")
        time.sleep(delay)
        if get_vsys_voltage() < 4.65: 
            write_lcd_display("B Percentage", str(((get_vsys_voltage() - battery_voltage_empty) / (battery_voltage_full - battery_voltage_empty)) * 100) + "%")
            time.sleep(delay)
        time.sleep(delay)
        write_lcd_display("Wi-Fi Connected", wlan.ifconfig()[0])  # Display the IP address
        time.sleep(delay)
        data = get(fronius_ip + '/solar_api/v1/GetPowerFlowRealtimeData.fcgi')
        if data[0] and data[1] is not None and data[1].get('Body', {}).get('Data', {}).get('Version', 0) == "12": 
            site_data = data[1].get('Body', {}).get('Data', {}).get('Site', {})

            dataToDisplay = {
                "Autonomy": str(site_data.get('rel_Autonomy', 0)) + "%" if site_data.get('rel_Autonomy', 0) is not None else "N/A",
                "Current Production": str(site_data.get('P_PV', 0)) + " W" if site_data.get('P_PV', 0) is not None else "N/A",
                "Grid Interaction": str(site_data.get('P_Grid', 0)) + " W" if site_data.get('P_Grid', 0) is not None else "N/A",
                "Consumption": str(site_data.get('P_Load', 0)) + " W" if site_data.get('P_Load', 0) is not None else "N/A",
                "Self Consumption": str(site_data.get('rel_SelfConsumption', 0)) + "%" if site_data.get('rel_SelfConsumption', 0) is not None else "N/A",
                "S Battery Power": str(site_data.get('P_Akku', 0)) + " W" if site_data.get('P_Akku', 0) is not None else "N/A",
                "Generation Today": str(site_data.get('E_Day', 0)) + " kWh" if site_data.get('E_Day', 0) is not None else "N/A",
            }
            for key, value in dataToDisplay.items(): 
                if value == "N/A": 
                    continue
                write_lcd_display(str(key), str(value))
                time.sleep(delay)
        cycle[0] += 1
        cycle.append(dataToDisplay)
        if cycle[0] == interval_to_send: 
            pass # for later use, send to a server

except KeyboardInterrupt: 
    write_lcd_display("","")