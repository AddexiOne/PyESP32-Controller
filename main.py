import machine
import network
from machine import Pin, I2C, RTC
from microdot import Microdot, send_file, Request
from neopixel import NeoPixel
from time import sleep
import ssd1306

# Constants
NUM_LEDS = 12
LED_PIN = 23

# Hardware setup
pin = Pin(LED_PIN, Pin.OUT)
np = NeoPixel(pin, NUM_LEDS)
rtc = RTC()
led_clock = False
port_ = 80


# Initialize OLED display
def init_oled():
    i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)
    oled = ssd1306.SSD1306_I2C(128, 32, i2c)
    oled.fill(0)
    return oled

# Display information on OLED
def display_oled_info():
    screen.fill(0)
    screen.text("Ip: " +wifi.ifconfig()[0], 0, 0)
    screen.text("Port: " + port_, 0, 10)
    screen.text("LED Clock: " + ("On" if led_clock else "Off"), 0, 20)
    screen.show()

# Enable LED clock
def enable_led_clock():
    hour = rtc.datetime()[4]%12
    minute = int(rtc.datetime()[5]*NUM_LEDS/60)
    second = int(rtc.datetime()[6]*NUM_LEDS/60)
    # Clear the previous LED states
    np.fill((0,0,0))
    states = [
        [0,0,0],
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
    ]

    for i in range(0, hour):
        states[i][0] = 125
    for i in range(0, minute):
        states[i][1] = 125
    for i in range(0, second):
        states[i][2] = 125

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

print("Hello from ESP32!")
screen = init_oled()
display_oled_info(screen, "Connecting...", "Off")

# WiFi setup
wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect("AlexiPhone", "titoupute")
while not wifi.isconnected():
    pass

print("Connected to WiFi:", wifi.ifconfig())
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
    rtc.datetime((year, month, day, 0, hour + 2, minute, 0, 0))

@app.post("/enable_led_clock")
def enable_led_clock_device(request: Request):
    global led_clock
    led_clock = True
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
    global led_clock
    led_clock = False
    timer = machine.Timer(1)
    timer.deinit()
    animation()

app.after_request_handlers.append(lambda t: display_oled_info())

# Main function
def main():
    app.run(host="0.0.0.0", port=port_, debug=True)
    print(f"Web server running on port {port_}")
    display_oled_info()


if __name__ == "__main__":
    main()