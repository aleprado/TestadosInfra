import csv
import os
import re
from google.cloud import firestore, storage

VERSION = "2026-01-22-01"

CAMPOS = [
    'orden', 'servicio', 'estado', 'usuario', 'direccion', 'titular', 'medidor', 'digitos', 'frecuencia', 'categoria', 'lectura_anterior', 'consumo_aa', 'porcentaje_control_aa', 'consumo_promedio_aa', 'porcentaje_control_promedio_aa', 'observacionlecturista'
]

def normalizar_nombre_campo(valor: str) -> str:
    if valor is None:
        return ''
    texto = str(valor).strip().strip('"').strip("'")
    return re.sub(r'\s+', '', texto).lower()

def es_fila_encabezado(fila) -> bool:
    normalizada = [normalizar_nombre_campo(celda) for celda in fila]
    return normalizada == CAMPOS

def detectar_delimitador(linea: str) -> str:
    if ';' in linea:
        return ';'
    if ',' in linea:
        return ','
    raise ValueError('Unknown delimiter')

def limpiar_valor(valor) -> str:
    if valor is None:
        return ''
    if isinstance(valor, bytes):
        valor = valor.decode('utf-8', errors='ignore')
    elif not isinstance(valor, str):
        valor = str(valor)
    if not isinstance(valor, (str, bytes)):
        return ''
    try:
        valor = re.sub(r' {2,}', ' ', valor).strip()
    except TypeError:
        valor = re.sub(r' {2,}', ' ', str(valor)).strip()
    if valor.isdigit():
        valor = valor.lstrip('0')
        if valor == '':
            return ''
    return '' if valor == '0' else valor

def procesar_csv(datos, contexto):
    print(f"csv_processor version: {VERSION}")
    nombre_bucket = datos['bucket']
    nombre_archivo = datos['name']

    cliente_firestore = firestore.Client()
    cliente_storage = storage.Client()

    bucket = cliente_storage.bucket(nombre_bucket)
    blob = bucket.blob(nombre_archivo)

    # Descargar como bytes primero para poder probar diferentes codificaciones
    contenido_bytes = blob.download_as_bytes()
    
    # Lista de codificaciones comunes para archivos españoles
    codificaciones = ['utf-8', 'iso-8859-1', 'windows-1252', 'latin1']
    lineas = None
    
    # Intentar decodificar con diferentes codificaciones
    for codificacion in codificaciones:
        try:
            contenido_texto = contenido_bytes.decode(codificacion)
            lineas = contenido_texto.splitlines()
            print(f"DEBUG: Archivo decodificado exitosamente con {codificacion}")
            break
        except UnicodeDecodeError as e:
            print(f"DEBUG: Falló decodificación con {codificacion}: {e}")
            continue
    
    # Si ninguna codificación funciona, usar 'ignore' como último recurso
    if lineas is None:
        print(f"WARNING: No se pudo decodificar con ninguna codificación, usando 'ignore'")
        contenido_texto = contenido_bytes.decode('utf-8', errors='ignore')
        lineas = contenido_texto.splitlines()

    if not lineas:
        raise ValueError('archivo vacío')

    delimitador = detectar_delimitador(lineas[0])
    primera = next(csv.reader([lineas[0]], delimiter=delimitador))
    if es_fila_encabezado(primera):
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

    ref_ruta.set({
        'cliente': ref_cliente,
        'localidad': ref_localidad,
        'procesamiento': {
            'estado': 'procesando',
            'actualizado': firestore.SERVER_TIMESTAMP,
        },
    }, merge=True)
    ref_localidad.set({'rutas': firestore.ArrayUnion([ref_ruta])}, merge=True)

    try:
        subcoleccion = ref_ruta.collection('RutaRecorrido')
        batch = cliente_firestore.batch()
        batch_count = 0
        total_filas_procesadas = 0
        for indice, fila in enumerate(lector):
            fila = {k: limpiar_valor(v) for k, v in fila.items() if k is not None}
            doc_ref = subcoleccion.document(str(indice))
            batch.set(doc_ref, fila)
            batch_count += 1
            total_filas_procesadas += 1
            if batch_count >= 400:
                batch.commit()
                batch = cliente_firestore.batch()
                batch_count = 0
        if batch_count:
            batch.commit()

        ref_ruta.set({
            'procesamiento': {
                'estado': 'ok',
                'filas': total_filas_procesadas,
                'actualizado': firestore.SERVER_TIMESTAMP,
            }
        }, merge=True)
        print(f"Processed {total_filas_procesadas} lines from {nombre_archivo}.")
        return total_filas_procesadas
    except Exception as exc:
        ref_ruta.set({
            'procesamiento': {
                'estado': 'error',
                'mensaje': str(exc),
                'actualizado': firestore.SERVER_TIMESTAMP,
            }
        }, merge=True)
        raise
