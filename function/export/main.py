import csv
import os
from google.cloud import firestore, storage

def export_subcollections(event, context):
    # Inicializar clientes Firestore y Storage
    firestore_client = firestore.Client()
    storage_client = storage.Client()

    # Obtener el nombre del bucket donde se almacenarán los archivos exportados
    export_bucket_name = os.environ['EXPORT_BUCKET_NAME']
    export_bucket = storage_client.bucket(export_bucket_name)

    # Obtener todas las colecciones de "Rutas"
    rutas_collection = firestore_client.collection('Rutas')
    clientes = rutas_collection.stream()

    for cliente in clientes:
        cliente_id = cliente.id
        subcollections = cliente.reference.collections()

        # Crear una carpeta para cada cliente dentro del bucket
        for subcollection in subcollections:
            subcollection_name = subcollection.id
            documents = subcollection.stream()

            # Ordenar los documentos por el ID del documento, asumiendo que es numérico
            sorted_docs = sorted(documents, key=lambda d: int(d.id))

            total_docs = len(sorted_docs)
            completed_docs = sum(1 for doc in sorted_docs if doc.to_dict().get('estado_actual'))
            completion_percentage = (completed_docs / total_docs) * 100 if total_docs > 0 else 0

            # Actualizar el campo 'completada' en el documento del cliente
            cliente.reference.update({'completada': completion_percentage})

            for doc in sorted_docs:
                documento_id = doc.id

                # Crear un archivo CSV con el nombre adecuado según el cliente y el documento
                file_name = f'{cliente_id}/{documento_id}.csv'
                blob = export_bucket.blob(file_name)

                # Crear el archivo CSV en la memoria y escribir los datos del documento
                with blob.open("wt", newline='') as csv_file:
                    writer = csv.writer(csv_file)
                    header_written = False
                    if not header_written:
                        # Escribir el encabezado en el CSV
                        writer.writerow(doc.to_dict().keys())
                        header_written = True
                    # Escribir los valores del documento en el CSV
                    writer.writerow(doc.to_dict().values())

                print(f'Documento {documento_id} exportado a {file_name}')

    print('Exportación completada.')
