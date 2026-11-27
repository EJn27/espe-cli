import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from unicodedata import combining, normalize
from zoneinfo import ZoneInfo

from icalendar import Calendar

ZONA_ECUADOR = "America/Guayaquil"
PATRON_CODIGO_MATERIA = re.compile(r"(?:[0-9]{6}_)?[0-9]{5}")


@dataclass(frozen=True)
class Vencimiento:
    dia: date
    hora: time | None
    titulo: str
    codigos_materia: tuple[str, ...]
    uid: str = ""

    @property
    def nrcs(self) -> tuple[str, ...]:
        return tuple(sorted({codigo.rsplit("_", 1)[-1] for codigo in self.codigos_materia}))

    def nombres_materias(self, nombres_por_codigo: dict[str, str]) -> tuple[str, ...]:
        nombres = (
            nombres_por_codigo.get(codigo) or nombres_por_codigo.get(codigo.rsplit("_", 1)[-1])
            for codigo in self.codigos_materia
        )
        return tuple(dict.fromkeys(nombre for nombre in nombres if nombre))


def normalizar_nombre(nombre: str) -> str:
    descompuesto = normalize("NFD", nombre.casefold())
    sin_tildes = "".join(letra for letra in descompuesto if not combining(letra))
    return " ".join(sin_tildes.split())


def cargar_calendario(archivo: Path) -> Calendar:
    calendario = Calendar.from_ical(archivo.read_bytes())
    if not isinstance(calendario, Calendar):
        raise ValueError("Se esperaba un calendario completo.")
    return calendario


def leer_vencimientos(
    archivo: Path, zona: ZoneInfo
) -> tuple[list[Vencimiento], int]:
    calendario = cargar_calendario(archivo)
    vencimientos = []
    omitidos = 0
    for evento in calendario.walk("VEVENT"):
        titulo = str(evento.get("SUMMARY", "")).strip()
        if not titulo.casefold().startswith("vencimiento de "):
            continue

        # MiCampus exporta el vencimiento como la fecha de inicio del evento.
        propiedad_fecha = evento.get("DTSTART")
        try:
            fecha = getattr(propiedad_fecha, "dt", None)
        except ValueError:
            fecha = None

        if isinstance(fecha, datetime):
            if fecha.tzinfo is not None:
                fecha = fecha.astimezone(zona)
            elif "TZID" in propiedad_fecha.params:
                omitidos += 1
                continue
            dia, hora = fecha.date(), fecha.time()
        elif isinstance(fecha, date):
            dia, hora = fecha, None
        else:
            omitidos += 1
            continue

        categorias = (texto.strip() for texto in evento.categories)
        codigos_materia = tuple(
            sorted({codigo for codigo in categorias if PATRON_CODIGO_MATERIA.fullmatch(codigo)})
        )
        uid = str(evento.get("UID", "")).strip()
        identificador = uid if uid.isprintable() else ""
        vencimientos.append(Vencimiento(dia, hora, titulo, codigos_materia, identificador))

    vencimientos.sort(key=lambda entrega: (entrega.dia, entrega.hora or time.min))
    return vencimientos, omitidos


def consultar_vencimientos(
    archivo: Path, zona: ZoneInfo
) -> tuple[list[Vencimiento], int] | None:
    try:
        return leer_vencimientos(archivo, zona)
    except OSError:
        print(
            f"No se pudo leer el archivo. Revisa la ruta y los permisos de {archivo}",
            file=sys.stderr,
        )
    except ValueError:
        print(
            "No se pudo interpretar el calendario. Exporta de nuevo el archivo .ics desde MiCampus.",
            file=sys.stderr,
        )
    return None


def imprimir_vencimientos(
    vencimientos: list[Vencimiento],
    nombres_materias: dict[str, str],
    estados: dict[str, str] | None = None,
) -> None:
    for entrega in vencimientos:
        hora = entrega.hora.strftime("%H:%M") if entrega.hora is not None else "sin hora"
        nrcs = ", ".join(entrega.nrcs)
        materia_texto = f"  [NRC {nrcs}]" if nrcs else ""
        nombres = " / ".join(entrega.nombres_materias(nombres_materias))
        nombre_texto = f"  {nombres}" if nombres else ""
        linea = f"{entrega.dia:%d/%m/%Y}  {hora}  {entrega.titulo}{nombre_texto}{materia_texto}"
        if estados is not None:
            estado = estados.get(entrega.uid, "sin registrar")
            identificador = entrega.uid or "sin ID"
            linea += f"  [Estado local: {estado} | ID: {identificador}]"
        print(linea)


def informar_omisiones(omitidos: int) -> None:
    if omitidos:
        print(
            f"Vencimientos omitidos por fecha inválida o no disponible: {omitidos}",
            file=sys.stderr,
        )


def mostrar_vencimientos(
    archivo: Path,
    semana: bool,
    *,
    proximos: int | None = None,
    materia: str | None = None,
    nombres_materias: dict[str, str] | None = None,
    estados: dict[str, str] | None = None,
    pendientes: bool = False,
) -> int:
    zona = ZoneInfo(ZONA_ECUADOR)
    consulta = consultar_vencimientos(archivo, zona)
    if consulta is None:
        return 1
    vencimientos, omitidos = consulta

    if pendientes:
        estados = estados or {}
        vencimientos = [
            entrega for entrega in vencimientos if estados.get(entrega.uid) == "pendiente"
        ]

    nombres_materias = nombres_materias or {}
    if materia is not None and PATRON_CODIGO_MATERIA.fullmatch(materia):
        vencimientos = [
            entrega
            for entrega in vencimientos
            if materia in entrega.codigos_materia or materia in entrega.nrcs
        ]
    elif materia is not None:
        nombre_buscado = normalizar_nombre(materia)
        vencimientos = [
            entrega
            for entrega in vencimientos
            if any(
                normalizar_nombre(nombre) == nombre_buscado
                for nombre in entrega.nombres_materias(nombres_materias)
            )
        ]

    if semana:
        hoy = datetime.now(zona).date()
        lunes = hoy - timedelta(days=hoy.weekday())
        proximo_lunes = lunes + timedelta(days=7)
        vencimientos = [
            entrega for entrega in vencimientos if lunes <= entrega.dia < proximo_lunes
        ]
    elif proximos is not None:
        ahora = datetime.now(zona)
        hoy = ahora.date()
        hora_actual = ahora.time()
        vencimientos = [
            entrega
            for entrega in vencimientos
            if 0 <= (entrega.dia - hoy).days < proximos
            and (entrega.dia != hoy or entrega.hora is None or entrega.hora >= hora_actual)
        ]

    if vencimientos:
        print("Vencimientos de MiCampus (hora de Ecuador continental)")
        imprimir_vencimientos(vencimientos, nombres_materias, estados)
    elif pendientes:
        print("No se encontraron tareas marcadas como pendientes con los filtros indicados.")
    elif materia is not None:
        print(
            f"No se encontraron vencimientos para la materia {materia} con los filtros indicados."
        )
    elif semana:
        print("No se encontraron vencimientos para la semana actual.")
    elif proximos is not None:
        print("No se encontraron vencimientos para los días indicados.")
    else:
        print("No se encontraron vencimientos en el archivo.")

    informar_omisiones(omitidos)
    return 0


def mostrar_panel(archivo: Path, nombres_materias: dict[str, str]) -> int:
    zona = ZoneInfo(ZONA_ECUADOR)
    consulta = consultar_vencimientos(archivo, zona)
    if consulta is None:
        return 1
    vencimientos, omitidos = consulta

    hoy = datetime.now(zona).date()
    manana = hoy + timedelta(days=1)
    ultimo_dia = hoy + timedelta(days=6)
    de_hoy = [entrega for entrega in vencimientos if entrega.dia == hoy]
    siguientes = [entrega for entrega in vencimientos if manana <= entrega.dia <= ultimo_dia]
    secciones = (
        (f"Hoy, {hoy:%d/%m/%Y}", de_hoy),
        (f"Del {manana:%d/%m/%Y} al {ultimo_dia:%d/%m/%Y}", siguientes),
    )

    print("ESPE-CLI | Vencimientos de MiCampus (hora de Ecuador continental)")
    for titulo, entregas in secciones:
        print(f"\n{titulo} ({len(entregas)})")
        if entregas:
            imprimir_vencimientos(entregas, nombres_materias)
        else:
            print("Sin vencimientos en el calendario exportado.")
    informar_omisiones(omitidos)
    return 0
