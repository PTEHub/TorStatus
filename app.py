# Tor Network Analysis Tool - September 2024
# Author: PTEHub
import json
import geoip2.database
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from flask import jsonify
import threading
import queue
import time

import sys
from stem import CircStatus
import stem

from utils.torstem import TorSingleton
import eventlet
eventlet.monkey_patch()

app = Flask(__name__)
socketio = SocketIO(app, async_mode='eventlet', ping_timeout=60, ping_interval=25, logger=True, engineio_logger=True)

data_queue = queue.Queue()
geoip_reader = geoip2.database.Reader('./geoip/GeoLite2-City.mmdb')  # Ensure this path is correct

# Tor authentication information
TOR_PASSWORD = 'welcome'
TOR_PORT = 8052

# Global variables to track network data
last_upload = 0
last_download = 0
last_time = time.time()

local_public_ip = {
    "ip": "8.8.8.8",
    "latitude": 37.5308,
    "longitude": 126.8751,
    "country": "kr",
    "type": "Local"
},

def get_node_details(ip_address, geoip_reader, controller):
    """Get details of a Tor node including geolocation."""
    try:
        response = geoip_reader.city(ip_address)
        country_info = controller.get_info(f"ip-to-country/{ip_address}")
        country_name = country_info.strip() if country_info else "N/A"
        return {
            "ip": ip_address,
            "country": country_name,
            "bandwidth": "N/A",
            "latitude": response.location.latitude,
            "longitude": response.location.longitude
        }
    except (geoip2.errors.AddressNotFoundError, Exception):
        return {
            "ip": ip_address,
            "country": "N/A",
            "bandwidth": "N/A",
            "latitude": "N/A",
            "longitude": "N/A"
        }


def get_bandwidth(fingerprint, controller):
    """Get bandwidth of a Tor node."""
    try:
        status_entry = controller.get_network_status(fingerprint)
        return status_entry.bandwidth if status_entry else "N/A"
    except Exception:
        return "N/A"


def collect_tor_nodes():
    """Collect information about Tor nodes in the current circuits."""
    nodes = []
    with geoip2.database.Reader('./geoip/GeoLite2-City.mmdb') as geoip_reader:
        tor = TorSingleton()
        tor.connect(password=TOR_PASSWORD, port=TOR_PORT)
        controller = tor.get_controller()
        circuits = controller.get_circuits()
        for circuit in circuits:
            if circuit.status == 'BUILT':
                for i, (relay, nickname) in enumerate(circuit.path):
                    relay_desc = controller.get_network_status(relay, None)
                    if relay_desc:
                        ip_address = relay_desc.address
                        if not any(node['ip'] == ip_address for node in nodes):
                            node_details = get_node_details(ip_address, geoip_reader, controller)
                            node_details["bandwidth"] = get_bandwidth(relay, controller)
                            node_details["type"] = "Entry" if i == 0 else "Exit" if i == len(
                                circuit.path) - 1 else "Middle"
                            nodes.append(node_details)

    return nodes


def get_tor_network_data():
    """Get current Tor network data including upload and download speeds."""
    global last_upload, last_download, last_time
    tor = TorSingleton()
    tor.connect(password=TOR_PASSWORD, port=TOR_PORT)
    controller = tor.get_controller()

    current_upload = int(controller.get_info("traffic/written"))
    current_download = int(controller.get_info("traffic/read"))
    current_time = time.time()

    time_diff = current_time - last_time if last_time else 1

    upload_speed = (current_upload - last_upload) / 1024 / time_diff if last_upload else 0
    download_speed = (current_download - last_download) / 1024 / time_diff if last_download else 0

    last_upload = current_upload
    last_download = current_download
    last_time = current_time

    return {
        "timestamp": time.strftime('%H:%M:%S'),
        "upload": round(upload_speed, 2),  # Upload speed in KB/s
        "download": round(download_speed, 2)  # Download speed in KB/s
    }


def get_geolocation(controller, ip):
    """Get geolocation information for an IP address."""
    try:
        response = geoip_reader.city(ip)
        country_info = controller.get_info(f"ip-to-country/{ip}")
        country_name = country_info.strip() if country_info else "N/A"
        return {
            "latitude": response.location.latitude,
            "longitude": response.location.longitude,
            "country": country_name
        }
    except geoip2.errors.AddressNotFoundError:
        return {
            "latitude": None,
            "longitude": None,
            "country": None
        }


def extract_ip(address):
    """Extract IP address from a string that may contain a port."""
    return address.split(':')[0] if ':' in address else address


def update_stream_handler(controller, stream_event):
    global local_public_ip
    """Handle Tor stream events."""
    print(f"stream_event.status {stream_event.status}")
    if stream_event.status not in [stem.StreamStatus.SUCCEEDED]:
        print(f"Skipping stream event with status: {stream_event.status}")
        return

    stream_target = stream_event.target
    circuit_id = stream_event.circ_id

    if not circuit_id:
        print(f"No circuit ID associated with the stream target {stream_target}")
        return

    try:
        circuit = controller.get_circuit(circuit_id)
    except stem.ControllerError as e:
        print(f"Failed to retrieve circuit {circuit_id}: {e}")
        return

    if not circuit.path:
        print(f"No path found for circuit ID {circuit_id}")
        return

    path = []
    for i, (fingerprint, nickname) in enumerate(circuit.path):
        ip, bandwidth = get_node_ip_and_bandwidth(controller, fingerprint)
        geolocation = get_geolocation(controller, ip)
        node_info = {
            "fingerprint": fingerprint,
            "nickname": nickname,
            "ip": ip,
            "country": geolocation["country"],
            "bandwidth": bandwidth,
            "type": "Entry" if i == 0 else "Exit" if i == len(circuit.path) - 1 else "Middle",
            "latitude": geolocation["latitude"],
            "longitude": geolocation["longitude"]
        }
        path.append(node_info)

    target_ip = extract_ip(stream_target)
    target_geolocation = get_geolocation(controller, target_ip)

    circuit_info = {
        "status": stream_event.status,
        "stream_target": stream_target,
        "target_geolocation": target_geolocation,
        "circuit_id": circuit_id,
        "local_public_ip": local_public_ip,
        "path": path
    }

    data = json.dumps(circuit_info, indent=4)
    print(f"Status Listener: Generated data: {data}")
    data_queue.put(data)
    data_queue.join()


def circuit_event_handler(event):
    """Handle Tor circuit events."""
    if event.status not in [CircStatus.BUILT]:
        print(f"Skipping circuit event with status: {event.status}")
        return
    circuit_info = {
        "status": event.status
    }
    data = json.dumps(circuit_info, indent=4)
    print(f"Status Listener: Generated data: {data}")
    data_queue.put(data)
    data_queue.join()
    print(f"Circuit {event.id} has been built with path: {event.path}")


def get_node_ip_and_bandwidth(controller, fingerprint):
    """Get IP and bandwidth information for a Tor node."""
    try:
        status_entry = controller.get_network_status(fingerprint)
        if status_entry:
            ip = status_entry.address
            bandwidth = (status_entry.bandwidth)
            return ip, bandwidth
        else:
            return "Unknown", "Unknown"
    except stem.OperationFailed:
        return "Unknown", "Unknown"


def status_listener():
    """Listen for Tor stream and circuit events."""
    try:
        tor = TorSingleton()
        tor.connect(password=TOR_PASSWORD, port=TOR_PORT)
        controller = tor.get_controller()
        controller.authenticate(TOR_PASSWORD)  # Ensure this password is correct
        controller.add_event_listener(
            lambda stream_event: update_stream_handler(controller, stream_event),
            stem.control.EventType.STREAM)

        controller.add_event_listener(circuit_event_handler, stem.control.EventType.CIRC)

        print("Listening for Tor stream events... Press Ctrl+C to exit.")
        while True:
            socketio.sleep(1)

    except stem.SocketError as exc:
        print(f"Unable to connect to Tor: {exc}")
        sys.exit(1)


def data_processor():
    """Process data from the queue and emit to Socket.IO clients."""
    while True:
        data = data_queue.get()
        parsed_json = json.loads(data)
        status = parsed_json["status"]

        if status in [stem.StreamStatus.SUCCEEDED]:
            print(f"Data Processor: Processing data: {data}")
            socketio.emit(f'{stem.StreamStatus.SUCCEEDED}', {'data': data})

        if status in [CircStatus.BUILT]:
            print(f"Data Processor: Processing data: {data}")
            SendData = json.dumps(collect_tor_nodes(), indent=4)
            socketio.emit(f'{CircStatus.BUILT}', {'data': SendData})
        data_queue.task_done()


@socketio.on('connect')
def handle_connect():
    """Handle client connection to Socket.IO."""
    print("Client connected.")
    emit('status_update', {'data': 'Welcome, you are connected!'})
    SendData = json.dumps(collect_tor_nodes(), indent=4)
    emit(f'{CircStatus.BUILT}', {'data': SendData})


@socketio.on('message')
def handle_message(message):
    """Handle messages from Socket.IO clients."""
    print(f"Received message from client: {message}")
    emit('status_update', {'data': f"Server received: {message}"})


@socketio.event
def my_ping():
    """Respond to ping events from Socket.IO clients."""
    emit('my_pong')


@socketio.event
def updateNodes():
    """Update and send current Tor node information to clients."""
    SendData = json.dumps(collect_tor_nodes(), indent=4)
    emit(f'{CircStatus.BUILT}', {'data': SendData})


@app.route('/')
def index():
    """Render the main page."""
    return render_template('tor.html')


@app.route('/data')
def data():
    """Provide current Tor network data as JSON."""
    return jsonify(get_tor_network_data())


if __name__ == '__main__':
    status_thread = threading.Thread(target=status_listener)
    status_thread.daemon = True
    status_thread.start()

    processor_thread = threading.Thread(target=data_processor)
    processor_thread.daemon = True
    processor_thread.start()

    try:
        socketio.run(app, debug=True, host='0.0.0.0', port=505, use_reloader=False)
    finally:
        geoip_reader.close()  # Ensure GeoIP database is closed when the program ends
