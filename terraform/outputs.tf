output "artifact_registry_repo" {
  value       = google_artifact_registry_repository.containers.repository_id
  description = "Artifact Registry repository id."
}

output "api_service_name" {
  value       = google_cloud_run_v2_service.api.name
  description = "Cloud Run service name for API."
}

output "api_url" {
  value       = google_cloud_run_v2_service.api.uri
  description = "Public URL for API."
}

output "web_service_name" {
  value       = google_cloud_run_v2_service.web.name
  description = "Cloud Run service name for Web."
}

output "web_url" {
  value       = google_cloud_run_v2_service.web.uri
  description = "Public URL for Web."
}

output "github_wif_provider" {
  value       = google_iam_workload_identity_pool_provider.github.name
  description = "Full resource name of the Workload Identity Provider (for GitHub Actions auth)."
}

output "github_deployer_service_account" {
  value       = google_service_account.deployer.email
  description = "Service account email impersonated by GitHub Actions."
}

