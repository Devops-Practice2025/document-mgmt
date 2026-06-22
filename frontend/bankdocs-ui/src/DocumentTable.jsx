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