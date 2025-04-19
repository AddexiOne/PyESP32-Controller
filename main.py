import machine
import network
from machine import Pin, I2C, RTC
from microdot import Microdot, send_file, Request, Response
from neopixel import NeoPixel
from time import sleep
import ssd1306
import dht

# Constants
NUM_LEDS = 12
LED_PIN = 23
buzzer = machine.PWM(Pin(14), freq=1000)
buzzer.duty_u16(0)
volume = 512
sensor = dht.DHT11(Pin(27))
# Hardware setup
pin = Pin(LED_PIN, Pin.OUT)
np = NeoPixel(pin, NUM_LEDS)
rtc = RTC()
led_clock = False
port_ = 80
# WiFi setup
wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect("AlexiPhone", "titoupute")
while not wifi.isconnected():
    pass

print("Connected to WiFi:", wifi.ifconfig())
# make a single buzz
buzzer.duty_u16(volume)
buzzer.freq(440)  # A4 tone
sleep(0.5)  # Duration of the sound
buzzer.duty_u16(0)  # Turn off the buzzer

# Initialize OLED display
def init_oled():
    i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)
    oled = ssd1306.SSD1306_I2C(128, 32, i2c)
    oled.fill(0)
    return oled


# Display information on OLED
def display_oled_info():
    date_ = rtc.datetime()
    screen.fill(0)
    screen.text(wifi.ifconfig()[0] + f": {port_}", 0, 0)
    screen.text("LED Clock: " + ("On" if led_clock else "Off"), 0, 20)
    screen.text(f"H: {date_[4]}:{date_[5]}:{date_[6]}", 0, 10)
    screen.show()

# Play church bell sound
# Variable pour suivre la dernière minute où la cloche a sonné
last_chime_minute = -1

# Fonction pour jouer la cloche
def play_church_bell():
    global last_chime_minute
    current_time = rtc.datetime()
    minute = current_time[5]

    # Vérifie si c'est le bon moment pour sonner
    if minute in [0, 15, 30, 45] and minute != last_chime_minute:
        last_chime_minute = minute  # Met à jour la dernière minute
        # Calcule le nombre de chimes
        # 1 chime à chaque quart d'heure, 2 chimes à chaque demi-heure, 3 chimes à chaque trois quarts d'heure
        chimes = 1 if minute == 0 else (2 if minute == 30 else 3)

        # Joue les chimes
        for _ in range(chimes):
            buzzer.freq(440)  # A4 tone
            buzzer.duty_u16(volume)  # Utilise le volume réglable
            sleep(0.5)  # Durée de chaque son
            buzzer.duty_u16(0)  # Éteint le buzzer
            sleep(0.5)  # Pause entre les sons

# Fonction pour activer la vérification périodique
def start_chime_timer():
    timer = machine.Timer(2)
    timer.init(period=1000, mode=machine.Timer.PERIODIC, callback=lambda t: play_church_bell())

# Enable LED clock
def enable_led_clock():
    _datetime = rtc.datetime()
    hour = _datetime[4] % 12
    minute = int(_datetime[5] * 0.2)
    second = int(_datetime[6] * 0.2)
    # Clear the previous LED states
    np.fill((0, 0, 0))
    states = [[0, 0, 0] for _ in range(13)]

    for i in range(0, NUM_LEDS):
        if i <= hour:
            states[i][0] = 75
        if i <= minute:
            states[i][1] = 75
        if i <= second:
            states[i][2] = 75

    for i in range(0, NUM_LEDS):
        np[i] = (states[i][0], states[i][1], states[i][2])
    np.write()


# LED animation
def animation():
    colors = [
        (148, 0, 211), (75, 0, 130), (0, 0, 255), (0, 255, 255),
        (0, 255, 0), (173, 255, 47), (255, 255, 0), (255, 165, 0),
        (255, 69, 0), (255, 0, 0), (255, 20, 147), (199, 21, 133)
    ]
    for color in colors:
        for i in range(NUM_LEDS):
            np[i] = color
            np.write()
            sleep(0.01)
    np.fill((0, 0, 0))
    np.write()

def get_temphum():
    while True:
        try:
            sensor.measure()
            temperature = sensor.temperature()
            humidity = sensor.humidity()
            return temperature, humidity
        except OSError as e:
            continue



clock_timer = machine.Timer(-1)
clock_timer.init(period=1000, mode=machine.Timer.PERIODIC, callback=lambda t: display_oled_info())

def clear_led_callback():
    if not led_clock:
        np.fill((0, 0, 0))
        np.write()

clear_led = machine.Timer(-1)
clear_led.init(period=1000, mode=machine.Timer.PERIODIC, callback=lambda t: clear_led_callback())

print("Hello from ESP32!")
screen = init_oled()
display_oled_info()

# Web server setup
app = Microdot()


@app.route("/")
def index(request):
    return send_file("index.html")


@app.post("/init_rtc")
def init_rtc(request: Request):
    data = request.form.get("rtc")
    date, time = data.split("T")
    year, month, day = map(int, date.split("-"))
    hour, minute = map(int, time.split(":"))
    rtc.datetime((year, month, day, 0, hour, minute, 0, 0))

@app.get("/sensor_data")
def get_temp_hum(request: Request):
    temperature, humidity = get_temphum()
    return {"temperature": temperature, "humidity": humidity}

@app.get("/clock_status")
def clock_status(request: Request):
    return {"status": "enabled" if led_clock else "disabled"}

@app.post("/enable_led_clock")
def enable_led_clock_device(request: Request):
    global led_clock
    led_clock = True
    start_chime_timer()
    timer = machine.Timer(1)
    timer.init(period=5000, mode=machine.Timer.PERIODIC, callback=lambda t: enable_led_clock())


@app.post("/disable_led_clock")
def disable_led_clock_device(request: Request):
    global led_clock
    led_clock = False
    timer = machine.Timer(1)
    timer.deinit()
    np.fill((0, 0, 0))
    np.write()


@app.post("/led_animation")
def led_animation(request: Request):
    np.fill((0, 0, 0))
    animation()


# Main function
def main():
    app.run(host="0.0.0.0", port=port_, debug=True)
    print(f"Web server running on port {port_}")
    display_oled_info()


if __name__ == "__main__":
    main()
