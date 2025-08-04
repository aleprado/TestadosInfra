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

variable "function_bucket_name" {
  description = "El nombre del bucket de Cloud Storage para funciones"
  type        = string
  default     = "testados-functions"
}

variable "export_bucket_name" {
  description = "El nombre del bucket de Cloud Storage para exportaciones"
  type        = string
  default     = "testados-rutas-exportadas"
}

variable "credentials_file" {
  description = "La ruta al archivo de credenciales de GCP"
  type        = string
  default     = ""
}

variable "cuenta_servicio_web" {
  description = "Cuenta de servicio de la app web"
  type        = string
  default     = ""
}
