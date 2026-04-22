#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test aislado de WSFEv1 para CUIT real.
Verifica conectividad WSAA + consulta de comprobantes sin pasar por la app web.

Uso:
    python scripts/test_wsfev1_cuit.py
    python scripts/test_wsfev1_cuit.py --cuit 20321518045
    python scripts/test_wsfev1_cuit.py --cuit 20321518045 --limite 3
"""

import sys
import time
import argparse
from pathlib import Path

# Agregar raiz del proyecto al path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from wsfev1_client import WSFEv1Client


# ── Config ────────────────────────────────────────────────────────────────────

CUIT_DEFAULT = "20321518045"
CERT_PATH = ROOT_DIR / "certs" / "certificado.crt"
KEY_PATH = ROOT_DIR / "certs" / "clave_privada.key"

# Tipos mas comunes, en orden de frecuencia para este contribuyente
TIPOS_PRINCIPALES = [
    (11, "Factura C"),
    (6,  "Factura B"),
    (1,  "Factura A"),
    (51, "Factura M"),
]

TIPOS_SECUNDARIOS = [
    (2,  "ND A"),
    (3,  "NC A"),
    (7,  "ND B"),
    (8,  "NC B"),
    (12, "ND C"),
    (13, "NC C"),
    (15, "Rec C"),
    (52, "ND M"),
    (53, "NC M"),
    (4,  "Rec A"),
    (5,  "NVta A"),
    (9,  "Rec B"),
    (10, "NVta B"),
    (201, "FCE A"),
    (202, "ND FCE A"),
    (203, "NC FCE A"),
    (206, "FCE B"),
    (207, "ND FCE B"),
    (208, "NC FCE B"),
    (211, "FCE C"),
    (212, "ND FCE C"),
    (213, "NC FCE C"),
]


def separador(titulo=""):
    ancho = 70
    if titulo:
        print(f"\n{'=' * ancho}")
        print(f"  {titulo}")
        print(f"{'=' * ancho}")
    else:
        print(f"{'-' * ancho}")


def verificar_certificados():
    """Paso 0: verificar que los certificados existen."""
    separador("PASO 0: Verificar certificados")
    ok = True
    for label, path in [("Certificado", CERT_PATH), ("Clave privada", KEY_PATH)]:
        existe = path.exists()
        size = path.stat().st_size if existe else 0
        status = f"OK ({size:,} bytes)" if existe else "NO ENCONTRADO"
        print(f"  {label}: {path}")
        print(f"    -> {status}")
        if not existe:
            ok = False
    return ok


def crear_cliente():
    """Paso 1: instanciar WSFEv1Client."""
    separador("PASO 1: Crear cliente WSFEv1")
    client = WSFEv1Client(
        cert_path=str(CERT_PATH),
        key_path=str(KEY_PATH),
        ambiente='prod'
    )
    print(f"  URL WSAA: {client.urls['prod']['wsaa']}")
    print(f"  URL WSFE: {client.urls['prod']['wsfe']}")
    return client


def test_autenticacion(client, cuit):
    """Paso 2: autenticar contra WSAA y medir latencia."""
    separador("PASO 2: Autenticacion WSAA")
    print(f"  CUIT: {cuit}")
    print(f"  Enviando TRA a WSAA produccion...")

    t0 = time.time()
    token, sign = client.autenticar_wsaa(cuit)
    elapsed = time.time() - t0

    print(f"  Token: {token[:40]}...  ({len(token)} chars)")
    print(f"  Sign:  {sign[:40]}...  ({len(sign)} chars)")
    print(f"  Latencia WSAA: {elapsed:.2f}s")

    # Segunda llamada: debe venir de cache
    t0 = time.time()
    token2, _ = client.autenticar_wsaa(cuit)
    elapsed2 = time.time() - t0

    cached = "SI (cache)" if token == token2 and elapsed2 < 0.01 else "NO (nueva llamada)"
    print(f"  Cache tokens: {cached} ({elapsed2*1000:.1f}ms)")

    return True


def descubrir_puntos_venta(client, cuit):
    """Paso 3: descubrir TODOS los puntos de venta.

    Estrategia:
      1. Intentar FEParamGetPtosVenta (lista oficial de AFIP)
      2. Si falla o viene vacio, barrer PV 1..99 con FECompUltimoAutorizado
         usando tipo 11 (Factura C) como sonda — si ultimo > 0, el PV existe.
    """
    separador("PASO 3: Descubrir TODOS los puntos de venta")

    # Intento 1: API oficial
    pvs_api = client.obtener_puntos_venta(cuit)
    if pvs_api:
        # obtener_puntos_venta ya retorna lista de ints o lista de dicts
        pvs = []
        for item in pvs_api:
            if isinstance(item, dict):
                pvs.append(item.get('numero', item.get('Nro', 0)))
            else:
                pvs.append(int(item))
        pvs = sorted(set(p for p in pvs if p > 0))
        print(f"  FEParamGetPtosVenta: {len(pvs)} PV(s) -> {pvs}")
    else:
        pvs = []
        print("  FEParamGetPtosVenta: sin resultados (puede ser normal)")

    # Intento 2: barrido exhaustivo PV 1..99 con Factura C (tipo 11) como sonda
    print("  Barriendo PV 1..99 con FECompUltimoAutorizado (tipo 11)...")
    pvs_encontrados_barrido = []
    for pv_candidato in range(1, 100):
        try:
            ultimo = client.obtener_ultimo_comprobante(cuit, 11, pv_candidato)
            if ultimo is not None and ultimo > 0:
                pvs_encontrados_barrido.append(pv_candidato)
        except Exception:
            pass

    if pvs_encontrados_barrido:
        print(f"  Barrido tipo 11: PVs con facturas C -> {pvs_encontrados_barrido}")

    # Barrido secundario: tipos 1 (Factura A) y 6 (Factura B) para PVs que no aparecieron
    pvs_extra = set()
    for tipo_sonda in [1, 6, 51]:
        for pv_candidato in range(1, 100):
            if pv_candidato in pvs or pv_candidato in pvs_encontrados_barrido or pv_candidato in pvs_extra:
                continue
            try:
                ultimo = client.obtener_ultimo_comprobante(cuit, tipo_sonda, pv_candidato)
                if ultimo is not None and ultimo > 0:
                    pvs_extra.add(pv_candidato)
            except Exception:
                pass

    if pvs_extra:
        print(f"  Barrido tipos 1/6/51: PVs adicionales -> {sorted(pvs_extra)}")

    # Unificar todo
    todos = sorted(set(pvs) | set(pvs_encontrados_barrido) | pvs_extra)

    if not todos:
        print("  NINGÚN punto de venta encontrado. Usando [1] como fallback.")
        todos = [1]

    print(f"\n  TOTAL puntos de venta a consultar: {todos}")
    return todos


def escanear_ultimos(client, cuit, puntos_venta):
    """Paso 4: para cada tipo+PV, obtener ultimo autorizado."""
    separador("PASO 4: Ultimo comprobante autorizado por tipo/PV")

    mapa = {}  # (tipo, pv) -> ultimo
    todos_tipos = TIPOS_PRINCIPALES + TIPOS_SECUNDARIOS

    for tipo_id, tipo_desc in todos_tipos:
        for pv in puntos_venta:
            ultimo = client.obtener_ultimo_comprobante(cuit, tipo_id, pv)
            if ultimo and ultimo > 0:
                mapa[(tipo_id, pv)] = ultimo
                print(f"  Tipo {tipo_id:3d} ({tipo_desc:8s}) PV {pv}: ultimo #{ultimo}")

    if not mapa:
        print("  No se encontraron comprobantes autorizados en ningun tipo/PV")
    else:
        total = sum(mapa.values())
        print(f"\n  Resumen: {len(mapa)} combinaciones tipo/PV con comprobantes")
        print(f"  Total acumulado (sum ultimos): {total}")

    return mapa


def consultar_comprobantes(client, cuit, mapa, limite_por_combo):
    """Paso 5: consultar los ultimos N comprobantes de cada combo tipo/PV."""
    separador(f"PASO 5: Consultar comprobantes (max {limite_por_combo} por tipo/PV)")

    if not mapa:
        print("  Nada que consultar (no hay ultimos autorizados)")
        return []

    resultados = []
    errores = 0

    for (tipo_id, pv), ultimo in sorted(mapa.items()):
        tipo_desc = dict(TIPOS_PRINCIPALES + TIPOS_SECUNDARIOS).get(tipo_id, f"Tipo {tipo_id}")
        inicio = max(1, ultimo - limite_por_combo + 1)

        print(f"\n  --- Tipo {tipo_id} ({tipo_desc}) PV {pv} | #{inicio}..#{ultimo} ---")

        for num in range(ultimo, inicio - 1, -1):
            try:
                t0 = time.time()
                comp = client.consultar_comprobante(cuit, tipo_id, pv, num)
                elapsed = time.time() - t0

                if comp is not None:
                    resultados.append(comp)
                    # Mostrar datos clave
                    fecha = comp.get('CbteFch', comp.get('fecha_emision', '?'))
                    total = comp.get('ImpTotal', comp.get('importe_total', '?'))
                    cae = comp.get('CAE', comp.get('cae', '-'))
                    doc_nro = comp.get('DocNro', comp.get('receptor_nro_doc', '-'))

                    print(f"    #{num:08d}  Fecha:{fecha}  Total:${total:>12s}  CAE:{cae}  DocNro:{doc_nro}  ({elapsed:.2f}s)")
                else:
                    print(f"    #{num:08d}  (sin datos / no encontrado)")

            except Exception as e:
                errores += 1
                print(f"    #{num:08d}  ERROR: {e}")

    return resultados


def resumen_final(cuit, resultados, mapa):
    """Paso 6: resumen."""
    separador("RESUMEN FINAL")

    print(f"  CUIT consultado:           {cuit}")
    print(f"  Combos tipo/PV con datos:  {len(mapa)}")
    print(f"  Comprobantes consultados:   {len(resultados)}")

    if resultados:
        # Agrupar por tipo
        por_tipo = {}
        for r in resultados:
            tipo = r.get('CbteTipo', '?')
            por_tipo.setdefault(tipo, []).append(r)

        print(f"\n  Desglose por tipo de comprobante:")
        tipos_ref = dict(TIPOS_PRINCIPALES + TIPOS_SECUNDARIOS)
        for tipo, comps in sorted(por_tipo.items(), key=lambda x: str(x[0])):
            desc = tipos_ref.get(int(tipo), f"Tipo {tipo}") if tipo != '?' else "?"
            importes = []
            for c in comps:
                try:
                    importes.append(float(c.get('ImpTotal', c.get('importe_total', 0))))
                except (ValueError, TypeError):
                    pass
            total_imp = sum(importes)
            print(f"    Tipo {tipo:>3s} ({desc:8s}): {len(comps):3d} comprobantes  |  Importe total: ${total_imp:,.2f}")

        print(f"\n  RESULTADO: WSFEv1 FUNCIONA CORRECTAMENTE")
    else:
        print(f"\n  RESULTADO: No se obtuvieron comprobantes.")
        print(f"  Posibles causas:")
        print(f"    - El CUIT no tiene facturas electronicas emitidas")
        print(f"    - El certificado no tiene permisos para este CUIT")
        print(f"    - Problema de conectividad con AFIP")


def main():
    parser = argparse.ArgumentParser(description="Test aislado WSFEv1")
    parser.add_argument("--cuit", default=CUIT_DEFAULT, help=f"CUIT a consultar (default: {CUIT_DEFAULT})")
    parser.add_argument("--limite", type=int, default=3, help="Max comprobantes por tipo/PV (default: 3)")
    parser.add_argument("--solo-escaneo", action="store_true", help="Solo escanear ultimos, no consultar detalle")
    args = parser.parse_args()

    cuit = args.cuit.replace("-", "").replace(" ", "")

    print(f"Test WSFEv1 aislado — {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"CUIT objetivo: {cuit}")

    # Paso 0
    if not verificar_certificados():
        print("\nERROR: Certificados no encontrados. Abortando.")
        sys.exit(1)

    # Paso 1
    client = crear_cliente()

    # Paso 2
    try:
        test_autenticacion(client, cuit)
    except Exception as e:
        print(f"\n  ERROR WSAA: {e}")
        print("  No se pudo autenticar. Verificar certificado y permisos.")
        sys.exit(2)

    # Paso 3
    pvs = descubrir_puntos_venta(client, cuit)

    # Paso 4
    mapa = escanear_ultimos(client, cuit, pvs)

    # Paso 5
    if args.solo_escaneo:
        print("\n  (--solo-escaneo: omitiendo consulta de detalle)")
        resultados = []
    else:
        resultados = consultar_comprobantes(client, cuit, mapa, args.limite)

    # Paso 6
    resumen_final(cuit, resultados, mapa)


if __name__ == "__main__":
    main()
