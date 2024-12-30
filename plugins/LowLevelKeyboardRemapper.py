import win32con
import ctypes
from ctypes import wintypes, POINTER, c_void_p, c_long, c_longlong, c_ulong, c_ulonglong
import atexit
import os
import sys
import logging
import orthy

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.OrthyPlugin_Interface import OrthyPlugin

# Define ULONG_PTR if not available
if not hasattr(wintypes, 'ULONG_PTR'):
    if ctypes.sizeof(c_void_p) == ctypes.sizeof(c_ulonglong):
        wintypes.ULONG_PTR = c_ulonglong
    else:
        wintypes.ULONG_PTR = c_ulong

# Define LRESULT if not available
if not hasattr(wintypes, 'LRESULT'):
    if ctypes.sizeof(c_void_p) == ctypes.sizeof(c_longlong):
        wintypes.LRESULT = c_longlong
    else:
        wintypes.LRESULT = c_long

# Define HHOOK, HINSTANCE, and HMODULE if not available
if not hasattr(wintypes, 'HHOOK'):
    wintypes.HHOOK = wintypes.HANDLE
if not hasattr(wintypes, 'HINSTANCE'):
    wintypes.HINSTANCE = wintypes.HANDLE
if not hasattr(wintypes, 'HMODULE'):
    wintypes.HMODULE = wintypes.HANDLE

class LowLevelKeyboardRemapper(OrthyPlugin):
    def __init__(self):
        self.app = None
        self.active_mode = False
        self.hook = None
        self.registered = False
        # Virtual key codes for WASD and arrows
        self.VK_W = 0x57
        self.VK_A = 0x41
        self.VK_S = 0x53
        self.VK_D = 0x44

        self.key_map = {
            self.VK_W: win32con.VK_UP,
            self.VK_S: win32con.VK_DOWN,
            self.VK_A: win32con.VK_LEFT,
            self.VK_D: win32con.VK_RIGHT
        }

        self.hooked_keys = set(self.key_map.keys())
        atexit.register(self.cleanup)

    def get_name(self):
        return "LowLevelKeyboardRemapper"

    def get_btn_configs(self):
        return [{
            'text': 'WASD Remap',
            'command': self.toggle_remap,
            'grid': {'row': 20, 'column': 0, 'columnspan': 2, 'pady': 2, 'sticky': 'ew'},
            'width': 10,
            'variable_name': 'btn_toggle_low_level_remap',
            'bg': 'red',
            'fg': 'white'
        }]

    def toggle_remap(self):
        self.set_active_mode(not self.active_mode)
            
    def set_active_mode(self, state: bool):
        """
        Merge activate/deactivate logic into one method.
        """
        if not self.registered:
            self.app.register_plugin_sentinels(self.get_name(),self.active_mode)
            self.active_mode = state
            self.registered = True
        if self.registered:
            self.active_mode = state
            if state:
                self.update_button()
                logging.info("[LLRemapper] Activated")
            else:
                self.update_button()
                logging.info("[LLRemapper] Deactivated")

    def initialize(self, app_instance):
        self.app = app_instance
        self.start_hook()

    def start_hook(self):
        """
        Installs a low-level keyboard hook if not already present.
        """
        if self.hook:
            return

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        HOOKPROC = ctypes.WINFUNCTYPE(wintypes.LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
        self.pointer = HOOKPROC(self.low_level_handler)

        user32.SetWindowsHookExA.argtypes = [wintypes.INT, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]
        user32.SetWindowsHookExA.restype = wintypes.HHOOK

        user32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
        user32.CallNextHookEx.restype = wintypes.LRESULT

        user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
        user32.UnhookWindowsHookEx.restype = wintypes.BOOL

        kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
        kernel32.GetModuleHandleW.restype = wintypes.HINSTANCE

        hMod = kernel32.GetModuleHandleW(None)

        self.hook = user32.SetWindowsHookExA(
            win32con.WH_KEYBOARD_LL,
            self.pointer,
            hMod,
            0
        )

        if self.hook:
            logging.info("[LLRemapper] Keyboard hook installed")
        else:
            logging.error("[LLRemapper] Failed to install keyboard hook")

    def low_level_handler(self, nCode, wParam, lParam):
        """
        The low-level keyboard callback that intercepts key presses.
        """
        if not self.active_mode:
            return ctypes.windll.user32.CallNextHookEx(self.hook, nCode, wParam, lParam)

        try:
            if nCode == win32con.HC_ACTION:
                kb_struct = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                vk_code = kb_struct.vkCode

                if vk_code in self.hooked_keys:
                    if wParam in (win32con.WM_KEYDOWN, win32con.WM_SYSKEYDOWN):
                        mapped_key = self.key_map[vk_code]
                        ctypes.windll.user32.keybd_event(mapped_key, 0, 0, 0)
                    elif wParam in (win32con.WM_KEYUP, win32con.WM_SYSKEYUP):
                        mapped_key = self.key_map[vk_code]
                        ctypes.windll.user32.keybd_event(mapped_key, 0, win32con.KEYEVENTF_KEYUP, 0)

                    # Return -1 to block the original key
                    return -1

        except Exception as e:
            logging.error(f"[LLRemapper] Error in hook: {e}")

        
        return ctypes.windll.user32.CallNextHookEx(self.hook, nCode, wParam, lParam)

    def cleanup(self):
        """
        Uninstalls the keyboard hook if present.
        """
        if self.hook:
            ctypes.windll.user32.UnhookWindowsHookEx(self.hook)
            self.hook = None
            logging.info("[LLRemapper] Keyboard hook removed")

    ########################################################
    # Helper function to create the plugin's button configs
    ########################################################
    def update_button(self):
        self.app.update_plugin_sentinels(self.get_name(),self.active_mode)
        self.app.update_plugin_buttons(self.get_name())

# Required structure for low-level keyboard hook
class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode",   wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags",    wintypes.DWORD),
        ("time",     wintypes.DWORD),
        ("dwExtraInfo", wintypes.ULONG_PTR)
    ]
