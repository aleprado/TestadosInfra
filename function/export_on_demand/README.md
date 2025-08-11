# Función de Exportación On-Demand

## Descripción
Esta función permite exportar datos de una ruta específica a CSV cuando se solicita, en lugar de ejecutarse automáticamente por cron.

## Formato de Nombres de Archivo
Los archivos CSV generados ahora tienen nombres con timestamps legibles para facilitar el seguimiento:

**Formato anterior:**
```
001_BAYAUCA_02_2025_1703123456789.csv
```

**Formato nuevo (legible):**
```
001_BAYAUCA_02_2025_2023-12-20_14-30-25.csv
```

## Estructura del Nombre de Archivo
```
{cliente}/{localidad}/{ruta_id}_{YYYY-MM-DD_HH-MM-SS}.csv
```

### Ejemplos:
- `tomatitos/Bayauca/001_BAYAUCA_02_2025_2023-12-20_14-30-25.csv`
- `tomatitos/Bayauca/002_BAYAUCA_03_2025_2023-12-20_15-45-12.csv`

## Ventajas del Nuevo Formato
1. **Legibilidad**: Fácil identificar cuándo se generó cada archivo
2. **Ordenamiento**: Los archivos se ordenan cronológicamente por nombre
3. **Trazabilidad**: Mantiene historial de exportaciones por ruta
4. **Mantenimiento**: Facilita la limpieza de archivos antiguos

## Parámetros de Entrada
- `cliente`: ID del cliente
- `localidad`: ID de la localidad  
- `rutaId`: ID de la ruta
- `t`: Timestamp en milisegundos (opcional, se convierte a formato legible)

## Respuesta
```json
{
  "success": true,
  "url": "https://storage.googleapis.com/bucket/...",
  "filename": "tomatitos/Bayauca/001_BAYAUCA_02_2025_2023-12-20_14-30-25.csv",
  "timestamp": "2023-12-20_14-30-25",
  "porcentaje_completado": 75.5
}
```

## Despliegue
Para desplegar esta función:

```bash
cd TestadosInfra
terraform apply
```

La función se desplegará automáticamente como parte de la infraestructura.
