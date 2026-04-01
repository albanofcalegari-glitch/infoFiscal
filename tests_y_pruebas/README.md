# InfoFiscal - Sistema de Gestión Contable con Integración AFIP

Una aplicación web profesional para estudios contables con integración completa a los servicios web de AFIP/ARCA.

## 🎯 Características Principales

### 🔐 **Autenticación Segura**
- Sistema de login con bcrypt
- Gestión de sesiones seguras
- Panel de administración

### 👥 **Gestión de Clientes**
- Búsqueda dinámica por CUIT/Razón Social
- Sistema de delegaciones AFIP
- Confirmación de clientes antes de descargas

### 📄 **Descarga de Facturas**
- Integración real con servicios WSFE de AFIP
- Modo simulación para testing
- Descarga automática en formato ZIP
- Soporte para múltiples períodos

### 🏢 **Sistema de Delegaciones**
- Manejo de autorizaciones AFIP
- Consulta de facturas de terceros autorizados
- Configuración automática de permisos

## 🚀 Instalación

### Requisitos Previos
- Python 3.8+
- OpenSSL (para certificados AFIP)
- Git

### Configuración del Proyecto

1. **Clonar el repositorio**
```bash
git clone https://github.com/tu-usuario/infofiscal.git
cd infofiscal
```

2. **Crear entorno virtual**
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

4. **Configurar base de datos**
```bash
python crear_db.py
```

5. **Configurar certificados AFIP**
- Seguir las instrucciones en `INSTRUCCIONES_PRODUCCION.txt`
- Generar certificados con `generar_certificados.py`

## 📱 Uso de la Aplicación

### Iniciar el Sistema
```bash
python src/app.py
```

Acceder a: http://127.0.0.1:5000
- **Usuario**: admin
- **Contraseña**: admin123

### Verificar Servicios AFIP
```bash
# Verificación manual
python verificar_servicios.py

# Monitoreo automático
.\monitor_afip.bat

# Verificación rápida
.\check.bat
```

### Cambiar Modo de Operación
```bash
# Activar producción (servicios reales AFIP)
python cambiar_modo.py produccion

# Activar simulación (facturas de ejemplo)
python cambiar_modo.py simulacion
```

## 🏗️ Estructura del Proyecto

```
infofiscal/
├── src/                      # Código fuente
│   ├── app.py               # Aplicación Flask principal
│   ├── arca_service_simple.py # Integración AFIP/ARCA
│   └── config_cuits.py      # Configuración de CUITs
├── templates/               # Plantillas HTML
│   ├── login.html
│   ├── home.html
│   └── consultafacturacliente.html
├── static/                  # Archivos estáticos
│   └── estudio.css         # Estilos CSS
├── certs/                   # Certificados AFIP
├── facturas/               # Facturas descargadas
├── crear_db.py             # Inicialización de BD
├── verificar_servicios.py  # Verificación AFIP
├── monitor_afip.bat        # Monitor automático
└── requirements.txt        # Dependencias
```

## 🔧 Configuración AFIP

### 1. Generar Certificados
```bash
python generar_certificados.py
```

### 2. Habilitar Servicios Web
1. Ingresar a https://auth.afip.gob.ar/
2. Ir a "Administrador de Relaciones"
3. Habilitar "Web Service Facturación Electrónica"
4. Asociar certificado digital
5. Esperar activación (hasta 24 horas)

### 3. Verificar Estado
```bash
python verificar_servicios.py
```

## 👥 Sistema de Delegaciones

### Configurar Cliente Delegado
```bash
python agregar_cliente_delegado.py
```

### Estructura de Delegación
- **Tu CUIT**: 20-32151804-5 (operador)
- **Cliente CUIT**: 23-33373021-9 (autoriza acceso)
- **Configuración**: `src/config_cuits.py`

## 🔄 Estados de Operación

### Modo Simulación ✅
- Facturas de ejemplo
- Sin conexión a AFIP
- Ideal para desarrollo y testing

### Modo Producción 🚀
- Servicios reales de AFIP
- Facturas legales descargables
- Requiere servicios habilitados

## 📊 Base de Datos

### Tabla: usuarios
- id, usuario, password_hash, activo

### Tabla: clientes  
- id, cuit, razon_social, activo

### Inicialización
```bash
python crear_db.py
```

## 🛠️ Herramientas de Desarrollo

### Scripts Útiles
- `verificar_servicios.py`: Estado de AFIP
- `cambiar_modo.py`: Alternar simulación/producción
- `monitor_afip.bat`: Verificación automática
- `check.bat`: Verificación rápida

### Logs y Monitoreo
- `monitor_log.txt`: Historial de verificaciones
- Notificaciones sonoras cuando AFIP está activo
- Verificación cada 5 minutos automática

## 🔒 Seguridad

### Autenticación
- Contraseñas hasheadas con bcrypt
- Sesiones Flask seguras
- Validación de permisos por ruta

### AFIP Integration
- Certificados digitales X.509
- Firmas CMS con OpenSSL
- Tokens de autenticación WSAA

## 📋 Dependencias

Ver `requirements.txt` para lista completa:
- Flask (framework web)
- bcrypt (autenticación)
- requests (HTTP)
- pathlib (manejo de archivos)
- sqlite3 (base de datos)

## 🤝 Contribuir

1. Fork el proyecto
2. Crear rama de feature (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir Pull Request

## 📞 Soporte

### AFIP
- Teléfono: 0800-999-2347
- Web: https://www.afip.gob.ar/

### Documentación
- `INSTRUCCIONES_PRODUCCION.txt`: Guía completa AFIP
- `GUIA_SERVICIOS_AFIP.txt`: Pasos detallados

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver `LICENSE` para detalles.

## 🎯 Estado del Proyecto

### ✅ Completado
- Sistema de autenticación
- Gestión de clientes
- Integración AFIP básica
- Sistema de delegaciones
- Interfaz web responsive
- Generación de certificados
- Monitoreo automático

### 🚧 En Desarrollo
- Reportes avanzados
- Notificaciones email
- API REST
- Dashboard analytics

### 📋 Por Hacer
- Tests automatizados
- Documentación API
- Docker deployment
- Backup automático

---

**Desarrollado para estudios contables argentinos** 🇦🇷  
*Integración completa con AFIP/ARCA*