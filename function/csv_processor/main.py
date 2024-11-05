import csv
import os
from google.cloud import firestore, storage

def detect_delimiter(sample: str) -> str:
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

    # Extract base file name without extension for the document name
    document_name = os.path.splitext(os.path.basename(file_name))[0]

    # Reference to Firestore document
    doc_ref = firestore_client.collection('Rutas').document(document_name)

    # Set the fields "cliente" and "localidad" at the document level
    doc_ref.set({
        'cliente': bucket_name,
        'localidad': 'Localidad Fija'  # Temporarily hardcoded value for "localidad"
    }, merge=True)

    # Process each row in the CSV and save in the sub-collection as the "RutaRecorrido"
    sub_collection_ref = doc_ref.collection('RutaRecorrido')
    for idx, row in enumerate(csv_reader):
        if 'estado_actual' not in row:
            row['estado_actual'] = ''
        # Create a new document in the sub-collection with data from CSV row
        sub_collection_ref.document(str(idx)).set(row)

    return len(content)
