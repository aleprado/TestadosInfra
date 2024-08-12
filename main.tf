provider "google" {
  project     = var.project_id
  region      = var.region
  credentials = file(var.credentials_file)
}

# Detectar si el bucket para datos ya existe
data "google_storage_bucket" "existing_data_bucket" {
  name = var.data_bucket_name
}

# Detectar si el bucket para la función ya existe
data "google_storage_bucket" "existing_function_bucket" {
  name = var.function_bucket_name
}

# Crear el bucket para datos solo si no existe
resource "google_storage_bucket" "data_bucket" {
  name     = var.data_bucket_name
  location = var.region

  lifecycle {
    prevent_destroy = true
    ignore_changes  = [name, location]
  }

  count = data.google_storage_bucket.existing_data_bucket.id == null ? 1 : 0
}

# Crear el bucket para la función solo si no existe
resource "google_storage_bucket" "function_bucket" {
  name     = var.function_bucket_name
  location = var.region

  lifecycle {
    prevent_destroy = true
    ignore_changes  = [name, location]
  }

  count = data.google_storage_bucket.existing_function_bucket.id == null ? 1 : 0
}

# Subir el archivo ZIP de la función al bucket de funciones
resource "google_storage_bucket_object" "upload_trigger" {
  name   = "function_trigger.zip"
  bucket = google_storage_bucket.function_bucket[0].name
  source = "${path.module}/function/function_trigger.zip"
}

# Crear la función de Cloud Functions
resource "google_cloudfunctions_function" "csv_processor" {
  name                  = "csvProcessor"
  runtime               = "python310"
  source_archive_bucket = google_storage_bucket.function_bucket[0].name
  source_archive_object = google_storage_bucket_object.upload_trigger.name
  entry_point           = "process_csv"
  environment_variables = {
    GOOGLE_RUNTIME = "python310"
  }
  event_trigger {
    event_type = "google.storage.object.finalize"
    resource   = google_storage_bucket.data_bucket[0].name
  }
}
