// src/UploadForm.jsx

import { useState } from "react";
import { uploadDocument } from "./api";

// This component receives "onUploadSuccess" from the parent (App.jsx)
// When upload succeeds, it calls that function so the table refreshes
function UploadForm({ onUploadSuccess }) {

  // useState = React's way of remembering values between renders
  const [customerId, setCustomerId] = useState("");       // text input value
  const [documentType, setDocumentType] = useState("KYC"); // dropdown value
  const [file, setFile] = useState(null);                  // selected file
  const [loading, setLoading] = useState(false);           // show/hide spinner
  const [message, setMessage] = useState("");              // success or error text

  // This runs when the user clicks "Upload"
  const handleSubmit = async (e) => {
    e.preventDefault(); // stops page from refreshing (default form behaviour)

    // Basic validation
    if (!customerId || !file) {
      setMessage("Please fill in Customer ID and select a file.");
      return;
    }

    setLoading(true);   // show "Uploading..." on button
    setMessage("");     // clear old messages

    try {
      const response = await uploadDocument(customerId, documentType, file);
      setMessage(`✅ Uploaded! Document ID: ${response.data.document_id}`);
      setFile(null);    // clear file input
      onUploadSuccess(); // tell parent to refresh the documents table
    } catch (error) {
      setMessage("❌ Upload failed. Check your backend is running.");
    } finally {
      setLoading(false); // hide "Uploading..." regardless of success/fail
    }
  };

  return (
    <div style={styles.card}>
      <h2>Upload Document</h2>

      <form onSubmit={handleSubmit} style={styles.form}>

        {/* Customer ID input */}
        <label>Customer ID</label>
        <input
          type="text"
          placeholder="e.g. CUST001"
          value={customerId}
          onChange={(e) => setCustomerId(e.target.value)} // update state on each keystroke
          style={styles.input}
        />

        {/* Document type dropdown */}
        <label>Document Type</label>
        <select
          value={documentType}
          onChange={(e) => setDocumentType(e.target.value)}
          style={styles.input}
        >
          <option value="KYC">KYC Document</option>
          <option value="LOAN">Loan Application</option>
          <option value="STATEMENT">Bank Statement</option>
          <option value="COMPLIANCE">Compliance Document</option>
        </select>

        {/* File picker */}
        <label>Select File (PDF, Word, Excel, Image)</label>
        <input
          type="file"
          accept=".pdf,.doc,.docx,.xls,.xlsx,.png,.jpg"
          onChange={(e) => setFile(e.target.files[0])} // files[0] = first selected file
          style={styles.input}
        />

        {/* Submit button - shows "Uploading..." while waiting */}
        <button type="submit" disabled={loading} style={styles.button}>
          {loading ? "Uploading..." : "Upload Document"}
        </button>

      </form>

      {/* Show success or error message */}
      {message && <p style={styles.message}>{message}</p>}
    </div>
  );
}

// Simple inline styles - no CSS file needed for now
const styles = {
  card: {
    background: "#fff",
    padding: "24px",
    borderRadius: "8px",
    boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
    marginBottom: "24px",
  },
  form: {
    display: "flex",
    flexDirection: "column", // stack inputs vertically
    gap: "10px",             // space between inputs
    maxWidth: "400px",
  },
  input: {
    padding: "8px",
    borderRadius: "4px",
    border: "1px solid #ccc",
    fontSize: "14px",
  },
  button: {
    padding: "10px",
    background: "#01696f",
    color: "white",
    border: "none",
    borderRadius: "4px",
    cursor: "pointer",
    fontSize: "15px",
  },
  message: {
    marginTop: "12px",
    fontSize: "14px",
  },
};

export default UploadForm;