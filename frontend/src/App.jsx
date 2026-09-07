// import { useMemo, useState } from "react";
// import CameraPanel from "./CameraPanel";

// import {
//   Camera,
//   Upload,
//   ShieldCheck,
//   CheckCircle2,
//   AlertTriangle,
//   Clock3,
//   ScanLine,
//   UserRound,
//   FileCheck2,
//   Database,
//   RotateCcw,
//   Search,
//   XCircle,
//   Landmark,
//   LockKeyhole,
//   Eye,
//   History,
//   Fingerprint,
//   ChevronRight,
//   ShieldAlert,
// } from "lucide-react";

// import "./App.css";

// const API_URL = "http://127.0.0.1:8000";

// const BACKEND_DOC_TYPES = {
//   Passport: "passport",
//   Visa: "visa",
//   "National ID": "national_id",
//   "Driving License": "driving_license",
// };

// function App() {
//   const [activeDocument, setActiveDocument] = useState("Passport");

//   const [documentFile, setDocumentFile] = useState(null);
//   const [selfieFile, setSelfieFile] = useState(null);

//   const [analyzing, setAnalyzing] = useState(false);
//   const [analyzed, setAnalyzed] = useState(false);

//   const [showCamera, setShowCamera] = useState(false);

//   const [result, setResult] = useState(null);
//   const [error, setError] = useState("");

//   // ================= LEDGER =================

//   const [showActivity, setShowActivity] = useState(false);
//   const [ledgerRecords, setLedgerRecords] = useState([]);
//   const [loadingLedger, setLoadingLedger] = useState(false);

//   const [selectedLedgerRecord, setSelectedLedgerRecord] =
//     useState(null);

//   const [showIdentityReuseAlert, setShowIdentityReuseAlert] =
//   useState(false);

//   const [identityReuseRecords, setIdentityReuseRecords] =
//   useState([]);

//   // ================= LOOKUP =================

//   const [lookupSource, setLookupSource] = useState("issuance");
//   const [lookupQuery, setLookupQuery] = useState("");
//   const [lookupResult, setLookupResult] = useState(null);
//   const [lookupLoading, setLookupLoading] = useState(false);

//   const documents = [
//     "Passport",
//     "Visa",
//     "National ID",
//     "Driving License",
//   ];

//   // ================= PREVIEWS =================

//   const documentPreview = useMemo(
//     () =>
//       documentFile
//         ? URL.createObjectURL(documentFile)
//         : null,
//     [documentFile],
//   );

//   const selfiePreview = useMemo(
//     () =>
//       selfieFile
//         ? URL.createObjectURL(selfieFile)
//         : null,
//     [selfieFile],
//   );

//   // ================= FILE HANDLERS =================

//   const handleDocumentUpload = (event) => {
//     const file = event.target.files?.[0];

//     if (!file) return;

//     setDocumentFile(file);
//     setAnalyzed(false);
//     setResult(null);
//     setError("");
//   };

//   const handleSelfieUpload = (event) => {
//     const file = event.target.files?.[0];

//     if (!file) return;

//     setSelfieFile(file);
//     setAnalyzed(false);
//     setResult(null);
//     setError("");
//   };

//   const handleSelfieCapture = (file) => {
//     if (!file) return;

//     setSelfieFile(file);
//     setAnalyzed(false);
//     setResult(null);
//     setError("");
//     setShowCamera(false);
//   };

//   // ================= SCREENING =================

//   const handleAnalyze = async () => {
//     setError("");

//     if (!documentFile) {
//       setError("Please upload a document image first.");
//       return;
//     }

//     if (!selfieFile) {
//       setError("Please capture or upload a selfie first.");
//       return;
//     }

//     setAnalyzing(true);
//     setAnalyzed(false);
//     setResult(null);

//     try {
//       const formData = new FormData();

//       formData.append("doc_image", documentFile);
//       formData.append("live_selfie", selfieFile);

//       formData.append(
//         "doc_type",
//         BACKEND_DOC_TYPES[activeDocument] ||
//           activeDocument.toLowerCase().replace(/\s+/g, "_"),
//       );

//       const response = await fetch(`${API_URL}/screen`, {
//         method: "POST",
//         body: formData,
//       });

//       if (!response.ok) {
//         let message =
//           `Backend returned HTTP ${response.status}.`;

//         try {
//           const body = await response.json();

//           if (body.detail) {
//             message =
//               typeof body.detail === "string"
//                 ? body.detail
//                 : JSON.stringify(body.detail);
//           }
//         } catch {
//           // Keep HTTP error.
//         }

//         throw new Error(message);
//       }

//       const data = await response.json();

//       console.log("Screening result:", data);

//       setResult(data);
//       setAnalyzed(true);
//     } catch (err) {
//       console.error(err);

//       setError(
//         err.message ||
//           "Unable to connect to the screening backend.",
//       );
//     } finally {
//       setAnalyzing(false);
//     }
//   };

//   // ================= LEDGER =================

//   const loadLedger = async () => {
//     setShowActivity(true);
//     setLoadingLedger(true);
//     setError("");

//     try {
//       const response = await fetch(`${API_URL}/ledger`);

//       if (!response.ok) {
//         throw new Error(
//           `Unable to load blockchain ledger: HTTP ${response.status}`,
//         );
//       }

//       const data = await response.json();

//       setLedgerRecords(
//         Array.isArray(data)
//           ? data
//           : Array.isArray(data.records)
//             ? data.records
//             : [],
//       );
//     } catch (err) {
//       console.error(err);

//       setError(
//         err.message ||
//           "Unable to load blockchain activity.",
//       );
//     } finally {
//       setLoadingLedger(false);
//     }
//   };

//   const getRecordHash = (record) =>
//     record?.record_hash ||
//     record?.hash ||
//     "Unavailable";

//   const getPreviousHash = (record) =>
//     record?.previous_hash ||
//     record?.prev_hash ||
//     record?.previous_record_hash ||
//     "Genesis";

//   const getRecordName = (record) =>
//     record?.declared_identity ||
//     record?.name ||
//     record?.full_name ||
//     "Identity record";

//   const getRecordDocumentNumber = (record) =>
//     record?.declared_doc_number ||
//     record?.document_number ||
//     record?.passport_number ||
//     record?.document_id ||
//     "Unavailable";

//   // ================= LOOKUP =================

//   const handleRecordLookup = async () => {
//     const query = lookupQuery.trim();

//     if (!query) {
//       setLookupResult(null);
//       setError("Enter a document number or ledger hash.");
//       return;
//     }

//     setLookupLoading(true);
//     setLookupResult(null);
//     setError("");

//     try {
//       // ==========================================
//       // DB #3 — BLOCKCHAIN LEDGER
//       // ==========================================

//       if (lookupSource === "ledger") {
//         const params = new URLSearchParams();

//         const isHash = /^[a-fA-F0-9]{64}$/.test(query);

//         if (isHash) {
//           params.set("record_hash", query);
//         } else {
//           params.set(
//             "document_number",
//             query.toUpperCase(),
//           );
//         }

//         const response = await fetch(
//           `${API_URL}/ledger/search?${params.toString()}`,
//         );

//         if (!response.ok) {
//           throw new Error(
//             `Ledger lookup failed: HTTP ${response.status}`,
//           );
//         }

//         const data = await response.json();

//         setLookupResult(data);
//         return;
//       }

//       // ==========================================
//       // DB #1 — ISSUANCE / BLACKLIST
//       // ==========================================

//       if (lookupSource === "issuance") {
//         const response = await fetch(
//           `${API_URL}/issuance/search?document_number=${encodeURIComponent(
//             query.toUpperCase(),
//           )}`,
//         );

//         if (!response.ok) {
//           throw new Error(
//             `Issuance DB lookup failed: HTTP ${response.status}`,
//           );
//         }

//         const data = await response.json();

//         setLookupResult(data);
//         return;
//       }

//       // ==========================================
//       // DB #2 — AUTHORITY REFERENCE
//       // ==========================================

//       if (lookupSource === "authority") {
//         const response = await fetch(
//           `${API_URL}/authority/search?document_number=${encodeURIComponent(
//             query.toUpperCase(),
//           )}`,
//         );

//         if (!response.ok) {
//           throw new Error(
//             `Authority DB lookup failed: HTTP ${response.status}`,
//           );
//         }

//         const data = await response.json();

//         setLookupResult(data);
//       }
//     } catch (err) {
//       console.error("Lookup error:", err);

//       setError(
//         err.message || "Lookup failed.",
//       );
//     } finally {
//       setLookupLoading(false);
//     }
//   };

//   const handleLookupKeyDown = (event) => {
//     if (event.key === "Enter") {
//       handleRecordLookup();
//     }
//   };

//   const handleUseCurrentDocument = () => {
//     const currentNumber =
//       getFieldValue("passport_number");

//     if (currentNumber !== "—") {
//       setLookupQuery(currentNumber);
//     }
//   };

//   // ================= RESET =================

//   const handleReset = () => {
//     setDocumentFile(null);
//     setSelfieFile(null);

//     setAnalyzing(false);
//     setAnalyzed(false);

//     setResult(null);
//     setError("");

//     setShowCamera(false);

//     setLookupQuery("");
//     setLookupResult(null);
//   };

//   // ================= BACKEND DATA =================

//   const ocr = result?.ocr;
//   const validation = result?.validation;
//   const tampering = result?.tampering;
//   const face = result?.face;
//   const authority = result?.authority_match;
//   const risk = result?.risk;
//   const ledger = result?.ledger;

//   // ================= OCR =================

//   const getFieldValue = (fieldName) =>
//     ocr?.extracted_fields?.[fieldName]?.value ?? "—";

//   // ================= VALIDATION =================

//   const validationPassed =
//     validation?.status === "success" &&
//     validation?.checksum_pass === true &&
//     validation?.text_mrz_match === true &&
//     validation?.expiry_valid === true &&
//     validation?.db_status === "clear" &&
//     (validation?.flags?.length ?? 0) === 0;

//   // ================= TAMPERING =================

//   const tamperFlag =
//     tampering?.overall_tamper_flag === true;

//   const tamperProbability =
//     tampering?.dl_tamper_probability ?? null;

//   // ================= FACE =================

//   const faceStatus = face?.status ?? null;

//   const faceScore =
//     face?.similarity ?? null;

//   // ================= AUTHORITY =================

//   const authorityStatus =
//     authority?.status ?? "not_available";

//   // ================= RISK =================

//   const riskScore =
//     risk?.risk_score ?? null;

//   const riskBand =
//     risk?.risk_band ?? null;

//   const recommendation =
//     risk?.final_recommendation ?? null;

//   const evidenceStrength =
//     risk?.evidence_strength ?? null;

//   // ================= LEDGER =================

//   const identityReuse =
//     ledger?.identity_reuse_flag === true;

//   // ================= HELPERS =================

//   const formatSimilarity = (score) => {
//     if (score === null || score === undefined) {
//       return "—";
//     }

//     const value = Number(score);

//     if (Number.isNaN(value)) {
//       return "—";
//     }

//     return value <= 1
//       ? `${Math.round(value * 100)}%`
//       : `${Math.round(value)}%`;
//   };

//   const getRiskClass = () => {
//     if (riskBand === "clear") return "clear";

//     if (riskBand === "secondary_check") {
//       return "secondary";
//     }

//     if (riskBand === "high_risk") {
//       return "high";
//     }

//     return "";
//   };

//   const getAuthorityDisplay = () => {
//     if (authorityStatus === "match") {
//       return "MATCH";
//     }

//     if (authorityStatus === "mismatch") {
//       return "MISMATCH";
//     }

//     return "NOT AVAILABLE";
//   };

//   // =====================================================
//   // RENDER
//   // =====================================================

//   return (
//     <div className="app">

//       {/* ================= GOV BANNER ================= */}

//       <div className="gov-banner">
//         <div className="gov-banner-inner">

//           <div className="gov-left">
//             <Landmark size={16} />

//             <span>
//               SMART INDIA HACKATHON • AI FOR SECURE DIGITAL IDENTITY
//             </span>
//           </div>

//           <div className="gov-right">
//             <LockKeyhole size={14} />
//             Privacy-aware identity screening
//           </div>

//         </div>
//       </div>

//       {/* ================= HEADER ================= */}

//       <header className="topbar">

//         <div>

//           <div className="title-row">

//             <Fingerprint
//               className="title-icon"
//               size={28}
//             />

//             <h1>
//               AI Based Fake Identity &amp;
//               Document Screening System
//             </h1>

//           </div>

//           <p>
//             Multi-layer AI verification for document
//             integrity, identity matching and fraud
//             risk assessment.
//           </p>

//         </div>

//         <div className="top-actions">

//           <button
//             className="activity-btn"
//             onClick={loadLedger}
//           >
//             <History size={17} />
//             Activity log
//           </button>

//           <button
//             className="scan-again"
//             onClick={handleReset}
//           >
//             <RotateCcw size={16} />
//             Scan again
//           </button>

//         </div>

//       </header>

//       {/* ================= PROGRESS ================= */}

//       <div className="progress">

//         <div className="progress-step active">
//           <span>01</span>
//           DOCUMENT CAPTURE
//         </div>

//         <div className="progress-line" />

//         <div
//           className={`progress-step ${
//             analyzed ? "active" : ""
//           }`}
//         >
//           <span>02</span>
//           IDENTITY CHECK
//         </div>

//         <div className="progress-line" />

//         <div
//           className={`progress-step ${
//             analyzed ? "active" : ""
//           }`}
//         >
//           <span>03</span>
//           DECISION
//         </div>

//       </div>

//       {/* ================= ERROR ================= */}

//       {error && (
//         <div className="error-banner">

//           <XCircle size={18} />

//           <span>{error}</span>

//           <button
//             onClick={() => setError("")}
//           >
//             ×
//           </button>

//         </div>
//       )}

//       {/* ================= MAIN GRID ================= */}

//       <main className="main-grid">

//         {/* ================= DOCUMENT ================= */}

//         <section className="capture-card card">

//           <div className="section-label">
//             <span>01</span>
//             DOCUMENT CAPTURE
//           </div>

//           <div className="card-heading">

//             <div>

//               <h2>
//                 Capture required documents
//               </h2>

//               <p>
//                 Upload a clear identity document
//                 for AI screening.
//               </p>

//             </div>

//             <span className="secure">
//               <ShieldCheck size={15} />
//               SECURE PROCESSING
//             </span>

//           </div>

//           {/* DOCUMENT TYPES */}

//           <div className="document-tabs">

//             {documents.map((doc) => (

//               <button
//                 key={doc}
//                 className={
//                   activeDocument === doc
//                     ? "tab active-tab"
//                     : "tab"
//                 }
//                 onClick={() => {
//                   setActiveDocument(doc);
//                   setAnalyzed(false);
//                   setResult(null);
//                   setError("");
//                 }}
//               >

//                 <FileCheck2 size={15} />

//                 <span>{doc}</span>

//               </button>

//             ))}

//           </div>

//           {/* DOCUMENT STATUS */}

//           <div className="capture-status">

//             <CheckCircle2 size={17} />

//             <div>

//               <strong>
//                 {documentFile
//                   ? documentFile.name
//                   : "Document upload required"}
//               </strong>

//               <span>
//                 {documentFile
//                   ? "Document image ready for screening."
//                   : "Upload a clear image of the identity document."}
//               </span>

//             </div>

//           </div>

//           {/* DOCUMENT PREVIEW */}

//           <div className="document-preview">

//             <div className="scan-corners" />

//             {documentPreview ? (

//               <img
//                 src={documentPreview}
//                 alt="Uploaded document"
//                 className="uploaded-document-preview"
//               />

//             ) : (

//               <div className="passport-placeholder">

//                 <div className="passport-header">
//                   <span>IDENTITY DOCUMENT</span>
//                   <span>AI SCREENING PREVIEW</span>
//                 </div>

//                 <div className="passport-body">

//                   <div className="fake-photo">
//                     <UserRound size={42} />
//                   </div>

//                   <div className="passport-lines">

//                     <div>
//                       <small>FULL NAME</small>
//                       <b>DOCUMENT PREVIEW</b>
//                     </div>

//                     <div>
//                       <small>NATIONALITY</small>
//                       <b>—</b>
//                     </div>

//                     <div className="mini-row">

//                       <div>
//                         <small>DATE OF BIRTH</small>
//                         <b>—</b>
//                       </div>

//                       <div>
//                         <small>DOCUMENT NO.</small>
//                         <b>—</b>
//                       </div>

//                     </div>

//                   </div>

//                 </div>

//                 <div className="mrz">
//                   Upload document image to begin
//                   automated verification
//                 </div>

//               </div>

//             )}

//             {analyzed && tamperFlag && (

//               <div className="suspicious-box">
//                 <span>AI FLAGGED</span>
//               </div>

//             )}

//           </div>

//           {/* ACTION BUTTONS */}

//           <div className="capture-actions">

//             <button
//               className="primary-btn"
//               onClick={() => setShowCamera(true)}
//             >
//               <Camera size={17} />
//               Capture Selfie
//             </button>

//             <label className="secondary-btn">

//               <Upload size={17} />
//               Upload Document

//               <input
//                 type="file"
//                 hidden
//                 accept="image/*"
//                 onChange={handleDocumentUpload}
//               />

//             </label>

//             <label className="secondary-btn">

//               <UserRound size={17} />
//               Upload Selfie

//               <input
//                 type="file"
//                 hidden
//                 accept="image/*"
//                 onChange={handleSelfieUpload}
//               />

//             </label>

//           </div>

//           {/* SELFIE STATUS */}

//           <div className="selfie-status-row">

//             <div className="capture-status selfie-status">

//               <CheckCircle2 size={17} />

//               <div>

//                 <strong>
//                   {selfieFile
//                     ? "Selfie ready"
//                     : "Live selfie required"}
//                 </strong>

//                 <span>
//                   {selfieFile
//                     ? selfieFile.name
//                     : "Capture or upload a selfie for face verification."}
//                 </span>

//               </div>

//             </div>

//             {selfiePreview && (

//               <img
//                 src={selfiePreview}
//                 className="selfie-thumbnail"
//                 alt="Selfie preview"
//               />

//             )}

//           </div>

//           <p className="helper-text">
//             <ShieldCheck size={14} />
//             Images are processed only for identity verification.
//           </p>

//         </section>

//         {/* ================= RIGHT ================= */}

//         <aside className="right-column">

//           {/* ================= VERIFICATION ================= */}

//           <section className="card verification-card">

//             <div className="card-top">

//               <div>

//                 <div className="section-label small-label">
//                   VERIFICATION RESULT
//                 </div>

//                 <h2>
//                   Identity confidence
//                 </h2>

//               </div>

//               <span className="safe-badge">

//                 <span />

//                 {analyzing
//                   ? "ANALYZING"
//                   : analyzed
//                     ? "COMPLETE"
//                     : "READY"}

//               </span>

//             </div>

//             {/* CONFIDENCE */}

//             <div className="confidence">

//               <div className="confidence-circle">

//                 <strong>
//                   {faceScore !== null
//                     ? formatSimilarity(faceScore)
//                         .replace("%", "")
//                     : "—"}
//                 </strong>

//                 {faceScore !== null && (
//                   <small>%</small>
//                 )}

//               </div>

//               <div>

//                 <h3>
//                   {analyzing
//                     ? "Screening in progress"
//                     : analyzed
//                       ? "Screening complete"
//                       : "Awaiting verification"}
//                 </h3>

//                 <p>
//                   {analyzing
//                     ? "Running all verification modules."
//                     : analyzed
//                       ? `Recommendation: ${
//                           recommendation
//                             ? recommendation
//                                 .replace(/_/g, " ")
//                                 .toUpperCase()
//                             : "REVIEW"
//                         }`
//                       : "Upload document and provide a selfie to begin."}
//                 </p>

//               </div>

//             </div>

//             {/* MODULE RESULTS */}

//             <div className="checks">

//               <VerificationRow
//                 icon={<FileCheck2 size={17} />}
//                 title="Document Integrity"
//                 subtitle={
//                   validation?.status === "failed"
//                     ? "Validation could not complete"
//                     : "Format and rule validation"
//                 }
//                 status={
//                   !analyzed
//                     ? "—"
//                     : validationPassed
//                       ? "PASS"
//                       : "REVIEW"
//                 }
//                 type={
//                   !analyzed
//                     ? "neutral"
//                     : validationPassed
//                       ? "success"
//                       : "warning"
//                 }
//               />

//               <VerificationRow
//                 icon={<Search size={17} />}
//                 title="OCR Extraction"
//                 subtitle={
//                   ocr?.status === "success"
//                     ? "Identity fields extracted"
//                     : "OCR extraction failed"
//                 }
//                 status={
//                   !analyzed
//                     ? "—"
//                     : ocr?.status === "success"
//                       ? "COMPLETE"
//                       : "FAILED"
//                 }
//                 type={
//                   !analyzed
//                     ? "neutral"
//                     : ocr?.status === "success"
//                       ? "success"
//                       : "warning"
//                 }
//               />

//               <VerificationRow
//                 icon={<ScanLine size={17} />}
//                 title="MRZ Validation"
//                 subtitle={
//                   validation?.text_mrz_match === true
//                     ? "Checksum and field consistency passed"
//                     : "MRZ requires review"
//                 }
//                 status={
//                   !analyzed
//                     ? "—"
//                     : validation?.text_mrz_match
//                       ? "PASS"
//                       : "REVIEW"
//                 }
//                 type={
//                   !analyzed
//                     ? "neutral"
//                     : validation?.text_mrz_match
//                       ? "success"
//                       : "warning"
//                 }
//               />

//               <VerificationRow
//                 icon={<AlertTriangle size={17} />}
//                 title="Tampering Detection"
//                 subtitle={
//                   analyzed &&
//                   tamperProbability !== null
//                     ? `DL probability: ${Math.round(
//                         tamperProbability * 100,
//                       )}% • ELA: ${
//                         tampering?.ela_score?.toFixed(4) ??
//                         "—"
//                       }`
//                     : "Digital manipulation screening"
//                 }
//                 status={
//                   !analyzed
//                     ? "—"
//                     : tamperFlag
//                       ? "FLAGGED"
//                       : "CLEAN"
//                 }
//                 type={
//                   !analyzed
//                     ? "neutral"
//                     : tamperFlag
//                       ? "warning"
//                       : "success"
//                 }
//               />

//               <VerificationRow
//                 icon={<UserRound size={17} />}
//                 title="Face Verification"
//                 subtitle={
//                   faceStatus === "no_face_detected"
//                     ? face?.face_detected_in_document
//                       ? "Selfie/document comparison unavailable"
//                       : "No usable document portrait detected"
//                     : "Document portrait vs live selfie"
//                 }
//                 status={
//                   !analyzed
//                     ? "—"
//                     : faceStatus === "match"
//                       ? formatSimilarity(faceScore)
//                       : faceStatus === "mismatch"
//                         ? "MISMATCH"
//                         : "NO FACE"
//                 }
//                 type={
//                   !analyzed
//                     ? "neutral"
//                     : faceStatus === "match"
//                       ? "success"
//                       : "warning"
//                 }
//               />

//               <VerificationRow
//                 icon={<Database size={17} />}
//                 title="Authority Reference"
//                 subtitle={
//                   authorityStatus === "not_available"
//                     ? "Independent authority reference unavailable"
//                     : "Independent authority comparison"
//                 }
//                 status={
//                   !analyzed
//                     ? "—"
//                     : getAuthorityDisplay()
//                 }
//                 type={
//                   !analyzed
//                     ? "neutral"
//                     : authorityStatus === "match"
//                       ? "success"
//                       : authorityStatus === "mismatch"
//                         ? "warning"
//                         : "neutral"
//                 }
//               />

//               {analyzed && (

//                 <VerificationRow
//                   icon={
//                     identityReuse ? (
//                       <ShieldAlert size={17} />
//                     ) : (
//                       <History size={17} />
//                     )
//                   }
//                   title="Identity Reuse Detection"
//                   subtitle="Historical ledger identity search"
//                   status={
//                     identityReuse
//                       ? "FLAGGED"
//                       : "CLEAR"
//                   }
//                   type={
//                     identityReuse
//                       ? "warning"
//                       : "success"
//                   }
//                 />

//               )}

//             </div>

//             {!analyzed && (

//               <button
//                 className="bottom-primary"
//                 onClick={handleAnalyze}
//                 disabled={analyzing}
//               >

//                 <ScanLine size={17} />

//                 {analyzing
//                   ? "Running AI Screening..."
//                   : "Analyze Document"}

//               </button>

//             )}

//           </section>

//           {/* ================= THREE DATABASE LOOKUP ================= */}

//           <section className="card trusted-card">

//             <div className="card-top">

//               <div>

//                 <div className="section-label small-label">
//                   THREE-SOURCE VERIFICATION
//                 </div>

//                 <h2>
//                   Database lookup
//                 </h2>

//               </div>

//               <Database size={18} />

//             </div>

//             {/* SOURCE SELECTOR */}

//             <div className="lookup-source-tabs">

//               <button
//                 className={
//                   lookupSource === "issuance"
//                     ? "lookup-source active"
//                     : "lookup-source"
//                 }
//                 onClick={() => {
//                   setLookupSource("issuance");
//                   setLookupResult(null);
//                   setError("");
//                 }}
//               >
//                 <strong>DB #1</strong>
//                 <span>Issuance</span>
//               </button>

//               <button
//                 className={
//                   lookupSource === "authority"
//                     ? "lookup-source active"
//                     : "lookup-source"
//                 }
//                 onClick={() => {
//                   setLookupSource("authority");
//                   setLookupResult(null);
//                   setError("");
//                 }}
//               >
//                 <strong>DB #2</strong>
//                 <span>Authority</span>
//               </button>

//               <button
//                 className={
//                   lookupSource === "ledger"
//                     ? "lookup-source active"
//                     : "lookup-source"
//                 }
//                 onClick={() => {
//                   setLookupSource("ledger");
//                   setLookupResult(null);
//                   setError("");
//                 }}
//               >
//                 <strong>DB #3</strong>
//                 <span>Ledger</span>
//               </button>

//             </div>

//             {/* SOURCE DESCRIPTION */}

//             <div className="lookup-source-description">

//               {lookupSource === "issuance" && (
//                 <>
//                   <strong>
//                     DB #1 — Issuance / Blacklist
//                   </strong>

//                   <span>
//                     Official-style issuance reference used
//                     to check document status.
//                   </span>
//                 </>
//               )}

//               {lookupSource === "authority" && (
//                 <>
//                   <strong>
//                     DB #2 — Authority Reference
//                   </strong>

//                   <span>
//                     Independent authority reference record
//                     and reference-photo availability.
//                   </span>
//                 </>
//               )}

//               {lookupSource === "ledger" && (
//                 <>
//                   <strong>
//                     DB #3 — Blockchain Audit Ledger
//                   </strong>

//                   <span>
//                     Historical screening records, hashes,
//                     risk decisions and audit evidence.
//                   </span>
//                 </>
//               )}

//             </div>

//             {/* SEARCH */}

//             <div className="record-search-row">

//               <div className="search-box lookup-search-box">

//                 <Search size={16} />

//                 <input
//                   value={lookupQuery}
//                   onChange={(e) =>
//                     setLookupQuery(e.target.value)
//                   }
//                   onKeyDown={handleLookupKeyDown}
//                   placeholder={
//                     lookupSource === "ledger"
//                       ? "Document number or ledger hash"
//                       : "Document number"
//                   }
//                 />

//               </div>

//               <button
//                 className="lookup-btn"
//                 onClick={handleRecordLookup}
//                 disabled={lookupLoading}
//               >
//                 {lookupLoading
//                   ? "..."
//                   : "Search"}
//               </button>

//             </div>

//             {analyzed && (

//               <button
//                 className="current-doc-btn"
//                 onClick={handleUseCurrentDocument}
//               >
//                 <FileCheck2 size={13} />
//                 Use current document number
//               </button>

//             )}

//             {/* LOOKUP RESULT */}

//             {lookupResult && (

//               <LookupResult
//                 source={lookupSource}
//                 result={lookupResult}
//                 getRecordHash={getRecordHash}
//                 getPreviousHash={getPreviousHash}
//                 getRecordDocumentNumber={
//                   getRecordDocumentNumber
//                 }
//                 getRecordName={getRecordName}
//                 onOpenLedger={(record) =>
//                   setSelectedLedgerRecord(record)
//                 }
//               />

//             )}

//           </section>

//         </aside>

//       </main>

//       {/* ================= BOTTOM ================= */}

//       <section className="bottom-grid">

//         {/* EXTRACTED INFO */}

//         <div className="card extracted-card">

//           <div className="section-label small-label">
//             EXTRACTED INFORMATION
//           </div>

//           <div className="info-grid">

//             <Info
//               label="Full name"
//               value={getFieldValue("name")}
//             />

//             <Info
//               label="Nationality"
//               value={getFieldValue("nationality")}
//             />

//             <Info
//               label="Date of birth"
//               value={getFieldValue("dob")}
//             />

//             <Info
//               label="Document number"
//               value={getFieldValue("passport_number")}
//             />

//             <Info
//               label="Expiry date"
//               value={getFieldValue("expiry")}
//             />

//             <Info
//               label="Gender"
//               value={getFieldValue("gender")}
//             />

//           </div>

//         </div>

//         {/* RISK */}

//         <div className="card risk-card">

//           <div className="section-label small-label">
//             SCREENING DECISION
//           </div>

//           <div className="risk-header">

//             <div>

//               <span>Risk score</span>

//               <strong>
//                 {riskScore !== null
//                   ? Math.round(Number(riskScore))
//                   : "—"}
//               </strong>

//               <small>/ 100</small>

//             </div>

//             <span
//               className={`risk-badge ${getRiskClass()}`}
//             >
//               {riskBand
//                 ? riskBand
//                     .replace(/_/g, " ")
//                     .toUpperCase()
//                 : "AWAITING ANALYSIS"}
//             </span>

//           </div>

//           {analyzed ? (

//             <div className="risk-reasons">

//               <div>
//                 {tamperFlag ? (
//                   <AlertTriangle size={15} />
//                 ) : (
//                   <CheckCircle2 size={15} />
//                 )}

//                 Tampering:{" "}
//                 {tamperVerdict(
//                   tampering?.tamper_verdict,
//                 )}
//               </div>

//               <div>
//                 {validationPassed ? (
//                   <CheckCircle2 size={15} />
//                 ) : (
//                   <AlertTriangle size={15} />
//                 )}

//                 Validation:{" "}
//                 {validationPassed
//                   ? "Passed"
//                   : "Requires review"}
//               </div>

//               <div>
//                 <Eye size={15} />

//                 Evidence strength:{" "}
//                 {evidenceStrength !== null
//                   ? `${Math.round(
//                       Number(evidenceStrength) * 100,
//                     )}%`
//                   : "—"}
//               </div>

//               <div>
//                 <Database size={15} />

//                 Authority:{" "}
//                 {getAuthorityDisplay()}
//               </div>

//               {identityReuse && (
//                 <div>
//                   <AlertTriangle size={15} />

//                   Identity reuse detected
//                 </div>
//               )}

//             </div>

//           ) : (

//             <p className="empty-risk">
//               Complete document analysis to generate
//               the screening decision.
//             </p>

//           )}

//         </div>

//       </section>

//       {/* ================= LEDGER SUMMARY ================= */}

//       {analyzed && ledger && (

//         <section className="ledger-summary">

//           <div className="ledger-summary-inner">

//             <div>

//               <div className="section-label">
//                 DB #3 • BLOCKCHAIN AUDIT TRAIL
//               </div>

//               <strong>
//                 Screening record secured
//               </strong>

//               <span>
//                 Hash:{" "}
//                 {getRecordHash(ledger).slice(
//                   0,
//                   28,
//                 )}
//                 ...
//               </span>

//             </div>

//             <button onClick={loadLedger}>

//               <Database size={16} />

//               View ledger

//             </button>

//           </div>

//         </section>

//       )}

//       {/* ================= FOOTER ================= */}

//       <footer>

//         <div>
//           <ShieldCheck size={15} />

//           AI-assisted screening • Final decision
//           remains with authorized personnel
//         </div>

//         <div>

//           <Clock3 size={14} />

//           {analyzing
//             ? "Screening pipeline running"
//             : "System ready"}

//         </div>

//       </footer>

//       {/* ================= CAMERA ================= */}

//       {showCamera && (

//         <div
//           className="camera-overlay"
//           onClick={() => setShowCamera(false)}
//         >

//           <div
//             className="camera-modal"
//             onClick={(e) =>
//               e.stopPropagation()
//             }
//           >

//             <CameraPanel
//               onCapture={handleSelfieCapture}
//               onClose={() =>
//                 setShowCamera(false)
//               }
//             />

//           </div>

//         </div>

//       )}

//       {/* ================= ACTIVITY LOG / DB #3 ================= */}

//       {showActivity && (

//         <div
//           className="activity-overlay"
//           onClick={() =>
//             setShowActivity(false)
//           }
//         >

//           <div
//             className="activity-modal"
//             onClick={(e) =>
//               e.stopPropagation()
//             }
//           >

//             <div className="activity-header">

//               <div>

//                 <div className="section-label">
//                   DB #3 • BLOCKCHAIN LEDGER
//                 </div>

//                 <h2>
//                   Screening activity
//                 </h2>

//               </div>

//               <button
//                 onClick={() =>
//                   setShowActivity(false)
//                 }
//               >
//                 ×
//               </button>

//             </div>

//             {loadingLedger ? (

//               <div className="ledger-loading">
//                 Loading ledger records...
//               </div>

//             ) : ledgerRecords.length === 0 ? (

//               <div className="ledger-loading">
//                 No ledger records found.
//               </div>

//             ) : (

//               <div className="ledger-list">

//                 {ledgerRecords
//                   .slice()
//                   .reverse()
//                   .map((record, index) => (

//                     <button
//                       type="button"
//                       className="ledger-item"
//                       key={
//                         getRecordHash(record) +
//                         String(index)
//                       }
//                       onClick={() =>
//                         setSelectedLedgerRecord(record)
//                       }
//                     >

//                       <div className="ledger-index">
//                         #
//                         {record.index !== undefined
//                           ? Number(record.index) + 1
//                           : ledgerRecords.length -
//                             index}
//                       </div>

//                       <div className="ledger-content">

//                         <strong>
//                           {getRecordName(record)}
//                         </strong>

//                         <span>
//                           {getRecordDocumentNumber(record)}
//                           {" • "}
//                           Risk{" "}
//                           {record.risk_result
//                             ?.risk_score ?? "—"}
//                         </span>

//                         <span>
//                           Authority:{" "}
//                           {record.authority_match_status ??
//                             "not_available"}
//                         </span>

//                         <span>
//                           Identity reuse:{" "}
//                           {record.identity_reuse_flag
//                             ? "FLAGGED"
//                             : "CLEAR"}
//                         </span>

//                         <span>
//                           {record.timestamp ||
//                             "Timestamp unavailable"}
//                         </span>

//                         <code>
//                           {getRecordHash(record)}
//                         </code>

//                       </div>

//                       <ChevronRight size={18} />

//                     </button>

//                   ))}

//               </div>

//             )}

//           </div>

//         </div>

//       )}

//       {/* ================= LEDGER DETAIL ================= */}

//       {selectedLedgerRecord && (

//         <div
//           className="activity-overlay"
//           onClick={() =>
//             setSelectedLedgerRecord(null)
//           }
//         >

//           <div
//             className="ledger-detail-modal"
//             onClick={(e) =>
//               e.stopPropagation()
//             }
//           >

//             <div className="activity-header">

//               <div>

//                 <div className="section-label">
//                   DB #3 • BLOCKCHAIN RECORD
//                 </div>

//                 <h2>
//                   Immutable screening record
//                 </h2>

//               </div>

//               <button
//                 onClick={() =>
//                   setSelectedLedgerRecord(null)
//                 }
//               >
//                 ×
//               </button>

//             </div>

//             <div className="ledger-detail-grid">

//               <DetailItem
//                 label="Record index"
//                 value={
//                   selectedLedgerRecord.index ??
//                   "—"
//                 }
//               />

//               <DetailItem
//                 label="Identity"
//                 value={getRecordName(
//                   selectedLedgerRecord,
//                 )}
//               />

//               <DetailItem
//                 label="Document number"
//                 value={getRecordDocumentNumber(
//                   selectedLedgerRecord,
//                 )}
//               />

//               <DetailItem
//                 label="Timestamp"
//                 value={
//                   selectedLedgerRecord.timestamp ||
//                   "—"
//                 }
//               />

//               <DetailItem
//                 label="Risk score"
//                 value={
//                   selectedLedgerRecord.risk_result
//                     ?.risk_score ?? "—"
//                 }
//               />

//               <DetailItem
//                 label="Risk band"
//                 value={
//                   selectedLedgerRecord.risk_result
//                     ?.risk_band
//                     ? selectedLedgerRecord.risk_result
//                         .risk_band
//                         .replace(/_/g, " ")
//                         .toUpperCase()
//                     : "—"
//                 }
//               />

//               <DetailItem
//                 label="Recommendation"
//                 value={
//                   selectedLedgerRecord.risk_result
//                     ?.final_recommendation
//                     ? selectedLedgerRecord.risk_result
//                         .final_recommendation
//                         .replace(/_/g, " ")
//                         .toUpperCase()
//                     : "—"
//                 }
//               />

//               <DetailItem
//                 label="Authority status"
//                 value={
//                   selectedLedgerRecord.authority_match_status ??
//                   "not_available"
//                 }
//               />

//               <DetailItem
//                 label="Authority similarity"
//                 value={formatSimilarity(
//                   selectedLedgerRecord.authority_match_similarity,
//                 )}
//               />

//               <DetailItem
//                 label="Identity reuse"
//                 value={
//                   selectedLedgerRecord.identity_reuse_flag
//                     ? "FLAGGED"
//                     : "NOT DETECTED"
//                 }
//               />

//               <DetailItem
//                 label="Reuse matches"
//                 value={
//                   Array.isArray(
//                     selectedLedgerRecord.identity_reuse_matches,
//                   )
//                     ? selectedLedgerRecord
//                         .identity_reuse_matches.length
//                     : 0
//                 }
//               />

//             </div>

//             <div className="hash-section">

//               <span>
//                 Record Hash
//               </span>

//               <code>
//                 {getRecordHash(
//                   selectedLedgerRecord,
//                 )}
//               </code>

//             </div>

//             <div className="hash-section">

//               <span>
//                 Previous Hash
//               </span>

//               <code>
//                 {getPreviousHash(
//                   selectedLedgerRecord,
//                 )}
//               </code>

//             </div>

//             <div className="ledger-detail-actions">

//               <button
//                 className="secondary-btn"
//                 onClick={() =>
//                   setSelectedLedgerRecord(null)
//                 }
//               >
//                 Close
//               </button>

//             </div>

//           </div>

//         </div>

//       )}

//     </div>
//   );
// }

// // =====================================================
// // LOOKUP RESULT
// // =====================================================

// function LookupResult({
//   source,
//   result,
//   getRecordHash,
//   getRecordDocumentNumber,
//   getRecordName,
//   onOpenLedger,
// }) {
//   if (!result || result.found === false) {
//     return (
//       <div className="lookup-empty">
//         <XCircle size={15} />
//         <span>No matching record found.</span>
//       </div>
//     );
//   }

//   // ===================================================
//   // DB #3 — BLOCKCHAIN LEDGER
//   // ===================================================

//   if (source === "ledger") {
//     const records = Array.isArray(result.records)
//       ? result.records
//       : result.record
//         ? [result.record]
//         : [];

//     if (records.length === 0) {
//       return (
//         <div className="lookup-empty">
//           <XCircle size={15} />
//           <span>No ledger record found.</span>
//         </div>
//       );
//     }

//     return (
//       <div className="lookup-results">

//         <div className="lookup-result-heading">
//           <div>
//             <span className="lookup-result-kicker">
//               DB #3
//             </span>
//             <strong>Blockchain Ledger</strong>
//           </div>

//           <span className="lookup-result-count">
//             {records.length} record
//             {records.length !== 1 ? "s" : ""}
//           </span>
//         </div>

//         {records.map((record, index) => (
//           <button
//             type="button"
//             className="lookup-record"
//             key={
//               getRecordHash(record) +
//               String(index)
//             }
//             onClick={() => onOpenLedger(record)}
//           >
//             <div className="lookup-record-number">
//               #{record.index !== undefined
//                 ? Number(record.index) + 1
//                 : index + 1}
//             </div>

//             <div className="lookup-record-main">

//               <div className="lookup-record-title">
//                 <strong>
//                   {getRecordName(record)}
//                 </strong>

//                 <span className="lookup-record-status">
//                   RISK{" "}
//                   {record.risk_result
//                     ?.risk_score ?? "—"}
//                 </span>
//               </div>

//               <div className="lookup-record-meta">
//                 <span>
//                   Document{" "}
//                   <b>
//                     {getRecordDocumentNumber(record)}
//                   </b>
//                 </span>

//                 <span>
//                   Authority{" "}
//                   <b>
//                     {record.authority_match_status ??
//                       "not available"}
//                   </b>
//                 </span>

//                 <span>
//                   Reuse{" "}
//                   <b>
//                     {record.identity_reuse_flag
//                       ? "FLAGGED"
//                       : "CLEAR"}
//                   </b>
//                 </span>
//               </div>

//               <code>
//                 {getRecordHash(record).slice(0, 28)}
//                 ...
//               </code>

//             </div>

//             <ChevronRight size={17} />
//           </button>
//         ))}

//       </div>
//     );
//   }

//   // ===================================================
//   // DB #1 — ISSUANCE
//   // ===================================================

//   if (source === "issuance") {
//     const status = result.status || "unknown";

//     return (
//       <div className="lookup-database-result">

//         <div className="lookup-result-heading">

//           <div>
//             <span className="lookup-result-kicker">
//               DB #1
//             </span>

//             <strong>
//               Issuance / Blacklist
//             </strong>
//           </div>

//           <span
//             className={`db-status ${
//               status === "clear"
//                 ? "clear"
//                 : "warning"
//             }`}
//           >
//             {status.toUpperCase()}
//           </span>

//         </div>

//         <div className="lookup-data-grid">

//           <div className="lookup-data-field">
//             <span>Document number</span>
//             <strong>
//               {result.document_number ||
//                 "Unavailable"}
//             </strong>
//           </div>

//           <div className="lookup-data-field">
//             <span>Issuance status</span>
//             <strong>
//               {status.toUpperCase()}
//             </strong>
//           </div>

//           <div className="lookup-data-field full-width">
//             <span>Issued to</span>
//             <strong>
//               {result.issued_to ||
//                 "No issuing identity available"}
//             </strong>
//           </div>

//         </div>

//         <div className="lookup-result-source-note">
//           {result.source_name ||
//             "Mock DB #1 - Issuance"}
//         </div>

//       </div>
//     );
//   }

//   // ===================================================
//   // DB #2 — AUTHORITY
//   // ===================================================

//   return (
//     <div className="lookup-database-result">

//       <div className="lookup-result-heading">

//         <div>
//           <span className="lookup-result-kicker">
//             DB #2
//           </span>

//           <strong>
//             Authority Reference
//           </strong>
//         </div>

//         <span
//           className={`db-status ${
//             result.reference_available
//               ? "clear"
//               : "warning"
//           }`}
//         >
//           {result.reference_available
//             ? "AVAILABLE"
//             : "NOT AVAILABLE"}
//         </span>

//       </div>

//       <div className="lookup-data-grid">

//         <div className="lookup-data-field">
//           <span>Document number</span>
//           <strong>
//             {result.document_number ||
//               "Unavailable"}
//           </strong>
//         </div>

//         <div className="lookup-data-field">
//           <span>Reference available</span>
//           <strong>
//             {result.reference_available
//               ? "YES"
//               : "NO"}
//           </strong>
//         </div>

//         <div className="lookup-data-field">
//           <span>Reference source</span>
//           <strong>
//             {result.reference_source ||
//               "Unavailable"}
//           </strong>
//         </div>

//         <div className="lookup-data-field">
//           <span>Reference file</span>
//           <strong>
//             {result.reference_file ||
//               "No reference file"}
//           </strong>
//         </div>

//       </div>

//       <div className="lookup-result-source-note">
//         {result.source_name ||
//           "Mock DB #2 - Authority Reference"}
//       </div>

//     </div>
//   );
// }

// // =====================================================
// // VERIFICATION ROW
// // =====================================================

// function VerificationRow({
//   icon,
//   title,
//   subtitle,
//   status,
//   type,
// }) {
//   return (
//     <div className="verification-row">

//       <div className={`check-icon ${type}`}>
//         {icon}
//       </div>

//       <div className="check-text">

//         <strong>{title}</strong>

//         <span>{subtitle}</span>

//       </div>

//       <span className={`check-status ${type}`}>

//         {type === "success" && (
//           <CheckCircle2 size={14} />
//         )}

//         {type === "warning" && (
//           <AlertTriangle size={14} />
//         )}

//         {status}

//       </span>

//     </div>
//   );
// }

// // =====================================================
// // INFO
// // =====================================================

// function Info({
//   label,
//   value,
// }) {
//   return (
//     <div className="info-item">

//       <span>{label}</span>

//       <strong>{value}</strong>

//     </div>
//   );
// }

// // =====================================================
// // DETAIL
// // =====================================================

// function DetailItem({
//   label,
//   value,
// }) {
//   return (
//     <div className="detail-item">

//       <span>{label}</span>

//       <strong>
//         {String(value)}
//       </strong>

//     </div>
//   );
// }

// // =====================================================
// // TAMPER VERDICT
// // =====================================================

// function tamperVerdict(value) {
//   if (!value) return "Unknown";

//   return value
//     .replace(/_/g, " ")
//     .toUpperCase();
// }

// export default App;

import { useMemo, useState } from "react";
import CameraPanel from "./CameraPanel";

import {
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
  Landmark,
  LockKeyhole,
  Eye,
  History,
  Fingerprint,
  ChevronRight,
  ShieldAlert,
} from "lucide-react";

import "./App.css";

const API_URL = "http://127.0.0.1:8000";

const BACKEND_DOC_TYPES = {
  Passport: "passport",
  Visa: "visa",
  "National ID": "national_id",
  "Driving License": "driving_license",
};

function App() {
  const [activeDocument, setActiveDocument] = useState("Passport");

  const [documentFile, setDocumentFile] = useState(null);
  const [selfieFile, setSelfieFile] = useState(null);

  const [analyzing, setAnalyzing] = useState(false);
  const [analyzed, setAnalyzed] = useState(false);

  const [showCamera, setShowCamera] = useState(false);

  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  // ================= LEDGER =================

  const [showActivity, setShowActivity] = useState(false);
  const [ledgerRecords, setLedgerRecords] = useState([]);
  const [loadingLedger, setLoadingLedger] = useState(false);

  const [selectedLedgerRecord, setSelectedLedgerRecord] =
    useState(null);

  // ================= IDENTITY REUSE ALERT =================

  const [showIdentityReuseAlert, setShowIdentityReuseAlert] =
    useState(false);

  const [identityReuseRecords, setIdentityReuseRecords] =
    useState([]);

  // ================= LOOKUP =================

  const [lookupSource, setLookupSource] = useState("issuance");
  const [lookupQuery, setLookupQuery] = useState("");
  const [lookupResult, setLookupResult] = useState(null);
  const [lookupLoading, setLookupLoading] = useState(false);

  const documents = [
    "Passport",
    "Visa",
    "National ID",
    "Driving License",
  ];

  // ================= PREVIEWS =================

  const documentPreview = useMemo(
    () =>
      documentFile
        ? URL.createObjectURL(documentFile)
        : null,
    [documentFile],
  );

  const selfiePreview = useMemo(
    () =>
      selfieFile
        ? URL.createObjectURL(selfieFile)
        : null,
    [selfieFile],
  );

  // ================= FILE HANDLERS =================

  const handleDocumentUpload = (event) => {
    const file = event.target.files?.[0];

    if (!file) return;

    setDocumentFile(file);
    setAnalyzed(false);
    setResult(null);
    setError("");
  };

  const handleSelfieUpload = (event) => {
    const file = event.target.files?.[0];

    if (!file) return;

    setSelfieFile(file);
    setAnalyzed(false);
    setResult(null);
    setError("");
  };

  const handleSelfieCapture = (file) => {
    if (!file) return;

    setSelfieFile(file);
    setAnalyzed(false);
    setResult(null);
    setError("");
    setShowCamera(false);
  };

  // ================= SCREENING =================

  const handleAnalyze = async () => {
    setError("");

    if (!documentFile) {
      setError("Please upload a document image first.");
      return;
    }

    if (!selfieFile) {
      setError("Please capture or upload a selfie first.");
      return;
    }

    setAnalyzing(true);
    setAnalyzed(false);
    setResult(null);

    // Close any old identity reuse alert before a new scan.
    setShowIdentityReuseAlert(false);
    setIdentityReuseRecords([]);

    try {
      const formData = new FormData();

      formData.append("doc_image", documentFile);
      formData.append("live_selfie", selfieFile);

      formData.append(
        "doc_type",
        BACKEND_DOC_TYPES[activeDocument] ||
          activeDocument
            .toLowerCase()
            .replace(/\s+/g, "_"),
      );

      const response = await fetch(`${API_URL}/screen`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        let message =
          `Backend returned HTTP ${response.status}.`;

        try {
          const body = await response.json();

          if (body.detail) {
            message =
              typeof body.detail === "string"
                ? body.detail
                : JSON.stringify(body.detail);
          }
        } catch {
          // Keep HTTP error.
        }

        throw new Error(message);
      }

      const data = await response.json();

      console.log("Screening result:", data);

      setResult(data);
      setAnalyzed(true);

      // ============================================
      // IDENTITY REUSE DETECTION
      // ============================================

      const reuseFlag =
        data?.ledger?.identity_reuse_flag === true;

      const reuseIndexes =
        Array.isArray(
          data?.ledger?.identity_reuse_matches,
        )
          ? data.ledger.identity_reuse_matches
          : [];

      if (reuseFlag && reuseIndexes.length > 0) {
        try {
          /*
            The backend returns the historical ledger
            indexes where the current embedding matched.

            Example:
              [3, 6, 8, 9, 10, 11, 12, 13, 15]

            Fetch DB #3 and resolve those indexes into
            the complete historical ledger records.
          */

          const ledgerResponse = await fetch(
            `${API_URL}/ledger`,
          );

          if (!ledgerResponse.ok) {
            throw new Error(
              `Ledger returned HTTP ${ledgerResponse.status}`,
            );
          }

          const ledgerData =
            await ledgerResponse.json();

          const allRecords = Array.isArray(ledgerData)
            ? ledgerData
            : Array.isArray(ledgerData.records)
              ? ledgerData.records
              : [];

          const matchedRecords =
            allRecords.filter((record) =>
              reuseIndexes.includes(
                Number(record?.index),
              ),
            );

          /*
            Keep the alert visible even if record resolution
            fails. The popup can still show the matching indexes.
          */
          setIdentityReuseRecords(
            matchedRecords,
          );

          setShowIdentityReuseAlert(true);
        } catch (reuseError) {
          console.error(
            "Unable to load identity reuse records:",
            reuseError,
          );

          /*
            The flag itself is already confirmed by the
            screening response, so still show the alert.
          */
          setIdentityReuseRecords([]);
          setShowIdentityReuseAlert(true);
        }
      } else {
        setIdentityReuseRecords([]);
        setShowIdentityReuseAlert(false);
      }
    } catch (err) {
      console.error(err);

      setError(
        err.message ||
          "Unable to connect to the screening backend.",
      );
    } finally {
      setAnalyzing(false);
    }
  };

  // ================= LEDGER =================

  const loadLedger = async () => {
    setShowActivity(true);
    setLoadingLedger(true);
    setError("");

    try {
      const response = await fetch(
        `${API_URL}/ledger`,
      );

      if (!response.ok) {
        throw new Error(
          `Unable to load blockchain ledger: HTTP ${response.status}`,
        );
      }

      const data = await response.json();

      setLedgerRecords(
        Array.isArray(data)
          ? data
          : Array.isArray(data.records)
            ? data.records
            : [],
      );
    } catch (err) {
      console.error(err);

      setError(
        err.message ||
          "Unable to load blockchain activity.",
      );
    } finally {
      setLoadingLedger(false);
    }
  };

  const getRecordHash = (record) =>
    record?.record_hash ||
    record?.hash ||
    "Unavailable";

  const getPreviousHash = (record) =>
    record?.previous_hash ||
    record?.prev_hash ||
    record?.previous_record_hash ||
    "Genesis";

  const getRecordName = (record) =>
    record?.declared_identity ||
    record?.name ||
    record?.full_name ||
    "Identity record";

  const getRecordDocumentNumber = (record) =>
    record?.declared_doc_number ||
    record?.document_number ||
    record?.passport_number ||
    record?.document_id ||
    "Unavailable";

  // ================= LOOKUP =================

  const handleRecordLookup = async () => {
    const query = lookupQuery.trim();

    if (!query) {
      setLookupResult(null);
      setError(
        "Enter a document number or ledger hash.",
      );
      return;
    }

    setLookupLoading(true);
    setLookupResult(null);
    setError("");

    try {
      // ==========================================
      // DB #3 — BLOCKCHAIN LEDGER
      // ==========================================

      if (lookupSource === "ledger") {
        const params = new URLSearchParams();

        const isHash =
          /^[a-fA-F0-9]{64}$/.test(query);

        if (isHash) {
          params.set("record_hash", query);
        } else {
          params.set(
            "document_number",
            query.toUpperCase(),
          );
        }

        const response = await fetch(
          `${API_URL}/ledger/search?${params.toString()}`,
        );

        if (!response.ok) {
          throw new Error(
            `Ledger lookup failed: HTTP ${response.status}`,
          );
        }

        const data = await response.json();

        setLookupResult(data);
        return;
      }

      // ==========================================
      // DB #1 — ISSUANCE / BLACKLIST
      // ==========================================

      if (lookupSource === "issuance") {
        const response = await fetch(
          `${API_URL}/issuance/search?document_number=${encodeURIComponent(
            query.toUpperCase(),
          )}`,
        );

        if (!response.ok) {
          throw new Error(
            `Issuance DB lookup failed: HTTP ${response.status}`,
          );
        }

        const data = await response.json();

        setLookupResult(data);
        return;
      }

      // ==========================================
      // DB #2 — AUTHORITY REFERENCE
      // ==========================================

      if (lookupSource === "authority") {
        const response = await fetch(
          `${API_URL}/authority/search?document_number=${encodeURIComponent(
            query.toUpperCase(),
          )}`,
        );

        if (!response.ok) {
          throw new Error(
            `Authority DB lookup failed: HTTP ${response.status}`,
          );
        }

        const data = await response.json();

        setLookupResult(data);
      }
    } catch (err) {
      console.error("Lookup error:", err);

      setError(
        err.message || "Lookup failed.",
      );
    } finally {
      setLookupLoading(false);
    }
  };

  const handleLookupKeyDown = (event) => {
    if (event.key === "Enter") {
      handleRecordLookup();
    }
  };

  const handleUseCurrentDocument = () => {
    const currentNumber =
      getFieldValue("passport_number");

    if (currentNumber !== "—") {
      setLookupQuery(currentNumber);
    }
  };

  // ================= RESET =================

  const handleReset = () => {
    setDocumentFile(null);
    setSelfieFile(null);

    setAnalyzing(false);
    setAnalyzed(false);

    setResult(null);
    setError("");

    setShowCamera(false);

    setLookupQuery("");
    setLookupResult(null);

    // Identity reuse alert reset.
    setShowIdentityReuseAlert(false);
    setIdentityReuseRecords([]);
  };

  // ================= BACKEND DATA =================

  const ocr = result?.ocr;
  const validation = result?.validation;
  const tampering = result?.tampering;
  const face = result?.face;
  const authority = result?.authority_match;
  const risk = result?.risk;
  const ledger = result?.ledger;

  // ================= OCR =================

  const getFieldValue = (fieldName) =>
    ocr?.extracted_fields?.[fieldName]?.value ??
    "—";

  // ================= VALIDATION =================

  const validationPassed =
    validation?.status === "success" &&
    validation?.checksum_pass === true &&
    validation?.text_mrz_match === true &&
    validation?.expiry_valid === true &&
    validation?.db_status === "clear" &&
    (validation?.flags?.length ?? 0) === 0;

  // ================= TAMPERING =================

  const tamperFlag =
    tampering?.overall_tamper_flag === true;

  const tamperProbability =
    tampering?.dl_tamper_probability ?? null;

  // ================= FACE =================

  const faceStatus = face?.status ?? null;

  const faceScore =
    face?.similarity ?? null;

  // ================= AUTHORITY =================

  const authorityStatus =
    authority?.status ?? "not_available";

  // ================= RISK =================

  const riskScore =
    risk?.risk_score ?? null;

  const riskBand =
    risk?.risk_band ?? null;

  const recommendation =
    risk?.final_recommendation ?? null;

  const evidenceStrength =
    risk?.evidence_strength ?? null;

  // ================= LEDGER =================

  const identityReuse =
    ledger?.identity_reuse_flag === true;

  // ================= HELPERS =================

  const formatSimilarity = (score) => {
    if (score === null || score === undefined) {
      return "—";
    }

    const value = Number(score);

    if (Number.isNaN(value)) {
      return "—";
    }

    return value <= 1
      ? `${Math.round(value * 100)}%`
      : `${Math.round(value)}%`;
  };

  const getRiskClass = () => {
    if (riskBand === "clear") return "clear";

    if (riskBand === "secondary_check") {
      return "secondary";
    }

    if (riskBand === "high_risk") {
      return "high";
    }

    return "";
  };

  const getAuthorityDisplay = () => {
    if (authorityStatus === "match") {
      return "MATCH";
    }

    if (authorityStatus === "mismatch") {
      return "MISMATCH";
    }

    return "NOT AVAILABLE";
  };

  // =====================================================
  // RENDER
  // =====================================================

  return (
    <div className="app">

      {/* ================= GOV BANNER ================= */}

      <div className="gov-banner">

        <div className="gov-banner-inner">

          <div className="gov-left">

            <Landmark size={16} />

            <span>
              SMART INDIA HACKATHON • AI FOR SECURE DIGITAL IDENTITY
            </span>

          </div>

          <div className="gov-right">

            <LockKeyhole size={14} />

            Privacy-aware identity screening

          </div>

        </div>

      </div>

      {/* ================= HEADER ================= */}

      <header className="topbar">

        <div>

          <div className="title-row">

            <Fingerprint
              className="title-icon"
              size={28}
            />

            <h1>
              AI Based Fake Identity &amp;
              Document Screening System
            </h1>

          </div>

          <p>
            Multi-layer AI verification for document
            integrity, identity matching and fraud
            risk assessment.
          </p>

        </div>

        <div className="top-actions">

          <button
            className="activity-btn"
            onClick={loadLedger}
          >
            <History size={17} />
            Activity log
          </button>

          <button
            className="scan-again"
            onClick={handleReset}
          >
            <RotateCcw size={16} />
            Scan again
          </button>

        </div>

      </header>

      {/* ================= PROGRESS ================= */}

      <div className="progress">

        <div className="progress-step active">
          <span>01</span>
          DOCUMENT CAPTURE
        </div>

        <div className="progress-line" />

        <div
          className={`progress-step ${
            analyzed ? "active" : ""
          }`}
        >
          <span>02</span>
          IDENTITY CHECK
        </div>

        <div className="progress-line" />

        <div
          className={`progress-step ${
            analyzed ? "active" : ""
          }`}
        >
          <span>03</span>
          DECISION
        </div>

      </div>

      {/* ================= ERROR ================= */}

      {error && (

        <div className="error-banner">

          <XCircle size={18} />

          <span>{error}</span>

          <button
            onClick={() => setError("")}
          >
            ×
          </button>

        </div>

      )}

      {/* ================= MAIN GRID ================= */}

      <main className="main-grid">

        {/* ================= DOCUMENT ================= */}

        <section className="capture-card card">

          <div className="section-label">
            <span>01</span>
            DOCUMENT CAPTURE
          </div>

          <div className="card-heading">

            <div>

              <h2>
                Capture required documents
              </h2>

              <p>
                Upload a clear identity document
                for AI screening.
              </p>

            </div>

            <span className="secure">

              <ShieldCheck size={15} />

              SECURE PROCESSING

            </span>

          </div>

          {/* DOCUMENT TYPES */}

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

          {/* DOCUMENT STATUS */}

          <div className="capture-status">

            <CheckCircle2 size={17} />

            <div>

              <strong>

                {documentFile
                  ? documentFile.name
                  : "Document upload required"}

              </strong>

              <span>

                {documentFile
                  ? "Document image ready for screening."
                  : "Upload a clear image of the identity document."}

              </span>

            </div>

          </div>

          {/* DOCUMENT PREVIEW */}

          <div className="document-preview">

            <div className="scan-corners" />

            {documentPreview ? (

              <img
                src={documentPreview}
                alt="Uploaded document"
                className="uploaded-document-preview"
              />

            ) : (

              <div className="passport-placeholder">

                <div className="passport-header">

                  <span>
                    IDENTITY DOCUMENT
                  </span>

                  <span>
                    AI SCREENING PREVIEW
                  </span>

                </div>

                <div className="passport-body">

                  <div className="fake-photo">
                    <UserRound size={42} />
                  </div>

                  <div className="passport-lines">

                    <div>
                      <small>
                        FULL NAME
                      </small>

                      <b>
                        DOCUMENT PREVIEW
                      </b>
                    </div>

                    <div>
                      <small>
                        NATIONALITY
                      </small>

                      <b>
                        —
                      </b>
                    </div>

                    <div className="mini-row">

                      <div>
                        <small>
                          DATE OF BIRTH
                        </small>

                        <b>
                          —
                        </b>
                      </div>

                      <div>
                        <small>
                          DOCUMENT NO.
                        </small>

                        <b>
                          —
                        </b>
                      </div>

                    </div>

                  </div>

                </div>

                <div className="mrz">

                  Upload document image to begin
                  automated verification

                </div>

              </div>

            )}

            {analyzed && tamperFlag && (

              <div className="suspicious-box">
                <span>
                  AI FLAGGED
                </span>
              </div>

            )}

          </div>

          {/* ACTION BUTTONS */}

          <div className="capture-actions">

            <button
              className="primary-btn"
              onClick={() =>
                setShowCamera(true)
              }
            >

              <Camera size={17} />

              Capture Selfie

            </button>

            <label className="secondary-btn">

              <Upload size={17} />

              Upload Document

              <input
                type="file"
                hidden
                accept="image/*"
                onChange={handleDocumentUpload}
              />

            </label>

            <label className="secondary-btn">

              <UserRound size={17} />

              Upload Selfie

              <input
                type="file"
                hidden
                accept="image/*"
                onChange={handleSelfieUpload}
              />

            </label>

          </div>

          {/* SELFIE STATUS */}

          <div className="selfie-status-row">

            <div className="capture-status selfie-status">

              <CheckCircle2 size={17} />

              <div>

                <strong>

                  {selfieFile
                    ? "Selfie ready"
                    : "Live selfie required"}

                </strong>

                <span>

                  {selfieFile
                    ? selfieFile.name
                    : "Capture or upload a selfie for face verification."}

                </span>

              </div>

            </div>

            {selfiePreview && (

              <img
                src={selfiePreview}
                className="selfie-thumbnail"
                alt="Selfie preview"
              />

            )}

          </div>

          <p className="helper-text">

            <ShieldCheck size={14} />

            Images are processed only for identity verification.

          </p>

        </section>

        {/* ================= RIGHT ================= */}

        <aside className="right-column">

          {/* ================= VERIFICATION ================= */}

          <section className="card verification-card">

            <div className="card-top">

              <div>

                <div className="section-label small-label">
                  VERIFICATION RESULT
                </div>

                <h2>
                  Identity confidence
                </h2>

              </div>

              <span className="safe-badge">

                <span />

                {analyzing
                  ? "ANALYZING"
                  : analyzed
                    ? "COMPLETE"
                    : "READY"}

              </span>

            </div>

            {/* CONFIDENCE */}

            <div className="confidence">

              <div className="confidence-circle">

                <strong>

                  {faceScore !== null
                    ? formatSimilarity(faceScore)
                        .replace("%", "")
                    : "—"}

                </strong>

                {faceScore !== null && (
                  <small>%</small>
                )}

              </div>

              <div>

                <h3>

                  {analyzing
                    ? "Screening in progress"
                    : analyzed
                      ? "Screening complete"
                      : "Awaiting verification"}

                </h3>

                <p>

                  {analyzing
                    ? "Running all verification modules."
                    : analyzed
                      ? `Recommendation: ${
                          recommendation
                            ? recommendation
                                .replace(/_/g, " ")
                                .toUpperCase()
                            : "REVIEW"
                        }`
                      : "Upload document and provide a selfie to begin."}

                </p>

              </div>

            </div>

            {/* MODULE RESULTS */}

            <div className="checks">

              <VerificationRow
                icon={<FileCheck2 size={17} />}
                title="Document Integrity"
                subtitle={
                  validation?.status === "failed"
                    ? "Validation could not complete"
                    : "Format and rule validation"
                }
                status={
                  !analyzed
                    ? "—"
                    : validationPassed
                      ? "PASS"
                      : "REVIEW"
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
                subtitle={
                  ocr?.status === "success"
                    ? "Identity fields extracted"
                    : "OCR extraction failed"
                }
                status={
                  !analyzed
                    ? "—"
                    : ocr?.status === "success"
                      ? "COMPLETE"
                      : "FAILED"
                }
                type={
                  !analyzed
                    ? "neutral"
                    : ocr?.status === "success"
                      ? "success"
                      : "warning"
                }
              />

              <VerificationRow
                icon={<ScanLine size={17} />}
                title="MRZ Validation"
                subtitle={
                  validation?.text_mrz_match === true
                    ? "Checksum and field consistency passed"
                    : "MRZ requires review"
                }
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
                subtitle={
                  analyzed &&
                  tamperProbability !== null
                    ? `DL probability: ${Math.round(
                        tamperProbability * 100,
                      )}% • ELA: ${
                        tampering?.ela_score?.toFixed(4) ??
                        "—"
                      }`
                    : "Digital manipulation screening"
                }
                status={
                  !analyzed
                    ? "—"
                    : tamperFlag
                      ? "FLAGGED"
                      : "CLEAN"
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
                subtitle={
                  faceStatus ===
                  "no_face_detected"
                    ? face?.face_detected_in_document
                      ? "Selfie/document comparison unavailable"
                      : "No usable document portrait detected"
                    : "Document portrait vs live selfie"
                }
                status={
                  !analyzed
                    ? "—"
                    : faceStatus === "match"
                      ? formatSimilarity(faceScore)
                      : faceStatus === "mismatch"
                        ? "MISMATCH"
                        : "NO FACE"
                }
                type={
                  !analyzed
                    ? "neutral"
                    : faceStatus === "match"
                      ? "success"
                      : "warning"
                }
              />

              <VerificationRow
                icon={<Database size={17} />}
                title="Authority Reference"
                subtitle={
                  authorityStatus ===
                  "not_available"
                    ? "Independent authority reference unavailable"
                    : "Independent authority comparison"
                }
                status={
                  !analyzed
                    ? "—"
                    : getAuthorityDisplay()
                }
                type={
                  !analyzed
                    ? "neutral"
                    : authorityStatus === "match"
                      ? "success"
                      : authorityStatus === "mismatch"
                        ? "warning"
                        : "neutral"
                }
              />

              {/* IDENTITY REUSE */}

              <VerificationRow
                icon={
                  !analyzed ? (
                    <History size={17} />
                  ) : identityReuse ? (
                    <ShieldAlert size={17} />
                  ) : (
                    <History size={17} />
                  )
                }
                title="Identity Reuse Detection"
                subtitle={
                  !analyzed
                    ? "Historical ledger identity search"
                    : identityReuse
                      ? "Matching identity found in previous records"
                      : "No matching identity found in ledger"
                }
                status={
                  !analyzed
                    ? "—"
                    : identityReuse
                      ? "FLAGGED"
                      : "CLEAR"
                }
                type={
                  !analyzed
                    ? "neutral"
                    : identityReuse
                      ? "warning"
                      : "success"
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

                {analyzing
                  ? "Running AI Screening..."
                  : "Analyze Document"}

              </button>

            )}

          </section>

          {/* ================= THREE DATABASE LOOKUP ================= */}

          <section className="card trusted-card">

            <div className="card-top">

              <div>

                <div className="section-label small-label">
                  THREE-SOURCE VERIFICATION
                </div>

                <h2>
                  Database lookup
                </h2>

              </div>

              <Database size={18} />

            </div>

            {/* SOURCE SELECTOR */}

            <div className="lookup-source-tabs">

              <button
                className={
                  lookupSource === "issuance"
                    ? "lookup-source active"
                    : "lookup-source"
                }
                onClick={() => {

                  setLookupSource("issuance");
                  setLookupResult(null);
                  setError("");

                }}
              >

                <strong>
                  DB #1
                </strong>

                <span>
                  Issuance
                </span>

              </button>

              <button
                className={
                  lookupSource === "authority"
                    ? "lookup-source active"
                    : "lookup-source"
                }
                onClick={() => {

                  setLookupSource("authority");
                  setLookupResult(null);
                  setError("");

                }}
              >

                <strong>
                  DB #2
                </strong>

                <span>
                  Authority
                </span>

              </button>

              <button
                className={
                  lookupSource === "ledger"
                    ? "lookup-source active"
                    : "lookup-source"
                }
                onClick={() => {

                  setLookupSource("ledger");
                  setLookupResult(null);
                  setError("");

                }}
              >

                <strong>
                  DB #3
                </strong>

                <span>
                  Ledger
                </span>

              </button>

            </div>

            {/* SOURCE DESCRIPTION */}

            <div className="lookup-source-description">

              {lookupSource === "issuance" && (
                <>
                  <strong>
                    DB #1 — Issuance / Blacklist
                  </strong>

                  <span>
                    Official-style issuance reference used
                    to check document status.
                  </span>
                </>
              )}

              {lookupSource === "authority" && (
                <>
                  <strong>
                    DB #2 — Authority Reference
                  </strong>

                  <span>
                    Independent authority reference record
                    and reference-photo availability.
                  </span>
                </>
              )}

              {lookupSource === "ledger" && (
                <>
                  <strong>
                    DB #3 — Blockchain Audit Ledger
                  </strong>

                  <span>
                    Historical screening records, hashes,
                    risk decisions and audit evidence.
                  </span>
                </>
              )}

            </div>

            {/* SEARCH */}

            <div className="record-search-row">

              <div className="search-box lookup-search-box">

                <Search size={16} />

                <input
                  value={lookupQuery}
                  onChange={(e) =>
                    setLookupQuery(e.target.value)
                  }
                  onKeyDown={handleLookupKeyDown}
                  placeholder={
                    lookupSource === "ledger"
                      ? "Document number or ledger hash"
                      : "Document number"
                  }
                />

              </div>

              <button
                className="lookup-btn"
                onClick={handleRecordLookup}
                disabled={lookupLoading}
              >
                {lookupLoading
                  ? "..."
                  : "Search"}
              </button>

            </div>

            {analyzed && (

              <button
                className="current-doc-btn"
                onClick={handleUseCurrentDocument}
              >

                <FileCheck2 size={13} />

                Use current document number

              </button>

            )}

            {/* LOOKUP RESULT */}

            {lookupResult && (

              <LookupResult
                source={lookupSource}
                result={lookupResult}
                getRecordHash={getRecordHash}
                getPreviousHash={getPreviousHash}
                getRecordDocumentNumber={
                  getRecordDocumentNumber
                }
                getRecordName={getRecordName}
                onOpenLedger={(record) =>
                  setSelectedLedgerRecord(record)
                }
              />

            )}

          </section>

        </aside>

      </main>

      {/* ================= BOTTOM ================= */}

      <section className="bottom-grid">

        {/* EXTRACTED INFO */}

        <div className="card extracted-card">

          <div className="section-label small-label">
            EXTRACTED INFORMATION
          </div>

          <div className="info-grid">

            <Info
              label="Full name"
              value={getFieldValue("name")}
            />

            <Info
              label="Nationality"
              value={getFieldValue("nationality")}
            />

            <Info
              label="Date of birth"
              value={getFieldValue("dob")}
            />

            <Info
              label="Document number"
              value={getFieldValue("passport_number")}
            />

            <Info
              label="Expiry date"
              value={getFieldValue("expiry")}
            />

            <Info
              label="Gender"
              value={getFieldValue("gender")}
            />

          </div>

        </div>

        {/* RISK */}

        <div className="card risk-card">

          <div className="section-label small-label">
            SCREENING DECISION
          </div>

          <div className="risk-header">

            <div>

              <span>
                Risk score
              </span>

              <strong>
                {riskScore !== null
                  ? Math.round(Number(riskScore))
                  : "—"}
              </strong>

              <small>
                / 100
              </small>

            </div>

            <span
              className={`risk-badge ${getRiskClass()}`}
            >
              {riskBand
                ? riskBand
                    .replace(/_/g, " ")
                    .toUpperCase()
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

                Tampering:{" "}

                {tamperVerdict(
                  tampering?.tamper_verdict,
                )}

              </div>

              <div>

                {validationPassed ? (
                  <CheckCircle2 size={15} />
                ) : (
                  <AlertTriangle size={15} />
                )}

                Validation:{" "}

                {validationPassed
                  ? "Passed"
                  : "Requires review"}

              </div>

              <div>

                <Eye size={15} />

                Evidence strength:{" "}

                {evidenceStrength !== null
                  ? `${Math.round(
                      Number(evidenceStrength) * 100,
                    )}%`
                  : "—"}

              </div>

              <div>

                <Database size={15} />

                Authority:{" "}

                {getAuthorityDisplay()}

              </div>

              {identityReuse && (

                <div>

                  <AlertTriangle size={15} />

                  Identity reuse detected

                </div>

              )}

            </div>

          ) : (

            <p className="empty-risk">

              Complete document analysis to generate
              the screening decision.

            </p>

          )}

        </div>

      </section>

      {/* ================= LEDGER SUMMARY ================= */}

      {analyzed && ledger && (

        <section className="ledger-summary">

          <div className="ledger-summary-inner">

            <div>

              <div className="section-label">

                DB #3 • BLOCKCHAIN AUDIT TRAIL

              </div>

              <strong>
                Screening record secured
              </strong>

              <span>

                Hash:{" "}

                {getRecordHash(ledger).slice(
                  0,
                  28,
                )}

                ...

              </span>

            </div>

            <button onClick={loadLedger}>

              <Database size={16} />

              View ledger

            </button>

          </div>

        </section>

      )}

      {/* ================= FOOTER ================= */}

      <footer>

        <div>

          <ShieldCheck size={15} />

          AI-assisted screening • Final decision
          remains with authorized personnel

        </div>

        <div>

          <Clock3 size={14} />

          {analyzing
            ? "Screening pipeline running"
            : "System ready"}

        </div>

      </footer>

      {/* ================= CAMERA ================= */}

      {showCamera && (

        <div
          className="camera-overlay"
          onClick={() =>
            setShowCamera(false)
          }
        >

          <div
            className="camera-modal"
            onClick={(e) =>
              e.stopPropagation()
            }
          >

            <CameraPanel
              onCapture={handleSelfieCapture}
              onClose={() =>
                setShowCamera(false)
              }
            />

          </div>

        </div>

      )}

      {/* ================= ACTIVITY LOG / DB #3 ================= */}

      {showActivity && (

        <div
          className="activity-overlay"
          onClick={() =>
            setShowActivity(false)
          }
        >

          <div
            className="activity-modal"
            onClick={(e) =>
              e.stopPropagation()
            }
          >

            <div className="activity-header">

              <div>

                <div className="section-label">
                  DB #3 • BLOCKCHAIN LEDGER
                </div>

                <h2>
                  Screening activity
                </h2>

              </div>

              <button
                onClick={() =>
                  setShowActivity(false)
                }
              >
                ×
              </button>

            </div>

            {loadingLedger ? (

              <div className="ledger-loading">
                Loading ledger records...
              </div>

            ) : ledgerRecords.length === 0 ? (

              <div className="ledger-loading">
                No ledger records found.
              </div>

            ) : (

              <div className="ledger-list">

                {ledgerRecords
                  .slice()
                  .reverse()
                  .map((record, index) => (

                    <button
                      type="button"
                      className="ledger-item"
                      key={
                        getRecordHash(record) +
                        String(index)
                      }
                      onClick={() =>
                        setSelectedLedgerRecord(
                          record,
                        )
                      }
                    >

                      <div className="ledger-index">

                        #

                        {record.index !== undefined
                          ? Number(record.index) + 1
                          : ledgerRecords.length -
                            index}

                      </div>

                      <div className="ledger-content">

                        <strong>
                          {getRecordName(record)}
                        </strong>

                        <span>

                          {getRecordDocumentNumber(
                            record,
                          )}

                          {" • "}

                          Risk{" "}

                          {record.risk_result
                            ?.risk_score ?? "—"}

                        </span>

                        <span>

                          Authority:{" "}

                          {record.authority_match_status ??
                            "not_available"}

                        </span>

                        <span>

                          Identity reuse:{" "}

                          {record.identity_reuse_flag
                            ? "FLAGGED"
                            : "CLEAR"}

                        </span>

                        <span>

                          {record.timestamp ||
                            "Timestamp unavailable"}

                        </span>

                        <code>
                          {getRecordHash(record)}
                        </code>

                      </div>

                      <ChevronRight size={18} />

                    </button>

                  ))}

              </div>

            )}

          </div>

        </div>

      )}

      {/* ================= LEDGER DETAIL ================= */}

      {selectedLedgerRecord && (

        <div
          className="activity-overlay"
          onClick={() =>
            setSelectedLedgerRecord(null)
          }
        >

          <div
            className="ledger-detail-modal"
            onClick={(e) =>
              e.stopPropagation()
            }
          >

            <div className="activity-header">

              <div>

                <div className="section-label">
                  DB #3 • BLOCKCHAIN RECORD
                </div>

                <h2>
                  Immutable screening record
                </h2>

              </div>

              <button
                onClick={() =>
                  setSelectedLedgerRecord(null)
                }
              >
                ×
              </button>

            </div>

            <div className="ledger-detail-grid">

              <DetailItem
                label="Record index"
                value={
                  selectedLedgerRecord.index ??
                  "—"
                }
              />

              <DetailItem
                label="Identity"
                value={getRecordName(
                  selectedLedgerRecord,
                )}
              />

              <DetailItem
                label="Document number"
                value={getRecordDocumentNumber(
                  selectedLedgerRecord,
                )}
              />

              <DetailItem
                label="Timestamp"
                value={
                  selectedLedgerRecord.timestamp ||
                  "—"
                }
              />

              <DetailItem
                label="Risk score"
                value={
                  selectedLedgerRecord.risk_result
                    ?.risk_score ?? "—"
                }
              />

              <DetailItem
                label="Risk band"
                value={
                  selectedLedgerRecord.risk_result
                    ?.risk_band
                    ? selectedLedgerRecord
                        .risk_result
                        .risk_band
                        .replace(/_/g, " ")
                        .toUpperCase()
                    : "—"
                }
              />

              <DetailItem
                label="Recommendation"
                value={
                  selectedLedgerRecord.risk_result
                    ?.final_recommendation
                    ? selectedLedgerRecord
                        .risk_result
                        .final_recommendation
                        .replace(/_/g, " ")
                        .toUpperCase()
                    : "—"
                }
              />

              <DetailItem
                label="Authority status"
                value={
                  selectedLedgerRecord
                    .authority_match_status ??
                  "not_available"
                }
              />

              <DetailItem
                label="Authority similarity"
                value={formatSimilarity(
                  selectedLedgerRecord
                    .authority_match_similarity,
                )}
              />

              <DetailItem
                label="Identity reuse"
                value={
                  selectedLedgerRecord
                    .identity_reuse_flag
                    ? "FLAGGED"
                    : "NOT DETECTED"
                }
              />

              <DetailItem
                label="Reuse matches"
                value={
                  Array.isArray(
                    selectedLedgerRecord
                      .identity_reuse_matches,
                  )
                    ? selectedLedgerRecord
                        .identity_reuse_matches
                        .length
                    : 0
                }
              />

            </div>

            <div className="hash-section">

              <span>
                Record Hash
              </span>

              <code>
                {getRecordHash(
                  selectedLedgerRecord,
                )}
              </code>

            </div>

            <div className="hash-section">

              <span>
                Previous Hash
              </span>

              <code>
                {getPreviousHash(
                  selectedLedgerRecord,
                )}
              </code>

            </div>

            <div className="ledger-detail-actions">

              <button
                className="secondary-btn"
                onClick={() =>
                  setSelectedLedgerRecord(null)
                }
              >
                Close
              </button>

            </div>

          </div>

        </div>

      )}

      {/* =====================================================
          IDENTITY REUSE ALERT
          ===================================================== */}

      {showIdentityReuseAlert && (

        <div
          className="identity-reuse-overlay"
          onClick={() =>
            setShowIdentityReuseAlert(false)
          }
        >

          <div
            className="identity-reuse-modal"
            onClick={(e) =>
              e.stopPropagation()
            }
          >

            {/* ALERT HEADER */}

            <div className="identity-reuse-header">

              <div className="identity-reuse-alert-icon">

                <ShieldAlert size={24} />

              </div>

              <div>

                <div className="section-label">
                  FRAUD ALERT
                </div>

                <h2>
                  Identity reuse detected
                </h2>

                <p>

                  The submitted identity matches previously
                  stored ledger embeddings under different
                  identity declarations.

                </p>

              </div>

              <button
                className="identity-reuse-close"
                onClick={() =>
                  setShowIdentityReuseAlert(false)
                }
              >
                ×
              </button>

            </div>

            {/* SUMMARY */}

            <div className="identity-reuse-summary">

              <div>

                <span>
                  Matched records
                </span>

                <strong>

                  {identityReuseRecords.length ||
                    ledger?.identity_reuse_matches
                      ?.length ||
                    0}

                </strong>

              </div>

              <div>

                <span>
                  Current identity
                </span>

                <strong>
                  {getFieldValue("name")}
                </strong>

              </div>

              <div>

                <span>
                  Current document
                </span>

                <strong>
                  {getFieldValue("passport_number")}
                </strong>

              </div>

            </div>

            {/* MATCHED HISTORICAL RECORDS */}

            <div className="identity-reuse-records">

              <div className="identity-reuse-records-title">
                MATCHED HISTORICAL RECORDS
              </div>

              {identityReuseRecords.length === 0 ? (

                <div className="identity-reuse-empty">

                  Matching ledger indexes:

                  <strong>

                    {ledger
                      ?.identity_reuse_matches
                      ?.map((index) =>
                        `#${Number(index) + 1}`,
                      )
                      .join(", ") ||
                      "Unavailable"}

                  </strong>

                </div>

              ) : (

                identityReuseRecords.map(
                  (record, index) => (

                    <button
                      type="button"
                      className="identity-reuse-record"
                      key={
                        getRecordHash(record) +
                        String(index)
                      }
                      onClick={() => {

                        setSelectedLedgerRecord(
                          record,
                        );

                        setShowIdentityReuseAlert(
                          false,
                        );

                      }}
                    >

                      <div className="identity-reuse-record-index">

                        #

                        {record.index !== undefined
                          ? Number(record.index) + 1
                          : "—"}

                      </div>

                      <div className="identity-reuse-record-body">

                        <div className="identity-reuse-record-title">

                          <strong>
                            {getRecordName(record)}
                          </strong>

                          <span>
                            Matched historical identity
                          </span>

                        </div>

                        <div className="identity-reuse-fields">

                          <div>

                            <span>
                              Document
                            </span>

                            <strong>
                              {getRecordDocumentNumber(
                                record,
                              )}
                            </strong>

                          </div>

                          <div>

                            <span>
                              Risk
                            </span>

                            <strong>

                              {record.risk_result
                                ?.risk_score ?? "—"}

                              /100

                            </strong>

                          </div>

                          <div>

                            <span>
                              Risk band
                            </span>

                            <strong>

                              {record.risk_result
                                ?.risk_band
                                ? record.risk_result
                                    .risk_band
                                    .replace(
                                      /_/g,
                                      " ",
                                    )
                                    .toUpperCase()
                                : "—"}

                            </strong>

                          </div>

                          <div>

                            <span>
                              Recommendation
                            </span>

                            <strong>

                              {record.risk_result
                                ?.final_recommendation
                                ? record.risk_result
                                    .final_recommendation
                                    .replace(
                                      /_/g,
                                      " ",
                                    )
                                    .toUpperCase()
                                : "—"}

                            </strong>

                          </div>

                          <div>

                            <span>
                              Authority
                            </span>

                            <strong>

                              {record.authority_match_status ??
                                "NOT AVAILABLE"}

                            </strong>

                          </div>

                          <div>

                            <span>
                              Authority similarity
                            </span>

                            <strong>

                              {formatSimilarity(
                                record.authority_match_similarity,
                              )}

                            </strong>

                          </div>

                          <div>

                            <span>
                              Identity reuse
                            </span>

                            <strong>

                              {record.identity_reuse_flag
                                ? "FLAGGED"
                                : "CLEAR"}

                            </strong>

                          </div>

                          <div>

                            <span>
                              Ledger index
                            </span>

                            <strong>

                              {record.index ??
                                "—"}

                            </strong>

                          </div>

                        </div>

                        <div className="identity-reuse-timestamp">

                          <span>

                            {record.timestamp ||
                              "Timestamp unavailable"}

                          </span>

                          <code>

                            {getRecordHash(
                              record,
                            ).slice(0, 24)}

                            ...

                          </code>

                        </div>

                      </div>

                      <ChevronRight size={18} />

                    </button>

                  ),
                )

              )}

            </div>

            {/* FOOTER */}

            <div className="identity-reuse-footer">

              <span>

                These records were matched using
                historical face embeddings stored in
                the audit ledger.

              </span>

              <button
                className="secondary-btn"
                onClick={() =>
                  setShowIdentityReuseAlert(false)
                }
              >
                Review later
              </button>

            </div>

          </div>

        </div>

      )}

    </div>
  );
}

// =====================================================
// LOOKUP RESULT
// =====================================================

function LookupResult({
  source,
  result,
  getRecordHash,
  getPreviousHash,
  getRecordDocumentNumber,
  getRecordName,
  onOpenLedger,
}) {
  if (!result || result.found === false) {
    return (
      <div className="lookup-empty">

        <XCircle size={15} />

        <span>
          No matching record found.
        </span>

      </div>
    );
  }

  // ===================================================
  // DB #3 — BLOCKCHAIN LEDGER
  // ===================================================

  if (source === "ledger") {

    const records = Array.isArray(
      result.records,
    )
      ? result.records
      : result.record
        ? [result.record]
        : [];

    if (records.length === 0) {
      return (
        <div className="lookup-empty">

          <XCircle size={15} />

          <span>
            No ledger record found.
          </span>

        </div>
      );
    }

    return (
      <div className="lookup-results">

        <div className="lookup-result-heading">

          <div>

            <span className="lookup-result-kicker">
              DB #3
            </span>

            <strong>
              Blockchain Ledger
            </strong>

          </div>

          <span className="lookup-result-count">

            {records.length} record
            {records.length !== 1 ? "s" : ""}

          </span>

        </div>

        {records.map((record, index) => (

          <button
            type="button"
            className="lookup-record"
            key={
              getRecordHash(record) +
              String(index)
            }
            onClick={() =>
              onOpenLedger(record)
            }
          >

            <div className="lookup-record-number">

              #

              {record.index !== undefined
                ? Number(record.index) + 1
                : index + 1}

            </div>

            <div className="lookup-record-main">

              <div className="lookup-record-title">

                <strong>
                  {getRecordName(record)}
                </strong>

                <span className="lookup-record-status">

                  RISK{" "}

                  {record.risk_result
                    ?.risk_score ?? "—"}

                </span>

              </div>

              <div className="lookup-record-meta">

                <span>

                  Document{" "}

                  <b>
                    {getRecordDocumentNumber(
                      record,
                    )}
                  </b>

                </span>

                <span>

                  Authority{" "}

                  <b>

                    {record.authority_match_status ??
                      "not available"}

                  </b>

                </span>

                <span>

                  Reuse{" "}

                  <b>

                    {record.identity_reuse_flag
                      ? "FLAGGED"
                      : "CLEAR"}

                  </b>

                </span>

              </div>

              <code>

                {getRecordHash(record).slice(
                  0,
                  28,
                )}

                ...

              </code>

            </div>

            <ChevronRight size={17} />

          </button>

        ))}

      </div>
    );
  }

  // ===================================================
  // DB #1 — ISSUANCE
  // ===================================================

  if (source === "issuance") {

    const status =
      result.status || "unknown";

    return (
      <div className="lookup-database-result">

        <div className="lookup-result-heading">

          <div>

            <span className="lookup-result-kicker">
              DB #1
            </span>

            <strong>
              Issuance / Blacklist
            </strong>

          </div>

          <span
            className={`db-status ${
              status === "clear"
                ? "clear"
                : "warning"
            }`}
          >
            {status.toUpperCase()}
          </span>

        </div>

        <div className="lookup-data-grid">

          <div className="lookup-data-field">

            <span>
              Document number
            </span>

            <strong>
              {result.document_number ||
                "Unavailable"}
            </strong>

          </div>

          <div className="lookup-data-field">

            <span>
              Issuance status
            </span>

            <strong>
              {status.toUpperCase()}
            </strong>

          </div>

          <div className="lookup-data-field full-width">

            <span>
              Issued to
            </span>

            <strong>
              {result.issued_to ||
                "No issuing identity available"}
            </strong>

          </div>

        </div>

        <div className="lookup-result-source-note">

          {result.source_name ||
            "Mock DB #1 - Issuance"}

        </div>

      </div>
    );
  }

  // ===================================================
  // DB #2 — AUTHORITY
  // ===================================================

  return (
    <div className="lookup-database-result">

      <div className="lookup-result-heading">

        <div>

          <span className="lookup-result-kicker">
            DB #2
          </span>

          <strong>
            Authority Reference
          </strong>

        </div>

        <span
          className={`db-status ${
            result.reference_available
              ? "clear"
              : "warning"
          }`}
        >
          {result.reference_available
            ? "AVAILABLE"
            : "NOT AVAILABLE"}
        </span>

      </div>

      <div className="lookup-data-grid">

        <div className="lookup-data-field">

          <span>
            Document number
          </span>

          <strong>
            {result.document_number ||
              "Unavailable"}
          </strong>

        </div>

        <div className="lookup-data-field">

          <span>
            Reference available
          </span>

          <strong>
            {result.reference_available
              ? "YES"
              : "NO"}
          </strong>

        </div>

        <div className="lookup-data-field">

          <span>
            Reference source
          </span>

          <strong>
            {result.reference_source ||
              "Unavailable"}
          </strong>

        </div>

        <div className="lookup-data-field">

          <span>
            Reference file
          </span>

          <strong>
            {result.reference_file ||
              "No reference file"}
          </strong>

        </div>

      </div>

      <div className="lookup-result-source-note">

        {result.source_name ||
          "Mock DB #2 - Authority Reference"}

      </div>

    </div>
  );
}

// =====================================================
// VERIFICATION ROW
// =====================================================

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

        <strong>
          {title}
        </strong>

        <span>
          {subtitle}
        </span>

      </div>

      <span className={`check-status ${type}`}>

        {type === "success" && (
          <CheckCircle2 size={14} />
        )}

        {type === "warning" && (
          <AlertTriangle size={14} />
        )}

        {status}

      </span>

    </div>
  );
}

// =====================================================
// INFO
// =====================================================

function Info({
  label,
  value,
}) {
  return (
    <div className="info-item">

      <span>
        {label}
      </span>

      <strong>
        {value}
      </strong>

    </div>
  );
}

// =====================================================
// DETAIL
// =====================================================

function DetailItem({
  label,
  value,
}) {
  return (
    <div className="detail-item">

      <span>
        {label}
      </span>

      <strong>
        {String(value)}
      </strong>

    </div>
  );
}

// =====================================================
// TAMPER VERDICT
// =====================================================

function tamperVerdict(value) {
  if (!value) return "Unknown";

  return value
    .replace(/_/g, " ")
    .toUpperCase();
}

export default App;