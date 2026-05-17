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
  value       = google_cloudfunctions2_function.csv_processor.name
}

output "export_csv_on_demand_url" {
  description = "La URL de la función HTTP de exportación on-demand"
  value       = google_cloudfunctions2_function.export_csv_on_demand.url
}

output "create_client_auth_url" {
  description = "La URL de la función HTTP para crear clientes"
  value       = google_cloudfunctions2_function.create_client_auth.url
}
