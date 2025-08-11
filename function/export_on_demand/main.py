import os
import csv
import json
from datetime import datetime
from google.cloud import firestore
from google.cloud import storage
from flask import Flask, request, jsonify
import functions_framework

app = Flask(__name__)

def _get_param(request, param_name):
    """Obtener parámetro de query string o JSON body"""
    # Intentar obtener de query string primero
    value = request.args.get(param_name)
    if value:
        return value
    
    # Si no está en query string, intentar del JSON body
    try:
        body = request.get_json()
        if body and param_name in body:
            return body[param_name]
    except:
        pass
    
    return None

@functions_framework.http
def export_on_demand_http(request):
    """Función HTTP para exportar datos de una ruta específica a CSV"""
    
    # Configurar CORS
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST',
            'Access-Control-Allow-Headers': 'Content-Type',
        }
        return ('', 204, headers)
    
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'application/json',
    }
    
    try:
        # Obtener parámetros
        cliente = _get_param(request, "cliente")
        localidad = _get_param(request, "localidad")
        ruta_id = _get_param(request, "rutaId")
        
        # Log de debug
        print(f"DEBUG: Parámetros recibidos - cliente: {cliente}, localidad: {localidad}, ruta_id: {ruta_id}")
        
        if not all([cliente, localidad, ruta_id]):
            return jsonify({
                'error': 'Faltan parámetros requeridos: cliente, localidad, rutaId'
            }), 400, headers
        
        # Inicializar Firestore
        db = firestore.Client()
        
        # Referencia a la ruta
        ruta_ref = db.collection("Clientes").document(cliente).collection("Localidades").document(localidad).collection("Rutas").document(ruta_id)
        ruta_doc = ruta_ref.get()
        
        if not ruta_doc.exists:
            return jsonify({
                'error': f'Ruta {ruta_id} no encontrada'
            }), 404, headers
        
        # Obtener datos de la ruta
        ruta_data = ruta_doc.to_dict()
        
        # Obtener usuarios asignados
        usuarios_ref = ruta_ref.collection("UsuariosAsignados")
        usuarios_snapshot = usuarios_ref.get()
        usuarios_asignados = [doc.id for doc in usuarios_snapshot]
        
        # Calcular porcentaje de completado
        ref_lecturas = ruta_ref.collection("RutaRecorrido")
        lecturas_snapshot = ref_lecturas.get()
        total_lecturas = len(lecturas_snapshot)
        
        if total_lecturas > 0:
            lecturas_con_medicion = sum(1 for doc in lecturas_snapshot if doc.to_dict().get("lectura_actual"))
            porcentaje_completado = (lecturas_con_medicion / total_lecturas) * 100
        else:
            porcentaje_completado = 0
        
        # Preparar datos para CSV
        csv_data = []
        
        # Agregar información de la ruta
        ruta_row = {
            "Ruta ID": ruta_id,
            "Cliente": cliente,
            "Localidad": localidad,
            "Estado": ruta_data.get("estado", "N/A"),
            "Porcentaje Completado": f"{porcentaje_completado:.1f}%",
            "Total Lecturas": total_lecturas,
            "Lecturas con Medición": lecturas_con_medicion if total_lecturas > 0 else 0,
            "Usuarios Asignados": ", ".join(usuarios_asignados) if usuarios_asignados else "Ninguno"
        }
        csv_data.append(ruta_row)
        
        # Agregar datos de lecturas
        for doc in lecturas_snapshot:
            lectura_data = doc.to_dict()
            # Filtrar solo campos relevantes, excluyendo metadatos de Firestore
            filtered_row = {}
            for key, value in lectura_data.items():
                if not key.startswith('_') and not callable(value):
                    filtered_row[key] = value
            
            if filtered_row:
                csv_data.append(filtered_row)
        
        if not csv_data:
            return jsonify({
                'error': 'No hay datos para exportar'
            }), 404, headers
        
        # Escribir CSV
        csv_filename = f"/tmp/{ruta_id}_export.csv"
        
        # Determinar headers basándose en la primera fila para mantener orden consistente
        if csv_data:
            headers = list(csv_data[0].keys())
            
            with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=headers)
                writer.writeheader()
                
                for row in csv_data:
                    # Asegurar que cada fila tenga todos los headers en el mismo orden
                    ordered_row = {header: row.get(header, '') for header in headers}
                    writer.writerow(ordered_row)
        
        # Subir a GCS
        storage_client = storage.Client()
        export_bucket_name = os.environ.get("EXPORT_BUCKET_NAME", "testados-rutas-exportadas")
        
        # Usar timestamp legible para generar nombre único
        timestamp = _get_param(request, "t")
        if timestamp:
            # Convertir timestamp de milisegundos a formato legible
            try:
                timestamp_ms = int(timestamp)
                timestamp_date = datetime.fromtimestamp(timestamp_ms / 1000)
                timestamp_readable = timestamp_date.strftime("%Y-%m-%d_%H-%M-%S")
            except:
                # Si falla la conversión, usar timestamp actual
                timestamp_readable = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        else:
            # Si no hay timestamp, usar el actual
            timestamp_readable = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        object_name = f"{cliente}/{localidad}/{ruta_id}_{timestamp_readable}.csv"
        
        bucket = storage_client.bucket(export_bucket_name)
        blob = bucket.blob(object_name)
        
        blob.upload_from_filename(csv_filename)
        
        # Hacer público el archivo
        blob.make_public()
        
        # Actualizar Firestore con información de completado
        ruta_ref.update({
            "ultima_exportacion": firestore.SERVER_TIMESTAMP,
            "porcentaje_completado": porcentaje_completado,
            "archivo_csv_url": blob.public_url
        })
        
        # Limpiar archivo temporal
        os.remove(csv_filename)
        
        return jsonify({
            'success': True,
            'url': blob.public_url,
            'filename': object_name,
            'timestamp': timestamp_readable,
            'porcentaje_completado': porcentaje_completado
        }), 200, headers
        
    except Exception as e:
        return jsonify({
            'error': f'Error interno: {str(e)}'
        }), 500, headers


