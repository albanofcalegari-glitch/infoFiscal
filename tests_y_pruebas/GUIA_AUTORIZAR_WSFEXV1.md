# 🔐 GUÍA COMPLETA: Cómo Autorizar WSFEXv1 en AFIP

## 📋 **¿QUÉ ES WSFEXv1?**

WSFEXv1 es el servicio web de AFIP para:
- ✅ **Facturas de Monotributistas** (tipo M)
- ✅ **Facturas de Exportación**
- ✅ **Comprobantes especiales** no cubiertos por WSFEv1

## 🎯 **PASO A PASO PARA AUTORIZACIÓN**

### 1️⃣ **REQUISITOS PREVIOS**
- 📋 Tener **CUIT activo** en AFIP
- 🔐 Acceso a **Mi AFIP** con Clave Fiscal
- 📄 Certificado digital válido (el mismo que usas para WSFEv1)
- 🏢 Estar registrado como **desarrollador** en AFIP

### 2️⃣ **PROCESO DE AUTORIZACIÓN**

#### **A. Ingresar a Mi AFIP**
1. 🌐 Ir a https://auth.afip.gob.ar/contribuyente_/login.xhtml
2. 🔑 Ingresar con tu CUIT y Clave Fiscal
3. 📱 Completar autenticación de dos factores

#### **B. Buscar el Servicio WSFEXv1**
1. 📋 En el menú principal buscar **"Administrador de Relaciones de Clave Fiscal"**
2. 🔍 O buscar directamente **"Web Services"** 
3. 📂 Ir a **"Servicios Interactivos"** → **"Web Services"**

#### **C. Solicitar Autorización**
1. 🔍 Buscar **"Servicio Web de Facturación Electrónica Exportadores y Monotributistas (WSFEXv1)"**
2. ➕ Hacer clic en **"Agregar"** o **"Solicitar Acceso"**
3. 📝 Completar el formulario de solicitud

### 3️⃣ **FORMULARIO DE SOLICITUD**

Vas a necesitar proporcionar:

```
📋 DATOS REQUERIDOS:
├── 🏢 Razón Social de tu empresa/sistema
├── 📧 Email de contacto técnico
├── 📱 Teléfono de contacto
├── 🎯 Descripción del sistema que vas a desarrollar
├── 🔧 Tipo de comprobantes que vas a manejar
└── 📄 Certificado digital (el mismo de WSFEv1)
```

#### **Ejemplo de Descripción:**
```
"Sistema de gestión de facturas electrónicas para monotributistas.
Permite la emisión, consulta y gestión de facturas tipo M.
Integración con WSFEXv1 para automatizar procesos de facturación."
```

### 4️⃣ **TIPOS DE ACCESO DISPONIBLES**

Al solicitar, especifica qué necesitas:

```
🎯 OPCIONES DE ACCESO:
├── 📋 Solo Consulta (FEXConsultarComprobante, etc.)
├── ✍️  Emisión y Consulta (FEXAutorizar + consultas)
├── 🔧 Acceso completo (todos los métodos)
└── 📊 Ambiente (Homologación y/o Producción)
```

### 5️⃣ **PROCESO DE APROBACIÓN**

#### **Tiempos:**
- ⏰ **Homologación**: 1-3 días hábiles
- ⏰ **Producción**: 5-10 días hábiles (después de probar homologación)

#### **Estados posibles:**
```
📊 ESTADOS:
├── 🟡 Pendiente de aprobación
├── 🟢 Aprobado para Homologación  
├── 🔵 Aprobado para Producción
└── 🔴 Rechazado (requiere correcciones)
```

### 6️⃣ **VERIFICAR AUTORIZACIÓN**

Una vez aprobado, podes verificar con:

```python
# Test básico de autorización WSFEXv1
from wsfexv1_client import WSFEXv1Client

client = WSFEXv1Client(
    cert_path='certs/certificado.crt',
    key_path='certs/clave_privada.key',
    ambiente='homologacion'  # Primero en homologación
)

try:
    # Probar obtener tipos de comprobante
    tipos = client.obtener_tipos_comprobante("TU_CUIT")
    if tipos:
        print("✅ AUTORIZACIÓN WSFEXv1 CONFIRMADA")
        print(f"📋 Tipos disponibles: {tipos}")
    else:
        print("❌ Sin autorización aún")
except Exception as e:
    print(f"❌ Error: {e}")
```

### 7️⃣ **CASOS ESPECIALES**

#### **Si sos Monotributista:**
- 🎯 Necesitas WSFEXv1 para **emitir** tus propias facturas M
- 📋 Para **consultar** facturas M de otros, también necesitas autorización

#### **Si desarrollas para terceros:**
- 🏢 Necesitas autorización como **desarrollador**
- 📋 Cada cliente debe autorizar tu certificado en su AFIP
- 🔐 Manejo de múltiples CUITs con el mismo certificado

### 8️⃣ **ALTERNATIVAS MIENTRAS ESPERAS**

#### **Para Facturas M (Monotributo):**
```python
# Algunas facturas M pueden estar en WSFEv1
# Probar tipos 51-54 antes de solicitar WSFEXv1
tipos_m_wsfev1 = [51, 52, 53, 54]  # Facturas M en WSFEv1
```

#### **Para Consultas Generales:**
```python
# WSFEv1 cubre la mayoría de casos
# Solo necesitas WSFEXv1 para casos específicos
```

## ⚠️ **ERRORES COMUNES**

### **Error HTTP 500:**
```
❌ "Internal Server Error"
💡 = Sin autorización WSFEXv1
🔧 = Necesitas completar el proceso de solicitud
```

### **Error de Certificado:**
```
❌ "Certificate error" 
💡 = Usar el MISMO certificado de WSFEv1
🔧 = No necesitas certificado nuevo
```

### **Error de CUIT:**
```
❌ "CUIT no autorizado"
💡 = El CUIT no tiene permisos WSFEXv1  
🔧 = Verificar autorización en Mi AFIP
```

## 📞 **CONTACTO AFIP**

Si tenés problemas:

```
📞 SOPORTE TÉCNICO AFIP:
├── 🌐 Web: https://www.afip.gob.ar/ws/
├── 📧 Email: webservice@afip.gob.ar  
├── 📱 Tel: 0800-999-AFIP (2347)
└── 🕒 Horarios: Lunes a Viernes 8-20hs
```

## 🎯 **RESUMEN RÁPIDO**

```bash
# Pasos principales:
1. 🌐 Ingresar a Mi AFIP
2. 🔍 Buscar "WSFEXv1" en Web Services  
3. ➕ Solicitar acceso
4. 📝 Completar formulario con datos del sistema
5. ⏳ Esperar aprobación (1-10 días)
6. ✅ Probar en homologación
7. 🚀 Solicitar producción
```

## 💡 **CONSEJOS ADICIONALES**

- 📋 **Sé específico** en la descripción del sistema
- 🔧 **Menciona integración** con sistemas existentes
- 📊 **Solicita homologación primero**, después producción
- ⏰ **Ten paciencia** - es un proceso manual de AFIP
- 📞 **Contacta soporte** si demora más de 15 días

---

**🎯 Una vez autorizado, tu factura 0002-00000235 debería ser consultable desde WSFEXv1!**