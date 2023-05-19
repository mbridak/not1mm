"""Fake client to test flrig"""
import xmlrpc.client

TARGET = "http://localhost:12345"
server = xmlrpc.client.ServerProxy(TARGET)

try:  # show the version
    response = server.main.get_version()
    print(f"Version: {response} {type(response)}")
except ConnectionRefusedError as exception:
    print(f"{exception}")
except xmlrpc.client.Fault as exception:
    print(f"{exception}")

try:  # get the vfo
    response = server.rig.get_vfo()
    print(f"VFO: {response} {type(response)}")
except ConnectionRefusedError as exception:
    print(f"{exception}")
except xmlrpc.client.Fault as exception:
    print(f"{exception}")

try:  # set the vfo
    response = server.rig.set_vfo(float(7035000.0))
    print(f"Setting VFO: {response} {type(response)}")
except ConnectionRefusedError as exception:
    print(f"{exception}")
except xmlrpc.client.Fault as exception:
    print(f"{exception}")

try:  # get the vfo
    response = server.rig.get_vfo()
    print(f"VFO: {response} {type(response)}")
except ConnectionRefusedError as exception:
    print(f"{exception}")
except xmlrpc.client.Fault as exception:
    print(f"{exception}")

try:  # set the frequency
    response = server.rig.set_frequency(float(7350000.0))
    print(f"Setting Frequency: {response} {type(response)}")
except ConnectionRefusedError as exception:
    print(f"{exception}")
except xmlrpc.client.Fault as exception:
    print(f"{exception}")


try:  # get the vfo
    response = server.rig.get_vfo()
    print(f"VFO: {response} {type(response)}")
except ConnectionRefusedError as exception:
    print(f"{exception}")
except xmlrpc.client.Fault as exception:
    print(f"{exception}")
