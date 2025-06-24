#!/bin/bash
set -e
# Import existing GCP resources into Terraform state if they already exist.

PROJECT_ID=${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}
REGION=${REGION:-${1:-us-central1}}

# Default names in case environment variables are not provided
DATA_BUCKET_NAME=${DATA_BUCKET_NAME:-testados-rutas}
FUNCTION_BUCKET_NAME=${FUNCTION_BUCKET_NAME:-testados-functions}
EXPORT_BUCKET_NAME=${EXPORT_BUCKET_NAME:-testados-rutas-exportadas}

# Ensure Terraform commands receive the credentials file path
TF_VAR_credentials_file="${GOOGLE_APPLICATION_CREDENTIALS}"
export TF_VAR_credentials_file

# Import storage buckets if they exist
if gsutil ls -b gs://$DATA_BUCKET_NAME >/dev/null 2>&1; then
  terraform import -allow-missing-config google_storage_bucket.data_bucket $DATA_BUCKET_NAME || true
fi
if gsutil ls -b gs://$FUNCTION_BUCKET_NAME >/dev/null 2>&1; then
  terraform import -allow-missing-config google_storage_bucket.function_bucket $FUNCTION_BUCKET_NAME || true
fi
if gsutil ls -b gs://$EXPORT_BUCKET_NAME >/dev/null 2>&1; then
  terraform import -allow-missing-config google_storage_bucket.export_bucket $EXPORT_BUCKET_NAME || true
fi

# Import Cloud Functions if they exist
if gcloud functions describe csvProcessor --region "$REGION" >/dev/null 2>&1; then
  terraform import -allow-missing-config google_cloudfunctions_function.csv_processor $REGION/csvProcessor || true
fi
if gcloud functions describe exportCSV --region "$REGION" >/dev/null 2>&1; then
  terraform import -allow-missing-config google_cloudfunctions_function.export_csv $REGION/exportCSV || true
fi

# Import Pub/Sub topic if it exists
if gcloud pubsub topics describe export-csv-topic >/dev/null 2>&1; then
  terraform import -allow-missing-config google_pubsub_topic.export_topic projects/$PROJECT_ID/topics/export-csv-topic || true
fi

# Import Cloud Scheduler job if it exists
if gcloud scheduler jobs describe export-csv-scheduler --location "$REGION" >/dev/null 2>&1; then
  terraform import -allow-missing-config google_cloud_scheduler_job.export_csv_scheduler projects/$PROJECT_ID/locations/$REGION/jobs/export-csv-scheduler || true
fi
