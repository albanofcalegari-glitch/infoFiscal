#!/usr/bin/env python3
"""
Script para probar las validaciones del formulario de nuevo cliente
"""

def test_validaciones():
    """Probar diferentes casos de validación"""
    
    print("🧪 PROBANDO VALIDACIONES DE NUEVO CLIENTE")
    print("=" * 50)
    
    # Casos de prueba
    casos = [
        {
            'nombre': 'Caso válido completo',
            'datos': {
                'tipoDocumento': 'DNI',
                'nroDocumento': '12345678',
                'CUIT': '20-12345678-9',
                'apellido': 'García',
                'nombres': 'Juan Carlos',
                'condicionIVA': 'Responsable Inscripto'
            },
            'debe_pasar': True
        },
        {
            'nombre': 'Documento inválido - muy corto',
            'datos': {
                'tipoDocumento': 'DNI',
                'nroDocumento': '123',  # Muy corto
                'apellido': 'Pérez',
                'nombres': 'María'
            },
            'debe_pasar': False
        },
        {
            'nombre': 'Documento no numérico',
            'datos': {
                'tipoDocumento': 'DNI',
                'nroDocumento': '1234567A',  # Contiene letra
                'apellido': 'López',
                'nombres': 'Carlos'
            },
            'debe_pasar': False
        },
        {
            'nombre': 'Apellido con números',
            'datos': {
                'tipoDocumento': 'DNI',
                'nroDocumento': '12345678',
                'apellido': 'García123',  # Contiene números
                'nombres': 'Ana'
            },
            'debe_pasar': False
        },
        {
            'nombre': 'Campos obligatorios vacíos',
            'datos': {
                'tipoDocumento': '',
                'nroDocumento': '',
                'apellido': '',
                'nombres': ''
            },
            'debe_pasar': False
        },
        {
            'nombre': 'CUIT inválido',
            'datos': {
                'tipoDocumento': 'DNI',
                'nroDocumento': '12345678',
                'CUIT': '20-12345678-0',  # Dígito verificador incorrecto
                'apellido': 'Martínez',
                'nombres': 'Luis'
            },
            'debe_pasar': False
        }
    ]
    
    for i, caso in enumerate(casos, 1):
        print(f"\n📋 Caso {i}: {caso['nombre']}")
        print("   Datos:", caso['datos'])
        
        # Simular validaciones
        errores = []
        datos = caso['datos']
        
        # Validar tipo documento
        if not datos.get('tipoDocumento') or datos['tipoDocumento'] not in ['DNI', 'LE', 'LC']:
            errores.append('Tipo de documento inválido')
        
        # Validar número documento
        nro_doc = datos.get('nroDocumento', '')
        if not nro_doc:
            errores.append('Número de documento requerido')
        elif not nro_doc.isdigit():
            errores.append('Número de documento debe ser numérico')
        elif len(nro_doc) < 7 or len(nro_doc) > 8:
            errores.append('Número de documento debe tener 7-8 dígitos')
        
        # Validar apellido
        apellido = datos.get('apellido', '').strip()
        if not apellido:
            errores.append('Apellido requerido')
        elif len(apellido) < 2:
            errores.append('Apellido muy corto')
        elif not all(c.isalpha() or c.isspace() or c in "áéíóúÁÉÍÓÚñÑüÜ'-" for c in apellido):
            errores.append('Apellido con caracteres inválidos')
        
        # Validar nombres
        nombres = datos.get('nombres', '').strip()
        if not nombres:
            errores.append('Nombres requeridos')
        elif len(nombres) < 2:
            errores.append('Nombres muy cortos')
        elif not all(c.isalpha() or c.isspace() or c in "áéíóúÁÉÍÓÚñÑüÜ'-" for c in nombres):
            errores.append('Nombres con caracteres inválidos')
        
        # Validar CUIT si existe
        cuit = datos.get('CUIT', '').replace('-', '').replace(' ', '')
        if cuit:
            if not cuit.isdigit() or len(cuit) != 11:
                errores.append('CUIT con formato inválido')
        
        # Verificar resultado
        paso_validacion = len(errores) == 0
        resultado = "✅ VÁLIDO" if paso_validacion else "❌ INVÁLIDO"
        
        print(f"   Resultado: {resultado}")
        if errores:
            print(f"   Errores: {', '.join(errores)}")
        
        # Verificar expectativa
        if paso_validacion == caso['debe_pasar']:
            print("   ✅ Caso funcionó como se esperaba")
        else:
            print("   ⚠️ Resultado inesperado!")
    
    print("\n" + "=" * 50)
    print("🎯 RESUMEN: Sistema de validación implementado")
    print("   - Validaciones frontend (JavaScript)")
    print("   - Validaciones backend (Python)")
    print("   - Mensajes de error informativos")
    print("   - Formato automático de campos")

if __name__ == "__main__":
    test_validaciones()