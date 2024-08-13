import os
import csv
from google.cloud import firestore, storage

def export_subcollections(data, context):
    # Inicializar clientes de Firestore y Cloud Storage
    firestore_client = firestore.Client()
    storage_client = storage.Client()

    # Obtener el nombre del cliente desde el contexto
    cliente_id = 'Cliente 1'  # En este ejemplo estamos usando un cliente fijo, puedes adaptarlo a tus necesidades

    # Referencia a la colección del cliente en Firestore
    rutas_ref = firestore_client.collection('Rutas').document(cliente_id)

    # Obtener todas las subcolecciones (las rutas)
    subcollections = rutas_ref.collections()

    # Crear un bucket en Cloud Storage
    bucket_name = os.environ.get('EXPORT_BUCKET_NAME')
    bucket = storage_client.bucket(bucket_name)

    for subcollection in subcollections:
        # Obtener el nombre de la subcolección (que será el nombre del archivo CSV)
        subcollection_name = subcollection.id
        csv_filename = f"{cliente_id}/{subcollection_name}.csv"

        # Crear un archivo temporal
        temp_file_path = f"/tmp/{subcollection_name}.csv"
        with open(temp_file_path, mode='w', newline='') as csv_file:
            csv_writer = csv.writer(csv_file)
            
            # Escribir encabezados en el CSV
            documents = subcollection.stream()
            first_doc = next(documents)
            headers = list(first_doc.to_dict().keys())
            csv_writer.writerow(headers)

            # Escribir las filas en el CSV
            csv_writer.writerow(first_doc.to_dict().values())
            for doc in documents:
                csv_writer.writerow(doc.to_dict().values())

        # Subir el archivo CSV al bucket en Cloud Storage
        blob = bucket.blob(csv_filename)
        blob.upload_from_filename(temp_file_path)

        # Eliminar el archivo temporal
        os.remove(temp_file_path)
