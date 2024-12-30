import sys
import math
import io
import os
import threading
import tkinter as tk
from tkinter import filedialog, colorchooser, simpledialog, messagebox, font as tkfont
from PIL import Image, ImageTk, ImageFont, ImageDraw
import cairosvg
from pynput import keyboard, mouse
import logging
from lxml import etree
import datetime
import ctypes
import importlib
from ctypes import wintypes
from pynput.keyboard import Key
from logging import Handler
import tkinter as tk
from core.OrthyPlugin_Interface import OrthyPlugin
from core.plugin_loader import PluginLoader
from Test_py_files import Button_Factory

# Configure the logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
# Get the path to the resource folder(Images)
def resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)
# Base dir of the orthy.py file
def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))
# TBA
class ImageState:
    def __init__(self, image_original, name, svg_content=None):
        self.image_original = image_original
        self.image_display = None
        self.name = name
        self.visible = True
        self.angle = 0
        self.scale = 1.0
        self.scale_log = 0
        self.offset_x = 512
        self.offset_y = 512
        self.rotation_point = None
        self.is_flipped_horizontally = False
        self.is_flipped_vertically = False
        self.image_transparency_level = 0.2
        self.svg_content = svg_content
# Class for emitting log messages to a tkinter text widget
class TextHandler(Handler):
    def __init__(self, text_widget):
        Handler.__init__(self)
        self.text_widget = text_widget
        self.text_font = tkfont.Font(family="Helvetica", size=8)
        self.text_widget.configure(font=self.text_font)

    def emit(self, record):
        msg = self.format(record)
        self.text_widget.insert(tk.END, msg + '\n')
        self.text_widget.see(tk.END)

''' The Orthy class should act as the central hub, 
    handling shared states,
    event broadcasting, and 
    providing interfaces for plugins to interact with each other.'''
class Orthy:
    def __init__(self, root):
        # Initialize the root window GUI
        self.root = root
        self.root.title("Controls")
        self.image_window_visible = False
        self.small_font = tk.font.Font(size=8) # Font for the log window(if i have one) 



        # Initialize the plugin loader
        self.plugin_loader = PluginLoader()
        self.plugin_loader.load_plugins(self)

        # Initialize Event System
        self.event_handlers = {}
        self.setup_event_system()

    def setup_event_system(self):
        """
        Sets up a simple publish-subscribe event system.
        Plugins can subscribe to and emit events to
        communicate with each other."""
        self.event_handlers = {}
    
    def register_event_handler(self, event_name, handler):
        if event_name not in self.event_handlers:
            # Initialize the dictionary with an empty list
            self.event_handlers[event_name] = [] # <-- This is an empty list
            # Append the handler to the list
            self.event_handlers[event_name].append(handler)
    
    def emit_event(self, event_name, data = None):
        handlers = self.event_handlers.get(event_name, [])
        for handler in handlers:
            handler(data)   
    
    def createButton(self, parent, btnConfig):
        btnConfig = Button_Factory.create_btnConfig(
            text=btnConfig['text'],
            command=lambda: self.emit_event(btnConfig['eventName'], btnConfig['data']),
            row=btnConfig['grid']['row'],
            column=btnConfig['grid']['column'],
            columnspan=btnConfig['grid']['columnspan'],
            pady=btnConfig['grid']['pady'],
            sticky=btnConfig['grid']['sticky'],
            width=btnConfig['width'],
            bg=btnConfig['bg'],
            fg=btnConfig['fg']
        )



        '''# Initialize the image control plugin
        #self.set_root_window_geometry()
        #self.base_dir = get_base_dir()
        #self.images_dir = os.path.join(self.base_dir, 'Images')

        self.predefined_buttons = {}
        self.images = {}
        self.active_image_name = None
        self.previous_active_image_name = None

        self.start_x = 0
        self.start_y = 0
        self.i6s_dragging = False
        self.is_rotation_point_mode = False

        self.additional_windows = []
        self.alt_pressed = False
        self.shift_pressed = False
        self.full_control_mode = False
        self.full_control_hotkey_listener = None
        self.ghost_click_positions = {}

        self.setup_buttons_window()
        self.setup_image_window()
        self.update_transparency_button()

        self.image_window.withdraw()
        self.btn_hide_show_image.config(text="Show")

        self.additional_images_visibility = {
            "Ruler": False,
            "Normal": False,
            "Tapered": False,
            "Ovoide": False,
            "Narrow Tapered": False,
            "Narrow Ovoide": False,
            "Angulation": False
        }

        self.setup_global_hotkeys()'''