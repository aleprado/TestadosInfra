variable "project_id" {
  description = "El ID del proyecto en GCP"
  type        = string
  default     = "estado-eb18c"
}

variable "region" {
  description = "La región donde se desplegarán los recursos"
  type        = string
  default     = "us-central1"
}

variable "data_bucket_name" {
  description = "El nombre del bucket de Cloud Storage para los datos"
  type        = string
  default     = "testados-rutas"
}

variable "export_bucket_name" {
  description = "El nombre del bucket de Cloud Storage para exportar subcolecciones"
  type        = string
  default     = "testados-rutas-exportadas"
}

variable "function_bucket_name" {
  description = "El nombre del bucket de Cloud Storage para las funciones"
  type        = string
  default     = "testados-functions"
}

variable "credentials_file" {
  description = "La ruta al archivo de credenciales de GCP"
  type        = string
  default     = ""
}
