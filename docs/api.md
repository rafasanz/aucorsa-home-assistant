# API de AUCORSA

Este proyecto no usa una API pública documentada por AUCORSA. El flujo actual se basa en la web de tiempos de paso y en sus llamadas internas.

## Flujo actual

1. Se descarga la página pública de tiempos de paso.
2. Se extrae el `_wpnonce` y el contexto necesario.
3. Se resuelve el identificador interno de la línea a partir del número visible.
4. Se consulta el endpoint interno de estimaciones.
5. Se parsea la respuesta HTML y se devuelve una estructura Python o JSON.

## Datos principales que obtenemos

- `stop_id`
- `line`
- `internal_line_id`
- `stop_label`
- `route`
- `next_bus_min`
- `following_bus_min`

## Ejemplo de salida

```json
{
  "stop_id": "101",
  "line": "12",
  "internal_line_id": "763",
  "stop_label": "Parada 101: Escultor Ramon Barba 1ª D.C.",
  "route": "NARANJO - TENDILLAS - SECTOR SUR",
  "next_bus_min": 14,
  "following_bus_min": 30
}
```

## Limitaciones

- AUCORSA puede cambiar su HTML o sus endpoints internos sin previo aviso.
- Los minutos cambian continuamente, así que no hay una salida fija.
- Conviene tratar este acceso como un scraping controlado, no como una API estable.

## Uso responsable

- No hagas polling agresivo.
- No bajes de `30 s` en despliegues reales.
- Reutiliza datos en memoria siempre que sea posible.
