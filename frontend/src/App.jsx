import { useState } from "react";
import CameraPanel from "./CameraPanel";
import {
  Activity,
  Camera,
  Upload,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Clock3,
  ScanLine,
  UserRound,
  FileCheck2,
  Database,
  RotateCcw,
  Search,
  XCircle,
} from "lucide-react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

function App() {
  const [activeDocument, setActiveDocument] = useState("Passport");
  const [documentFile, setDocumentFile] = useState(null);
  const [selfieFile, setSelfieFile] = useState(null);

  const [analyzing, setAnalyzing] = useState(false);
  const [analyzed, setAnalyzed] = useState(false);
  const [showCamera, setShowCamera] = useState(false);

  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const documents = [
    "Passport",
    "Visa",
    "National ID",
    "Driving License",
  ];

  // IMPORTANT: Backend-compatible document types
  const docTypeMap = {
    Passport: "passport",
    Visa: "visa",
    "National ID": "national_id",
    "Driving License": "driving_license",
  };

  const handleDocumentUpload = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setDocumentFile(file);
    setAnalyzed(false);
    setResult(null);
    setError("");
  };

  const handleSelfieCapture = (file) => {
    setSelfieFile(file);
    setAnalyzed(false);
    setResult(null);
    setError("");
  };

  const handleAnalyze = async () => {
    setError("");

    if (!documentFile) {
      setError("Please upload a document image first.");
      return;
    }

    if (!selfieFile) {
      setError("Please capture a live selfie first.");
      return;
    }

    setAnalyzing(true);
    setAnalyzed(false);
    setResult(null);

    try {
      const formData = new FormData();

      formData.append("doc_image", documentFile);
      formData.append("live_selfie", selfieFile);

      // FIX: Send lowercase backend-compatible document type
      formData.append(
        "doc_type",
        docTypeMap[activeDocument] || activeDocument.toLowerCase()
      );

      console.log(
        "Sending doc_type:",
        docTypeMap[activeDocument] || activeDocument.toLowerCase()
      );

      const response = await fetch(`${API_URL}/screen`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        let message = `Backend returned HTTP ${response.status}.`;

        try {
          const errorBody = await response.json();
          if (errorBody.detail) {
            message =
              typeof errorBody.detail === "string"
                ? errorBody.detail
                : JSON.stringify(errorBody.detail);
          }
        } catch {
          // Keep default error
        }

        throw new Error(message);
      }

      const data = await response.json();

      console.log("Screening result:", data);

      setResult(data);
      setAnalyzed(true);
    } catch (err) {
      console.error("Screening request failed:", err);
      setError(
        err.message || "Unable to connect to the screening backend."
      );
    } finally {
      setAnalyzing(false);
    }
  };

  const handleReset = () => {
    setDocumentFile(null);
    setSelfieFile(null);
    setAnalyzed(false);
    setAnalyzing(false);
    setResult(null);
    setError("");
    setShowCamera(false);
  };

  // API results
  const ocr = result?.ocr;
  const validation = result?.validation;
  const tampering = result?.tampering;
  const face = result?.face;
  const authority = result?.authority_match;
  const risk = result?.risk;

  const getFieldValue = (fieldName) => {
    return ocr?.extracted_fields?.[fieldName]?.value ?? "—";
  };

  const riskScore = risk?.risk_score ?? null;
  const riskBand = risk?.risk_band ?? null;

  // API uses "similarity", not similarity_score
  const faceScore = face?.similarity ?? null;

  const tamperFlag =
    tampering?.overall_tamper_flag ?? false;

  // FIX: Your backend does NOT return is_valid.
  // Calculate validation from actual backend fields.
  const validationPassed =
    validation?.status === "success" &&
    validation?.checksum_pass === true &&
    validation?.text_mrz_match === true &&
    validation?.expiry_valid === true &&
    validation?.db_status === "clear";

  // Authority API uses status, not authority_match/matched
  const authorityMatched =
    authority?.status === "match"
      ? true
      : authority?.status === "mismatch"
        ? false
        : null;

  return (
    <div className="app">

      <header className="topbar">
        <div>
          <h1>
            AI Based Fake Identity &amp; Document Screening System
          </h1>
          <p>
            Capture and verify identity documents before completing
            identity screening.
          </p>
        </div>

        <div className="top-actions">
          <button className="activity-btn">
            <Activity size={17} />
            Activity log
          </button>

          <button className="scan-again" onClick={handleReset}>
            <RotateCcw size={16} />
            Scan again
          </button>
        </div>
      </header>

      <div className="progress">
        <div className="progress-step active">
          <span>01</span>
          DOCUMENT CAPTURE
        </div>

        <div className="progress-line"></div>

        <div className={`progress-step ${analyzed ? "active" : ""}`}>
          <span>02</span>
          IDENTITY CHECK
        </div>

        <div className="progress-line"></div>

        <div className={`progress-step ${analyzed ? "active" : ""}`}>
          <span>03</span>
          DECISION
        </div>
      </div>

      {error && (
        <div className="error-banner">
          <XCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      <main className="main-grid">

        <section className="capture-card card">

          <div className="section-label">
            <span>01</span>
            DOCUMENT CAPTURE
          </div>

          <div className="card-heading">
            <div>
              <h2>Capture required documents</h2>
              <p>Choose a document type and upload a clear image.</p>
            </div>

            <span className="secure">
              <ShieldCheck size={15} />
              ENCRYPTED
            </span>
          </div>

          <div className="document-tabs">
            {documents.map((doc) => (
              <button
                key={doc}
                className={
                  activeDocument === doc
                    ? "tab active-tab"
                    : "tab"
                }
                onClick={() => {
                  setActiveDocument(doc);
                  setAnalyzed(false);
                  setResult(null);
                  setError("");
                }}
              >
                <FileCheck2 size={15} />
                <span>{doc}</span>
              </button>
            ))}
          </div>

          <div className="capture-status">
            <CheckCircle2 size={17} />
            <div>
              <strong>
                {documentFile
                  ? documentFile.name
                  : "Document capture ready"}
              </strong>
              <span>
                {documentFile
                  ? "Document image selected."
                  : "Upload an image to begin automated screening."}
              </span>
            </div>
          </div>

          <div className="document-preview">
            {showCamera ? (
              <CameraPanel
                onClose={() => setShowCamera(false)}
                onCapture={handleSelfieCapture}
              />
            ) : (
              <>
                <div className="scan-corners"></div>

                {documentFile ? (
                  <img
                    src={URL.createObjectURL(documentFile)}
                    alt="Uploaded document"
                    className="uploaded-document-preview"
                  />
                ) : (
                  <div className="passport-placeholder">
                    <div className="passport-header">
                      <span>REPUBLIC OF INDIA</span>
                      <span>PASSPORT</span>
                    </div>

                    <div className="passport-body">
                      <div className="fake-photo">
                        <UserRound size={42} />
                      </div>

                      <div className="passport-lines">
                        <div>
                          <small>SURNAME</small>
                          <b>DOCUMENT</b>
                        </div>

                        <div>
                          <small>GIVEN NAME</small>
                          <b>PREVIEW</b>
                        </div>
                      </div>
                    </div>

                    <div className="mrz">
                      Upload a document image to begin
                    </div>
                  </div>
                )}

                {analyzed && tamperFlag && (
                  <div className="suspicious-box">
                    <span>Possible alteration</span>
                  </div>
                )}
              </>
            )}
          </div>

          <div className="capture-actions">
            <button
              className="primary-btn"
              onClick={() => setShowCamera(true)}
            >
              <Camera size={17} />
              Capture Selfie
            </button>

            <label className="secondary-btn">
              <Upload size={17} />
              Upload Image
              <input
                type="file"
                hidden
                accept="image/*"
                onChange={handleDocumentUpload}
              />
            </label>

            <button className="secondary-btn" type="button">
              <ScanLine size={17} />
              Check NFC Chip
            </button>
          </div>

          <div className="capture-status">
            <CheckCircle2 size={17} />
            <div>
              <strong>
                {selfieFile ? "Selfie captured" : "Selfie required"}
              </strong>
              <span>
                {selfieFile
                  ? "Live selfie is ready for face verification."
                  : "Open the camera and capture a selfie."}
              </span>
            </div>
          </div>

          <p className="helper-text">
            <ShieldCheck size={14} />
            Documents are processed securely.
          </p>

        </section>

        <aside className="right-column">

          <section className="card verification-card">

            <div className="card-top">
              <div>
                <div className="section-label small-label">
                  VERIFICATION RESULT
                </div>
                <h2>Identity confidence</h2>
              </div>

              <span className="safe-badge">
                <span></span>
                {analyzing
                  ? "ANALYZING"
                  : analyzed
                    ? "COMPLETE"
                    : "READY"}
              </span>
            </div>

            <div className="confidence">
              <div className="confidence-circle">
                <strong>
                  {faceScore !== null
                    ? Math.round(Number(faceScore) * 100)
                    : "—"}
                </strong>

                {faceScore !== null && <small>%</small>}
              </div>

              <div>
                <h3>
                  {analyzing
                    ? "Screening in progress"
                    : analyzed
                      ? "Identity screening complete"
                      : "Complete document set"}
                </h3>
                <p>
                  {analyzed
                    ? "Verification signals have been analyzed."
                    : "Upload a document and capture a selfie to start."}
                </p>
              </div>
            </div>

            <div className="checks">

              <VerificationRow
                icon={<FileCheck2 size={17} />}
                title="Document Integrity"
                subtitle="Format and structure validation"
                status={
                  !analyzed
                    ? "—"
                    : validationPassed
                      ? "PASS"
                      : "FAIL"
                }
                type={
                  !analyzed
                    ? "neutral"
                    : validationPassed
                      ? "success"
                      : "warning"
                }
              />

              <VerificationRow
                icon={<Search size={17} />}
                title="OCR Extraction"
                subtitle="Extract document information"
                status={
                  analyzed
                    ? ocr?.status === "success"
                      ? "COMPLETE"
                      : "FAILED"
                    : "—"
                }
                type={
                  analyzed
                    ? ocr?.status === "success"
                      ? "success"
                      : "warning"
                    : "neutral"
                }
              />

              <VerificationRow
                icon={<ScanLine size={17} />}
                title="MRZ Validation"
                subtitle="Checksum and field consistency"
                status={
                  !analyzed
                    ? "—"
                    : validation?.text_mrz_match
                      ? "PASS"
                      : "REVIEW"
                }
                type={
                  !analyzed
                    ? "neutral"
                    : validation?.text_mrz_match
                      ? "success"
                      : "warning"
                }
              />

              <VerificationRow
                icon={<AlertTriangle size={17} />}
                title="Tampering Detection"
                subtitle="Digital manipulation screening"
                status={
                  !analyzed
                    ? "—"
                    : tamperFlag
                      ? "REVIEW"
                      : "PASS"
                }
                type={
                  !analyzed
                    ? "neutral"
                    : tamperFlag
                      ? "warning"
                      : "success"
                }
              />

              <VerificationRow
                icon={<UserRound size={17} />}
                title="Face Verification"
                subtitle="Document photo comparison"
                status={
                  !analyzed
                    ? "—"
                    : face?.status === "match"
                      ? "MATCH"
                      : face?.status === "mismatch"
                        ? "MISMATCH"
                        : "NO FACE"
                }
                type={
                  face?.status === "match"
                    ? "success"
                    : face?.status === "mismatch" ||
                      face?.status === "no_face_detected"
                      ? "warning"
                      : "neutral"
                }
              />

              <VerificationRow
                icon={<Database size={17} />}
                title="Authority Reference"
                subtitle="Trusted record comparison"
                status={
                  authority?.status === "match"
                    ? "MATCH"
                    : authority?.status === "mismatch"
                      ? "MISMATCH"
                      : authority?.status === "not_available"
                        ? "NOT AVAILABLE"
                        : "—"
                }
                type={
                  authority?.status === "match"
                    ? "success"
                    : authority?.status === "mismatch"
                      ? "warning"
                      : "neutral"
                }
              />

            </div>

            {!analyzed && (
              <button
                className="bottom-primary"
                onClick={handleAnalyze}
                disabled={analyzing}
              >
                <ScanLine size={17} />
                {analyzing ? "Analyzing..." : "Analyze document"}
              </button>
            )}

          </section>

          <section className="card trusted-card">

            <div className="card-top">
              <div>
                <div className="section-label small-label">
                  RECORD LOOKUP
                </div>
                <h2>Trusted record</h2>
              </div>
              <Database size={18} />
            </div>

            <div className="search-box">
              <Search size={16} />
              <span>Lookup identity after document screening</span>
            </div>

            <div className="record">
              <div className="avatar">
                {getFieldValue("name") !== "—"
                  ? getFieldValue("name")
                      .split(" ")
                      .map((part) => part[0])
                      .join("")
                      .slice(0, 2)
                  : "—"}
              </div>

              <div className="record-info">
                <strong>{getFieldValue("name")}</strong>
                <span>
                  Document: {getFieldValue("passport_number")}
                </span>
              </div>

              <span className="record-status">
                {authorityMatched === true
                  ? "Verified"
                  : authorityMatched === false
                    ? "Mismatch"
                    : "Pending validation"}
              </span>
            </div>

          </section>

        </aside>
      </main>

      <section className="bottom-grid">

        <div className="card extracted-card">
          <div className="section-label small-label">
            EXTRACTED INFORMATION
          </div>

          <div className="info-grid">
            <Info label="Full name" value={getFieldValue("name")} />
            <Info label="Nationality" value={getFieldValue("nationality")} />
            <Info label="Date of birth" value={getFieldValue("dob")} />
            <Info
              label="Document number"
              value={getFieldValue("passport_number")}
            />
            <Info label="Expiry date" value={getFieldValue("expiry")} />
            <Info label="Document type" value={activeDocument} />
          </div>
        </div>

        <div className="card risk-card">

          <div className="section-label small-label">
            SCREENING DECISION
          </div>

          <div className="risk-header">
            <div>
              <span>Risk score</span>
              <strong>
                {riskScore !== null ? riskScore : "—"}
              </strong>
              <small>/ 100</small>
            </div>

            <span
              className={
                riskBand
                  ? `risk-badge ${String(riskBand).toLowerCase()}`
                  : "risk-badge"
              }
            >
              {riskBand
                ? String(riskBand).replace("_", " ").toUpperCase()
                : "AWAITING ANALYSIS"}
            </span>
          </div>

          {analyzed ? (
            <div className="risk-reasons">

              <div>
                {tamperFlag ? (
                  <AlertTriangle size={15} />
                ) : (
                  <CheckCircle2 size={15} />
                )}
                {tamperFlag
                  ? "Document tampering detected"
                  : "No document tampering detected"}
              </div>

              <div>
                {validationPassed ? (
                  <CheckCircle2 size={15} />
                ) : (
                  <AlertTriangle size={15} />
                )}
                {validationPassed
                  ? "Document validation passed"
                  : "Document validation requires review"}
              </div>

              {face?.status === "no_face_detected" && (
                <div>
                  <AlertTriangle size={15} />
                  No face detected in document
                </div>
              )}

            </div>
          ) : (
            <p className="empty-risk">
              Complete document analysis to generate the screening decision.
            </p>
          )}

        </div>
      </section>

      <footer>
        <div>
          <ShieldCheck size={15} />
          AI-assisted screening • Final decision remains with authorized officer
        </div>

        <div>
          <Clock3 size={14} />
          {analyzing ? "Screening in progress" : "System ready"}
        </div>
      </footer>

    </div>
  );
}

function VerificationRow({
  icon,
  title,
  subtitle,
  status,
  type,
}) {
  return (
    <div className="verification-row">
      <div className={`check-icon ${type}`}>
        {icon}
      </div>

      <div className="check-text">
        <strong>{title}</strong>
        <span>{subtitle}</span>
      </div>

      <span className={`check-status ${type}`}>
        {type === "success" && <CheckCircle2 size={14} />}
        {type === "warning" && <AlertTriangle size={14} />}
        {status}
      </span>
    </div>
  );
}

function Info({ label, value }) {
  return (
    <div className="info-item">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export default App;