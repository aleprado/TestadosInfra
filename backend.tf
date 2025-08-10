terraform {
  backend "gcs" {
    bucket = "testados-terraform-state"
    prefix = "terraform/state"
  }
}
