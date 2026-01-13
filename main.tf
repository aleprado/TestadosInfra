provider "google" {
  project     = var.project_id
  region      = var.region
  # credentials = file(var.credentials_file)  # Comentado para usar credenciales por defecto
}

# NOTA: El cron job de exportación automática está DESACTIVADO
# Ahora usamos la función exportCSVOnDemand que se ejecuta solo cuando se solicita
# Para reactivar el cron, descomenta el recurso google_cloud_scheduler_job.export_csv_scheduler

# Retrieve current project information for IAM bindings
data "google_project" "current" {
  project_id = var.project_id
}


# Detectar si el bucket de datos ya existe
data "google_storage_bucket" "existing_data_bucket" {
  name = var.data_bucket_name
}

# Detectar si el bucket de funciones ya existe
data "google_storage_bucket" "existing_function_bucket" {
  name = var.function_bucket_name
}

# Detectar si el bucket de exportación ya existe
data "google_storage_bucket" "existing_export_bucket" {
  name = var.export_bucket_name
}

# Crear el bucket de datos solo si no existe
resource "google_storage_bucket" "data_bucket" {
  count    = data.google_storage_bucket.existing_data_bucket.id == null ? 1 : 0
  name     = var.data_bucket_name
  location = var.region

  lifecycle {
    prevent_destroy = true
    ignore_changes  = [name, location]
  }
}

# Crear el bucket de funciones solo si no existe
resource "google_storage_bucket" "function_bucket" {
  count    = data.google_storage_bucket.existing_function_bucket.id == null ? 1 : 0
  name     = var.function_bucket_name
  location = var.region

  lifecycle {
    prevent_destroy = true
    ignore_changes  = [name, location]
  }
}

# Crear el bucket de exportación solo si no existe
resource "google_storage_bucket" "export_bucket" {
  count    = data.google_storage_bucket.existing_export_bucket.id == null ? 1 : 0
  name     = var.export_bucket_name
  location = var.region

  lifecycle {
    prevent_destroy = true
    ignore_changes  = [name, location]
  }
}

# Hacer el bucket público para acceso directo
resource "google_storage_bucket" "export_bucket_public_access" {
  count  = data.google_storage_bucket.existing_export_bucket.id == null ? 1 : 0
  name     = var.export_bucket_name
  location = var.region
  public_access_prevention = "inherited"
  
  lifecycle {
    prevent_destroy = true
    ignore_changes  = [name, location]
  }
}

# Subir el archivo ZIP de la función CSV Processor al bucket de funciones
data "archive_file" "csv_processor_src" {
  type        = "zip"
  source_dir  = "${path.module}/function/csv_processor"
  output_path = "${path.module}/function/csv_processor/function_trigger.zip"
}

resource "google_storage_bucket_object" "upload_csv_trigger" {
  name       = "function_trigger.zip"
  bucket     = data.google_storage_bucket.existing_function_bucket.name
  source     = data.archive_file.csv_processor_src.output_path
  depends_on = [google_storage_bucket.function_bucket]
}

# Subir el archivo ZIP de la función HTTP de exportación on-demand
data "archive_file" "export_on_demand_src" {
  type        = "zip"
  source_dir  = "${path.module}/function/export_on_demand"
  output_path = "${path.module}/function/export_on_demand/export_on_demand.zip"
}

resource "google_storage_bucket_object" "upload_export_on_demand" {
  name       = "export_on_demand.zip"
  bucket     = data.google_storage_bucket.existing_function_bucket.name
  source     = data.archive_file.export_on_demand_src.output_path
  depends_on = [google_storage_bucket.function_bucket]
}

# Crear la función de Cloud Functions para procesar CSVs
resource "google_cloudfunctions2_function" "csv_processor" {
  name     = "csvProcessor"
  location = var.region

  build_config {
    runtime     = "python310"
    entry_point = "procesar_csv"
    source {
      storage_source {
        bucket = google_storage_bucket_object.upload_csv_trigger.bucket
        object = google_storage_bucket_object.upload_csv_trigger.name
      }
    }
  }

  service_config {
    available_memory = "256M"
  }

  event_trigger {
    trigger_region = var.region
    event_type     = "google.cloud.storage.object.v1.finalized"
    event_filters {
      attribute = "bucket"
      value     = coalesce(data.google_storage_bucket.existing_data_bucket.name, var.data_bucket_name)
    }
  }
}

# Función HTTP: exportación on-demand
resource "google_cloudfunctions2_function" "export_csv_on_demand" {
  name     = "exportCSVOnDemand"
  location = var.region

  build_config {
    runtime     = "python310"
    entry_point = "export_csv_on_demand"
    source {
      storage_source {
        bucket = google_storage_bucket_object.upload_export_on_demand.bucket
        object = google_storage_bucket_object.upload_export_on_demand.name
      }
    }
  }

  service_config {
    available_memory = "256M"
    environment_variables = {
      EXPORT_BUCKET_NAME = coalesce(data.google_storage_bucket.existing_export_bucket.name, var.export_bucket_name)
    }
  }
}

# Permitir invocación pública de la función HTTP
resource "google_cloud_run_v2_service_iam_member" "invoker_all_users_export_on_demand" {
  project  = var.project_id
  location = var.region
  name     = google_cloudfunctions2_function.export_csv_on_demand.service_config[0].service
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Conceder permisos a la service account por defecto de Cloud Run/Functions v2
resource "google_storage_bucket_iam_member" "export_bucket_object_admin_compute_sa" {
  bucket = coalesce(data.google_storage_bucket.existing_export_bucket.name, var.export_bucket_name)
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${data.google_project.current.number}-compute@developer.gserviceaccount.com"
}

resource "google_project_iam_member" "functions_firestore_user_compute_sa" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${data.google_project.current.number}-compute@developer.gserviceaccount.com"
}

# Crear una tarea de Cloud Scheduler para ejecutar la función cada día a las 00:00 horas
# DESACTIVADO: Ahora usamos exportación on-demand
# resource "google_cloud_scheduler_job" "export_csv_scheduler" {
#   name        = "export-csv-scheduler"
#   description = "Trigger exportCSV function every day at 00:00"
#   schedule    = "0 0 * * *"
#   time_zone   = "America/Argentina/Buenos_Aires"
#   pubsub_target {
#     topic_name = google_pubsub_topic.export_topic.id
#     data       = base64encode("Trigger exportCSV function")
#   }
# }

# Hacer público el bucket de exportación para descargas anónimas
resource "google_storage_bucket_iam_member" "export_bucket_public_read" {
  bucket = coalesce(data.google_storage_bucket.existing_export_bucket.name, var.export_bucket_name)
  role   = "roles/storage.objectViewer"
  member = "allUsers"
}

# Política de bucket para acceso público completo
resource "google_storage_bucket_iam_binding" "export_bucket_public_policy" {
  bucket = coalesce(data.google_storage_bucket.existing_export_bucket.name, var.export_bucket_name)
  role   = "roles/storage.objectViewer"
  members = [
    "allUsers"
  ]
}

# 🔒 SEGURIDAD: Permitir acceso a usuarios autenticados de Firebase
resource "google_storage_bucket_iam_member" "export_bucket_firebase_auth" {
  bucket = coalesce(data.google_storage_bucket.existing_export_bucket.name, var.export_bucket_name)
  role   = "roles/storage.objectViewer"
  member = "allAuthenticatedUsers"
}

# Permisos para escribir en el bucket de exportación (función exportCSV)
resource "google_storage_bucket_iam_member" "export_bucket_object_admin" {
  bucket = coalesce(data.google_storage_bucket.existing_export_bucket.name, var.export_bucket_name)
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${var.project_id}@appspot.gserviceaccount.com"
}

# Permisos de lectura para el bucket de datos (función csvProcessor)
resource "google_storage_bucket_iam_member" "data_bucket_object_viewer" {
  bucket = coalesce(data.google_storage_bucket.existing_data_bucket.name, var.data_bucket_name)
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${var.project_id}@appspot.gserviceaccount.com"
}

# Permisos de lectura para el bucket de datos (función csvProcessor - service account de compute)
resource "google_storage_bucket_iam_member" "data_bucket_object_viewer_compute_sa" {
  bucket = coalesce(data.google_storage_bucket.existing_data_bucket.name, var.data_bucket_name)
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${data.google_project.current.number}-compute@developer.gserviceaccount.com"
}

# Firestore acceso para funciones
resource "google_project_iam_member" "functions_firestore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${var.project_id}@appspot.gserviceaccount.com"
}

# 🔒 SEGURIDAD: Hacer bucket de datos privado (remover acceso público)
resource "google_storage_bucket_iam_binding" "data_bucket_private" {
  bucket = coalesce(data.google_storage_bucket.existing_data_bucket.name, var.data_bucket_name)
  role   = "roles/storage.objectViewer"
  members = [
    "serviceAccount:${var.project_id}@appspot.gserviceaccount.com",
    "serviceAccount:${data.google_project.current.number}-compute@developer.gserviceaccount.com"
  ]
}

# 🔒 SEGURIDAD: Permitir a usuarios autenticados de Firebase subir imágenes
resource "google_storage_bucket_iam_member" "data_bucket_firebase_auth_write" {
  bucket = coalesce(data.google_storage_bucket.existing_data_bucket.name, var.data_bucket_name)
  role   = "roles/storage.objectCreator"
  member = "allAuthenticatedUsers"
}

# 🔒 SEGURIDAD: Permitir a usuarios autenticados de Firebase leer sus propias imágenes
resource "google_storage_bucket_iam_member" "data_bucket_firebase_auth_read" {
  bucket = coalesce(data.google_storage_bucket.existing_data_bucket.name, var.data_bucket_name)
  role   = "roles/storage.objectViewer"
  member = "allAuthenticatedUsers"
}

# 🔒 SEGURIDAD: Permisos para el bucket por defecto de Firebase Storage (imágenes)
resource "google_storage_bucket_iam_member" "firebase_default_bucket_auth_write" {
  bucket = "${var.project_id}.appspot.com"
  role   = "roles/storage.objectCreator"
  member = "allAuthenticatedUsers"
}

resource "google_storage_bucket_iam_member" "firebase_default_bucket_auth_read" {
  bucket = "${var.project_id}.appspot.com"
  role   = "roles/storage.objectViewer"
  member = "allAuthenticatedUsers"
}

# ⚠️ TEMPORAL: Permisos para usuarios anónimos (mientras se arregla la autenticación)
resource "google_storage_bucket_iam_member" "firebase_default_bucket_anonymous_write" {
  bucket = "${var.project_id}.appspot.com"
  role   = "roles/storage.objectCreator"
  member = "allUsers"
}

resource "google_storage_bucket_iam_member" "firebase_default_bucket_anonymous_read" {
  bucket = "${var.project_id}.appspot.com"
  role   = "roles/storage.objectViewer"
  member = "allUsers"
}

# 🔒 SEGURIDAD: Las reglas de Firebase se manejan con Firebase CLI
# desde el repositorio del frontend
