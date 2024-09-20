# TorStatus

TorStatus is a visualization application for monitoring the status of the Tor network. It is implemented based on the stem library and Flask framework, primarily used for whonix-gateway monitoring.

## Screenshot
<img src=".\Document\b67c089c77390278b00febf2a50090c.jpg" alt="TorStatus Screenshot"  width="854" height="480">

## Features

1. **Node Display**: Shows all currently built Tor nodes.
2. **Traffic Monitoring**: Displays the incoming and outgoing traffic of the Tor network within the last 3 minutes.
3. **Communication Path**: Visualizes the current active communication link paths.

## Tech Stack

- Python
- stem (Tor controller library)
- Flask (Web application framework)
- Flask-SocketIO (for WebSocket communication)
- GeoIP2 (for IP geolocation queries)
- eventlet (concurrent networking library)

## Installation

1. Ensure that Python is installed on your system.
2. Clone or download this repository to your local machine.
3. Use pip to install the required dependencies:
   ```
   pip install flask flask-socketio stem geoip2 eventlet
   ```

## Usage

1. Before running the application, you need to modify the following configuration in the code:

   ```python
   TOR_PASSWORD = 'welcome'
   TOR_PORT = 8052
   local_public_ip = {
       "ip": "8.8.8.8",
       "latitude": 37.5308,
       "longitude": 126.8751,
       "country": "kr",
       "type": "Local"
   }
   ```

   - `TOR_PASSWORD`: This is the password for Tor. You need to change it to your Tor password.
   - `TOR_PORT`: This is the control port for Tor, default is 9051. If your Tor uses a different control port, please modify this value accordingly.
   - `local_public_ip`: This is your local internet address information. You need to modify these values according to your actual situation.
     - You can obtain your IP address, latitude, longitude, and country information at https://ipinfo.io/.

2. Navigate to the project directory in the command line.

3. Run the following command to start the application:
   ```
   python app.py
   ```

4. Open a web browser and visit `http://localhost:505` to view the TorStatus interface.

Note: The application runs on port 505 by default. If you need to change the port, please modify the relevant configuration in the `app.py` file.

## Author

PTEHub

## Contribution

If you have any suggestions for this project or have found a bug, please feel free to submit via GitHub issues or pull requests.

## License

### TorStatus Custom Non-Commercial Open Source License

Copyright (c) 2024 PTEHub

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, subject to the following conditions:

1. The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

2. The Software may only be used for non-commercial purposes. "Non-commercial purposes" means purposes that are not primarily intended for or directed towards commercial advantage or monetary compensation.

3. The Software may not be used for any commercial purpose without the explicit written permission of the copyright owner. Commercial purposes include but are not limited to:
   a) Integrating or using the Software in commercial products or services
   b) Using the Software to provide commercial services
   c) Using the Software to create products for sale
   d) Using the Software for any activity that may generate income

4. Modifications and improvements to the Software are allowed, but any derivative work must be distributed under the same license terms.

5. THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

6. This license does not grant permission to use the trade names, trademarks, service marks, or product names of the Licensor, except as required for reasonable and customary use in describing the origin of the Software and reproducing the content of the copyright notice.

7. If you modify the Software, you must clearly indicate the modifications made in the modified files.

8. If you distribute the Software, you must retain all copyright, patent, trademark, and attribution notices that are present in the Software.

9. This license may be revised from time to time. By using the Software, you agree to be bound by any such revisions.

By using this Software, you agree to abide by these license terms. If you do not agree to these terms, please do not use, modify, or distribute the Software.

## Contact

Twitter (X): [@PTEHubOnline](https://twitter.com/PTEHubOnline)
