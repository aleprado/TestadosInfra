import csv
import os
import re
from google.cloud import firestore, storage

CAMPOS = [
    'zona', 'orden', 'servicio', 'estado', 'usuario', 'direccion', 'localidad',
    'medidor', 'digitos', 'frecuencia', 'categoria', 'lectura_anterior',
    'controles', 'novedades', 'lectura_actual', 'consumo_aa',
    'porcentaje_control_aa', 'consumo_promedio_aa',
    'porcentaje_control_promedio_aa', 'observacionlecturista',
    'fecha_hora_lectura', 'esta_cortado', 'latitud', 'longitud', 'altura'
]

def detectar_delimitador(linea: str) -> str:
    if ';' in linea:
        return ';'
    if ',' in linea:
        return ','
    raise ValueError('Unknown delimiter')

def limpiar_valor(valor) -> str:
    if valor is None:
        return ''
    if not isinstance(valor, str):
        valor = str(valor)
    valor = re.sub(r' {2,}', ' ', valor).strip()
    if valor.isdigit():
        valor = valor.lstrip('0')
        if valor == '':
            return ''
    return '' if valor == '0' else valor

def procesar_csv(datos, contexto):
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
        for indice, fila in enumerate(lector):
            fila = {k: limpiar_valor(v) for k, v in fila.items() if k is not None}
            subcoleccion.document(str(indice)).set(fila)

        ref_ruta.set({
            'procesamiento': {
                'estado': 'ok',
                'filas': len(lineas),
                'actualizado': firestore.SERVER_TIMESTAMP,
            }
        }, merge=True)
        print(f"Processed {len(lineas)} lines from {nombre_archivo}.")
        return len(lineas)
    except Exception as exc:
        ref_ruta.set({
            'procesamiento': {
                'estado': 'error',
                'mensaje': str(exc),
                'actualizado': firestore.SERVER_TIMESTAMP,
            }
        }, merge=True)
        raise
