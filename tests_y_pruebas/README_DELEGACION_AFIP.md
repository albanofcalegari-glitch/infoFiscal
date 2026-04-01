# Guía: Delegación de Permisos AFIP para Consulta de Facturas

## Problema Detectado

```
Error AFIP Code 600: ValidacionDeToken: No aparecio CUIT en lista de relaciones: 27312238018
```

**Significado:** El CUIT 27312238018 no aparece correctamente en la lista de relaciones del CUIT 20321518045.

---

## Solución: Configurar Delegación Correctamente

### Paso 1: Ingresar como el CLIENTE (27312238018 - Regina Cereto)

1. Ir a https://auth.afip.gob.ar
2. Ingresar con **CUIT: 27312238018** y Clave Fiscal
3. Ir a **"Administrador de Relaciones"**

### Paso 2: Verificar Delegaciones Existentes

1. Clic en **"Administrador de Relaciones de Recursos"**
2. Ver sección **"Mis Representantes"**
3. Buscar si aparece el CUIT **20321518045**

### Paso 3A: Si NO aparece la delegación

1. Clic en **"Nueva Relación"**
2. Tipo de relación: **"Representante"**
3. CUIT del representante: **20321518045**
4. Servicios a delegar:
   - ✅ **Facturación Electrónica** (wsfe/wsfev1)
   - ✅ **Factura Electrónica con Detalle - MTXCA** (si es monotributo)
   - ✅ Marcar: **Consulta** y **Emisión**
5. Fecha de vigencia: Desde hoy hasta fecha futura (ej: 1 año)
6. Guardar

### Paso 3B: Si YA aparece la delegación

1. Seleccionar la relación con CUIT 20321518045
2. Clic en **"Modificar"** o **"Ver Detalle"**
3. Verificar que incluya:
   - ✅ Servicio: **"Facturación Electrónica"**
   - ✅ Permisos: **Consulta** (no solo Emisión)
   - ✅ Estado: **Activa** (no vencida ni suspendida)
4. Si falta algo, **modificar** la relación o **eliminar y crear nueva**

### Paso 3C: Si da error "ya existe"

El error `La autorizacion: 20321518045-27312238018-ws://wsfe-27312238018 ya existe` indica:

1. **Opción A - Esperar:** A veces AFIP tarda en sincronizar (esperar 15-30 minutos)
2. **Opción B - Eliminar y recrear:**
   - Buscar la relación existente
   - Eliminarla completamente
   - Esperar 5 minutos
   - Crear nueva relación

---

## Servicios Específicos Necesarios

Según el screenshot de AFIP, los nombres exactos son:

| Servicio | Para qué sirve |
|----------|---------------|
| **Facturación Electrónica** | Facturas A, B, C tradicionales (WSFEv1) |
| **Factura Electrónica con Detalle - MTXCA** | Monotributo con codificación |
| **Factura electronica de exportacion** | Facturas de exportación (WSFEX) |

**Para Regina (Monotributo):** Necesitás delegar **"Facturación Electrónica"** como mínimo.

---

## Verificación Post-Delegación

Después de configurar la delegación, esperar **15-30 minutos** para que AFIP sincronice.

Luego ejecutar:
```bash
python test_facturas_regina_debug.py
```

Si todo está bien, deberías ver:
- ✅ Autenticación exitosa
- ✅ Facturas encontradas (no error 600)

---

## Preguntas Frecuentes

**Q: ¿Por qué no puedo consultar facturas de mi cliente?**
A: Necesitás que el cliente te delegue permisos en "Administrador de Relaciones".

**Q: ¿La delegación es para todos los servicios?**
A: No. Cada servicio (wsfe, wsmtxca, wsfex) se delega por separado.

**Q: ¿Puedo consultar facturas sin delegación?**
A: Solo podés consultar tus propias facturas. Para clientes, necesitás delegación.

**Q: ¿La delegación expira?**
A: Sí, tiene fecha de vencimiento. Debe renovarse periódicamente.

---

## Contacto Soporte AFIP

Si seguís teniendo problemas:
- Email: mayuda@afip.gov.ar
- Mencionar: Número de Ticket del error
- Describir: "Problema con delegación de servicios web para consulta de facturas"
