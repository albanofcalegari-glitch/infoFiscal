# 🚀 RESUMEN RÁPIDO: Obtener Permisos WSFEXv1

## 🎯 **LO QUE NECESITAS HACER:**

```
📍 PASO 1: IR A MI AFIP
└── 🌐 https://auth.afip.gob.ar
    ├── 🔑 Login con CUIT y Clave Fiscal
    └── 📱 Completar 2FA

📍 PASO 2: BUSCAR WEB SERVICES  
└── 🔍 Buscar "Web Services" o "Administrador de Relaciones"
    └── 🎯 Encontrar "WSFEXv1" en la lista

📍 PASO 3: SOLICITAR ACCESO
└── ➕ Hacer clic "Agregar" o "Solicitar Acceso"
    └── 📝 Completar formulario

📍 PASO 4: ESPERAR APROBACIÓN
└── ⏰ 1-10 días hábiles
    ├── 📧 Vas a recibir email de confirmación
    └── 🧪 Primero homologación, después producción
```

## 📝 **DATOS PARA EL FORMULARIO:**

```
🏢 Sistema: "Consulta de Facturas Electrónicas InfoFiscal"
📧 Email: [tu_email_técnico]
📱 Teléfono: [tu_número] 
🎯 Descripción: "Sistema para consultar facturas de monotributistas 
                 y exportadores. Integración con WSFEXv1 para 
                 completar cobertura de todos los tipos de comprobantes."
💼 Uso: ☑️ Consulta ☐ Emisión
🔧 Justificación: "Necesario para consultar facturas tipo M que no 
                   están disponibles en WSFEv1. Complementa sistema 
                   existente que ya usa WSFEv1."
```

## ⚡ **VERIFICAR ESTADO:**

```bash
# Ejecutar este script para verificar si ya tenés autorización:
python verificador_autorizacion_wsfexv1.py
```

## 🎉 **UNA VEZ AUTORIZADO:**

```python
# Tu factura 0002-00000235 será accesible con:
from busqueda_hibrida_wsfev1_wsfexv1 import buscar_factura_especifica_hibrida

factura = buscar_factura_especifica_hibrida("27312238018", 2, 235)
# Debería encontrarla en WSFEXv1 como Factura M
```

## 📞 **AYUDA:**
- 📧 **Email:** webservice@afip.gob.ar
- 📱 **Tel:** 0800-999-2347  
- 📖 **Guía completa:** `GUIA_OBTENER_PERMISOS_WSFEXV1.md`

---
**⏰ Tiempo estimado total: 2-3 semanas**