provider "google" {
  project     = var.project_id
  region      = var.region
  credentials = file(var.credentials_file)
}

# Detectar si el bucket de datos ya existe
data "google_storage_bucket" "existing_data_bucket" {
  name = var.data_bucket_name
}

# Detectar si el bucket de funciones ya existe
data "google_storage_bucket" "existing_function_bucket" {
  name = var.function_bucket_name
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

# Subir el archivo ZIP de la función al bucket de funciones
resource "google_storage_bucket_object" "upload_trigger" {
  name   = "function_trigger.zip"
  bucket = length(google_storage_bucket.function_bucket) > 0 ? google_storage_bucket.function_bucket[0].name : data.google_storage_bucket.existing_function_bucket.name
  source = "${path.module}/function/function_trigger.zip"
}

# Crear la función de Cloud Functions
resource "google_cloudfunctions_function" "csv_processor" {
  name                  = "csvProcessor"
  runtime               = "python310"
  source_archive_bucket = google_storage_bucket_object.upload_trigger.bucket
  source_archive_object = google_storage_bucket_object.upload_trigger.name
  entry_point           = "process_csv"
  environment_variables = {
    GOOGLE_RUNTIME = "python310"
  }
  event_trigger {
    event_type = "google.storage.object.finalize"
    resource   = length(google_storage_bucket.data_bucket) > 0 ? google_storage_bucket.data_bucket[0].name : data.google_storage_bucket.existing_data_bucket.name
  }
}
