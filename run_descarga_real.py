import os, sys, json
os.environ['INFOFISCAL_MODE'] = 'production'
os.environ['AFIP_DEBUG_WSAA'] = '1'
sys.path.insert(0, 'src')

from arca_service_simple import descargar_facturas_arca_simple

CUIT_OBJETIVO = '23333730219'   # Ajustar si corresponde
CUIT_CONSULTOR = '20321518045'

print("=== DESCARGA REAL WSFE ===")
print(f"Objetivo: {CUIT_OBJETIVO} | Consultor: {CUIT_CONSULTOR}")

res = descargar_facturas_arca_simple(
    cuit=CUIT_OBJETIVO,
    output_dir=f'facturas/{CUIT_OBJETIVO}',
    modo_real=True,
    consultar_como=CUIT_CONSULTOR
)

print("=== RESULTADO ===")
print(json.dumps(res, indent=2, ensure_ascii=False))
