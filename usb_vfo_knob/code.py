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

    
