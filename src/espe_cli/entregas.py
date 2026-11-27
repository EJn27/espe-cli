import sqlite3
import sys
from contextlib import closing
from pathlib import Path
from zoneinfo import ZoneInfo

from .configuracion import ruta_configuracion
from .tareas import ZONA_ECUADOR, consultar_vencimientos

ESTADOS = ("pendiente", "entregada", "sin-registrar")


def ruta_registro() -> Path:
    return ruta_configuracion().with_name("entregas.sqlite3")


def leer_estados() -> dict[str, str]:
    ruta = ruta_registro()
    try:
        ruta.stat()
    except FileNotFoundError:
        return {}

    uri = f"{ruta.absolute().as_uri()}?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as registro:
        existe_tabla = registro.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'entregas'"
        ).fetchone()
        if existe_tabla is None:
            return {}
        return dict(registro.execute("SELECT uid, estado FROM entregas"))


def guardar_estado(uid: str, estado: str) -> None:
    ruta = ruta_registro()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(ruta)) as registro, registro:
        registro.execute(
            """
            CREATE TABLE IF NOT EXISTS entregas (
                uid TEXT PRIMARY KEY NOT NULL,
                estado TEXT NOT NULL CHECK (estado IN ('pendiente', 'entregada'))
            )
            """
        )
        if estado == "sin-registrar":
            registro.execute("DELETE FROM entregas WHERE uid = ?", (uid,))
        else:
            registro.execute(
                """
                INSERT INTO entregas (uid, estado) VALUES (?, ?)
                ON CONFLICT(uid) DO UPDATE SET estado = excluded.estado
                """,
                (uid, estado),
            )


def marcar_entrega(archivo: Path, uid: str, estado: str) -> int:
    consulta = consultar_vencimientos(archivo, ZoneInfo(ZONA_ECUADOR))
    if consulta is None:
        return 1
    vencimientos, _ = consulta
    entrega = next((entrega for entrega in vencimientos if uid and entrega.uid == uid), None)
    if entrega is None:
        print(
            "El ID no aparece en el calendario. Consulta espe tareas --estados.", file=sys.stderr
        )
        return 1

    try:
        guardar_estado(uid, estado)
    except (OSError, sqlite3.Error):
        print("No se pudo actualizar el registro local de entregas.", file=sys.stderr)
        return 1

    estado_visible = estado.replace("-", " ")
    print(f"{entrega.titulo} | Estado local: {estado_visible}")
    return 0
