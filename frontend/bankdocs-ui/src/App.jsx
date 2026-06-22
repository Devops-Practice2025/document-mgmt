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