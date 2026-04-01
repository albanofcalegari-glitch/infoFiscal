#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUÍA COMPLETA: Habilitar WSFEXv1 en AFIP
Pasos detallados para configurar el servicio WSFEXv1 con tu certificado existente
"""

def guia_habilitar_wsfexv1():
    """Guía paso a paso para habilitar WSFEXv1"""
    print("🔐 GUÍA: HABILITAR WSFEXv1 CON TU CERTIFICADO ACTUAL")
    print("=" * 70)
    
    print("\n📋 REQUISITOS PREVIOS:")
    print("✅ Ya tienes certificado digital funcionando con WSFEv1")
    print("✅ Ya tienes acceso a AFIP con Clave Fiscal")
    print("✅ El CUIT debe estar en régimen de Monotributo o ser Exportador")
    
    print(f"\n🎯 PASO 1: INGRESAR A AFIP ADMINISTRADOR")
    print("-" * 50)
    print("1. Ir a: https://auth.afip.gob.ar/contribuyente_sin_clave")
    print("2. Ingresar CUIT y Clave Fiscal")
    print("3. Ir a 'Administrador de Relaciones de Clave Fiscal'")
    
    print(f"\n🎯 PASO 2: BUSCAR EL SERVICIO WSFEXv1")
    print("-" * 50)
    print("1. Hacer clic en 'Nueva Relación'")
    print("2. En el buscador escribir: 'WSFEXv1' o 'Facturación Electrónica Exportación'")
    print("3. Buscar específicamente:")
    print("   📌 'Web Service de Facturación Electrónica Exportación'")
    print("   📌 'WSFEX' (nombre corto)")
    print("   📌 'Monotributo Web Service'")
    
    print(f"\n🎯 PASO 3: HABILITAR EL SERVICIO")
    print("-" * 50)
    print("1. Seleccionar el servicio WSFEXv1")
    print("2. Elegir 'Generar nueva relación'")
    print("3. Completar los datos solicitados:")
    print("   • Denominación: 'InfoFiscal WSFEXv1'")
    print("   • Fecha desde: Hoy")
    print("   • Fecha hasta: 1 año (máximo permitido)")
    
    print(f"\n🎯 PASO 4: ASOCIAR TU CERTIFICADO")
    print("-" * 50)
    print("1. En la nueva relación creada, buscar 'Certificados'")
    print("2. Hacer clic en 'Adherir Certificado'")
    print("3. Subir el MISMO archivo .crt que usas para WSFEv1")
    print("4. Confirmar la asociación")
    
    print(f"\n⚠️ IMPORTANTE - VERIFICACIONES:")
    print("-" * 50)
    print("📍 El CUIT debe cumplir al menos UNA de estas condiciones:")
    print("   ✅ Estar inscrito en Monotributo")
    print("   ✅ Realizar operaciones de exportación")
    print("   ✅ Emitir facturas tipo M (51, 52, 53)")
    print("   ✅ Emitir facturas de exportación (19, 20, 21)")
    
    print(f"\n🔍 VERIFICAR SI YA TIENES WSFEXv1:")
    print("-" * 50)
    print("1. En Administrador de Relaciones")
    print("2. Buscar 'WSFEXv1' o 'Exportación'")
    print("3. Si ya aparece, verificar:")
    print("   • Estado: ACTIVO")
    print("   • Certificado: ADHERIDO")
    print("   • Vigencia: NO VENCIDA")

def diferencias_servicios():
    """Explicar diferencias entre servicios"""
    print(f"\n📊 DIFERENCIAS ENTRE SERVICIOS AFIP")
    print("=" * 70)
    
    print(f"\n🔸 WSFEv1 (Web Service Facturación Electrónica v1):")
    print("   🎯 Para: RESPONSABLES INSCRIPTOS")
    print("   📄 Tipos: Facturas A (1), B (6), C (11)")
    print("   📄 Tipos: Notas Débito/Crédito A, B, C")
    print("   ✅ Disponible: SIEMPRE (servicio base)")
    print("   🔐 Certificado: TU CERTIFICADO ACTUAL")
    print("   ⚙️ Estado: YA HABILITADO ✅")
    
    print(f"\n🔸 WSFEXv1 (Web Service Facturación Electrónica Exportación v1):")
    print("   🎯 Para: MONOTRIBUTISTAS + EXPORTADORES")
    print("   📄 Tipos: Facturas M (51, 52, 53)")
    print("   📄 Tipos: Exportación (19, 20, 21)")
    print("   📄 Tipos: Recibos M (54)")
    print("   ⚠️ Disponible: SOLO SI SE HABILITA")
    print("   🔐 Certificado: EL MISMO QUE WSFEv1")
    print("   ⚙️ Estado: PENDIENTE DE HABILITAR ⚠️")
    
    print(f"\n🔸 WSMTXCA (Web Service Códigos MTX):")
    print("   🎯 Para: FACTURAS CON CÓDIGOS MTX ESPECIALES")
    print("   📄 Tipos: Todos los anteriores + códigos MTX")
    print("   ⚠️ Disponible: SOLO CASOS MUY ESPECÍFICOS")
    print("   🔐 Certificado: EL MISMO")
    print("   ⚙️ Estado: PENDIENTE DE HABILITAR ⚠️")

def verificar_tipo_cuit():
    """Cómo verificar qué tipo de CUIT tienes"""
    print(f"\n🔍 VERIFICAR TIPO DE CUIT")
    print("=" * 70)
    
    print(f"\n💡 ¿Cómo saber si necesitas WSFEXv1?")
    print("-" * 40)
    print("1. 📋 Si eres MONOTRIBUTISTA → SÍ necesitas WSFEXv1")
    print("2. 📋 Si eres RESPONSABLE INSCRIPTO → WSFEv1 es suficiente")
    print("3. 📋 Si EXPORTAS → SÍ necesitas WSFEXv1")
    print("4. 📋 Si emites facturas M → SÍ necesitas WSFEXv1")
    
    print(f"\n🔍 Verificar en AFIP:")
    print("1. Ir a 'Mi AFIP' → Datos del Contribuyente")
    print("2. Ver 'Impuestos y Regímenes':")
    print("   🔸 Si dice 'Monotributo' → necesitas WSFEXv1")
    print("   🔸 Si dice 'IVA Responsable Inscripto' → WSFEv1 suficiente")
    print("   🔸 Si dice 'Exportador' → necesitas WSFEXv1")

def errores_comunes():
    """Errores comunes y soluciones"""
    print(f"\n❌ ERRORES COMUNES Y SOLUCIONES")
    print("=" * 70)
    
    print(f"\n🚫 ERROR: 'HTTP 500 Internal Server Error'")
    print("💡 CAUSA: Servicio WSFEXv1 no habilitado")
    print("✅ SOLUCIÓN: Seguir PASO 1-4 de arriba")
    
    print(f"\n🚫 ERROR: 'Service not found' o 'Unauthorized'")
    print("💡 CAUSA: Certificado no asociado al servicio")
    print("✅ SOLUCIÓN: Repetir PASO 4 (asociar certificado)")
    
    print(f"\n🚫 ERROR: 'No se encuentra el servicio'")
    print("💡 CAUSA: El CUIT no cumple requisitos")
    print("✅ SOLUCIÓN: Verificar que seas Monotributista o Exportador")
    
    print(f"\n🚫 ERROR: 'Certificado vencido'")
    print("💡 CAUSA: Certificado expirado")
    print("✅ SOLUCIÓN: Renovar certificado en AFIP")

def resumen_final():
    """Resumen de lo que necesitas"""
    print(f"\n🎯 RESUMEN: QUÉ NECESITAS PARA WSFEXv1")
    print("=" * 70)
    
    print(f"\n✅ LO QUE YA TIENES:")
    print("🔐 Certificado digital (.crt y .key) ← EL MISMO")
    print("🔐 Acceso a AFIP con Clave Fiscal")
    print("🔐 WSFEv1 funcionando")
    
    print(f"\n⚙️ LO QUE NECESITAS CONFIGURAR:")
    print("📝 Habilitar servicio WSFEXv1 en AFIP")
    print("📝 Asociar tu certificado actual al nuevo servicio")
    print("📝 Verificar que tu CUIT sea Monotributo o Exportador")
    
    print(f"\n⏱️ TIEMPO ESTIMADO:")
    print("🕐 5-10 minutos en AFIP (si todo está bien)")
    print("🕐 24-48 horas para activación completa")
    
    print(f"\n💰 COSTO:")
    print("💰 GRATIS (no tiene costo adicional)")

def main():
    """Función principal"""
    guia_habilitar_wsfexv1()
    diferencias_servicios()
    verificar_tipo_cuit()
    errores_comunes()
    resumen_final()
    
    print(f"\n" + "="*70)
    print("🎉 CONCLUSIÓN")
    print("="*70)
    print("NO necesitas un certificado nuevo para WSFEXv1")
    print("Solo necesitas HABILITAR el servicio en AFIP")
    print("con el mismo certificado que ya tienes funcionando")
    print(f"\n🔗 ENLACE DIRECTO:")
    print("https://auth.afip.gob.ar/contribuyente_sin_clave")

if __name__ == "__main__":
    main()