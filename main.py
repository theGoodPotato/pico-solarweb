from machine import I2C, Pin, ADC, reset # type: ignore
import asyncio # type: ignore
import time
import network # type: ignore
import urequests
from creds import ssid, password  # Import credentials from creds.py
from PiicoDev_SSD1306 import create_PiicoDev_SSD1306 # type: ignore
import time
import gc

# configuration
# ssid = 'your_SSID'  # Replace with your Wi-Fi SSID
# password = 'your_PASSWORD'  # Replace with your Wi-Fi password
fronius_ip = 'http://192.168.1.17'  # Replace with your Fronius inverter IP address
delay = 3
interval_to_send = 60
battery_voltage_full = 1.4 * 3 # Replace with your COMBINED battery voltage
battery_voltage_empty = 1.1 * 3 # Replace with your COMBINED battery voltage when empty

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
# cycle = [0]

state = {
    "dataToDisplay": {},
    "vsys": 0.0,
}

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
        response = urequests.get(url, timeout=5)  # Set a timeout of 5 seconds
        
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
        gc.collect()

    return [usable, data]

async def fetch_data():
    while True:
        data = get(fronius_ip + '/solar_api/v1/GetPowerFlowRealtimeData.fcgi')
        if len(data) < 2 or data[0] is False or data[1] is None: 
            pass
        elif data[0] and data[1] is not None and data[1].get('Body', {}).get('Data', {}).get('Version', 0) == "12": 
            site_data = data[1].get('Body', {}).get('Data', {}).get('Site', {})
            state["dataToDisplay"] = {
                "Autonomy": str(site_data.get('rel_Autonomy', 0)) + "%" if site_data.get('rel_Autonomy', 0) is not None else "N/A",
                "Current Production": str(site_data.get('P_PV', 0)) + " W" if site_data.get('P_PV', 0) is not None else "N/A",
                "Grid Interaction": str(site_data.get('P_Grid', 0)) + " W" if site_data.get('P_Grid', 0) is not None else "N/A",
                "Consumption": str(site_data.get('P_Load', 0)) + " W" if site_data.get('P_Load', 0) is not None else "N/A",
                "Self Consumption": str(site_data.get('rel_SelfConsumption', 0)) + "%" if site_data.get('rel_SelfConsumption', 0) is not None else "N/A",
                "S Battery Power": str(site_data.get('P_Akku', 0)) + " W" if site_data.get('P_Akku', 0) is not None else "N/A",
                "Generation Today": str(site_data.get('E_Day', 0)) + " kWh" if site_data.get('E_Day', 0) is not None else "N/A",
            }
        await asyncio.sleep(30)

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


async def ensure_wifi():
    if wlan.isconnected():
        return True
    wlan.active(True)
    try:
        wlan.config(pm=0xa11140)  # Disables Wi-Fi power save mode
    except Exception:
        pass

    wlan.connect(ssid, password)
    
    for _ in range(15):
        if wlan.isconnected():
            return True
        await asyncio.sleep(1)

    return False

# pinging section

async def display_lcd(): 
    write_lcd_display("SolarWeb Display", "Stats Fetching")
    await asyncio.sleep(delay)
    while True: 
        if not wlan.isconnected():
            write_lcd_display("Wi-Fi Lost", "Reconnecting...")
            piicodevdisplay.fill(0)
            piicodevdisplay.text("Wi-Fi Lost", 0, 0, 1)
            piicodevdisplay.text("Reconnecting...", 0, 12, 1)
            piicodevdisplay.show()
            
            if not await ensure_wifi():
                await asyncio.sleep(5)  # Pause before trying again
                continue  # Skip displaying stats until reconnected
        current_vsys = get_vsys_voltage()
        write_lcd_display("Current V:" + str(current_vsys), "USB Power" if current_vsys > 4.65 else "Battery Power")
        await asyncio.sleep(delay)
        if current_vsys < 4.65: 
            write_lcd_display("B Percentage", str(((current_vsys - battery_voltage_empty) / (battery_voltage_full - battery_voltage_empty)) * 100) + "%")
            await asyncio.sleep(delay)
        write_lcd_display("Wi-Fi Connected", wlan.ifconfig()[0])  # Display the IP address
        await asyncio.sleep(delay)
        displaying_data = state["dataToDisplay"]
        for key, value in displaying_data.items(): 
            # if value == "N/A": 
            #     continue
            write_lcd_display(str(key), str(value))
            await asyncio.sleep(delay)
        # cycle[0] += 1
        # cycle.append(state["dataToDisplay"])
        # if cycle[0] == interval_to_send: 
        #     pass # for later use, send to a server

async def main():
    can_continue = True
    try: 
        # startup tasks startup and clearing the display, connecting to wifi
        for c in [0x38, 0x08, 0x01, 0x06, 0x0C]:
            send_cmd(c)
            await asyncio.sleep_ms(5)

        write_lcd_display("Starting up...", "Please wait")

        # connect to Wi-Fi
        network.hostname("pico_solarweb_display")
        global wlan
        wlan = network.WLAN(network.STA_IF)

        write_lcd_display("Connecting Wi-Fi", ssid)
        piicodevdisplay.fill(0)
        piicodevdisplay.text("Connecting Wi-Fi", 0, 0, 1)
        piicodevdisplay.text(ssid, 0, 10, 1)
        piicodevdisplay.show()

        connected = await ensure_wifi()
        if not connected:
            write_lcd_display("Wi-Fi Failed", "Retrying in background")
            await asyncio.sleep(2)
        else:
            ip = wlan.ifconfig()[0]
            write_lcd_display("Wi-Fi Connected", ip)
            piicodevdisplay.fill(0)
            piicodevdisplay.text("Wi-Fi Connected", 0, 0, 1)
            piicodevdisplay.text(ip, 0, 10, 1)
            piicodevdisplay.show()
            await asyncio.sleep(2)

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
        can_continue = False
    if can_continue: 
        try: 
            asyncio.create_task(fetch_data())
            asyncio.create_task(display_lcd())
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            try: 
                write_lcd_display("","")
            except: 
                from picozero import pico_led # type: ignore
                pico_led.on()
                time.sleep(delay)
                reset()

if __name__ == "__main__":
    asyncio.run(main())