import pyroslib

host, port = pyroslib.get_connection_details()

print(f"DISCOVERY-PYROS: running pyros on MQTT server {host}:{port}")

# TODO check if host is local IP, too...
if host == 'localhost' or host == '127.0.0.1':
    print(f"DISCOVERY-PYROS: Registered PYROS on port {port} with discovery service.")
    discovery.register_service("PYROS", str(port))
else:
    print("DISCOVERY-PYROS: This is not local Pyros - not registering PYROS with discovery service.")
