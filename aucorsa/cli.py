#!/usr/bin/env python3
import argparse
import json
from dataclasses import asdict

from .client import AucorsaClient


def _print_json(payload):
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def cmd_estimate(args):
    client = AucorsaClient(debug=args.debug)
    result = client.estimate(
        visible_line=args.line,
        stop_id=args.stop,
        internal_line_id=args.line_id,
    )
    _print_json(asdict(result))


def cmd_estimate_stop(args):
    client = AucorsaClient(debug=args.debug)
    result = client.estimate_stop(stop_id=args.stop)
    _print_json(asdict(result))


def cmd_search_line(args):
    client = AucorsaClient(debug=args.debug)
    result = client.search_lines(term=args.term)
    _print_json([asdict(item) for item in result])


def cmd_search_stop(args):
    client = AucorsaClient(debug=args.debug)
    result = client.search_stops(term=args.term, line=args.line)
    _print_json([asdict(item) for item in result])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CLI para consultar tiempos de Aucorsa")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_estimate = subparsers.add_parser("estimate", help="Consultar tiempos de una línea y parada")
    p_estimate.add_argument("--line", required=True, help="Número visible de línea, ej. 12 o C2")
    p_estimate.add_argument("--stop", required=True, help="ID de parada, ej. 101")
    p_estimate.add_argument(
        "--line-id",
        help="ID interno opcional de línea para evitar la resolución automática",
    )
    p_estimate.add_argument("--debug", action="store_true", help="Mostrar logs de depuración")
    p_estimate.set_defaults(func=cmd_estimate)

    p_estimate_stop = subparsers.add_parser(
        "estimate-stop",
        help="Consultar todas las líneas disponibles en una parada",
    )
    p_estimate_stop.add_argument("--stop", required=True, help="ID de parada, ej. 101")
    p_estimate_stop.add_argument("--debug", action="store_true", help="Mostrar logs de depuración")
    p_estimate_stop.set_defaults(func=cmd_estimate_stop)

    p_search_line = subparsers.add_parser("search-line", help="Buscar líneas y sus IDs internos")
    p_search_line.add_argument("--term", required=True, help="Texto de búsqueda, ej. 12 o C2")
    p_search_line.add_argument("--debug", action="store_true", help="Mostrar logs de depuración")
    p_search_line.set_defaults(func=cmd_search_line)

    p_search_stop = subparsers.add_parser("search-stop", help="Buscar paradas por texto")
    p_search_stop.add_argument("--term", required=True, help="Texto de búsqueda, ej. Escultor")
    p_search_stop.add_argument(
        "--line",
        help="Filtrar por línea visible para limitar las paradas devueltas",
    )
    p_search_stop.add_argument("--debug", action="store_true", help="Mostrar logs de depuración")
    p_search_stop.set_defaults(func=cmd_search_stop)

    return parser


def main(argv: list[str] | None = None):
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
