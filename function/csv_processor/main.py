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

    # Extract base file name without extension for sub-collection name
    sub_collection_name = os.path.splitext(os.path.basename(file_name))[0]

    # Extract client name from file path
    parts = file_name.split('/')
    if len(parts) >= 2:
        client_name = parts[0]
    else:
        client_name = 'Cliente 1'  # Default client name or handle accordingly

    # Reference to Firestore sub-collection
    doc_ref = firestore_client.collection('Rutas').document(client_name).collection(sub_collection_name)

    # Process each row in the CSV
    for idx, row in enumerate(csv_reader):
        if 'estado_actual' not in row:
            row['estado_actual'] = ''
        # Create a new document with data from CSV row
        doc_ref.document(str(idx)).set(row)

    # Update the 'nombres' array in the client's document
    client_doc_ref = firestore_client.collection('Rutas').document(client_name)
    client_doc_ref.set({
        'nombres': firestore.ArrayUnion([sub_collection_name])
    }, merge=True)

    return len(content)
