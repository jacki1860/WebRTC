# WebRTC Audio Streamer (Python -> Unity)

This project streams your microphone audio from a Python server to a Unity client using WebRTC.

## Prerequisites

- **Python 3.7+**
- **Unity 2021.3+** (or any version supporting `com.unity.webrtc`)
- **PortAudio** (System dependency for PyAudio)
    - **macOS**: `brew install portaudio`
    - **Linux**: `sudo apt-get install python3-pyaudio portaudio19-dev`
    - **Windows**: Usually pre-compiled wheels are available, or use pipwin.

## Installation (Python Server)

1.  Create and activate a virtual environment:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
    *Note: If `pyaudio` fails to install, ensure you have `portaudio` installed.*

## Usage

### 1. Start the Server (GUI)

The easiest way to use the server is via the new GUI:

```bash
source venv/bin/activate
python gui.py
```

- Select your microphone from the dropdown.
- (Optional) Change the port (default 8080).
- Click **Start Server**.
- The server will show the local IP address which you can use in Unity if testing on a different device.

### 1b. Start the Server (Command Line)
Alternatively, you can still run the server from the command line:

```bash
source venv/bin/activate
python server.py --port 8080
```

### 2. Unity Client Setup

1.  Open your Unity Project.
2.  Open **Window > Package Manager**.
3.  Click `+` > **Add package from git URL...** and enter:
    `com.unity.webrtc`
4.  Wait for installation to complete.
5.  Create a new specific GameObject (e.g., "WebRTCClient") in your scene.
6.  Add an **AudioSource** component to it.
    - Set `Loop` to true (optional, depends on stream behavior, but usually streaming is continuous).
    - Ensure `Play On Awake` is checked.
7.  Create a new C# script named `UnityClient.cs` and paste the content provided in this project.
8.  Attach the `UnityClient` script to the GameObject.
9.  Assign the **AudioSource** to the script's `Audio Source` field in the Inspector.
10. Press **Play**. You should see "WebRTC Connection Established!" in the console and hear your microphone audio.

## Troubleshooting

- **No Audio?** 
    - Check Unity Console for errors.
    - Verify your microphone is working on the server side.
    - Ensure `com.unity.webrtc` package is installed.
- **ICE Connection Failed?**
    - Ensure no firewall blocks the connection.
    - If running on different machines, allow port 8080 and UDP ports range (usually arbitrary for WebRTC, or configure ICE servers).
