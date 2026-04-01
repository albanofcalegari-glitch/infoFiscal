# 🔐 GUÍA PASO A PASO: Obtener Autorización WSFEXv1 en AFIP

## 🎯 **OBJETIVO**
Obtener autorización para **WSFEXv1** (Facturación Electrónica para Monotributistas y Exportadores) para poder consultar facturas como la **0002-00000235** del CUIT **27312238018**.

---

## 📋 **PASO 1: Preparación Previa**

### ✅ **Requisitos:**
- 📄 **CUIT activo** en AFIP  
- 🔑 **Clave Fiscal Nivel 3** (con token físico o app móvil)
- 📱 **Dispositivo para autenticación de dos factores**
- 💻 **Navegador web actualizado**
- 📋 **Datos de tu sistema/aplicación** para completar el formulario

### 📝 **Información que vas a necesitar:**
```
📊 DATOS PARA EL FORMULARIO:
├── 🏢 Razón social de tu empresa/sistema
├── 📧 Email de contacto técnico  
├── 📱 Teléfono de contacto
├── 🎯 Descripción del sistema
├── 💼 Tipo de uso (consulta/emisión)
└── 🔧 Justificación técnica
```

---

## 🚀 **PASO 2: Acceso a Mi AFIP**

### 1️⃣ **Ingresar a Mi AFIP:**
```
🌐 URL: https://auth.afip.gob.ar/contribuyente_/login.xhtml
```

### 2️⃣ **Login:**
1. 🔢 Ingresá tu **CUIT** (sin guiones)
2. 🔑 Ingresá tu **Clave Fiscal**
3. 📱 Completá la **autenticación de dos factores**

### 3️⃣ **Verificar nivel de clave:**
- ✅ Necesitas **Clave Fiscal Nivel 3**
- ❌ Si tenés Nivel 2, primero tenés que actualizarla

---

## 🔍 **PASO 3: Encontrar el Servicio WSFEXv1**

### 📂 **Navegación en Mi AFIP:**

#### **Opción A - Búsqueda Directa:**
1. 🔍 En el **buscador** de Mi AFIP, escribí: `"Web Services"`
2. 🎯 Seleccioná: **"Administrador de Relaciones de Clave Fiscal"**

#### **Opción B - Navegación por Menú:**
1. 📋 **Sistema** → **Administración**
2. 🔧 **Administrador de Relaciones de Clave Fiscal**
3. 🌐 **Web Services**

#### **Opción C - Acceso Directo:**
1. 🔗 Buscá **"Servicios Interactivos"**
2. 🌐 **Web Services**
3. 📋 **Consultar Relaciones Vigentes**

---

## 📝 **PASO 4: Solicitar Autorización WSFEXv1**

### 🔍 **Buscar el servicio específico:**
En la lista de servicios web disponibles, buscá:
```
📋 NOMBRE EXACTO:
"Servicio Web de Facturación Electrónica Exportadores y Monotributistas (WSFEXv1)"

🔍 ALIAS POSIBLES:
- WSFEXv1
- Facturación Electrónica Exportadores
- Monotributistas WSFEXv1
```

### ➕ **Agregar el servicio:**
1. ✅ Hacer clic en **"Agregar"** o **"Solicitar Acceso"**
2. 📋 Se abrirá un **formulario de solicitud**

---

## 📋 **PASO 5: Completar el Formulario**

### 📝 **Ejemplo de formulario completado:**

```
🏢 RAZÓN SOCIAL DEL SISTEMA:
"Sistema de Consulta de Facturas Electrónicas InfoFiscal"

📧 EMAIL DE CONTACTO:
tu_email@dominio.com

📱 TELÉFONO:
+54 11 XXXX-XXXX

🎯 DESCRIPCIÓN DEL SISTEMA:
"Sistema web para consulta y gestión de facturas electrónicas. 
Permite a contribuyentes consultar sus comprobantes emitidos 
a través de los servicios web de AFIP (WSFEv1 y WSFEXv1). 
Integración técnica para automatización de procesos contables."

💼 TIPO DE USO:
☑️ Consulta de comprobantes
☐ Emisión de comprobantes  
☐ Ambos

🔧 JUSTIFICACIÓN TÉCNICA:
"Necesidad de consultar facturas tipo M (monotributo) y de 
exportación que no están disponibles en WSFEv1. El sistema 
requiere acceso completo a todos los tipos de comprobantes 
para brindar un servicio integral a los usuarios."

📄 CERTIFICADO DIGITAL:
☑️ Utilizar el mismo certificado de WSFEv1
```

### ⚠️ **Consejos para el formulario:**
- 📝 **Sé específico** sobre la funcionalidad
- 🎯 **Menciona la integración** con servicios existentes
- 💼 **Justifica la necesidad** de acceso a facturas M
- 📧 **Usa un email técnico** que revises frecuentemente

---

## ⏱️ **PASO 6: Proceso de Aprobación**

### 📊 **Tiempos estimados:**
```
⏰ HOMOLOGACIÓN (Testing):
├── 📅 Tiempo: 1-3 días hábiles
├── 🎯 Propósito: Pruebas técnicas
└── 🔧 Ambiente: Homologación

⏰ PRODUCCIÓN:
├── 📅 Tiempo: 5-10 días hábiles adicionales
├── 🎯 Propósito: Uso en vivo
└── 🔧 Ambiente: Producción
```

### 📧 **Seguimiento:**
- 📬 Vas a recibir **emails de confirmación**
- 🔍 Podés **consultar el estado** en Mi AFIP
- 📞 Si demora más de 15 días, **contactar soporte**

---

## 🧪 **PASO 7: Probar la Autorización**

### ✅ **Una vez aprobado (Homologación):**

```python
# Crear archivo: test_autorizacion_wsfexv1.py
from wsfexv1_client import WSFEXv1Client

def probar_autorizacion():
    client = WSFEXv1Client(
        cert_path='certs/certificado.crt',
        key_path='certs/clave_privada.key',
        ambiente='homologacion'  # ¡IMPORTANTE: Empezar con homologación!
    )
    
    try:
        # Probar con tu CUIT
        tipos = client.obtener_tipos_comprobante("TU_CUIT")
        
        if tipos:
            print("🎉 ¡AUTORIZACIÓN WSFEXv1 CONFIRMADA!")
            print(f"📋 Tipos disponibles: {len(tipos)}")
            return True
        else:
            print("❌ Sin autorización aún")
            return False
            
    except Exception as e:
        if "500" in str(e):
            print("❌ Aún sin autorización (error 500)")
        else:
            print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    probar_autorizacion()
```

### 🚀 **Solicitar Producción:**
Una vez que funcione en **homologación**, solicitar acceso a **producción** siguiendo el mismo proceso.

---

## 🔧 **PASO 8: Buscar la Factura Específica**

### ✅ **Una vez autorizado en producción:**

```python
# Usar la búsqueda híbrida que ya implementamos
from busqueda_hibrida_wsfev1_wsfexv1 import buscar_factura_especifica_hibrida

# Buscar la factura problemática
resultado = buscar_factura_especifica_hibrida(
    cuit="27312238018", 
    punto_venta=2, 
    numero=235
)

if resultado:
    print("🎉 ¡FACTURA ENCONTRADA!")
    print(f"Servicio: {resultado['servicio_origen']}")
    print(f"CAE: {resultado.get('CAE', 'N/A')}")
else:
    print("❌ Aún no encontrada - puede estar en WSMTXCA")
```

---

## 📞 **PASO 9: Soporte y Contactos**

### 🆘 **Si tenés problemas:**

```
📞 SOPORTE TÉCNICO AFIP:
├── 🌐 Web: https://www.afip.gob.ar/ws/
├── 📧 Email: webservice@afip.gob.ar
├── 📱 Tel: 0800-999-AFIP (2347)
├── 🕒 Horarios: Lunes a Viernes 8-20hs
└── 💬 Chat: Disponible en Mi AFIP

🔍 PROBLEMAS COMUNES:
├── ⏰ Demora > 15 días → Contactar soporte
├── ❌ Rechazo → Revisar justificación técnica
├── 🔒 Error de certificado → Usar el mismo de WSFEv1
└── 📧 Sin respuesta → Verificar email en formulario
```

---

## 📊 **RESUMEN EJECUTIVO**

### ✅ **Checklist de acciones:**
- [ ] 1️⃣ Verificar Clave Fiscal Nivel 3
- [ ] 2️⃣ Acceder a Mi AFIP → Web Services
- [ ] 3️⃣ Buscar "WSFEXv1" en servicios disponibles
- [ ] 4️⃣ Completar formulario con datos técnicos
- [ ] 5️⃣ Esperar aprobación (1-10 días)
- [ ] 6️⃣ Probar en homologación
- [ ] 7️⃣ Solicitar producción
- [ ] 8️⃣ ¡Buscar la factura 0002-00000235!

### 🎯 **Tiempo estimado total:**
**2-3 semanas** (considerando tiempos de AFIP y pruebas)

### 💡 **Resultado esperado:**
Una vez completado este proceso, tu **extractor completo de facturas** podrá acceder a:
- ✅ **WSFEv1**: Facturas A, B, C tradicionales
- ✅ **WSFEXv1**: Facturas M (monotributo) y de exportación
- 🎯 **Cobertura completa** de todos los tipos de comprobantes

---

**¡Con esta autorización, tu sistema será 100% completo para consultar cualquier factura de AFIP!** 🚀