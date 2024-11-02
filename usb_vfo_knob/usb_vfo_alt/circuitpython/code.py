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

last_position = 0
inputstring = ""
fine_mode = True  # Start in fine mode

def out(data):
    serial.write(data.encode())

def update_leds():
    green_led.value = fine_mode
    red_led.value = not fine_mode

update_leds()  # Initialize LEDs

last_switch_state = switch.value
last_toggle_time = time.monotonic()

while True:
    current_switch_state = switch.value
    current_time = time.monotonic()

    if current_switch_state != last_switch_state and (current_time - last_toggle_time) > 0.2:
        if not current_switch_state:  # Switch is pressed (active low)
            fine_mode = not fine_mode
            update_leds()
            last_toggle_time = current_time
        last_switch_state = current_switch_state

    current_position = enc.position
    if current_position != last_position:
        change = current_position - last_position
        if fine_mode:
            change = change // 20  # Finer steps
        else:
            change = change // 1  # Coarser steps
        
        if change != 0:
            new_position = last_position + (change * (1 if fine_mode else 20))
            enc.position = new_position
            out(f"{new_position}\r\n")
        last_position = enc.position

    if serial.in_waiting:
        led.value = True
        incoming = serial.read(serial.in_waiting).decode()
        inputstring += incoming

        if '\r' in inputstring:
            command, inputstring = inputstring.split('\r', 1)
            command = command.strip()
            if command == 'f':
                out(f"{enc.position}\r\n")
            elif command.startswith("F") and len(command.split()) == 2:
                freq = command.split()[1]
                if freq.isdigit():
                    enc.position = int(freq)
                    last_position = enc.position
            elif command == 'whatareyou':
                out("vfoknob\r\n")
        led.value = False

