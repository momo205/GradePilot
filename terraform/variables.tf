variable "project_id" {
  type        = string
  description = "GCP project id to deploy into."
}

variable "region" {
  type        = string
  description = "GCP region for Cloud Run and Artifact Registry."
  default     = "us-east1"
}

variable "github_repository" {
  type        = string
  description = "GitHub repo in the form owner/repo (used for Workload Identity Federation)."
}

variable "artifact_registry_repo" {
  type        = string
  description = "Artifact Registry repository id for container images."
  default     = "gradepilot"
}

variable "api_service_name" {
  type        = string
  description = "Cloud Run service name for the FastAPI backend."
  default     = "gradepilot-api"
}

variable "web_service_name" {
  type        = string
  description = "Cloud Run service name for the Next.js frontend."
  default     = "gradepilot-web"
}

variable "api_image" {
  type        = string
  description = "Full container image URI for the backend (e.g., us-docker.pkg.dev/PROJ/REPO/api:latest)."
}

variable "web_image" {
  type        = string
  description = "Full container image URI for the frontend (e.g., us-docker.pkg.dev/PROJ/REPO/web:latest)."
}

variable "supabase_url" {
  type        = string
  description = "SUPABASE_URL used by the backend."
  sensitive   = true
}

variable "database_url" {
  type        = string
  description = "DATABASE_URL used by the backend (can be Supabase Postgres connection string)."
  sensitive   = true
}

variable "google_api_key" {
  type        = string
  description = "Optional GOOGLE_API_KEY for Gemini calls."
  sensitive   = true
  default     = ""
}

variable "google_oauth_client_id" {
  type        = string
  description = "Optional GOOGLE_OAUTH_CLIENT_ID for Calendar integration."
  sensitive   = true
  default     = ""
}

variable "google_oauth_client_secret" {
  type        = string
  description = "Optional GOOGLE_OAUTH_CLIENT_SECRET for Calendar integration."
  sensitive   = true
  default     = ""
}

variable "google_oauth_redirect_uri" {
  type        = string
  description = "Optional GOOGLE_OAUTH_REDIRECT_URI for OAuth callback."
  sensitive   = true
  default     = ""
}

variable "frontend_supabase_url" {
  type        = string
  description = "Optional NEXT_PUBLIC_SUPABASE_URL for frontend auth (can reuse supabase_url)."
  sensitive   = true
  default     = ""
}

variable "frontend_supabase_anon_key" {
  type        = string
  description = "Optional NEXT_PUBLIC_SUPABASE_ANON_KEY for frontend auth."
  sensitive   = true
  default     = ""
}

