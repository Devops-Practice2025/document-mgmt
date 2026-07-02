## Step 1 — Create the React app

```bash
cd /mnt/c/Users/UO85HU/Documents/New_repos/document-mgmt/frontend
npm create vite@latest bankdocs-ui -- --template react
cd bankdocs-ui
npm install
npm install axios
```

- **Vite** = fast React project creator (better than old create-react-app)
- **axios** = makes HTTP calls to your FastAPI backend easier than raw `fetch`

***

## Step 2 — Project structure

After creation, your `frontend/bankdocs-ui/src/` will have these files. **Delete everything in `src/`** and replace with just these:

```
src/
├── main.jsx          ← entry point (don't touch)
├── App.jsx           ← main app, holds everything together
├── api.js            ← all backend calls in one place
├── UploadForm.jsx    ← the upload form component
└── DocumentTable.jsx ← the documents list component
```

***

## Step 3 — `src/api.js`

This file is your **single place for all backend communication**. If your backend URL changes later (e.g. when deployed to EKS), you only change it here.

```js
// src/api.js

import axios from "axios";

// This is where your FastAPI backend is running locally
// In Phase 2, this will change to your EKS load balancer URL
const BASE_URL = "http://localhost:8000";

// Upload a document
// Sends: customer_id, document_type, and the file itself
// Returns: { document_id: "uuid..." }
export const uploadDocument = (customerId, documentType, file) => {
  const formData = new FormData();
  formData.append("file", file); // the actual file bytes

  return axios.post(
    `${BASE_URL}/upload?customer_id=${customerId}&document_type=${documentType}`,
    formData,
    { headers: { "Content-Type": "multipart/form-data" } }
  );
};

// Get all documents from MySQL
// Returns: array of document objects
export const listDocuments = () => {
  return axios.get(`${BASE_URL}/documents`);
};

// Get a presigned S3 URL for one document
// Returns: { url: "https://s3.amazonaws.com/..." }
export const getDocumentUrl = (documentId) => {
  return axios.get(`${BASE_URL}/document/${documentId}`);
};

// Delete a document (marks as DELETED in MySQL + removes from S3)
export const deleteDocument = (documentId) => {
  return axios.delete(`${BASE_URL}/document/${documentId}`);
};
```

***

## Step 4 — `src/UploadForm.jsx`

This is the **upload form** — customer ID input, document type dropdown, file picker, and submit button.

```jsx
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
```

***

## Step 5 — `src/DocumentTable.jsx`

This is the **documents list** — shows all uploaded files with View and Delete buttons.

```jsx
// src/DocumentTable.jsx

import { getDocumentUrl, deleteDocument } from "./api";

// "documents" = array of doc objects from GET /documents
// "onRefresh" = function to reload the list after delete
function DocumentTable({ documents, onRefresh }) {

  // When user clicks "View" - get presigned URL then open in new tab
  const handleView = async (documentId) => {
    try {
      const response = await getDocumentUrl(documentId);
      window.open(response.data.url, "_blank"); // open S3 file in new browser tab
    } catch {
      alert("Could not get document URL.");
    }
  };

  // When user clicks "Delete"
  const handleDelete = async (documentId) => {
    // Ask user to confirm before deleting
    if (!window.confirm("Are you sure you want to delete this document?")) return;

    try {
      await deleteDocument(documentId);
      onRefresh(); // refresh the table after deletion
    } catch {
      alert("Delete failed.");
    }
  };

  // If no documents yet, show a friendly message
  if (documents.length === 0) {
    return (
      <div style={styles.card}>
        <h2>Documents</h2>
        <p style={{ color: "#999" }}>No documents uploaded yet.</p>
      </div>
    );
  }

  return (
    <div style={styles.card}>
      <h2>Documents ({documents.length})</h2>

      <table style={styles.table}>
        <thead>
          <tr style={styles.headerRow}>
            <th style={styles.th}>Customer ID</th>
            <th style={styles.th}>File Name</th>
            <th style={styles.th}>Type</th>
            <th style={styles.th}>Upload Date</th>
            <th style={styles.th}>Status</th>
            <th style={styles.th}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {/* Loop through each document and render a row */}
          {documents.map((doc) => (
            <tr key={doc.document_id} style={styles.row}>
              <td style={styles.td}>{doc.customer_id}</td>
              <td style={styles.td}>{doc.file_name}</td>
              <td style={styles.td}>{doc.document_type}</td>
              <td style={styles.td}>
                {/* Format the date nicely */}
                {new Date(doc.upload_date).toLocaleDateString()}
              </td>
              <td style={styles.td}>
                <span style={styles.statusBadge}>{doc.status}</span>
              </td>
              <td style={styles.td}>
                {/* View button */}
                <button
                  onClick={() => handleView(doc.document_id)}
                  style={styles.viewBtn}
                >
                  View
                </button>
                {/* Delete button */}
                <button
                  onClick={() => handleDelete(doc.document_id)}
                  style={styles.deleteBtn}
                >
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const styles = {
  card: {
    background: "#fff",
    padding: "24px",
    borderRadius: "8px",
    boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
  },
  table: {
    width: "100%",
    borderCollapse: "collapse", // removes double borders
    marginTop: "16px",
  },
  headerRow: {
    background: "#f5f5f5",
  },
  th: {
    padding: "10px",
    textAlign: "left",
    borderBottom: "2px solid #ddd",
    fontSize: "13px",
    fontWeight: "600",
  },
  row: {
    borderBottom: "1px solid #eee",
  },
  td: {
    padding: "10px",
    fontSize: "13px",
  },
  statusBadge: {
    background: "#d4dfcc",
    color: "#437a22",
    padding: "2px 8px",
    borderRadius: "999px",
    fontSize: "12px",
    fontWeight: "600",
  },
  viewBtn: {
    marginRight: "8px",
    padding: "4px 12px",
    background: "#01696f",
    color: "white",
    border: "none",
    borderRadius: "4px",
    cursor: "pointer",
    fontSize: "12px",
  },
  deleteBtn: {
    padding: "4px 12px",
    background: "#a12c2c",
    color: "white",
    border: "none",
    borderRadius: "4px",
    cursor: "pointer",
    fontSize: "12px",
  },
};

export default DocumentTable;
```

***

## Step 6 — `src/App.jsx`

This is the **main file** that wires everything together. It fetches the document list and passes it down to the table.

```jsx
// src/App.jsx

import { useState, useEffect } from "react";
import { listDocuments } from "./api";
import UploadForm from "./UploadForm";
import DocumentTable from "./DocumentTable";

function App() {

  // documents = the list we got from GET /documents
  const [documents, setDocuments] = useState([]);

  // This function calls the backend and stores results in state
  const fetchDocuments = async () => {
    try {
      const response = await listDocuments();
      setDocuments(response.data); // response.data = the JSON array
    } catch {
      console.error("Could not fetch documents.");
    }
  };

  // useEffect = run this code when the page first loads
  // The [] means "only run once on mount, not on every render"
  useEffect(() => {
    fetchDocuments();
  }, []);

  return (
    <div style={styles.page}>

      {/* Header */}
      <div style={styles.header}>
        <h1 style={styles.title}>🏦 BankDocs Platform</h1>
        <p style={styles.subtitle}>Banking Document Management System</p>
      </div>

      <div style={styles.container}>
        {/* Upload form - when upload succeeds, it calls fetchDocuments to refresh table */}
        <UploadForm onUploadSuccess={fetchDocuments} />

        {/* Documents table - receives the list and a way to refresh */}
        <DocumentTable documents={documents} onRefresh={fetchDocuments} />
      </div>

    </div>
  );
}

const styles = {
  page: {
    minHeight: "100vh",
    background: "#f7f6f2",
    fontFamily: "sans-serif",
  },
  header: {
    background: "#01696f",
    color: "white",
    padding: "24px 32px",
  },
  title: {
    margin: 0,
    fontSize: "24px",
  },
  subtitle: {
    margin: "4px 0 0",
    opacity: 0.8,
    fontSize: "14px",
  },
  container: {
    maxWidth: "1000px",
    margin: "32px auto",
    padding: "0 24px",
  },
};

export default App;
```

***

## Step 7 — One CORS fix needed in FastAPI

React runs on port `5173`, FastAPI on `8000`. Browser will **block** the calls unless you allow it. Add this to `backend/app/main.py`:

```python
# Add after: app = FastAPI(title="BankDocs Backend")

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # React dev server
    allow_methods=["*"],
    allow_headers=["*"],
)
```

***

## Step 8 — Run the frontend

```bash
cd frontend/bankdocs-ui
npm run dev
```

Open **http://localhost:5173** in your browser. You should see the upload form and documents table. 🎉

***

## What each piece does — summary

| File | Plain English |
|---|---|
| `api.js` | All backend calls in one place |
| `UploadForm.jsx` | Form to pick and upload a file |
| `DocumentTable.jsx` | Table showing all uploaded files |
| `App.jsx` | Glues everything together, loads on start |

Tell me what you see when you open `localhost:5173`!