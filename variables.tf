variable "project_id" {
  description = "El ID del proyecto en GCP"
  type        = string
}

variable "region" {
  description = "La región donde se desplegarán los recursos"
  type        = string
  default     = "us-central1"
}

variable "credentials_file" {
  description = "La ruta al archivo de credenciales de GCP"
  type        = string
}

variable "bucket_name" {
  description = "El nombre del bucket de Cloud Storage"
  type        = string
}
