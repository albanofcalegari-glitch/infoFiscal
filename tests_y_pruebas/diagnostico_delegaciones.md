# Diagnóstico: Delegaciones AFIP - CUIT 27312238018

## Estado Actual

✅ **Delegaciones creadas:**
- `20321518045-27312238018-ws://wsfe-27312238018` → YA EXISTE
- `20321518045-27312238018-ws://wsmtxca-27312238018` → YA EXISTE

❌ **Problema:**
```
Error Code 600: ValidacionDeToken: No aparecio CUIT en lista de relaciones: 27312238018
```

**Conclusión:** Las delegaciones existen en AFIP pero NO están activas o NO tienen los permisos correctos.

---

## Checklist de Verificación

### 1. Ingresar a AFIP como 27312238018 (Regina)

- URL: https://auth.afip.gob.ar
- Usuario: CUIT 27312238018
- Ir a: **Administrador de Relaciones**

### 2. Ver "Mis Representantes"

Buscar si aparece **CUIT: 20321518045** en la lista.

**¿Aparece?**
- ❌ **NO:** Hay un problema grave, las delegaciones no se guardaron correctamente
- ✅ **SÍ:** Continuar con verificación

### 3. Verificar ESTADO de la relación

Para el CUIT 20321518045, verificar:

| Campo | Valor Esperado | ✓ |
|-------|----------------|---|
| Estado | **ACTIVO** (no Pendiente, no Inactivo) | ☐ |
| Fecha Desde | Fecha pasada o actual | ☐ |
| Fecha Hasta | Fecha futura (ej: 2026) | ☐ |

### 4. Verificar SERVICIOS delegados

Hacer clic en la relación para ver detalle:

#### Servicio 1: Facturación Electrónica (WSFE)

| Campo | Valor Esperado | ✓ |
|-------|----------------|---|
| Servicio | Facturación Electrónica | ☐ |
| Alias/Código | wsfe o wsfev1 | ☐ |
| Permiso CONSULTA | ✅ Habilitado | ☐ |
| Permiso PRESENTACION | ✅ Habilitado | ☐ |
| Estado | ACTIVO | ☐ |

#### Servicio 2: MTXCA (si corresponde)

| Campo | Valor Esperado | ✓ |
|-------|----------------|---|
| Servicio | Factura Electrónica con Detalle - MTXCA | ☐ |
| Alias/Código | wsmtxca | ☐ |
| Permiso CONSULTA | ✅ Habilitado | ☐ |
| Permiso PRESENTACION | ✅ Habilitado | ☐ |
| Estado | ACTIVO | ☐ |

---

## Problemas Comunes y Soluciones

### Problema 1: Relación en estado "Pendiente"

**Causa:** La relación fue creada pero nunca se activó.

**Solución:**
1. Hacer clic en la relación
2. Buscar botón "Activar" o "Aprobar"
3. Confirmar activación

### Problema 2: Falta permiso de CONSULTA

**Causa:** Solo se delegó "Presentación" (emisión) pero no "Consulta".

**Solución:**
1. Modificar la relación
2. Marcar checkbox: ✅ **Consulta**
3. Guardar cambios
4. **Esperar 15-30 minutos** para sincronización

### Problema 3: Servicio mal especificado

**Causa:** Se delegó un servicio genérico pero no el servicio específico de web services.

**Solución:**
1. Eliminar relación actual
2. Crear nueva relación
3. Seleccionar EXACTAMENTE:
   - "Facturación Electrónica" (para wsfe)
   - "Factura Electrónica con Detalle - MTXCA" (para wsmtxca)

### Problema 4: Sincronización pendiente

**Causa:** AFIP puede tardar hasta 30 minutos en sincronizar cambios.

**Solución:**
- Esperar 15-30 minutos después de cualquier cambio
- No hacer múltiples cambios seguidos
- Verificar después de espera

---

## Acción Recomendada

### Opción 1: Revisar y Corregir (Más Rápido)

1. Ver estado actual de la relación
2. Si está "Pendiente" → Activar
3. Si falta permiso "Consulta" → Agregar
4. Esperar 30 minutos
5. Probar: `python test_facturas_regina_debug.py`

### Opción 2: Eliminar y Recrear (Más Seguro)

1. **Eliminar** la relación con CUIT 20321518045
2. **Esperar 10 minutos**
3. **Crear nueva** relación:
   - Representante: 20321518045
   - Tipo: Representante/Apoderado
   - Servicios:
     - ✅ Facturación Electrónica
     - ✅ Factura Electrónica con Detalle - MTXCA
   - Permisos PARA CADA SERVICIO:
     - ✅ Consulta
     - ✅ Presentación
   - Vigencia: Desde hoy hasta 31/12/2026
4. **Activar** la relación (si queda pendiente)
5. **Esperar 30 minutos**
6. **Probar** de nuevo

---

## Verificación Post-Corrección

Ejecutar script de prueba:
```bash
python test_facturas_regina_debug.py
```

**Resultado esperado:**
```
[1] Autenticando con WSAA...
    ✓ Autenticación exitosa

[2] Consultando último autorizado PV 0002...
    Último: 238  # ← Debería ser > 0

[3] Consultando facturas específicas...
    --- Factura 0002-00000235 ---
    ✓ ENCONTRADO
       CAE: 75398005844240
       Fecha: 20250930
       Importe: $150000
```

**Si sigue fallando con Error 600:**
→ La delegación AÚN no está correcta o no se sincronizó.

---

## Contacto Soporte AFIP

Si después de seguir todos los pasos sigue sin funcionar:

**Email:** mayuda@afip.gov.ar
**Asunto:** Problema con delegación de servicios web
**Ticket:** 44644838 o 44644848
**Descripción:**
```
Estimados,

Tengo un problema con la delegación de servicios web.

CUIT Representado: 27312238018
CUIT Representante: 20321518045
Servicio: Facturación Electrónica (wsfe/wsfev1)

Al consultar comprobantes, recibo el error:
"Code 600: ValidacionDeToken: No aparecio CUIT en lista de relaciones"

Sin embargo, al intentar crear la delegación, dice que ya existe.

¿Podrían verificar el estado de la delegación?

Gracias.
```

---

## Notas Técnicas

- El error "ya existe" es DIFERENTE al error "no autorizado"
- "Ya existe" = la delegación está registrada en BD de AFIP
- Error 600 = la delegación NO está activa en el servicio web
- Hay 2 sistemas: uno para administrar relaciones, otro para validar web services
- La sincronización entre ambos puede tardar hasta 30 minutos
