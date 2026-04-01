# InfoFiscal - Sistema de Gestión Contable con Integración AFIP

Sistema completo de gestión contable para contadores con integración directa a los Web Services de AFIP.

## ✨ Características

- ✅ **Integración completa con AFIP Web Services**
  - WSFEv1 (Factura Electrónica tradicional)
  - WSMTXCA (Monotributo con detalle)
  - WSFEX (Factura de Exportación)

- ✅ **Gestión de clientes**
  - Base de datos SQLite
  - CRUD completo de clientes
  - Seguimiento de facturas

- ✅ **Autenticación segura**
  - Sistema de login con control de intentos
  - Certificados digitales AFIP
  - Tokens con caché inteligente

## 🚀 Instalación

### Requisitos previos

```bash
Python 3.13+
Git for Windows (incluye OpenSSL)
```

### Instalación

```bash
# Clonar repositorio
git clone [URL_DEL_REPO]
cd infofiscal

# Instalar dependencias
pip install -r requirements.txt

# Configurar certificados AFIP
# Copiar certificado.crt y clave_privada.key a carpeta certs/
```

### Configuración

Crear archivo `.env` en la raíz del proyecto:

```env
# Configuración AFIP
AFIP_CERT_PATH=certs/certificado.crt
AFIP_KEY_PATH=certs/clave_privada.key
AFIP_CUIT=20321518045
AFIP_ENV=prod

# Configuración Base de Datos
DB_PATH=infofiscal.db
```

## 📋 Uso

### Iniciar la aplicación

```bash
python src/app.py
```

Acceder a: http://localhost:5000

### Usuario por defecto

- **Usuario**: admin
- **Contraseña**: (configurar en primer acceso)

## 📁 Estructura del Proyecto

```
infofiscal/
├── src/
│   ├── app.py                  # Aplicación Flask principal
│   ├── wsfev1_client.py        # Cliente WSFEv1
│   ├── wsmtxca_client.py       # Cliente WSMTXCA
│   └── wsfexv1_client.py       # Cliente WSFEX
├── templates/
│   └── index.html              # Frontend principal
├── static/
│   ├── css/
│   └── js/
├── certs/
│   ├── certificado.crt         # Certificado AFIP
│   └── clave_privada.key       # Clave privada
├── tests_y_pruebas/            # Scripts de prueba
├── .env                        # Configuración (no incluido en git)
├── crear_db.py                 # Script para crear BD
├── requirements.txt            # Dependencias Python
└── README.md                   # Este archivo
```

## 🔧 Utilidades

### Crear base de datos

```bash
python crear_db.py
```

### Ver clientes

```bash
python ver_clientes.py
```

### Consultar puntos de venta AFIP

```bash
python consultar_puntos_venta.py
```

## 📡 Servicios AFIP Integrados

### WSFEv1 - Factura Electrónica

Permite consultar facturas tipos A, B, C, M emitidas desde 2011.

**Requisitos:**
- Punto de venta configurado como "Factura Electrónica - Web Services"
- Delegación del servicio "Facturación Electrónica" en Administrador de Relaciones

### WSMTXCA - Monotributo

Para monotributistas que emiten con detalle de productos.

**Requisitos:**
- Punto de venta configurado como "Factura Electrónica - Monotributo - Web Services"
- Delegación del servicio "Factura Electrónica con Detalle - MTXCA"

### WSFEX - Exportación

Para facturas de exportación tipo E.

## 🔐 Configuración de Delegaciones AFIP

Para que un contador pueda consultar facturas de clientes:

1. **Cliente** debe ingresar a AFIP con Clave Fiscal
2. Ir a **"Administrador de Relaciones"**
3. **"Nueva Relación"**
4. Representante: CUIT del contador
5. Servicios a delegar:
   - ✅ Facturación Electrónica
   - ✅ Factura Electrónica con Detalle - MTXCA (si corresponde)
6. Permisos: **Consulta** y **Presentación**
7. Guardar y esperar 15-30 minutos para sincronización

## ⚠️ Notas Importantes

### Limitaciones conocidas

- **"Factura en Línea"** del portal AFIP NO es accesible vía Web Services
- Solo se pueden consultar facturas emitidas vía Web Services
- Las delegaciones pueden tardar hasta 30 minutos en sincronizar

### Ambiente de producción vs homologación

- **Producción**: Facturas reales, certificado de producción
- **Homologación**: Pruebas, certificado de testing (obtener vía WSASS)

## 🛠️ Solución de Problemas

### Error 600: "No apareció CUIT en lista de relaciones"

**Causa**: Falta delegación o no está sincronizada

**Solución**:
1. Verificar delegación en Administrador de Relaciones
2. Esperar 30 minutos
3. Verificar que el servicio sea "Facturación Electrónica" (no genérico)

### Error: "OpenSSL no encontrado"

**Causa**: OpenSSL no está instalado o no está en PATH

**Solución**:
- Instalar Git for Windows (incluye OpenSSL)
- O instalar OpenSSL manualmente

### "Último comprobante = 0" pero sé que hay facturas

**Causa**: Las facturas fueron emitidas con "Factura en Línea" (portal web)

**Solución**:
- Crear punto de venta tipo "Web Services"
- Futuras facturas usar ese punto de venta

## 📞 Soporte

Para problemas con AFIP:
- Email: mayuda@afip.gov.ar
- Tel: 0810-999-2347

## 📄 Licencia

Este proyecto es privado y de uso interno.

## 🙏 Agradecimientos

Desarrollado con asistencia de Claude (Anthropic)
