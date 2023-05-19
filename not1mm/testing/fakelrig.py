"""Main PC does not have radio attached. So we'll make a fake flrig server."""
import logging
from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.server import SimpleXMLRPCRequestHandler


logging.basicConfig(level=logging.WARNING)


class RequestHandler(SimpleXMLRPCRequestHandler):
    """Doc String"""

    rpc_paths = ("/RPC2",)


def get_vfo():
    """return frequency in hz"""
    return "14032000"


def set_vfo(value):
    """return frequency in hz"""
    print(f"Frequency set to: {value}")
    return


def get_mode():
    """return frequency in hz"""
    return "CW"


def set_mode(value):
    """return frequency in hz"""
    print(f"Mode set to: {value}")
    return


def get_bw():
    """return frequency in hz"""
    return "500"


def get_version():
    """return frequency in hz"""
    return "1.4.8"


print("Stupid server to fake an flrig CAT control server.")

# Create server
with SimpleXMLRPCServer(("0.0.0.0", 12345), allow_none=True) as server:
    server.register_function(get_vfo, name="rig.get_vfo")
    server.register_function(get_mode, name="rig.get_mode")
    server.register_function(set_vfo, name="rig.set_vfo")
    server.register_function(set_mode, name="rig.set_mode")
    server.register_function(get_bw, name="rig.get_bw")
    server.register_function(get_version, name="main.get_version")

    server.register_introspection_functions()
    server.serve_forever()
