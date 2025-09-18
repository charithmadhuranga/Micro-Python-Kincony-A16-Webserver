## KC868-A16 MicroPython Web Server

This project provides a simple, memory-efficient web server written in MicroPython for controlling the KC868-A16 smart relay board. It allows you to toggle 16 relays via a web interface and monitors 16 digital inputs, which can also be used to control the relays.

## Features

1. Web-based Control: A lightweight, single-page web application to control all 16 relays.

2. Intuitive UI: Each relay is controlled by a single toggle button that changes color and label to reflect its current state. A single "Toggle All" button is also available.

3. Real-time Status: The web interface automatically updates to show the live status of all relays and digital inputs.

4. Hardware Control: The ESP32 can control the relays and read the inputs using two PCF8574 I2C port expanders.

5. Asynchronous: The web server is built with uasyncio, enabling it to handle web requests and continuously scan physical input pins for button presses simultaneously without blocking.

6. Physical Button Integration: The code includes logic to detect presses on the physical input pins (X01-X16) and toggle the corresponding relays.

7. Memory Efficient: The HTML for the web page is stored as a constant string to minimize memory usage on the MicroPython board.

## Hardware Requirements

ESP32-S3 board running MicroPython

KC868-A16 board

Standard Micro-USB cable for power and programming

## Getting Started

Flash MicroPython: Ensure your ESP32 board is running the latest MicroPython firmware. You can use tools like esptool.py to flash the firmware.

Connect Hardware: Connect the ESP32 board to the KC868-A16 using the I2C interface (SDA and SCL pins).

Upload the Code: Upload main.py to your ESP32 board.

Configure Wi-Fi: Edit the do_connect() function in main.py to enter your Wi-Fi credentials (router and 1234).

Run the Server: After uploading, the board will automatically connect to your Wi-Fi network and start the web server.

## Web Interface Usage

Open a web browser on a device connected to the same network.

Navigate to the IP address of your ESP32 board (you can find this in the serial monitor output).

The page will display the status of all inputs and provide a set of buttons to control the relays.

Click a relay button to toggle its on/off state. The button's appearance will update to show the new state.

Click the "Toggle All" button to turn all relays ON if they are all OFF, or turn them all OFF if they are all ON.

## API Endpoints

The web server exposes a simple API for state management:

GET /: Serves the main web page.

GET /?relay=<id>&state=<on|off>: Toggles a specific relay (<id> is a number from 1 to 16) or all relays (<id> is "all") to the specified state.

GET /api/state: Returns the current state of all relays and inputs in a JSON format. This is used by the front end to update the UI.

## Code Structure

PCF8574 Class: A class to simplify communication with the I2C port expanders for reading inputs and writing to outputs.

AsyncWebServer Class: A minimal asynchronous web server implementation using uasyncio to handle HTTP requests.

index_handler: Manages control requests and serves the main HTML page.

api_state_handler: Provides the JSON data for the web interface.

scan_keys Task: An asynchronous task that runs in the background to monitor the physical input pins for state changes and trigger the corresponding relay.