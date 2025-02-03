import sounddevice as sd
import numpy as np
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import messagebox
import webbrowser
import json
import os
from collections import deque
import threading

class AudioMixerApp:
    def __init__(self, root, style):
        self.root = root
        self.style = style
        self.root.title("Joyner Audio Mixer")
        self.root.geometry("500x380")
        self.root.resizable(False, False)

        # Audio settings
        self.vb_input_device = None
        self.mic_input_device = None
        self.output_device = None
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

        # Build the UI
        self.create_widgets()

        # Configure window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Debug: Print available devices
        print("Available Devices:")
        for i, dev in enumerate(self.devices):
            print(f"{i}: {dev['name']} (Inputs: {dev['max_input_channels']}, Outputs: {dev['max_output_channels']})")

    def create_widgets(self):
        # Main container with padding; using less vertical padding for compactness
        container = ttk.Frame(self.root, padding=(15, 10))
        container.pack(expand=YES, fill=BOTH)

        # Top bar with header and Dark Mode toggle
        top_bar = ttk.Frame(container)
        top_bar.pack(fill=X)
        header = ttk.Label(top_bar, text="Joyner Audio Mixer", font=("Helvetica", 18, "bold"))
        header.pack(side=LEFT, padx=(0, 10))

        self.dark_mode_var = ttk.BooleanVar(value=self.style.theme.name in ["cyborg", "superhero", "darkly"])
        dark_mode_switch = ttk.Checkbutton(top_bar, text="Dark Mode", variable=self.dark_mode_var, command=self.toggle_dark_mode, bootstyle="round-toggle")
        dark_mode_switch.pack(side=RIGHT)

        # Device selection section in a labeled frame
        device_frame = ttk.Labelframe(container, text="Device Selection", bootstyle="info", padding=10)
        device_frame.pack(fill=X, padx=5, pady=5)

        # Row 1: VB-Cable Input + Mute button
        row1 = ttk.Frame(device_frame)
        row1.pack(fill=X, pady=2)
        ttk.Label(row1, text="VB-Cable Output:", width=20, anchor="w").pack(side=LEFT, padx=(0, 5))
        self.vb_input_combo = ttk.Combobox(row1, values=self.get_input_devices(), state="readonly", width=35)
        self.vb_input_combo.pack(side=LEFT, padx=(0, 10))
        if hasattr(self, 'last_vb_input'):
            self.vb_input_combo.set(self.last_vb_input)
        self.vb_mute_var = ttk.BooleanVar(value=self.last_vb_muted if hasattr(self, 'last_vb_muted') else False)
        self.vb_mute_check = ttk.Checkbutton(row1, text="Mute", variable=self.vb_mute_var, command=self.toggle_vb_mute)
        self.vb_mute_check.pack(side=LEFT)

        # Row 2: Microphone Input + Mute button
        row2 = ttk.Frame(device_frame)
        row2.pack(fill=X, pady=2)
        ttk.Label(row2, text="Microphone Input:", width=20, anchor="w").pack(side=LEFT, padx=(0, 5))
        self.mic_input_combo = ttk.Combobox(row2, values=self.get_input_devices(), state="readonly", width=35)
        self.mic_input_combo.pack(side=LEFT, padx=(0, 10))
        if hasattr(self, 'last_mic_input'):
            self.mic_input_combo.set(self.last_mic_input)
        self.mic_mute_var = ttk.BooleanVar(value=self.last_mic_muted if hasattr(self, 'last_mic_muted') else False)
        self.mic_mute_check = ttk.Checkbutton(row2, text="Mute", variable=self.mic_mute_var, command=self.toggle_mic_mute)
        self.mic_mute_check.pack(side=LEFT)

        # Row 3: Output device selection
        row3 = ttk.Frame(device_frame)
        row3.pack(fill=X, pady=2)
        ttk.Label(row3, text="Output Device:", width=20, anchor="w").pack(side=LEFT, padx=(0, 5))
        self.output_combo = ttk.Combobox(row3, values=self.get_output_devices(), state="readonly", width=35)
        self.output_combo.pack(side=LEFT, padx=(0, 10))
        if hasattr(self, 'last_output'):
            self.output_combo.set(self.last_output)

        # Gain controls section in a labeled frame
        gain_frame = ttk.Labelframe(container, text="Gain Controls", bootstyle="success", padding=10)
        gain_frame.pack(fill=X, padx=5, pady=5)

        # Microphone Gain
        gain_mic_frame = ttk.Frame(gain_frame)
        gain_mic_frame.pack(fill=X, pady=2)
        ttk.Label(gain_mic_frame, text="Microphone Gain (up to 150%):", width=25, anchor="w").pack(side=LEFT, padx=(0, 5))
        self.mic_slider = ttk.Scale(gain_mic_frame, from_=0, to=1.5, command=lambda v: self.update_gain('mic', float(v)), bootstyle="primary")
        self.mic_slider.set(self.last_mic_gain if hasattr(self, 'last_mic_gain') else 1.0)
        self.mic_slider.pack(side=LEFT, fill=X, expand=YES, padx=(0, 10))
        self.mic_value_label = ttk.Label(gain_mic_frame, text=f"{self.mic_slider.get():.2f}", width=5)
        self.mic_value_label.pack(side=LEFT)

        # VB-Cable Gain
        gain_vb_frame = ttk.Frame(gain_frame)
        gain_vb_frame.pack(fill=X, pady=2)
        ttk.Label(gain_vb_frame, text="VB-Cable Gain (up to 300%):", width=25, anchor="w").pack(side=LEFT, padx=(0, 5))
        self.vb_slider = ttk.Scale(gain_vb_frame, from_=0, to=3.0, command=lambda v: self.update_gain('vb', float(v)), bootstyle="primary")
        self.vb_slider.set(self.last_vb_gain if hasattr(self, 'last_vb_gain') else 1.0)
        self.vb_slider.pack(side=LEFT, fill=X, expand=YES, padx=(0, 10))
        self.vb_value_label = ttk.Label(gain_vb_frame, text=f"{self.vb_slider.get():.2f}", width=5)
        self.vb_value_label.pack(side=LEFT)

        # Control buttons section (make buttons longer for clear text)
        control_frame = ttk.Frame(container)
        control_frame.pack(fill=X, padx=5, pady=10)
        self.start_btn = ttk.Button(control_frame, text="Start Stream", command=self.start_stream, bootstyle=SUCCESS, width=20)
        self.start_btn.pack(side=LEFT, expand=YES, fill=X, padx=5)
        self.stop_btn = ttk.Button(control_frame, text="Stop Stream", command=self.stop_stream, state=DISABLED, bootstyle=DANGER, width=20)
        self.stop_btn.pack(side=LEFT, expand=YES, fill=X, padx=5)

        # Footer with clickable link
        footer = ttk.Frame(container)
        footer.pack(fill=X, pady=(5, 0))
        link = ttk.Label(footer, text="Made by Loom", foreground="blue", cursor="hand2", font=("Helvetica", 9, "underline"))
        link.pack(side=RIGHT)
        link.bind("<Button-1>", lambda e: webbrowser.open("https://discord.gg/3QXEmdRktR"))

    def toggle_dark_mode(self):
        """Toggle between light (flatly) and dark (cyborg) themes."""
        if self.dark_mode_var.get():
            self.style.theme_use("cyborg")
        else:
            self.style.theme_use("flatly")

    def get_input_devices(self):
        return [d['name'] for d in self.devices if d['max_input_channels'] > 0]

    def get_output_devices(self):
        return [d['name'] for d in self.devices if d['max_output_channels'] > 0]

    def update_gain(self, source, value):
        if source == 'mic':
            self.mic_gain = value
            self.mic_value_label.config(text=f"{value:.2f}")
        else:
            self.vb_gain = value
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
        with self.buffer_lock:
            self.vb_buffer.append(indata.copy())

    def mic_input_callback(self, indata, frames, time, status):
        with self.buffer_lock:
            self.mic_buffer.append(indata.copy())

    def output_callback(self, outdata, frames, time, status):
        try:
            with self.buffer_lock:
                vb_data = self.vb_buffer.popleft() if self.vb_buffer else np.zeros((self.blocksize, 1))
                mic_data = self.mic_buffer.popleft() if self.mic_buffer else np.zeros((self.blocksize, 1))
                # Validate block sizes
                if len(vb_data) != self.blocksize:
                    vb_data = np.zeros((self.blocksize, 1))
                if len(mic_data) != self.blocksize:
                    mic_data = np.zeros((self.blocksize, 1))
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

        if not vb_input_name or not mic_input_name or not output_name:
            messagebox.showerror("Error", "Please select all devices!")
            return

        self.vb_input_device = self.find_device_index(vb_input_name, is_input=True)
        self.mic_input_device = self.find_device_index(mic_input_name, is_input=True)
        self.output_device = self.find_device_index(output_name, is_input=False)

        if None in [self.vb_input_device, self.mic_input_device, self.output_device]:
            messagebox.showerror("Error", "One or more devices not found!")
            return

        try:
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
            self.out_stream = sd.OutputStream(
                device=self.output_device,
                channels=1,
                samplerate=self.samplerate,
                blocksize=self.blocksize,
                callback=self.output_callback
            )

            self.vb_stream.start()
            self.mic_stream.start()
            self.out_stream.start()

            self.start_btn.config(state=DISABLED)
            self.stop_btn.config(state=NORMAL)
        except Exception as e:
            messagebox.showerror("Stream Error", f"Could not start stream:\n{str(e)}")

    def stop_stream(self):
        for stream in ['vb_stream', 'mic_stream', 'out_stream']:
            if hasattr(self, stream):
                getattr(self, stream).stop()
                getattr(self, stream).close()
        self.start_btn.config(state=NORMAL)
        self.stop_btn.config(state=DISABLED)

    def load_settings(self):
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
        self.save_settings()
        self.stop_stream()
        self.root.destroy()


if __name__ == "__main__":
    # Start with light theme ("flatly"); dark mode toggle can switch to "cyborg"
    app_style = ttk.Style("flatly")
    root = app_style.master
    app = AudioMixerApp(root, app_style)
    root.mainloop()
