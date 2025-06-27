import csv
import os
from google.cloud import firestore, storage

CAMPOS = [
    'zona', 'orden', 'servicio', 'estado', 'cliente', 'direccion', 'localidad',
    'medidor', 'digitos', 'frecuencia', 'categoria', 'lectura_anterior',
    'controles', 'novedades', 'lectura_actual', 'consumo_aa',
    'porcentaje_control_aa', 'consumo_promedido_aa',
    'porcentaje_control_promedio_aa', 'observacionlecturista',
    'fecha_hora_lectura', 'esta_cortado', 'latitud', 'longitud', 'altura'
]

def detectar_delimitador(linea: str) -> str:
    if ';' in linea:
        return ';'
    if ',' in linea:
        return ','
    raise ValueError('Unknown delimiter')

def procesar_csv(datos, contexto):
    nombre_bucket = datos['bucket']
    nombre_archivo = datos['name']

    cliente_firestore = firestore.Client()
    cliente_storage = storage.Client()

    bucket = cliente_storage.bucket(nombre_bucket)
    blob = bucket.blob(nombre_archivo)

    lineas = blob.download_as_text().splitlines()
    delimitador = detectar_delimitador(lineas[0])
    primera = next(csv.reader([lineas[0]], delimiter=delimitador))
    if primera == CAMPOS:
        lineas = lineas[1:]
    lector = csv.DictReader(lineas, delimiter=delimitador, fieldnames=CAMPOS)

    nombre_documento = os.path.splitext(os.path.basename(nombre_archivo))[0]

    partes = nombre_archivo.split('/')
    if len(partes) >= 3:
        cliente_nombre = partes[0]
        localidad_nombre = partes[1]
    else:
        raise ValueError('estructura de ruta invalida')

    ref_cliente = cliente_firestore.collection('Clientes').document(cliente_nombre)
    ref_localidad = ref_cliente.collection('Localidades').document(localidad_nombre)
    ref_ruta = cliente_firestore.collection('Rutas').document(nombre_documento)

    ref_ruta.set({'cliente': ref_cliente, 'localidad': ref_localidad}, merge=True)
    ref_localidad.set({'rutas': firestore.ArrayUnion([ref_ruta])}, merge=True)

    subcoleccion = ref_ruta.collection('RutaRecorrido')
    for indice, fila in enumerate(lector):
        subcoleccion.document(str(indice)).set(fila)

    print(f"Processed {len(lineas)} lines from {nombre_archivo}.")
    return len(lineas)
