output "data_bucket_name" {
  description = "El nombre del bucket de Cloud Storage para datos creado"
  value       = length(google_storage_bucket.data_bucket) > 0 ? google_storage_bucket.data_bucket[0].name : data.google_storage_bucket.existing_data_bucket.name
}

output "function_bucket_name" {
  description = "El nombre del bucket de Cloud Storage para la función creado"
  value       = length(google_storage_bucket.function_bucket) > 0 ? google_storage_bucket.function_bucket[0].name : data.google_storage_bucket.existing_function_bucket.name
}

output "function_name" {
  description = "El nombre de la función de Cloud Functions creada"
  value       = google_cloudfunctions_function.csv_processor.name
}
