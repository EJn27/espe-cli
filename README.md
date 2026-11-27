# ESPE-CLI

ESPE-CLI es un asistente académico local para estudiantes de la ESPE. Lee el calendario `.ics` exportado desde MiCampus, muestra vencimientos en hora de Ecuador continental y permite registrar entregas de forma manual.

La versión `1.0.0` es la primera versión estable. `espe login` abre MiCampus en el navegador. Para consultar las fechas, descarga una exportación desde **Calendario → Exportar calendario** en MiCampus.

## Instalar en Windows

Necesitas Python 3.12 o posterior. Abre CMD o PowerShell en la carpeta del proyecto, donde está `pyproject.toml`. Ejecuta cada bloque por separado. Usa la versión de Python que tengas instalada si es diferente de 3.15.

```bat
py -3.15 -m venv .venv
```

```bat
.\.venv\Scripts\python.exe -m pip install .
```

```bat
.\.venv\Scripts\espe.exe --version
```

Este último comando debe mostrar `ESPE-CLI 1.0.0`.

## Probar con datos ficticios

Desde la carpeta del proyecto, ejecuta la consulta con el calendario de ejemplo. Este comando usa el ejemplo solo para esa consulta.

```bat
.\.venv\Scripts\espe.exe tareas --archivo ejemplos\calendario-demo.ics --estados
```

Deberías ver tres vencimientos. El evento de revisión del diseño figura en UTC como `20261130T040000Z` y se muestra como **29/11/2026 a las 23:00** en Ecuador continental. Los filtros de fechas se calculan a partir del día en que ejecutas el comando y los datos del ejemplo tienen fechas fijas.

## Usar tu calendario de MiCampus

Para usar el comando corto `espe`, activa el entorno con `.venv\Scripts\activate.bat` en CMD o `.\.venv\Scripts\Activate.ps1` en PowerShell. También puedes ejecutar `.\.venv\Scripts\espe.exe` en cualquiera de las dos terminales.

Guarda la ruta de tu exportación. Sustituye la ruta del ejemplo por la ubicación de tu archivo.

```bat
espe calendario usar "C:\Users\Usuario\Downloads\calendario.ics"
```

| Comando | Resultado |
|---|---|
| `espe login` | Abre el portal de MiCampus en el navegador. |
| `espe tareas` | Muestra los vencimientos del calendario guardado. |
| `espe tareas --semana` | Muestra la semana actual, de lunes a domingo. |
| `espe tareas --proximos 7` | Muestra lo que vence desde ahora hasta el final del sexto día siguiente. |
| `espe tareas --materia 90001` | Filtra por NRC. También acepta el código con período o el nombre guardado. |
| `espe calendario nombrar-materia 202651_90001 "Usabilidad"` | Guarda un nombre local para el NRC de ese período. |
| `espe dashboard` | Resume los vencimientos de hoy y de los seis días siguientes. |
| `espe tareas --estados` | Muestra el identificador y el estado local de cada tarea. |
| `espe entrega marcar "ID" entregada` | Registra una entrega después de que la hayas enviado en MiCampus. Usa el ID que muestra `--estados`. |
| `espe tareas --pendientes` | Muestra las tareas que marcaste como `pendiente`. |
| `espe exportar --formato csv` | Exporta todos los vencimientos a `vencimientos.csv`. |
| `espe exportar --formato json` | Exporta todos los vencimientos a `vencimientos.json`. |

Usa `sin-registrar` en `espe entrega marcar` para quitar una marca. Los estados, nombres y la ruta del calendario se guardan en `%LOCALAPPDATA%\ESPE-CLI`. El estado de entrega se registra manualmente en la CLI. Para enviar una tarea o consultar su estado oficial, usa MiCampus.

Si descargas una exportación nueva en la misma ruta, la CLI la leerá en la próxima consulta. Usa `--archivo` para consultar otro `.ics` temporalmente. En las exportaciones a CSV o JSON, `--salida` permite elegir el destino. Si el archivo de destino ya existe, el comando pide un nombre distinto.

## Pruebas

Después de instalar el proyecto, ejecuta las pruebas desde la carpeta raíz.

```bat
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Las pruebas usan el calendario ficticio y crean su propia configuración temporal. Revisan la conversión horaria, los filtros, el registro de entregas y la exportación.

## Estructura del proyecto

| Carpeta | Contenido |
|---|---|
| `src/espe_cli/` | Comandos, configuración local, lectura de tareas, estados y exportación. |
| `ejemplos/` | Calendario ficticio para probar la CLI. |
| `tests/` | Pruebas que ejecutan el comando instalado. |
