from machine import Pin
import time

# --- Pin configuration ---
RELAY_PIN = 25          # Relay IN

LED_PINS = [13, 12, 14, 27, 26]  # One pin per LED anode

# --- Setup ---
relay = Pin(RELAY_PIN, Pin.OUT)
relay.value(0)  # Start with relay OFF

leds = [Pin(p, Pin.OUT) for p in LED_PINS]
for led in leds:
    led.value(0)  # Start with all LEDs off


# --- Helper functions ---

def relay_on():
    relay.value(1)
    print("Relay ON")

def relay_off():
    relay.value(0)
    print("Relay OFF")

def set_led(index, state):
    """Turn a single LED on (1) or off (0). Index 0-4."""
    leds[index].value(state)

def all_leds_on():
    for led in leds:
        led.value(1)

def all_leds_off():
    for led in leds:
        led.value(0)

def leds_blink(times=3, delay_ms=300):
    """Blink all LEDs a number of times."""
    for _ in range(times):
        all_leds_on()
        time.sleep_ms(delay_ms)
        all_leds_off()
        time.sleep_ms(delay_ms)

def leds_chase(times=2, delay_ms=100):
    """Knight Rider-style chase effect."""
    for _ in range(times):
        for i in range(5):
            all_leds_off()
            set_led(i, 1)
            time.sleep_ms(delay_ms)
        for i in range(3, -1, -1):
            all_leds_off()
            set_led(i, 1)
            time.sleep_ms(delay_ms)
    all_leds_off()


# --- Main demo loop ---
print("Starting demo...")

while True:
    # Turn relay on, blink all LEDs
    relay_on()
    leds_blink(times=3, delay_ms=300)
    time.sleep(1)

    # Chase effect while relay stays on
    leds_chase(times=2, delay_ms=120)
    time.sleep(1)

    # Turn everything off
    relay_off()
    all_leds_off()
    time.sleep(2)