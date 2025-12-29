import pyaudio
import sys

try:
    p = pyaudio.PyAudio()
    print("PyAudio initialized successfully")
    count = p.get_device_count()
    print(f"Found {count} devices")
    p.terminate()
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
