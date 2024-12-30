import logging
import os
import ctypes
from ctypes import wintypes
from tkinter import messagebox, filedialog, Toplevel, Label, Frame, Button
from pynput import keyboard, mouse
from pynput.keyboard import Key
from  core.OrthyPlugin_Interface import OrthyPlugin
from  Test_py_files.ButtonFactory import ButtonFactory

class MaestroControlsPlugin(OrthyPlugin):
    def __init__(self):
        self.app = None # Reference to the main app
        self.full_control_mode = False
        self.full_control_hotkey_listener = None
        self.maestro_version = None
        self.ghost_click_positions = {}
        self.alt_pressed = False
        self.ctrl_pressed = False
        self.coords_loaded = False
        self.registered = False

        #this will be a temp solution to the button update, we will need to change this later
        #self.btn_full_control_maestro = None

    def initialize(self, app_instance): # Called by the plugin loader 
        self.app = app_instance
        
    def get_name(self): # Make sure the string here matches the filename!!!

        return "SegmentationMaestro"

    #this is the universal name for the method that returns the button(even if its only one)
    def get_btn_configs(self): 
       return [{
            'text': 'Segmentation Maestro',
            'command': self.toggle_full_control,
            'grid': {'row': 22, 'column': 0, 'columnspan': 2, 'pady': 2, 'sticky': 'ew'},
            'width': 10,
            'variable_name': 'btn_toggle_full_control_maestro',
            'bg': 'red',
            'fg': 'white'
        }]

    def toggle_full_control(self):
        if not self.registered:
            self.app.register_plugin_sentinels(self.get_name(),self.full_control_mode)
            self.registered = True
        if self.full_control_mode is False:
            # We are about to enable full control mode

            # If we already have maestro_version and coords_loaded, skip prompts
            if self.maestro_version is not None and self.coords_loaded is True:
                self.full_control_mode = True
                self.start_full_control_hotkeys()
                remmapper = self.app.plugin_loader.get_plugin('LowLevelKeyboardRemapper')
                if remmapper is not None:
                    remmapper.toggle_remap()
                self.update_button()
                logging.info(f"Full Control Mode Resumed for Maestro {self.maestro_version}")
                return

            version = self.prompt_maestro_version()
            if version is None:
                return
            self.maestro_version = version

            if not self.setup_coordinates():
                return

            self.full_control_mode = True
            remmapper = self.app.plugin_loader.get_plugin('LowLevelKeyboardRemapper')
            self.start_full_control_hotkeys()
            if remmapper:
                remmapper.toggle_remap()
            self.update_button()
            logging.info(f"Full Control Mode Enabled for Maestro {self.maestro_version}")
        else:
            # Turning off full control mode
            self.full_control_mode = False
            remmapper = self.app.plugin_loader.get_plugin('LowLevelKeyboardRemapper')
            if remmapper:
                remmapper.toggle_remap()
            self.stop_full_control_hotkeys()
            self.update_button()
            logging.info("Full Control Mode Disabled")
    
    def setup_coordinates(self):
        """
        Adjusted method:
        1. Check if coords file for current maestro_version exists.
           If yes, load it and set coords_loaded = True, return True.
        2. If not, ask yes/no for manual selection or skip coordinates selection.
           If yes (manual), run select_control_coordinates. If that fails, return False.
           If no, just return False (or you can decide to load a default file if you want).
        """
        coords_file = os.path.join(self.app.base_dir, f'coords_maestro_{self.maestro_version}.txt')
        if os.path.exists(coords_file):
            # Load coordinates silently
            if self.load_coords_from_file(coords_file):
                self.coords_loaded = True
                logging.info(f"Coordinates for Maestro {self.maestro_version} loaded from {coords_file} without prompting.")
                return True
            else:
                logging.error("Failed to load existing coords file. Will prompt user.")
                # If loading failed, proceed to prompt as fallback.

        # No coords file found or loading failed. Prompt user.
        response = messagebox.askyesno("Coordinate Setup",
            "Coordinates file not found.\nClick Yes to select coords manually, No to skip full control setup.")
        if response:
            if not self.select_control_coordinates():
                return False
            # If select_control_coordinates succeeded, coords_loaded = True
            self.coords_loaded = True
        else:
            # User chose not to select coords, cannot proceed.
            logging.info("User skipped coordinate setup. Full control mode not enabled.")
            return False

        return True

    def select_control_coordinates(self):
        """
        Guides user to select coords manually.
        """
        controls = [
            'EnFaceOcclusion', 'LateralOcclusionLeft', 'LateralOcclusionRight',
            'Enface', 'BottomView', 'TopView',
            'UpperArch', 'LowerArch', 
            'JoinDivide', 'SegBrush',
            'Smoothing', 'AddRemove', 
            'DistalTip', 'MesialTip', 
            'PositiveTorque', 'NegativeTorque',
            'DistalLinear', 'MesialLinear',
            'BuccalLinear', 'LingualLinear',
        ]
        self.ghost_click_positions = {}

        for control in controls:
            messagebox.showinfo("Select Control", f"Please click on the '{control}' control on the screen.")
            self.app.root.withdraw()
            self.app.image_window.withdraw()
            pos = self.wait_for_click()
            self.app.root.deiconify()
            self.app.image_window.deiconify()
            if pos is None:
                logging.error(f"Failed to record position for {control}")
                return False
            self.ghost_click_positions[control] = pos
        # Save coordinates to file
        self.save_coords_to_file(controls)
        return True

    def wait_for_click(self):
        position = [None]

        def on_click(x, y, button, pressed):
            if pressed and button == mouse.Button.left:
                position[0] = (x, y)
                """After storing the coordinates, the function returns False. 
                In many mouse-listener patterns, returning False indicates that the 
                listener should stop processing further events, effectively capturing 
                just one click before concluding. This approach is often used to retrieve a 
                single coordinate pair and then halt the callback to prevent ongoing mouse event tracking."""
                return False

        with mouse.Listener(on_click=on_click) as listener:
            listener.join() # this blocks code execution until there is a click event
        return position[0]

    def save_coords_to_file(self, controls):
        coords_file = os.path.join(self.app.base_dir, f'coords_maestro_{self.maestro_version}.txt')
        try:
            with open(coords_file, 'w') as f:
                for c in controls:
                    pos = self.ghost_click_positions.get(c)
                    if pos:
                        f.write(f"{c}:{pos[0]},{pos[1]}\n")
            logging.info(f"Coordinates saved to {coords_file}")
            messagebox.showinfo("Coordinates Saved", f"Coordinates saved to {coords_file}")
        except Exception as e:
            logging.error(f"Failed to save coordinates: {e}")
            messagebox.showerror("Save Failed", "Failed to save coordinates")

    def load_coords_from_file(self, filepath):
        try:
            self.ghost_click_positions.clear()
            with open(filepath, 'r') as f:
                for line in f:
                    if ':' not in line:
                        continue
                    control, pos = line.strip().split(':')
                    x_str, y_str = pos.split(',')
                    self.ghost_click_positions[control] = (int(x_str), int(y_str))
            logging.info(f"Coordinates loaded from {filepath}")
            return True
        except Exception as e:
            logging.error(f"Failed to load coordinates from file: {e}")
            messagebox.showerror("Load Failed", "Failed to load coordinates from the file")
            return False

    def prompt_maestro_version(self):
        return self.create_dual_prompt("Maestro 4", "Maestro 6")

    def create_dual_prompt(self, option1, option2):
        selected = [None]

        def select_option(option):
            selected[0] = option
            top.destroy()

        top = self._create_modal_window("Select Maestro Version")
        top.width = 300
        top.height = 150
        self._center_window(top)
        self._add_prompt_controls(top, "Select Maestro version:", option1, option2, select_option)
        top.wait_window()
        return selected[0]

    def start_full_control_hotkeys(self):
        if self.full_control_hotkey_listener:
            self.stop_full_control_hotkeys()

        def on_press(key): # this is a good method to add in an emit_event method
            if key in (Key.alt_l, Key.alt_r): self.alt_pressed = True
            if key in (Key.ctrl_l, Key.ctrl_r): self.ctrl_pressed = True
            if self.alt_pressed:
                self.handle_alt_combos(key)
            return True

        def on_release(key):
            if key in (Key.alt_l, Key.alt_r): self.alt_pressed = False
            if key in (Key.ctrl_l, Key.ctrl_r): self.ctrl_pressed = False
            return True

        try:
            self.full_control_hotkey_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
            self.full_control_hotkey_listener.start()
        except Exception as e:
            logging.error(f"Failed to start hotkeys: {e}")
            messagebox.showerror("Hotkey Error", f"Could not start hotkeys: {e}")

    def handle_alt_combos(self, key):
        # Alt + ctrl only
        if self.ctrl_pressed:
            if key == Key.up:
                self.perform_ghost_click('BuccalLinear')
            elif key == Key.down:
                self.perform_ghost_click('LingualLinear')
        else:
            # Just Alt
            if key == Key.up:
                self.perform_ghost_click('PositiveTorque')
            elif key == Key.down:
                self.perform_ghost_click('NegativeTorque')
            elif key == Key.right:
                self.perform_ghost_click('MesialLinear')
            elif key == Key.left:
                self.perform_ghost_click('DistalLinear')
            elif hasattr(key, 'char'):
                mapping = {
                    'e': 'MesialTip',
                    'q': 'DistalTip',
                    'z': 'DistalRotation',
                    'c': 'MesialRotation',
                    'x': 'JoinDivide',
                    'v': 'JoinDivide',
                    '1': 'EnFace',
                    '2': 'BottomView', 
                    '3': 'TopView',
                    '-': 'UpperArch',
                    '=': 'LowerArch',
                    'y': 'EnFaceOcclusion',
                    'h': 'LateralOcclusionLeft',
                    'j': 'LateralOcclusionRight',
                }
                action = mapping.get(key.char)
                if action:
                    self.perform_ghost_click(action)

    def stop_full_control_hotkeys(self):
        if self.full_control_hotkey_listener:
            self.full_control_hotkey_listener.stop()
            self.full_control_hotkey_listener = None

    def perform_ghost_click(self, action_name):
        pos = self.ghost_click_positions.get(action_name)
        if not pos:
            logging.error(f"No position for '{action_name}'")
            return
        original = self.get_cursor_pos()
        self.ghost_click_at_position(pos)
        self.set_cursor_pos(*original)
        logging.info(f"Performed ghost click on action '{action_name}' at position {pos}.")

    def get_cursor_pos(self):
        pt = wintypes.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        return (pt.x, pt.y)

    def set_cursor_pos(self, x, y):
        ctypes.windll.user32.SetCursorPos(x, y)

    def ghost_click_at_position(self, pos):
        x, y = pos
        screen_w = ctypes.windll.user32.GetSystemMetrics(0)
        screen_h = ctypes.windll.user32.GetSystemMetrics(1)
        abs_x = int(x * 65536 / screen_w)
        abs_y = int(y * 65536 / screen_h)

        INPUT_MOUSE = 0
        MOUSE_MOVE = 0x0001 | 0x8000
        MOUSE_DOWN = 0x0002
        MOUSE_UP = 0x0004

        class MOUSEINPUT(ctypes.Structure):
            _fields_ = [
                ("dx", ctypes.c_long), ("dy", ctypes.c_long), ("mouseData", ctypes.c_ulong),
                ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong), ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))
            ]

        class INPUT(ctypes.Structure):
            _fields_ = [("type", ctypes.c_ulong), ("mi", MOUSEINPUT)]

        def make_input(dx, dy, flags):
            inp = INPUT()
            inp.type = INPUT_MOUSE
            inp.mi = MOUSEINPUT(dx=dx, dy=dy, mouseData=0, dwFlags=flags, time=0, dwExtraInfo=None)
            return inp

        inputs = (make_input(abs_x, abs_y, MOUSE_MOVE),
                  make_input(0, 0, MOUSE_DOWN),
                  make_input(0, 0, MOUSE_UP))

        ctypes.windll.user32.SendInput(len(inputs), (INPUT * len(inputs))(*inputs), ctypes.sizeof(INPUT))

    def cleanup(self):
        if self.full_control_hotkey_listener:
            self.stop_full_control_hotkeys()

    def _create_modal_window(self, title):
        top = Toplevel(self.app.root)
        top.title(title)
        top.attributes('-topmost', True)
        top.grab_set()
        return top

    def _add_prompt_controls(self, parent, prompt_text, option1, option2, callback):
        Label(parent, text=prompt_text).pack(pady=10)
        btn_frame = Frame(parent)
        btn_frame.pack(pady=10)
        Button(btn_frame, text=option1, command=lambda: callback(option1)).pack(side='left', padx=20)
        Button(btn_frame, text=option2, command=lambda: callback(option2)).pack(side='right', padx=20)

    def _center_window(self, window):
        window.update_idletasks()
        w = window.winfo_width()
        h = window.winfo_height()
        x = (window.winfo_screenwidth() // 2) - (w // 2)
        y = (window.winfo_screenheight() // 2) - (h // 2)
        window.geometry(f'{w}x{h}+{x}+{y}')

    ##################################################################################
    # Helper functions
    ##################################################################################
    def update_button(self):
        self.app.update_plugin_sentinels(self.get_name(),self.full_control_mode)
        self.app.update_plugin_buttons(self.get_name())