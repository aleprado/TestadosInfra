output "bucket_name" {
  description = "El nombre del bucket de Cloud Storage creado"
  value       = google_storage_bucket.data_bucket.name
}

output "function_name" {
  description = "El nombre de la función de Cloud Functions creada"
  value       = google_cloudfunctions_function.csv_processor.name
}
