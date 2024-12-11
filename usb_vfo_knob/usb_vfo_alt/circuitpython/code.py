import rotaryio
import time
from board import *
import digitalio
import usb_cdc

led = digitalio.DigitalInOut(LED)
led.direction = digitalio.Direction.OUTPUT

green_led = digitalio.DigitalInOut(GP19)
green_led.direction = digitalio.Direction.OUTPUT

red_led = digitalio.DigitalInOut(GP18)
red_led.direction = digitalio.Direction.OUTPUT

switch = digitalio.DigitalInOut(GP20)
switch.direction = digitalio.Direction.INPUT
switch.pull = digitalio.Pull.UP

serial = usb_cdc.console

enc = rotaryio.IncrementalEncoder(GP22, GP21)
enc.position = 0

last_position = None
inputstring = ""
fine_mode = True  # Start in fine mode

def out(data):
    usb_cdc.console.write(data.encode())

def update_leds():
    green_led.value = fine_mode
    red_led.value = not fine_mode

update_leds()  # Initialize LEDs

last_switch_state = switch.value
last_toggle_time = time.monotonic()

while True:
    current_time = time.monotonic()
    current_switch_state = switch.value

    if current_switch_state != last_switch_state and (current_time - last_toggle_time) > 0.2:
        if current_switch_state == False:  # Switch is pressed (active low)
            fine_mode = not fine_mode
            update_leds()
            last_toggle_time = current_time
        last_switch_state = current_switch_state

    current_position = enc.position
    if last_position is None:
        last_position = current_position
    
    if current_position != last_position:
        change = current_position - last_position
        if fine_mode:
            change = change // 20  # Finer steps
        else:
            change = change // 1  # Coarser steps
        
        if change != 0:
            enc.position = last_position + (change * (1 if fine_mode else 20))
            out(f"{enc.position}\r\n")
        last_position = enc.position

    if usb_cdc.console.in_waiting:
        led.value = True
        incoming = usb_cdc.console.read(usb_cdc.console.in_waiting)
        inputstring = inputstring + incoming.decode()

        if inputstring[-1] == "\r":
            if inputstring.strip() == 'f':
                position = enc.position
                out(f"{position}\r\n")
            if inputstring[0] == "F" and len(inputstring.strip().split()) == 2:
                freq = inputstring.strip().split()[1]
                if freq.isdigit():
                    enc.position = int(freq)
                    last_position = enc.position
            if inputstring.strip() == 'whatareyou':
                out("vfoknob\r\n")
            inputstring = ""
        led.value = False

    time.sleep(0.01)  # Small delay to prevent busy-waiting
