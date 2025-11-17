output "service_url" {
  description = "URL of the deployed Cloud Run service"
  value       = google_cloud_run_v2_service.rag_agent.uri
}

output "service_name" {
  description = "Name of the Cloud Run service"
  value       = google_cloud_run_v2_service.rag_agent.name
}

output "organization_name" {
  description = "Organization name used for this deployment"
  value       = var.organization_name
}

output "project_id" {
  description = "GCP Project ID"
  value       = var.project_id
}

output "region" {
  description = "GCP region"
  value       = var.region
}

output "data_bucket" {
  description = "GCS bucket used for data storage"
  value       = google_storage_bucket.data_storage.name
}

output "secret_name" {
  description = "Secret Manager secret name for OpenAI API key"
  value       = google_secret_manager_secret.openai_key.secret_id
}

output "service_account_email" {
  description = "Service account email for the RAG agent"
  value       = google_service_account.rag_agent.email
}

output "deployment_info" {
  description = "Complete deployment information"
  value = {
    service_url           = google_cloud_run_v2_service.rag_agent.uri
    organization         = var.organization_name
    project_id          = var.project_id
    region              = var.region
    data_bucket         = google_storage_bucket.data_storage.name
    secret_name         = google_secret_manager_secret.openai_key.secret_id
    service_account     = google_service_account.rag_agent.email
    max_instances       = var.max_instances
    min_instances       = var.min_instances
    cpu_limit           = var.cpu_limit
    memory_limit        = var.memory_limit
    public_access       = var.enable_public_access
  }
}