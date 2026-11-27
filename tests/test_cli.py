import csv
import json
import os
import subprocess
import sysconfig
import tempfile
import unittest
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from icalendar import Calendar, Event

RAIZ = Path(__file__).resolve().parents[1]
DEMO = RAIZ / "ejemplos" / "calendario-demo.ics"
ID_DISENO = "demo-usabilidad-1@espe-cli.example.invalid"
ZONA = ZoneInfo("America/Guayaquil")


class PruebasCLI(unittest.TestCase):
    def setUp(self):
        temporal = tempfile.TemporaryDirectory(prefix="espe pruebas ")
        self.addCleanup(temporal.cleanup)
        self.directorio = Path(temporal.name)
        perfil = self.directorio / "perfil"
        self.entorno = {
            **os.environ,
            "LOCALAPPDATA": str(perfil),
            "XDG_CONFIG_HOME": str(perfil),
            "PYTHONIOENCODING": "utf-8",
        }
        ejecutable = "espe.exe" if os.name == "nt" else "espe"
        self.comando = Path(sysconfig.get_path("scripts")) / ejecutable

    def ejecutar(self, *argumentos, codigo=0):
        resultado = subprocess.run(
            [self.comando, *argumentos],
            cwd=self.directorio,
            env=self.entorno,
            capture_output=True,
            encoding="utf-8",
            timeout=20,
        )
        self.assertEqual(resultado.returncode, codigo, resultado)
        return resultado

    def test_lectura_del_calendario_demo(self):
        salida = self.ejecutar("tareas", "--archivo", DEMO, "--estados").stdout
        self.assertIn("29/11/2026  23:00  Vencimiento de Revisión del diseño", salida)
        self.assertIn("30/11/2026  23:00  Vencimiento de Prototipo web", salida)
        self.assertIn("02/12/2026  sin hora  Vencimiento de Informe de usabilidad", salida)
        self.assertIn(f"sin registrar | ID: {ID_DISENO}", salida)

    def test_filtros_y_panel_respetan_la_fecha_local(self):
        hoy = datetime.now(ZONA).date()
        calendario = Calendar()
        calendario.add("version", "2.0")
        calendario.add("prodid", "-//ESPE-CLI//Prueba//ES")
        for dias, titulo in (
            (0, "entrega de hoy"),
            (6, "último día"),
            (7, "fuera del rango"),
        ):
            evento = Event()
            dia = hoy + timedelta(days=dias)
            inicio = datetime.combine(dia, time(23, 59), ZONA).astimezone(timezone.utc)
            evento.add("uid", f"dia-{dias}@espe-cli.example.invalid")
            evento.add("dtstamp", datetime.now(timezone.utc))
            evento.add("dtstart", dia if dias == 0 else inicio)
            evento.add("summary", f"Vencimiento de {titulo}")
            evento.add("categories", ["202651_90001"])
            calendario.add_component(evento)
        ruta = self.directorio / "fechas.ics"
        ruta.write_bytes(calendario.to_ical())

        self.ejecutar("calendario", "usar", ruta)
        self.ejecutar("calendario", "nombrar-materia", "202651_90001", "Ingeniería")
        filtradas = self.ejecutar("tareas", "--proximos", "7", "--materia", "ingenieria").stdout
        self.assertIn("entrega de hoy", filtradas)
        self.assertIn("último día", filtradas)
        self.assertNotIn("fuera del rango", filtradas)

        panel = self.ejecutar("dashboard").stdout
        self.assertIn(f"Hoy, {hoy:%d/%m/%Y} (1)", panel)
        self.assertIn("último día  Ingeniería", panel)
        self.assertNotIn("fuera del rango", panel)

    def test_registro_local_conserva_el_estado(self):
        self.ejecutar("calendario", "usar", DEMO)
        self.ejecutar("entrega", "marcar", ID_DISENO, "pendiente")
        pendientes = self.ejecutar("tareas", "--pendientes", "--materia", "90001").stdout
        self.assertIn(f"pendiente | ID: {ID_DISENO}", pendientes)

        self.ejecutar("entrega", "marcar", ID_DISENO, "entregada")
        self.assertNotIn(ID_DISENO, self.ejecutar("tareas", "--pendientes").stdout)
        estados = self.ejecutar("tareas", "--estados").stdout
        self.assertIn(f"entregada | ID: {ID_DISENO}", estados)

        self.ejecutar("entrega", "marcar", ID_DISENO, "sin-registrar")
        estados = self.ejecutar("tareas", "--estados").stdout
        self.assertIn(f"sin registrar | ID: {ID_DISENO}", estados)

    def test_exportaciones_y_proteccion_del_destino(self):
        self.ejecutar("calendario", "usar", DEMO)
        self.ejecutar("calendario", "nombrar-materia", "202651_90001", "Diseño")
        self.ejecutar("exportar", "--formato", "csv")
        ruta_csv = self.directorio / "vencimientos.csv"
        with ruta_csv.open(encoding="utf-8-sig", newline="") as archivo:
            filas = list(csv.DictReader(archivo, delimiter=";"))
        self.assertEqual(len(filas), 3)
        self.assertEqual(filas[0]["fecha"], "2026-11-29")
        self.assertEqual(filas[0]["materias"], "Diseño")

        original = ruta_csv.read_bytes()
        self.ejecutar("exportar", "--formato", "csv", codigo=1)
        self.assertEqual(ruta_csv.read_bytes(), original)

        self.ejecutar("exportar", "--formato", "json")
        datos = json.loads((self.directorio / "vencimientos.json").read_text(encoding="utf-8"))
        self.assertEqual(datos["zona_horaria"], "America/Guayaquil")
        self.assertEqual(datos["vencimientos"][0]["nrcs"], ["90001"])
        self.assertIsNone(datos["vencimientos"][-1]["hora"])
