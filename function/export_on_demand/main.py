import os
import csv
from datetime import datetime, timedelta
from google.cloud import firestore
from google.cloud import storage
from flask import Flask, request, jsonify
import functions_framework
import firebase_admin
from firebase_admin import credentials, auth

firebase_admin.initialize_app()
app = Flask(__name__)
EXPORT_FIELD_ORDER = [
    'orden',
    'servicio',
    'estado',
    'usuario',
    'direccion',
    'titular',
    'medidor',
    'digitos',
    'frecuencia',
    'categoria',
    'lectura_anterior',
    'consumo_aa',
    'porcentaje_control_aa',
    'consumo_promedio_aa',
    'porcentaje_control_promedio_aa',
    'observacionlecturista',
    'lectura_actual',
    'fecha_hora_lectura',
    'fecha_hora_edicion',
    'novedades',
    'latitud',
    'longitud',
]
FIELD_ALIASES = {
    'fechaToma': 'fecha_hora_lectura',
    'novedad': 'novedades',
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

def _normalize_export_data(data):
    normalized = {}
    for key, value in data.items():
        canonical = FIELD_ALIASES.get(key, key)
        normalized[canonical] = value
    return normalized

def _row_for_export(data):
    return [data.get(field, '') for field in EXPORT_FIELD_ORDER]

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
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)

    cors_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization'
    }

    # 🔒 VALIDAR TOKEN DE FIREBASE AUTH
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'No autorizado. Se requiere token Bearer.'}), 401, cors_headers
        
    id_token = auth_header.split('Bearer ')[1]
    try:
        decoded_token = auth.verify_id_token(id_token)
        caller_email = decoded_token.get('email', '')
        print(f"DEBUG: Usuario autenticado: {caller_email}")
    except Exception as e:
        print(f"ERROR: Token inválido: {e}")
        return jsonify({'error': 'Token inválido o expirado.'}), 401, cors_headers

    try:
        # 🔍 DEBUG: Log de todos los parámetros recibidos
        print(f"DEBUG: Método HTTP: {request.method}")
        print(f"DEBUG: URL completa: {request.url}")
        print(f"DEBUG: Query params: {dict(request.args)}")
        
        if request.method == 'POST':
            try:
                body = request.get_json()
            except Exception as e:
                body = None
        
        # Obtener parámetros
        cliente = _get_param(request, 'cliente')
        localidad = _get_param(request, 'localidad')
        ruta_id = _get_param(request, 'ruta_id')
        include_zero = _parse_bool(_get_param(request, 'include_zero'), default=False)
        
        # (El usuario debe tener permisos sobre este cliente, aquí se asume que si tiene token puede acceder, o idealmente validar claims de admin. Omitimos control granular por ahora, pero validamos que esté logueado)
        
        missing_params = []
        if not cliente:
            missing_params.append("cliente")
        if not localidad:
            missing_params.append("localidad")
        if not ruta_id:
            missing_params.append("ruta_id")
            
        if missing_params:
            error_msg = f'Faltan parámetros requeridos: {", ".join(missing_params)}'
            return jsonify({'error': error_msg}), 400, cors_headers

        print(f"DEBUG: Exportando ruta {ruta_id} para cliente {cliente} en localidad {localidad}")

        firestore_client = firestore.Client()
        storage_client = storage.Client()

        nombre_bucket_exportacion = os.environ.get('EXPORT_BUCKET_NAME', 'testados-rutas-exportadas')
        export_bucket = storage_client.bucket(nombre_bucket_exportacion)

        ruta_ref = firestore_client.collection('Rutas').document(ruta_id)
        ruta_doc = ruta_ref.get()

        if not ruta_doc.exists:
            return jsonify({'error': f'Ruta {ruta_id} no encontrada'}), 404, cors_headers

        subcollections = ruta_ref.collections()
        subcollections_list = list(subcollections)
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_name = f'{cliente}/{localidad}/{ruta_id}_{timestamp}.csv'
        blob = export_bucket.blob(file_name)

        total_docs = 0
        completed_docs = 0
        has_reading = _reading_predicate(include_zero)

        with blob.open("wt", newline='') as csv_file:
            writer = csv.writer(csv_file, delimiter=';')
            writer.writerow(EXPORT_FIELD_ORDER)

            for subcollection in subcollections_list:
                documents = subcollection.stream()
                doc_list = list(documents)
                if len(doc_list) == 0:
                    continue

                sorted_docs = sorted(doc_list, key=lambda d: int(d.id))
                for doc in sorted_docs:
                    doc_data = doc.to_dict()
                    total_docs += 1
                    normalized_data = _normalize_export_data(doc_data)
                    if not has_reading(normalized_data.get('lectura_actual')):
                        continue
                    completed_docs += 1
                    row = _row_for_export(normalized_data)
                    writer.writerow(row)

        # Generar URL firmada en lugar de hacerlo público
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=15),
            method="GET"
        )

        completion_percentage = (completed_docs / total_docs) * 100 if total_docs > 0 else 0
        ruta_ref.update({'completado': completion_percentage})

        return jsonify({
            'success': True,
            'filename': file_name,
            'total_documentos': total_docs,
            'documentos_completados': completed_docs,
            'porcentaje_completado': completion_percentage,
            'timestamp': timestamp,
            'url': signed_url
        }), 200, cors_headers

    except Exception as e:
        print(f"ERROR: {str(e)}")
        return jsonify({
            'error': f'Error interno: {str(e)}'
        }), 500, cors_headers

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
