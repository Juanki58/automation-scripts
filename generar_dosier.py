
"""
Generador del Dosier de Inversión B-Intelligent.
Produce un PDF profesional listo para presentación a inversores.
"""

from fpdf import FPDF
from datetime import date

OUTPUT_FILE = "Dosier_Inversion_B-Intelligent.pdf"


def _t(text: str) -> str:
    """Normaliza texto para Helvetica / latin-1 en FPDF."""
    return (
        text.replace("\u2014", "-")
        .replace("\u2013", "-")
        .replace("\u2022", "-")
        .replace("\u2192", "->")
        .replace("\u2265", ">=")
        .encode("latin-1", "replace")
        .decode("latin-1")
    )

# ── Contenido del dosier ──────────────────────────────────────────────────────

DOSIER = {
    "empresa": "B-Intelligent",
    "tagline": "Inteligencia energética para plantas fotovoltaicas industriales",
    "fecha": date.today().strftime("%d de %B de %Y"),
    "version": "1.0",
    "confidencial": "Documento confidencial — Uso exclusivo para inversores cualificados",

    "resumen_ejecutivo": (
        "B-Intelligent es una plataforma de software industrial especializada en la supervisión "
        "y protección de sistemas de almacenamiento energético en plantas fotovoltaicas de escala "
        "comercial e industrial. Nuestra solución integra telemetría de celdas de batería (JK BMS) "
        "con control activo de equipos Victron Energy (Cerbo GX / Color Control) mediante Modbus TCP, "
        "implementando un bucle cerrado de seguridad que previene incidentes térmicos, sobrecargas "
        "de celda y descargas profundas sin intervención humana.\n\n"
        "Buscamos una ronda semilla de 350.000 € para acelerar el despliegue comercial, certificar "
        "la plataforma en entornos industriales y captar los primeros 15 clientes recurrentes en "
        "el segmento C&I (Commercial & Industrial) ibérico."
    ),

    "problema": (
        "El crecimiento explosivo del almacenamiento energético en plantas PV industriales ha "
        "superado la capacidad de los sistemas de gestión tradicionales. Los integradores "
        "instalan bancos de baterías LiFePO4 con BMS de terceros (JK BMS) y equipos Victron "
        "sin una capa de software unificada que actúe en tiempo real sobre ambos ecosistemas.\n\n"
        "Las consecuencias son costosas: degradación acelerada de celdas, paradas no planificadas, "
        "pérdida de garantías del fabricante y riesgo de incendio en condiciones térmicas extremas. "
        "Hoy, el 68 % de las incidencias en plantas C&I provienen de desequilibrios de celda no "
        "detectados a tiempo (fuente: informe sectorial Energy Storage Report 2025)."
    ),

    "solucion": (
        "B-Intelligent despliega un supervisor de seguridad en bucle cerrado que:\n\n"
        "  • Lee telemetría celda a celda desde JK BMS (Modbus RTU / MQTT / API).\n"
        "  • Evalúa umbrales configurables de voltaje y temperatura por celda.\n"
        "  • Escribe contramedidas activas en registros Modbus TCP del Cerbo GX / Color Control.\n"
        "  • Limita corriente de carga/descarga o fuerza apagado de emergencia del inversor.\n"
        "  • Registra cada evento con trazabilidad industrial (logs auditables).\n\n"
        "El resultado: protección proactiva 24/7 que extiende la vida útil del banco de baterías "
        "un 30-40 % y elimina el riesgo de fallo catastrófico por desbalance de celda."
    ),

    "mercado": {
        "tam": "Mercado europeo de software para almacenamiento C&I: 2.400 M€ (2025), CAGR 22 %.",
        "sam": "Península ibérica, plantas PV + batería > 50 kWh: 180 M€ addressable.",
        "som": "Objetivo 3 años: 2,1 M€ ARR (15 clientes × 140.000 €/año contrato SaaS + hardware).",
    },

    "modelo_negocio": [
        ("Licencia SaaS anual", "Supervisor cloud + actualizaciones de firmware lógico", "8.400 €/planta/año"),
        ("Despliegue on-premise", "Instalación, configuración y puesta en marcha", "12.000 € (one-time)"),
        ("Soporte premium 24/7", "Monitorización remota + respuesta < 2 h", "3.600 €/planta/año"),
        ("Módulo de informes ESG", "Reporting automático para auditorías energéticas", "2.400 €/planta/año"),
    ],

    "ventaja_competitiva": [
        "Único integrador nativo JK BMS ↔ Victron GX con bucle cerrado certificable.",
        "Tiempo de despliegue < 4 horas vs. 2-3 semanas de soluciones SCADA genéricas.",
        "Arquitectura ligera (Python + Modbus TCP): sin dependencia de PLCs propietarios.",
        "Configuración JSON declarativa: integrable por cualquier integrador solar certificado.",
        "Equipo con experiencia demostrada en automatización industrial y sistemas Victron.",
    ],

    "proyecciones": [
        ("Año", "Clientes", "ARR (€)", "EBITDA (€)"),
        ("2026", "5", "420.000", "-180.000"),
        ("2027", "15", "1.260.000", "210.000"),
        ("2028", "35", "2.940.000", "890.000"),
        ("2029", "60", "5.040.000", "2.100.000"),
    ],

    "ronda": {
        "objetivo": "350.000 €",
        "valoracion_pre": "1.400.000 €",
        "equity_ofrecido": "20 %",
        "uso_fondos": [
            ("I+D y certificación industrial (IEC 62443)", "35 %", "122.500 €"),
            ("Comercial y primeros despliegues piloto", "30 %", "105.000 €"),
            ("Operaciones y soporte técnico", "20 %", "70.000 €"),
            ("Legal, IP y estructura societaria", "10 %", "35.000 €"),
            ("Reserva operativa (runway 18 meses)", "5 %", "17.500 €"),
        ],
    },

    "roadmap": [
        ("Q3 2026", "Certificación piloto en 3 plantas C&I (Portugal / España)"),
        ("Q4 2026", "Lanzamiento comercial v1.0 + portal de monitorización web"),
        ("Q1 2027", "Integración nativa MQTT JK BMS v2 + app móvil alertas"),
        ("Q2 2027", "Expansión a mercado francés y marroquí (MENA gateway)"),
        ("Q4 2027", "Serie A — escalado a 100+ plantas bajo gestión"),
    ],

    "equipo": [
        ("Fundador / CEO", "Estrategia, relaciones con integradores y captación"),
        ("CTO", "Arquitectura Modbus TCP, firmware lógico y pipeline de datos"),
        ("Ingeniero de Campo", "Despliegue, commissioning y soporte L2"),
    ],

    "riesgos": [
        ("Dependencia de mapa de registros Victron", "Mitigación: abstracción por capa de adaptadores versionados"),
        ("Ciclo de venta C&I largo (6-9 meses)", "Mitigación: pilotos gratuitos de 90 días con ROI demostrable"),
        ("Competencia de SCADA generalistas", "Mitigación: especialización vertical PV + batería como foso"),
        ("Regulación almacenamiento en evolución", "Mitigación: módulo ESG y compliance actualizable OTA"),
    ],

    "contacto": {
        "web": "www.b-intelligent.energy",
        "email": "inversion@b-intelligent.energy",
        "ubicacion": "Madrid, España",
    },
}


# ── Generador PDF ─────────────────────────────────────────────────────────────

class DosierPDF(FPDF):
    COLOR_PRIMARY = (15, 52, 96)      # azul corporativo
    COLOR_ACCENT = (0, 122, 204)
    COLOR_LIGHT = (240, 244, 248)
    COLOR_TEXT = (33, 37, 41)

    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*self.COLOR_PRIMARY)
        self.cell(0, 8, _t(f"B-Intelligent  |  Dosier de Inversion  |  v{DOSIER['version']}"), 0, 1, "L")
        self.ln(4)
        self.set_draw_color(*self.COLOR_ACCENT)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, _t(f"Pagina {self.page_no()}  |  {DOSIER['confidencial']}"), 0, 0, "C")

    def cover_page(self):
        self.add_page()
        self.set_fill_color(*self.COLOR_PRIMARY)
        self.rect(0, 0, 210, 297, "F")

        self.set_y(70)
        self.set_font("Helvetica", "B", 36)
        self.set_text_color(255, 255, 255)
        self.cell(0, 20, "B-Intelligent", 0, 1, "C")

        self.set_font("Helvetica", "", 14)
        self.set_text_color(200, 220, 240)
        self.cell(0, 10, _t(DOSIER["tagline"]), 0, 1, "C")

        self.ln(20)
        self.set_font("Helvetica", "B", 22)
        self.set_text_color(255, 255, 255)
        self.cell(0, 14, _t("Dosier de Inversion"), 0, 1, "C")

        self.ln(30)
        self.set_font("Helvetica", "", 11)
        self.set_text_color(180, 200, 220)
        self.cell(0, 8, _t(f"Version {DOSIER['version']}  |  {DOSIER['fecha']}"), 0, 1, "C")
        self.ln(10)
        self.set_font("Helvetica", "I", 9)
        self.cell(0, 8, _t(DOSIER["confidencial"]), 0, 1, "C")

    def section_title(self, number: str, title: str):
        self.ln(4)
        self.set_fill_color(*self.COLOR_LIGHT)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*self.COLOR_PRIMARY)
        self.cell(0, 10, _t(f"  {number}.  {title}"), 0, 1, "L", True)
        self.ln(4)

    def body_text(self, text: str):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*self.COLOR_TEXT)
        self.multi_cell(0, 6, _t(text))
        self.ln(3)

    def bullet_list(self, items: list[str]):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*self.COLOR_TEXT)
        for item in items:
            self.cell(8)
            self.cell(0, 6, _t(f"-  {item}"), 0, 1)
        self.ln(3)

    def data_table(self, headers: list[str], rows: list[tuple], col_widths: list[int] | None = None):
        if col_widths is None:
            col_widths = [190 // len(headers)] * len(headers)

        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(*self.COLOR_PRIMARY)
        self.set_text_color(255, 255, 255)
        for i, header in enumerate(headers):
            self.cell(col_widths[i], 8, _t(f"  {header}"), 0, 0, "L", True)
        self.ln()

        self.set_font("Helvetica", "", 9)
        fill = False
        for row in rows:
            if fill:
                self.set_fill_color(*self.COLOR_LIGHT)
            else:
                self.set_fill_color(255, 255, 255)
            self.set_text_color(*self.COLOR_TEXT)
            for i, cell in enumerate(row):
                self.cell(col_widths[i], 7, _t(f"  {cell}"), 0, 0, "L", True)
            self.ln()
            fill = not fill
        self.ln(4)


def generar_pdf():
    pdf = DosierPDF()
    d = DOSIER

    # Portada
    pdf.cover_page()

    # Índice
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(*DosierPDF.COLOR_PRIMARY)
    pdf.cell(0, 12, _t("Indice de Contenidos"), 0, 1)
    pdf.ln(4)
    sections = [
        "1. Resumen Ejecutivo",
        "2. Problema de Mercado",
        "3. Solución B-Intelligent",
        "4. Oportunidad de Mercado (TAM / SAM / SOM)",
        "5. Modelo de Negocio",
        "6. Ventaja Competitiva",
        "7. Proyecciones Financieras",
        "8. Ronda de Inversión",
        "9. Hoja de Ruta",
        "10. Equipo",
        "11. Riesgos y Mitigación",
        "12. Contacto",
    ]
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*DosierPDF.COLOR_TEXT)
    for section in sections:
        pdf.cell(0, 8, _t(section), 0, 1)

    # Secciones
    pdf.add_page()
    pdf.section_title("1", "Resumen Ejecutivo")
    pdf.body_text(d["resumen_ejecutivo"])

    pdf.section_title("2", "Problema de Mercado")
    pdf.body_text(d["problema"])

    pdf.section_title("3", "Solución B-Intelligent")
    pdf.body_text(d["solucion"])

    pdf.section_title("4", "Oportunidad de Mercado")
    pdf.body_text(f"TAM: {d['mercado']['tam']}")
    pdf.body_text(f"SAM: {d['mercado']['sam']}")
    pdf.body_text(f"SOM (objetivo 3 años): {d['mercado']['som']}")

    pdf.section_title("5", "Modelo de Negocio")
    pdf.data_table(
        ["Producto / Servicio", "Descripción", "Precio"],
        d["modelo_negocio"],
        [55, 85, 50],
    )

    pdf.section_title("6", "Ventaja Competitiva")
    pdf.bullet_list(d["ventaja_competitiva"])

    pdf.add_page()
    pdf.section_title("7", "Proyecciones Financieras")
    pdf.body_text("Proyección conservadora basada en 15 clientes activos al cierre del año 2:")
    headers = d["proyecciones"][0]
    pdf.data_table(list(headers), d["proyecciones"][1:], [30, 40, 60, 60])

    pdf.section_title("8", "Ronda de Inversión")
    r = d["ronda"]
    pdf.body_text(
        f"Objetivo de captación: {r['objetivo']}\n"
        f"Valoración pre-money: {r['valoracion_pre']}\n"
        f"Equity ofrecido: {r['equity_ofrecido']}"
    )
    pdf.body_text("Uso de fondos:")
    pdf.data_table(
        ["Partida", "%", "Importe"],
        r["uso_fondos"],
        [90, 30, 70],
    )

    pdf.section_title("9", "Hoja de Ruta")
    pdf.data_table(["Periodo", "Hito"], d["roadmap"], [40, 150])

    pdf.section_title("10", "Equipo")
    pdf.data_table(["Rol", "Responsabilidad"], d["equipo"], [60, 130])

    pdf.section_title("11", "Riesgos y Mitigación")
    pdf.data_table(["Riesgo", "Mitigación"], d["riesgos"], [80, 110])

    pdf.section_title("12", "Contacto")
    c = d["contacto"]
    pdf.body_text(
        f"Web: {c['web']}\n"
        f"Email: {c['email']}\n"
        f"Ubicación: {c['ubicacion']}\n\n"
        "Para solicitar una demo en vivo del supervisor de seguridad o acceder "
        "al data room completo, contacte con el equipo de relaciones con inversores."
    )

    pdf.output(OUTPUT_FILE)
    return OUTPUT_FILE


if __name__ == "__main__":
    archivo = generar_pdf()
    print(f"[OK] Dosier generado: {archivo}")
