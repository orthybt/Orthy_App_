# plugins/ghost_click_plugin.py

from core.OrthyPlugin_Interface import OrthyPlugin
import ctypes
from ctypes import wintypes
import logging
from tkinter import messagebox

class GhostClickPlugin(OrthyPlugin):
    def __init__(self):
        self.app = None
        self.enabled = True
        self.click_positions = {}
        self.buttons = {}  # Store button references
        self._setup_mouse_structures()

    def _setup_mouse_structures(self):
        self.INPUT_MOUSE = 0
        
        class MOUSEINPUT(ctypes.Structure):
            _fields_ = [
                ("dx", ctypes.c_long),
                ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))
            ]

        class INPUT(ctypes.Structure):
            _fields_ = [
                ("type", ctypes.c_ulong),
                ("mi", MOUSEINPUT)
            ]
            
        self.MOUSEINPUT = MOUSEINPUT
        self.INPUT = INPUT

    def initialize(self, app_instance):
        self.app = app_instance
        logging.debug("GhostClick plugin initialized")

    def get_name(self):
        return "GhostClick"

    def register_button(self, name, button):
        """Store reference to created button"""
        self.buttons[name] = button
        logging.debug(f"Registered button: {name}")

    def get_buttons(self):
        return [{
            'text': 'Ghost: ON' if self.enabled else 'Ghost: OFF',
            'command': self.toggle_ghost_clicks,
            'grid': {'row': 8, 'column': 0, 'columnspan': 2, 'pady': 2, 'sticky': 'ew'},
            'width': 12,
            'variable_name': 'btn_ghost_click',
            'relief': 'sunken' if self.enabled else 'raised',
            'bg': '#a0ffa0' if self.enabled else '#ffa0a0',
            'register_callback': self.register_button  # Pass callback to store button
        }]

    def perform_ghost_click(self, position_name):
        """Performs ghost click and returns cursor to original position."""
        position = self.click_positions.get(position_name)
        if position is None:
            logging.error(f"No position defined for '{position_name}'")
            return

        point = wintypes.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(point))
        original_x, original_y = point.x, point.y

        logging.info(f"Ghost click at '{position_name}': {position}")
        self._ghost_click_at_position(position)

        ctypes.windll.user32.SetCursorPos(original_x, original_y)

    def _ghost_click_at_position(self, position):
        """Simulates mouse click at specified position."""
        x, y = position
        screen_width = ctypes.windll.user32.GetSystemMetrics(0)
        screen_height = ctypes.windll.user32.GetSystemMetrics(1)

        absolute_x = int(x * 65536 / screen_width)
        absolute_y = int(y * 65536 / screen_height)

        # Create move, down, up inputs
        inputs = (
            self._create_input(absolute_x, absolute_y, 0x0001 | 0x8000),  # MOVE
            self._create_input(0, 0, 0x0002),  # DOWN
            self._create_input(0, 0, 0x0004)   # UP
        )
        
        nInputs = len(inputs)
        pInputs = (self.INPUT * nInputs)(*inputs)
        cbSize = ctypes.sizeof(self.INPUT)

        ctypes.windll.user32.SendInput(nInputs, pInputs, cbSize)

    def _create_input(self, dx, dy, flags):
        """Creates INPUT structure for mouse event."""
        input_struct = self.INPUT()
        input_struct.type = self.INPUT_MOUSE
        input_struct.mi = self.MOUSEINPUT(
            dx=dx,
            dy=dy,
            mouseData=0,
            dwFlags=flags,
            time=0,
            dwExtraInfo=None
        )
        return input_struct

    def toggle_ghost_clicks(self):
        """Toggles ghost click functionality."""
        self.enabled = not self.enabled
        state = "enabled" if self.enabled else "disabled"
        logging.info(f"Ghost clicks {state}")
        
        if 'btn_ghost_click' in self.buttons:
            self.buttons['btn_ghost_click'].config(
                text=f'Ghost: {"ON" if self.enabled else "OFF"}',
                relief='sunken' if self.enabled else 'raised',
                bg='#a0ffa0' if self.enabled else '#ffa0a0'
            )

    def register_position(self, name, position):
        """Registers a named position for ghost clicks."""
        self.click_positions[name] = position
        logging.debug(f"Registered position '{name}': {position}")

    def cleanup(self):
        """Cleanup plugin resources."""
        self.click_positions.clear()
        logging.debug("GhostClick plugin cleaned up")