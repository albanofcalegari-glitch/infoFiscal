#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cliente RCEL (scraping) — Consulta de comprobantes via portal web AFIP.
Cubre PVs que NO son accesibles via Web Services (Factura en Linea, Factuweb).

Uso como modulo:
    from rcel_scraper import RCELScraper
    scraper = RCELScraper(cuit='20321518045', password='...')
    comprobantes = scraper.consultar(punto_venta=2, fecha_desde='01/01/2020', fecha_hasta='02/04/2026')
"""

import time
import os
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
)


class RCELScraper:
    """Scraper del portal RCEL de AFIP para comprobantes emitidos y recibidos."""

    def __init__(self, cuit, password, headless=True):
        self.cuit = cuit
        self.password = password
        self.headless = headless
        self._driver = None

    # ── Driver ────────────────────────────────────────────────────────

    def _crear_driver(self):
        opts = webdriver.ChromeOptions()
        if self.headless:
            opts.add_argument('--headless=new')
        opts.add_argument('--disable-blink-features=AutomationControlled')
        opts.add_argument('--no-sandbox')
        opts.add_argument('--disable-gpu')
        opts.add_argument('--window-size=1280,900')
        driver = webdriver.Chrome(options=opts)
        driver.implicitly_wait(5)
        return driver

    def _log(self, msg):
        print(f"[RCEL] {msg}", flush=True)

    # ── Login ─────────────────────────────────────────────────────────

    def _login(self, driver):
        self._log("Login AFIP...")
        driver.get('https://auth.afip.gob.ar/contribuyente_/login.xhtml')
        time.sleep(2)
        wait = WebDriverWait(driver, 15)

        wait.until(EC.presence_of_element_located((By.ID, 'F1:username'))).send_keys(self.cuit)
        driver.find_element(By.ID, 'F1:btnSiguiente').click()
        time.sleep(2)

        wait.until(EC.presence_of_element_located((By.ID, 'F1:password'))).send_keys(self.password)
        driver.find_element(By.ID, 'F1:btnIngresar').click()
        time.sleep(3)
        self._log(f"Login OK")

    # ── Navegacion RCEL ───────────────────────────────────────────────

    def _ir_a_rcel(self, driver):
        self._log("Navegando a RCEL...")
        driver.get('https://portalcf.cloud.afip.gob.ar/portal/app/mis-servicios')
        time.sleep(3)

        for link in driver.find_elements(By.TAG_NAME, 'a'):
            if 'comprobantes en l' in (link.text or '').lower():
                link.click()
                time.sleep(4)
                break

        if len(driver.window_handles) > 1:
            driver.switch_to.window(driver.window_handles[-1])
        self._log(f"RCEL: {driver.current_url}")

    def _seleccionar_empresa(self, driver, empresa=None, cuit_empresa=None):
        """Seleccionar empresa a representar.

        Args:
            empresa: nombre parcial para buscar (ej: 'CERETO')
            cuit_empresa: CUIT de la empresa a buscar (ej: '27312238018')
            Si ambos son None, selecciona la primera disponible.
        """
        self._log(f"Seleccionando empresa... (buscar={empresa}, cuit={cuit_empresa})")

        # Listar todas las empresas disponibles para debug
        buttons = driver.find_elements(By.CSS_SELECTOR, 'input[type="button"]')
        empresas_disponibles = []
        for btn in buttons:
            val = (btn.get_attribute('value') or '').strip()
            if val:
                empresas_disponibles.append(val)
        self._log(f"Empresas disponibles: {empresas_disponibles}")

        # Buscar por CUIT primero (mas preciso)
        if cuit_empresa:
            cuit_limpio = cuit_empresa.replace('-', '').replace(' ', '')
            for btn in buttons:
                val = (btn.get_attribute('value') or '').strip()
                if not val:
                    continue
                # El boton puede tener formato "CUIT - NOMBRE" o contener el CUIT
                val_numeros = val.replace('-', '').replace(' ', '')
                if cuit_limpio in val_numeros:
                    self._log(f"Empresa (por CUIT): {val}")
                    btn.click()
                    time.sleep(3)
                    return val

        # Buscar por nombre
        if empresa:
            # Intentar match con cada palabra del nombre
            buscar = empresa.lower().split(',')[0].strip()  # "Cereto, Regina" -> "cereto"
            for btn in buttons:
                val = (btn.get_attribute('value') or '').strip()
                if not val:
                    continue
                if buscar in val.lower():
                    self._log(f"Empresa (por nombre): {val}")
                    btn.click()
                    time.sleep(3)
                    return val

        # Si no se pidio ninguna especifica, tomar la primera
        if empresa is None and cuit_empresa is None:
            for btn in buttons:
                val = (btn.get_attribute('value') or '').strip()
                if val:
                    self._log(f"Empresa (primera): {val}")
                    btn.click()
                    time.sleep(3)
                    return val

        # Fallback: buscar en celdas de tabla
        if empresa or cuit_empresa:
            buscar_texto = (empresa or '').lower().split(',')[0].strip()
            for td in driver.find_elements(By.TAG_NAME, 'td'):
                text = (td.text or '').strip()
                if not text or len(text) < 3:
                    continue
                if buscar_texto and buscar_texto in text.lower():
                    self._log(f"Empresa (td match): {text}")
                    td.click()
                    time.sleep(3)
                    return text

        self._log(f"Empresa NO encontrada: buscar={empresa}, cuit={cuit_empresa}")
        return None

    def _navegar_seccion(self, driver, seccion='emitidos'):
        """Navegar al formulario de consulta de la sección indicada.

        Args:
            seccion: 'emitidos' (Comprobantes Generados) o 'recibidos' (Comprobantes Recibidos)
        """
        driver.get('https://fe.afip.gob.ar/rcel/jsp/menu_ppal.jsp')
        time.sleep(2)

        if seccion == 'recibidos':
            keywords = ['filtrarComprobantesRecibidos', 'consultarComprobantesRecibidos',
                        'comprobantesRecibidos']
        else:
            keywords = ['filtrarComprobantesGenerados']

        for link in driver.find_elements(By.TAG_NAME, 'a'):
            href = link.get_attribute('href') or ''
            if any(kw in href for kw in keywords):
                link.click()
                time.sleep(3)
                return True

        # Fallback: buscar por texto del link
        if seccion == 'recibidos':
            for link in driver.find_elements(By.TAG_NAME, 'a'):
                text = (link.text or '').lower()
                if 'recibido' in text and 'comprobante' in text:
                    link.click()
                    time.sleep(3)
                    return True

        self._log(f"No se encontro seccion '{seccion}' en el menu RCEL")
        return False

    def _obtener_pvs_disponibles(self, driver, seccion='emitidos'):
        """Ir al formulario de consulta y devolver lista de PVs disponibles."""
        if not self._navegar_seccion(driver, seccion):
            return []

        try:
            pv_el = driver.find_element(By.ID, 'puntodeventa')
            pv_select = Select(pv_el)
            pvs = []
            for o in pv_select.options:
                val = o.get_attribute('value')
                if val:
                    pvs.append({'value': val, 'text': o.text.strip()})
            return pvs
        except NoSuchElementException:
            return []

    # ── Consulta ──────────────────────────────────────────────────────

    def _consultar_pv(self, driver, punto_venta, fecha_desde, fecha_hasta, seccion='emitidos'):
        """Consultar comprobantes para un PV especifico. Retorna lista de dicts."""
        self._log(f"Consultando PV {punto_venta} ({fecha_desde} - {fecha_hasta}) [{seccion}]...")

        if not self._navegar_seccion(driver, seccion):
            return []

        # Setear fechas
        fed = driver.find_element(By.NAME, 'fechaEmisionDesde')
        driver.execute_script("arguments[0].value = arguments[1];", fed, fecha_desde)

        feh = driver.find_element(By.NAME, 'fechaEmisionHasta')
        driver.execute_script("arguments[0].value = arguments[1];", feh, fecha_hasta)

        # Seleccionar PV
        pv_el = driver.find_element(By.ID, 'puntodeventa')
        pv_select = Select(pv_el)

        selected = False
        for o in pv_select.options:
            val = o.get_attribute('value')
            if val == str(punto_venta):
                pv_select.select_by_value(val)
                self._log(f"PV: {o.text.strip()}")
                selected = True
                break

        if not selected:
            self._log(f"PV {punto_venta} no disponible")
            return []

        # Buscar
        try:
            driver.execute_script("validarCampos();")
        except Exception:
            for btn in driver.find_elements(By.CSS_SELECTOR, 'input[type="button"]'):
                if 'buscar' in (btn.get_attribute('value') or '').lower():
                    btn.click()
                    break
        time.sleep(5)

        # Extraer tabla de comprobantes
        return self._extraer_tabla(driver, punto_venta)

    def _extraer_tabla(self, driver, punto_venta):
        """Extraer comprobantes de la tabla de resultados."""
        comprobantes = []
        tables = driver.find_elements(By.TAG_NAME, 'table')

        for table in tables:
            rows = table.find_elements(By.TAG_NAME, 'tr')
            if len(rows) <= 1:
                continue

            header_cells = rows[0].find_elements(By.TAG_NAME, 'th')
            if not header_cells:
                header_cells = rows[0].find_elements(By.TAG_NAME, 'td')
            headers = [h.text.strip() for h in header_cells]

            # Solo tabla de comprobantes
            headers_lower = ' '.join(headers).lower()
            if not any(kw in headers_lower for kw in ['fecha', 'comprobante', 'cae', 'importe']):
                continue

            self._log(f"Tabla: {len(rows)-1} filas, headers={headers[:5]}")

            for row in rows[1:]:
                cells = row.find_elements(By.TAG_NAME, 'td')
                if len(cells) < 3:
                    continue
                registro = {}
                for j, h in enumerate(headers):
                    if j < len(cells):
                        registro[h] = cells[j].text.strip()
                registro['punto_venta_rcel'] = punto_venta
                comprobantes.append(registro)

            # Verificar paginacion
            page_links = driver.find_elements(By.PARTIAL_LINK_TEXT, 'Siguiente')
            if page_links:
                self._log(f"Paginacion detectada — solo primera pagina extraida")

            break  # Solo la primera tabla de comprobantes

        self._log(f"PV {punto_venta}: {len(comprobantes)} comprobantes")
        return comprobantes

    # ── API publica ───────────────────────────────────────────────────

    def consultar(self, puntos_venta=None, fecha_desde='01/01/2020', fecha_hasta=None,
                  empresa=None, cuit_empresa=None, seccion='emitidos'):
        """Consultar comprobantes RCEL.

        Args:
            puntos_venta: lista de PVs a consultar, o None para todos los disponibles
            fecha_desde: 'dd/mm/yyyy'
            fecha_hasta: 'dd/mm/yyyy' (default: hoy)
            empresa: nombre parcial de la empresa a representar (None = primera)
            cuit_empresa: CUIT de la empresa a representar (mas preciso que nombre)
            seccion: 'emitidos' o 'recibidos'

        Returns:
            dict con 'comprobantes', 'pvs_consultados', 'empresa', 'error'
        """
        from datetime import datetime

        if fecha_hasta is None:
            fecha_hasta = datetime.now().strftime('%d/%m/%Y')

        driver = None
        try:
            driver = self._crear_driver()
            inicio = time.time()

            self._login(driver)
            self._ir_a_rcel(driver)
            empresa_nombre = self._seleccionar_empresa(driver, empresa, cuit_empresa)

            if not empresa_nombre:
                return {'comprobantes': [], 'error': 'No se pudo seleccionar empresa en RCEL'}

            # Obtener PVs disponibles para la sección
            pvs_disponibles = self._obtener_pvs_disponibles(driver, seccion)
            self._log(f"PVs disponibles [{seccion}]: {pvs_disponibles}")

            if puntos_venta is None:
                puntos_venta = [int(pv['value']) for pv in pvs_disponibles]

            todos = []
            pvs_consultados = []

            for pv in puntos_venta:
                pv_existe = any(p['value'] == str(pv) for p in pvs_disponibles)
                if not pv_existe:
                    self._log(f"PV {pv} no existe en RCEL [{seccion}], saltando")
                    continue

                comps = self._consultar_pv(driver, pv, fecha_desde, fecha_hasta, seccion)
                todos.extend(comps)
                pvs_consultados.append(pv)

            elapsed = time.time() - inicio
            self._log(f"Total [{seccion}]: {len(todos)} comprobantes en {elapsed:.1f}s")

            return {
                'comprobantes': todos,
                'pvs_disponibles': pvs_disponibles,
                'pvs_consultados': pvs_consultados,
                'empresa': empresa_nombre,
                'tiempo': round(elapsed, 1),
                'seccion': seccion,
                'error': None,
            }

        except Exception as e:
            self._log(f"ERROR [{seccion}]: {e}")
            return {
                'comprobantes': [],
                'seccion': seccion,
                'error': str(e),
            }

        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

    # ── Normalizar a formato compatible con el sistema ────────────────

    @staticmethod
    def normalizar_comprobantes(comprobantes_rcel, seccion='emitidos'):
        """Convertir comprobantes RCEL al formato del sistema.

        Args:
            comprobantes_rcel: lista de dicts crudos extraídos de la tabla HTML
            seccion: 'emitidos' o 'recibidos' — ajusta qué campos buscar
        """
        normalizados = []
        for c in comprobantes_rcel:
            nro_comp = c.get('Nro. Comprobante', c.get('Nro Comprobante', ''))
            pv = ''
            nro = ''
            if '-' in nro_comp:
                parts = nro_comp.split('-')
                pv = parts[0].lstrip('0') or '0'
                nro = parts[1].lstrip('0') or '0'

            # Fecha: "02/07/2024" -> "20240702"
            fecha_raw = c.get('Fecha Emisión', c.get('Fecha Emision',
                        c.get('Fecha Emisin', c.get('Fecha', ''))))
            fecha_afip = ''
            if fecha_raw and '/' in fecha_raw:
                partes = fecha_raw.split('/')
                if len(partes) == 3:
                    fecha_afip = f"{partes[2]}{partes[1]}{partes[0]}"

            importe = c.get('Importe Total', c.get('Imp. Total', ''))
            try:
                importe = float(str(importe).replace('.', '').replace(',', '.'))
            except (ValueError, TypeError):
                importe = 0

            tipo_desc = c.get('Tipo Comprobante', c.get('Tipo de Comprobante', ''))

            # Documento: receptor (emitidos) o emisor (recibidos)
            if seccion == 'recibidos':
                doc_nro = c.get('Nro. Doc. del Emisor', c.get('Nro Doc. del Emisor',
                          c.get('Nro. Doc. Emisor', c.get('CUIT Emisor', ''))))
                doc_tipo = c.get('Tipo Doc. del Emisor', c.get('Tipo Doc del Emisor',
                           c.get('Tipo Doc. Emisor', '')))
                denominacion = c.get('Denominación Emisor', c.get('Denominacion Emisor',
                               c.get('Razón Social', c.get('Razon Social', ''))))
            else:
                doc_nro = c.get('Nro. Doc. del Receptor', c.get('Nro Doc. del Receptor', ''))
                doc_tipo = c.get('Tipo Doc. del Receptor', c.get('Tipo Doc del Receptor', ''))
                denominacion = ''

            norm = {
                'CbteTipo': tipo_desc,
                'CbteTipoDesc': tipo_desc,
                'PtoVta': pv,
                'CbteNro': nro,
                'CbteFch': fecha_afip,
                'ImpTotal': importe,
                'CAE': c.get('CAE', ''),
                'DocNro': doc_nro,
                'DocTipo': doc_tipo,
                'origen': 'RCEL',
                'seccion': seccion,
                'consulta': {
                    'tipo_descripcion': tipo_desc,
                    'punto_venta': int(pv) if pv.isdigit() else 0,
                    'numero': int(nro) if nro.isdigit() else 0,
                    'numero_formateado': nro_comp,
                },
            }
            if denominacion:
                norm['DenominacionEmisor'] = denominacion

            normalizados.append(norm)

        return normalizados
