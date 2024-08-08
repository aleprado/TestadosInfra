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

variable "bucket_name" {
  description = "El nombre del bucket de Cloud Storage"
  type        = string
  default     = "estado-eb18c.appspot.com"
}

variable "credentials_file" {
  description = "La ruta al archivo de credenciales de GCP"
  type        = string
  default     = ""
}
