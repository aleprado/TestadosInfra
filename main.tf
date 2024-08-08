provider "google" {
  project = var.project_id
  region  = var.region
  credentials = file(var.credentials_file)
}

resource "google_storage_bucket" "data_bucket" {
  name     = "${var.bucket_name}"
  location = var.region
}

resource "google_storage_bucket_object" "upload_trigger" {
  name   = "function_trigger.zip"
  bucket = google_storage_bucket.data_bucket.name
  source = "${path.module}/function/function_trigger.zip"
}

resource "google_cloudfunctions_function" "csv_processor" {
  name                  = "csvProcessor"
  runtime               = "python310"
  source_archive_bucket = google_storage_bucket.data_bucket.name
  source_archive_object = google_storage_bucket_object.upload_trigger.name
  trigger_http          = false
  event_trigger {
    event_type = "google.storage.object.finalize"
    resource   = google_storage_bucket.data_bucket.name
  }
  entry_point = "process_csv"
  environment_variables = {
    GOOGLE_RUNTIME = "python310"
  }
}
