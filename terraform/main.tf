data "google_project" "current" {}

locals {
  services = toset([
    "aiplatform.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudscheduler.googleapis.com",
    "documentai.googleapis.com",
    "firestore.googleapis.com",
    "iamcredentials.googleapis.com",
    "run.googleapis.com",
    "storage.googleapis.com",
  ])

  deploy_services  = var.backend_image != "" && var.frontend_image != ""
  backend_audience = "https://loan-agent-backend-${data.google_project.current.number}.${var.region}.run.app"
}

resource "google_project_service" "required" {
  for_each = local.services
  project  = var.project_id
  service  = each.value

  disable_on_destroy = false
}

resource "google_artifact_registry_repository" "loan_agent" {
  location      = var.region
  repository_id = "loan-agent"
  description   = "Loan application assistant container images"
  format        = "DOCKER"

  depends_on = [google_project_service.required]
}

resource "google_storage_bucket" "documents" {
  name                        = "${var.project_id}-loan-applications"
  location                    = var.bucket_location
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  versioning {
    enabled = true
  }

  cors {
    origin          = var.frontend_origins
    method          = ["PUT"]
    response_header = ["Content-Type", "ETag"]
    max_age_seconds = 3600
  }

  depends_on = [google_project_service.required]
}

resource "google_firestore_database" "applications" {
  project                     = var.project_id
  name                        = "(default)"
  location_id                 = var.firestore_location
  type                        = "FIRESTORE_NATIVE"
  concurrency_mode            = "PESSIMISTIC"
  app_engine_integration_mode = "DISABLED"
  deletion_policy             = "ABANDON"

  depends_on = [google_project_service.required]
}

resource "google_service_account" "backend" {
  account_id   = "loan-agent-backend"
  display_name = "Loan agent backend runtime"
}

resource "google_service_account" "frontend" {
  account_id   = "loan-agent-frontend"
  display_name = "Loan agent frontend runtime"
}

resource "google_service_account" "reset_scheduler" {
  account_id   = "loan-agent-reset-scheduler"
  display_name = "Loan agent inactivity reset scheduler"
}

locals {
  backend_roles = toset([
    "roles/aiplatform.user",
    "roles/datastore.user",
    "roles/documentai.apiUser",
  ])
}

resource "google_project_iam_member" "backend_roles" {
  for_each = local.backend_roles
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.backend.email}"
}

resource "google_storage_bucket_iam_member" "backend_documents" {
  bucket = google_storage_bucket.documents.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.backend.email}"
}

resource "google_service_account_iam_member" "backend_signer" {
  service_account_id = google_service_account.backend.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:${google_service_account.backend.email}"
}

locals {
  cloud_build_account = "${data.google_project.current.number}@cloudbuild.gserviceaccount.com"
  cloud_build_roles   = toset(["roles/artifactregistry.writer"])
}

resource "google_project_iam_member" "cloud_build_roles" {
  for_each = local.cloud_build_roles
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${local.cloud_build_account}"
}

resource "google_cloud_run_v2_service" "backend" {
  count    = local.deploy_services ? 1 : 0
  name     = "loan-agent-backend"
  location = var.region

  template {
    service_account = google_service_account.backend.email

    containers {
      image = var.backend_image

      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = var.region
      }
      env {
        name  = "APPLICATION_STORE"
        value = "firestore"
      }
      env {
        name  = "FIRESTORE_COLLECTION"
        value = "loan_applications"
      }
      env {
        name  = "UPLOAD_BUCKET"
        value = google_storage_bucket.documents.name
      }
      env {
        name  = "DOCAI_LOCATION"
        value = var.document_ai_location
      }
      env {
        name  = "DOCAI_PROCESSOR_ID"
        value = var.document_ai_processor_id
      }
      env {
        name  = "BACKEND_SERVICE_ACCOUNT_EMAIL"
        value = google_service_account.backend.email
      }
      env {
        name  = "ALLOWED_ORIGINS"
        value = join(",", var.frontend_origins)
      }
      env {
        name  = "GOOGLE_GENAI_USE_VERTEXAI"
        value = "true"
      }
      env {
        name  = "RESET_SCHEDULER_SERVICE_ACCOUNT"
        value = google_service_account.reset_scheduler.email
      }
      env {
        name  = "RESET_SWEEP_AUDIENCE"
        value = local.backend_audience
      }
    }
  }

  depends_on = [
    google_firestore_database.applications,
    google_project_iam_member.backend_roles,
    google_storage_bucket_iam_member.backend_documents,
  ]
}

resource "google_cloud_run_v2_service" "frontend" {
  count    = local.deploy_services ? 1 : 0
  name     = "loan-agent-frontend"
  location = var.region

  template {
    service_account = google_service_account.frontend.email
    containers {
      image = var.frontend_image
      env {
        name  = "LOAN_API_BASE"
        value = google_cloud_run_v2_service.backend[0].uri
      }
    }
  }

  depends_on = [google_project_service.required]
}

resource "google_cloud_run_v2_service_iam_member" "backend_public" {
  count    = local.deploy_services ? 1 : 0
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.backend[0].name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_service_iam_member" "frontend_public" {
  count    = local.deploy_services ? 1 : 0
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.frontend[0].name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_service_iam_member" "reset_scheduler_invoker" {
  count    = local.deploy_services ? 1 : 0
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.backend[0].name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.reset_scheduler.email}"
}

resource "google_cloud_scheduler_job" "reset_inactive_applications" {
  count       = local.deploy_services ? 1 : 0
  name        = "loan-agent-reset-inactive-applications"
  description = "Reset demo applications after five minutes of inactivity."
  region      = var.region
  schedule    = "* * * * *"
  time_zone   = "Etc/UTC"

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_v2_service.backend[0].uri}/api/maintenance/reset-inactive"

    oidc_token {
      service_account_email = google_service_account.reset_scheduler.email
      audience              = local.backend_audience
    }
  }

  depends_on = [
    google_cloud_run_v2_service_iam_member.reset_scheduler_invoker,
    google_project_service.required,
  ]
}
