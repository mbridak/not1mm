import storage
import board
import digitalio
import time
import supervisor

# Set up the switch
switch = digitalio.DigitalInOut(board.GP20)
switch.direction = digitalio.Direction.INPUT
switch.pull = digitalio.Pull.UP

# Use the green LED on GP19
green_led = digitalio.DigitalInOut(board.GP19)
green_led.direction = digitalio.Direction.OUTPUT

# Wait for 3 seconds, blinking the green LED
start_time = time.monotonic()
while time.monotonic() - start_time < 3:
    green_led.value = True
    time.sleep(0.1)
    green_led.value = False
    time.sleep(0.1)
    
    # Check if the switch is pressed
    if not switch.value:
        green_led.value = True  # Keep green LED on to indicate USB access enabled
        storage.enable_usb_drive()
        supervisor.set_next_code_file(None)
        supervisor.reload()

# If the switch wasn't pressed, disable the USB drive
green_led.value = False  # Turn off green LED
storage.disable_usb_drive()
