import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from pynput import keyboard

# Create the main window
root = tk.Tk()
root.title("Key Logger")
root.configure(bg='#1C1B1B')  # Set window background color

# Create a ScrolledText widget to display logs
text_box = ScrolledText(root, wrap='word', width=50, height=20, bg='#1C1B1B', fg='#FFFFFF')
text_box.pack(fill='both', expand=True)

# Make the text box read-only
text_box.configure(state='disabled')

def on_press(key):
    try:
        # Try to get the key character or name
        key_name = key.char if hasattr(key, 'char') and key.char is not None else key.name
    except AttributeError:
        key_name = str(key)

    log = f"Key pressed: {key_name}\n---\n"

    # Enable text box, insert log, disable text box
    text_box.configure(state='normal')
    text_box.insert('end', log)
    text_box.see('end')  # Scroll to the end
    text_box.configure(state='disabled')

    if key == keyboard.Key.esc:
        # Stop the listener and close the GUI
        listener.stop()
        root.destroy()

# Start listening to keyboard events
listener = keyboard.Listener(on_press=on_press)
listener.start()

# Start the Tkinter event loop
root.mainloop()