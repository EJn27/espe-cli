import csv
import json
import sys
from io import StringIO
from pathlib import Path
from zoneinfo import ZoneInfo

from .tareas import ZONA_ECUADOR, consultar_vencimientos, informar_omisiones

CAMPOS_CSV = ("fecha", "hora", "titulo", "materias", "nrcs", "codigos_materia")


def celda_csv(valor: str | list[str] | None) -> str:
    texto = " | ".join(valor) if isinstance(valor, list) else (valor or "")
    # Mantiene como texto los valores que una hoja de cálculo podría tratar como fórmulas.
    parece_formula = texto.lstrip().startswith(("=", "+", "-", "@", "＝", "＋", "－", "＠"))
    if parece_formula or texto.startswith(("\t", "\r", "\n")):
        return "'" + texto
    return texto


def guardar_archivo_nuevo(ruta: Path, contenido: bytes) -> None:
    creado = False
    try:
        with ruta.open("xb") as salida:
            creado = True
            salida.write(contenido)
    except OSError:
        if creado:
            ruta.unlink(missing_ok=True)
        raise


def exportar_vencimientos(
    archivo: Path, nombres_materias: dict[str, str], formato: str, salida: Path
) -> int:
    consulta = consultar_vencimientos(archivo, ZoneInfo(ZONA_ECUADOR))
    if consulta is None:
        return 1
    vencimientos, omitidos = consulta
    registros = [
        {
            "fecha": entrega.dia.isoformat(),
            "hora": entrega.hora.isoformat() if entrega.hora is not None else None,
            "titulo": entrega.titulo,
            "materias": list(entrega.nombres_materias(nombres_materias)),
            "nrcs": list(entrega.nrcs),
            "codigos_materia": list(entrega.codigos_materia),
        }
        for entrega in vencimientos
    ]

    if formato == "csv":
        texto = StringIO(newline="")
        escritor = csv.writer(texto, delimiter=";", quoting=csv.QUOTE_ALL)
        escritor.writerow(CAMPOS_CSV)
        escritor.writerows(
            [celda_csv(registro[campo]) for campo in CAMPOS_CSV] for registro in registros
        )
        contenido = texto.getvalue().encode("utf-8-sig")
    else:
        datos = {"zona_horaria": ZONA_ECUADOR, "vencimientos": registros}
        contenido = (json.dumps(datos, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

    try:
        guardar_archivo_nuevo(salida, contenido)
    except FileExistsError:
        print(f"El archivo ya existe: {salida}. Elige otro nombre con --salida.", file=sys.stderr)
        return 1
    except OSError:
        print(f"No se pudo escribir en {salida}. Revisa la ruta y los permisos.", file=sys.stderr)
        return 1

    print(f"Vencimientos exportados: {len(registros)}. Archivo: {salida.absolute()}")
    informar_omisiones(omitidos)
    return 0
