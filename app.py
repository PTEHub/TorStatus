import json
import geoip2.database
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
import threading
import queue
import time
from stem import CircStatus
import stem
from utils.torstem import TorSingleton
import eventlet

eventlet.monkey_patch()


class TorNetworkAnalyzer:
    def __init__(self, tor_password, tor_port, geoip_db_path):
        self.tor_password = tor_password
        self.tor_port = tor_port
        self.geoip_reader = geoip2.database.Reader(geoip_db_path)
        self.data_queue = queue.Queue()
        self.last_upload = 0
        self.last_download = 0
        self.last_time = time.time()
        self.controller = None

    def initialize_tor_controller(self):
        tor = TorSingleton()
        tor.connect(password=self.tor_password, port=self.tor_port)
        self.controller = tor.get_controller()
        self.controller.authenticate(self.tor_password)

    def get_node_details(self, ip_address):
        try:
            response = self.geoip_reader.city(ip_address)
            country_info = self.controller.get_info(f"ip-to-country/{ip_address}")
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

    def get_bandwidth(self, fingerprint):
        try:
            status_entry = self.controller.get_network_status(fingerprint)
            return status_entry.bandwidth if status_entry else "N/A"
        except Exception:
            return "N/A"

    def collect_tor_nodes(self):
        nodes = []
        circuits = self.controller.get_circuits()
        for circuit in circuits:
            if circuit.status == 'BUILT':
                for i, (relay, nickname) in enumerate(circuit.path):
                    relay_desc = self.controller.get_network_status(relay, None)
                    if relay_desc:
                        ip_address = relay_desc.address
                        if not any(node['ip'] == ip_address for node in nodes):
                            node_details = self.get_node_details(ip_address)
                            node_details["bandwidth"] = self.get_bandwidth(relay)
                            node_details["type"] = "Entry" if i == 0 else "Exit" if i == len(
                                circuit.path) - 1 else "Middle"
                            nodes.append(node_details)
        return nodes

    def get_tor_network_data(self):
        current_upload = int(self.controller.get_info("traffic/written"))
        current_download = int(self.controller.get_info("traffic/read"))
        current_time = time.time()

        time_diff = current_time - self.last_time if self.last_time else 1

        upload_speed = (current_upload - self.last_upload) / 1024 / time_diff if self.last_upload else 0
        download_speed = (current_download - self.last_download) / 1024 / time_diff if self.last_download else 0

        self.last_upload = current_upload
        self.last_download = current_download
        self.last_time = current_time

        return {
            "timestamp": time.strftime('%H:%M:%S'),
            "upload": round(upload_speed, 2),
            "download": round(download_speed, 2)
        }

    def update_stream_handler(self, stream_event):
        if stream_event.status not in [stem.StreamStatus.SUCCEEDED]:
            print(f"Skipping stream event with status: {stream_event.status}")
            return

        stream_target = stream_event.target
        circuit_id = stream_event.circ_id

        if not circuit_id:
            print(f"No circuit ID associated with the stream target {stream_target}")
            return

        try:
            circuit = self.controller.get_circuit(circuit_id)
        except stem.ControllerError as e:
            print(f"Failed to retrieve circuit {circuit_id}: {e}")
            return

        if not circuit.path:
            print(f"No path found for circuit ID {circuit_id}")
            return

        path = []
        for i, (fingerprint, nickname) in enumerate(circuit.path):
            ip, bandwidth = self.get_node_ip_and_bandwidth(fingerprint)
            geolocation = self.get_geolocation(ip)
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

        target_ip = self.extract_ip(stream_target)
        target_geolocation = self.get_geolocation(target_ip)

        circuit_info = {
            "status": stream_event.status,
            "stream_target": stream_target,
            "target_geolocation": target_geolocation,
            "circuit_id": circuit_id,
            "local_public_ip": self.get_local_public_ip(),
            "path": path
        }

        data = json.dumps(circuit_info, indent=4)
        print(f"Status Listener: Generated data: {data}")
        self.data_queue.put(data)

    def circuit_event_handler(self, event):
        if event.status not in [CircStatus.BUILT]:
            print(f"Skipping circuit event with status: {event.status}")
            return

        circuit_info = {
            "status": event.status,
            "circuit_id": event.id,
            "path": [{"fingerprint": fingerprint, "nickname": nickname} for fingerprint, nickname in event.path]
        }

        data = json.dumps(circuit_info, indent=4)
        print(f"Circuit Event Handler: Generated data: {data}")
        self.data_queue.put(data)
        print(f"Circuit {event.id} has been built with path: {event.path}")

    def get_node_ip_and_bandwidth(self, fingerprint):
        try:
            status_entry = self.controller.get_network_status(fingerprint)
            if status_entry:
                ip = status_entry.address
                bandwidth = status_entry.bandwidth
                return ip, bandwidth
            else:
                return "Unknown", "Unknown"
        except stem.OperationFailed:
            return "Unknown", "Unknown"

    def get_geolocation(self, ip):
        try:
            response = self.geoip_reader.city(ip)
            country_info = self.controller.get_info(f"ip-to-country/{ip}")
            country_name = country_info.strip() if country_info else "N/A"
            return {
                "country": country_name,
                "latitude": response.location.latitude,
                "longitude": response.location.longitude
            }
        except geoip2.errors.AddressNotFoundError:
            return {
                "country": "Unknown",
                "latitude": None,
                "longitude": None
            }

    def extract_ip(self, address):
        return address.split(':')[0] if ':' in address else address

    def get_local_public_ip(self):
        # This is a placeholder. In a real implementation, you'd want to fetch your actual public IP.
        return {
            "ip": "8.8.8.8",
            "latitude": 37.5308,
            "longitude": 126.8751,
            "country": "kr",
            "type": "Local"
        }

    def status_listener(self):
        self.controller.add_event_listener(
            self.update_stream_handler,
            stem.control.EventType.STREAM)
        self.controller.add_event_listener(
            self.circuit_event_handler,
            stem.control.EventType.CIRC)

        print("Listening for Tor stream events... Press Ctrl+C to exit.")
        while True:
            eventlet.sleep(1)

    def data_processor(self):
        while True:
            data = self.data_queue.get()
            parsed_json = json.loads(data)
            status = parsed_json["status"]

            if status in [stem.StreamStatus.SUCCEEDED]:
                print(f"Data Processor: Processing data: {data}")
                socketio.emit(f'{stem.StreamStatus.SUCCEEDED}', {'data': data})

            if status in [CircStatus.BUILT]:
                print(f"Data Processor: Processing data: {data}")
                SendData = json.dumps(self.collect_tor_nodes(), indent=4)
                socketio.emit(f'{CircStatus.BUILT}', {'data': SendData})
            self.data_queue.task_done()

    def close(self):
        self.geoip_reader.close()


app = Flask(__name__)
socketio = SocketIO(app, async_mode='eventlet', ping_timeout=60, ping_interval=25, logger=True, engineio_logger=True)

# Global instance of TorNetworkAnalyzer
tor_analyzer = None


@socketio.on('connect')
def handle_connect():
    print("Client connected.")
    emit('status_update', {'data': 'Welcome, you are connected!'})
    SendData = json.dumps(tor_analyzer.collect_tor_nodes(), indent=4)
    emit(f'{CircStatus.BUILT}', {'data': SendData})


@socketio.on('message')
def handle_message(message):
    print(f"Received message from client: {message}")
    emit('status_update', {'data': f"Server received: {message}"})


@socketio.event
def my_ping():
    emit('my_pong')


@socketio.event
def updateNodes():
    SendData = json.dumps(tor_analyzer.collect_tor_nodes(), indent=4)
    emit(f'{CircStatus.BUILT}', {'data': SendData})


@app.route('/')
def index():
    return render_template('tor.html')


@app.route('/data')
def data():
    return jsonify(tor_analyzer.get_tor_network_data())


if __name__ == '__main__':
    TOR_PASSWORD = 'welcome'
    TOR_PORT = 8052
    GEOIP_DB_PATH = './geoip/GeoLite2-City.mmdb'

    tor_analyzer = TorNetworkAnalyzer(TOR_PASSWORD, TOR_PORT, GEOIP_DB_PATH)
    tor_analyzer.initialize_tor_controller()

    status_thread = threading.Thread(target=tor_analyzer.status_listener)
    status_thread.daemon = True
    status_thread.start()

    processor_thread = threading.Thread(target=tor_analyzer.data_processor)
    processor_thread.daemon = True
    processor_thread.start()

    try:
        socketio.run(app, debug=True, host='0.0.0.0', port=505, use_reloader=False)
    finally:
        tor_analyzer.close()