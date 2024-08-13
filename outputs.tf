output "export_bucket_name" {
  description = "El nombre del bucket de Cloud Storage para las exportaciones creado"
  value       = length(google_storage_bucket.export_bucket) > 0 ? google_storage_bucket.export_bucket[0].name : data.google_storage_bucket.existing_export_bucket.name
}

output "function_bucket_name" {
  description = "El nombre del bucket de Cloud Storage para la función creado"
  value       = length(google_storage_bucket.function_bucket) > 0 ? google_storage_bucket.function_bucket[0].name : data.google_storage_bucket.existing_function_bucket.name
}

output "export_function_name" {
  description = "El nombre de la función de Cloud Functions creada para exportar subcolecciones"
  value       = google_cloudfunctions_function.export_csv.name
}
