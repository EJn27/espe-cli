import json
import os
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

from .tareas import PATRON_CODIGO_MATERIA, cargar_calendario


def ruta_configuracion() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local"
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(base) / "ESPE-CLI" / "configuracion.json"


def calendario_guardado() -> Path | None:
    try:
        contenido = ruta_configuracion().read_text(encoding="utf-8")
    except FileNotFoundError:
        return None

    datos = json.loads(contenido)
    ruta = datos.get("archivo_calendario") if isinstance(datos, dict) else None
    if not isinstance(ruta, str) or not Path(ruta).is_absolute():
        raise ValueError("La configuración debe contener una ruta absoluta al calendario.")
    return Path(ruta)


def guardar_calendario(archivo: Path) -> Path:
    archivo = archivo.absolute()
    try:
        cargar_calendario(archivo)
    except OSError as error:
        raise OSError(f"No se pudo leer el calendario en {archivo}") from error
    except ValueError as error:
        raise ValueError("El archivo no contiene un calendario .ics válido.") from error

    contenido = json.dumps({"archivo_calendario": str(archivo)}, ensure_ascii=False)
    guardar_texto(ruta_configuracion(), contenido)
    return archivo


def guardar_texto(destino: Path, contenido: str) -> None:
    temporal = None
    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
        # Completa el archivo temporal antes de reemplazar la configuración anterior.
        with NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=destino.parent, delete=False
        ) as salida:
            temporal = Path(salida.name)
            salida.write(contenido)
        temporal.replace(destino)
        temporal = None
    except OSError as error:
        raise OSError(f"No se pudo guardar la configuración en {destino}") from error
    finally:
        if temporal is not None:
            temporal.unlink(missing_ok=True)


def guardar_nombre_materia(codigo: str, nombre: str) -> None:
    if not PATRON_CODIGO_MATERIA.fullmatch(codigo):
        raise ValueError("Indica un NRC (37824) o un código con período (202651_37824).")
    if not nombre or not nombre.isprintable() or PATRON_CODIGO_MATERIA.fullmatch(nombre):
        raise ValueError("Escribe un nombre de materia que se distinga de un NRC.")

    carpeta = ruta_configuracion().with_name("materias")
    guardar_texto(carpeta / f"{codigo}.txt", nombre)


def leer_nombres_materias() -> dict[str, str]:
    carpeta = ruta_configuracion().with_name("materias")
    try:
        archivos = list(carpeta.iterdir())
    except FileNotFoundError:
        return {}

    nombres = {}
    for archivo in archivos:
        if archivo.suffix == ".txt" and PATRON_CODIGO_MATERIA.fullmatch(archivo.stem):
            nombre = archivo.read_text(encoding="utf-8").strip()
            if nombre and nombre.isprintable():
                nombres[archivo.stem] = nombre
    return nombres
