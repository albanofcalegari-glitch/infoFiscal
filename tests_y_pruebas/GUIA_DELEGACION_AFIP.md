# 🏛️ GUÍA COMPLETA: DELEGACIÓN AFIP PARA CONSULTA DE FACTURAS

## 📋 PASO 1: IDENTIFICAR QUÉ NECESITAS

### Para consultar facturas de otro CUIT necesitas:
- **Tu CUIT**: 20321518045 (el que consulta)
- **CUIT Cliente**: El que emite las facturas que quieres consultar
- **Servicio AFIP**: WSFEv1 (Facturación Electrónica)

---

## 👨‍💼 PASO 2: EL CLIENTE DEBE DELEGARTE PERMISOS

### 🔐 El TITULAR del CUIT (cliente) debe:

1. **Ingresar a AFIP con su Clave Fiscal**
   - Sitio: [https://auth.afip.gob.ar/contribuyente_/login.xhtml](https://auth.afip.gob.ar/contribuyente_/login.xhtml)

2. **Ir al Administrador de Relaciones**
   ```
   AFIP → Administrador de Relaciones de Clave Fiscal
   ```

3. **Seleccionar "Adherir Servicios"**

4. **Buscar el servicio de facturación**
   - Buscar: "Facturación Electrónica"
   - Seleccionar: **"Facturación Electrónica - Web Service"**

5. **Agregar tu CUIT como delegado**
   - CUIT Representante: **20321518045**
   - Tipo de Relación: **"Representante"** o **"Consultor"**

---

## 🔄 ALTERNATIVA: REPRESENTACIÓN FISCAL COMPLETA

### Si manejas completamente la contabilidad del cliente:

1. **El cliente va a**:
   ```
   AFIP → Administrador de Relaciones → Representantes
   ```

2. **Agrega tu CUIT como Representante Fiscal**
   - CUIT: **20321518045**
   - Tipo: **Representante**
   - Servicios: **Todos** o **Facturación Electrónica**

---

## 📞 PASO 3: VERIFICACIÓN

### Una vez delegado, verificar en:

1. **Tu AFIP** (CUIT 20321518045):
   ```
   AFIP → Mis Representados → Ver Representados
   ```
   
2. **Debería aparecer**:
   - El CUIT del cliente
   - Servicios disponibles: "Facturación Electrónica"

---

## 🛠️ PASO 4: CONFIGURACIÓN EN TU SISTEMA

### Una vez delegado, actualizar tu script:

```python
# En lugar de usar siempre tu CUIT:
cuit_consultor = "20321518045"  # Tu CUIT
cuit_representado = "30123456789"  # CUIT del cliente

# El sistema automáticamente consultará las facturas del cliente
```

---

## ⚠️ PROBLEMAS COMUNES

### ❌ "No autorizado"
- **Causa**: No hay delegación activa
- **Solución**: Verificar delegación en AFIP

### ❌ "Servicio no adherido"
- **Causa**: El cliente no tiene facturación electrónica
- **Solución**: Cliente debe adherirse a WSFEv1

### ❌ "CUIT no encontrado"
- **Causa**: CUIT mal ingresado o inexistente
- **Solución**: Verificar número de CUIT

---

## 🎯 RESUMEN RÁPIDO

| Quien | Qué hace | Dónde |
|-------|----------|-------|
| **Cliente** | Delega permisos a tu CUIT | Su AFIP → Administrador Relaciones |
| **Tú** | Verificas delegación | Tu AFIP → Mis Representados |
| **Sistema** | Consulta automáticamente | WSFEv1 con CUIT delegado |

---

## 📱 CONTACTO AFIP

Si hay problemas:
- **Teléfono**: 0810-999-2347
- **Web**: [www.afip.gob.ar](https://www.afip.gob.ar)
- **Horario**: Lunes a Viernes 8-20hs

---

## ✅ VERIFICACIÓN FINAL

Una vez completada la delegación, ejecutar:
```bash
python test_cuit_especifico.py
```

El sistema debería mostrar las facturas del cliente delegado.