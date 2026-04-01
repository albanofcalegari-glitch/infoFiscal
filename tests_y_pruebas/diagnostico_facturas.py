#!/usr/bin/env python3
"""
Diagnóstico: ¿Por qué no aparecen las facturas?
Verificaciones paso a paso sin dependencia de OpenSSL
"""

def diagnostico_facturas():
    print("🔍 === DIAGNÓSTICO: ¿POR QUÉ NO APARECEN LAS FACTURAS? ===")
    print()
    
    print("📋 VERIFICACIONES NECESARIAS:")
    print("1. Tipo de facturas generadas")
    print("2. Puntos de venta utilizados") 
    print("3. Tipos de comprobante emitidos")
    print("4. Fechas de emisión")
    print("5. Autenticación WSAA")
    print()
    
    # Verificar certificados
    print("🔐 1. VERIFICACIÓN DE CERTIFICADOS:")
    from pathlib import Path
    import os
    
    if os.path.basename(os.getcwd()) == 'src':
        base_dir = Path(os.getcwd()).parent
    else:
        base_dir = Path(os.getcwd())
    
    cert_path = base_dir / 'certs' / 'certificado.crt'
    key_path = base_dir / 'certs' / 'clave_privada.key'
    
    if cert_path.exists() and key_path.exists():
        print(f"   ✅ Certificados encontrados:")
        print(f"   📄 {cert_path}")
        print(f"   🔑 {key_path}")
        
        # Verificar contenido del certificado
        try:
            with open(cert_path, 'r') as f:
                cert_content = f.read()
            if 'BEGIN CERTIFICATE' in cert_content:
                print(f"   ✅ Formato de certificado válido")
            else:
                print(f"   ❌ Formato de certificado inválido")
        except Exception as e:
            print(f"   ⚠️ Error leyendo certificado: {e}")
    else:
        print(f"   ❌ Certificados no encontrados")
    
    print()
    print("🏭 2. VERIFICACIÓN MANUAL NECESARIA:")
    print("   Ve a https://auth.afip.gob.ar/contribuyente_/login.xhtml")
    print("   Ingresa con tu CUIT y clave fiscal")
    print("   Ve a: Comprobantes en línea > Consultar comprobantes emitidos")
    print("   Verifica:")
    print("   - ¿Qué puntos de venta tenés activos?")
    print("   - ¿Qué tipos de comprobante emitiste?") 
    print("   - ¿En qué fechas?")
    print("   - ¿Son facturas electrónicas o de talonario?")
    print()
    
    print("📊 3. DATOS A VERIFICAR:")
    cuits_a_verificar = [
        ("20321518045", "CALEGARI ALBANO FEDERICO", "Tu CUIT"),
        ("23333730219", "VEGA MARTIN MATIAS", "Cliente Martin Vega")
    ]
    
    for cuit, nombre, desc in cuits_a_verificar:
        print(f"   🏢 {desc} ({cuit}):")
        print(f"      - Nombre: {nombre}")
        print(f"      - ¿Tiene facturas electrónicas?")
        print(f"      - ¿En qué puntos de venta?")
        print(f"      - ¿Qué tipos de comprobante?")
        print(f"      - ¿Monotributo o Responsable Inscripto?")
        print()
    
    print("🔧 4. SOLUCIONES POSIBLES:")
    print("   A. Instalar OpenSSL para autenticación WSAA")
    print("   B. Verificar que las facturas sean electrónicas (no talonario)")
    print("   C. Consultar puntos de venta específicos donde emitiste")
    print("   D. Usar tipos de comprobante correctos según régimen fiscal")
    print("   E. Verificar fechas de emisión en AFIP")
    print()
    
    print("🎯 5. PRÓXIMOS PASOS:")
    print("   1. Verificar manualmente en AFIP qué facturas electrónicas hay")
    print("   2. Anotar: PV, Tipo, Números, Fechas")
    print("   3. Instalar OpenSSL o usar método alternativo")
    print("   4. Ajustar búsqueda con datos reales")
    print()
    
    print("💡 IMPORTANTE:")
    print("   Las facturas de TALONARIO no aparecen en WSFEv1")
    print("   Solo las facturas ELECTRÓNICAS son consultables vía web services")
    print("   Monotributo usa tipos diferentes (51, 52, 53) vs RI (1, 6, 11)")

if __name__ == "__main__":
    diagnostico_facturas()