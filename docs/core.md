# Core Python y CLI

El directorio `aucorsa/` contiene el cliente Python reutilizable sobre el que se apoya la integración de Home Assistant.

## Archivos principales

```text
aucorsa/
    client.py
    cli.py
    lines.py
    models.py
    parser.py
aucorsa_cli.py
tests/
```

## Responsabilidades

- `client.py`: orquesta peticiones, resolución de línea y consulta de estimaciones.
- `parser.py`: convierte HTML en datos estructurados.
- `models.py`: modelos tipados del dominio.
- `lines.py`: ayuda a localizar la línea correcta.
- `cli.py`: comandos para probar el flujo desde terminal.

## Comandos útiles

```powershell
python aucorsa_cli.py estimate --line 12 --stop 101
python aucorsa_cli.py estimate-stop --stop 101
python aucorsa_cli.py search-line --term 46
python aucorsa_cli.py search-stop --term Escultor --line 12
python aucorsa_cli.py estimate --line 12 --stop 101 --debug
```

## Pruebas

```powershell
python -m unittest tests.test_parser
```

## Por qué mantener este core separado

- Permite depurar la parte de AUCORSA fuera de Home Assistant.
- Facilita probar cambios del parser sin reiniciar Home Assistant.
- Hace posible reutilizar la lógica en CLI, scripts o futuras integraciones.
