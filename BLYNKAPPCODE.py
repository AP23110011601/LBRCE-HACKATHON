from machine import Pin, ADC
import network, time, dht
from BlynkLib import Blynk
import BlynkLib
blynk = BlynkLib.Blynk('WZGOoNTn9bplmZ-EUusXL_gUYgGXTKdK', server='blynk.cloud', port=80)

# ====== CONFIG ======
WIFI_SSID = "kusuma"
WIFI_PASS = "12345678"
BLYNK_AUTH = "WZGOoNTn9bplmZ-EUusXL_gUYgGXTKdK"

# ====== SENSOR PINS ======
soil = ADC(Pin(34)); soil.atten(ADC.ATTN_11DB)
tank = ADC(Pin(35)); tank.atten(ADC.ATTN_11DB)
rain = Pin(22, Pin.IN)
relay = Pin(13, Pin.OUT); relay.value(1)  # OFF initially
dht_sensor = dht.DHT11(Pin(4))

# ====== THRESHOLDS ======
dry_threshold = 2700
wet_threshold = 2300
tank_low_threshold = 1500

# ====== VARIABLES ======
mode_auto = True
relay_state = 1  # 1 = off, 0 = on
manual_timer = 0

# ====== CONNECT WIFI ======
wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect(WIFI_SSID, WIFI_PASS)
print("Connecting to WiFi...")
while not wifi.isconnected():
    time.sleep(1)
print("Connected! IP:", wifi.ifconfig()[0])

# ====== START BLYNK ======
blynk = Blynk(BLYNK_AUTH)

# ====== FUNCTIONS ======
def pump_control(state):
    global relay_state
    relay.value(0 if state else 1)
    relay_state = 0 if state else 1
    blynk.virtual_write(7, 1 if state else 0)  # Update button

def read_sensors():
    try:
        dht_sensor.measure()
        temp = dht_sensor.temperature()
        hum = dht_sensor.humidity()
    except:
        temp, hum = 0, 0
    soil_val = soil.read()
    tank_val = tank.read()
    rain_val = rain.value()

    # Soil
    if soil_val > dry_threshold:
        soil_msg = "Soil Dry"
    elif soil_val < wet_threshold:
        soil_msg = "Soil Wet"
    else:
        soil_msg = "Soil Moist"

    # Tank
    if tank_val < tank_low_threshold:
        tank_msg = "Tank Low"
    else:
        tank_msg = "Tank OK"

    rain_msg = "Rain" if rain_val == 0 else "No Rain"

    return soil_val, soil_msg, tank_val, tank_msg, rain_msg, temp, hum

# ====== BLYNK HANDLERS ======
@blynk.on("V8")
def mode_control(value):
    global mode_auto
    mode_auto = (int(value[0]) == 1)
    print("Mode:", "Auto" if mode_auto else "Manual")

@blynk.on("V7")
def manual_pump(value):
    global manual_timer
    if not mode_auto:
        if int(value[0]) == 1:
            pump_control(True)
            manual_timer = time.time()
        else:
            pump_control(False)

# ====== MAIN LOOP ======
while True:
    blynk.run()

    soil_val, soil_msg, tank_val, tank_msg, rain_msg, temp, hum = read_sensors()

    # AUTO MODE
    if mode_auto:
        if rain_msg == "Rain":
            pump_control(False)
        elif soil_msg == "Soil Dry" and rain_msg == "No Rain":
            pump_control(True)
        else:
            pump_control(False)

    # MANUAL AUTO-OFF (after 10 sec)
    if not mode_auto and relay_state == 0 and (time.time() - manual_timer > 10):
        pump_control(False)

    # RAIN OVERRIDE (all modes)
    if rain_msg == "Rain":
        pump_control(False)

    # UPDATE BLYNK VALUES
    blynk.virtual_write(0, soil_val)
    blynk.virtual_write(1, soil_msg)
    blynk.virtual_write(2, tank_val)
    blynk.virtual_write(3, tank_msg)
    blynk.virtual_write(4, rain_msg)
    blynk.virtual_write(5, temp)
    blynk.virtual_write(6, hum)

    print(f"Soil:{soil_val}({soil_msg}) Tank:{tank_val}({tank_msg}) Rain:{rain_msg} Temp:{temp} Hum:{hum} Pump:{'ON' if relay_state==0 else 'OFF'} Mode:{'Auto' if mode_auto else 'Manual'}")
    time.sleep(5)
