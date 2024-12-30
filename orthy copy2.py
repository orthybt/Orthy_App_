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

from core.OrthyPlugin_Interface import OrthyPlugin
from core.plugin_loader import PluginLoader

# Configure the logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def resource_path(relative_path):
    """Return the absolute path to the resource, whether running in a frozen app or not."""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_base_dir():
    """Return the directory of this script or the frozen executable."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

class ImageState:
    """Holds an image, its transformations, and its visibility state."""
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

class TextHandler(Handler):
    """A logging handler that writes log messages to a Tkinter Text widget."""
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        self.text_font = tkfont.Font(family="Helvetica", size=8)
        self.text_widget.configure(font=self.text_font)

    def emit(self, record):
        msg = self.format(record)
        self.text_widget.insert(tk.END, msg + '\n')
        self.text_widget.see(tk.END)

class Orthy:
    """Main application class for Orthy. Loads plugins, manages images, and handles the main UI."""
    def __init__(self, root):
        self.root = root
        self.root.title("Controls")

        # Plugin system
        self.plugin_loader = PluginLoader()
        self.plugin_loader.load_plugins(self)

        # Basic paths & geometry
        self.base_dir = get_base_dir()
        self.images_dir = os.path.join(self.base_dir, 'Images', 'ArchSaves')
        self.set_root_window_geometry()

        # Internal state
        self.images = {}
        self.active_image_name = None
        self.previous_active_image_name = None
        self.is_dragging = False
        self.is_rotation_point_mode = False

        self.image_window_visible = False
        self.alt_pressed = False
        self.shift_pressed = False
        self.full_control_mode = False
        self.full_control_hotkey_listener = None
        self.ghost_click_positions = {}
        self.additional_windows = []

        # Additional flags
        self.small_font = tk.font.Font(size=8)

        # Mapping for toggled images
        self.additional_images_visibility = {
            "Ruler": False,
            "Normal": False,
            "Tapered": False,
            "Ovoide": False,
            "Narrow Tapered": False,
            "Narrow Ovoide": False,
            "Angulation": False
        }

        # Build UI
        self.setup_buttons_window()
        self.setup_image_window()

        # Attempt to set default transparency button state
        self.update_transparency_button()

        # Hide image window initially
        self.image_window.withdraw()
        if hasattr(self, 'btn_hide_show_image'):
            self.btn_hide_show_image.config(text="Show")
        else:
            logging.warning("btn_hide_show_image not initialized properly.")

        # Hotkeys
        self.setup_global_hotkeys()

    def set_root_window_geometry(self):
        """Position the main control window on the right side of the screen."""
        window_width = 135
        button_height = 25
        padding = 2
        num_rows = 20
        extra_padding = 20
        window_height = (button_height + padding) * num_rows + extra_padding

        margin_right = 60
        margin_top = 150

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x_position = screen_width - window_width - margin_right
        y_position = margin_top
        self.root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")

    ########################################################################
    # UI Setup
    ########################################################################

    def setup_buttons_window(self):
        """Create the scrollable button area, load plugin buttons, etc."""
        button_canvas = tk.Canvas(self.root)
        scrollbar = tk.Scrollbar(self.root, orient="vertical", command=button_canvas.yview)
        btn_frame = tk.Frame(button_canvas)

        button_canvas.configure(yscrollcommand=scrollbar.set)
        button_canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        button_canvas.create_window((0, 0), window=btn_frame, anchor="nw")

        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # Transparency button
        transparency_config = {
            'text': "Min Transp",
            'command': self.toggle_transparency,
            'grid': {'row': 0, 'column': 0, 'columnspan': 2, 'pady': 2, 'sticky': 'ew'},
            'width': 15,
            'variableName': 'btn_toggle_transparency'
        }
        self.create_button(btn_frame, transparency_config)
        last_row = 1

        self.create_image_controls(btn_frame)        # Hide/Show
        self.create_flip_controls(btn_frame)         # Flip H/V
        self.create_rotation_point_control(btn_frame)
        self.create_zoom_controls(btn_frame)
        self.create_predefined_image_buttons(btn_frame)

        # Process plugin buttons
        plugin_button_count = 0
        for plugin in self.plugin_loader.plugins.values():
            plugin_name = plugin.get_name()
            buttons = plugin.get_buttons()
            logging.info(f"Processing plugin: {plugin_name}")
            logging.info(f"Found {len(buttons)} buttons for plugin {plugin_name}")

            for button_config in buttons:
                if 'grid' not in button_config:
                    button_config['grid'] = {
                        'row': last_row,
                        'column': 0,
                        'columnspan': 2,
                        'pady': 2,
                        'sticky': 'ew'
                    }
                self.create_button(btn_frame, button_config)
                last_row += 1
                plugin_button_count += 1
                logging.info(f"Created button: {button_config.get('text')} for {plugin_name}")

        btn_frame.update_idletasks()
        button_canvas.configure(scrollregion=button_canvas.bbox("all"))
        logging.info(f"Completed loading {plugin_button_count} plugin buttons")

    def create_button(self, parent, btn_cfg):
        """Create and grid a Tk button based on the dictionary config."""
        button = tk.Button(
            parent,
            text=btn_cfg.get('text', ''),
            command=btn_cfg.get('command'),
            width=btn_cfg.get('width', 10)
        )

        if btn_cfg.get('bg'):
            button.config(bg=btn_cfg['bg'])
        if btn_cfg.get('fg'):
            button.config(fg=btn_cfg['fg'])

        grid_cfg = btn_cfg.get('grid', {})
        if 'columnspan' in grid_cfg:
            grid_cfg['columnspan'] = max(1, int(grid_cfg['columnspan']))
        else:
            grid_cfg['columnspan'] = 1

        button.grid(**grid_cfg)

        # If variableName is provided, store a reference on self
        var_name = btn_cfg.get('variableName')
        if var_name:
            setattr(self, var_name, button)

        return button

    def create_image_controls(self, parent):
        """Build the Hide/Show button for the image window."""
        buttons = [{
            'text': 'Hide',
            'command': self.toggle_image_window,
            'grid': {'row': 1, 'column': 0, 'columnspan': 2, 'pady': 2, 'sticky': 'ew'},
            'width': 10,
            'variableName': 'btn_hide_show_image'
        }]
        for btn_cfg in buttons:
            self.create_button(parent, btn_cfg)

    def create_flip_controls(self, parent):
        buttons = [
            {
                'text': 'Flip H',
                'command': self.flip_image_horizontal,
                'grid': {'row': 2, 'column': 0, 'pady': 2, 'sticky': 'ew'},
                'width': 6
            },
            {
                'text': 'Flip V',
                'command': self.flip_image_vertical,
                'grid': {'row': 2, 'column': 1, 'pady': 2, 'sticky': 'ew'},
                'width': 6
            }
        ]
        for btn_cfg in buttons:
            self.create_button(parent, btn_cfg)

    def create_rotation_point_control(self, parent):
        buttons = [
            {
                'text': 'Rot Pt',
                'command': self.toggle_rotation_point_mode,
                'grid': {'row': 3, 'column': 0, 'columnspan': 2, 'pady': 2, 'sticky': 'ew'},
                'width': 10,
                'variableName': 'btn_rotation_point'
            }
        ]
        for btn_cfg in buttons:
            self.create_button(parent, btn_cfg)

    def create_zoom_controls(self, parent):
        buttons = [
            {
                'text': '+',
                'command': self.zoom_in,
                'grid': {'row': 4, 'column': 0, 'pady': 2, 'sticky': 'ew'},
                'width': 6
            },
            {
                'text': '-',
                'command': self.zoom_out,
                'grid': {'row': 4, 'column': 1, 'pady': 2, 'sticky': 'ew'},
                'width': 6
            },
            {
                'text': '+ Fine',
                'command': self.fine_zoom_in,
                'grid': {'row': 5, 'column': 0, 'pady': 2, 'sticky': 'ew'},
                'width': 6
            },
            {
                'text': '- Fine',
                'command': self.fine_zoom_out,
                'grid': {'row': 5, 'column': 1, 'pady': 2, 'sticky': 'ew'},
                'width': 6
            },
            {
                'text': 'Rot +',
                'command': self.fine_rotate_clockwise,
                'grid': {'row': 6, 'column': 0, 'pady': 2, 'sticky': 'ew'},
                'width': 6
            },
            {
                'text': 'Rot -',
                'command': self.fine_rotate_counterclockwise,
                'grid': {'row': 6, 'column': 1, 'pady': 2, 'sticky': 'ew'},
                'width': 6
            }
        ]
        for btn_cfg in buttons:
            self.create_button(parent, btn_cfg)

    def create_predefined_image_buttons(self, parent):
        image_buttons = [
            ("Angul", "angulation.svg", self.toggle_angulation),
            ("Ruler", "liniar_new_n2.svg", self.toggle_ruler),
            ("Normal", "Normal(medium).svg", self.toggle_normal),
            ("Tapered", "Tapered.svg", self.toggle_tapered),
            ("Ovoide", "Ovoide.svg", self.toggle_ovoide),
            ("Narrow T", "NarrowTapered.svg", self.toggle_narrow_tapered),
            ("Narrow O", "NarrowOvoide.svg", self.toggle_narrow_ovoide),
        ]
        start_row = 10
        for idx, (label, filename, command) in enumerate(image_buttons):
            btn_cfg = {
                'text': label,
                'command': command,
                'grid': {'row': start_row + idx, 'column': 0, 'columnspan': 2, 'pady': 2, 'sticky': 'ew'},
                'width': 10,
                'variable_name': f'btn_{label.lower().replace(" ", "_")}'
            }
            self.create_button(parent, btn_cfg)

    ########################################################################
    # Image Window
    ########################################################################

    def setup_image_window(self):
        """Create the borderless/transparent image window."""
        self.image_window = tk.Toplevel(self.root)
        self.image_window.title("Image Window")
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        self.image_window.geometry(f"{screen_width}x{screen_height}+0+0")
        self.image_window.resizable(True, True)
        self.image_window.overrideredirect(True)
        self.image_window.attributes('-transparentcolor', 'grey')
        self.image_window.attributes('-topmost', True)
        self.image_window.protocol("WM_DELETE_WINDOW", self.on_close)

        self.canvas = tk.Canvas(
            self.image_window, bg='grey',
            highlightthickness=0, borderwidth=0
        )
        self.canvas.pack(fill='both', expand=True)
        self.image_window.update_idletasks()

        self.bind_canvas_events()
        self.image_window.bind('<Configure>', self.on_image_window_resize)

    def bind_canvas_events(self):
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.canvas.bind("<B1-Motion>", self.on_mouse_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_click)
        self.canvas.bind("<Button-3>", self.on_right_click)

        if sys.platform.startswith('win'):
            self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        elif sys.platform == 'darwin':
            self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        else:
            self.canvas.bind("<Button-4>", lambda event: self.on_mouse_wheel(event))
            self.canvas.bind("<Button-5>", lambda event: self.on_mouse_wheel(event))

    ########################################################################
    # Global Hotkeys
    ########################################################################

    def setup_global_hotkeys(self):
        logging.info("Initializing global hotkeys...")

        def toggle_image_control_hotkey():
            logging.info("Global hotkey: Ctrl+Alt+1 pressed. Toggling image control.")
            ic_plugin = self.plugin_loader.get_plugin("ImageControl")
            if ic_plugin:
                self.root.after(0, ic_plugin.toggle_image_control)
            else:
                logging.warning("ImageControl plugin not found.")

        def toggle_image_window_hotkey():
            logging.info("Global hotkey: Ctrl+Alt+2 pressed. Toggling image window visibility.")
            self.root.after(0, self.toggle_image_window)

        # If you re-enable full control, add your hotkey back
        # def toggle_full_control_hotkey():
        #     logging.info("Global hotkey: Ctrl+Alt+3 pressed. Toggling full control mode.")
        #     self.root.after(0, self.toggle_full_control_mode_from_hotkey)

        def toggle_wsad_remap():
            logging.info("Global hotkey: Ctrl+Alt+4 pressed. Toggling WASD remap.")
            keyboard_remapper_plugin = self.plugin_loader.get_plugin("LowLevelKeyboardRemapper")
            if keyboard_remapper_plugin:
                self.root.after(0, keyboard_remapper_plugin.toggle_remap)

        try:
            self.global_hotkey_listener = keyboard.GlobalHotKeys({
                '<ctrl>+<alt>+1': toggle_image_control_hotkey,
                '<ctrl>+<alt>+2': toggle_image_window_hotkey,
                # '<ctrl>+<alt>+3': toggle_full_control_hotkey,  # Commented out for now
                '<ctrl>+<alt>+4': toggle_wsad_remap
            })
            self.global_hotkey_listener.start()
            logging.info("Global Hotkeys listener started successfully.")
        except ValueError as ve:
            logging.error(f"Failed to start Global Hotkeys: {ve}")
            messagebox.showerror("Hotkey Error", f"Failed to start hotkeys: {ve}")

    ########################################################################
    # Event Handlers - Canvas
    ########################################################################

    def on_image_window_resize(self, event):
        self.canvas.config(width=event.width, height=event.height)
        self.draw_images()

    def on_mouse_down(self, event):
        if not self.is_rotation_point_mode:
            self.is_dragging = True
            self.start_x = event.x_root
            self.start_y = event.y_root
            logging.debug(f"Mouse down at ({self.start_x}, {self.start_y}).")

    def on_mouse_up(self, event):
        self.is_dragging = False
        logging.debug(f"Mouse up at ({event.x_root}, {event.y_root}).")

    def on_mouse_move(self, event):
        active_image = self.get_active_image()
        if self.is_dragging and active_image:
            dx = event.x_root - self.start_x
            dy = event.y_root - self.start_y
            if event.state & 0x0004:  # Middle mouse drag?
                active_image.angle += dx * 0.1
                active_image.angle %= 360
                logging.debug(f"Rotating image '{active_image.name}' by {dx * 0.1} degrees.")
            else:
                active_image.offset_x += dx
                active_image.offset_y += dy
                logging.debug(f"Moving image '{active_image.name}' by ({dx}, {dy}).")
            self.start_x = event.x_root
            self.start_y = event.y_root
            self.draw_images()

    def on_canvas_click(self, event):
        active_image = self.get_active_image()
        if active_image and self.is_rotation_point_mode:
            active_image.rotation_point = (event.x, event.y)
            self.is_rotation_point_mode = False
            if hasattr(self, 'btn_rotation_point'):
                self.btn_rotation_point.config(text="Rot Pt")
            self.draw_images()
            logging.info(f"Rotation point set for image '{active_image.name}' at ({event.x}, {event.y}).")
        elif active_image:
            # Check if clicked outside the active image
            img = active_image.image_original.copy()
            img = img.resize(
                (int(img.width * active_image.scale), int(img.height * active_image.scale)),
                Image.LANCZOS
            )

            if active_image.is_flipped_horizontally:
                img = img.transpose(Image.FLIP_LEFT_RIGHT)
            if active_image.is_flipped_vertically:
                img = img.transpose(Image.FLIP_TOP_BOTTOM)

            img_width, img_height = img.size
            x_min = active_image.offset_x - img_width / 2
            y_min = active_image.offset_y - img_height / 2
            x_max = active_image.offset_x + img_width / 2
            y_max = active_image.offset_y + img_height / 2

            if not (x_min <= event.x <= x_max and y_min <= event.y <= y_max):
                ic_plugin = self.plugin_loader.get_plugin("ImageControl")
                if ic_plugin:
                    ic_plugin.toggle_image_control(False)
                logging.info("Clicked outside the active image. Image control disabled.")

    def on_mouse_wheel(self, event):
        active_image = self.get_active_image()
        if not active_image:
            return
        delta = self.get_mouse_wheel_delta(event)
        active_image.scale_log += delta * 0.05
        active_image.scale = pow(2, active_image.scale_log)
        active_image.scale = max(0.1, min(active_image.scale, 10.0))
        active_image.scale_log = math.log2(active_image.scale)
        logging.debug(f"Zooming image '{active_image.name}' to scale {active_image.scale}.")
        self.draw_images()

    def get_mouse_wheel_delta(self, event):
        if sys.platform.startswith('win') or sys.platform == 'darwin':
            return event.delta / 120
        else:
            if event.num == 4:
                return 1
            elif event.num == 5:
                return -1
            return 0

    def on_right_click(self, event=None):
        """Reset the active image to default transforms on right-click."""
        active_image = self.get_active_image()
        if not active_image:
            return
        active_image.angle = 0
        active_image.scale = 1.0
        active_image.scale_log = 0
        active_image.offset_x = self.canvas.winfo_width() / 2
        active_image.offset_y = self.canvas.winfo_height() / 2
        active_image.image_transparency_level = 1.0

        if hasattr(self, 'btn_toggle_transparency'):
            self.btn_toggle_transparency.config(text="Transp")

        active_image.is_flipped_horizontally = False
        active_image.is_flipped_vertically = False
        active_image.rotation_point = None
        self.is_rotation_point_mode = False
        if hasattr(self, 'btn_rotation_point'):
            self.btn_rotation_point.config(text="Rot Pt")

        self.draw_images()
        logging.info(f"Reset transformations for image '{active_image.name}'.")

    ########################################################################
    # Toggle Window
    ########################################################################

    def toggle_image_window(self):
        """Show or hide the separate image window."""
        if self.image_window_visible:
            self.image_window.withdraw()
            self.image_window_visible = False
            if hasattr(self, 'btn_hide_show_image'):
                self.btn_hide_show_image.config(text="Show")
            logging.info("Image window hidden.")
        else:
            self.image_window.deiconify()
            self.image_window_visible = True
            if hasattr(self, 'btn_hide_show_image'):
                self.btn_hide_show_image.config(text="Hide")
            logging.info("Image window shown.")
            self.image_window.update_idletasks()
            self.draw_images()

    ########################################################################
    # Image Transparency
    ########################################################################

    def toggle_transparency(self):
        """Toggle the active image's transparency between min and max."""
        active_image = self.get_active_image()
        if not active_image:
            return

        if active_image.image_transparency_level > 0.2:
            active_image.image_transparency_level = 0.2
            if hasattr(self, 'btn_toggle_transparency'):
                self.btn_toggle_transparency.config(text="Max Transp")
            logging.info(f"Transparency of image '{active_image.name}' set to minimum.")
        else:
            active_image.image_transparency_level = 1.0
            if hasattr(self, 'btn_toggle_transparency'):
                self.btn_toggle_transparency.config(text="Min Transp")
            logging.info(f"Transparency of image '{active_image.name}' set to maximum.")
        self.draw_images()

    def update_transparency_button(self):
        """Set the transparency button label based on the current active image's transparency."""
        active_image = self.get_active_image()
        if not hasattr(self, 'btn_toggle_transparency'):
            return

        if active_image and active_image.image_transparency_level <= 0.2:
            self.btn_toggle_transparency.config(text="Max Transp")
        else:
            self.btn_toggle_transparency.config(text="Min Transp")

    ########################################################################
    # Image Loading & Drawing
    ########################################################################

    def load_image(self, image_name):
        """Prompt the user to load an image, store it in self.images, then draw."""
        filepath = filedialog.askopenfilename(
            title=f"Select {image_name}",
            filetypes=[("Image Files", "*.jpg;*.jpeg;*.png;*.bmp;*.svg")]
        )
        if filepath:
            image_original, svg_content = self.open_image_file(filepath)
            if image_original:
                image_state = ImageState(image_original, image_name, svg_content=svg_content)
                self.images[image_name] = image_state
                self.active_image_name = image_name
                self.draw_images()
                logging.info(f"Image '{image_name}' loaded from '{filepath}'.")
                if not self.image_window_visible:
                    self.toggle_image_window()

    def open_image_file(self, filepath):
        """Open an image (or SVG) from filepath, returning (PIL.Image, possible_svg_content)."""
        try:
            if filepath.lower().endswith('.svg'):
                with open(filepath, 'r', encoding='utf-8') as svg_file:
                    svg_content = svg_file.read()
                png_data = cairosvg.svg2png(url=filepath)
                image_original = Image.open(io.BytesIO(png_data)).convert("RGBA")
                return image_original, svg_content
            else:
                image_original = Image.open(filepath).convert("RGBA")
                return image_original, None
        except Exception as e:
            logging.error(f"Error loading image: {e}")
            return None, None

    def load_default_image(self, image_key, filename):
        """Load a predefined image from the Images folder."""
        filepath = resource_path(os.path.join('Images', filename))
        if os.path.exists(filepath):
            image_original, svg_content = self.open_image_file(filepath)
            if image_original:
                image_state = ImageState(image_original, image_key, svg_content=svg_content)
                self.images[image_key] = image_state
                self.center_image(image_key)
                self.draw_images()
                logging.info(f"Default '{image_key}' image loaded.")
                if not self.image_window_visible:
                    self.toggle_image_window()
        else:
            logging.error(f"'{filename}' not found at {filepath}")

    def center_image(self, image_key):
        """Center the specified image on the canvas, offset by a small margin."""
        if image_key in self.images:
            self.image_window.update_idletasks()
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            image_state = self.images[image_key]
            image_state.offset_x = (canvas_width / 2) + 156
            image_state.offset_y = (canvas_height / 2) + 100

    def draw_images(self):
        """Redraw all visible images in self.images."""
        self.canvas.delete("all")
        for image_state in self.images.values():
            if image_state.visible:
                self.draw_image(image_state)
        self.image_window.update_idletasks()

    def draw_image(self, image_state):
        """Apply flips, rotation, scaling, and transparency, then draw the image on canvas."""
        img = image_state.image_original.copy()
        if image_state.image_transparency_level < 1.0:
            alpha = img.getchannel('A')
            alpha = alpha.point(lambda p: int(p * image_state.image_transparency_level))
            img.putalpha(alpha)

        img = img.resize(
            (int(img.width * image_state.scale), int(img.height * image_state.scale)),
            Image.LANCZOS
        )

        if image_state.is_flipped_horizontally:
            img = img.transpose(Image.FLIP_LEFT_RIGHT)
        if image_state.is_flipped_vertically:
            img = img.transpose(Image.FLIP_TOP_BOTTOM)

        if image_state.rotation_point:
            rotation_center = (
                image_state.rotation_point[0] - (image_state.offset_x - img.width / 2),
                image_state.rotation_point[1] - (image_state.offset_y - img.height / 2)
            )
            img = img.rotate(image_state.angle, expand=True, center=rotation_center)
        else:
            img = img.rotate(image_state.angle, expand=True)

        image_state.image_display = ImageTk.PhotoImage(img)
        self.canvas.create_image(
            image_state.offset_x, image_state.offset_y, image=image_state.image_display
        )

        if image_state.rotation_point:
            radius = 1.5
            self.canvas.create_oval(
                image_state.rotation_point[0] - radius, image_state.rotation_point[1] - radius,
                image_state.rotation_point[0] + radius, image_state.rotation_point[1] + radius,
                fill='red', outline=''
            )

    ########################################################################
    # Image Toggling
    ########################################################################

    def toggle_ruler(self):
        self.toggle_predefined_image("Ruler", 'liniar_new_n2.svg', "Ruler")

    def toggle_normal(self):
        self.toggle_predefined_image("Normal", 'Normal(medium).svg', "Normal")

    def toggle_tapered(self):
        self.toggle_predefined_image("Tapered", 'Tapered.svg', "Tapered")

    def toggle_ovoide(self):
        self.toggle_predefined_image("Ovoide", 'Ovoide.svg', "Ovoide")

    def toggle_narrow_tapered(self):
        self.toggle_predefined_image("Narrow Tapered", 'NarrowTapered.svg', "Narrow Tapered")

    def toggle_narrow_ovoide(self):
        self.toggle_predefined_image("Narrow Ovoide", 'NarrowOvoide.svg', "Narrow Ovoide")

    def toggle_angulation(self):
        self.toggle_predefined_image("Angulation", 'angulation.svg', "Angulation")

    def toggle_predefined_image(self, image_key, filename, button_label):
        """Show/hide a predefined image using our images dict and additional_images_visibility."""
        if not self.additional_images_visibility[image_key]:
            # Hide previously active
            if self.active_image_name and self.active_image_name in self.images:
                self.images[self.active_image_name].visible = False

            # If not loaded, load
            if image_key not in self.images:
                self.load_default_image(image_key, filename)
            else:
                self.images[image_key].visible = True
                self.draw_images()

            self.additional_images_visibility[image_key] = True
            logging.info(f"{image_key} image made visible.")
            self.previous_active_image_name = self.active_image_name
            self.active_image_name = image_key

            # Enable image control if present
            ic_plugin = self.plugin_loader.get_plugin("ImageControl")
            if ic_plugin:
                ic_plugin.toggle_image_control(True)

            if not self.image_window_visible:
                self.toggle_image_window()
        else:
            # Hide it
            if image_key in self.images:
                self.images[image_key].visible = False
                self.draw_images()

            self.additional_images_visibility[image_key] = False
            logging.info(f"{image_key} image hidden.")

            if self.active_image_name == image_key:
                self.active_image_name = self.previous_active_image_name
                if self.active_image_name and self.active_image_name in self.images:
                    self.images[self.active_image_name].visible = True
                self.previous_active_image_name = None

                ic_plugin = self.plugin_loader.get_plugin("ImageControl")
                if ic_plugin:
                    ic_plugin.toggle_image_control(False)

                self.draw_images()

    ########################################################################
    # Rotation, Zoom, Flips
    ########################################################################

    def toggle_rotation_point_mode(self):
        active_image = self.get_active_image()
        if not active_image:
            return
        if not self.is_rotation_point_mode:
            self.is_rotation_point_mode = True
            if hasattr(self, 'btn_rotation_point'):
                self.btn_rotation_point.config(text="Cancel Rot Pt")
            logging.info("Rotation point mode enabled.")
        else:
            self.is_rotation_point_mode = False
            if hasattr(self, 'btn_rotation_point'):
                self.btn_rotation_point.config(text="Rot Pt")
            active_image.rotation_point = None
            logging.info("Rotation point mode disabled and rotation point reset.")
            self.draw_images()

    def zoom_in(self):
        self.adjust_zoom(0.05)

    def zoom_out(self):
        self.adjust_zoom(-0.05)

    def fine_zoom_in(self):
        self.adjust_zoom(0.01)

    def fine_zoom_out(self):
        self.adjust_zoom(-0.01)

    def adjust_zoom(self, amount):
        active_image = self.get_active_image()
        if not active_image:
            return
        active_image.scale = max(0.1, min(active_image.scale + amount, 10.0))
        active_image.scale_log = math.log2(active_image.scale)
        logging.info(f"Adjusted zoom for image '{active_image.name}' to scale {active_image.scale}.")
        self.draw_images()

    def fine_rotate_clockwise(self):
        self.adjust_rotation(0.5)

    def fine_rotate_counterclockwise(self):
        self.adjust_rotation(-0.5)

    def adjust_rotation(self, angle_increment):
        active_image = self.get_active_image()
        if not active_image:
            return
        active_image.angle = (active_image.angle + angle_increment) % 360
        logging.info(f"Rotated image '{active_image.name}' by {angle_increment} degrees.")
        self.draw_images()

    def flip_image_horizontal(self):
        active_image = self.get_active_image()
        if not active_image:
            return
        active_image.is_flipped_horizontally = not active_image.is_flipped_horizontally
        logging.info(f"Image '{active_image.name}' flipped horizontally.")
        self.draw_images()

    def flip_image_vertical(self):
        active_image = self.get_active_image()
        if not active_image:
            return
        active_image.is_flipped_vertically = not active_image.is_flipped_vertically
        logging.info(f"Image '{active_image.name}' flipped vertically.")
        self.draw_images()

    ########################################################################
    # Image Helpers
    ########################################################################

    def get_active_image(self):
        return self.images.get(self.active_image_name)

    def load_user_image(self):
        """Prompt the user to load any user image at runtime."""
        filepath = filedialog.askopenfilename(
            initialdir=self.images_dir,
            title="Select Image",
            filetypes=[("Image Files", "*.jpg;*.jpeg;*.png;*.bmp;*.svg")]
        )
        if not filepath:
            return
        image_original, svg_content = self.open_image_file(filepath)
        if not image_original:
            messagebox.showerror("Load Failed", "Failed to load the selected image.")
            return

        default_name = os.path.splitext(os.path.basename(filepath))[0]
        image_name = simpledialog.askstring("Image Name", "Enter a unique name for the image:", initialvalue=default_name)
        if not image_name:
            messagebox.showwarning("Name Required", "Image name is required to load the image.")
            return

        original_name = image_name
        counter = 1
        while image_name in self.images:
            image_name = f"{original_name}_{counter}"
            counter += 1

        if self.active_image_name and self.active_image_name in self.images:
            self.images[self.active_image_name].visible = False

        image_state = ImageState(image_original, image_name, svg_content=svg_content)
        self.images[image_name] = image_state
        self.active_image_name = image_name
        self.images[self.active_image_name].visible = True
        self.draw_images()
        logging.info(f"User-loaded image '{image_name}' loaded from '{filepath}'.")

        ic_plugin = self.plugin_loader.get_plugin("ImageControl")
        if ic_plugin:
            ic_plugin.toggle_image_control(True)

        if not self.image_window_visible:
            self.toggle_image_window()

    ########################################################################
    # Closing and Cleanup
    ########################################################################

    def on_close(self):
        """Gracefully stop plugins, close windows, and end the application."""
        try:
            if hasattr(self, 'plugin_loader'):
                self.plugin_loader.cleanup()
            if hasattr(self, 'image_window'):
                self.image_window.destroy()
            for window in self.additional_windows:
                if window.winfo_exists():
                    window.destroy()
            if hasattr(self, 'global_hotkey_listener'):
                self.global_hotkey_listener.stop()
            if hasattr(self, 'images'):
                self.images.clear()
            if self.root.winfo_exists():
                self.root.destroy()
        except Exception as e:
            logging.error(f"Error during application cleanup: {e}")
        finally:
            sys.exit(0)

    ########################################################################
    # (Optional) Toggling Full Control
    ########################################################################
    def toggle_image_control_via_plugin(self):
        """Example method to toggle the ImageControl plugin from within Orthy."""
        ic_plugin = self.plugin_loader.get_plugin("ImageControl")
        if ic_plugin:
            ic_plugin.toggle_image_control()
        else:
            logging.warning("ImageControl plugin not found.")

    def toggle_full_control_mode_from_plugin(self):
        """Example method to toggle a hypothetical MaestroControls plugin from within Orthy."""
        mc_plugin = self.plugin_loader.get_plugin("MaestroControls")
        if mc_plugin and hasattr(mc_plugin, 'toggle_full_control'):
            mc_plugin.toggle_full_control()
        else:
            logging.warning("MaestroControls plugin not found or missing toggle_full_control method.")

    ########################################################################
    # SVG-Related (Optional)
    ########################################################################

    def apply_transformations_to_svg(self, image_state):
        try:
            svg_content = image_state.svg_content
            if not svg_content:
                return None
            parser = etree.XMLParser(ns_clean=True, recover=True, encoding='utf-8')
            svg_root = etree.fromstring(svg_content.encode('utf-8'), parser=parser)

            transforms = []
            if image_state.is_flipped_horizontally or image_state.is_flipped_vertically:
                scale_x = -1 if image_state.is_flipped_horizontally else 1
                scale_y = -1 if image_state.is_flipped_vertically else 1
                transforms.append(f"scale({scale_x},{scale_y})")

            if image_state.scale != 1.0:
                transforms.append(f"scale({image_state.scale})")

            if image_state.angle != 0:
                if image_state.rotation_point:
                    cx, cy = image_state.rotation_point
                else:
                    cx = image_state.offset_x
                    cy = image_state.offset_y
                transforms.append(f"rotate({image_state.angle},{cx},{cy})")

            transforms.append(f"translate({image_state.offset_x},{image_state.offset_y})")
            transform_str = ' '.join(transforms)
            g = etree.Element("g")
            g.set("transform", transform_str)

            for child in list(svg_root):
                svg_root.remove(child)
                g.append(child)

            svg_root.append(g)
            if image_state.image_transparency_level != 1.0:
                g.set("opacity", str(image_state.image_transparency_level))

            return etree.tostring(svg_root, encoding='utf-8', method='xml', pretty_print=True).decode('utf-8')
        except Exception as e:
            logging.error(f"Error applying transformations to SVG: {e}")
            return None

    def get_transformed_image(self, image_state):
        """Return a PIL Image with all flips/rotations/transparency applied, for e.g. saving."""
        try:
            img = image_state.image_original.copy()
            if image_state.is_flipped_horizontally:
                img = img.transpose(Image.FLIP_LEFT_RIGHT)
            if image_state.is_flipped_vertically:
                img = img.transpose(Image.FLIP_TOP_BOTTOM)

            img = img.resize(
                (int(img.width * image_state.scale), int(img.height * image_state.scale)),
                Image.LANCZOS
            )
            img = img.rotate(-image_state.angle, expand=True)
            if image_state.image_transparency_level < 1.0:
                alpha = img.getchannel('A')
                alpha = alpha.point(lambda p: int(p * image_state.image_transparency_level))
                img.putalpha(alpha)

            return img
        except Exception as e:
            logging.error(f"Error getting transformed image: {e}")
            return None

##############################################################################
# Main Entry Point
##############################################################################

if __name__ == "__main__":
    root = tk.Tk()
    app = Orthy(root)
    root.mainloop()
