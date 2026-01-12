import csv
import os
from google.cloud import firestore, storage

def export_subcollections(event, context):
    # Inicializar clientes Firestore y Storage
    firestore_client = firestore.Client()
    storage_client = storage.Client()

    # Obtener el nombre del bucket donde se almacenarán los archivos exportados
    nombre_bucket_exportacion = os.environ.get('EXPORT_BUCKET_NAME', 'testados-rutas-exportadas')
    os.environ['EXPORT_BUCKET_NAME'] = nombre_bucket_exportacion
    export_bucket = storage_client.bucket(nombre_bucket_exportacion)

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

        # Obtener IDs legibles para cliente y localidad
        cliente_id = cliente_ref.id if isinstance(cliente_ref, firestore.DocumentReference) else str(cliente_ref)
        localidad_id = localidad_ref.id if isinstance(localidad_ref, firestore.DocumentReference) else str(localidad_ref)

        # Obtener las subcolecciones dentro de la ruta
        subcollections = ruta.reference.collections()

        # Crear un archivo CSV único para la ruta
        file_name = f'testados-rutas-exportadas/{cliente_id}/{localidad_id}/{ruta_id}.csv'
        blob = export_bucket.blob(file_name)
        
        # Configurar el blob para acceso público
        blob.make_public()

        with blob.open("wt", newline='') as csv_file:
            writer = csv.writer(csv_file, delimiter=';')
            header_written = False

            for subcollection in subcollections:
                documents = subcollection.stream()

                # Ordenar los documentos por el ID del documento, asumiendo que es numérico
                sorted_docs = sorted(documents, key=lambda d: int(d.id))

                # Calcular el porcentaje de documentos completados
                total_docs = len(sorted_docs)
                completed_docs = sum(1 for doc in sorted_docs if doc.to_dict().get('lectura_actual'))
                completion_percentage = (completed_docs / total_docs) * 100 if total_docs > 0 else 0

                # Actualizar el campo 'completado' en la ruta
                ruta.reference.update({'completado': completion_percentage})

                for doc in sorted_docs:
                    doc_data = doc.to_dict()
                    if not doc_data.get('lectura_actual'):
                        continue

                    doc_data.pop('altura', None)
                    if not header_written:
                        # Escribir el encabezado en el CSV
                        writer.writerow(doc_data.keys())
                        header_written = True
                    # Escribir los valores del documento en el CSV
                    writer.writerow(doc_data.values())

            print(f'Ruta {ruta_id} exportada a {file_name} con porcentaje tomado: {completion_percentage:.2f}%')

    print('Exportación completa.')
