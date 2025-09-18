import time
import network
import ujson
from machine import Pin, I2C
import uasyncio as asyncio

# --- Hardware Configuration ---
PIN_I2C_SDA = 4
PIN_I2C_SCL = 5

ADDR_INPUTS_1_8 = 0x22
ADDR_INPUTS_9_16 = 0x21
ADDR_OUTPUTS_1_8 = 0x24
ADDR_OUTPUTS_9_16 = 0x25

PIN_HT1 = 32
PIN_HT2 = 33
PIN_HT3 = 14

# --- Helper Class for PCF8574 ---
class PCF8574:
    def __init__(self, i2c_bus, address):
        self.i2c = i2c_bus
        self.address = address
        self.value = 0xFF 
        self.is_valid = True
        try:
            self.i2c.scan()
            # print(f"Found I2C device at address 0x{self.address:x}")
        except OSError:
            print(f"I2C device not found at address 0x{self.address:x}")
            self.is_valid = False

    def read_all(self):
        if not self.is_valid: return None
        try:
            self.value = self.i2c.readfrom(self.address, 1)[0]
            return self.value
        except OSError as e:
            # print(f"I2C read error on address 0x{self.address:x}: {e}")
            return None

    def read_pin(self, pin_number):
        if not self.is_valid: return False
        if self.read_all() is not None:
            return not bool(self.value & (1 << pin_number))
        return False

    def write_all(self, value):
        if not self.is_valid: return
        try:
            self.i2c.writeto(self.address, bytes([value]))
            self.value = value
        except OSError as e:
            print(f"I2C write error on address 0x{self.address:x}: {e}")

    def write_pin(self, pin_number, state):
        if not self.is_valid: return
        if not state:
            self.value &= ~(1 << pin_number)
        else:
            self.value |= (1 << pin_number)
        self.write_all(self.value)

# --- Web Server HTML Generation ---
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>KC868-A16 Web Server</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; text-align: center; margin: 0; padding: 0; background-color: #f4f4f4; color: #333; }
        .container { max-width: 600px; margin: 20px auto; padding: 20px; background-color: white; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
        h1 { color: #007BFF; }
        .section { margin-bottom: 20px; }
        .state-text { font-size: 1.2rem; font-weight: bold; }
        .input-state { display: inline-block; width: 100px; padding: 5px; margin: 5px; border-radius: 5px; background-color: #eee; }
        .input-state.on { background-color: #d4edda; color: #155724; }
        .input-state.off { background-color: #f8d7da; color: #721c24; }
        .relay-group { margin-bottom: 15px; }
        .button-container { display: flex; flex-wrap: wrap; justify-content: center; gap: 10px; }
        .button { 
            padding: 12px 24px; border: none; border-radius: 25px; cursor: pointer; text-decoration: none; font-size: 1rem;
            font-weight: bold; transition: all 0.3s ease; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            color: white; background-color: #6c757d;
        }
        .button.on { background-color: #28a745; }
        .button.off { background-color: #dc3545; }
        .button:hover { transform: translateY(-2px); box-shadow: 0 6px 8px rgba(0,0,0,0.15); }
    </style>
</head>
<body>
    <div class="container">
        <h1>KC868-A16 Web Server</h1>
        <div class="section">
            <h2>Input Status</h2>
            <div id="input-status-container"></div>
        </div>
        <div class="section">
            <h2>Relay Control</h2>
            <div id="relay-buttons-container" class="button-container"></div>
            <div class="button-container" style="margin-top: 20px;">
                <button class="button" id="all-toggle-btn">Toggle All</button>
            </div>
        </div>
    </div>

    <script>
        // This is the JavaScript that runs in the browser
        const updateInterval = 1000; // 1 second
        
        const createRelayToggleButton = (id, state) => {
            const button = document.createElement('button');
            button.className = 'button ' + state;
            button.textContent = `Relay ${id} - ${state.toUpperCase()}`;
            button.onclick = () => {
                toggleRelay(id, state === 'on' ? 'off' : 'on');
            };
            return button;
        };

        const toggleRelay = async (id, state) => {
            try {
                const response = await fetch(`/?relay=${id}&state=${state}`);
                if (!response.ok) {
                    console.error('Failed to toggle relay');
                }
            } catch (error) {
                console.error('Network error:', error);
            }
        };
        
        const updateUI = async () => {
            try {
                const response = await fetch('/api/state');
                const data = await response.json();
                
                // Update relay buttons
                const relayContainer = document.getElementById('relay-buttons-container');
                relayContainer.innerHTML = '';
                for (const [id, state] of Object.entries(data.relays)) {
                    relayContainer.appendChild(createRelayToggleButton(id, state));
                }

                // Update "All On/Off" button
                const allToggleBtn = document.getElementById('all-toggle-btn');
                const allRelaysOn = Object.values(data.relays).every(state => state === 'on');
                const allRelaysOff = Object.values(data.relays).every(state => state === 'off');

                if (allRelaysOn) {
                    allToggleBtn.textContent = 'All OFF';
                    allToggleBtn.onclick = () => toggleRelay('all', 'off');
                    allToggleBtn.className = 'button off';
                } else if (allRelaysOff) {
                    allToggleBtn.textContent = 'All ON';
                    allToggleBtn.onclick = () => toggleRelay('all', 'on');
                    allToggleBtn.className = 'button on';
                } else {
                    allToggleBtn.textContent = 'Toggle All';
                    allToggleBtn.onclick = () => {
                        // Default to turning all off if states are mixed
                        toggleRelay('all', 'off');
                    };
                    allToggleBtn.className = 'button';
                }
                
                // Update input status
                const inputContainer = document.getElementById('input-status-container');
                inputContainer.innerHTML = '';
                for (const [name, state] of Object.entries(data.inputs)) {
                    const stateText = state ? 'ON' : 'OFF';
                    const stateClass = state ? 'on' : 'off';
                    const p = document.createElement('p');
                    p.className = 'input-state ' + stateClass;
                    p.textContent = `${name}: ${stateText}`;
                    inputContainer.appendChild(p);
                }

            } catch (error) {
                console.error('Error fetching state:', error);
            }
        };

        // Initial UI update and start the polling loop
        updateUI();
        setInterval(updateUI, updateInterval);
    </script>
</body>
</html>
"""
def get_html_page():
    return HTML_PAGE

# --- Hardware Instances (Global) ---
i2c0 = I2C(0, sda=Pin(PIN_I2C_SDA), scl=Pin(PIN_I2C_SCL))
sensor_ht1 = Pin(PIN_HT1, Pin.IN, Pin.PULL_UP)
sensor_ht2 = Pin(PIN_HT2, Pin.IN, Pin.PULL_UP)
sensor_ht3 = Pin(PIN_HT3, Pin.IN, Pin.PULL_UP)

pcf_inputs_1_8 = PCF8574(i2c0, ADDR_INPUTS_1_8)
pcf_inputs_9_16 = PCF8574(i2c0, ADDR_INPUTS_9_16)
pcf_outputs_1_8 = PCF8574(i2c0, ADDR_OUTPUTS_1_8)
pcf_outputs_9_16 = PCF8574(i2c0, ADDR_OUTPUTS_9_16)

# Map relay numbers to their corresponding PCF and pin number
outputs_map = {
    str(i + 1): (pcf_outputs_1_8, i) for i in range(8)
}
outputs_map.update({
    str(i + 9): (pcf_outputs_9_16, i) for i in range(8)
})

# Map input PCF pins to output names
input_to_output_map = {
    pcf_inputs_1_8.address: {i: str(i + 1) for i in range(8)},
    pcf_inputs_9_16.address: {i: str(i + 9) for i in range(8)},
}

# --- New Async Web Server Class ---
class AsyncWebServer:
    def __init__(self, host='0.0.0.0', port=80):
        self.host = host
        self.port = port
        self.routes = {}

    def route(self, path):
        def decorator(handler):
            self.routes[path] = handler
            return handler
        return decorator

    async def run(self):
        server = await asyncio.start_server(self.handle_client, self.host, self.port)
        print(f"Web server started on {self.host}:{self.port}")
        await server.wait_closed()

    async def handle_client(self, reader, writer):
        try:
            request_line = await asyncio.wait_for(reader.readline(), timeout=3.0)
            if not request_line:
                return

            request_line_str = request_line.decode('utf-8').strip()
            # print("Request:", request_line_str)
            
            while await asyncio.wait_for(reader.readline(), timeout=3.0) != b"\r\n":
                pass

            method, path, _ = request_line_str.split(' ')
            path_base = path.split('?')[0]
            
            handler = self.routes.get(path_base)
            if handler:
                await handler(reader, writer, path)
            else:
                writer.write(b"HTTP/1.1 404 Not Found\r\n")
                writer.write(b"Content-Type: text/plain\r\n\r\n")
                writer.write(b"404 Not Found")

        except asyncio.TimeoutError:
            print("Request timed out.")
        except Exception as e:
            print(f"Error handling request: {e}")
        finally:
            await writer.drain()
            writer.close()
            await writer.wait_closed()

# --- Application Logic ---
app = AsyncWebServer()

def do_connect():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('Connecting to network...')
        wlan.connect('router', '1234')
        for i in range(10):
            if wlan.isconnected():
                break
            time.sleep(1)
        if wlan.isconnected():
            print('Network config:', wlan.ifconfig())
        else:
            print('Could not connect to network.')

@app.route('/')
async def index_handler(reader, writer, path):
    """Main handler for the web page and control requests."""
    # Check for a relay control request via query parameters
    if '?' in path:
        try:
            query = path.split("?")[1]
            params = dict(param.split("=") for param in query.split("&"))
            
            relay_id = params.get("relay")
            state = params.get("state")

            if relay_id == "all" and state in ["on", "off"]:
                state_value = True if state == "on" else False
                for relay_num in outputs_map:
                    pcf, pin_num = outputs_map[relay_num]
                    pcf.write_pin(pin_num, state_value)
                print(f"All relays set to {state.upper()}")
            elif relay_id in outputs_map and state in ["on", "off"]:
                state_value = True if state == "on" else False
                pcf, pin_num = outputs_map[relay_id]
                pcf.write_pin(pin_num, state_value)
                print(f"Relay {relay_id} set to {state.upper()}")

            writer.write(b"HTTP/1.1 200 OK\r\n")
            writer.write(b"Content-Type: text/plain\r\n\r\n")
            writer.write(b"OK")
        except Exception as e:
            print(f"Error parsing request: {e}")
            writer.write(b"HTTP/1.1 500 Internal Server Error\r\n")
            writer.write(b"Content-Type: text/plain\r\n\r\n")
            writer.write(f"Error: {e}".encode('utf-8'))
        finally:
            await writer.drain()
            writer.close()
            await writer.wait_closed()
            return
            
    # Serve the main HTML page
    html_response = get_html_page()
    writer.write(b"HTTP/1.1 200 OK\r\n")
    writer.write(b"Content-Type: text/html\r\n")
    writer.write(b"Connection: close\r\n")
    writer.write(f"Content-Length: {len(html_response)}\r\n".encode('utf-8'))
    writer.write(b"\r\n")
    writer.write(html_response.encode('utf-8'))

@app.route('/api/state')
async def api_state_handler(reader, writer, path):
    """API handler to return the current state of all relays and inputs in JSON format."""
    
    # Get inputs state
    inputs_states = {
        "HT1": not sensor_ht1.value(),
        "HT2": not sensor_ht2.value(),
        "HT3": not sensor_ht3.value()
    }
    # Read from PCF inputs
    if pcf_inputs_1_8.is_valid:
        for i in range(8):
            inputs_states[f"X{i+1:02d}"] = pcf_inputs_1_8.read_pin(i)
    if pcf_inputs_9_16.is_valid:
        for i in range(8):
            inputs_states[f"X{i+9:02d}"] = pcf_inputs_9_16.read_pin(i)

    # Get outputs state
    relays_state = {}
    for relay_id, (pcf, pin_num) in outputs_map.items():
        state = not bool(pcf.value & (1 << pin_num))
        # This is the line that has been updated to reverse the display
        relays_state[relay_id] = "off" if state else "on"

    response_data = {
        "relays": relays_state,
        "inputs": inputs_states
    }
    
    json_response = ujson.dumps(response_data)
    writer.write(b"HTTP/1.1 200 OK\r\n")
    writer.write(b"Content-Type: application/json\r\n")
    writer.write(b"Connection: close\r\n")
    writer.write(f"Content-Length: {len(json_response)}\r\n".encode('utf-8'))
    writer.write(b"\r\n")
    writer.write(json_response.encode('utf-8'))
    
    await writer.drain()
    writer.close()
    await writer.wait_closed()

async def scan_keys():
    """Asynchronously scans for button presses and toggles relays."""
    print("Starting key scanning task.")
    pcf_inputs = {
        pcf_inputs_1_8.address: pcf_inputs_1_8,
        pcf_inputs_9_16.address: pcf_inputs_9_16
    }
    
    prev_state = {addr: pcf.read_all() for addr, pcf in pcf_inputs.items() if pcf.is_valid}
    
    while True:
        try:
            for addr, pcf in pcf_inputs.items():
                if not pcf.is_valid: continue
                current_state = pcf.read_all()
                if current_state is None:
                    continue

                diff = prev_state[addr] ^ current_state
                for i in range(8):
                    if diff & (1 << i):
                        if not (current_state & (1 << i)):
                            relay_id = input_to_output_map[addr][i]
                            pcf_out, pin_num = outputs_map[relay_id]
                            
                            current_relay_state = not bool(pcf_out.value & (1 << pin_num))
                            new_relay_state = not current_relay_state
                            pcf_out.write_pin(pin_num, new_relay_state)
                            print(f"Input {i} on board 0x{addr:x} triggered relay {relay_id} to {'ON' if new_relay_state else 'OFF'}")
                prev_state[addr] = current_state
        except Exception as e:
            print(f"Error in scan_keys: {e}")
        await asyncio.sleep_ms(100)

# --- Entry Point ---
if __name__ == "__main__":
    try:
        do_connect()
        # Initialize relays to OFF (HIGH on PCF8574)
        if pcf_outputs_1_8.is_valid: pcf_outputs_1_8.write_all(0xFF)
        if pcf_outputs_9_16.is_valid: pcf_outputs_9_16.write_all(0xFF)
        
        tasks = [
            asyncio.create_task(app.run()),
            asyncio.create_task(scan_keys())
        ]
        
        asyncio.run(asyncio.gather(*tasks))

    except KeyboardInterrupt:
        print("Web server stopped.")
    finally:
        asyncio.new_event_loop()
