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

variable "function_bucket_name" {
  description = "El nombre del bucket para almacenar el archivo ZIP de la función"
  type        = string
  default     = "testados-functions"
}

variable "data_bucket_name" {
  description = "El nombre del bucket para almacenar los archivos que la función procesará"
  type        = string
  default     = "testados-rutas"
}

variable "credentials_file" {
  description = "La ruta al archivo de credenciales de GCP"
  type        = string
  default     = ""
}
