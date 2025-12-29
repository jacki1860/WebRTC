using System.Collections;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;
using Unity.WebRTC;

public class UnityClient : MonoBehaviour
{
    [SerializeField] private string serverUrl = "http://localhost:8080/offer";
    [SerializeField] private AudioSource audioSource;
    
    private RTCPeerConnection pc;
    
    private void Start()
    {
        StartCoroutine(WebRTCSetup());
    }

    private IEnumerator WebRTCSetup()
    {
        var config = new RTCConfiguration
        {
            iceServers = new[] { new RTCIceServer { urls = new[] { "stun:stun.l.google.com:19302" } } }
        };

        pc = new RTCPeerConnection(ref config);

        pc.OnTrack = e =>
        {
            if (e.Track is AudioStreamTrack audioTrack)
            {
                audioTrack.OnAudioReceived += vol =>
                {
                    // Optional: Visualizer logic here
                };
                
                // IMPORTANT: In Unity WebRTC, received audio is automatically routed to the AudioSource
                // if you wire it up correctly.
                // However, direct AudioSource output from track varies by version.
                // Modern Unity WebRTC often plays directly if not explicit.
                // Just ensuring the track is enabled.
                audioTrack.Enabled = true;
            }
        };

        // Create Transceiver to receive audio only
        pc.AddTransceiver(TrackKind.Audio, new RTCRtpTransceiverInit { direction = RTCRtpTransceiverDirection.RecvOnly });

        var op = pc.CreateOffer();
        yield return op;

        if (op.IsError)
        {
            Debug.LogError($"CreateOffer failed: {op.Error}");
            yield break;
        }

        var offerDesc = op.Desc;
        var op2 = pc.SetLocalDescription(ref offerDesc);
        yield return op2;

        if (op2.IsError)
        {
            Debug.LogError($"SetLocalDescription failed: {op2.Error}");
            yield break;
        }

        // Send Offer to Server
        var jsonOffer = JsonUtility.ToJson(new SignallingMessage
        {
            sdp = offerDesc.sdp,
            type = offerDesc.type.ToString().ToLower()
        });

        var request = new UnityWebRequest(serverUrl, "POST");
        byte[] bodyRaw = Encoding.UTF8.GetBytes(jsonOffer);
        request.uploadHandler = new UploadHandlerRaw(bodyRaw);
        request.downloadHandler = new DownloadHandlerBuffer();
        request.SetRequestHeader("Content-Type", "application/json");

        yield return request.SendWebRequest();

        if (request.result != UnityWebRequest.Result.Success)
        {
            Debug.LogError($"Signaling error: {request.error}");
            yield break;
        }

        var response = JsonUtility.FromJson<SignallingMessage>(request.downloadHandler.text);
        var answerDesc = new RTCSessionDescription
        {
            sdp = response.sdp,
            type = RTCSdpType.Answer
        };

        var op3 = pc.SetRemoteDescription(ref answerDesc);
        yield return op3;

        if (op3.IsError)
        {
            Debug.LogError($"SetRemoteDescription failed: {op3.Error}");
        }
        else
        {
            Debug.Log("WebRTC Connection Established!");
        }
    }
    
    private void OnDestroy()
    {
        pc?.Close();
        pc?.Dispose();
    }

    [System.Serializable]
    class SignallingMessage
    {
        public string sdp;
        public string type;
    }
}
