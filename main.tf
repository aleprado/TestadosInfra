provider "google" {
  project     = var.project_id
  region      = var.region
  credentials = file(var.credentials_file)
}

# Detectar si el bucket de exportación ya existe
data "google_storage_bucket" "existing_export_bucket" {
  name = var.export_bucket_name
}

# Detectar si el bucket de funciones ya existe
data "google_storage_bucket" "existing_function_bucket" {
  name = var.function_bucket_name
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

# Subir el archivo ZIP de la nueva función al bucket de funciones
resource "google_storage_bucket_object" "upload_export_trigger" {
  name   = "export_trigger.zip"
  bucket = length(google_storage_bucket.function_bucket) > 0 ? google_storage_bucket.function_bucket[0].name : data.google_storage_bucket.existing_function_bucket.name
  source = "${path.module}/function/export_trigger.zip"
}

# Crear la función de Cloud Functions para exportar subcolecciones
resource "google_cloudfunctions_function" "export_csv" {
  name                  = "exportCSV"
  runtime               = "python310"
  source_archive_bucket = google_storage_bucket_object.upload_export_trigger.bucket
  source_archive_object = google_storage_bucket_object.upload_export_trigger.name
  entry_point           = "export_subcollections"
  environment_variables = {
    EXPORT_BUCKET_NAME = length(google_storage_bucket.export_bucket) > 0 ? google_storage_bucket.export_bucket[0].name : data.google_storage_bucket.existing_export_bucket.name
  }

  event_trigger {
    event_type = "providers/cloud.pubsub/eventTypes/topic.publish"
    resource   = google_pubsub_topic.export_topic.id
  }
}

# Crear un Pub/Sub topic para disparar la función exportCSV
resource "google_pubsub_topic" "export_topic" {
  name = "export-csv-topic"
}

# Crear una tarea de Cloud Scheduler para ejecutar la función cada día a las 00:00 horas
resource "google_cloud_scheduler_job" "export_csv_scheduler" {
  name             = "export-csv-scheduler"
  description      = "Trigger exportCSV function every day at 00:00"
  schedule         = "0 0 * * *"
  time_zone        = "America/Argentina/Buenos_Aires" # Ajusta la zona horaria según sea necesario
  pubsub_target {
    topic_name = google_pubsub_topic.export_topic.id
    data       = base64encode("Trigger exportCSV function")
  }
}
