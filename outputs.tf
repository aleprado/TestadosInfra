output "bucket_name" {
  description = "El nombre del bucket de Cloud Storage creado"
  value       = length(google_storage_bucket.data_bucket) > 0 ? google_storage_bucket.data_bucket[0].name : data.google_storage_bucket.existing_data_bucket.name
}

output "function_name" {
  description = "El nombre de la función de Cloud Functions creada"
  value       = google_cloudfunctions_function.csv_processor.name
}
