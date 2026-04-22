#!/usr/bin/env python3
r"""
Scraping de comprobantes AFIP via portal web RCEL.
Para PVs que NO son accesibles via Web Services (Factuweb, Factura en Linea).

Uso:
    cd "C:\Users\DELL\Desktop\proyectos python\infofiscal"
    python scripts/scraping_afip.py --cuit 20321518045 --password LioLio2025!
"""

import argparse
import json
import time
import os
import glob as glob_mod
from pathlib import Path
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

ROOT = Path(__file__).parent.parent
DOWNLOAD_DIR = str(ROOT / 'facturas' / 'scraping')


def crear_driver(headless=False):
    opts = webdriver.ChromeOptions()
    if headless:
        opts.add_argument('--headless=new')
    opts.add_argument('--disable-blink-features=AutomationControlled')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--window-size=1280,900')

    # Configurar directorio de descargas
    prefs = {
        'download.default_directory': DOWNLOAD_DIR,
        'download.prompt_for_download': False,
        'download.directory_upgrade': True,
    }
    opts.add_experimental_option('prefs', prefs)

    driver = webdriver.Chrome(options=opts)
    driver.implicitly_wait(5)
    return driver


def ss(driver, name):
    path = ROOT / 'scripts' / f'debug_{name}.png'
    driver.save_screenshot(str(path))
    print(f"  [ss] {name}", flush=True)


def login_afip(driver, cuit, password):
    print(f"\n[1] LOGIN...", flush=True)
    driver.get('https://auth.afip.gob.ar/contribuyente_/login.xhtml')
    time.sleep(2)
    wait = WebDriverWait(driver, 15)

    wait.until(EC.presence_of_element_located((By.ID, 'F1:username'))).send_keys(cuit)
    driver.find_element(By.ID, 'F1:btnSiguiente').click()
    time.sleep(2)

    wait.until(EC.presence_of_element_located((By.ID, 'F1:password'))).send_keys(password)
    driver.find_element(By.ID, 'F1:btnIngresar').click()
    time.sleep(3)
    print(f"  OK", flush=True)


def ir_a_rcel(driver):
    print(f"\n[2] RCEL...", flush=True)
    driver.get('https://portalcf.cloud.afip.gob.ar/portal/app/mis-servicios')
    time.sleep(3)

    for link in driver.find_elements(By.TAG_NAME, 'a'):
        if 'comprobantes en l' in (link.text or '').lower():
            link.click()
            time.sleep(4)
            break

    if len(driver.window_handles) > 1:
        driver.switch_to.window(driver.window_handles[-1])
    print(f"  OK: {driver.current_url}", flush=True)


def seleccionar_empresa(driver):
    print(f"\n[3] EMPRESA...", flush=True)
    for btn in driver.find_elements(By.CSS_SELECTOR, 'input[type="button"]'):
        if 'calegari' in (btn.get_attribute('value') or '').lower():
            btn.click()
            time.sleep(3)
            print(f"  OK", flush=True)
            return True

    for el in driver.find_elements(By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'calegari')]"):
        el.click()
        time.sleep(3)
        return True

    print(f"  FALLO", flush=True)
    return False


def consultar_pv(driver, punto_venta, fecha_desde='01/01/2020', fecha_hasta='02/04/2026'):
    """Ir a consultas, seleccionar PV, rango de fechas, y buscar."""
    print(f"\n[4] CONSULTA PV {punto_venta} ({fecha_desde} - {fecha_hasta})...", flush=True)

    # Ir al menu principal y clickear Consultas
    driver.get('https://fe.afip.gob.ar/rcel/jsp/menu_ppal.jsp')
    time.sleep(2)

    for link in driver.find_elements(By.TAG_NAME, 'a'):
        href = link.get_attribute('href') or ''
        if 'filtrarComprobantesGenerados' in href:
            link.click()
            time.sleep(4)
            break

    print(f"  Pagina: {driver.title} - {driver.current_url}", flush=True)
    ss(driver, f'04_form_pv{punto_venta}')

    # Dump todos los elementos del formulario para debugging
    all_selects = driver.find_elements(By.TAG_NAME, 'select')
    all_inputs = driver.find_elements(By.TAG_NAME, 'input')
    print(f"  Form: {len(all_selects)} selects, {len(all_inputs)} inputs", flush=True)

    for sel in all_selects:
        sid = sel.get_attribute('id') or '?'
        sname = sel.get_attribute('name') or '?'
        opts = [f"{o.get_attribute('value')}={o.text}" for o in sel.find_elements(By.TAG_NAME, 'option')[:5]]
        print(f"    SELECT id={sid} name={sname} -> {opts}", flush=True)

    for inp in all_inputs:
        itype = inp.get_attribute('type') or 'text'
        if itype == 'hidden':
            continue
        iid = inp.get_attribute('id') or '?'
        iname = inp.get_attribute('name') or '?'
        ival = inp.get_attribute('value') or ''
        print(f"    INPUT id={iid} name={iname} type={itype} value={ival}", flush=True)

    # Buscar campo fecha desde (probar varios nombres)
    fed = None
    for name in ['fechaEmisionDesde', 'fed', 'fecha_desde']:
        try:
            fed = driver.find_element(By.NAME, name)
            print(f"  Fecha desde: name={name}", flush=True)
            break
        except NoSuchElementException:
            continue
    if not fed:
        # Buscar por id
        for iid in ['fechaEmisionDesde', 'fed']:
            try:
                fed = driver.find_element(By.ID, iid)
                print(f"  Fecha desde: id={iid}", flush=True)
                break
            except NoSuchElementException:
                continue
    if not fed:
        print(f"  NO se encontro campo fecha desde!", flush=True)
        return []

    # Buscar campo fecha hasta
    feh = None
    for name in ['fechaEmisionHasta', 'feh', 'fecha_hasta']:
        try:
            feh = driver.find_element(By.NAME, name)
            break
        except NoSuchElementException:
            continue
    if not feh:
        for iid in ['fechaEmisionHasta', 'feh']:
            try:
                feh = driver.find_element(By.ID, iid)
                break
            except NoSuchElementException:
                continue

    # Setear fechas via JavaScript (mas confiable que send_keys en campos date)
    driver.execute_script("arguments[0].value = arguments[1];", fed, fecha_desde)
    if feh:
        driver.execute_script("arguments[0].value = arguments[1];", feh, fecha_hasta)
    print(f"  Fechas seteadas: {fecha_desde} - {fecha_hasta}", flush=True)

    # Buscar select de punto de venta (probar varios nombres/ids)
    pv_el = None
    for selector in ['puntodeventa', 'puntoventa', 'idPuntoVenta', 'ptovta']:
        try:
            pv_el = driver.find_element(By.NAME, selector)
            print(f"  PV select: name={selector}", flush=True)
            break
        except NoSuchElementException:
            try:
                pv_el = driver.find_element(By.ID, selector)
                print(f"  PV select: id={selector}", flush=True)
                break
            except NoSuchElementException:
                continue

    if not pv_el:
        # Buscar en todos los selects
        for sel in all_selects:
            opts_text = ' '.join(o.text for o in sel.find_elements(By.TAG_NAME, 'option'))
            if '0002' in opts_text or 'pto' in (sel.get_attribute('id') or '').lower():
                pv_el = sel
                sid = sel.get_attribute('id') or sel.get_attribute('name')
                print(f"  PV select encontrado por contenido: {sid}", flush=True)
                break

    if pv_el:
        pv_select = Select(pv_el)
        options = pv_select.options
        print(f"  PVs disponibles:", flush=True)
        for o in options:
            print(f"    [{o.get_attribute('value')}] {o.text}", flush=True)

        selected = False
        for o in options:
            val = o.get_attribute('value')
            text = o.text
            if val == str(punto_venta) or f'{punto_venta:04d}' in text:
                pv_select.select_by_value(val)
                print(f"  PV seleccionado: {text}", flush=True)
                selected = True
                break

        if not selected:
            print(f"  PV {punto_venta} NO disponible en RCEL", flush=True)
            return []
    else:
        print(f"  NO se encontro select de PV!", flush=True)

    time.sleep(1)
    ss(driver, f'05_form_filled_pv{punto_venta}')

    # Click Buscar
    try:
        driver.execute_script("validarCampos();")
    except Exception:
        # Fallback: click el boton Buscar directamente
        for btn in driver.find_elements(By.CSS_SELECTOR, 'input[type="button"]'):
            if 'buscar' in (btn.get_attribute('value') or '').lower():
                btn.click()
                break
    time.sleep(5)

    ss(driver, f'06_resultados_pv{punto_venta}')
    print(f"  URL resultados: {driver.current_url}", flush=True)
    print(f"  Titulo: {driver.title}", flush=True)

    # Explorar resultados
    comprobantes = extraer_resultados(driver, punto_venta)

    return comprobantes


def extraer_resultados(driver, punto_venta):
    """Extraer comprobantes de la pagina de resultados."""
    comprobantes = []

    # Buscar la tabla de comprobantes (no la de header)
    tables = driver.find_elements(By.TAG_NAME, 'table')
    print(f"  {len(tables)} tablas en pagina", flush=True)

    for i, table in enumerate(tables):
        rows = table.find_elements(By.TAG_NAME, 'tr')
        if len(rows) <= 1:
            continue

        # Headers
        header_cells = rows[0].find_elements(By.TAG_NAME, 'th')
        if not header_cells:
            header_cells = rows[0].find_elements(By.TAG_NAME, 'td')
        headers = [h.text.strip() for h in header_cells]

        # Solo nos interesa la tabla de comprobantes (tiene headers como "Fecha", "Tipo", "Nro", etc)
        has_comp_headers = any(kw in ' '.join(headers).lower() for kw in ['fecha', 'tipo', 'nro', 'importe', 'cae', 'comprobante'])
        if not has_comp_headers:
            continue

        print(f"\n  TABLA COMPROBANTES (tabla {i}): {len(rows)-1} filas", flush=True)
        print(f"  Headers: {headers}", flush=True)

        for row in rows[1:]:
            cells = row.find_elements(By.TAG_NAME, 'td')
            if len(cells) < 3:
                continue
            registro = {}
            for j, h in enumerate(headers):
                if j < len(cells):
                    registro[h] = cells[j].text.strip()
            registro['punto_venta'] = punto_venta
            comprobantes.append(registro)

        # Mostrar primeros
        for c in comprobantes[:5]:
            print(f"    {c}", flush=True)
        if len(comprobantes) > 5:
            print(f"    ... y {len(comprobantes) - 5} mas", flush=True)

    # Intentar "Exportar Todos (Txt)" si hay comprobantes
    try:
        export_links = driver.find_elements(By.PARTIAL_LINK_TEXT, 'Exportar')
        for el in export_links:
            text = el.text.strip()
            print(f"  Boton export: [{text}]", flush=True)

        # Click en "Exportar Todos (Txt)" o similar
        for el in export_links:
            if 'todos' in el.text.lower() or 'all' in el.text.lower():
                print(f"  Descargando: {el.text.strip()}", flush=True)
                el.click()
                time.sleep(5)

                # Buscar archivo descargado
                files = glob_mod.glob(os.path.join(DOWNLOAD_DIR, '*.txt'))
                recent = sorted(files, key=os.path.getmtime, reverse=True)
                if recent:
                    print(f"  Archivo descargado: {recent[0]}", flush=True)
                    with open(recent[0], 'r', encoding='latin-1') as f:
                        content = f.read()
                    print(f"  Contenido ({len(content)} bytes):", flush=True)
                    lines = content.strip().split('\n')
                    for line in lines[:10]:
                        print(f"    {line}", flush=True)
                    if len(lines) > 10:
                        print(f"    ... ({len(lines)} lineas total)", flush=True)
                break

    except Exception as e:
        print(f"  Error en export: {e}", flush=True)

    # Verificar paginacion
    try:
        # RCEL suele tener links de paginacion o un "Siguiente"
        page_links = driver.find_elements(By.CSS_SELECTOR, 'a')
        for pl in page_links:
            text = (pl.text or '').strip().lower()
            if 'siguiente' in text or 'next' in text or '>>' in text:
                print(f"  Paginacion detectada: [{pl.text.strip()}]", flush=True)
    except:
        pass

    print(f"  Total extraidos: {len(comprobantes)} comprobantes", flush=True)
    return comprobantes


def main():
    parser = argparse.ArgumentParser(description='Scraping comprobantes AFIP')
    parser.add_argument('--cuit', required=True, help='CUIT para login')
    parser.add_argument('--password', required=True, help='Clave fiscal')
    parser.add_argument('--puntos-venta', default='1,2', help='PVs a consultar')
    parser.add_argument('--desde', default='01/01/2020', help='Fecha desde dd/mm/yyyy')
    parser.add_argument('--hasta', default='02/04/2026', help='Fecha hasta dd/mm/yyyy')
    parser.add_argument('--headless', action='store_true', help='Sin ventana visible')
    args = parser.parse_args()

    pvs = [int(x) for x in args.puntos_venta.split(',')]

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    driver = crear_driver(headless=args.headless)

    try:
        login_afip(driver, args.cuit, args.password)
        ir_a_rcel(driver)
        seleccionar_empresa(driver)

        todos = []
        for pv in pvs:
            comps = consultar_pv(driver, pv, args.desde, args.hasta)
            todos.extend(comps)

        # Guardar JSON
        if todos:
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            filepath = Path(DOWNLOAD_DIR) / f'scraping_{args.cuit}_{ts}.json'
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({
                    'cuit': args.cuit,
                    'fecha': datetime.now().isoformat(),
                    'puntos_venta': pvs,
                    'total': len(todos),
                    'comprobantes': todos
                }, f, indent=2, ensure_ascii=False)
            print(f"\nJSON: {filepath} ({len(todos)} comprobantes)", flush=True)

        print(f"\n{'='*60}", flush=True)
        print(f"FIN", flush=True)
        print(f"{'='*60}", flush=True)

        # Browser abierto para debug
        time.sleep(120)

    except Exception as e:
        print(f"\n[ERROR] {e}", flush=True)
        ss(driver, 'error')
        import traceback
        traceback.print_exc()
        time.sleep(30)

    finally:
        driver.quit()


if __name__ == '__main__':
    main()
