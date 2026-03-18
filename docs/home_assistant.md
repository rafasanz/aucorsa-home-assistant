# Home Assistant: integración, panel y tarjeta

La integración vive en `custom_components/aucorsa/` y ahora incluye también el frontend necesario dentro de:

```text
custom_components/aucorsa/static/aucorsa-panel.js
```

Eso permite que la propia integración sirva el JS desde:

```text
/api/aucorsa/static/aucorsa-panel.js
```

## Qué aporta la integración

- Configuración desde `Devices & Services`
- Sensores de:
  - nombre de parada
  - próximo autobús
  - siguiente autobús
- Botón de refresco manual por parada configurada
- Tarjeta Lovelace `custom:aucorsa-card`
- Panel lateral `panel_custom`

## Instalación manual

1. Copia `custom_components/aucorsa/` a:

```text
<config>/custom_components/aucorsa/
```

2. Reinicia Home Assistant.

3. Añade la integración desde:

```text
Settings > Devices & Services > Add Integration > Aucorsa
```

## Instalación con HACS

Mientras el repositorio no esté en la lista por defecto de HACS, puedes instalarlo como repositorio personalizado:

1. Abre HACS.
2. Ve al menú de tres puntos.
3. Entra en `Custom repositories`.
4. Añade `https://github.com/rafasanz/aucorsa-home-assistant`.
5. Elige tipo `Integration`.
6. Instala `Aucorsa`.
7. Reinicia Home Assistant.

## Cuando esté aprobado en HACS

Cuando el repositorio entre en los repositorios por defecto de HACS, ya no tendrás que añadirlo como repositorio personalizado:

1. Abre HACS.
2. Ve a `Integrations`.
3. Busca `Aucorsa`.
4. Instala la integración.
5. Reinicia Home Assistant.

## Cómo solicitar inclusión en HACS

Según la documentación oficial de HACS, para pedir inclusión en los repositorios por defecto:

1. El repositorio debe ser público en GitHub.
2. Debe pasar `HACS Action`.
3. Debe pasar `Hassfest`.
4. Debe tener al menos una GitHub Release pública.
5. Debe poder añadirse ya como `custom repository`.
6. Después hay que abrir un PR en `hacs/default` y añadir el repositorio en la lista de `integration`, en orden alfabético.

Referencias oficiales:

- `https://www.hacs.xyz/docs/publish/start/`
- `https://www.hacs.xyz/docs/publish/include/`

## Configurar el panel lateral

Ejemplo:

```yaml
panel_custom:
  - name: aucorsa-panel
    sidebar_title: Aucorsa
    sidebar_icon: mdi:bus-clock
    url_path: aucorsa
    module_url: /api/aucorsa/static/aucorsa-panel.js
    config:
      title: Aucorsa
      subtitle: Tiempos de llegada por parada
```

Si quieres filtrar solo ciertas paradas:

```yaml
panel_custom:
  - name: aucorsa-panel
    sidebar_title: Aucorsa
    sidebar_icon: mdi:bus-clock
    url_path: aucorsa
    module_url: /api/aucorsa/static/aucorsa-panel.js
    config:
      stop_ids:
        - "72"
        - "101"
```

También tienes un ejemplo en [panel_custom.yaml.example](../examples/panel_custom.yaml.example).

## Configurar la tarjeta Lovelace

Añade el recurso:

```yaml
lovelace:
  resources:
    - url: /api/aucorsa/static/aucorsa-panel.js
      type: module
```

Luego puedes añadir `custom:aucorsa-card` desde el editor visual o con YAML:

```yaml
type: custom:aucorsa-card
stop_id: "101"
title: Aucorsa
subtitle: Tiempos de llegada por parada
show_header: true
show_refresh: true
```

## Comportamiento del frontend

- El panel agrupa líneas por parada.
- La tarjeta muestra una sola parada por instancia.
- El botón de refresco es un icono con `hover` de `Actualizar ahora`.
- El panel lateral muestra un pie con `@rafasanz` y versión.
- La tarjeta usa el logo de Aucorsa por defecto si no se ha definido un título personalizado.

## Capturas

Puedes guardar capturas del panel y de la tarjeta en:

```text
docs/images/
```

Y enlazarlas luego desde este documento y desde el README del repositorio.
