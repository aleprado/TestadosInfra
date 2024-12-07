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
    rutas = rutas_collection.stream()

    for ruta in rutas:
        ruta_id = ruta.id
        ruta_data = ruta.to_dict()

        # Obtener las referencias a cliente y localidad
        cliente_ref = ruta_data.get('cliente')
        localidad_ref = ruta_data.get('localidad')

        if not cliente_ref or not localidad_ref:
            print(f"La ruta {ruta_id} no tiene referencias de cliente o localidad.")
            continue

        # Obtener las subcolecciones dentro de la ruta
        subcollections = ruta.reference.collections()

        for subcollection in subcollections:
            subcollection_name = subcollection.id
            documents = subcollection.stream()

            # Ordenar los documentos por el ID del documento, asumiendo que es numérico
            sorted_docs = sorted(documents, key=lambda d: int(d.id))

            # Calcular el porcentaje de documentos completados
            total_docs = len(sorted_docs)
            completed_docs = sum(1 for doc in sorted_docs if doc.to_dict().get('estado_actual'))
            completion_percentage = (completed_docs / total_docs) * 100 if total_docs > 0 else 0

            # Actualizar el campo 'completado' en la ruta
            ruta.reference.update({'completado': completion_percentage})

            # Crear un archivo CSV con los datos de la subcolección
            file_name = f'{cliente_ref}/{localidad_ref}/{ruta_id}.csv'
            blob = export_bucket.blob(file_name)

            with blob.open("wt", newline='') as csv_file:
                writer = csv.writer(csv_file)
                header_written = False
                for doc in sorted_docs:
                    if not header_written:
                        # Escribir el encabezado en el CSV
                        writer.writerow(doc.to_dict().keys())
                        header_written = True
                    # Escribir los valores del documento en el CSV
                    writer.writerow(doc.to_dict().values())

            print(f'Ruta {ruta_id} exportada a {file_name} con porcentaje completado: {completion_percentage:.2f}%')

    print('Exportación completada.')
