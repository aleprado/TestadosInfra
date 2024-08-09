import csv
import os
from google.cloud import firestore, storage

def detect_delimiter(sample: str) -> str:
    """
    Detect the delimiter used in the sample string.
    """
    if ';' in sample:
        return ';'
    elif ',' in sample:
        return ','
    else:
        raise ValueError('Unknown delimiter')

def process_csv(data, context):
    bucket_name = data['bucket']
    file_name = data['name']

    # Initialize Firestore and Storage clients
    firestore_client = firestore.Client()
    storage_client = storage.Client()

    # Define the path for the file in Cloud Storage
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(file_name)

    # Read the file content
    content = blob.download_as_text().splitlines()

    # Detect the delimiter from the first line of the CSV
    delimiter = detect_delimiter(content[0])

    # Parse the CSV content with the detected delimiter
    csv_reader = csv.DictReader(content, delimiter=delimiter)

    # Extract file name without extension for sub-collection name
    sub_collection_name = os.path.splitext(file_name)[0]

    # Reference to Firestore document
    doc_ref = firestore_client.collection('Rutas').document('Cliente 1').collection(sub_collection_name)

    # Process each row in the CSV
    for idx, row in enumerate(csv_reader):
        # Ensure 'estado_actual' column is present and set to an empty string if not present
        if 'estado_actual' not in row:
            row['estado_actual'] = ''

        # Create a new document with data from CSV row
        doc_ref.document(str(idx)).set(row)

    # Optionally: return the number of documents created
    return len(content)
