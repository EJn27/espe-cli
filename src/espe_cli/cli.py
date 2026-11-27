import argparse
import sys
import webbrowser
from importlib.metadata import version
from pathlib import Path
from sqlite3 import Error as ErrorSQLite

from .configuracion import (
    calendario_guardado,
    guardar_calendario,
    guardar_nombre_materia,
    leer_nombres_materias,
)
from .entregas import ESTADOS, leer_estados, marcar_entrega
from .exportacion import exportar_vencimientos
from .tareas import mostrar_panel, mostrar_vencimientos

URL_MICAMPUS = "https://micampus.espe.edu.ec/"


def abrir_micampus() -> int:
    try:
        abierto = webbrowser.open(URL_MICAMPUS, new=2)
    except webbrowser.Error:
        abierto = False

    if abierto:
        print("Abriendo MiCampus en tu navegador.")
        return 0

    print(f"No se pudo abrir el navegador. Abre {URL_MICAMPUS}", file=sys.stderr)
    return 1


def usar_calendario(archivo: Path) -> int:
    try:
        ruta = guardar_calendario(archivo)
    except (OSError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1

    print(f"Calendario guardado en la configuración: {ruta}")
    return 0


def nombrar_materia(codigo: str, nombre: str) -> int:
    try:
        guardar_nombre_materia(codigo, nombre)
    except (OSError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1

    print(f"Nombre guardado para {codigo}: {nombre}")
    return 0


def resolver_calendario(archivo: Path | None, analizador: argparse.ArgumentParser) -> Path:
    try:
        archivo = archivo or calendario_guardado()
    except (OSError, ValueError):
        analizador.error(
            'No se pudo leer la configuración. Ejecuta espe calendario usar "ruta.ics".'
        )
    if archivo is None:
        analizador.error(
            'Elige un calendario con espe calendario usar "ruta.ics" o indica --archivo.'
        )
    return archivo


def preparar_consulta(
    archivo: Path | None, analizador: argparse.ArgumentParser
) -> tuple[Path, dict[str, str]]:
    archivo = resolver_calendario(archivo, analizador)
    try:
        nombres_materias = leer_nombres_materias()
    except (OSError, ValueError):
        print("No se pudieron leer los nombres guardados de las materias.", file=sys.stderr)
        nombres_materias = {}
    return archivo, nombres_materias


def principal() -> int:
    analizador = argparse.ArgumentParser(
        prog="espe",
        description="Asistente académico para estudiantes de la ESPE.",
    )
    analizador.add_argument(
        "--version",
        action="version",
        version=f"ESPE-CLI {version('espe-cli')}",
        help="Muestra la versión instalada.",
    )
    comandos = analizador.add_subparsers(dest="comando")
    comandos.add_parser("login", help="Abre el acceso oficial de MiCampus.")
    calendario = comandos.add_parser(
        "calendario", help="Configura el calendario local y los nombres de materias."
    )
    acciones_calendario = calendario.add_subparsers(dest="accion", required=True)
    usar = acciones_calendario.add_parser(
        "usar", help="Guarda la ruta del calendario habitual."
    )
    usar.add_argument("archivo", type=Path, help="Ruta al archivo .ics exportado.")
    nombrar = acciones_calendario.add_parser(
        "nombrar-materia", help="Guarda un nombre para un NRC o código con período."
    )
    nombrar.add_argument("codigo", type=str.strip, metavar="NRC")
    nombrar.add_argument("nombre", type=str.strip, help="Nombre que mostrará la CLI.")

    tareas = comandos.add_parser(
        "tareas", help="Lee vencimientos de un calendario de MiCampus."
    )
    tareas.add_argument(
        "--estados", action="store_true", help="Muestra el ID y el estado local de cada tarea."
    )
    tareas.add_argument(
        "--pendientes", action="store_true", help="Muestra las tareas que marcaste como pendientes."
    )
    entregas = comandos.add_parser(
        "entrega", help="Registra el estado de una tarea en este equipo."
    )
    acciones_entrega = entregas.add_subparsers(required=True)
    marcar = acciones_entrega.add_parser("marcar", help="Cambia el estado local de una tarea.")
    marcar.add_argument(
        "id_evento", type=str.strip, metavar="ID", help="ID de espe tareas --estados."
    )
    marcar.add_argument("estado", choices=ESTADOS)
    panel = comandos.add_parser(
        "dashboard", help="Resume los vencimientos de hoy y de los seis días siguientes."
    )
    exportar = comandos.add_parser(
        "exportar", help="Guarda todos los vencimientos del calendario en CSV o JSON."
    )
    exportar.add_argument("--formato", choices=("csv", "json"), required=True)
    exportar.add_argument(
        "--salida",
        type=Path,
        help="Destino del archivo. Por defecto, vencimientos.csv o vencimientos.json.",
    )
    for consulta in (tareas, panel, exportar, marcar):
        consulta.add_argument(
            "--archivo", type=Path, help="Lee este .ics en lugar del calendario guardado."
        )
    tareas.add_argument(
        "--materia",
        type=str.strip,
        metavar="NOMBRE_O_NRC",
        help="Filtra por nombre guardado, NRC (37824) o código con período (202651_37824).",
    )
    filtro_fechas = tareas.add_mutually_exclusive_group()
    filtro_fechas.add_argument(
        "--semana", action="store_true", help="Muestra la semana actual, de lunes a domingo."
    )
    filtro_fechas.add_argument(
        "--proximos",
        type=int,
        metavar="DÍAS",
        help="Muestra vencimientos desde ahora, contando hoy como el primer día.",
    )

    argumentos = analizador.parse_args()
    if argumentos.comando == "login":
        return abrir_micampus()
    if argumentos.comando == "calendario":
        if argumentos.accion == "nombrar-materia":
            return nombrar_materia(argumentos.codigo, argumentos.nombre)
        return usar_calendario(argumentos.archivo)
    if argumentos.comando == "dashboard":
        archivo, nombres_materias = preparar_consulta(argumentos.archivo, panel)
        return mostrar_panel(archivo, nombres_materias)
    if argumentos.comando == "exportar":
        archivo, nombres_materias = preparar_consulta(argumentos.archivo, exportar)
        salida = argumentos.salida or Path(f"vencimientos.{argumentos.formato}")
        return exportar_vencimientos(archivo, nombres_materias, argumentos.formato, salida)
    if argumentos.comando == "entrega":
        archivo = resolver_calendario(argumentos.archivo, marcar)
        return marcar_entrega(archivo, argumentos.id_evento, argumentos.estado)
    if argumentos.comando == "tareas":
        if argumentos.proximos is not None and argumentos.proximos < 1:
            tareas.error("--proximos requiere un número de días mayor que cero.")
        if argumentos.materia == "":
            tareas.error("--materia requiere un nombre, un NRC o un código con período.")
        archivo, nombres_materias = preparar_consulta(argumentos.archivo, tareas)
        estados = None
        if argumentos.estados or argumentos.pendientes:
            try:
                estados = leer_estados()
            except (OSError, ErrorSQLite):
                print("No se pudo leer el registro local de entregas.", file=sys.stderr)
                return 1
        return mostrar_vencimientos(
            archivo,
            argumentos.semana,
            proximos=argumentos.proximos,
            materia=argumentos.materia,
            nombres_materias=nombres_materias,
            estados=estados,
            pendientes=argumentos.pendientes,
        )

    analizador.print_help()
    return 0
