provider "google" {
  project     = var.project_id
  region      = var.region
  credentials = file(var.credentials_file)
}

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

# Subir el archivo ZIP de la función Export Subcollections al bucket de funciones
data "archive_file" "export_src" {
  type        = "zip"
  source_dir  = "${path.module}/function/export"
  output_path = "${path.module}/function/export/export_trigger.zip"
}

resource "google_storage_bucket_object" "upload_export_trigger" {
  name       = "export_trigger.zip"
  bucket     = data.google_storage_bucket.existing_function_bucket.name
  source     = data.archive_file.export_src.output_path
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

# Crear la función de Cloud Functions para exportar subcolecciones
resource "google_cloudfunctions2_function" "export_csv" {
  name     = "exportCSV"
  location = var.region

  build_config {
    runtime     = "python310"
    entry_point = "export_subcollections"
    source {
      storage_source {
        bucket = google_storage_bucket_object.upload_export_trigger.bucket
        object = google_storage_bucket_object.upload_export_trigger.name
      }
    }
  }

  service_config {
    available_memory = "256M"
  }

  event_trigger {
    trigger_region = var.region
    event_type     = "google.cloud.pubsub.topic.v1.messagePublished"
    pubsub_topic   = google_pubsub_topic.export_topic.id
  }
}

# Crear un Pub/Sub topic para disparar la función exportCSV
resource "google_pubsub_topic" "export_topic" {
  name = "export-csv-topic"
}

# Crear una tarea de Cloud Scheduler para ejecutar la función cada día a las 00:00 horas
resource "google_cloud_scheduler_job" "export_csv_scheduler" {
  name        = "export-csv-scheduler"
  description = "Trigger exportCSV function every day at 00:00"
  schedule    = "0 0 * * *"
  time_zone   = "America/Argentina/Buenos_Aires"
  pubsub_target {
    topic_name = google_pubsub_topic.export_topic.id
    data       = base64encode("Trigger exportCSV function")
  }
}
