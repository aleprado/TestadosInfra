provider "google" {
  project     = var.project_id
  region      = var.region
  credentials = file(var.credentials_file)
}

# Bucket para almacenar la función
resource "google_storage_bucket" "function_bucket" {
  name     = var.function_bucket_name
  location = var.region

  lifecycle {
    prevent_destroy = true
    ignore_changes  = [name, location]
  }
}

# Bucket para almacenar los archivos que la función procesará
resource "google_storage_bucket" "data_bucket" {
  name     = var.data_bucket_name
  location = var.region

  lifecycle {
    prevent_destroy = true
    ignore_changes  = [name, location]
  }
}

# Subir el archivo ZIP de la función al bucket de funciones
resource "google_storage_bucket_object" "upload_trigger" {
  name   = "function_trigger.zip"
  bucket = google_storage_bucket.function_bucket.name
  source = "${path.module}/function/function_trigger.zip"
}

# Crear la función de Cloud Functions
resource "google_cloudfunctions_function" "csv_processor" {
  name                  = "csvProcessor"
  runtime               = "python310"
  source_archive_bucket = google_storage_bucket.function_bucket.name
  source_archive_object = google_storage_bucket_object.upload_trigger.name
  entry_point           = "process_csv"
  environment_variables = {
    GOOGLE_RUNTIME = "python310"
  }
  event_trigger {
    event_type = "google.storage.object.finalize"
    resource   = google_storage_bucket.data_bucket.name
  }
}
