# AFIP Extract by Date - Documentación

## Descripción

`afip_extract_by_date.py` es un script completo para extraer comprobantes electrónicos de AFIP WSFEv1 por rango de fechas. Implementa todas las mejores prácticas para interactuar con los servicios web de AFIP de manera robusta y eficiente.

## Características

### ✅ Funcionalidades Principales
- **Autenticación WSAA** con certificados PKCS#7 usando OpenSSL
- **Consulta WSFEv1** completa (puntos de venta, tipos de comprobante, consultas individuales)
- **Extracción inteligente** por rango de fechas con recorrido hacia atrás
- **Exportación dual**: CSV (campos planos) y JSON (con datos _raw completos)
- **CLI configurable** con múltiples opciones y validaciones
- **Logging estructurado** con niveles DEBUG/INFO
- **Manejo robusto de errores** HTTP, SOAP Fault, OpenSSL, etc.

### 🛡️ Características de Robustez
- **Cortes inteligentes**: Por fecha (cuando encuentra comprobantes anteriores al rango) y por huecos (máximo de números consecutivos inexistentes)
- **Rate limiting**: Sleep configurable entre requests para no saturar AFIP
- **Validación completa**: Argumentos CLI, fechas, configuración .env, certificados
- **Resiliencia**: Manejo de timeouts, errores de red, SOAP faults
- **Compatibilidad**: Funciona en producción y homologación

## Instalación

### 1. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 2. Configurar certificados AFIP
Asegúrese de tener sus certificados en formato PEM:
```
certs/
├── certificado.crt    # Certificado público AFIP
└── clave_privada.key  # Clave privada (sin contraseña)
```

### 3. Configurar variables de entorno
Copie `.env.ejemplo` a `.env` y complete:
```bash
cp .env.ejemplo .env
```

Edite `.env`:
```env
AFIP_ENV=prod
AFIP_CUIT=20321518045
AFIP_CERT_PATH=certs/certificado.crt
AFIP_KEY_PATH=certs/clave_privada.key
LOG_LEVEL=INFO
```

### 4. Verificar OpenSSL
El script requiere OpenSSL disponible en PATH:
```bash
openssl version
```

## Uso

### Ejemplos Básicos

```bash
# Extraer todo el año 2025
python afip_extract_by_date.py --desde 2025-01-01 --hasta 2025-12-31

# Extraer enero 2025 con nombre personalizado
python afip_extract_by_date.py --desde 2025-01-01 --hasta 2025-01-31 --out facturas_enero_2025

# Solo facturas A, B, C (tipos 1, 6, 11)
python afip_extract_by_date.py --desde 2025-01-01 --hasta 2025-01-31 --incluir-tipos 1,6,11

# Excluir notas de crédito/débito (tipos 201, 202)
python afip_extract_by_date.py --desde 2025-01-01 --hasta 2025-01-31 --excluir-tipos 201,202
```

### Parámetros Avanzados

```bash
# Configurar velocidad y límites
python afip_extract_by_date.py \
  --desde 2025-01-01 \
  --hasta 2025-01-31 \
  --sleep-ms 100 \
  --max-vacios 50 \
  --out facturas_lentas
```

### Opciones CLI Completas

| Parámetro | Requerido | Default | Descripción |
|-----------|-----------|---------|-------------|
| `--desde` | ✅ | - | Fecha inicio (YYYY-MM-DD) |
| `--hasta` | ✅ | - | Fecha fin (YYYY-MM-DD) |
| `--incluir-tipos` | ❌ | todos | Tipos a incluir (ej: 11,13,15) |
| `--excluir-tipos` | ❌ | ninguno | Tipos a excluir (ej: 201,202) |
| `--out` | ❌ | `facturas_afip` | Nombre base archivos salida |
| `--sleep-ms` | ❌ | 40 | Pausa entre requests (ms) |
| `--max-vacios` | ❌ | 80 | Máx. huecos consecutivos |

## Funcionamiento Interno

### Estrategia de Extracción

El script implementa la estrategia de **"recorrido hacia atrás"** porque WSFEv1 no tiene un método directo para listar comprobantes por fecha:

1. **Obtener metadatos**: Lista puntos de venta y tipos de comprobante disponibles
2. **Por cada (PtoVta, Tipo)**:
   - Obtener último comprobante autorizado (`FECompUltimoAutorizado`)
   - Recorrer hacia atrás desde el último número
   - Consultar cada comprobante individualmente (`FECompConsultar`)
   - Filtrar por rango de fechas (`CbteFch`)
3. **Cortes inteligentes**:
   - **Por fecha**: Si encuentra un comprobante anterior al rango, corta esa rama
   - **Por huecos**: Si encuentra muchos números consecutivos inexistentes, corta

### Manejo de Errores

- **Error 602**: Comprobante inexistente (hueco normal)
- **SOAP Fault**: Errores de servicio AFIP
- **HTTP errors**: Problemas de conectividad
- **OpenSSL errors**: Problemas de certificados
- **Timeout**: Configurables por request

## Archivos de Salida

### CSV (campos planos)
```csv
PtoVta,CbteTipo,CbteNro,CbteFch,DocTipo,DocNro,ImpTotal,ImpNeto,ImpOpEx,ImpIVA,MonId,MonCotiz,CAE,CAE_FchVto
1,11,1,20250115,80,20321518045,1250.00,1033.88,0.00,216.12,PES,1.000000,70123456789,20250125
```

### JSON (con datos _raw)
```json
[
  {
    "PtoVta": 1,
    "CbteTipo": 11,
    "CbteNro": 1,
    "CbteFch": "20250115",
    "DocTipo": 80,
    "DocNro": "20321518045",
    "ImpTotal": 1250.00,
    "_raw": {
      // Objeto completo de respuesta AFIP
      // Útil para generar PDFs, QRs, etc.
    }
  }
]
```

## Tipos de Comprobante Comunes

| Código | Descripción |
|--------|-------------|
| 1 | Factura A |
| 6 | Factura B |
| 11 | Factura C |
| 13 | Factura M |
| 201 | Nota de Crédito A |
| 202 | Nota de Crédito B |

## Logging

### Niveles disponibles
- **INFO**: Progreso general, resumen de resultados
- **DEBUG**: Detalles técnicos, requests individuales

### Mensajes importantes
- ✅ Autenticación WSAA exitosa y expiración del token
- 📊 Puntos de venta y tipos detectados
- ✂️ Cortes por fecha o huecos máximos
- 📁 Paths de archivos exportados
- 🔢 Conteo final de comprobantes

## Solución de Problemas

### OpenSSL no encontrado
```bash
# Windows - Instalar Git (incluye OpenSSL)
# O descargar OpenSSL para Windows

# Linux/Mac
sudo apt-get install openssl  # Ubuntu/Debian
brew install openssl          # macOS
```

### Certificados inválidos
- Verificar que están en formato PEM
- Verificar que la clave privada no tiene contraseña
- Verificar que están habilitados para WSAA y WSFE en AFIP

### Errores de autenticación
- Verificar CUIT en .env
- Verificar que el entorno (prod/homo) coincide con los certificados
- Verificar delegaciones en AFIP para el CUIT consultor

### Performance lenta
- Reducir `--max-vacios` si hay muchos huecos
- Aumentar `--sleep-ms` si AFIP rechaza requests
- Usar `--incluir-tipos` para limitar consultas

## Arquitectura del Código

```
afip_extract_by_date.py
├── Imports y configuración
├── Dataclasses (WsaaCredentials, ExtractConfig)
├── Utilidades de fecha
├── WSAA (autenticación)
│   ├── build_login_ticket_request()
│   ├── sign_tra_pkcs7_openssl()
│   └── wsaa_login()
├── Cliente WSFE
│   ├── WsfeClient.__init__()
│   ├── get_ptos_venta()
│   ├── get_tipos_cbte()
│   ├── get_ultimo_autorizado()
│   └── consultar_cbte()
├── Extracción por rango
│   └── extraer_comprobantes()
├── Exportación
│   └── export_csv_json()
└── CLI y main()
```

## Notas Técnicas

- **PDF del portal**: No se obtiene por WS; usar `_raw` para generar después
- **QR codes**: Generables con datos del `_raw` + algoritmo AFIP
- **Rate limits**: AFIP puede limitar requests; ajustar `sleep_ms`
- **Timeouts**: Configurables per-request, default 30s
- **Memory**: Procesa de a uno, no carga todo en memoria

---

**Nota**: Este script está optimizado para uso en producción con manejo robusto de errores y logging completo. Para consultas puntuales, considere usar la aplicación web infoFiscal.