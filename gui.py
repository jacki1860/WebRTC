import customtkinter as ctk
import asyncio
import threading
import socket
import logging
import sys
from server import WebRTCServer, get_audio_devices

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class TextHandler(logging.Handler):
    def __init__(self, text_widget):
        logging.Handler.__init__(self)
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        def append():
            self.text_widget.configure(state=("normal"))
            self.text_widget.insert("end", msg + "\n")
            self.text_widget.see("end")
            self.text_widget.configure(state=("disabled"))
        self.text_widget.after(0, append)

class ServerControlFrame(ctk.CTkFrame):
    def __init__(self, master, title, default_port, **kwargs):
        super().__init__(master, **kwargs)
        self.server_title = title
        self.default_port = default_port
        
        # State
        self.server_thread = None
        self.server_loop = None
        self.server_instance = None
        self.is_running = False

        self.setup_ui()

    def setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        
        # Title
        self.label = ctk.CTkLabel(self, text=self.server_title, font=ctk.CTkFont(size=18, weight="bold"))
        self.label.grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 5))
        
        # IP info
        local_ip = self.get_local_ip()
        self.ip_label = ctk.CTkLabel(self, text=f"IP: {local_ip}")
        self.ip_label.grid(row=1, column=0, columnspan=2, padx=10, pady=(0, 10))

        # Port
        ctk.CTkLabel(self, text="Port:").grid(row=2, column=0, padx=10, pady=10, sticky="e")
        self.port_entry = ctk.CTkEntry(self, width=120)
        self.port_entry.insert(0, str(self.default_port))
        self.port_entry.grid(row=2, column=1, padx=10, pady=10, sticky="w")

        # Device Selection
        ctk.CTkLabel(self, text="Input:").grid(row=3, column=0, padx=10, pady=10, sticky="e")
        self.devices = get_audio_devices()
        self.device_names = [f"{i}: {name}" for i, name in self.devices]
        
        self.device_menu = ctk.CTkOptionMenu(self, values=self.device_names, width=200)
        if self.device_names:
            self.device_menu.set(self.device_names[0])
        else:
            self.device_menu.set("No Microphone Found")
            self.device_menu.configure(state="disabled")
        
        self.device_menu.grid(row=3, column=1, padx=10, pady=10, sticky="ew")

        # Start Button
        self.start_button = ctk.CTkButton(self, text="Start Server", command=self.toggle_server)
        self.start_button.grid(row=4, column=0, columnspan=2, padx=20, pady=20)

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    def toggle_server(self):
        if not self.is_running:
            self.start_server()
        else:
            self.stop_server()

    def start_server(self):
        port_str = self.port_entry.get()
        try:
            port = int(port_str)
        except ValueError:
            logging.error(f"[{self.server_title}] Invalid port")
            return

        device_str = self.device_menu.get()
        device_index = None
        if device_str != "No Microphone Found":
            try:
                device_index = int(device_str.split(":")[0])
            except:
                pass
        
        self.is_running = True
        self.start_button.configure(text="Stop Server", fg_color="red")
        self.port_entry.configure(state="disabled")
        self.device_menu.configure(state="disabled")
        
        logging.info(f"[{self.server_title}] Starting on port {port}...")

        # Start server thread
        self.server_thread = threading.Thread(target=self.run_server_thread, args=(port, device_index))
        self.server_thread.start()

    def stop_server(self):
        if self.server_loop and self.server_instance:
            async def shutdown():
                await self.server_instance.stop()
                self.server_loop.stop()

            asyncio.run_coroutine_threadsafe(shutdown(), self.server_loop)
        
        self.is_running = False
        self.start_button.configure(text="Start Server", fg_color=["#3B8ED0", "#1F6AA5"])
        self.port_entry.configure(state="normal")
        self.device_menu.configure(state="normal")
        logging.info(f"[{self.server_title}] Stopped.")

    def run_server_thread(self, port, device_index):
        asyncio.set_event_loop(asyncio.new_event_loop())
        self.server_loop = asyncio.get_event_loop()
        self.server_instance = WebRTCServer(port=port, device_index=device_index)
        
        try:
            self.server_loop.create_task(self.server_instance.start())
            self.server_loop.run_forever()
        except Exception as e:
            logging.error(f"[{self.server_title}] Server crashed: {e}")
        finally:
            if self.server_loop.is_running():
                self.server_loop.close()

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("WebRTC Dual Audio Server")
        self.geometry("900x600")

        # Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Main Title
        self.label = ctk.CTkLabel(self, text="WebRTC Multi-Stream Control", font=ctk.CTkFont(size=24, weight="bold"))
        self.label.grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 10))

        # Server 1 Frame
        self.server1 = ServerControlFrame(self, title="Server A", default_port=8880)
        self.server1.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        # Server 2 Frame
        self.server2 = ServerControlFrame(self, title="Server B", default_port=8881)
        self.server2.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")

        # Log
        self.log_textbox = ctk.CTkTextbox(self, height=200)
        self.log_textbox.grid(row=2, column=0, columnspan=2, padx=20, pady=10, sticky="nsew")
        self.log_textbox.configure(state="disabled")

        # Setup Logging to GUI
        self.setup_logging()
        
        # Override close protocol to stop threads
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_logging(self):
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        
        handler = TextHandler(self.log_textbox)
        formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%H:%M:%S')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # Add File Handler for persistence
        file_handler = logging.FileHandler("webrtc_server.log", mode='w')
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)

    def on_closing(self):
        if self.server1.is_running:
            self.server1.stop_server()
        if self.server2.is_running:
            self.server2.stop_server()
        self.destroy()
        sys.exit(0)

if __name__ == "__main__":
    app = App()
    app.mainloop()
