#!/bin/bash
set -e

# Delete GCP resources if they exist, ignoring errors when they do not.

PROJECT_ID=${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}
REGION=${REGION:-${1:-us-central1}}

DATA_BUCKET_NAME=${DATA_BUCKET_NAME:-testados-rutas}
FUNCTION_BUCKET_NAME=${FUNCTION_BUCKET_NAME:-testados-functions}
EXPORT_BUCKET_NAME=${EXPORT_BUCKET_NAME:-testados-rutas-exportadas}

# Ensure Terraform commands receive the credentials file path
TF_VAR_credentials_file="${GOOGLE_APPLICATION_CREDENTIALS}"
export TF_VAR_credentials_file

# Delete Cloud Scheduler job if it exists
if gcloud scheduler jobs describe export-csv-scheduler --location "$REGION" >/dev/null 2>&1; then
  gcloud scheduler jobs delete export-csv-scheduler --location "$REGION" --quiet || true
fi

# Delete Pub/Sub topic if it exists
if gcloud pubsub topics describe export-csv-topic >/dev/null 2>&1; then
  gcloud pubsub topics delete export-csv-topic --quiet || true
fi

# Delete Cloud Functions if they exist
if gcloud functions describe csvProcessor --region "$REGION" --gen2 >/dev/null 2>&1; then
  gcloud functions delete csvProcessor --region "$REGION" --gen2 --quiet || true
fi
if gcloud functions describe exportCSV --region "$REGION" --gen2 >/dev/null 2>&1; then
  gcloud functions delete exportCSV --region "$REGION" --gen2 --quiet || true
fi

# Buckets are preserved between runs. They will be created if missing in
# import_existing_resources.sh and should not be deleted here.
