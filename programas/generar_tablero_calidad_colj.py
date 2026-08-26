# -*- coding: utf-8 -*-
"""
Genera el tablero de seguimiento de los COLJ para la vigencia 2026.

El tablero sigue la estructura de tablero-cij y tablero-ppdj: una portada con
las cifras generales y accesos a las secciones, y cada sección en su propia
página. Se produce este árbol de archivos:

    index.html            portada, con las dos franjas de cifras y los accesos
    periodicidad.html     si cada localidad sesionó lo que debía
    documentos.html       si cargó acta y planillas de cada sesión
    pendientes.html       qué le falta a cada localidad
    ajustes.html          ajustes del registro por localidad
    detalle.html          qué habría que corregir en cada acta
    recursos/tablero.css  estilos comunes, con las tipográficas embebidas
    recursos/tablero.js   funciones de pintado comunes
    datos/datos_colj.js   los datos, para que los lean todas las páginas
    datos/calidad_colj_2026.json  los mismos datos en formato legible

Dos decisiones que conviene conocer antes de tocar esto:

Los datos se entregan como un .js que asigna window.DATOS_COLJ, no como un
.json que se pida con fetch. La razón es que el tablero se abre con doble clic
desde el disco y el navegador bloquea fetch sobre file://, mientras que una
etiqueta script sí carga. Es el mismo mecanismo que usa tablero-ppdj.

Las tipográficas van embebidas en base64 dentro del CSS y no como archivos
sueltos, porque el navegador sí bloquea la carga de fuentes sobre file:// por
CORS. Las imágenes en cambio se referencian con ruta relativa, que funciona
sin problema y evita repetir el mismo PNG en seis páginas.

Se alimenta de:
  - ../../programas/calidad_actas_2026.json, que produce
    extraer_calidad_actas_2026.py al abrir las 90 actas una por una.
  - La carpeta ../../2026/, para saber qué documentos se cargaron.
  - El Excel de seguimiento con las respuestas del formulario.

Se corre desde esta carpeta:
    python programas/generar_tablero_calidad_colj.py
"""

import os
import re
import sys
import json
import base64
import unicodedata
import collections
import warnings

warnings.filterwarnings("ignore")

import pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ_TABLERO = os.path.dirname(AQUI)
RAIZ_COLJ = os.path.dirname(RAIZ_TABLERO)

JSON_ACTAS = os.path.join(RAIZ_COLJ, "programas", "calidad_actas_2026.json")
CARPETA_2026 = os.path.join(RAIZ_COLJ, "2026")
CARPETA_DRIVE = os.path.join(RAIZ_COLJ, "Drive")


def buscar_excel_seguimiento():
    """Encuentra el Excel de respuestas del formulario dentro de Drive/.

    El nombre cambia con cada descarga porque el navegador le agrega " (1)",
    " (2)" y así sucesivamente cuando ya existe una copia. Por eso no se fija
    un nombre exacto: se buscan todos los que empiecen por "Seguimiento" y se
    toma el más reciente. Se ignoran los archivos temporales de Excel, que son
    los que empiezan por "~$" y aparecen mientras el libro está abierto.
    """
    candidatos = [
        os.path.join(CARPETA_DRIVE, nombre)
        for nombre in os.listdir(CARPETA_DRIVE)
        if nombre.lower().startswith("seguimiento")
        and nombre.lower().endswith(".xlsx")
        and not nombre.startswith("~$")
    ]
    if not candidatos:
        raise FileNotFoundError(
            "No se encontró ningún Excel de seguimiento en:\n  "
            + CARPETA_DRIVE
            + "\nDescarga las respuestas del formulario y déjalas ahí.")
    return max(candidatos, key=os.path.getmtime)


EXCEL_SEGUIMIENTO = buscar_excel_seguimiento()
CARPETA_DATOS = os.path.join(RAIZ_TABLERO, "datos")
CARPETA_RECURSOS = os.path.join(RAIZ_TABLERO, "recursos")
CARPETA_FUENTES = os.path.join(RAIZ_TABLERO, "fuentes")
CARPETA_HTML = os.path.join(RAIZ_TABLERO, "html")
CARPETA_ACTUALIZACION = os.path.join(RAIZ_TABLERO, "actualizacion")
EXCEL_ENLACES = os.path.join(CARPETA_ACTUALIZACION, "enlaces.xlsx")

FUENTES = [
    ("Anton", "400", "normal", "anton-latin-400.woff2"),
    ("Antonio", "700", "normal", "antonio-latin-700.woff2"),
    ("Figtree", "400 600", "normal", "figtree-latin-variable.woff2"),
]

# Piezas gráficas institucionales. El banner lo entregó la Subdirección y es el
# mismo del tablero de Power BI, así que se usa tal como llegó. La marca del pie
# es la que ya usa tablero-cij, para que las dos piezas se lean como del mismo
# sistema.
BANNER = "imagenes/Header.png"
MARCA_PIE = "imagenes/marca-pie.png"

ORDEN = ["Usaquén", "Chapinero", "Santa Fe", "San Cristóbal", "Usme",
         "Tunjuelito", "Bosa", "Kennedy", "Fontibón", "Engativá",
         "Suba", "Barrios Unidos", "Teusaquillo", "Los Mártires",
         "Antonio Nariño", "Puente Aranda", "La Candelaria",
         "Rafael Uribe Uribe", "Ciudad Bolívar", "Sumapaz"]

CAMPOS = ["no_juveniles", "juveniles", "consejeros", "plataformas", "otros"]

# El reglamento acordado en 2025 y recogido en el Decreto 647 de 2025 fija
# sesiones ordinarias cada dos meses. Al corte del 24 de julio de 2026 hay tres
# bimestres cerrados: enero-febrero, marzo-abril y mayo-junio. El bimestre de
# julio-agosto todavía está corriendo, así que no se le exige a nadie.
BIMESTRES_CERRADOS = [1, 2, 3]

# Sesiones ordinarias que se le piden a cada localidad al corte: una por cada
# bimestre ya cerrado. Es el número, no la casilla del calendario, lo que se
# mira para decir si una localidad sesionó lo que debía.
ORDINARIAS_EXIGIDAS = len(BIMESTRES_CERRADOS)

# Cargas del formulario que repiten una sesión ya registrada, pero con otra
# fecha. El de-duplicado normal, que agrupa por localidad y fecha, no las ve:
# para él son sesiones distintas.
#
# El número de comité es lo que las delata. Una localidad no tiene dos comités
# número 2, así que cuando el mismo número llega con fechas distintas hay una
# carga mal hecha. Engativá cargó cuatro veces su comité 2 mientras corregía
# los datos, y dos de esas cargas traían fechas de sesiones que nunca
# existieron: no hay acta archivada del 23 de abril ni del 29 de junio, y las
# cuatro actas de la localidad corresponden a los comités 1, 2, 3 y 4 con
# fechas 25 de febrero, 29 de abril, 3 de junio y 25 de junio.
#
# Se identifican por la marca temporal, que es única por respuesta. No se
# resuelve con una regla automática porque no la hay: quedarse con la carga más
# reciente daría la fecha equivocada en Engativá, y quedarse con la primera la
# daría equivocada en otros casos. Son pocos y se revisan a mano.
CARGAS_REPETIDAS = {
    "2026-06-14 13:16:06": ("Engativá, comité 2 con fecha 23 de abril; la "
                            "carga posterior lo corrigió al 29 de abril, que "
                            "es la fecha del acta archivada"),
    "2026-06-14 13:22:29": ("Engativá, comité 2 con fecha 29 de junio; no hay "
                            "acta de esa fecha y el comité 4 es el del 25 de "
                            "junio, así que la sesión no existió"),
}

# Días que pueden pasar sin que la localidad se reúna antes de que valga la
# pena mirarlo. Son los dos meses del reglamento traducidos a días corridos.
# No es una regla del decreto: es el punto donde el silencio del espacio deja
# de ser una fecha corrida y empieza a ser una ausencia.
DIAS_SIN_SESIONAR_ALERTA = 61
NOMBRE_BIMESTRE = {1: "enero y febrero", 2: "marzo y abril",
                   3: "mayo y junio", 4: "julio y agosto"}
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def fecha_larga(fecha):
    """Convierte una fecha en texto tipo '24 de julio de 2026'."""
    return "%d de %s de %d" % (fecha.day, MESES[fecha.month - 1], fecha.year)

# Actas archivadas en 2024, por localidad y en el orden de ORDEN. Vienen del
# balance ya documentado (Balance COLJ 2024-2026), no de un recorrido de
# carpeta, porque el material de 2024 no está en esta carpeta.
#
# OJO: son actas archivadas, no sesiones realizadas. La matriz sistematizada
# que alimenta el tablero de Power BI registra 234 sesiones en 2024, doce más
# que actas hay. La diferencia son sesiones que se hicieron y cuya acta nunca
# se radicó. Está explicado en Notes/hallazgo-tres-cifras-sesiones-colj-2024.
ACTAS_2024 = [11, 7, 10, 12, 12, 12, 11, 14, 12, 11,
              12, 6, 10, 10, 9, 12, 12, 14, 13, 12]
SESIONES_MATRIZ_2024 = 234

CARPETA_2025 = os.path.join(RAIZ_COLJ, "2025", "COLJ - Actas")

# Filas con que se crea actualizacion/enlaces.xlsx la primera vez. Después el
# Excel manda: para agregar, quitar o corregir un enlace se edita ahí y se
# vuelve a correr este programa, sin tocar código.
ENLACES_INICIALES = [
    ("SharePoint", "Carpeta institucional donde se archivan actas y planillas.",
     ""),
    ("Google Drive", "Carpeta de trabajo con lo que llega por el formulario.",
     ""),
    ("Formulario de seguimiento",
     "El formulario que diligencian los equipos locales tras cada sesión.", ""),
    ("NotebookLM", "Cuadernos con las actas sistematizadas por año.", ""),
    ("Tablero Power BI", "Sesiones y asistencia de la vigencia 2024.", ""),
    ("Protocolo de sistematización",
     "Convención de nombres y reglas de archivo de las actas.", ""),
]


# ---------------------------------------------------------------- utilidades

def leer_enlaces():
    """Lee actualizacion/enlaces.xlsx y devuelve las fichas de la página.

    Si el archivo no existe lo crea con las filas iniciales, para que siempre
    haya de dónde partir. Las filas sin nombre se ignoran y las que no traen
    dirección salen marcadas como pendientes.
    """
    os.makedirs(CARPETA_ACTUALIZACION, exist_ok=True)
    if not os.path.exists(EXCEL_ENLACES):
        crear_excel_enlaces()
    df = pd.read_excel(EXCEL_ENLACES, sheet_name="Enlaces", header=3)
    fichas = []
    for _, fila in df.iterrows():
        nombre = str(fila.get("Nombre") or "").strip()
        if not nombre or nombre.lower() == "nan":
            continue
        detalle = str(fila.get("Detalle") or "").strip()
        enlace = str(fila.get("Link") or "").strip()
        if detalle.lower() == "nan":
            detalle = ""
        if enlace.lower() == "nan":
            enlace = ""
        fichas.append({"nombre": nombre, "glosa": detalle, "url": enlace})
    return fichas


def crear_excel_enlaces():
    """Crea el Excel de enlaces con sus tres columnas y las filas iniciales."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment

    libro = Workbook()
    hoja = libro.active
    hoja.title = "Enlaces"
    hoja["A1"] = "Enlaces del tablero COLJ"
    hoja["A1"].font = Font(name="Calibri", size=14, bold=True,
                           color="FF2F3E3C")
    hoja["A2"] = ("Edita esta hoja para agregar, quitar o corregir un enlace. "
                  "Después vuelve a correr programas/"
                  "generar_tablero_calidad_colj.py y la página se actualiza. "
                  "Las filas sin link salen marcadas como pendientes; las "
                  "filas sin nombre se ignoran.")
    hoja["A2"].font = Font(name="Calibri", size=9, color="FF83766C")
    hoja["A2"].alignment = Alignment(wrap_text=True, vertical="top")
    hoja.merge_cells("A2:C2")
    hoja.row_dimensions[2].height = 42

    for i, titulo_col in enumerate(["Nombre", "Detalle", "Link"]):
        celda = hoja.cell(row=4, column=i + 1, value=titulo_col)
        celda.font = Font(name="Calibri", size=10, bold=True,
                          color="FFFFFFFF")
        celda.fill = PatternFill("solid", fgColor="FF663A93")
    for j, (nombre, detalle, enlace) in enumerate(ENLACES_INICIALES):
        hoja.cell(row=5 + j, column=1, value=nombre)
        hoja.cell(row=5 + j, column=2, value=detalle)
        hoja.cell(row=5 + j, column=3, value=enlace)
    hoja.column_dimensions["A"].width = 30
    hoja.column_dimensions["B"].width = 62
    hoja.column_dimensions["C"].width = 58
    hoja.freeze_panes = "A5"
    libro.save(EXCEL_ENLACES)


def sin_tildes(texto):
    """Quita tildes y pasa a minúscula, para poder comparar nombres."""
    texto = unicodedata.normalize("NFD", str(texto))
    return "".join(c for c in texto if unicodedata.category(c) != "Mn").lower()


def bimestre_de(mes):
    """Devuelve a qué bimestre pertenece un mes: 1 es enero y febrero."""
    return ((mes - 1) // 2) + 1


# ------------------------------------------------------- revisión de actas

def revisar_numeracion(acta):
    """Clasifica cómo quedó el número del acta. Devuelve estado y detalle."""
    if acta["texto_leido"] < 300:
        return "escaneo", ("el PDF está guardado como imagen, así que no se "
                           "alcanza a leer el número por dentro")
    estado = acta["estado_num_declarado"]
    if estado == "sin_linea":
        return "sin_linea", "al documento le falta la línea ACTA N°"
    if estado == "en_blanco":
        return "blanco", "la línea ACTA N° quedó sin número"
    if acta["num_declarado"] != acta["num_nombre"]:
        return "distinto", ("el nombre del archivo dice acta %s y por dentro "
                            "dice ACTA N° %s"
                            % (acta["num_nombre"], acta["num_declarado"]))
    return "ok", None


def revisar_recuadro(acta):
    """Clasifica cómo quedó el recuadro de participantes."""
    if acta["texto_leido"] < 300:
        return "escaneo", ("el PDF está guardado como imagen, así que no se "
                           "alcanza a leer el recuadro")
    etiquetas = acta["etiquetas_recuadro"]
    rec = acta["recuadro"]
    if not etiquetas:
        return "sin_recuadro", "falta el recuadro de participantes"
    if acta.get("recuadro_con_fila_propia"):
        return "modificado", ("el recuadro usa «entidades locales» donde el "
                              "formato pide «otros jóvenes»")
    vacias = [c for c in CAMPOS if c in etiquetas and rec.get(c) is None]
    faltantes = [c for c in CAMPOS if c not in etiquetas]
    if faltantes:
        return "modificado", "al recuadro le faltan filas respecto al formato"
    if vacias:
        return "modificado", "quedaron filas del recuadro sin número"
    suma = sum(rec[c] for c in ("consejeros", "plataformas", "otros"))
    if suma != rec["juveniles"]:
        return "no_cuadra", ("el total de jóvenes dice %d %s y las tres filas "
                             "de abajo suman %d"
                             % (rec["juveniles"],
                                "joven" if rec["juveniles"] == 1 else "jóvenes",
                                suma))
    return "ok", None


# ------------------------------------------------- documentos de cada sesión

def es_planilla(nombre):
    """Reconoce la planilla de asistencia, escaneada o en foto."""
    return bool(re.search(r"_asistencia(_\d+)?\.(pdf|jpg|jpeg|png)$",
                          sin_tildes(nombre)))


def es_digital(nombre):
    """Reconoce la planilla de asistencia sistematizada en Excel."""
    return bool(re.search(r"_asistencia_digital", sin_tildes(nombre)))


def numero_al_final(nombre):
    """Devuelve el número de sesión que trae el final del nombre."""
    m = re.search(r"_(\d+)\.[a-z]+$", sin_tildes(nombre))
    return int(m.group(1)) if m else None


def contar_actas_2025():
    """Cuenta las actas archivadas de 2025, por localidad.

    En 2025 los archivos no siempre traen la palabra acta en el nombre, así
    que se cuenta todo lo que esté en la carpeta de actas y no sea planilla.
    """
    conteo = {}
    if not os.path.isdir(CARPETA_2025):
        return {loc: 0 for loc in ORDEN}
    for carpeta in sorted(os.listdir(CARPETA_2025)):
        ruta = os.path.join(CARPETA_2025, carpeta)
        if not os.path.isdir(ruta):
            continue
        nombre = re.sub(r"^\d+[\.\s_]*", "", carpeta).strip()
        plano = sin_tildes(nombre).replace(" ", "")
        localidad = next(
            (o for o in ORDEN if sin_tildes(o).replace(" ", "") == plano), None)
        if localidad is None:
            localidad = next(
                (o for o in ORDEN if sin_tildes(o).replace(" ", "") in plano),
                nombre)
        n = 0
        for raiz, _, archivos in os.walk(ruta):
            for archivo in archivos:
                if archivo.startswith("~$"):
                    continue
                if os.path.splitext(archivo)[1].lower() not in (".pdf", ".docx",
                                                                ".doc"):
                    continue
                if "_asistencia" in sin_tildes(os.path.splitext(archivo)[0]):
                    continue
                n += 1
        conteo[localidad] = n
    return {loc: conteo.get(loc, 0) for loc in ORDEN}


def inventario_carpeta():
    """Lista todos los archivos de la carpeta 2026, por localidad."""
    inventario = collections.defaultdict(list)
    if not os.path.isdir(CARPETA_2026):
        return inventario
    for carpeta in sorted(os.listdir(CARPETA_2026)):
        ruta = os.path.join(CARPETA_2026, carpeta)
        if not os.path.isdir(ruta):
            continue
        nombre = re.sub(r"^\d+[\.\s]*", "", carpeta).strip()
        plano = sin_tildes(nombre).replace(" ", "")
        localidad = next(
            (o for o in ORDEN if sin_tildes(o).replace(" ", "") == plano),
            nombre)
        for raiz, _, archivos in os.walk(ruta):
            for archivo in archivos:
                if not archivo.startswith("~$"):
                    inventario[localidad].append(archivo)
    return inventario


def revisar_carga(acta, archivos):
    """Mira si la sesión tiene planilla de asistencia y planilla digital.

    Se empareja primero por número de sesión y solo si eso no da, por fecha.
    El orden importa: hay actas con la fecha mal escrita en el nombre, como
    la sesión 1 de Ciudad Bolívar que quedó con año 2025, y emparejar por
    fecha las daría por incompletas cuando sus planillas sí están.
    """
    numero = acta["num_nombre"]
    clave_fecha = (acta["fecha_nombre"] or "").replace("-", "")
    candidatos = [a for a in archivos
                  if (numero is not None and numero_al_final(a) == numero)
                  or (clave_fecha and clave_fecha in a)]
    tiene_planilla = any(es_planilla(a) for a in candidatos)
    if not tiene_planilla and clave_fecha:
        # Hay planillas sin número al final, como en Tunjuelito
        tiene_planilla = any(es_planilla(a) for a in archivos
                             if clave_fecha in a)
    tiene_digital = any(es_digital(a) for a in candidatos)
    return tiene_planilla, tiene_digital


# ------------------------------------------------------------------- datos

def avisar_numeros_repetidos(unicas):
    """Avisa si una localidad tiene el mismo número de comité en dos fechas.

    Es la señal de que alguien cargó la misma sesión dos veces. No detiene el
    programa, porque a veces el número está mal digitado y la sesión sí es
    distinta, pero deja el caso a la vista para revisarlo antes de publicar.
    Si el caso resulta ser una carga repetida, se agrega a CARGAS_REPETIDAS.
    """
    avisos = []
    for (loc, num), grupo in unicas.groupby(["Localidad",
                                             "Número de comité"]):
        fechas = sorted(set(grupo["fecha"]))
        if len(fechas) > 1:
            avisos.append("  %s, comité %g en %s"
                          % (loc, num,
                             " y ".join(f.strftime("%d/%m") for f in fechas)))
    if avisos:
        print("\nOJO: el mismo número de comité aparece con fechas distintas.")
        print("Puede ser una sesión cargada dos veces o un número mal escrito.")
        print("\n".join(avisos))
        print("Si es una carga repetida, agrégala a CARGAS_REPETIDAS.\n")


def construir():
    """Arma el resumen por localidad cruzando actas, carpeta y formulario."""
    with open(JSON_ACTAS, encoding="utf-8") as f:
        actas = json.load(f)
    archivos = inventario_carpeta()

    df = pd.read_excel(EXCEL_SEGUIMIENTO,
                       sheet_name="Respuestas de formulario 1")
    df["fecha"] = pd.to_datetime(df["Fecha del comité"], errors="coerce",
                                 dayfirst=True)
    f26 = df[df["fecha"].dt.year == 2026]

    # Fuera las cargas que repiten una sesión ya registrada con otra fecha.
    marcas = f26["Marca temporal"].dt.strftime("%Y-%m-%d %H:%M:%S")
    f26 = f26[~marcas.isin(CARGAS_REPETIDAS)]

    unicas = f26.drop_duplicates(subset=["Localidad", "fecha"])
    avisar_numeros_repetidos(unicas)

    # El corte es la última sesión reportada, no una fecha escrita a mano: así
    # se mueve solo cuando entren sesiones nuevas al formulario.
    fecha_corte = f26["fecha"].max()
    corte = fecha_larga(fecha_corte)

    # La última vez que alguien subió un acta: es la primera columna del Excel
    # de respuestas, "Marca temporal", que el formulario llena solo. Sirve para
    # saber si el registro está fresco o lleva semanas quieto.
    ultima_carga = fecha_larga(f26["Marca temporal"].max())

    # El último comité que quedó registrado, con su localidad. No siempre es el
    # de la carga más reciente: las actas no entran en el mismo orden en que se
    # sesiona, así que se calcula aparte.
    fila_ultima = f26.loc[f26["fecha"].idxmax()]
    ultima_sesion = "%s, %s" % (fila_ultima["Localidad"],
                                fecha_larga(fila_ultima["fecha"]))

    # Cifras de asistentes que reportó el formulario, por localidad y fecha
    reportado = {}
    for _, fila in unicas.iterrows():
        clave = (fila["Localidad"], fila["fecha"].strftime("%Y-%m-%d"))
        reportado[clave] = (fila["Cantidad de asistentes (no juveniles)"],
                            fila["Cantidad de asistentes jóvenes"])

    por_loc = collections.defaultdict(list)
    for a in actas:
        por_loc[a["localidad"]].append(a)

    localidades = []
    for nombre in ORDEN:
        propias = sorted(por_loc.get(nombre, []),
                         key=lambda x: x["fecha_nombre"] or "")
        del_form = unicas[unicas["Localidad"] == nombre]

        # ---- periodicidad
        ordinarias = del_form[del_form["Tipo"] == "Ordinario"]
        extraordinarias = del_form[del_form["Tipo"] == "Extraordinario"]
        bimestres = set(bimestre_de(f.month) for f in ordinarias["fecha"])
        cubiertos = sorted(b for b in bimestres if b in BIMESTRES_CERRADOS)
        faltantes_bim = [b for b in BIMESTRES_CERRADOS if b not in bimestres]

        # El cumplimiento se mide por el número de sesiones ordinarias, no por
        # la cuadrícula de bimestres. La razón está en los datos: hay
        # localidades que sesionaron cada dos meses de forma pareja pero cuyas
        # fechas cayeron a los lados del corte del calendario, y aparecían
        # incumpliendo al lado de otras menos regulares que sí encajaron en la
        # cuadrícula. Los bimestres se siguen mostrando, pero como lectura del
        # ritmo del año, no como veredicto.
        faltan_ordinarias = max(0, ORDINARIAS_EXIGIDAS - len(ordinarias))

        # Cuánto lleva la localidad sin reunirse a la fecha de corte. Cuenta
        # cualquier sesión, ordinaria o extraordinaria: lo que interesa aquí es
        # si el espacio está activo, no de qué tipo fue la última reunión.
        if len(del_form):
            dias_sin_sesionar = int((fecha_corte
                                     - del_form["fecha"].max()).days)
        else:
            dias_sin_sesionar = None

        # ---- documentos cargados
        planillas = digitales = 0
        pendientes_carga = []
        for acta in propias:
            tiene_planilla, tiene_digital = revisar_carga(
                acta, archivos.get(nombre, []))
            planillas += tiene_planilla
            digitales += tiene_digital
            if not tiene_planilla:
                pendientes_carga.append(
                    "por cargar la planilla de asistencia de la sesión %s"
                    % acta["num_nombre"])
            if not tiene_digital:
                pendientes_carga.append(
                    "por cargar la planilla digital de la sesión %s"
                    % acta["num_nombre"])
        pendientes_sesion = []
        if faltan_ordinarias:
            pendientes_sesion.append(
                "%s para llegar a las %d que se esperan al corte"
                % ("queda pendiente una sesión ordinaria" if faltan_ordinarias
                   == 1 else "quedan pendientes %d sesiones ordinarias"
                   % faltan_ordinarias, ORDINARIAS_EXIGIDAS))
        if dias_sin_sesionar is not None                 and dias_sin_sesionar > DIAS_SIN_SESIONAR_ALERTA:
            pendientes_sesion.append(
                "lleva %d días sin reunirse" % dias_sin_sesionar)

        # ---- revisión documento por documento
        num = collections.Counter()
        rec = collections.Counter()
        cifras = {"comparables": 0, "coinciden": 0, "difieren": 0}
        limpias = 0
        detalle = []
        for acta in propias:
            estado_num, nota_num = revisar_numeracion(acta)
            estado_rec, nota_rec = revisar_recuadro(acta)
            num[estado_num] += 1
            rec[estado_rec] += 1

            nota_cif = None
            clave = (nombre, acta["fecha_nombre"])
            caja = acta["recuadro"]
            if clave in reportado and caja.get("no_juveniles") is not None \
                    and caja.get("juveniles") is not None:
                cifras["comparables"] += 1
                rep_nj, rep_j = reportado[clave]
                if int(rep_nj) == caja["no_juveniles"] \
                        and int(rep_j) == caja["juveniles"]:
                    cifras["coinciden"] += 1
                else:
                    cifras["difieren"] += 1
                    nota_cif = ("el Excel reporta %d y %d; el acta dice %d y "
                                "%d, hay que definir cuál queda"
                                % (int(rep_nj), int(rep_j),
                                   caja["no_juveniles"], caja["juveniles"]))

            ajustes = [x for x in (nota_num, nota_rec, nota_cif) if x]
            if not ajustes:
                limpias += 1
            else:
                detalle.append({"archivo": acta["archivo"],
                                "fecha": acta["fecha_nombre"],
                                "ajustes": ajustes})

        # ---- estado general de la localidad
        if faltan_ordinarias:
            estado = "falta sesionar"
        elif pendientes_carga:
            estado = "falta cargar"
        elif detalle:
            estado = "revisar forma"
        else:
            estado = "al día"

        localidades.append({
            "localidad": nombre,
            "actas": len(propias),
            "respuestas_formulario": int((f26["Localidad"] == nombre).sum()),
            "sesiones_formulario": len(del_form),
            "ordinarias": len(ordinarias),
            "extraordinarias": len(extraordinarias),
            "bimestres_cubiertos": len(cubiertos),
            "bimestres_con_ordinaria": cubiertos,
            "bimestres_exigidos": len(BIMESTRES_CERRADOS),
            "bimestres_faltantes": [NOMBRE_BIMESTRE[b] for b in faltantes_bim],
            "ordinarias_exigidas": ORDINARIAS_EXIGIDAS,
            "faltan_ordinarias": faltan_ordinarias,
            "dias_sin_sesionar": dias_sin_sesionar,
            "planillas": planillas,
            "digitales": digitales,
            "pendientes_carga": pendientes_carga,
            "pendientes_sesion": pendientes_sesion,
            "estado": estado,
            "limpias": limpias,
            "numeracion": {"ok": num["ok"], "distinto": num["distinto"],
                           "blanco": num["blanco"],
                           "sin_linea": num["sin_linea"],
                           "escaneo": num["escaneo"]},
            "recuadro": {"ok": rec["ok"], "sin_recuadro": rec["sin_recuadro"],
                         "modificado": rec["modificado"],
                         "no_cuadra": rec["no_cuadra"],
                         "escaneo": rec["escaneo"]},
            "cifras": cifras,
            "detalle": detalle,
        })

    def suma(*camino):
        """Suma un campo, anidado o no, a lo largo de las veinte localidades."""
        total = 0
        for loc in localidades:
            valor = loc
            for paso in camino:
                valor = valor[paso]
            total += valor
        return total

    resumen = {
        "actas": suma("actas"),
        "respuestas_formulario": suma("respuestas_formulario"),
        "sesiones_formulario": suma("sesiones_formulario"),
        "ordinarias": suma("ordinarias"),
        "extraordinarias": suma("extraordinarias"),
        "planillas": suma("planillas"),
        "digitales": suma("digitales"),
        "al_dia_sesiones": sum(1 for l in localidades
                               if not l["faltan_ordinarias"]),
        "en_silencio": sum(1 for l in localidades
                           if l["dias_sin_sesionar"] is not None
                           and l["dias_sin_sesionar"]
                           > DIAS_SIN_SESIONAR_ALERTA),
        "dias_alerta": DIAS_SIN_SESIONAR_ALERTA,
        "ordinarias_exigidas": ORDINARIAS_EXIGIDAS,
        "carga_completa": sum(1 for l in localidades
                              if not l["pendientes_carga"]),
        "sin_pendientes": sum(1 for l in localidades
                              if l["estado"] == "al día"),
        "con_pendientes": sum(1 for l in localidades
                              if l["pendientes_sesion"]
                              or l["pendientes_carga"]),
        "actas_con_ajustes": sum(len(l["detalle"]) for l in localidades),
        "localidades_con_ajustes": sum(1 for l in localidades if l["detalle"]),
        "limpias": suma("limpias"),
        "num_problema": (suma("numeracion", "distinto")
                         + suma("numeracion", "blanco")
                         + suma("numeracion", "sin_linea")),
        "rec_problema": (suma("recuadro", "sin_recuadro")
                         + suma("recuadro", "modificado")
                         + suma("recuadro", "no_cuadra")),
        "cifras_difieren": suma("cifras", "difieren"),
        "cifras_comparables": suma("cifras", "comparables"),
        "escaneadas": suma("numeracion", "escaneo"),
    }
    # Serie por año, para la página de estadísticas generales. Es un croquis:
    # 2024 y 2025 traen el conteo de actas archivadas que ya estaba
    # documentado, y todavía no se recalcularon con el método de 2026.
    actas25 = contar_actas_2025()
    serie = []
    for i, loc in enumerate(ORDEN):
        serie.append({"localidad": loc,
                      "a2024": ACTAS_2024[i],
                      "a2025": actas25[loc],
                      "a2026": localidades[i]["actas"]})
    totales_serie = {
        "a2024": sum(x["a2024"] for x in serie),
        "a2025": sum(x["a2025"] for x in serie),
        "a2026": sum(x["a2026"] for x in serie),
        "sesiones_matriz_2024": SESIONES_MATRIZ_2024,
    }

    return {"corte": corte, "ultima_carga": ultima_carga,
            "ultima_sesion": ultima_sesion,
            "bimestres_exigidos": len(BIMESTRES_CERRADOS),
            "resumen": resumen, "localidades": localidades,
            "serie": serie, "totales_serie": totales_serie,
            "enlaces": leer_enlaces()}


# ------------------------------------------------------------------ estilos

CSS = """
:root {
  /* Acento del tablero: morado oficial de la paleta Distrito Joven. Se eligió
     por el banner institucional de la cabecera, que es morado, para que la
     pieza se lea completa. El acento es solo cromo, nunca estado: los colores
     de estado van aparte y no se mezclan con este. */
  --acento: #663a93;

  /* Neutros y cremas, los mismos que ya usa tablero-cij, para que las dos
     piezas se lean como del mismo sistema. */
  --crema: #f5efd2;
  --gris-oscuro: #2f2b28;
  --gris: #83766c;
  --gris-claro: #f4f2ee;
  --blanco: #ffffff;

  /* Estados. Escala de dos familias, como pide la nota canónica: azul
     petróleo para lo bueno, gris neutro para el intermedio, rosa coral claro
     y oscuro para los dos grados de lo malo. Sin verde ni naranja. */
  --bueno: #1e7895;
  --neutral: #bbb4ae;
  --malo-claro: #e86269;
  --malo: #c35258;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
/* La página es una columna flexible de alto completo para que la marca del
   pie quede siempre abajo. En páginas cortas, como la portada, se ancla al
   borde inferior de la pantalla en vez de quedar flotando a media altura;
   en las largas fluye después del contenido como cualquier pie. */
body {
  font-family: 'Figtree', 'Segoe UI', sans-serif;
  background: var(--blanco);
  color: var(--gris-oscuro);
  line-height: 1.5;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}
a { color: inherit; }

/* --------------------------------------------------------------- cabecera */

.banner { display: block; width: 100%; height: auto; }
.container {
  width: 100%; max-width: 1320px; margin: 0 auto; padding: 1.5rem;
}

.titulo-zona {
  width: 100%; max-width: 1320px; margin: 0 auto; padding: 2.2rem 1.5rem 0;
}
.titulo-zona h1 {
  font-family: 'Anton', 'Segoe UI', sans-serif; font-weight: 400;
  text-transform: uppercase; letter-spacing: 0.01em;
  font-size: 2.9rem; line-height: 1.08; color: var(--gris-oscuro);
}
.titulo-zona .intro {
  margin-top: 0.7rem; max-width: 74ch; color: var(--gris); font-size: 0.98rem;
}

/* El volver va arriba del título y en el mismo lugar en todas las páginas
   internas, para que no haya que buscarlo. */
.volver {
  display: inline-block; text-decoration: none;
  font-family: 'Antonio', 'Segoe UI', sans-serif; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.05em; font-size: 0.78rem;
  color: var(--acento); padding: 7px 15px; border-radius: 8px;
  background: var(--gris-claro); margin-bottom: 1.3rem;
}
.volver:hover { background: var(--acento); color: var(--blanco); }

/* ------------------------------------------------------------- estructura */

.rotulo-seccion { margin: 2.4rem 0 1rem; }
.rotulo-seccion:first-child { margin-top: 0.6rem; }
.rotulo-seccion .numero {
  font-family: 'Antonio', 'Segoe UI', sans-serif; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.05em; font-size: 0.78rem;
  color: var(--acento); display: block; margin-bottom: 0.25rem;
}
.rotulo-seccion h2 {
  font-family: 'Anton', 'Segoe UI', sans-serif; font-weight: 400;
  text-transform: uppercase; letter-spacing: 0.01em;
  font-size: 1.6rem; line-height: 1.15; color: var(--gris-oscuro);
}
.rotulo-seccion p {
  margin-top: 0.45rem; max-width: 82ch; color: var(--gris); font-size: 0.9rem;
}

/* Franja de cifras: una sola pieza de color dividida por separadores finos,
   sin tarjetas sueltas ni bordes. */
.franja {
  display: flex; background: var(--acento);
  border-radius: 10px; overflow: hidden; margin-bottom: 1.5rem;
}
.franja .casilla { position: relative; flex: 1; padding: 26px 24px 22px; }
.franja .casilla:not(:first-child)::before {
  content: ''; position: absolute; left: 0; top: 50%;
  width: 1px; height: 58%; background: rgba(255,255,255,0.22);
  transform: translateY(-50%);
}
.franja .rotulo {
  display: block; color: var(--crema);
  font-family: 'Antonio', 'Figtree', sans-serif; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.04em;
  font-size: 0.74rem; margin-bottom: 18px;
}
.franja .valor {
  font-family: 'Anton', 'Figtree', sans-serif; font-weight: 400;
  font-size: 2.4rem; color: var(--blanco); line-height: 1; margin-bottom: 8px;
}
.franja .glosa { font-size: 0.78rem; color: var(--crema); }
@media (max-width: 860px) {
  .franja { flex-direction: column; }
  .franja .casilla:not(:first-child)::before {
    left: 50%; top: 0; width: 58%; height: 1px; transform: translateX(-50%);
  }
}

.tarjeta {
  background: var(--blanco); border-radius: 10px; padding: 1.4rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06); margin-bottom: 1.2rem;
}

/* --------------------------------------------------------------- portada */

/* Portada a dos columnas, como tablero-cij y tablero-ppdj: a la izquierda el
   título grande y las cifras del año, a la derecha los campos que llevan a
   cada parte del tablero. */
.portada {
  width: 100%; max-width: 1320px; margin: 0 auto; padding: 2.6rem 1.5rem 1rem;
  display: grid; grid-template-columns: minmax(320px, 1.05fr) 1fr;
  gap: 3rem;
  /* Crece para ocupar el alto que sobra y centra ahí su contenido: el título
     y los campos quedan a media pantalla en vez de pegados al banner.
     align-items alinea las dos columnas entre sí, align-content centra el
     bloque completo dentro del alto disponible. */
  flex: 1;
  align-items: center;
  align-content: center;
}
@media (max-width: 980px) {
  .portada { grid-template-columns: 1fr; gap: 2rem; }
}
.portada h1 {
  font-family: 'Anton', 'Segoe UI', sans-serif; font-weight: 400;
  text-transform: uppercase; letter-spacing: 0.01em;
  font-size: clamp(4rem, 8vw, 6.4rem); line-height: 0.92;
  color: var(--gris-oscuro);
}
.portada .nombre-largo {
  font-family: 'Antonio', 'Segoe UI', sans-serif; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.045em;
  font-size: clamp(0.95rem, 1.5vw, 1.18rem); line-height: 1.25;
  color: var(--gris); margin-top: 0.55rem; max-width: 24ch;
}
/* Las dos fechas del registro. El rótulo va en gris y el dato en el gris
   oscuro: son dos hechos distintos y sin ese contraste quedaban con el mismo
   peso. El tamaño no baja de 0.9rem para que el gris secundario mantenga
   contraste suficiente sobre el fondo blanco. */
.portada .ultimo-registro {
  font-size: 0.9rem; color: var(--gris); margin-top: 0.9rem; line-height: 1.7;
}
.portada .ultimo-registro span { display: block; }
.portada .ultimo-registro b { font-weight: 600; color: var(--gris-oscuro); }

.portada .seguimiento {
  font-family: 'Anton', 'Segoe UI', sans-serif; font-weight: 400;
  text-transform: uppercase; letter-spacing: 0.01em;
  font-size: clamp(1.6rem, 2.6vw, 2.2rem); line-height: 1.05;
  color: var(--acento); margin-top: 0.75rem;
}

.instruccion {
  font-family: 'Antonio', 'Segoe UI', sans-serif; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.05em; font-size: 0.82rem;
  color: var(--gris); margin-bottom: 0.9rem;
}

/* Campos de la portada. Se pintan con tres colores de la paleta oficial que
   no se usan para estado en ninguna parte del tablero, para que nadie los lea
   como semáforo: morado, teal y azul cielo. */
.campos { display: flex; flex-direction: column; gap: 0.9rem; }
.campo {
  display: block; text-decoration: none; border-radius: 12px;
  padding: 1.15rem 1.4rem 1.25rem; color: var(--blanco);
  transition: transform 0.15s ease;
}
.campo:hover { transform: translateY(-2px); }
.campo:nth-child(1) { background: #663a93; }
.campo:nth-child(2) { background: #1e9da3; }
.campo:nth-child(3) { background: #2fa4d4; }
.campo .titulo-campo {
  font-family: 'Antonio', 'Segoe UI', sans-serif; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.05em; font-size: 1.12rem;
}
.campo .titulo-campo .num { opacity: 0.72; margin-right: 0.45rem; }
.campo .glosa-campo {
  font-size: 0.87rem; margin-top: 0.3rem; color: var(--crema);
}


/* --------------------------------------------------------------- accesos */

/* Los accesos de la portada. Cada uno lleva su propia cifra, para que desde
   la portada ya se sepa qué hay adentro sin tener que entrar. */
.accesos {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(238px, 1fr));
  gap: 1rem;
}
.acceso {
  display: block; text-decoration: none; background: var(--blanco);
  border-radius: 10px; padding: 1.3rem 1.4rem 1.2rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.acceso:hover {
  transform: translateY(-2px); box-shadow: 0 2px 10px rgba(0,0,0,0.05);
}
.acceso .cifra {
  font-family: 'Anton', 'Figtree', sans-serif; font-weight: 400;
  font-size: 2rem; line-height: 1; color: var(--acento);
}
.acceso .nombre {
  font-family: 'Antonio', 'Segoe UI', sans-serif; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.05em; font-size: 0.92rem;
  color: var(--gris-oscuro); margin: 0.65rem 0 0.35rem;
}
.acceso .glosa { font-size: 0.85rem; color: var(--gris); }
.acceso .entrar {
  display: block; margin-top: 0.8rem;
  font-family: 'Antonio', 'Segoe UI', sans-serif; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.05em; font-size: 0.72rem;
  color: var(--acento);
}

/* Fichas de enlace externo. Las que todavía no tienen dirección se marcan
   como pendientes y no son clicables, para que se vea el croquis completo. */
.enlace {
  display: block; text-decoration: none; background: var(--blanco);
  border-radius: 10px; padding: 1.1rem 1.3rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
a.enlace:hover { transform: translateY(-2px); }
a.enlace { transition: transform 0.15s ease; }
.enlace .nombre-enlace {
  font-family: 'Antonio', 'Segoe UI', sans-serif; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.05em; font-size: 0.92rem;
  color: var(--gris-oscuro);
}
.enlace .glosa { font-size: 0.85rem; color: var(--gris); margin-top: 0.3rem; }
.enlace .marca-pendiente {
  display: inline-block; margin-top: 0.7rem; padding: 3px 10px;
  border-radius: 4px; background: var(--gris-claro); color: var(--gris);
  font-family: 'Antonio', 'Segoe UI', sans-serif; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.05em; font-size: 0.68rem;
}
.enlace .ir {
  display: block; margin-top: 0.7rem;
  font-family: 'Antonio', 'Segoe UI', sans-serif; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.05em; font-size: 0.72rem;
  color: var(--acento);
}

/* ---------------------------------------------------------------- tablas */

table { width: 100%; border-collapse: collapse; }
thead th {
  font-family: 'Antonio', 'Segoe UI', sans-serif; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.04em; font-size: 0.7rem;
  color: var(--gris); padding: 10px 9px 12px; text-align: center;
  border-bottom: 2px solid var(--gris-claro); vertical-align: bottom;
}
thead th:first-child { text-align: left; padding-left: 16px; }
tbody td {
  padding: 9px; text-align: center; font-size: 0.88rem;
  border-bottom: 1px solid var(--gris-claro);
}
tbody td:first-child { text-align: left; padding-left: 16px; font-weight: 600; }
tbody tr:hover td { background: var(--gris-claro); }
tbody tr.total td {
  font-weight: 600; border-top: 2px solid var(--gris-oscuro);
  border-bottom: 0; background: var(--blanco);
}
tbody tr.total:hover td { background: var(--blanco); }

.pastilla {
  display: inline-block; min-width: 28px; padding: 2px 9px; border-radius: 4px;
  font-weight: 600; font-size: 0.85rem;
}
.pastilla.mal { background: var(--malo); color: var(--blanco); }
/* El cero en las columnas de ajustes es la mejor noticia posible, así que va
   en el gris de texto y no en un tono apagado que lea como sin dato. */
.neutro { color: var(--gris-oscuro); }

.chip {
  display: inline-block; padding: 3px 11px; border-radius: 4px;
  font-family: 'Antonio', 'Segoe UI', sans-serif; font-weight: 700;
  font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.05em;
  white-space: nowrap;
}
.chip.al-dia { background: var(--bueno); color: var(--blanco); }
.chip.revisar { background: var(--neutral); color: var(--gris-oscuro); }
.chip.cargar { background: var(--malo-claro); color: var(--blanco); }
.chip.sesionar { background: var(--malo); color: var(--blanco); }

.barra {
  display: flex; height: 8px; border-radius: 3px; overflow: hidden;
  background: var(--gris-claro); min-width: 84px; margin-top: 5px;
}
.barra span { display: block; height: 100%; }
.barra .b-bien { background: var(--bueno); }
.barra .b-mal { background: var(--malo); }

/* Puntos de bimestre: tres casillas que muestran de un vistazo en cuál se
   sesionó y en cuál no. */
.bimestres { display: inline-flex; gap: 4px; }
.bimestres i {
  width: 15px; height: 15px; border-radius: 3px; display: block;
  font-style: normal;
}
.bimestres i.si { background: var(--bueno); }
/* El cuadro de un bimestre sin sesión ordinaria va en el neutral, no en el
   rojo de estado. Desde que el cumplimiento se mide por número de sesiones y
   no por la cuadrícula del calendario, un bimestre vacío es un dato del ritmo
   del año y no un incumplimiento, y el color tiene que decir lo mismo que el
   texto de la página. */
.bimestres i.no { background: var(--neutral); }

/* --------------------------------------------------------- listas y pie */

.rejilla {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1rem;
}
.bloque {
  background: var(--blanco); border-radius: 10px; padding: 1.1rem 1.3rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.bloque .nombre {
  font-family: 'Antonio', 'Segoe UI', sans-serif; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.05em; font-size: 0.9rem;
  color: var(--gris-oscuro); margin-bottom: 0.5rem;
}
.bloque ul { margin: 0; padding-left: 17px; }
.bloque li { font-size: 0.85rem; color: var(--gris); margin-bottom: 3px; }

details.localidad {
  background: var(--blanco); border-radius: 10px; margin-bottom: 0.7rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
details.localidad > summary {
  cursor: pointer; padding: 14px 18px;
  font-family: 'Antonio', 'Segoe UI', sans-serif; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.05em; font-size: 0.9rem;
  color: var(--gris-oscuro); display: flex; justify-content: space-between;
  align-items: center; gap: 16px; list-style: none;
}
details.localidad > summary::-webkit-details-marker { display: none; }
details.localidad > summary .conteo {
  font-family: 'Figtree', sans-serif; font-weight: 600; text-transform: none;
  letter-spacing: 0; font-size: 0.82rem; color: var(--malo);
}
details.localidad .cuerpo { padding: 0 18px 14px; }
.ajuste { padding: 10px 0; border-top: 1px solid var(--gris-claro); }
.ajuste .archivo {
  font-family: 'Antonio', 'Segoe UI', sans-serif; font-weight: 700;
  font-size: 0.78rem; letter-spacing: 0.03em; color: var(--acento);
  word-break: break-all;
}
.ajuste ul { margin: 5px 0 0; padding-left: 17px; }
.ajuste li { font-size: 0.85rem; color: var(--gris); margin-bottom: 2px; }

.leyenda {
  display: flex; flex-wrap: wrap; gap: 16px; align-items: center;
  font-size: 0.82rem; color: var(--gris); margin: 0.2rem 0 0.4rem;
}
.leyenda .punto {
  display: inline-block; width: 11px; height: 11px; border-radius: 3px;
  margin-right: 6px; vertical-align: -1px;
}
.leyenda .punto.bien { background: var(--bueno); }
.leyenda .punto.mal { background: var(--neutral); }

/* Nota destacada bajo una franja de cifras: fondo suave, sin borde de color
   ni icono, para que se lea como aclaración y no como alerta. */
/* Aclaración de lectura, no alerta: texto plano, sin fondo ni borde, a la
   misma medida que el resto de los párrafos de la hoja. */
.nota-general {
  font-size: 0.9rem; color: var(--gris);
  margin-bottom: 1.6rem; max-width: 82ch;
}
.nota-general strong { color: var(--gris-oscuro); }

/* Recordatorio del corte, bajo el título de cada página con datos. Texto
   corriente en gris secundario: es una precisión de lectura, no una alerta. */
.corte-aviso {
  font-size: 0.85rem; color: var(--gris); margin-top: 0.7rem;
}
.corte-aviso b { font-weight: 600; color: var(--gris-oscuro); }

.pie-nota {
  font-size: 0.8rem; line-height: 1.6; color: var(--gris); margin-top: 2.4rem;
}
.marca-pie {
  display: block; width: 100%; height: auto;
  margin-top: auto;   /* empuja el pie al fondo cuando sobra alto */
}
/* El aire entre el contenido y el pie lo pone el contenido, porque el margen
   automático de arriba se consume al empujar. */
.container, .portada { padding-bottom: 2.5rem; }

@media (max-width: 700px) {
  .titulo-zona h1 { font-size: 2rem; }
  .rotulo-seccion h2 { font-size: 1.3rem; }
  .tabla-ancha { overflow-x: auto; }
  table { min-width: 640px; }
}
"""


# ------------------------------------------------------------- javascript

JS_COMUN = """
/* Funciones de pintado que comparten la portada y las paginas internas.
   Los datos llegan por datos/datos_colj.js, que asigna window.DATOS_COLJ.
   Lo genera programas/generar_tablero_calidad_colj.py: no editar a mano. */

var D = window.DATOS_COLJ;

function pastilla(valor) {
  if (valor === 0) return '<span class="neutro">0</span>';
  return '<span class="pastilla mal">' + valor + '</span>';
}

function fraccion(parte, total) {
  if (parte === total) {
    return '<span class="neutro">' + parte + ' de ' + total + '</span>';
  }
  return '<span class="pastilla mal">' + parte + ' de ' + total + '</span>';
}

/* Un cuadro por bimestre cerrado, en el orden del calendario. Recibe la lista
   de bimestres que sí tuvieron sesión ordinaria, no cuántos fueron: pintar los
   primeros N cuadros mostraba el bimestre equivocado a las localidades que se
   saltaron uno del medio. */
function bimestres(conOrdinaria, exigidos) {
  var h = '<span class="bimestres">';
  for (var i = 1; i <= exigidos; i++) {
    h += '<i class="' + (conOrdinaria.indexOf(i) >= 0 ? 'si' : 'no') +
         '" title="' + NOMBRE_BIMESTRE[i] + '"></i>';
  }
  return h + '</span>';
}

var NOMBRE_BIMESTRE = {1: 'enero y febrero', 2: 'marzo y abril',
                       3: 'mayo y junio', 4: 'julio y agosto'};

/* Los días que una localidad lleva sin reunirse. Se marca solo cuando pasa el
   umbral de dos meses, para que la columna no se lea como semáforo: todas las
   localidades tienen algún número aquí y eso es normal. */
function silencio(dias) {
  if (dias === null) return '<span class="neutro">sin sesiones</span>';
  var texto = dias + (dias === 1 ? ' día' : ' días');
  if (dias > D.resumen.dias_alerta) {
    return '<span class="pastilla mal">' + texto + '</span>';
  }
  return '<span class="neutro">' + texto + '</span>';
}

function barra(bien, total) {
  if (!total) return '';
  var p = function (n) { return (n / total * 100).toFixed(1); };
  return '<div class="barra">' +
    '<span class="b-bien" style="width:' + p(bien) + '%"></span>' +
    '<span class="b-mal" style="width:' + p(total - bien) + '%"></span></div>';
}

var ETIQUETA_ESTADO = {
  'al día': ['al-dia', 'Al día'],
  'revisar forma': ['revisar', 'Ajustes de forma'],
  'falta cargar': ['cargar', 'Por cargar'],
  'falta sesionar': ['sesionar', 'Por sesionar']
};

function chip(estado) {
  var e = ETIQUETA_ESTADO[estado];
  return '<span class="chip ' + e[0] + '">' + e[1] + '</span>';
}

function franja(id, casillas) {
  var nodo = document.getElementById(id);
  if (!nodo) return;
  nodo.innerHTML = casillas.map(function (c) {
    return '<div class="casilla">' +
      '<span class="rotulo">' + c.rot + '</span>' +
      '<div class="valor">' + c.v + '</div>' +
      '<div class="glosa">' + c.glosa + '</div></div>';
  }).join('');
}

/* --------------------------------------------------------------- portada */

/* El recordatorio de hasta dónde llegan los datos. Se corre en todas las
   páginas y no hace nada donde no está el nodo.

   Dice las dos cosas a la vez porque ahí está la confusión: la fecha de corte
   es la del último COLJ que quedó registrado, no la del día en que alguien
   abre el tablero. Una tabla puede estar completa aunque la fecha se vea
   vieja, y eso solo se entiende si se dice de dónde sale la fecha. */
function pintarCorte() {
  var nodo = document.getElementById('corte-aviso');
  if (!nodo) return;
  nodo.innerHTML = 'La fecha de corte es el <b>' + D.corte + '</b>: el día ' +
    'en que sesionó el último COLJ registrado, no el día de consulta.';
}

function pintarCampos() {
  var r = D.resumen;
  var campos = [
    {href: 'html/estadisticas.html', num: '1', titulo: 'Estadísticas generales',
     glosa: 'Las sesiones de 2024, 2025 y 2026 en las veinte localidades.'},
    {href: 'html/zoom.html', num: '2', titulo: 'Zoom año en curso',
     glosa: 'Cómo va cada localidad en 2026 y qué ajustes tiene su registro.'},
    {href: 'html/enlaces.html', num: '3', titulo: 'Enlaces',
     glosa: 'Dónde vive cada cosa: el archivo, el formulario y los tableros.'}
  ];
  var nodo = document.getElementById('campos');
  if (!nodo) return;
  nodo.innerHTML = campos.map(function (c) {
    return '<a class="campo" href="' + c.href + '">' +
      '<div class="titulo-campo"><span class="num">' + c.num + '.</span>' +
      c.titulo + '</div>' +
      '<div class="glosa-campo">' + c.glosa + '</div></a>';
  }).join('');
}

function pintarFranjaAnios() {
  var t = D.totales_serie;
  franja('franja-anios', [
    {v: t.a2024, rot: 'Actas 2024', glosa: 'Año completo, con sesiones ' +
     'mensuales.'},
    {v: t.a2025, rot: 'Actas 2025', glosa: 'Año completo, ya con sesiones ' +
     'ordinarias bimensuales.'},
    {v: t.a2026 + '*', rot: 'Actas 2026', glosa: 'Año en curso, con corte ' +
     'al ' + D.corte + '.'}
  ]);
}

function pintarSerie() {
  var filas = D.serie.map(function (l) {
    return '<tr><td>' + l.localidad + '</td>' +
      '<td>' + l.a2024 + '</td>' +
      '<td>' + l.a2025 + '</td>' +
      '<td>' + l.a2026 + '</td></tr>';
  }).join('');
  var t = D.totales_serie;
  document.getElementById('tabla-serie').innerHTML = filas +
    '<tr class="total"><td>Total</td>' +
    '<td>' + t.a2024 + '</td><td>' + t.a2025 + '</td>' +
    '<td>' + t.a2026 + '</td></tr>';
}

function pintarEnlaces() {
  var nodo = document.getElementById('enlaces');
  if (!nodo) return;
  nodo.innerHTML = D.enlaces.map(function (e) {
    var cuerpo = '<div class="nombre-enlace">' + e.nombre + '</div>' +
      '<div class="glosa">' + e.glosa + '</div>';
    if (e.url) {
      return '<a class="enlace" href="' + e.url + '" target="_blank" ' +
        'rel="noopener">' + cuerpo +
        '<span class="ir">Abrir &rarr;</span></a>';
    }
    return '<div class="enlace">' + cuerpo +
      '<span class="marca-pendiente">Dirección por definir</span></div>';
  }).join('');
}

function pintarAccesosZoom() {
  var r = D.resumen;
  var fichas = [
    {href: 'periodicidad.html', cifra: r.al_dia_sesiones + ' de 20',
     nombre: 'Periodicidad de las sesiones',
     glosa: 'Localidades con las ' + r.ordinarias_exigidas +
            ' sesiones ordinarias que se esperan al corte.'},
    {href: 'documentos.html', cifra: r.digitales + ' de ' + r.actas,
     nombre: 'Documentos de cada sesión',
     glosa: 'Sesiones que ya tienen cargada su planilla digital.'},
    {href: 'pendientes.html', cifra: r.con_pendientes,
     nombre: 'Qué está pendiente',
     glosa: 'Localidades con alguna sesión o documento por entregar.'},
    {href: 'detalle.html', cifra: r.localidades_con_ajustes,
     nombre: 'Detalle acta por acta',
     glosa: 'Localidades con el detalle de qué corregir en cada acta.'},
    {href: 'ajustes.html', cifra: r.actas_con_ajustes,
     nombre: 'Ajustes por localidad',
     glosa: 'Actas que necesitan algún ajuste en su registro.'}
  ];
  var nodo = document.getElementById('accesos');
  if (!nodo) return;
  nodo.innerHTML = fichas.map(function (f) {
    return '<a class="acceso" href="' + f.href + '">' +
      '<div class="cifra">' + f.cifra + '</div>' +
      '<div class="nombre">' + f.nombre + '</div>' +
      '<div class="glosa">' + f.glosa + '</div>' +
      '<span class="entrar">Ver la página &rarr;</span></a>';
  }).join('');
}

function pintarPanorama() {
  var r = D.resumen;
  franja('franja-general', [
    {v: r.sesiones_formulario, rot: 'Sesiones realizadas',
     glosa: r.ordinarias + ' ordinarias y ' + r.extraordinarias +
            ' extraordinarias en las 20 localidades.'},
    {v: r.actas, rot: 'Sesiones con acta',
     glosa: 'De ' + r.sesiones_formulario + ' reportadas al formulario.'},
    {v: r.al_dia_sesiones + ' de 20', rot: 'Localidades al día en sesiones',
     glosa: 'Hicieron las ' + r.ordinarias_exigidas +
            ' sesiones ordinarias que se esperan al corte.'},
    {v: r.sin_pendientes + ' de 20', rot: 'Localidades sin nada pendiente',
     glosa: 'Sesionaron, cargaron todo y no tienen ajustes de forma.'}
  ]);
}

function pintarResumenAjustes() {
  var r = D.resumen;
  franja('franja-ajustes', [
    {v: r.limpias, rot: 'Actas ya listas',
     glosa: 'De ' + r.actas + '. No necesitan ningún ajuste.'},
    {v: r.num_problema, rot: 'Numeración por ajustar',
     glosa: 'El número que trae el acta por dentro no coincide con el del ' +
            'archivo o quedó vacío.'},
    {v: r.rec_problema, rot: 'Recuadros por completar',
     glosa: 'Al cuadro de participantes le falta algo o sus filas no suman.'},
    {v: r.cifras_difieren, rot: 'Cifras por conciliar',
     glosa: 'De ' + r.cifras_comparables + ' sesiones comparables.'}
  ]);
}

/* ------------------------------------------------------- paginas internas */

function pintarPeriodicidad() {
  var filas = D.localidades.map(function (l) {
    return '<tr>' +
      '<td>' + l.localidad + '</td>' +
      '<td>' + bimestres(l.bimestres_con_ordinaria, l.bimestres_exigidos) +
      '</td>' +
      '<td>' + (l.faltan_ordinarias
                ? '<span class="pastilla mal">' + l.ordinarias + ' de ' +
                  l.ordinarias_exigidas + '</span>'
                : '<span class="neutro">' + l.ordinarias + '</span>') +
      '</td>' +
      '<td>' + l.extraordinarias + '</td>' +
      '<td>' + l.sesiones_formulario + '</td>' +
      '<td>' + silencio(l.dias_sin_sesionar) + '</td></tr>';
  }).join('');
  var r = D.resumen;
  document.getElementById('tabla-periodicidad').innerHTML = filas +
    '<tr class="total"><td>Total</td><td></td>' +
    '<td>' + r.ordinarias + '</td>' +
    '<td>' + r.extraordinarias + '</td>' +
    '<td>' + r.sesiones_formulario + '</td>' +
    '<td></td></tr>';

  // El conteo de localidades en silencio va en la leyenda y no en la fila de
  // total: esa fila suma columnas y una frase ahí rompe la lectura.
  var aviso = document.getElementById('resumen-silencio');
  if (aviso) {
    aviso.innerHTML = r.en_silencio
      ? 'Hoy, ' + r.en_silencio + (r.en_silencio === 1 ? ' localidad.' : ' localidades.')
      : 'Hoy, ninguna.';
  }
}

function pintarDocumentos() {
  var filas = D.localidades.map(function (l) {
    return '<tr>' +
      '<td>' + l.localidad + '</td>' +
      '<td>' + l.sesiones_formulario + '</td>' +
      '<td>' + fraccion(l.actas, l.sesiones_formulario) + '</td>' +
      '<td>' + fraccion(l.planillas, l.actas) + '</td>' +
      '<td>' + fraccion(l.digitales, l.actas) + '</td>' +
      '<td>' + chip(l.estado) + '</td></tr>';
  }).join('');
  var r = D.resumen;
  document.getElementById('tabla-documentos').innerHTML = filas +
    '<tr class="total"><td>Total</td>' +
    '<td>' + r.sesiones_formulario + '</td>' +
    '<td>' + r.actas + '</td>' +
    '<td>' + r.planillas + '</td>' +
    '<td>' + r.digitales + '</td><td></td></tr>';
}

function pintarPendientes() {
  var bloques = D.localidades.filter(function (l) {
    return l.pendientes_sesion.length || l.pendientes_carga.length;
  }).map(function (l) {
    var todos = l.pendientes_sesion.concat(l.pendientes_carga);
    return '<div class="bloque"><div class="nombre">' + l.localidad +
      '</div><ul>' + todos.map(function (p) {
        return '<li>' + p + '</li>';
      }).join('') + '</ul></div>';
  }).join('');
  document.getElementById('pendientes').innerHTML = bloques ||
    '<p>Ninguna localidad tiene sesiones ni documentos pendientes.</p>';
}

function pintarAjustes() {
  var filas = D.localidades.map(function (l) {
    var n = l.numeracion, c = l.recuadro;
    return '<tr>' +
      '<td>' + l.localidad + '</td>' +
      '<td>' + l.respuestas_formulario + '</td>' +
      '<td>' + l.sesiones_formulario + '</td>' +
      '<td>' + l.actas + '</td>' +
      '<td>' + pastilla(n.distinto + n.blanco + n.sin_linea) + '</td>' +
      '<td>' + pastilla(c.sin_recuadro + c.modificado + c.no_cuadra) + '</td>' +
      '<td>' + pastilla(l.cifras.difieren) + '</td>' +
      '<td>' + l.limpias + ' de ' + l.actas + barra(l.limpias, l.actas) +
      '</td></tr>';
  }).join('');
  var r = D.resumen;
  document.getElementById('tabla-ajustes').innerHTML = filas +
    '<tr class="total"><td>Total</td>' +
    '<td>' + r.respuestas_formulario + '</td>' +
    '<td>' + r.sesiones_formulario + '</td>' +
    '<td>' + r.actas + '</td>' +
    '<td>' + r.num_problema + '</td>' +
    '<td>' + r.rec_problema + '</td>' +
    '<td>' + r.cifras_difieren + '</td>' +
    '<td>' + r.limpias + ' de ' + r.actas + '</td></tr>';
}

function pintarDetalle() {
  document.getElementById('detalle').innerHTML =
    D.localidades.filter(function (l) { return l.detalle.length; })
    .map(function (l) {
      var items = l.detalle.map(function (d) {
        return '<div class="ajuste"><div class="archivo">' + d.archivo +
          '</div><ul>' + d.ajustes.map(function (h) {
            return '<li>' + h + '</li>';
          }).join('') + '</ul></div>';
      }).join('');
      return '<details class="localidad"><summary>' + l.localidad +
        '<span class="conteo">' + l.detalle.length +
        (l.detalle.length === 1 ? ' acta con ajustes' : ' actas con ajustes') +
        '</span></summary><div class="cuerpo">' + items + '</div></details>';
    }).join('');
}
"""


# -------------------------------------------------------------- plantillas

ESQUELETO = """<!DOCTYPE html>
<html lang="es-CO">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(pestana)s</title>
<link rel="stylesheet" href="%(raiz)srecursos/tablero.css">
</head>
<body>

<img class="banner" src="%(raiz)s%(banner)s"
     alt="Juventud en acción. Innovación para el seguimiento y la participación.
          Distrito Joven, Secretaría Distrital de Integración Social, Bogotá">

%(cabecera)s%(contenedor)s

<img class="marca-pie" src="%(raiz)s%(marca)s"
     alt="Distrito Joven, Secretaría Distrital de Integración Social">

<script src="%(raiz)sdatos/datos_colj.js"></script>
<script src="%(raiz)srecursos/tablero.js"></script>
<script>pintarCorte();%(llamada)s</script>
</body>
</html>
"""


def envoltura(pestana, pagina, llamada, es_portada=False, vuelve_a=None,
              con_corte=False):
    """Arma una página completa con la cabecera y el pie comunes.

    La portada vive en la raíz de la carpeta y las demás páginas en html/, así
    que las rutas a recursos, datos e imágenes llevan ../ en esas últimas.

    con_corte agrega el recordatorio de hasta cuándo llegan los datos. Va en
    las páginas con tablas y no en las que solo tienen enlaces.

    vuelve_a dice a dónde lleva el botón de volver. Las cinco vistas del año
    en curso regresan a zoom.html, que es de donde se entra a ellas, y no a la
    portada: volver siempre al inicio obligaría a rehacer dos clics.
    """
    raiz = "" if es_portada else "../"
    destino = vuelve_a or ("../index.html", "Inicio")
    volver = ("" if es_portada else
              '  <a class="volver" href="%s">&larr; %s</a>\n'
              % (destino[0], destino[1]))
    if es_portada:
        cabecera = pagina["titulo"]
    else:
        # El aviso de corte lo llena tablero.js con el dato del año en curso.
        # Va vacío en el HTML a propósito: si la fecha se escribiera aquí,
        # habría que acordarse de cambiarla en nueve páginas.
        aviso = ('  <p class="corte-aviso" id="corte-aviso"></p>\n'
                 if con_corte else "")
        cabecera = ('<div class="titulo-zona">\n%s%s%s</div>\n'
                    % (volver, pagina["titulo"], aviso))
    # La portada no tiene cuerpo, solo el bloque del título, así que se omite
    # el contenedor: dejarlo vacío metía un espacio muerto antes del pie.
    contenedor = ("" if not pagina["cuerpo"].strip()
                  else '\n<div class="container">%s</div>\n' % pagina["cuerpo"])
    return ESQUELETO % {"pestana": pestana, "banner": BANNER, "raiz": raiz,
                        "marca": MARCA_PIE, "cabecera": cabecera,
                        "contenedor": contenedor, "llamada": llamada}


def pagina_portada(ultima_carga, ultima_sesion):
    """La portada: el título, las fechas del registro y los tres campos."""
    titulo = """<div class="portada">
  <div class="col-izq">
    <h1>COLJ</h1>
    <p class="nombre-largo">Comités Operativos Locales de Juventud</p>
    <p class="seguimiento">Seguimiento</p>
    <p class="ultimo-registro">
      <span>Última acta cargada al formulario: <b>%s</b></span>
      <span>Último comité registrado: <b>%s</b></span>
    </p>
  </div>

  <div class="col-der">
    <p class="instruccion">Haz clic en un campo para entrar</p>
    <div class="campos" id="campos"></div>
  </div>
</div>
""" % (ultima_carga, ultima_sesion)
    return {"titulo": titulo, "cuerpo": ""}


def pagina_estadisticas():
    """Página de estadísticas generales: la serie 2024, 2025 y 2026."""
    titulo = """  <h1>Estadísticas generales</h1>
  <p class="intro">Actas archivadas en las tres vigencias. Sirve para ver cómo
     se mueve el ritmo del espacio de un año a otro.</p>
"""
    cuerpo = """
  <div class="franja" id="franja-anios"></div>

  <p class="nota-general"><strong>Nota:</strong> En 2025 se pasó de sesiones
     mensuales a ordinarias bimensuales, así que el mínimo esperado bajó de
     doce a seis al año.</p>

  <div class="rotulo-seccion">
    <h2>Por localidad</h2>
    <p>Número de sesiones con sus actas de asistencia.</p>
  </div>
  <div class="tarjeta tabla-ancha">
    <table>
      <thead>
        <tr>
          <th>Localidad</th>
          <th>Actas 2024</th>
          <th>Actas 2025</th>
          <th>Actas 2026*</th>
        </tr>
      </thead>
      <tbody id="tabla-serie"></tbody>
    </table>
  </div>
"""
    return {"titulo": titulo, "cuerpo": cuerpo}


def pagina_zoom():
    """Página que agrupa las cinco vistas de la vigencia en curso."""
    titulo = """  <h1>Zoom año en curso</h1>
  <p class="intro">Cómo va cada localidad en 2026, en cinco vistas. La cifra de
     cada acceso adelanta lo que se va a encontrar adentro.</p>
"""
    cuerpo = """
  <div class="rotulo-seccion">
    <span class="numero">1</span>
    <h2>El panorama general</h2>
    <p>Lo que pasó en las veinte localidades entre enero y julio de 2026, antes
       de mirar localidad por localidad.</p>
  </div>
  <div class="franja" id="franja-general"></div>

  <div class="rotulo-seccion">
    <span class="numero">2</span>
    <h2>Resumen de ajustes</h2>
    <p>Este bloque es para afinar el registro. Compara los documentos
       adjuntos con la tabla de seguimiento en Excel.</p>
  </div>
  <div class="franja" id="franja-ajustes"></div>

  <div class="rotulo-seccion">
    <span class="numero">3</span>
    <h2>Explora el detalle</h2>
    <p>Cada página abre una parte del seguimiento.</p>
  </div>
  <div class="accesos" id="accesos"></div>
"""
    return {"titulo": titulo, "cuerpo": cuerpo}


def pagina_enlaces():
    """Página con los accesos a donde vive cada cosa."""
    titulo = """  <h1>Enlaces</h1>
"""
    cuerpo = """
  <div class="rejilla" id="enlaces"></div>
"""
    return {"titulo": titulo, "cuerpo": cuerpo}


def pagina_periodicidad():
    """Página de periodicidad de las sesiones."""
    titulo = """  <h1>Periodicidad de las sesiones</h1>
  <p class="intro">El reglamento fija sesiones ordinarias cada dos meses, así
     que al corte se le piden tres a cada localidad. Las extraordinarias son
     adicionales y no cuentan para ese mínimo.</p>
"""
    cuerpo = """
  <p class="nota-general"><strong>Bimestre fijo o móvil.</strong> El
     calendario parte el año en bloques, pero el reglamento habla de dos meses
     entre una sesión y la siguiente. Varias localidades mantuvieron esa
     distancia y sus fechas cayeron a los lados de un corte. Por eso el
     cumplimiento se cuenta por número de sesiones ordinarias, y los cuadros
     solo muestran el ritmo del año.</p>

  <div class="leyenda">
    <div><span class="punto bien"></span>Bimestre con sesión ordinaria</div>
    <div><span class="punto mal"></span>Bimestre sin sesión ordinaria</div>
    <div>Días sin reunirse al corte, contando las extraordinarias. Se marca al
      pasar de dos meses. <span id="resumen-silencio"></span></div>
  </div>
  <div class="tarjeta tabla-ancha">
    <table>
      <thead>
        <tr>
          <th>Localidad</th>
          <th>Ritmo en el año<br>Ene-feb · Mar-abr · May-jun</th>
          <th>Sesiones<br>ordinarias</th>
          <th>Sesiones<br>extraordinarias</th>
          <th>Total<br>sesiones</th>
          <th>Días sin<br>reunirse al corte</th>
        </tr>
      </thead>
      <tbody id="tabla-periodicidad"></tbody>
    </table>
  </div>
"""
    return {"titulo": titulo, "cuerpo": cuerpo}


def pagina_documentos():
    """Página de documentos cargados por sesión."""
    titulo = """  <h1>Documentos de cada sesión</h1>
  <p class="intro">Cada sesión debería quedar con tres documentos: el acta, la
     planilla de asistencia firmada y esa misma planilla sistematizada en
     Excel. La planilla digital es la que permite analizar la asistencia sin
     transcribir a mano.</p>
"""
    cuerpo = """
  <div class="tarjeta tabla-ancha">
    <table>
      <thead>
        <tr>
          <th>Localidad</th>
          <th>Sesiones<br>reportadas</th>
          <th>Actas<br>cargadas</th>
          <th>Planilla de<br>asistencia</th>
          <th>Planilla<br>digital</th>
          <th>Estado general<br>de la localidad</th>
        </tr>
      </thead>
      <tbody id="tabla-documentos"></tbody>
    </table>
  </div>
  <div class="leyenda">
    <div><span class="chip al-dia">Al día</span> sesionó, cargó todo y no tiene
      ajustes por hacer</div>
    <div><span class="chip revisar">Ajustes de forma</span> sesionó y cargó,
      con detalles de formato por afinar en algunas actas</div>
    <div><span class="chip cargar">Por cargar</span> le falta subir algún
      documento</div>
    <div><span class="chip sesionar">Por sesionar</span> hizo menos de las tres
      sesiones ordinarias que se esperan al corte</div>
  </div>
"""
    return {"titulo": titulo, "cuerpo": cuerpo}


def pagina_pendientes():
    """Página con lo que le falta a cada localidad."""
    titulo = """  <h1>Qué está pendiente</h1>
  <p class="intro">Solo aparecen las localidades con algo por entregar. Son
     pendientes de sesión o de documento; los ajustes de forma están en la
     página de ajustes por localidad.</p>
"""
    cuerpo = """
  <div class="rejilla" id="pendientes"></div>
"""
    return {"titulo": titulo, "cuerpo": cuerpo}


def pagina_ajustes():
    """Página con los ajustes de registro por localidad."""
    titulo = """  <h1>Ajustes por localidad</h1>
  <p class="intro">Las tres primeras columnas responden cuántas sesiones hubo
     según cada fuente. Las tres siguientes cuentan actas que necesitan un
     ajuste, así que entre menos, mejor. La última resume cuántas actas de la
     localidad ya quedaron listas.</p>
"""
    cuerpo = """
  <div class="tarjeta tabla-ancha">
    <table>
      <thead>
        <tr>
          <th>Localidad</th>
          <th>Respuestas<br>en el Excel</th>
          <th>Sesiones<br>distintas</th>
          <th>Actas<br>archivadas</th>
          <th>Numeración<br>por ajustar</th>
          <th>Recuadro<br>por completar</th>
          <th>Cifras por<br>conciliar</th>
          <th>Actas<br>ya listas</th>
        </tr>
      </thead>
      <tbody id="tabla-ajustes"></tbody>
    </table>
  </div>
  <div class="leyenda">
    <div><span class="punto bien"></span>Actas ya listas</div>
    <div><span class="punto mal"></span>Actas con algún ajuste</div>
    <div>Numeración: el número que trae el acta por dentro no coincide con el
      del archivo, quedó vacío o no está.</div>
    <div>Recuadro: al cuadro de participantes le falta diligenciar algo, se
      cambió respecto al formato o sus filas no suman.</div>
  </div>
"""
    return {"titulo": titulo, "cuerpo": cuerpo}


def pagina_detalle(escaneadas):
    """Página con el detalle acta por acta."""
    titulo = """  <h1>Detalle acta por acta</h1>
  <p class="intro">Solo aparecen las localidades con algún ajuste por hacer. De
     cada acta se indica qué habría que corregir. Haz clic en una localidad
     para abrir su lista.</p>
"""
    cuerpo = """
  <div id="detalle"></div>

  <p class="pie-nota">Un alcance que conviene tener presente: la lectura de los
     PDF es automática, así que las actas guardadas como imagen escaneada no se
     pueden leer y quedan por fuera de estos conteos. Son %d. No es que tengan
     algo por ajustar, es que no se alcanzan a revisar.</p>
""" % escaneadas
    return {"titulo": titulo, "cuerpo": cuerpo}


# ------------------------------------------------------------------ salida

def css_de_fuentes():
    """Arma las reglas @font-face con las tipográficas empaquetadas.

    Cada archivo woff2 se convierte a base64 y se incrusta en el CSS. Hace
    falta porque el navegador bloquea por CORS la carga de fuentes desde
    file://, que es como se abre este tablero.
    """
    reglas = []
    for familia, peso, estilo, archivo in FUENTES:
        ruta = os.path.join(CARPETA_FUENTES, archivo)
        if not os.path.exists(ruta):
            print("  aviso: falta la fuente %s, el tablero usará la del "
                  "sistema" % archivo, file=sys.stderr)
            continue
        with open(ruta, "rb") as f:
            datos = base64.b64encode(f.read()).decode("ascii")
        reglas.append(
            "@font-face{font-family:'%s';font-style:%s;font-weight:%s;"
            "font-display:swap;"
            "src:url(data:font/woff2;base64,%s) format('woff2');}"
            % (familia, estilo, peso, datos))
    return "\n".join(reglas)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    datos = construir()
    r = datos["resumen"]

    for carpeta in (CARPETA_DATOS, CARPETA_RECURSOS):
        os.makedirs(carpeta, exist_ok=True)

    # ---- datos, en dos formatos: uno para el navegador y otro legible
    with open(os.path.join(CARPETA_DATOS, "calidad_colj_2026.json"),
              "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    with open(os.path.join(CARPETA_DATOS, "datos_colj.js"),
              "w", encoding="utf-8") as f:
        f.write("/* Datos del tablero COLJ 2026. Se entrega como .js y no como\n"
                "   .json porque el navegador bloquea fetch sobre file://, y\n"
                "   este tablero se abre con doble clic desde el disco.\n"
                "   Lo genera programas/generar_tablero_calidad_colj.py:\n"
                "   no editar a mano. */\n")
        f.write("window.DATOS_COLJ = ")
        json.dump(datos, f, ensure_ascii=False)
        f.write(";\n")

    # ---- recursos comunes
    with open(os.path.join(CARPETA_RECURSOS, "tablero.css"),
              "w", encoding="utf-8") as f:
        f.write(css_de_fuentes())
        f.write("\n")
        f.write(CSS)
    with open(os.path.join(CARPETA_RECURSOS, "tablero.js"),
              "w", encoding="utf-8") as f:
        f.write(JS_COMUN)

    # ---- las seis páginas
    paginas = [
        ("index.html", "Revisión COLJ 2026",
         pagina_portada(datos["ultima_carga"], datos["ultima_sesion"]),
         "pintarCampos();", True),
        ("estadisticas.html", "Estadísticas generales · COLJ",
         pagina_estadisticas(),
         "pintarFranjaAnios();pintarSerie();", False),
        ("zoom.html", "Zoom año en curso · COLJ 2026",
         pagina_zoom(),
         "pintarPanorama();pintarResumenAjustes();pintarAccesosZoom();", False),
        ("enlaces.html", "Enlaces · COLJ", pagina_enlaces(),
         "pintarEnlaces();", False),
        ("periodicidad.html", "Periodicidad de las sesiones · COLJ 2026",
         pagina_periodicidad(), "pintarPeriodicidad();", False),
        ("documentos.html", "Documentos de cada sesión · COLJ 2026",
         pagina_documentos(), "pintarDocumentos();", False),
        ("pendientes.html", "Qué está pendiente · COLJ 2026",
         pagina_pendientes(), "pintarPendientes();", False),
        ("ajustes.html", "Ajustes por localidad · COLJ 2026",
         pagina_ajustes(), "pintarAjustes();", False),
        ("detalle.html", "Detalle acta por acta · COLJ 2026",
         pagina_detalle(r["escaneadas"]), "pintarDetalle();", False),
    ]
    # Las cinco vistas del año en curso vuelven a zoom.html, que es de donde
    # se entra a ellas; el resto vuelve a la portada.
    vuelve_a_zoom = ("zoom.html", "Zoom año en curso")
    de_zoom = {"periodicidad.html", "documentos.html", "pendientes.html",
               "ajustes.html", "detalle.html"}
    # Todas las páginas con datos llevan el recordatorio del corte. La de
    # enlaces no, porque ahí no hay ninguna cifra que se pueda leer mal.
    con_corte = de_zoom | {"estadisticas.html", "zoom.html"}
    os.makedirs(CARPETA_HTML, exist_ok=True)
    for archivo, pestana, pagina, llamada, portada in paginas:
        vuelve = vuelve_a_zoom if archivo in de_zoom else None
        # La portada queda en la raíz; las demás páginas dentro de html/
        destino = RAIZ_TABLERO if portada else CARPETA_HTML
        with open(os.path.join(destino, archivo), "w", encoding="utf-8") as f:
            f.write(envoltura(pestana, pagina, llamada, portada, vuelve,
                              archivo in con_corte))

    # Barrido de las páginas que quedaron en la raíz de versiones anteriores
    for archivo, _, _, _, portada in paginas:
        if portada:
            continue
        sobrante = os.path.join(RAIZ_TABLERO, archivo)
        if os.path.exists(sobrante):
            os.remove(sobrante)

    print("Tablero generado en %s" % RAIZ_TABLERO)
    for archivo, _, _, _, portada in paginas:
        ruta = os.path.join(RAIZ_TABLERO if portada else CARPETA_HTML, archivo)
        etiqueta = archivo if portada else "html/" + archivo
        print("  %-26s %4d KB"
              % (etiqueta, max(1, os.path.getsize(ruta) // 1024)))
    for ruta, etiqueta in ((os.path.join(CARPETA_RECURSOS, "tablero.css"),
                            "recursos/tablero.css"),
                           (os.path.join(CARPETA_RECURSOS, "tablero.js"),
                            "recursos/tablero.js"),
                           (os.path.join(CARPETA_DATOS, "datos_colj.js"),
                            "datos/datos_colj.js"),
                           (EXCEL_ENLACES, "actualizacion/enlaces.xlsx")):
        print("  %-26s %4d KB" % (etiqueta, max(1, os.path.getsize(ruta) // 1024)))
    print()
    print("Portada | sesiones %d | actas %d | al día en sesiones %d de 20 | "
          "sin nada pendiente %d de 20"
          % (r["sesiones_formulario"], r["actas"], r["al_dia_sesiones"],
             r["sin_pendientes"]))
    print("Ajustes | ya listas %d | numeración %d | recuadro %d | cifras %d"
          % (r["limpias"], r["num_problema"], r["rec_problema"],
             r["cifras_difieren"]))


if __name__ == "__main__":
    main()
