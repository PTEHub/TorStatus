from stem import Signal
from stem.control import Controller
import threading
import time

class TorSingleton:
    _instance = None
    _lock = threading.Lock()  # Lock to ensure thread safety

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(TorSingleton, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        self.controller = None
        self.controller_lock = threading.Lock()  # Lock for controlling access to the controller

    def connect(self, password="my_tor_password", port=9051):
        """Connect to the Tor network using a controller."""
        with self.controller_lock:
            if self.controller is None:
                try:
                    # Connect to the Tor controller
                    self.controller = Controller.from_port(port=port)
                    self.controller.authenticate(password=password)
                    print("Connected to Tor")
                except Exception as e:
                    print(f"Failed to connect to Tor: {e}")

    def renew_identity(self):
        """Renew Tor identity to get a new IP."""
        with self.controller_lock:
            try:
                if self.controller:
                    self.controller.signal(Signal.NEWNYM)
                    time.sleep(self.controller.get_newnym_wait())
                    print("New identity acquired.")
                else:
                    print("Controller not connected.")
            except Exception as e:
                print(f"Failed to renew identity: {e}")

    def get_controller(self):
        """Externally access the controller."""
        with self.controller_lock:
            return self.controller

# Example of multithreading
def worker():
    tor = TorSingleton()
    tor.connect(password="your_tor_control_password")
    tor.renew_identity()

if __name__ == "__main__":
    threads = []
    for _ in range(5):  # Create 5 threads to call Tor simultaneously
        t = threading.Thread(target=worker)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()  # Wait for all threads to finish