// src/api.js

import axios from "axios";

// This is where your FastAPI backend is running locally
// In Phase 2, this will change to your EKS load balancer URL
const BASE_URL = "http://localhost:8080";

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