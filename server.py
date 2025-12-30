import asyncio
import argparse
import logging
import json
import time
import threading

pyaudio_lock = threading.Lock()

from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription, AudioStreamTrack
from aiortc.contrib.media import MediaPlayer, MediaRelay
import pyaudio
import numpy as np
from av import AudioFrame
from fractions import Fraction

# Configure logging to also log to file or just rely on handlers added by GUI
logger = logging.getLogger("pc")

class MicrophoneStreamTrack(AudioStreamTrack):
    """
    A MediaStreamTrack that reads audio from the microphone using PyAudio.
    """
    kind = "audio"

    def __init__(self, device_index=None):
        super().__init__()
        with pyaudio_lock:
            self.p = pyaudio.PyAudio()
        self.rate = 48000
        self.channels = 1
        self.format = pyaudio.paInt16
        self.chunk = 960 
        
        try:
            self.stream = self.p.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.chunk
            )
            logger.info(f"Opened microphone device index: {device_index if device_index is not None else 'Default'}")
        except Exception as e:
            logger.error(f"Failed to open microphone: {e}")
            self.stream = None

        self.start_time = None
        self.pts = 0

    async def recv(self):
        if self.stream is None:
            # Output silence if mic failed
            frame = AudioFrame(format='s16', layout='mono', samples=self.chunk)
            frame.planes[0].update(bytes(self.chunk * 2))
            frame.sample_rate = self.rate
            frame.pts = self.pts
            frame.time_base = Fraction(1, self.rate)
            self.pts += self.chunk
            return frame

        if self.start_time is None:
            self.start_time = time.time()

        try:
            loop = asyncio.get_event_loop()
            # Run blocking read in executor to avoid blocking the main event loop (stutter fix)
            data = await loop.run_in_executor(None, lambda: self.stream.read(self.chunk, exception_on_overflow=False))
            
            np_data = np.frombuffer(data, dtype=np.int16)
            
            # Apply Gain (Volume Boost)
            # Convert to float32 for processing to avoid overflow
            float_data = np_data.astype(np.float32)
            float_data = float_data * 5.0 # Boost volume by 5x (adjustable)
            
            # Clip to int16 range
            float_data = np.clip(float_data, -32768, 32767)
            
            # Convert back to int16
            np_data = float_data.astype(np.int16)
            
            frame = AudioFrame(format='s16', layout='mono', samples=self.chunk)
            frame.planes[0].update(np_data.tobytes())
            frame.sample_rate = self.rate
            frame.pts = self.pts
            frame.time_base = Fraction(1, self.rate)
            self.pts += self.chunk
            return frame
        except Exception as e:
            logger.error(f"Error reading audio stream: {e}")
            # Output silence on error to prevent crash
            frame = AudioFrame(format='s16', layout='mono', samples=self.chunk)
            frame.planes[0].update(bytes(self.chunk * 2))
            frame.sample_rate = self.rate
            frame.pts = self.pts
            frame.time_base = Fraction(1, self.rate)
            self.pts += self.chunk
            return frame

    def stop(self):
        super().stop()
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception:
                pass
        if self.p:
            try:
                self.p.terminate()
            except Exception:
                pass

class WebRTCServer:
    def __init__(self, port=8080, device_index=None):
        self.port = port
        self.device_index = device_index
        self.pcs = set()
        self.app = web.Application()
        self.app.router.add_post("/offer", self.offer)
        self.app.on_shutdown.append(self.on_shutdown)
        self.runner = None
        self.site = None

    async def offer(self, request):
        try:
            logger.info("Received offer request")
            params = await request.json()
            logger.info(f"Offer SDP received. Type: {params.get('type')}")
            
            offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

            pc = RTCPeerConnection()
            self.pcs.add(pc)

            logger.info("Created PC for %s", request.remote)

            track = MicrophoneStreamTrack(self.device_index)
            pc.addTrack(track)
            logger.info(f"Added microphone track: {track}")

            @pc.on("iceconnectionstatechange")
            async def on_iceconnectionstatechange():
                logger.info("ICE connection state is %s", pc.iceConnectionState)
                if pc.iceConnectionState == "failed":
                    await pc.close()
                    self.pcs.discard(pc)

            logger.info("Setting remote description...")
            await pc.setRemoteDescription(offer)
            logger.info("Remote description set.")

            logger.info("Creating answer...")
            answer = await pc.createAnswer()
            logger.info("Answer created.")
            
            logger.info("Setting local description...")
            await pc.setLocalDescription(answer)
            logger.info("Local description set.")
            return web.Response(
                content_type="application/json",
                text=json.dumps(
                    {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
                ),
            )
        except Exception as e:
            logger.error(f"Error in offer handling: {e}", exc_info=True)
            return web.Response(status=500, text=str(e))

    async def on_shutdown(self, app):
        coros = [pc.close() for pc in self.pcs]
        if coros:
            await asyncio.gather(*coros)
        self.pcs.clear()

    async def index(self, request):
        content = open("index.html", "r").read()
        return web.Response(content_type="text/html", text=content)

    async def start(self):
        self.app.router.add_get("/", self.index)
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, "0.0.0.0", self.port)
        await self.site.start()
        logger.info(f"Server started at http://localhost:{self.port}")

    async def stop(self):
        if self.runner:
            await self.runner.cleanup()
        logger.info("Server stopped")

def get_audio_devices():
    p = pyaudio.PyAudio()
    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    devices = []
    for i in range(0, numdevices):
        if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
            name = p.get_device_info_by_host_api_device_index(0, i).get('name')
            devices.append((i, name))
    p.terminate()
    return devices

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WebRTC Audio Streamer")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on")
    args = parser.parse_args()

    # Simple run for command line
    logging.basicConfig(level=logging.INFO)
    server = WebRTCServer(port=args.port)
    web.run_app(server.app, host="0.0.0.0", port=args.port)
