import os
import csv
from datetime import datetime
from google.cloud import firestore
from google.cloud import storage
from flask import Flask, request, jsonify
import functions_framework

app = Flask(__name__)
SERVICE_FIELD = 'servicio'
DROP_FIELDS = {
    'latitud',
    'longitud',
    'altura',
    'imagenUrl',
    'consumo_aa',
    'consumo_promedio_aa',
    'controlado',
    'esta_cortado',
    'observacionlecturista',
    'porcentaje_control_aa',
    'porcentaje_control_promedio_aa',
}

def _parse_bool(value, default=False):
    """Parsea booleanos desde query/body."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {'true', '1', 'yes', 'y', 'si'}:
            return True
        if normalized in {'false', '0', 'no', 'n'}:
            return False
    return default

def _reading_present_default(value):
    """Replica la lógica histórica: cualquier falsy se considera sin lectura."""
    return bool(value)

def _reading_present_include_zero(value):
    """Permite lectura 0 sin cambiar el criterio para strings vacíos o None."""
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (int, float)):
        return True
    return bool(value)

def _reading_predicate(include_zero):
    return _reading_present_include_zero if include_zero else _reading_present_default

def _build_headers(data, extra_fields, service_field=SERVICE_FIELD):
    headers = sorted(data.keys())
    if service_field in headers:
        headers.remove(service_field)
    for campo in extra_fields:
        if campo not in headers and campo != service_field:
            headers.append(campo)
    if service_field not in headers:
        headers.append(service_field)
    return headers

def _row_from_headers(data, headers):
    return [data.get(header, '') for header in headers]

def _filter_export_fields(data):
    return {key: value for key, value in data.items() if key not in DROP_FIELDS}

def _get_param(request, param_name):
    """Obtiene un parámetro del request, ya sea de query params o del body JSON"""
    # ✅ SOLUCIÓN: Buscar primero en el body JSON, luego en query params como fallback
    if request.method == 'POST':
        try:
            body = request.get_json()
            if body and param_name in body:
                return body.get(param_name)
        except:
            pass
    
    # Si no se encontró en el body JSON, buscar en query params
    return request.args.get(param_name)

@functions_framework.http
def export_csv_on_demand(request):
    """Función simplificada basada en la función original de exportación"""
    
    # Log de versión para verificar que estamos usando la última
    print(f"DEBUG: [VERSION 2025-08-11 12:45] Función export_csv_on_demand iniciada")
    print(f"DEBUG: [VERSION 2025-08-11 12:45] Timestamp de inicio: {datetime.now().isoformat()}")

    # Configurar CORS
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)

    cors_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST',
        'Access-Control-Allow-Headers': 'Content-Type'
    }

    try:
        # 🔍 DEBUG: Log de todos los parámetros recibidos
        print(f"DEBUG: Método HTTP: {request.method}")
        print(f"DEBUG: URL completa: {request.url}")
        print(f"DEBUG: Query params: {dict(request.args)}")
        print(f"DEBUG: Headers: {dict(request.headers)}")
        
        if request.method == 'POST':
            try:
                body = request.get_json()
                print(f"DEBUG: Body JSON: {body}")
            except Exception as e:
                print(f"DEBUG: Error parseando body JSON: {e}")
                body = None
        
        # Obtener parámetros con logs detallados
        cliente = _get_param(request, 'cliente')
        localidad = _get_param(request, 'localidad')
        ruta_id = _get_param(request, 'ruta_id')
        include_zero = _parse_bool(_get_param(request, 'include_zero'), default=False)
        
        print(f"DEBUG: Parámetros extraídos:")
        print(f"DEBUG: - cliente: '{cliente}' (tipo: {type(cliente)})")
        print(f"DEBUG: - localidad: '{localidad}' (tipo: {type(localidad)})")
        print(f"DEBUG: - ruta_id: '{ruta_id}' (tipo: {type(ruta_id)})")
        print(f"DEBUG: - include_zero: '{include_zero}' (tipo: {type(include_zero)})")

        # ✅ MEJORA: Validación más detallada de parámetros
        missing_params = []
        if not cliente:
            missing_params.append("cliente")
        if not localidad:
            missing_params.append("localidad")
        if not ruta_id:
            missing_params.append("ruta_id")
            
        if missing_params:
            error_msg = f'Faltan parámetros requeridos: {", ".join(missing_params)}. Recibidos: cliente="{cliente}", localidad="{localidad}", ruta_id="{ruta_id}"'
            print(f"ERROR: {error_msg}")
            return jsonify({
                'error': error_msg,
                'missing_params': missing_params,
                'received_params': {
                    'cliente': cliente,
                    'localidad': localidad,
                    'ruta_id': ruta_id
                }
            }), 400, cors_headers

        # La validación ya se hizo arriba, continuar con el procesamiento

        print(f"DEBUG: Exportando ruta {ruta_id} para cliente {cliente} en localidad {localidad}")
        print(f"DEBUG: include_zero={include_zero}")

        # Inicializar clientes
        firestore_client = firestore.Client()
        storage_client = storage.Client()

        # Obtener bucket de exportación
        nombre_bucket_exportacion = os.environ.get('EXPORT_BUCKET_NAME', 'testados-rutas-exportadas')
        export_bucket = storage_client.bucket(nombre_bucket_exportacion)

        # Buscar la ruta específica
        ruta_ref = firestore_client.collection('Rutas').document(ruta_id)
        ruta_doc = ruta_ref.get()

        if not ruta_doc.exists:
            return jsonify({
                'error': f'Ruta {ruta_id} no encontrada'
            }), 404, cors_headers

        ruta_data = ruta_doc.to_dict()
        print(f"DEBUG: Ruta encontrada, datos: {list(ruta_data.keys())}")

        # Obtener las subcolecciones de la ruta
        subcollections = ruta_ref.collections()
        subcollections_list = list(subcollections)  # Convertir a lista una sola vez
        print(f"DEBUG: Subcolecciones encontradas: {[sc.id for sc in subcollections_list]}")
        
        print(f"DEBUG: Iniciando procesamiento de {len(subcollections_list)} subcolecciones")

        # Crear archivo CSV
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_name = f'{cliente}/{localidad}/{ruta_id}_{timestamp}.csv'
        blob = export_bucket.blob(file_name)

        total_docs = 0
        completed_docs = 0
        headers_definitive = []  # Lista ordenada para mantener el orden de headers
        campos_extra = ['titular', 'fecha_hora_edicion']
        has_reading = _reading_predicate(include_zero)

        with blob.open("wt", newline='') as csv_file:
            writer = csv.writer(csv_file, delimiter=';')
            header_written = False

            for subcollection in subcollections_list:
                print(f"DEBUG: Procesando subcolección: {subcollection.id}")
                documents = subcollection.stream()
                doc_list = list(documents)
                print(f"DEBUG: Documentos en {subcollection.id}: {len(doc_list)}")
                
                if len(doc_list) == 0:
                    print(f"DEBUG: Subcolección {subcollection.id} está vacía")
                    continue

                print(f"DEBUG: Encontrados {len(doc_list)} documentos en {subcollection.id}")
                print(f"DEBUG: IDs de documentos: {[doc.id for doc in doc_list[:5]]}")  # Mostrar primeros 5 IDs

                # Ordenar documentos por ID numérico
                sorted_docs = sorted(doc_list, key=lambda d: int(d.id))
                print(f"DEBUG: Procesando {len(sorted_docs)} documentos en {subcollection.id}")

                for doc in sorted_docs:
                    doc_data = doc.to_dict()
                    total_docs += 1
                    if not has_reading(doc_data.get('lectura_actual')):
                        continue
                    completed_docs += 1
                    print(f"DEBUG: Escribiendo documento {doc.id} con {len(doc_data)} campos")
                    
                    # Mapear campos para normalizar nombres
                    normalized_data = {}
                    for key, value in doc_data.items():
                        if key == 'controles':
                            normalized_data['controlado'] = value
                        elif key == 'fecha_hora_lectura':
                            normalized_data['fechaToma'] = value
                        elif key == 'novedades':
                            normalized_data['novedad'] = value
                        else:
                            normalized_data[key] = value

                    normalized_data = _filter_export_fields(normalized_data)
                    normalized_data.pop('altura', None)
                    if not normalized_data:
                        continue

                    if not header_written:
                        # Escribir el encabezado en el CSV y guardar el orden
                        headers_definitive = _build_headers(normalized_data, campos_extra)
                        writer.writerow(headers_definitive)
                        header_written = True
                        print(f"DEBUG: Headers definitivos escritos: {headers_definitive}")
                    
                    # ✅ SOLUCIÓN: Crear fila usando el mismo orden que los headers escritos
                    row = _row_from_headers(normalized_data, headers_definitive)
                    writer.writerow(row)
                    print(f"DEBUG: Documento {doc.id} escrito con {len(row)} campos")

        # ✅ CORRECCIÓN: Hacer público el blob DESPUÉS de escribir el contenido
        print(f"DEBUG: Haciendo público el archivo: {file_name}")
        blob.make_public()
        print(f"DEBUG: Archivo configurado como público exitosamente")

        # Calcular porcentaje de completado
        completion_percentage = (completed_docs / total_docs) * 100 if total_docs > 0 else 0

        # Actualizar el campo 'completado' en la ruta
        ruta_ref.update({'completado': completion_percentage})

        print(f"DEBUG: Total de filas en CSV: {total_docs}")
        print(f"DEBUG: Total de lecturas: {completed_docs}")

        return jsonify({
            'success': True,
            'filename': file_name,
            'total_documentos': total_docs,
            'documentos_completados': completed_docs,
            'porcentaje_completado': completion_percentage,
            'timestamp': timestamp,
            'url': f"https://storage.googleapis.com/{nombre_bucket_exportacion}/{file_name}"
        }), 200, cors_headers

    except Exception as e:
        print(f"ERROR: {str(e)}")
        return jsonify({
            'error': f'Error interno: {str(e)}'
        }), 500, cors_headers

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
