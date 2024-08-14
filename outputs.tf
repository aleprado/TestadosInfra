¿output "data_bucket_name" {
  description = "El nombre del bucket de Cloud Storage para datos"
  value       = google_storage_bucket.data_bucket[0].name
}

output "function_bucket_name" {
  description = "El nombre del bucket de Cloud Storage para funciones"
  value       = google_storage_bucket.function_bucket[0].name
}

output "export_bucket_name" {
  description = "El nombre del bucket de Cloud Storage para exportaciones"
  value       = google_storage_bucket.export_bucket[0].name
}

output "csv_processor_function_name" {
  description = "El nombre de la función de Cloud Functions creada para procesar CSV"
  value       = google_cloudfunctions_function.csv_processor.name
}

output "export_function_name" {
  description = "El nombre de la función de Cloud Functions creada para exportar subcolecciones"
  value       = google_cloudfunctions_function.export_csv.name
}
