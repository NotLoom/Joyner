import sounddevice as sd
import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox
from collections import deque
import threading
import webbrowser
import json
import os


class AudioMixerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Joyner")

        # Audio settings
        self.vb_input_device = None
        self.mic_input_device = None
        self.output_device = None
        self.stream = None
        self.mic_gain = 1.0
        self.vb_gain = 1.0
        self.devices = sd.query_devices()

        # Audio buffers and locks
        self.vb_buffer = deque(maxlen=10)
        self.mic_buffer = deque(maxlen=10)
        self.buffer_lock = threading.Lock()

        # Stream settings
        self.samplerate = 48000
        self.blocksize = 1024

        # Mute states
        self.mic_muted = False
        self.vb_muted = False

        # Settings file
        self.settings_file = "settings.json"

        # Load last settings
        self.load_settings()

        # UI Setup
        self.create_widgets()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Print devices for debugging
        print("Available Devices:")
        for i, dev in enumerate(self.devices):
            print(f"{i}: {dev['name']} (Inputs: {dev['max_input_channels']}, Outputs: {dev['max_output_channels']})")

    def create_widgets(self):
        # Device selection
        ttk.Label(self.root, text="VB-Cable Output:").grid(row=0, column=0, padx=10, pady=5)
        self.vb_input_combo = ttk.Combobox(self.root, values=self.get_input_devices(), width=40)
        self.vb_input_combo.grid(row=0, column=1, padx=10, pady=5)
        if hasattr(self, 'last_vb_input'):
            self.vb_input_combo.set(self.last_vb_input)

        ttk.Label(self.root, text="Microphone Input:").grid(row=1, column=0, padx=10, pady=5)
        self.mic_input_combo = ttk.Combobox(self.root, values=self.get_input_devices(), width=40)
        self.mic_input_combo.grid(row=1, column=1, padx=10, pady=5)
        if hasattr(self, 'last_mic_input'):
            self.mic_input_combo.set(self.last_mic_input)

        ttk.Label(self.root, text="Input Device:").grid(row=2, column=0, padx=10, pady=5)
        self.output_combo = ttk.Combobox(self.root, values=self.get_output_devices(), width=40)
        self.output_combo.grid(row=2, column=1, padx=10, pady=5)
        if hasattr(self, 'last_output'):
            self.output_combo.set(self.last_output)

        # Mute checkboxes
        self.mic_mute_var = tk.BooleanVar(value=self.last_mic_muted if hasattr(self, 'last_mic_muted') else False)
        self.mic_mute_check = ttk.Checkbutton(self.root, text="Mute", variable=self.mic_mute_var, command=self.toggle_mic_mute)
        self.mic_mute_check.grid(row=1, column=2, padx=10, pady=5)

        self.vb_mute_var = tk.BooleanVar(value=self.last_vb_muted if hasattr(self, 'last_vb_muted') else False)
        self.vb_mute_check = ttk.Checkbutton(self.root, text="Mute", variable=self.vb_mute_var, command=self.toggle_vb_mute)
        self.vb_mute_check.grid(row=0, column=2, padx=10, pady=5)

        # Initialize labels before sliders
        self.mic_value_label = ttk.Label(self.root, text="1.00")
        self.mic_value_label.grid(row=3, column=2, padx=5, pady=5)

        self.vb_value_label = ttk.Label(self.root, text="1.00")
        self.vb_value_label.grid(row=4, column=2, padx=5, pady=5)

        # Gain controls
        ttk.Label(self.root, text="Microphone Gain (150%):").grid(row=3, column=0, padx=10, pady=5)
        self.mic_slider = ttk.Scale(self.root, from_=0, to=1.5, command=lambda v: self.update_gain('mic', float(v)))
        self.mic_slider.set(self.last_mic_gain if hasattr(self, 'last_mic_gain') else 1.0)
        self.mic_slider.grid(row=3, column=1, padx=10, pady=5)

        ttk.Label(self.root, text="VB-Cable Gain (300%):").grid(row=4, column=0, padx=10, pady=5)
        self.vb_slider = ttk.Scale(self.root, from_=0, to=3.0, command=lambda v: self.update_gain('vb', float(v)))
        self.vb_slider.set(self.last_vb_gain if hasattr(self, 'last_vb_gain') else 1.0)
        self.vb_slider.grid(row=4, column=1, padx=10, pady=5)

        # Control buttons
        self.start_btn = ttk.Button(self.root, text="Start", command=self.start_stream)
        self.start_btn.grid(row=5, column=0, padx=10, pady=10)

        self.stop_btn = ttk.Button(self.root, text="Stop", command=self.stop_stream, state=tk.DISABLED)
        self.stop_btn.grid(row=5, column=1, padx=10, pady=10)

        # Made by Loom label
        self.made_by_label = ttk.Label(
            self.root,
            text="Made by Loom",
            foreground="blue",
            cursor="hand2"
        )
        self.made_by_label.grid(row=5, column=2, padx=10, pady=10, sticky="e")  # Aligned with Start/Stop buttons
        self.made_by_label.bind("<Button-1>", lambda e: webbrowser.open("https://discord.gg/3QXEmdRktR"))

    def get_input_devices(self):
        return [d['name'] for d in self.devices if d['max_input_channels'] > 0]

    def get_output_devices(self):
        return [d['name'] for d in self.devices if d['max_output_channels'] > 0]

    def update_gain(self, source, value):
        if source == 'mic':
            self.mic_gain = value
            if hasattr(self, 'mic_value_label'):  # Check if label exists
                self.mic_value_label.config(text=f"{value:.2f}")
        else:
            self.vb_gain = value
            if hasattr(self, 'vb_value_label'):  # Check if label exists
                self.vb_value_label.config(text=f"{value:.2f}")

    def toggle_mic_mute(self):
        self.mic_muted = self.mic_mute_var.get()

    def toggle_vb_mute(self):
        self.vb_muted = self.vb_mute_var.get()

    def find_device_index(self, name, is_input=True):
        for i, dev in enumerate(self.devices):
            if name.lower() in dev['name'].lower():
                if is_input and dev['max_input_channels'] > 0:
                    return i
                elif not is_input and dev['max_output_channels'] > 0:
                    return i
        return None

    def vb_input_callback(self, indata, frames, time, status):
        """Callback for VB-Cable input stream"""
        with self.buffer_lock:
            self.vb_buffer.append(indata.copy())

    def mic_input_callback(self, indata, frames, time, status):
        """Callback for microphone input stream"""
        with self.buffer_lock:
            self.mic_buffer.append(indata.copy())

    def output_callback(self, outdata, frames, time, status):
        """Callback for output stream"""
        try:
            with self.buffer_lock:
                # Get the oldest available data from both buffers
                vb_data = self.vb_buffer.popleft() if self.vb_buffer else np.zeros((self.blocksize, 1))
                mic_data = self.mic_buffer.popleft() if self.mic_buffer else np.zeros((self.blocksize, 1))

                # Ensure both inputs are the correct size
                if len(vb_data) != self.blocksize:
                    vb_data = np.zeros((self.blocksize, 1))
                if len(mic_data) != self.blocksize:
                    mic_data = np.zeros((self.blocksize, 1))

            # Process and mix audio
            if self.mic_muted:
                mic_data = np.zeros_like(mic_data)
            if self.vb_muted:
                vb_data = np.zeros_like(vb_data)
            mixed = (vb_data * self.vb_gain) + (mic_data * self.mic_gain)
            outdata[:] = np.clip(mixed, -1.0, 1.0)
        except Exception as e:
            print("Output error:", str(e))

    def start_stream(self):
        vb_input_name = self.vb_input_combo.get()
        mic_input_name = self.mic_input_combo.get()
        output_name = self.output_combo.get()

        # Validate selections
        if not vb_input_name or not mic_input_name or not output_name:
            messagebox.showerror("Error", "Please select all devices!")
            return

        # Find device indices
        self.vb_input_device = self.find_device_index(vb_input_name, is_input=True)
        self.mic_input_device = self.find_device_index(mic_input_name, is_input=True)
        self.output_device = self.find_device_index(output_name, is_input=False)

        if None in [self.vb_input_device, self.mic_input_device, self.output_device]:
            messagebox.showerror("Error", "One or more devices not found!")
            return

        try:
            # Create separate input streams with fixed blocksize
            self.vb_stream = sd.InputStream(
                device=self.vb_input_device,
                channels=1,
                samplerate=self.samplerate,
                blocksize=self.blocksize,
                callback=self.vb_input_callback
            )

            self.mic_stream = sd.InputStream(
                device=self.mic_input_device,
                channels=1,
                samplerate=self.samplerate,
                blocksize=self.blocksize,
                callback=self.mic_input_callback
            )

            # Output stream
            self.out_stream = sd.OutputStream(
                device=self.output_device,
                channels=1,
                samplerate=self.samplerate,
                blocksize=self.blocksize,
                callback=self.output_callback
            )

            # Start streams
            self.vb_stream.start()
            self.mic_stream.start()
            self.out_stream.start()

            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)

        except Exception as e:
            messagebox.showerror("Error", f"Stream error: {str(e)}")

    def stop_stream(self):
        if hasattr(self, 'vb_stream'):
            self.vb_stream.stop()
            self.vb_stream.close()
        if hasattr(self, 'mic_stream'):
            self.mic_stream.stop()
            self.mic_stream.close()
        if hasattr(self, 'out_stream'):
            self.out_stream.stop()
            self.out_stream.close()

        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

    def load_settings(self):
        """Load settings from a JSON file"""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    self.last_vb_input = settings.get('vb_input', '')
                    self.last_mic_input = settings.get('mic_input', '')
                    self.last_output = settings.get('output', '')
                    self.last_mic_gain = settings.get('mic_gain', 1.0)
                    self.last_vb_gain = settings.get('vb_gain', 1.0)
                    self.last_mic_muted = settings.get('mic_muted', False)
                    self.last_vb_muted = settings.get('vb_muted', False)
            except Exception as e:
                print("Error loading settings:", str(e))

    def save_settings(self):
        """Save settings to a JSON file"""
        settings = {
            'vb_input': self.vb_input_combo.get(),
            'mic_input': self.mic_input_combo.get(),
            'output': self.output_combo.get(),
            'mic_gain': self.mic_gain,
            'vb_gain': self.vb_gain,
            'mic_muted': self.mic_muted,
            'vb_muted': self.vb_muted
        }
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f)
        except Exception as e:
            print("Error saving settings:", str(e))

    def on_close(self):
        """Save settings and clean up on window close"""
        self.save_settings()
        self.stop_stream()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = AudioMixerApp(root)
    root.mainloop()