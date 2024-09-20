import json
import geoip2.database
from stem import Signal
from stem.control import Controller


def get_node_details(ip_address, geoip_reader, controller):
    try:
        response = geoip_reader.city(ip_address)
        country_info = controller.get_info(f"ip-to-country/{ip_address}")
        country_name = country_info.strip() if country_info else "N/A"
        return {
            "ip": ip_address,
            "country": country_name,
            "speed": "N/A",
            "latitude": response.location.latitude,
            "longitude": response.location.longitude
        }
    except (geoip2.errors.AddressNotFoundError, Exception):
        return {
            "ip": ip_address,
            "country": "N/A",
            "speed": "N/A",
            "latitude": "N/A",
            "longitude": "N/A"
        }


def get_bandwidth(fingerprint, controller):
    try:
        status_entry = controller.get_network_status(fingerprint)
        return status_entry.bandwidth if status_entry else "N/A"
    except Exception:
        return "N/A"


def collect_tor_nodes():
    nodes = []
    with geoip2.database.Reader('./geoip/GeoLite2-City.mmdb') as geoip_reader:
        with Controller.from_port(port=8052) as controller:
            controller.authenticate(password='welcome')
            controller.signal(Signal.NEWNYM)
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


if __name__ == "__main__":
    tor_nodes = collect_tor_nodes()
    print(json.dumps(tor_nodes, indent=4))