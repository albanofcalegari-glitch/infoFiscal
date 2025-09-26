#!/usr/bin/env python3
"""
InfoFiscal - Aplicacion principal para consultar facturas en ARCA
"""

import argparse
import sys
from typing import Optional
from .arca_client import ARCAClient
from .config import Config


def main():
    """Función principal de la aplicación"""
    parser = argparse.ArgumentParser(
        description="InfoFiscal - Consultar facturas en ARCA",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--cuit", 
        type=str, 
        help="CUIT del contribuyente a consultar"
    )
    
    parser.add_argument(
        "--fecha-desde",
        type=str,
        help="Fecha desde (formato: DD/MM/YYYY)"
    )
    
    parser.add_argument(
        "--fecha-hasta",
        type=str,
        help="Fecha hasta (formato: DD/MM/YYYY)"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        default="config.ini",
        help="Archivo de configuración (default: config.ini)"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        help="Archivo de salida (CSV o Excel)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Mostrar información detallada"
    )
    
    args = parser.parse_args()
    
    try:
        # Cargar configuración
        config = Config(args.config)
        
        # Crear cliente ARCA
        client = ARCAClient(config, verbose=args.verbose)
        
        # Obtener CUIT desde argumentos o configuración
        cuit = args.cuit or config.get_default_cuit()
        
        if not cuit:
            print("Error: Debe especificar un CUIT mediante --cuit o en el archivo de configuración")
            sys.exit(1)
        
        # Realizar consulta
        print(f"Consultando facturas para CUIT: {cuit}")
        
        if args.fecha_desde and args.fecha_hasta:
            print(f"Periodo: {args.fecha_desde} - {args.fecha_hasta}")
            facturas = client.consultar_facturas(
                cuit, 
                fecha_desde=args.fecha_desde,
                fecha_hasta=args.fecha_hasta
            )
        else:
            print("Consultando facturas del último mes")
            facturas = client.consultar_facturas(cuit)
        
        if not facturas:
            print("No se encontraron facturas para los criterios especificados")
            return
        
        print(f"Se encontraron {len(facturas)} facturas")
        
        # Mostrar resumen
        for i, factura in enumerate(facturas[:5], 1):  # Mostrar solo las primeras 5
            print(f"{i}. {factura}")
        
        if len(facturas) > 5:
            print(f"... y {len(facturas) - 5} facturas más")
        
        # Guardar resultados si se especifica archivo de salida
        if args.output:
            client.exportar_facturas(facturas, args.output)
            print(f"Resultados guardados en: {args.output}")
            
    except Exception as e:
        print(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()