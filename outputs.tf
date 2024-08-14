output "export_bucket_name" {
  description = "El nombre del bucket de Cloud Storage de exportación creado"
  value       = length(google_storage_bucket.export_bucket) > 0 ? google_storage_bucket.export_bucket[0].name : data.google_storage_bucket.existing_export_bucket.name
}

output "function_bucket_name" {
  description = "El nombre del bucket de funciones creado"
  value       = length(google_storage_bucket.function_bucket) > 0 ? google_storage_bucket.function_bucket[0].name : data.google_storage_bucket.existing_function_bucket.name
}

output "csv_function_name" {
  description = "El nombre de la función de Cloud Functions para procesar CSV creada"
  value       = google_cloudfunctions_function.csv_processor.name
}

output "export_function_name" {
  description = "El nombre de la función de Cloud Functions para exportar subcolecciones creada"
  value       = google_cloudfunctions_function.export_csv.name
}
