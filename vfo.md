# VFO USB Knob

## The Idea

It was brought up and decided that there should be some facility to accommodate fine tuning the VFO if the user happened to be using a remote rig. Further it was agreed that some sort of USB VFO knob would be the best fit.

## The Hardware

I've paired a Raspberry Pico with a cheap but decent [rotary encoder](https://www.amazon.com/dp/B07JM9YRTQ?psc=1&ref=ppx_yo2ov_dt_b_product_details) that has no detents, so smooth rotation. The two together were under 20 bucks.

The encoder can operate between 5-24V, and has 600 pulses per revolution. 4 wires from the encoder are VCC and GND for power, and A+, B+ for pulses.

Even though the Pico is a 3.3v device, the 5v can be pulled from the Pico's VBUS terminal.

So connect the encoder VCC to VBUS, GND to GND, A+ to GPIO22 and B+ to GPIO21.

![Rotary Encoder](https://github.com/mbridak/not1mm/raw/master/pic/encoder.jpg)

## The Firmware

Load the Pico with CircuitPython. Copy the script below over to the Pico and call it `code.py`

```python
import rotaryio
import time
from board import *
import usb_cdc

serial = usb_cdc.console

enc = rotaryio.IncrementalEncoder(GP22, GP21,3)
enc.position = 0
last_position = None
inputstring = ""

def out(data):
    usb_cdc.console.write(data.encode())
    
while True:
    if usb_cdc.console.in_waiting:
        incomming = usb_cdc.console.read(usb_cdc.console.in_waiting)
        inputstring = inputstring + incomming.decode()
        if inputstring[-1] == "\r":
            if inputstring.strip() == 'f':
                position = enc.position
                out(f"{position}\r\n")
            if inputstring[0] == "F" and len(inputstring.strip().split()) == 2:
                freq = inputstring.strip().split()[1]
                if freq.isdigit():
                    enc.position = int(freq)
            inputstring = ""
```

Reading and setting the frequency from the serial device is pretty simple. To set the frequency you send it for example 'F 14032000\r'. To get the current frequency from the device just send it 'f\r'. It will report back just the frequency '14032000'.