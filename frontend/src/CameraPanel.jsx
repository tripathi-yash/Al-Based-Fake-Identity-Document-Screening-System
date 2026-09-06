import { useEffect, useRef, useState } from "react";
import {
  Camera,
  CameraOff,
  CheckCircle2,
  AlertCircle,
  RotateCcw,
} from "lucide-react";

function CameraPanel({ onClose, onCapture }) {
  const videoRef = useRef(null);
  const streamRef = useRef(null);

  const [cameraOn, setCameraOn] = useState(false);
  const [error, setError] = useState("");

  const startCamera = async () => {
    setError("");

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: "user",
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      });

      streamRef.current = stream;

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }

      setCameraOn(true);
    } catch (err) {
      console.error(err);
      setError(
        "Camera access denied or camera is not available. Please allow camera permission."
      );
    }
  };

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }

    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }

    setCameraOn(false);
  };

  const captureSelfie = () => {
    const video = videoRef.current;

    if (!video || !video.videoWidth || !video.videoHeight) {
      setError("Camera is not ready yet.");
      return;
    }

    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const context = canvas.getContext("2d");

    context.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob(
      (blob) => {
        if (!blob) {
          setError("Failed to capture selfie.");
          return;
        }

        const selfieFile = new File(
          [blob],
          "live_selfie.jpg",
          { type: "image/jpeg" }
        );

        onCapture(selfieFile);

        stopCamera();
        onClose();
      },
      "image/jpeg",
      0.92
    );
  };

  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  return (
    <div className="camera-panel">
      <div className="camera-header">
        <div>
          <span className="camera-label">LIVE CAMERA</span>
          <h3>Identity capture</h3>
        </div>

        <button
          className="camera-close"
          onClick={() => {
            stopCamera();
            onClose();
          }}
        >
          ×
        </button>
      </div>

      <div className="camera-view">
        <video
          ref={videoRef}
          className="camera-video"
          autoPlay
          playsInline
          muted
        />

        {!cameraOn && !error && (
          <div className="camera-placeholder">
            <Camera size={45} />
            <strong>Camera is ready</strong>
            <span>Click Start Camera to begin</span>
          </div>
        )}

        {cameraOn && (
          <>
            <div className="face-frame"></div>

            <div className="camera-status">
              <span></span>
              LIVE
            </div>

            <div className="face-status">
              <CheckCircle2 size={16} />
              Position your face inside the frame
            </div>
          </>
        )}

        {error && (
          <div className="camera-error">
            <AlertCircle size={25} />
            <strong>Camera unavailable</strong>
            <span>{error}</span>
          </div>
        )}
      </div>

      <div className="camera-controls">
        {!cameraOn ? (
          <button className="primary-btn" onClick={startCamera}>
            <Camera size={17} />
            Start Camera
          </button>
        ) : (
          <>
            <button className="primary-btn" onClick={captureSelfie}>
              <CheckCircle2 size={17} />
              Capture Selfie
            </button>

            <button className="stop-camera-btn" onClick={stopCamera}>
              <CameraOff size={17} />
              Stop Camera
            </button>
          </>
        )}

        {error && (
          <button className="secondary-btn" onClick={startCamera}>
            <RotateCcw size={17} />
            Try Again
          </button>
        )}
      </div>

      <p className="camera-note">
        Camera video stays on this device and is used for identity verification.
      </p>
    </div>
  );
}

export default CameraPanel;