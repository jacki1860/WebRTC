import customtkinter as ctk
import asyncio
import threading
import socket
import logging
import sys
import queue
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

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("WebRTC Audio Server")
        self.geometry("600x800")

        # Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # Title
        self.label = ctk.CTkLabel(self, text="WebRTC Audio Streamer", font=ctk.CTkFont(size=20, weight="bold"))
        self.label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # Controls Frame
        self.controls_frame = ctk.CTkFrame(self)
        self.controls_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        
        # IP Address
        local_ip = self.get_local_ip()
        self.ip_label = ctk.CTkLabel(self.controls_frame, text=f"Local IP: {local_ip}")
        self.ip_label.grid(row=0, column=0, padx=10, pady=10)

        # Port
        self.port_entry = ctk.CTkEntry(self.controls_frame, placeholder_text="Port (8080)")
        self.port_entry.insert(0, "8080")
        self.port_entry.grid(row=0, column=1, padx=10, pady=10)

        # Device Selection
        self.devices = get_audio_devices()
        self.device_names = [f"{i}: {name}" for i, name in self.devices]
        
        self.device_menu = ctk.CTkOptionMenu(self.controls_frame, values=self.device_names)
        if self.device_names:
            self.device_menu.set(self.device_names[0])
        else:
            self.device_menu.set("No Microphone Found")
            self.device_menu.configure(state="disabled")
        
        self.device_menu.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        # Start Button
        self.start_button = ctk.CTkButton(self, text="Start Server", command=self.toggle_server)
        self.start_button.grid(row=2, column=0, padx=20, pady=10)

        # Log
        self.log_textbox = ctk.CTkTextbox(self, width=500, height=200)
        self.log_textbox.grid(row=3, column=0, padx=20, pady=10, sticky="nsew")
        self.log_textbox.configure(state="disabled")

        # Setup Logging
        self.setup_logging()

        # Server State
        self.server_thread = None
        self.server_loop = None
        self.server_instance = None
        self.is_running = False

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    def setup_logging(self):
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        
        handler = TextHandler(self.log_textbox)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

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
            logging.error("Invalid port")
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

    def run_server_thread(self, port, device_index):
        asyncio.set_event_loop(asyncio.new_event_loop())
        self.server_loop = asyncio.get_event_loop()
        self.server_instance = WebRTCServer(port=port, device_index=device_index)
        
        try:
            self.server_loop.create_task(self.server_instance.start())
            self.server_loop.run_forever()
        except Exception as e:
            logging.error(f"Server crashed: {e}")
        finally:
            self.server_loop.close()

if __name__ == "__main__":
    app = App()
    app.mainloop()
