variable "project_id" {
  description = "GCP project that hosts the loan application prototype."
  type        = string
}

variable "region" {
  description = "Region for Artifact Registry and Cloud Run."
  type        = string
  default     = "us-central1"
}

variable "bucket_location" {
  description = "Location for uploaded loan documents."
  type        = string
  default     = "US"
}

variable "firestore_location" {
  description = "Firestore database location."
  type        = string
  default     = "us-central1"
}

variable "document_ai_location" {
  description = "Location of the Document AI OCR processor."
  type        = string
  default     = "us"
}

variable "document_ai_processor_id" {
  description = "Existing Document AI OCR processor ID."
  type        = string
}

variable "frontend_origins" {
  description = "Browser origins allowed by backend CORS and bucket upload CORS."
  type        = list(string)
  default     = ["http://localhost:8080"]
}

variable "backend_image" {
  description = "Backend image URL. Leave empty during the bootstrap apply."
  type        = string
  default     = ""
}

variable "frontend_image" {
  description = "Frontend image URL. Leave empty during the bootstrap apply."
  type        = string
  default     = ""
}
