# InfoFiscal

Aplicación en Python para consultar facturas en ARCA (Administración de Rentas de la Ciudad Autónoma de Buenos Aires)

## Descripción

InfoFiscal es una herramienta de línea de comandos que permite consultar y exportar información de facturas desde el sistema ARCA de manera automatizada.

## Características

- Consulta de facturas por CUIT
- Filtrado por rangos de fechas
- Exportación a CSV y Excel
- Configuración personalizable
- Validación de CUIT según algoritmo oficial
- Logging detallado para debugging

## Instalación

### Requisitos

- Python 3.7 o superior
- pip (gestor de paquetes de Python)

### Instalación desde el código fuente

```bash
# Clonar el repositorio
git clone https://github.com/albanofcalegari-glitch/infoFiscal.git
cd infoFiscal

# Instalar dependencias
pip install -r requirements.txt

# Instalar el paquete
pip install -e .
```

## Configuración

1. Copia el archivo de configuración de ejemplo:
```bash
cp config.example.ini config.ini
```

2. Edita `config.ini` según tus necesidades:
```ini
[DEFAULT]
cuit = 20123456789  # Tu CUIT por defecto (opcional)
output_format = csv  # Formato de salida preferido

[ARCA]
timeout = 30  # Timeout para conexiones
max_retries = 3  # Reintentos en caso de error
```

## Uso

### Línea de comandos

```bash
# Consultar facturas para un CUIT específico
infofiscal --cuit 20123456789

# Consultar facturas en un rango de fechas
infofiscal --cuit 20123456789 --fecha-desde 01/01/2023 --fecha-hasta 31/12/2023

# Exportar resultados a Excel
infofiscal --cuit 20123456789 --output facturas.xlsx

# Mostrar información detallada
infofiscal --cuit 20123456789 --verbose

# Usar archivo de configuración personalizado
infofiscal --config mi_config.ini --cuit 20123456789
```

### Como módulo de Python

```python
from infofiscal import ARCAClient, Config

# Crear cliente
config = Config('config.ini')
client = ARCAClient(config)

# Consultar facturas
facturas = client.consultar_facturas('20123456789')

# Exportar a archivo
client.exportar_facturas(facturas, 'facturas.csv')
```

## Opciones de línea de comandos

| Opción | Descripción |
|--------|-------------|
| `--cuit` | CUIT del contribuyente a consultar |
| `--fecha-desde` | Fecha inicial (formato: DD/MM/YYYY) |
| `--fecha-hasta` | Fecha final (formato: DD/MM/YYYY) |
| `--config` | Archivo de configuración (default: config.ini) |
| `--output` | Archivo de salida (CSV o Excel) |
| `--verbose, -v` | Mostrar información detallada |

## Formatos soportados

- **CSV**: Formato de texto separado por comas
- **Excel**: Formato XLSX de Microsoft Excel

## Desarrollo

### Estructura del proyecto

```
infoFiscal/
├── infofiscal/
│   ├── __init__.py
│   ├── main.py          # Punto de entrada principal
│   ├── arca_client.py   # Cliente para interactuar con ARCA
│   ├── config.py        # Manejo de configuración
│   └── models.py        # Modelos de datos
├── config.example.ini   # Archivo de configuración de ejemplo
├── requirements.txt     # Dependencias del proyecto
├── setup.py            # Configuración del paquete
└── README.md           # Documentación
```

### Ejecutar en modo desarrollo

```bash
python -m infofiscal.main --help
```

## Contribuir

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crea un Pull Request

## Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo LICENSE para más detalles.

## Soporte

Para reportar bugs o solicitar nuevas funcionalidades, por favor crea un issue en GitHub.

## Disclaimer

Esta herramienta es para uso educativo y personal. Asegúrate de cumplir con los términos de uso del sitio web de ARCA al utilizar esta aplicación.
