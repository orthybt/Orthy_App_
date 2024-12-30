# plugins/maestro_controls.py

from core.OrthyPlugin_Interface import OrthyPlugin
from tkinter import messagebox, filedialog, Toplevel, Label, Frame, Button
from pynput import keyboard, mouse
from pynput.keyboard import Key
import logging
import os
import ctypes
from ctypes import wintypes

class MaestroControlsPlugin(OrthyPlugin):
    def __init__(self): # Class constructor
        self.app = None 
        self.full_control_mode = False # sentinel for full control mode
        self.full_control_hotkey_listener = None # sentinel for hotkey listener
        self.maestro_version = None
        self.ghost_click_positions = {} # empty dictionary for ghost click positions

    def initialize(self, app_instance):  # this is the setter for the app instance
        self.app = app_instance

    def get_name(self): # this are the getters for the plugin name and the buttons
        return "MaestroControls"

    def get_buttons(self): 
        return [{
            'text': 'Maestro Controls',
            'command': self.toggle_full_control,
            'grid': {'row': 18, 'column': 0, 'columnspan': 2, 'pady': 2, 'sticky': 'ew'},
            'width': 10,
            'variable_name': 'btn_full_control',
            'bg': 'red',
            'fg': 'white'
        }]
    ###########################################################################################################################################
    ### Toggle_full_control defines:
    # ######  maestro version 
    # ######  activates or deactivates start_full_controls
    # ######  and changes the apperance of the buttons ###
    ###########################################################################################################################################
    # TODO   : Create a button method to generate buttons, every plugin that has gui elements should have its own guiGenerator method
    # TODO  : Change the management of the buttons to the plugin itself, so the app does not have to handle the buttons state 
    # TODO  : Change the name of this method to toggle_key_remmaping!!! !GPT DO NOT DELETE TODO    comments! NEVER!
    def toggle_full_control(self):  
        if self.full_control_mode==False: # I like this syntax better, it is more readable, rather than using if not self.full_control_mode!!! REMEMBER THIS! !GPT
            # Prompt user to select Maestro version
            maestro_version = self.create_dual_prompt() 
            if maestro_version is None:
                return # User cancelled
            self.maestro_version = maestro_version

            # Simplified coordinate setup dialog
            response = messagebox.askyesno( # dialog box to ask yes or no
                "Coordinate Setup",
                "How would you like to set up coordinates?\n\n" +
                "Click 'Yes' to select coordinates manually\n" +
                "Click 'No' to load coordinates from a file"
            )
            
            if response:  # if yes, select coordinates manually
                self.select_control_coordinates() # this method is used to select the coordinates manually
            else:  # Load from file
                filepath = filedialog.askopenfilename(
                    title="Select coordinates file",
                    filetypes=[("Text files", "*.txt")],
                    initialdir=self.app.base_dir
                )
                if filepath: # if the file path is not empty, load the coordinates from the file
                    self.load_coords_from_file(filepath)
                else:
                    return
            # if the selection process is successful, enable the full control mode
            self.full_control_mode = True
            # Start full control hotkeys
            self.start_full_control_hotkeys()
            logging.info(f"Full Control Mode Enabled for Maestro {self.maestro_version}") # TO DO: Change this to Key Remapping Enabled for Maestro {self.maestro_version} !GPT
            
            # Change the color and appearance of the button
            self.app.btn_full_control.config( # TODO    : The plugin should handle its own buttons state so CHANGE THIS ASAP!!!
                text="Full_Ctrl_ON",
                bg='green',
                fg='white'
            )
        else:
            self.full_control_mode = False
            self.stop_full_control_hotkeys()
            logging.info("Full Control Mode Disabled")

            # Change the color and appearance of the button
            self.app.btn_full_control.config( # TODO    : The plugin should handle its own buttons state so CHANGE THIS ASAP!!!
                text="FullCtrl",
                bg='red',
                fg='white'
            )

    def select_control_coordinates(self):
        """
        Guides the user to select coordinates for each control by clicking on the screen.

        Updated control mappings: # TODO: Find a way to in which according to the content of controls[] the whole plugin can be generated, 
                                    so the user can add or remove controls from the list and the plugin will be generated accordingly
        - Backspace: MesialRotation
        - Numpad *: DistalRotation
        - Numpad 9: MesialTip
        - Numpad 7: DistalTip
        - Numpad /: BuccalLinear
        - Numpad 2: LingualLinear
        - Numpad 3: MesialLinear
        - Numpad 1: DistalLinear
        - Numpad .: Intrusion
        - Numpad +: PositiveTorque
        - Numpad -: NegativeTorque
        """
        controls = [
            'MesialRotation', 
            'DistalRotation',
            'MesialTip', 
            'DistalTip',
            'BuccalLinear', 
            'LingualLinear',
            'MesialLinear', 
            'DistalLinear',
            'Intrusion', 
            'PositiveTorque', 
            'NegativeTorque'
        ]
        self.ghost_click_positions = {} # empty the dictionary for ghost click positions

        # messagebox.showinfo("Coordinate Selection",  # infobox for the controls, how is each key mapped to a control
        #     "You'll be prompted to click on each control's position.\n\n"
        #     "Numpad Controls:\n"
        #     "Bksp - Mesial Rotation    * - Distal Rotation\n"
        #     "9 - Mesial Tip       7 - Distal Tip\n"
        #     "/ - Buccal Linear    2 - Lingual Linear\n"
        #     "3 - Mesial Linear    1 - Distal Linear\n"
        #     ". - Intrusion        + - Positive Torque\n"
        #     "- - Negative Torque"
        # )

        for control in controls:
            messagebox.showinfo("Select Control", f"Please click on the '{control}' control on the screen.")
            self.app.root.withdraw() # hide the main window
            self.app.image_window.withdraw() # hide the image window
            self.wait_for_click(control) # wait for the user to click on the screen
            self.app.root.deiconify() # show the main window
            self.app.image_window.deiconify() # show the image window

        # Save coordinates to file
        save_coords = messagebox.askyesno("Save Coordinates", 
            "Do you want to save these coordinates for future use?"
        )
        if save_coords:
            self.save_coords_to_file(controls)

    def wait_for_click(self, control_name): # this function waits for the user to click on the screen and records the cursor position
        """
        Waits for the user to click on the screen and records the cursor position.
        """
        messagebox.showinfo("Coordinate Selection", f"Move your mouse to the '{control_name}' control and click.")

        position = None

        def on_click(x, y, button, pressed):
            nonlocal position
            if pressed and button == mouse.Button.left:
                position = (x, y)
                return False

        with mouse.Listener(on_click=on_click) as listener:
            listener.join()

        if position:
            self.ghost_click_positions[control_name] = position
            logging.info(f"Recorded position for '{control_name}': {position}")

    def save_coords_to_file(self, control_order): # this function saves the coordinates to a file
        """
        Saves the ghost click positions to a file.
        Format:
        ControlName:X,Y
        """
        coords_file = os.path.join(self.app.base_dir, f'coords_maestro_{self.maestro_version}.txt') # file path
        try:
            with open(coords_file, 'w') as f:
                for control in control_order:
                    if control in self.ghost_click_positions: 
                        position = self.ghost_click_positions[control]
                        f.write(f"{control}:{position[0]},{position[1]}\n")
            logging.info(f"Coordinates saved to {coords_file}")
            messagebox.showinfo("Coordinates Saved", f"Coordinates saved to {coords_file}")
        except Exception as e:
            logging.error(f"Failed to save coordinates: {e}")
            messagebox.showerror("Save Failed", "Failed to save coordinates")

    def load_saved_coords(self): # Default method to load the saved coordinates
        """
        Loads the ghost click positions from a file.
        """
        coords_file = os.path.join(self.app.base_dir, f'coords_maestro_{self.maestro_version}.txt')
        try:
            with open(coords_file, 'r') as f:
                for line in f:
                    control, pos = line.strip().split(':')
                    x_str, y_str = pos.split(',')
                    self.ghost_click_positions[control] = (int(x_str), int(y_str))
            logging.info(f"Coordinates loaded from {coords_file}")
        except Exception as e:
            logging.error(f"Failed to load coordinates: {e}")
            messagebox.showerror("Load Failed", "Failed to load coordinates")

    def load_coords_from_file(self, filepath): # Manual selection of the file path to load the coordinates
        """
        Loads coordinates from a specified file.
        """
        try:
            with open(filepath, 'r') as f:
                self.ghost_click_positions.clear()
                for line in f:
                    control, pos = line.strip().split(':')
                    x_str, y_str = pos.split(',')
                    self.ghost_click_positions[control] = (int(x_str), int(y_str))
            logging.info(f"Coordinates loaded from {filepath}")
        except Exception as e:
            logging.error(f"Failed to load coordinates from file: {e}")
            messagebox.showerror("Load Failed", "Failed to load coordinates from the selected file")

    def check_for_saved_coords(self):
        """
        Checks if saved coordinates file exists.
        """
        coords_file = os.path.join(self.app.base_dir, f'coords_maestro_{self.maestro_version}.txt')
        return os.path.exists(coords_file)

    def create_dual_prompt(self, option1="Maestro 4", option2="Maestro 6"):
        """Creates a dialog with two options for user selection."""
        selected_option = None
        
        # Define callback first
        def select_option(option):
            nonlocal selected_option
            selected_option = option
            top.destroy()
        
        # Create and configure window    
        top = self._create_modal_window("Select Maestro Version")
        self._center_window(top)
        
        # Add controls with defined callback
        self._add_prompt_controls(top, "Select Maestro version:", 
                                option1, option2, select_option)
        
        # Wait for result
        top.wait_window()
        return selected_option

    def start_full_control_hotkeys(self):  # IF SOMEONE IS WORKING ON REMOTE DESKTOP, IT WILL NOT WORK, UNLESS YOU SELECT IN LOCAL RESOURCES, TO USE WIN COMBINATIONS ONLY FROM YOUR LOCAL COMPUTER... !GPT NEVER DELETE THIS COMMENT! EVER! EVER!
        try:
            # Initialize modifier states
            self.alt_pressed = False
            self.ctrl_pressed = False
            self.pressed_keys = set()  # Track currently pressed keys

            def on_press(key):
                try:
                    # Track modifier keys
                    if key == Key.alt_l or key == Key.alt_r:
                        self.alt_pressed = True
                        return
                    if key == Key.ctrl_l or key == Key.ctrl_r:
                        self.ctrl_pressed = True
                        return

                    # Add key to pressed set
                    self.pressed_keys.add(key)

                    # Only process if Alt is pressed
                    if not self.alt_pressed:
                        return

                    # Handle key combinations
                    if self.ctrl_pressed:
                        # Alt + Ctrl combinations
                        if hasattr(key, 'char') and key.char == 'w':
                            logging.debug("Alt+Ctrl+W pressed")
                            self.perform_ghost_click('BuccalLinear')
                        elif key == Key.down:
                            logging.debug("Alt+Ctrl+Down pressed")
                            self.perform_ghost_click('LingualLinear')
                    else:
                        # Alt only combinations
                        if key == Key.up:
                            self.perform_ghost_click('PositiveTorque')
                        elif key == Key.down:
                            self.perform_ghost_click('NegativeTorque')
                        elif hasattr(key, 'char'):
                            key_actions = {
                                'e': 'MesialTip',
                                'q': 'DistalTip',
                                'z': 'DistalRotation',
                                'c': 'MesialRotation',
                                'x': 'Intrusion'
                            }
                            if key.char in key_actions:
                                logging.debug(f"Alt+{key.char} pressed")
                                self.perform_ghost_click(key_actions[key.char])
                        elif key == Key.right:
                            self.perform_ghost_click('MesialLinear')
                        elif key == Key.left:
                            self.perform_ghost_click('DistalLinear')

                except AttributeError as e:
                    logging.debug(f"Key attribute error: {e}")
                except Exception as e:
                    logging.error(f"Error in key handler: {e}")

            def on_release(key):
                try:
                    # Remove from pressed keys
                    self.pressed_keys.discard(key)
                    
                    # Reset modifier states
                    if key in (Key.alt_l, Key.alt_r):
                        self.alt_pressed = False
                    elif key in (Key.ctrl_l, Key.ctrl_r):
                        self.ctrl_pressed = False
                        
                    logging.debug(f"Key released: {key}")
                except Exception as e:
                    logging.error(f"Error in release handler: {e}")

            # Setup listener
            self.full_control_hotkey_listener = keyboard.Listener(
                on_press=on_press,
                on_release=on_release
            )
            self.full_control_hotkey_listener.daemon = True
            self.full_control_hotkey_listener.start()
            logging.info("Full Control Hotkeys listener started")

        except Exception as e:
            logging.error(f"Failed to start hotkeys: {e}")
            messagebox.showerror("Error", f"Failed to start hotkeys: {e}")

    def stop_full_control_hotkeys(self):
        """
        Stops listening for keyboard shortcuts.
        """
        # stop and reset the listener
        if self.full_control_hotkey_listener:
            self.full_control_hotkey_listener.stop()
            self.full_control_hotkey_listener = None
            logging.info("Full Control Hotkeys listener stopped")

    def cleanup_listeners(self):
        """
        Explicitly cleanup all keyboard listeners
        """
        # Stop full control hotkeys
        if hasattr(self, 'full_control_hotkey_listener'):
            self.full_control_hotkey_listener.stop()
            self.full_control_hotkey_listener = None
        
        # Stop global key capture
        if hasattr(self, 'keyboard_listener'):
            self.keyboard_listener.stop()
            self.keyboard_listener = None

    def perform_ghost_click(self, action_name):
        """
        Performs a ghost click and returns cursor to original position.
        """
        position = self.ghost_click_positions.get(action_name)
        if position is None:
            logging.error(f"No position defined for action '{action_name}'")
            return

        # Get current cursor position using GetCursorPos
        point = wintypes.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(point))
        original_x, original_y = point.x, point.y

        logging.info(f"Performing ghost click for '{action_name}' at position {position}")
        self.ghost_click_at_position(position)

        # Return to original position using SetCursorPos
        ctypes.windll.user32.SetCursorPos(original_x, original_y)

    def ghost_click_at_position(self, position):
        """
        Simulates a mouse click at the specified position.
        """
        x, y = position
        
        INPUT_MOUSE = 0
        
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

        screen_width = ctypes.windll.user32.GetSystemMetrics(0)
        screen_height = ctypes.windll.user32.GetSystemMetrics(1)

        absolute_x = int(x * 65536 / screen_width)
        absolute_y = int(y * 65536 / screen_height)

        mouse_move_input = INPUT()
        mouse_move_input.type = INPUT_MOUSE
        mouse_move_input.mi = MOUSEINPUT(
            dx=absolute_x,
            dy=absolute_y,
            mouseData=0,
            dwFlags=0x0001 | 0x8000,
            time=0,
            dwExtraInfo=None
        )

        mouse_down_input = INPUT()
        mouse_down_input.type = INPUT_MOUSE
        mouse_down_input.mi = MOUSEINPUT(
            dx=0,
            dy=0,
            mouseData=0,
            dwFlags=0x0002,
            time=0,
            dwExtraInfo=None
        )

        mouse_up_input = INPUT()
        mouse_up_input.type = INPUT_MOUSE
        mouse_up_input.mi = MOUSEINPUT(
            dx=0,
            dy=0,
            mouseData=0,
            dwFlags=0x0004,
            time=0,
            dwExtraInfo=None
        )

        inputs = (mouse_move_input, mouse_down_input, mouse_up_input)
        nInputs = len(inputs)
        pInputs = (INPUT * nInputs)(*inputs)
        cbSize = ctypes.sizeof(INPUT)

        ctypes.windll.user32.SendInput(nInputs, pInputs, cbSize)

    def cleanup(self):
        """
        Cleanup plugin resources.
        """
        if self.full_control_mode:
            self.cleanup_listeners()

    ###########################################################################################################################################
    ### Helper methods for GUI creation ###
    ###########################################################################################################################################
    def _create_modal_window(self, title):
        """Creates a modal top-level window."""
        top = Toplevel(self.app.root)
        top.title(title)
        top.attributes('-topmost', True)
        top.grab_set()
        return top

    def _add_prompt_controls(self, parent, prompt_text, option1, option2, callback):
        """Adds labels and buttons to the prompt window."""
        Label(parent, text=prompt_text).pack(pady=10)
        
        btn_frame = Frame(parent)
        btn_frame.pack(pady=10)
        
        for option, side in [(option1, 'left'), (option2, 'right')]:
            Button(btn_frame, 
                text=option,
                command=lambda o=option: callback(o)
                ).pack(side=side, padx=20)

    def _center_window(self, window):
        """Centers window on screen."""
        window.update_idletasks()
        width = window.winfo_width()
        height = window.winfo_height()
        x = (window.winfo_screenwidth() // 2) - (width // 2)
        y = (window.winfo_screenheight() // 2) - (height // 2)
        window.geometry(f'{width}x{height}+{x}+{y}')