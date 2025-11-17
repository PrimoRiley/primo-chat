# Configure the Google Cloud Provider
provider "google" {
  project = var.project_id
  region  = var.region
}

# Service account for Cloud Run
resource "google_service_account" "rag_agent" {
  account_id   = "${var.organization_name}-rag-agent"
  display_name = "${var.organization_name} RAG Agent Service Account"
  description  = "Service account for RAG agent Cloud Run service"
}

# Secret Manager secret for OpenAI API key
resource "google_secret_manager_secret" "openai_key" {
  secret_id = "${var.organization_name}-openai-key"
  
  replication {
    auto {}
  }
  
  labels = {
    organization = var.organization_name
    environment  = "production"
    service      = "rag-agent"
  }
}

# Secret version with the actual API key
resource "google_secret_manager_secret_version" "openai_key_version" {
  secret      = google_secret_manager_secret.openai_key.id
  secret_data = var.openai_api_key
}

# IAM binding for service account to access the secret
resource "google_secret_manager_secret_iam_member" "openai_key_access" {
  secret_id = google_secret_manager_secret.openai_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.rag_agent.email}"
}

# GCS bucket for SQLite data persistence (using Cloud Storage FUSE)
resource "google_storage_bucket" "data_storage" {
  name          = "${var.organization_name}-rag-data"
  location      = var.region
  force_destroy = false # Protect against accidental deletion
  
  # Versioning for backup
  versioning {
    enabled = true
  }
  
  # Lifecycle rules
  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }
  
  # Uniform bucket-level access
  uniform_bucket_level_access = true
  
  labels = {
    organization = var.organization_name
    environment  = "production"
    service      = "rag-agent"
    purpose      = "data-storage"
  }
}

# IAM for service account to access the storage bucket
resource "google_storage_bucket_iam_member" "data_storage_access" {
  bucket = google_storage_bucket.data_storage.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.rag_agent.email}"
}

# Cloud Run service
resource "google_cloud_run_v2_service" "rag_agent" {
  name     = "${var.organization_name}-rag-agent"
  location = var.region
  
  template {
    # Service account
    service_account = google_service_account.rag_agent.email
    
    # Timeout
    timeout = "${var.timeout_seconds}s"
    
    # Scaling configuration
    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }
    
    # Container specification
    containers {
      image = "gcr.io/${var.project_id}/${var.organization_name}-rag-agent:latest"
      
      # Resource limits
      resources {
        limits = {
          cpu    = var.cpu_limit
          memory = var.memory_limit
        }
        cpu_idle = true
        startup_cpu_boost = true
      }
      
      # Environment variables
      env {
        name = "ORGANIZATION_NAME"
        value = var.organization_name
      }
      
      env {
        name = "ORGANIZATION_DISPLAY_NAME"
        value = replace(title(replace(var.organization_name, "-", " ")), " ", " ")
      }
      
      env {
        name = "GCP_PROJECT_ID"
        value = var.project_id
      }
      
      env {
        name = "GCP_REGION"
        value = var.region
      }
      
      env {
        name = "DATA_DIRECTORY"
        value = "/data"
      }
      
      # OpenAI API key from Secret Manager
      env {
        name = "OPENAI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.openai_key.secret_id
            version = "latest"
          }
        }
      }
      
      # Mount point for data storage
      volume_mounts {
        name       = "data"
        mount_path = "/data"
      }
      
      # Health check port
      ports {
        container_port = 8000
      }
      
      # Startup probe
      startup_probe {
        http_get {
          path = "/health"
          port = 8000
        }
        initial_delay_seconds = 10
        timeout_seconds       = 5
        period_seconds        = 10
        failure_threshold     = 3
      }
      
      # Liveness probe
      liveness_probe {
        http_get {
          path = "/health"
          port = 8000
        }
        initial_delay_seconds = 30
        timeout_seconds       = 5
        period_seconds        = 30
        failure_threshold     = 3
      }
    }
    
    # Volume configuration for data persistence
    volumes {
      name = "data"
      gcs {
        bucket    = google_storage_bucket.data_storage.name
        read_only = false
      }
    }
  }
  
  # Traffic allocation
  traffic {
    percent = 100
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
  }
  
  depends_on = [
    google_secret_manager_secret_iam_member.openai_key_access,
    google_storage_bucket_iam_member.data_storage_access
  ]
}

# IAM policy for public access (if enabled)
resource "google_cloud_run_service_iam_member" "public_access" {
  count = var.enable_public_access ? 1 : 0
  
  service  = google_cloud_run_v2_service.rag_agent.name
  location = google_cloud_run_v2_service.rag_agent.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Cloud Build trigger for automatic deployments (optional)
resource "google_cloudbuild_trigger" "deploy_trigger" {
  name     = "${var.organization_name}-rag-agent-deploy"
  location = var.region
  
  github {
    owner = "PrimoRiley"  # Replace with your GitHub username
    name  = "primo-chat"   # Replace with your repository name
    push {
      branch = "^main$"
    }
  }
  
  build {
    step {
      name = "gcr.io/cloud-builders/docker"
      args = [
        "build",
        "-t", "gcr.io/${var.project_id}/${var.organization_name}-rag-agent:$SHORT_SHA",
        "-t", "gcr.io/${var.project_id}/${var.organization_name}-rag-agent:latest",
        "."
      ]
    }
    
    step {
      name = "gcr.io/cloud-builders/docker"
      args = [
        "push", 
        "gcr.io/${var.project_id}/${var.organization_name}-rag-agent:$SHORT_SHA"
      ]
    }
    
    step {
      name = "gcr.io/cloud-builders/docker"
      args = [
        "push", 
        "gcr.io/${var.project_id}/${var.organization_name}-rag-agent:latest"
      ]
    }
    
    step {
      name = "gcr.io/cloud-builders/gcloud"
      args = [
        "run", "deploy", "${var.organization_name}-rag-agent",
        "--image", "gcr.io/${var.project_id}/${var.organization_name}-rag-agent:$SHORT_SHA",
        "--region", var.region,
        "--platform", "managed"
      ]
    }
  }
}