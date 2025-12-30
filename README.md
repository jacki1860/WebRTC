# WebRTC 音訊串流 (Python -> Unity)

此專案使用 WebRTC 將您的麥克風音訊從 Python 伺服器串流傳輸到 Unity 用戶端。

## 先決條件

- **Python 3.7+**
- **Unity 2021.3+** (或任何支援 `com.unity.webrtc` 的版本)
- **PortAudio** (PyAudio 的系統相依套件)
    - **macOS**: `brew install portaudio`
    - **Linux**: `sudo apt-get install python3-pyaudio portaudio19-dev`
    - **Windows**: 通常有預編譯的 wheel 可用，或者使用 pipwin。

## 安裝 (Python 伺服器)

1.  建立並啟用虛擬環境：
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

2.  安裝相依套件：
    ```bash
    pip install -r requirements.txt
    ```
    *注意：如果 `pyaudio` 安裝失敗，請確認您已安裝 `portaudio`。*

## 使用方法

### 1. 啟動伺服器 (GUI)

使用伺服器最簡單的方法是透過新的 GUI 介面：

```bash
source venv/bin/activate
python gui.py
```

- 從下拉式選單中選擇您的麥克風。
- (選用) 更改連接埠 (預設為 8080)。
- 點擊 **Start Server** (啟動伺服器)。
- 伺服器將顯示本機 IP 位址，如果您在不同的裝置上測試 Unity，可以使用此位址。

### 1b. 啟動伺服器 (命令列)
或者，您仍然可以從命令列執行伺服器：

```bash
source venv/bin/activate
python server.py --port 8080
```

### 1c. 同時執行多個伺服器 (進階)
如果您需要同時串流多個音訊來源，可以開啟多個伺服器實例，但必須指定不同的連接埠。

**GUI 模式：**
您可以開啟多個 `gui.py` 視窗，在每個視窗中分別設定不同的連接埠（例如 8080 和 8081），並選擇不同的麥克風來源，然後點擊啟動。

**命令列模式：**
開啟兩個終端機視窗，分別執行：
```bash
# 終端機 1
python server.py --port 8080

# 終端機 2
python server.py --port 8081
```

### 2. Unity 用戶端設定

1.  開啟您的 Unity 專案。
2.  開啟 **Window > Package Manager**。
3.  點擊 `+` > **Add package from git URL...** 並輸入：
    `com.unity.webrtc`
4.  等待安裝完成。
5.  在場景中建立一個新的 GameObject (例如 "WebRTCClient")。
6.  為其新增一個 **AudioSource** 元件。
    - 將 `Loop` 設定為 true (選用，取決於串流行為，但通常串流是連續的)。
    - 確認已勾選 `Play On Awake`。
7.  建立一個名為 `UnityClient.cs` 的新 C# 腳本，並貼上此專案中提供的內容。
8.  將 `UnityClient` 腳本附加到該 GameObject 上。
9.  在 Inspector 中將 **AudioSource** 指派給腳本的 `Audio Source` 欄位。
10. 按下 **Play**。您應該會在主控台看到 "WebRTC Connection Established!" (WebRTC 連線已建立！)，並聽到您的麥克風音訊。

## 疑難排解

- **沒有聲音？**
    - 檢查 Unity Console 是否有錯誤。
    - 確認伺服器端的麥克風是否正常運作。
    - 確認已安裝 `com.unity.webrtc` 套件。
- **ICE 連線失敗？**
    - 確認沒有防火牆阻擋連線。
    - 如果在不同機器上執行，請允許 8080 連接埠和 UDP 連接埠範圍 (WebRTC 通常是任意的，或是設定 ICE 伺服器)。
