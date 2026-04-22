# Guia de Delegacion de Servicios ARCA para InfoFiscal

## Introduccion

InfoFiscal consulta los comprobantes emitidos por cada cliente a traves de dos vias:

1. **Web Services AFIP** (WSFEv1, WSMTXCA, WSFEXv1): consulta automatica mediante certificado digital. Cubre puntos de venta del tipo "Factura Electronica - Web Services".

2. **Portal RCEL** (Comprobantes en Linea): consulta via navegacion automatizada del portal ARCA. Cubre puntos de venta del tipo "Factura en Linea" y "Factuweb", que **no** son accesibles por Web Services.

Para que ambas vias funcionen, es necesario que cada cliente delegue ciertos servicios al contador en ARCA.

---

## Servicios que debe delegar el cliente

### 1. Web Service de Facturacion Electronica (WSFEv1)

- **Nombre en ARCA**: `Web Service Comprobantes T` o `Facturacion Electronica`
- **Para que sirve**: Permite consultar comprobantes emitidos desde puntos de venta tipo "Factura Electronica - Web Services"
- **Necesario para**: Clientes que emiten facturas via sistemas de facturacion (software contable, ERP, etc.)

### 2. Comprobantes en Linea (RCEL)

- **Nombre en ARCA**: `Comprobantes en linea`
- **Para que sirve**: Permite al contador acceder al portal de comprobantes del cliente y ver las facturas emitidas desde "Factura en Linea"
- **Necesario para**: Clientes que emiten facturas desde el portal web de ARCA (monotributistas, profesionales, etc.)

### 3. Factura Electronica de Exportacion (WSFEXv1) — Opcional

- **Nombre en ARCA**: `Factura electronica de exportacion`
- **Para que sirve**: Consultar comprobantes de exportacion (Factura E)
- **Necesario para**: Clientes que realizan exportaciones de bienes o servicios

### 4. Factura Electronica con Detalle - MTXCA (WSMTXCA) — Opcional

- **Nombre en ARCA**: `Factura Electronica con Detalle - MTXCA`
- **Para que sirve**: Consultar comprobantes con detalle de items (tipo ticket)
- **Necesario para**: Clientes que usan facturacion con detalle de productos

---

## Como delegar los servicios (lo hace el cliente)

### Paso 1 — Ingresar a ARCA con Clave Fiscal

El cliente debe ingresar a [https://auth.afip.gob.ar/contribuyente_/login.xhtml](https://auth.afip.gob.ar/contribuyente_/login.xhtml) con su CUIT y Clave Fiscal.

### Paso 2 — Ir al Administrador de Relaciones

Desde el portal de servicios, buscar e ingresar a **"Administrador de Relaciones de Clave Fiscal"**.

### Paso 3 — Nueva Relacion

1. Click en **"Nueva Relacion"**
2. Seleccionar el servicio a delegar (ver lista arriba)
3. Ingresar el CUIT del contador como **Representante**
4. Confirmar la delegacion

### Paso 4 — Aceptacion por parte del contador

Una vez que el cliente genera la relacion:

1. El contador ingresa a ARCA con su propia Clave Fiscal
2. Va a **"Administrador de Relaciones de Clave Fiscal"**
3. Click en **"Consultar"**
4. Busca la relacion pendiente del cliente
5. Click en **"Pendiente"** para aceptar la relacion

---

## Tipos de Punto de Venta y servicios requeridos

| Tipo de Punto de Venta | Servicio requerido | Via de consulta |
|---|---|---|
| Factura Electronica - Web Services | Web Service Comprobantes T | WSFEv1 (automatico) |
| Factura en Linea - Monotributo | Comprobantes en linea | RCEL (portal web) |
| Factura en Linea - Regimen General | Comprobantes en linea | RCEL (portal web) |
| Factuweb (Imprenta) | Comprobantes en linea | RCEL (portal web) |
| Factura Electronica Exportacion | Factura electronica de exportacion | WSFEXv1 (automatico) |
| Factura con Detalle (MTXCA) | Factura Electronica con Detalle | WSMTXCA (automatico) |

---

## Como saber que tipo de punto de venta tiene un cliente

1. Ingresar a ARCA como el cliente (o como representante si ya tiene delegacion)
2. Ir a **"Punto de Venta / Emision"** (PVE) en el menu de servicios
3. La columna **"Sistema"** indica el tipo:
   - `Factuweb (Imprenta) - Monotributo` → necesita RCEL
   - `Factura en Linea - Monotributo` → necesita RCEL
   - `RECE/Web Services` → necesita Web Service Comprobantes T

---

## Delegacion minima recomendada

Para que InfoFiscal pueda consultar **todos** los comprobantes de un cliente, se recomienda delegar al menos:

1. **Comprobantes en linea** — cubre Factura en Linea y Factuweb
2. **Web Service Comprobantes T** — cubre facturacion electronica via Web Services
3. **Facturacion Electronica** — necesario para el certificado digital

Con estos tres servicios delegados, InfoFiscal consultara automaticamente todas las fuentes disponibles y unificara los resultados.

---

## Notas importantes

- La delegacion la debe hacer el **cliente** desde su cuenta de ARCA. El contador no puede auto-delegarse.
- El contador debe **aceptar** cada delegacion desde su propia cuenta.
- Si un cliente solo tiene puntos de venta "Factura en Linea" y no delega "Comprobantes en linea", InfoFiscal no podra obtener sus comprobantes.
- Las delegaciones son permanentes hasta que alguna de las partes las revoque.
- InfoFiscal utiliza las credenciales del portal ARCA del contador (configuradas en el sistema) para acceder a RCEL. El contador ingresa sus credenciales una sola vez en la configuracion.
