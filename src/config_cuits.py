# Configuración de CUITs autorizados para consulta

CUITS_AUTORIZADOS = {
    "20321518045": {
        "nombre": "CALEGARI ALBANO FEDERICO",
        "tipo": "propio",
        "servicios": ["facturacion_electronica"]
    },
    "23333730219": {  # Sin guiones para uso en sistema
        "nombre": "VEGA MARTIN MATIAS", 
        "tipo": "delegado",
        "servicios": ["facturacion_electronica"],
        "autorizante": "23-33373021-9",
        "fecha_autorizacion": "2025-09-25"
    }
}

# Función para obtener CUIT sin guiones
def limpiar_cuit(cuit):
    """Remover guiones del CUIT"""
    return cuit.replace("-", "")

# Función para formatear CUIT con guiones
def formatear_cuit(cuit):
    """Agregar guiones al CUIT"""
    if len(cuit) == 11:
        return f"{cuit[:2]}-{cuit[2:10]}-{cuit[10]}"
    return cuit