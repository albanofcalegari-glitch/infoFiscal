r"""Script de diagnóstico WSAA / WSFE para AFIP.

Uso (PowerShell):

    Set-Location "C:\Users\DELL\Desktop\proyectos python\infofiscal"
    $env:INFOFISCAL_MODE = 'production'
    $env:AFIP_DEBUG_WSAA = '1'
    python .\src\diagnostico_wsaa.py -cuit 20321518045 -cert certs/certificado.crt -key certs/clave_privada.key

rEste script:
 1. Verifica existencia de certificado y clave
 2. Intenta localizar OpenSSL
 3. Genera TRA y lo guarda (debug_wsaa/TRA.xml)
 4. Firma TRA y guarda CMS base64
 5. Realiza loginCms (WSAA)
 6. Muestra token/sign o errores (last_error_code / last_error_detail)
 7. Opcional: hace FECompUltimoAutorizado si WSAA éxito
"""

from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, 'src')  # aseguramos import local

from arca_service_simple import ARCAServiceSimple  # type: ignore


def encontrar_openssl() -> str | None:
    posibles = [
        "C:/Program Files/Git/usr/bin/openssl.exe",
        "openssl.exe",
        "openssl"
    ]
    for p in posibles:
        try:
            from subprocess import run
            r = run([p, 'version'], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                return p
        except Exception:
            continue
    return None


def diagnostico(cuit: str, cert_path: Path, key_path: Path, probar_wsfe: bool = True):
    print("========== DIAGNOSTICO WSAA/WSFE ==========")
    print(f"Hora local: {datetime.now().isoformat()}")
    print(f"CUIT autenticado: {cuit}")
    print(f"Cert: {cert_path} | Key: {key_path}")
    print(f"AFIP_DEBUG_WSAA={os.environ.get('AFIP_DEBUG_WSAA')}")

    # Info de certificado (fechas / subject) usando openssl si disponible
    try:
        openssl = encontrar_openssl()
        if openssl:
            from subprocess import run
            info = run([openssl, 'x509', '-in', str(cert_path), '-noout', '-dates', '-subject', '-issuer'], capture_output=True, text=True, timeout=10)
            if info.returncode == 0:
                print('[CERT] Info:')
                for line in info.stdout.strip().splitlines():
                    print('   ' + line)
    except Exception as e:
        print(f"[WARN] No se pudo extraer info de certificado: {e}")

    # 1. Archivos
    if not cert_path.exists():
        print("[FATAL] No existe certificado")
        return
    if not key_path.exists():
        print("[FATAL] No existe clave privada")
        return
    print("[OK] Archivos de certificado y clave presentes")

    # 2. OpenSSL
    openssl = encontrar_openssl()
    if not openssl:
        print("[FATAL] No se encontró OpenSSL en PATH ni Git. Instalar Git o OpenSSL")
        return
    print(f"[OK] OpenSSL detectado: {openssl}")

    # 3. Instanciar servicio (esto imprime debug)
    svc = ARCAServiceSimple(cuit=cuit, cert_path=str(cert_path), key_path=str(key_path), testing=False)

    # 4. Generar y firmar TRA directamente
    print("[STEP] Generando TRA...")
    tra_xml = svc._generate_tra()
    print(f"[INFO] TRA length: {len(tra_xml)} chars")
    print("[STEP] Firmando TRA (smime)...")
    try:
        cms = svc._sign_tra_openssl(tra_xml)
        print(f"[OK] CMS firmado bytes={len(cms)}")
    except Exception as e:
        print(f"[FATAL] Error firmando TRA: {e}")
        return

    # 5. Autenticación WSAA
    print("[STEP] Autenticando WSAA...")
    if svc.authenticate_wsaa():
        print("[SUCCESS] WSAA OK. Token y Sign disponibles.")
        print(f"Token (10 primeros): {svc.token[:10]}...")
        if probar_wsfe:
            print("[STEP] Obteniendo último comprobante autorizado (pto 1 tipo 1)...")
            ultimo = svc.wsfe_fecomp_ultimo_autorizado(pto_vta=1, cbte_tipo=1)
            if ultimo is None:
                print("[WARN] No se pudo obtener último comprobante (delegación / permisos / inexistente).")
            else:
                print(f"[OK] Último comprobante: {ultimo}")
            print("[STEP] Enumerando últimos comprobantes básicos (tipos 1,6,11,13; max 2 por tipo)...")
            enum = svc.wsfe_enumerar_ultimos(max_por_tipo=2)
            print("[ENUM] Resumen (truncado 1800 chars):")
            import json as _json
            print(_json.dumps(enum, indent=2, ensure_ascii=False)[:1800])
    else:
        print("[ERROR] WSAA FALLÓ")
        print(f"last_error_code = {svc.last_error_code}")
        if svc.last_error_detail:
            print("---- detalle (truncado) ----")
            print(svc.last_error_detail[:800])
            print("----------------------------")
        print("Revisar: 1) Cert vinculado a CUIT, 2) Delegación WSFE, 3) Vigencia, 4) Modulus clave-cert, 5) Service=wsfe en TRA, 6) Hora del sistema.")

    print("Artefactos debug (si debug activo) en carpeta: debug_wsaa")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-cuit', required=True, help='CUIT autenticado (el del certificado)')
    parser.add_argument('-cert', default='certs/certificado.crt')
    parser.add_argument('-key', default='certs/clave_privada.key')
    parser.add_argument('--no-wsfe', action='store_true', help='No intentar paso WSFE')
    args = parser.parse_args()

    diagnostico(
        cuit=args.cuit,
        cert_path=Path(args.cert),
        key_path=Path(args.key),
        probar_wsfe=not args.no_wsfe
    )
