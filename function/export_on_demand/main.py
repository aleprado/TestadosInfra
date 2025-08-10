import os
import csv
from flask import Request, make_response
from google.cloud import firestore, storage


def _json_response(payload, status=200):
    from json import dumps
    resp = make_response(dumps(payload), status)
    resp.headers["Content-Type"] = "application/json"
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return resp


def _get_param(request: Request, key: str) -> str:
    # admite querystring o JSON body
    value = request.args.get(key)
    if value:
        return value.strip()
    try:
        data = request.get_json(silent=True) or {}
        value = data.get(key, "")
        return str(value).strip()
    except Exception:
        return ""


def export_on_demand_http(request: Request):
    # Manejo preflight CORS
    if request.method == "OPTIONS":
        resp = make_response("", 204)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Headers"] = "*"
        resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
        return resp
    cliente = _get_param(request, "cliente")
    localidad = _get_param(request, "localidad")
    ruta_id = _get_param(request, "rutaId")

    if not (cliente and localidad and ruta_id):
        return _json_response({"error": "Parámetros requeridos: cliente, localidad, rutaId"}, 400)

    # Inicializar clientes
    firestore_client = firestore.Client()
    storage_client = storage.Client()

    # Verificar que la ruta existe
    ruta_ref = firestore_client.collection("Rutas").document(ruta_id)
    ruta_doc = ruta_ref.get()
    if not ruta_doc.exists:
        return _json_response({"error": f"Ruta {ruta_id} no encontrada"}, 404)

    # Leer subcolecciones (RutaRecorrido) y exportar a CSV
    subcollection = ruta_ref.collection("RutaRecorrido")
    docs = list(subcollection.stream())
    # Ordenar por ID numérico
    docs = sorted(docs, key=lambda d: int(d.id)) if docs else []

    # Calcular porcentaje completado
    total_docs = len(docs)
    completed_docs = sum(1 for doc in docs if (doc.to_dict() or {}).get("lectura_actual"))
    completion_percentage = (completed_docs / total_docs) * 100 if total_docs > 0 else 0

    # Actualizar campo 'completado' en la ruta
    ruta_ref.update({"completado": completion_percentage})

    export_bucket_name = os.environ.get("EXPORT_BUCKET_NAME", "testados-rutas-exportadas")
    object_name = f"{cliente}/{localidad}/{ruta_id}.csv"
    bucket = storage_client.bucket(export_bucket_name)
    blob = bucket.blob(object_name)

    # Escribir CSV
    header_written = False
    with blob.open("wt", newline="") as csv_file:
        writer = csv.writer(csv_file)
        for doc in docs:
            row = doc.to_dict() or {}
            if not header_written:
                writer.writerow(list(row.keys()))
                header_written = True
            writer.writerow(list(row.values()))

    public_url = f"https://storage.googleapis.com/{export_bucket_name}/{object_name}"

    # Redirección directa para evitar CORS en front si se usa navegación
    if (_get_param(request, "redirect") or "").lower() in ("1", "true", "yes"): 
        resp = make_response("", 302)
        resp.headers["Location"] = public_url
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Headers"] = "*"
        resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
        return resp

    return _json_response({"url": public_url, "completado": completion_percentage})


