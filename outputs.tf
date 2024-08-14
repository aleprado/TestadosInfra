output "data_bucket_name" {
  description = "El nombre del bucket de Cloud Storage para datos"
  value       = coalesce(data.google_storage_bucket.existing_data_bucket.name, var.data_bucket_name)
}

output "function_bucket_name" {
  description = "El nombre del bucket de Cloud Storage para funciones"
  value       = coalesce(data.google_storage_bucket.existing_function_bucket.name, var.function_bucket_name)
}

output "export_bucket_name" {
  description = "El nombre del bucket de Cloud Storage para exportaciones"
  value       = coalesce(data.google_storage_bucket.existing_export_bucket.name, var.export_bucket_name)
}

output "csv_processor_function_name" {
  description = "El nombre de la función de Cloud Functions creada para procesar CSV"
  value       = google_cloudfunctions_function.csv_processor.name
}

output "export_function_name" {
  description = "El nombre de la función de Cloud Functions creada para exportar subcolecciones"
  value       = google_cloudfunctions_function.export_csv.name
}
