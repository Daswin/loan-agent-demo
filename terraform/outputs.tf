output "document_bucket" {
  value = google_storage_bucket.documents.name
}

output "artifact_repository" {
  value = google_artifact_registry_repository.loan_agent.name
}

output "backend_service_account" {
  value = google_service_account.backend.email
}

output "backend_url" {
  value = local.deploy_services ? google_cloud_run_v2_service.backend[0].uri : null
}

output "frontend_url" {
  value = local.deploy_services ? google_cloud_run_v2_service.frontend[0].uri : null
}
