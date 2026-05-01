locals {
  wif_pool_id     = "gradepilot-gh"
  wif_provider_id = "github"

  deployer_sa_id   = "gradepilot-deployer"
  runtime_api_sa   = "gradepilot-api-runtime"
  runtime_web_sa   = "gradepilot-web-runtime"
  secrets_prefix   = "gradepilot"
  container_port   = 8080
  api_env_required = {
    SUPABASE_URL = var.supabase_url
    DATABASE_URL = var.database_url
  }
}

resource "google_artifact_registry_repository" "containers" {
  location      = var.region
  repository_id = var.artifact_registry_repo
  description   = "GradePilot container images"
  format        = "DOCKER"
}

# ---- Workload Identity Federation for GitHub Actions (OIDC) ----

resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = local.wif_pool_id
  display_name              = "GradePilot GitHub Actions"
  description               = "OIDC identity pool for GitHub Actions"
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = local.wif_provider_id
  display_name                       = "GitHub"

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
    "attribute.ref"        = "assertion.ref"
    "attribute.actor"      = "assertion.actor"
  }

  attribute_condition = "attribute.repository == \"${var.github_repository}\""
}

resource "google_service_account" "deployer" {
  account_id   = local.deployer_sa_id
  display_name = "GradePilot GitHub deployer"
}

resource "google_service_account_iam_member" "deployer_wif" {
  service_account_id = google_service_account.deployer.name
  role               = "roles/iam.workloadIdentityUser"
  member = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repository}"
}

resource "google_project_iam_member" "deployer_run_admin" {
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.deployer.email}"
  project = var.project_id
}

resource "google_project_iam_member" "deployer_sa_user" {
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.deployer.email}"
  project = var.project_id
}

resource "google_project_iam_member" "deployer_ar_writer" {
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.deployer.email}"
  project = var.project_id
}

# ---- Runtime service accounts ----

resource "google_service_account" "api_runtime" {
  account_id   = local.runtime_api_sa
  display_name = "GradePilot API runtime"
}

resource "google_service_account" "web_runtime" {
  account_id   = local.runtime_web_sa
  display_name = "GradePilot Web runtime"
}

# ---- Secrets (values injected via TF variables / GitHub secrets) ----

resource "google_secret_manager_secret" "supabase_url" {
  secret_id = "${local.secrets_prefix}-supabase-url"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "supabase_url" {
  secret      = google_secret_manager_secret.supabase_url.id
  secret_data = var.supabase_url
}

resource "google_secret_manager_secret" "database_url" {
  secret_id = "${local.secrets_prefix}-database-url"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "database_url" {
  secret      = google_secret_manager_secret.database_url.id
  secret_data = var.database_url
}

resource "google_secret_manager_secret" "google_api_key" {
  count    = var.google_api_key != "" ? 1 : 0
  secret_id = "${local.secrets_prefix}-google-api-key"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "google_api_key" {
  count       = var.google_api_key != "" ? 1 : 0
  secret      = google_secret_manager_secret.google_api_key[0].id
  secret_data = var.google_api_key
}

resource "google_secret_manager_secret" "google_oauth_client_id" {
  count    = var.google_oauth_client_id != "" ? 1 : 0
  secret_id = "${local.secrets_prefix}-google-oauth-client-id"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "google_oauth_client_id" {
  count       = var.google_oauth_client_id != "" ? 1 : 0
  secret      = google_secret_manager_secret.google_oauth_client_id[0].id
  secret_data = var.google_oauth_client_id
}

resource "google_secret_manager_secret" "google_oauth_client_secret" {
  count    = var.google_oauth_client_secret != "" ? 1 : 0
  secret_id = "${local.secrets_prefix}-google-oauth-client-secret"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "google_oauth_client_secret" {
  count       = var.google_oauth_client_secret != "" ? 1 : 0
  secret      = google_secret_manager_secret.google_oauth_client_secret[0].id
  secret_data = var.google_oauth_client_secret
}

resource "google_secret_manager_secret" "google_oauth_redirect_uri" {
  count    = var.google_oauth_redirect_uri != "" ? 1 : 0
  secret_id = "${local.secrets_prefix}-google-oauth-redirect-uri"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "google_oauth_redirect_uri" {
  count       = var.google_oauth_redirect_uri != "" ? 1 : 0
  secret      = google_secret_manager_secret.google_oauth_redirect_uri[0].id
  secret_data = var.google_oauth_redirect_uri
}

# Frontend public envs (still secrets in CI; injected at build time)
resource "google_secret_manager_secret" "frontend_supabase_url" {
  count     = var.frontend_supabase_url != "" ? 1 : 0
  secret_id = "${local.secrets_prefix}-frontend-supabase-url"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "frontend_supabase_url" {
  count       = var.frontend_supabase_url != "" ? 1 : 0
  secret      = google_secret_manager_secret.frontend_supabase_url[0].id
  secret_data = var.frontend_supabase_url
}

resource "google_secret_manager_secret" "frontend_supabase_anon_key" {
  count     = var.frontend_supabase_anon_key != "" ? 1 : 0
  secret_id = "${local.secrets_prefix}-frontend-supabase-anon-key"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "frontend_supabase_anon_key" {
  count       = var.frontend_supabase_anon_key != "" ? 1 : 0
  secret      = google_secret_manager_secret.frontend_supabase_anon_key[0].id
  secret_data = var.frontend_supabase_anon_key
}

# Allow runtimes to read secrets.
resource "google_project_iam_member" "api_runtime_secret_access" {
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.api_runtime.email}"
  project = var.project_id
}

resource "google_project_iam_member" "web_runtime_secret_access" {
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.web_runtime.email}"
  project = var.project_id
}

# ---- Cloud Run: API ----

resource "google_cloud_run_v2_service" "api" {
  name     = var.api_service_name
  location = var.region

  template {
    service_account = google_service_account.api_runtime.email
    containers {
      image = var.api_image

      ports {
        container_port = local.container_port
      }

      env {
        name = "SUPABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.supabase_url.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.database_url.secret_id
            version = "latest"
          }
        }
      }

      dynamic "env" {
        for_each = var.google_api_key != "" ? [1] : []
        content {
          name = "GOOGLE_API_KEY"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.google_api_key[0].secret_id
              version = "latest"
            }
          }
        }
      }

      dynamic "env" {
        for_each = var.google_oauth_client_id != "" ? [1] : []
        content {
          name = "GOOGLE_OAUTH_CLIENT_ID"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.google_oauth_client_id[0].secret_id
              version = "latest"
            }
          }
        }
      }

      dynamic "env" {
        for_each = var.google_oauth_client_secret != "" ? [1] : []
        content {
          name = "GOOGLE_OAUTH_CLIENT_SECRET"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.google_oauth_client_secret[0].secret_id
              version = "latest"
            }
          }
        }
      }

      dynamic "env" {
        for_each = var.google_oauth_redirect_uri != "" ? [1] : []
        content {
          name = "GOOGLE_OAUTH_REDIRECT_URI"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.google_oauth_redirect_uri[0].secret_id
              version = "latest"
            }
          }
        }
      }
    }
  }
}

resource "google_cloud_run_v2_service_iam_member" "api_invoker_public" {
  name     = google_cloud_run_v2_service.api.name
  location = google_cloud_run_v2_service.api.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ---- Cloud Run: Web ----

resource "google_cloud_run_v2_service" "web" {
  name     = var.web_service_name
  location = var.region

  template {
    service_account = google_service_account.web_runtime.email
    containers {
      image = var.web_image
      ports {
        container_port = local.container_port
      }
      # Note: NEXT_PUBLIC_* envs are baked at build time for client bundles.
      # We still set them here for server-side reads and debugging.
      env {
        name  = "NEXT_PUBLIC_BACKEND_URL"
        value = google_cloud_run_v2_service.api.uri
      }
    }
  }
}

resource "google_cloud_run_v2_service_iam_member" "web_invoker_public" {
  name     = google_cloud_run_v2_service.web.name
  location = google_cloud_run_v2_service.web.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

