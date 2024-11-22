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

    # Extract the client name from the folder structure in the bucket path
    folder_parts = file_name.split('/')
    if len(folder_parts) > 1:
        client_name = folder_parts[-2]  # Assume the client name is the last folder before the file name
    else:
        raise ValueError('Invalid file path structure. Expected at least one folder before the file name.')

    # Determine the locality name (you can adjust this if you have another source for this information)
    if len(folder_parts) > 2:
        locality_name = folder_parts[-3]  # Assume locality is part of the folder structure
    else:
        raise ValueError('Invalid file path structure. Expected a locality folder before the client folder.')

    # Firestore references
    client_ref = firestore_client.collection('Clientes').document(client_name)
    locality_ref = client_ref.collection('Localidades').document(locality_name)
    ruta_ref = firestore_client.collection('Rutas').document(document_name)

    # Save metadata in the route document
    ruta_ref.set({
        'cliente': client_ref,
        'localidad': locality_ref
    }, merge=True)

    # Add a reference to the route in the client's locality sub-collection
    locality_ref.set({
        'rutas': firestore.ArrayUnion([ruta_ref])
    }, merge=True)

    # Process each row in the CSV and save it in the sub-collection "RutaRecorrido"
    sub_collection_ref = ruta_ref.collection('RutaRecorrido')
    for idx, row in enumerate(csv_reader):
        if 'estado_actual' not in row:
            row['estado_actual'] = ''  # Default value if not provided
        sub_collection_ref.document(str(idx)).set(row)

    print(f"Processed {len(content)} lines from {file_name}.")
    return len(content)
