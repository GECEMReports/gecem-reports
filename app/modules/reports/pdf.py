import io
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    Image,
)
from pathlib import Path


def generar_reporte_cliente_pdf(
    falla: dict,
    equipment: dict,
    contenido: dict,
    refacciones: list[dict],
    pasos: list[dict],
    fotos_por_paso: dict[int, list[str]],
) -> io.BytesIO:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5 * inch)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "Title2", parent=styles["Heading1"], fontSize=20,
        spaceAfter=6, textColor=colors.HexColor("#1a1a1a"),
    )
    subtitle_style = ParagraphStyle(
        "Sub2", parent=styles["Heading2"], fontSize=13,
        spaceAfter=4, textColor=colors.HexColor("#333333"),
    )
    normal_style = ParagraphStyle(
        "Norm2", parent=styles["Normal"], fontSize=10, spaceAfter=3, leading=14,
    )
    small_style = ParagraphStyle(
        "Small2", parent=styles["Normal"], fontSize=8,
        textColor=colors.HexColor("#888888"),
    )

    elements = []

    # Header
    elements.append(Paragraph("GECEM Reports", title_style))
    elements.append(Paragraph("Reporte de Reparacion", subtitle_style))
    elements.append(Spacer(1, 6))

    fecha = datetime.now().strftime("%d/%m/%Y")
    elements.append(Paragraph(f"Fecha: {fecha}", small_style))
    elements.append(Spacer(1, 12))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#dddddd")))
    elements.append(Spacer(1, 12))

    # Equipment info
    elements.append(Paragraph("Equipo", subtitle_style))
    brand = equipment.get("brand", "")
    model = equipment.get("model", "")
    equip_data = [
        ["Marca/Modelo:", f"{brand} {model}"],
        ["Serie:", equipment.get("serial_number", "N/A")],
        ["Horas:", f"{equipment.get('hours', 0):,.1f}"],
    ]
    if equipment.get("year"):
        equip_data.append(["Año:", str(equipment["year"])])
    equip_table = Table(equip_data, colWidths=[2 * inch, 4 * inch])
    equip_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#666666")),
        ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#1a1a1a")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(equip_table)
    elements.append(Spacer(1, 16))

    # Resumen ejecutivo
    if contenido.get("resumen_ejecutivo"):
        elements.append(Paragraph("Resumen", subtitle_style))
        elements.append(Paragraph(contenido["resumen_ejecutivo"], normal_style))
        elements.append(Spacer(1, 12))

    # Diagnóstico
    if contenido.get("diagnostico"):
        elements.append(Paragraph("Diagnostico", subtitle_style))
        elements.append(Paragraph(contenido["diagnostico"], normal_style))
        elements.append(Spacer(1, 12))

    # Trabajo realizado
    if contenido.get("trabajo_realizado"):
        elements.append(Paragraph("Trabajo Realizado", subtitle_style))
        elements.append(Paragraph(contenido["trabajo_realizado"], normal_style))
        elements.append(Spacer(1, 12))

    # Pasos de reparación con fotos
    if pasos:
        elements.append(Paragraph("Procedimiento", subtitle_style))
        for paso in pasos:
            num = paso.get("numero_paso", 0)
            desc = paso.get("descripcion", "")
            tiempo = paso.get("tiempo_minutos", 0)
            elements.append(Paragraph(
                f"<b>Paso {num}</b> ({tiempo} min): {desc}",
                normal_style,
            ))
            # Add photos if available
            fotos = fotos_por_paso.get(num, [])
            for foto_path in fotos:
                if Path(foto_path).exists():
                    try:
                        img = Image(foto_path, width=3 * inch, height=2.25 * inch)
                        elements.append(img)
                        elements.append(Spacer(1, 4))
                    except Exception:
                        pass
        elements.append(Spacer(1, 12))

    # Refacciones utilizadas
    if contenido.get("refacciones_utilizadas"):
        elements.append(Paragraph("Refacciones Utilizadas", subtitle_style))
        elements.append(Paragraph(contenido["refacciones_utilizadas"], normal_style))
    elif refacciones:
        elements.append(Paragraph("Refacciones Utilizadas", subtitle_style))
        ref_text = "\n".join(
            f"- {r.get('nombre', 'N/A')} x{r.get('cantidad', 1)}"
            for r in refacciones
        )
        elements.append(Paragraph(ref_text, normal_style))
    elements.append(Spacer(1, 12))

    # Recomendaciones
    if contenido.get("recomendaciones"):
        elements.append(Paragraph("Recomendaciones", subtitle_style))
        elements.append(Paragraph(contenido["recomendaciones"], normal_style))
        elements.append(Spacer(1, 12))

    # Garantía
    if contenido.get("garantia"):
        elements.append(Paragraph("Garantia", subtitle_style))
        elements.append(Paragraph(contenido["garantia"], normal_style))
        elements.append(Spacer(1, 12))

    # Footer
    elements.append(Spacer(1, 24))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#dddddd")))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(
        "Reporte generado por GECEM Reports",
        small_style,
    ))

    doc.build(elements)
    buffer.seek(0)
    return buffer
