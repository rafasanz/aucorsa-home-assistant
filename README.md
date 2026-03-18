# Aucorsa for Home Assistant

Integración no oficial para Home Assistant y cliente Python para consultar tiempos de llegada de AUCORSA en Córdoba.

El repositorio queda dividido en tres bloques claros:

- `aucorsa/`: cliente Python y CLI para entender y probar la API web de AUCORSA.
- `custom_components/aucorsa/`: integración de Home Assistant lista para instalar.
- `docs/`: documentación de API, core, HACS y frontend.

## Estructura

```text
aucorsa/                     Cliente Python reutilizable
custom_components/aucorsa/   Integración Home Assistant
docs/                        Guías y documentación
examples/                    Ejemplos de configuración
tests/                       Pruebas del parser
```

## Qué incluye

- Config flow para añadir línea y parada desde Home Assistant.
- Sensores para nombre de parada, próximo autobús y siguiente autobús.
- Botón de refresco manual por entrada.
- Panel lateral visual de Aucorsa.
- Tarjeta Lovelace `custom:aucorsa-card` con editor visual.
- Frontend servido por la propia integración, sin depender de `/www`.
- Política de peticiones conservadora para no castigar la web de AUCORSA.

## Documentación

- [API de AUCORSA](docs/api.md)
- [Core Python y CLI](docs/core.md)
- [Home Assistant: integración, panel y tarjeta](docs/home_assistant.md)
- [Ejemplo de `panel_custom`](examples/panel_custom.yaml.example)

## Instalación rápida del core Python

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

Comandos útiles:

```powershell
python aucorsa_cli.py estimate --line 12 --stop 101
python aucorsa_cli.py estimate-stop --stop 101
python aucorsa_cli.py search-line --term 46
python aucorsa_cli.py search-stop --term Escultor --line 12
python -m unittest tests.test_parser
```

## Instalación manual en Home Assistant

1. Copia `custom_components/aucorsa/` dentro de tu carpeta de configuración.
2. Reinicia Home Assistant.
3. Ve a `Settings > Devices & Services > Add Integration`.
4. Busca `Aucorsa`.
5. Configura línea, parada e intervalo.

Para usar el panel y la tarjeta, la integración ya expone su frontend en:

```text
/api/aucorsa/static/aucorsa-panel.js
```

Eso permite usar:

- `panel_custom` con `module_url: /api/aucorsa/static/aucorsa-panel.js`
- recurso Lovelace con `url: /api/aucorsa/static/aucorsa-panel.js`

## Versionado

- La versión de la integración se toma de `custom_components/aucorsa/manifest.json`.
- El paquete Python `aucorsa-api` usa esa misma versión de forma dinámica.
- Para publicar una versión en HACS, crea el tag y la GitHub Release con el mismo número.
