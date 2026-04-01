# Certificado Producción AFIP - Verificación y Regeneración

## 1. Verificar que estamos en producción
El log al inicializar `ARCAServiceSimple` debe mostrar:
```
[ARCAServiceSimple] Modo=PRODUCCION | WSAA=https://wsaa.afip.gov.ar/ws/services/LoginCms | WSFE=https://servicios1.afip.gov.ar/wsfev1/service.asmx
```
Si aparece `wsaahomo` o `wswhomo` en producción => error de configuración.

## 2. Instalar OpenSSL en Windows (si querés ver detalles completos)
Descargar (Light version): https://slproweb.com/products/Win32OpenSSL.html
Durante instalación: marcar "Add OpenSSL to the system PATH".

Luego verificar:
```
openssl version
```

## 3. Ver detalles del certificado
```
openssl x509 -in certs/certificado.crt -noout -text | more
```
Datos clave:
- `Subject: ... serialNumber=CUIT 20321518045`  (Debe incluir CUIT correcto)
- `Issuer:` (Debe corresponder a CA de producción, no contener `homo` ni `test`)
- `Public-Key: (2048 bit)`
- Vigencia: fechas correctas.

## 4. Regenerar certificado (si CMS no válido persiste)
### 4.1 Generar clave privada
```
openssl genrsa -out clave_privada.key 2048
```
### 4.2 Generar CSR
```
openssl req -new -key clave_privada.key -out pedido.csr -subj "/CN=albano/serialNumber=CUIT 20321518045"
```
(Opcional agregar: `/O=AFIP/OU=Servicios Web`)

### 4.3 Subir CSR
En AFIP > Administrador > "Administración de Certificados Digitales" > Seleccionar representación correcta > "Agregar Certificado" > Pegar contenido de `pedido.csr`.

### 4.4 Descargar certificado emitido
Guardar como `certificado.crt` reemplazando el anterior en `certs/`.

### 4.5 Probar autenticación
Iniciar app y observar:
```
AUTENTICACION WSAA EXITOSA!
```
Si aparece `cms.bad` => certificado o CSR incorrecto.

## 5. Checklist rápido si sigue fallando CMS
| Ítem | Debe ser | OK |
|------|----------|----|
| Subject tiene CUIT correcto | serialNumber=CUIT 20321518045 | |
| Fechas vigencia vigentes | >= hoy | |
| Public-Key 2048 bit | Sí | |
| Se usa WSAA producción | wsaa.afip.gov.ar | |
| El archivo clave coincide con cert | Sí | |
| Permisos delegación (si aplica) | Asignados | |

## 6. Script Python simple para validar par clave/cert
Correr dentro del venv (requiere `openssl` CLI):
```
openssl rsa -in certs/clave_privada.key -modulus -noout > key.mod
openssl x509 -in certs/certificado.crt -modulus -noout > cert.mod
fc cert.mod key.mod
```
La comparación debe decir que son iguales.

## 7. Notas
- El mensaje `cms.bad` casi siempre es: (a) certificado no emitido para ese CUIT/servicio, (b) CSR mal formado, (c) se mezcló clave privada distinta, (d) se usa cert de homologación contra URL producción.
- La app ahora tiene una guardia que lanzará error si accidentalmente intenta usar URLs homo en producción.

## 8. Próximo paso
Si tras regenerar sigue `cms.bad`, abrir ticket AFIP adjuntando: TRA sin firmar, CMS firmado, y hora exacta del intento.
