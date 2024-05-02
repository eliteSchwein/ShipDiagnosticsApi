import sys
import tkinter as tk
import os.path
import myNotebook as nb
import logging
import json
import socket

from tkinter import ttk
from threading import Thread, Timer, Event
from typing import TYPE_CHECKING, Any, List, Dict, Mapping, MutableMapping, Optional, Tuple
from config import appname, user_agent, config
from http.server import BaseHTTPRequestHandler, HTTPServer

if TYPE_CHECKING:
    def _(x: str) -> str:
        return x

this = sys.modules[__name__]

this.version: str = "0.0.1"
this.cmdr_name: str = None

#config
this.port: str = None
this.ip: str = None
this.no_proxy: bool = False

# UI elements
# Preferences
this.port_entry: nb.Entry = None
this.ip_entry: nb.Entry = None
this.no_proxy_entry: nb.Entry = None
this.port_tk: tk.StringVar = tk.StringVar(master=None, value="6009")
this.ip_tk: tk.StringVar = tk.StringVar(master=None, value="127.0.0.1")
this.no_proxy_tk: tk.BooleanVar = tk.BooleanVar(master=None, value=False)

# setup logging
plugin_name: str = os.path.basename(os.path.dirname(__file__))

# webserver
api_server: HTTPServer = None

this.thread: Optional[Thread] = None

# setup logging
plugin_name: str = os.path.basename(os.path.dirname(__file__))

logger = logging.getLogger(f'{appname}.{plugin_name}')

# Dashboard Flags constants
FlagsDocked = 1 << 0  # on a landing pad
FlagsLanded = 1 << 1  # on planet surface
FlagsLandingGearDown = 1 << 2
FlagsShieldsUp = 1 << 3
FlagsSupercruise = 1 << 4
FlagsFlightAssistOff = 1 << 5
FlagsHardpointsDeployed = 1 << 6
FlagsInWing = 1 << 7
FlagsLightsOn = 1 << 8
FlagsCargoScoopDeployed = 1 << 9
FlagsSilentRunning = 1 << 10
FlagsScoopingFuel = 1 << 11
FlagsSrvHandbrake = 1 << 12
FlagsSrvTurret = 1 << 13  # using turret view
FlagsSrvUnderShip = 1 << 14  # turret retracted
FlagsSrvDriveAssist = 1 << 15
FlagsFsdMassLocked = 1 << 16
FlagsFsdCharging = 1 << 17
FlagsFsdCooldown = 1 << 18
FlagsLowFuel = 1 << 19  # <25%
FlagsOverHeating = 1 << 20  # > 100%
FlagsHasLatLong = 1 << 21
FlagsIsInDanger = 1 << 22
FlagsBeingInterdicted = 1 << 23
FlagsInMainShip = 1 << 24
FlagsInFighter = 1 << 25
FlagsInSRV = 1 << 26
FlagsAnalysisMode = 1 << 27  # Hud in Analysis mode
FlagsNightVision = 1 << 28
FlagsAverageAltitude = 1 << 29  # Altitude from Average radius
FlagsFsdJump = 1 << 30
FlagsSrvHighBeam = 1 << 31

this.data: str = None


def plugin_prefs(parent: tk.Tk, cmdr: str, is_beta: bool) -> tk.Frame:
    this.cmdr_name = cmdr

    this.port = config.get_str(f'sda_port')
    this.ip = config.get_str(f'sda_ip')
    this.no_proxy = config.get_bool(f'sda_no_proxy')

    this.no_proxy_tk.set(config.get_bool(f'sda_no_proxy'))
    this.ip_tk.set(config.get_str(f'sda_ip'))
    this.port_tk.set(config.get_str(f'sda_port'))

    frame = nb.Frame(parent)
    # Make the second column fill available space
    frame.columnconfigure(1, weight=1)

    nb.Label(frame, text="API Server Settings").grid(padx=10, sticky=tk.W)
    ttk.Separator(frame, orient=tk.HORIZONTAL).grid(columnspan=2, padx=10, pady=2, sticky=tk.EW, row=2)
    nb.Label(frame, text="Server Port:").grid(column=0, padx=10, sticky=tk.W, row=3)
    this.port_entry = nb.Entry(frame, textvariable=this.port_tk).grid(column=1, padx=10, pady=2, sticky=tk.EW, row=3)
    nb.Label(frame, text="No Proxy:").grid(column=0, padx=10, sticky=tk.W, row=4)
    this.no_proxy_entry = nb.Checkbutton(frame, variable=this.no_proxy_tk).grid(column=1, padx=10, pady=2, sticky=tk.EW,
                                                                                row=4)
    ttk.Separator(frame, orient=tk.HORIZONTAL).grid(columnspan=2, padx=10, pady=2, sticky=tk.EW, row=5)
    nb.Label(frame, text="Full Address to the API:").grid(column=0, padx=10, sticky=tk.W, row=6)
    this.ip_entry = nb.Entry(frame, textvariable=this.ip_tk, state="readonly").grid(column=1, padx=10, pady=2,
                                                                                    sticky=tk.EW, row=6)

    return frame


def prefs_changed(cmdr: str, is_beta: bool) -> None:
    if is_beta:
        return

    config.set(f'sda_port', this.port_tk.get().strip())
    config.set(f'sda_ip', this.ip_tk.get().strip())
    config.set(f'sda_no_proxy', this.no_proxy_tk.get())
    this.ip = this.ip_tk.get().strip()
    this.port = this.port_tk.get().strip()
    this.no_proxy = this.no_proxy_tk.get()
    start_api()


def plugin_stop() -> None:
    this.api_server.server_close()
    this.api_server = None
    this.thread.join()
    this.thread = None


def plugin_start3(plugin_dir: str) -> str:
    start_api()

    return "ShipDiagnosticsApi"


def load_config() -> None:
    this.port = config.get_str(f'sda_port')
    this.no_proxy = config.get_bool(f'sda_no_proxy')

    if this.port is None:
        config.set(f'sda_port', this.port_tk.get().strip())
        this.port = this.port_tk.get().strip()

    if this.no_proxy is None:
        config.set(f'sda_no_proxy', this.no_proxy_tk.get())
        this.no_proxy = this.no_proxy_tk.get()

    ip = '127.0.0.1'

    if this.no_proxy:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)

    this.ip = f'http://{ip}:{this.port}'
    config.set(f'sda_ip', this.ip)


def dashboard_entry(cmdr, is_beta, entry):
    data = {}
    data['gear_down'] = (entry['Flags'] & FlagsLandingGearDown) > 0
    data['scoop_deployed'] = (entry['Flags'] & FlagsCargoScoopDeployed) > 0
    data['hardpoint_deployed'] = (entry['Flags'] & FlagsHardpointsDeployed) > 0
    data['in_ship'] = (entry['Flags'] & FlagsInMainShip) > 0
    this.data = json.dumps(data)


def start_api() -> None:
    load_config()

    if this.api_server is not None:
        this.api_server.server_close()
        this.api_server = None

    if this.thread is not None:
        this.thread.join()
        this.thread = None

    this.thread = Thread(target=worker, name='SDA worker')
    this.thread.daemon = True
    this.thread.start()


class ApiServer(BaseHTTPRequestHandler):
    def log_request(self, code='-', size='-'):
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(bytes(this.data, "utf-8"))


def worker() -> None:
    ip = '0.0.0.0'

    if not this.no_proxy:
        ip = '127.0.0.1'

    logger.info(f'launch api server: http://{ip}:{this.port}')
    this.api_server = HTTPServer((ip, int(this.port)), ApiServer)
    try:
        this.api_server.serve_forever()
    except:
        pass
