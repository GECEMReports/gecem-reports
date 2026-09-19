import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable


def generar_cotizacion_pdf(falla, equipment, cotizacion, refacciones):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5 * inch)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle("Title2", parent=styles["Heading1"], fontSize=18, spaceAfter=6, textColor=colors.HexColor("#1a1a1a"))
    subtitle_style = ParagraphStyle("Sub2", parent=styles["Heading2"], fontSize=12, spaceAfter=4, textColor=colors.HexColor("#444444"))
    normal_style = ParagraphStyle("Norm2", parent=styles["Normal"], fontSize=10, spaceAfter=3)
    small_style = ParagraphStyle("Small2", parent=styles["Normal"], fontSize=8, textColor=colors.HexColor("#888888"))

    elements = []
    elements.append(Paragraph("GECEM Reports", title_style))
    elements.append(Paragraph("Cotizacion de Reparacion", subtitle_style))
    elements.append(Spacer(1, 12))

    fecha = datetime.now().strftime("%d/%m/%Y")
    status = cotizacion.get("status", "borrador").upper()
    elements.append(Paragraph(f"Fecha: {fecha}  |  Status: {status}", small_style))
    elements.append(Spacer(1, 12))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#dddddd")))
    elements.append(Spacer(1, 12))

    # Equipment
    elements.append(Paragraph("Equipo", subtitle_style))
    brand = equipment.get("brand", "")
    model = equipment.get("model", "")
    equip_data = [
        ["Marca/Modelo:", f"{brand} {model}"],
        ["Serie:", equipment.get("serial_number", "N/A")],
        ["Horas:", f"{equipment.get('hours', 0):,.1f}"],
    ]
    equip_table = Table(equip_data, colWidths=[2 * inch, 4 * inch])
    equip_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#666666")),
        ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#1a1a1a")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(equip_table)
    elements.append(Spacer(1, 16))

    # Falla
    elements.append(Paragraph("Falla", subtitle_style))
    parte = falla.get("parte", "")
    pieza = falla.get("pieza", "")
    elements.append(Paragraph(f"<b>{parte} - {pieza}</b>", normal_style))
    elements.append(Paragraph(falla.get("descripcion", ""), normal_style))
    elements.append(Spacer(1, 16))

    # Refacciones
    elements.append(Paragraph("Refacciones", subtitle_style))
    if refacciones:
        ref_data = [["Refaccion", "P/N", "Cant.", "Precio Unit.", "Total"]]
        for r in refacciones:
            precio = r.get("precio_unitario", 0) or 0
            cant = r.get("cantidad", 1)
            ref_data.append([
                r.get("nombre", ""),
                r.get("numero_parte", "-") or "-",
                str(int(cant)),
                f"${precio:,.2f}",
                f"${precio * cant:,.2f}",
            ])
        subtotal = cotizacion.get("subtotal_refacciones", 0)
        ref_data.append(["", "", "", "Subtotal:", f"${subtotal:,.2f}"])

        ref_table = Table(ref_data, colWidths=[2.5 * inch, 1.2 * inch, 0.6 * inch, 1.1 * inch, 1.1 * inch])
        ref_table.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
            ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ]))
        elements.append(ref_table)
    else:
        elements.append(Paragraph("Sin refacciones registradas.", normal_style))
    elements.append(Spacer(1, 16))

    # Totals
    elements.append(Paragraph("Resumen", subtitle_style))
    subtotal = cotizacion.get("subtotal_refacciones", 0)
    mano = cotizacion.get("mano_de_obra", 0)
    total = cotizacion.get("total", 0)
    moneda = cotizacion.get("moneda", "MXN")
    totals_data = [
        ["Refacciones:", f"${subtotal:,.2f} {moneda}"],
        ["Mano de obra:", f"${mano:,.2f} {moneda}"],
        ["TOTAL:", f"${total:,.2f} {moneda}"],
    ]
    totals_table = Table(totals_data, colWidths=[4.5 * inch, 2 * inch])
    totals_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTSIZE", (-1, -1), (-1, -1), 12),
        ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor("#1a1a1a")),
    ]))
    elements.append(totals_table)

    if cotizacion.get("notas"):
        elements.append(Spacer(1, 16))
        elements.append(Paragraph("Notas", subtitle_style))
        elements.append(Paragraph(cotizacion["notas"], normal_style))

    doc.build(elements)
    buffer.seek(0)
    return buffer
