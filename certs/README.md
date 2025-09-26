# Instrucciones para configurar certificados AFIP/ARCA

## 1. Generar clave privada
openssl genrsa -out clave_privada.key 2048

## 2. Generar CSR (Certificate Signing Request)
openssl req -new -key clave_privada.key -out solicitud.csr

## Al generar el CSR, completar:
# - Country Name: AR
# - State: [Tu provincia]
# - City: [Tu ciudad]  
# - Organization Name: [Razón social]
# - Organizational Unit: [Opcional]
# - Common Name: [CUIT SIN GUIONES] ← MUY IMPORTANTE
# - Email: [Tu email]
# - Challenge password: [Dejar vacío]

## 3. Subir el CSR a AFIP
# - Ingresar a AFIP con Clave Fiscal
# - Ir a "Administración de Certificados Digitales"
# - Subir el archivo solicitud.csr
# - AFIP generará el certificado.crt

## 4. Descargar y colocar archivos
# - Guardar certificado.crt en carpeta certs/
# - Guardar clave_privada.key en carpeta certs/
# - Verificar permisos de archivos (solo lectura para el usuario)

## 5. Habilitar servicios web en AFIP
### PASO A PASO DETALLADO:
1. **Ingresar a AFIP** con tu CUIT y Clave Fiscal
2. **Buscar "Administrador de Relaciones"** en el menú principal
3. **Seleccionar tu CUIT** como contribuyente
4. **Hacer clic en "Nueva Relación"**
5. **Buscar estos servicios (pueden tener nombres similares):**
   
   **NOMBRES POSIBLES PARA FACTURA ELECTRÓNICA:**
   - "Factura Electrónica" o "FE"
   - "Web Service Factura Electrónica" 
   - "WSFE" o "wsfe"
   - "Servicio Web de Facturación"
   - "Comprobantes Electrónicos"
   
   **OTROS SERVICIOS ÚTILES:**
   - "Monotributo" o "wsmtx" - Si corresponde
   - "Padrón de Contribuyentes" - Opcional
   
   **SI NO ENCONTRÁS NINGUNO:**
   - Busca servicios que contengan "factura" o "electrónica"
   - Pregunta en AFIP por "servicios web para desarrolladores"
6. **Asociar el certificado** que descargaste a cada servicio
7. **Esperar activación** (puede tomar algunas horas)

### VERIFICAR HABILITACIÓN:
- Los servicios deben aparecer como "ACTIVO" en tu panel
- El certificado debe estar asociado y válido

## NOTA: Los archivos de certificados NO están incluidos por seguridad
## Debes generarlos y colocarlos manualmente en la carpeta certs/