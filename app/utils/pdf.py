import io
from datetime import datetime, timedelta, timezone

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
)


def _p(text, style):
    """Wrap text in Paragraph for proper cell wrapping."""
    return Paragraph(str(text), style)


def generar_cotizacion_pdf(falla, equipment, cotizacion, refacciones):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5 * inch)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "Title2", parent=styles["Heading1"], fontSize=18,
        spaceAfter=6, textColor=colors.HexColor("#1a1a1a"),
    )
    subtitle_style = ParagraphStyle(
        "Sub2", parent=styles["Heading2"], fontSize=12,
        spaceAfter=4, textColor=colors.HexColor("#444444"),
    )
    normal_style = ParagraphStyle(
        "Norm2", parent=styles["Normal"], fontSize=10, spaceAfter=3,
    )
    small_style = ParagraphStyle(
        "Small2", parent=styles["Normal"], fontSize=8,
        textColor=colors.HexColor("#888888"),
    )
    cell_style = ParagraphStyle(
        "Cell", parent=styles["Normal"], fontSize=9,
        leading=11, wordWrap="CJK",
    )
    cell_bold_style = ParagraphStyle(
        "CellBold", parent=cell_style, fontName="Helvetica-Bold",
    )
    header_style = ParagraphStyle(
        "CellHeader", parent=styles["Normal"], fontSize=9,
        fontName="Helvetica-Bold", textColor=colors.HexColor("#333333"),
    )

    # Column widths: Refaccion(2.3) + P/N(1.4) + Cant(0.5) + Precio(1.3) + Total(1.3) = 6.8in
    col_widths = [2.3 * inch, 1.4 * inch, 0.5 * inch, 1.3 * inch, 1.3 * inch]

    elements = []

    # Header
    elements.append(Paragraph("GECEM Reports", title_style))
    elements.append(Paragraph("Cotizacion de Reparacion", subtitle_style))
    elements.append(Spacer(1, 12))

    # Date and status
    fecha = datetime.now().strftime("%d/%m/%Y")
    status = cotizacion.get("status", "borrador").upper()
    vencimiento = cotizacion.get("fecha_vencimiento")
    if vencimiento:
        if isinstance(vencimiento, str):
            fecha_venc = vencimiento[:10]
        else:
            fecha_venc = vencimiento.strftime("%d/%m/%Y")
    else:
        fecha_venc = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%d/%m/%Y")

    elements.append(Paragraph(
        f"Fecha: {fecha}  |  Valida hasta: {fecha_venc}  |  Status: {status}",
        small_style,
    ))
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

    # Refacciones table
    elements.append(Paragraph("Refacciones", subtitle_style))
    if refacciones:
        ref_data = [
            [
                _p("Refaccion", header_style),
                _p("P/N", header_style),
                _p("Cant.", header_style),
                _p("Precio Unit.", header_style),
                _p("Total", header_style),
            ]
        ]
        for r in refacciones:
            precio = r.get("precio_unitario", 0) or 0
            cant = r.get("cantidad", 1)
            ref_data.append([
                _p(r.get("nombre", ""), cell_style),
                _p(r.get("numero_parte", "-") or "-", cell_style),
                _p(str(int(cant)), cell_style),
                _p(f"${precio:,.2f}", cell_style),
                _p(f"${precio * cant:,.2f}", cell_bold_style),
            ])

        subtotal = cotizacion.get("subtotal_refacciones", 0)
        ref_data.append([
            "", "", "",
            _p("<b>Subtotal:</b>", cell_bold_style),
            _p(f"<b>${subtotal:,.2f}</b>", cell_bold_style),
        ])

        ref_table = Table(ref_data, colWidths=col_widths, repeatRows=1)
        ref_table.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
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
        ["IVA:", "Incluido"],
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

    # Notes
    elements.append(Spacer(1, 8))
    elements.append(Paragraph(
        "Todos los precios incluyen IVA.",
        small_style,
    ))

    if cotizacion.get("notas"):
        elements.append(Spacer(1, 16))
        elements.append(Paragraph("Notas", subtitle_style))
        elements.append(Paragraph(cotizacion["notas"], normal_style))

    # Footer
    elements.append(Spacer(1, 24))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#dddddd")))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(
        f"Cotizacion generada por GECEM Reports  |  Valida hasta: {fecha_venc}",
        small_style,
    ))

    doc.build(elements)
    buffer.seek(0)
    return buffer
