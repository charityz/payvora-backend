# from reportlab.lib.pagesizes import A4
# from reportlab.lib import colors
# from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
# from reportlab.lib.units import cm
# from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
# from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
# import urllib.request
# import io

# def generate_receipt_pdf(
#     reference: str,
#     business_name: str,
#     logo_url: str,
#     customer_email: str,
#     amount: float,
#     payment_method: str,
#     date: str,
#     purpose: str = "", 
#     status: str = "Successful",
# ) -> bytes:
#     buffer = io.BytesIO()
#     doc = SimpleDocTemplate(
#         buffer,
#         pagesize=A4,
#         rightMargin=2*cm,
#         leftMargin=2*cm,
#         topMargin=2*cm,
#         bottomMargin=2*cm,
#     )

#     styles = getSampleStyleSheet()
#     elements = []

#     # ── HEADER STYLE ──
#     header_style = ParagraphStyle(
#         "header", fontSize=22, textColor=colors.HexColor("#6366f1"),
#         alignment=TA_CENTER, fontName="Helvetica-Bold", spaceAfter=4,
#     )
#     sub_style = ParagraphStyle(
#         "sub", fontSize=10, textColor=colors.HexColor("#6b7280"),
#         alignment=TA_CENTER, spaceAfter=2,
#     )
#     label_style = ParagraphStyle(
#         "label", fontSize=9, textColor=colors.HexColor("#6b7280"),
#         fontName="Helvetica", spaceAfter=2,
#     )
#     value_style = ParagraphStyle(
#         "value", fontSize=11, textColor=colors.HexColor("#111827"),
#         fontName="Helvetica-Bold", spaceAfter=2,
#     )
#     amount_style = ParagraphStyle(
#         "amount", fontSize=28, textColor=colors.HexColor("#16a34a"),
#         alignment=TA_CENTER, fontName="Helvetica-Bold", spaceAfter=4,
#     )
#     footer_style = ParagraphStyle(
#         "footer", fontSize=8, textColor=colors.HexColor("#9ca3af"),
#         alignment=TA_CENTER,
#     )

#     # ── LOGO ──
#     if logo_url:
#         try:
#             from reportlab.platypus import Image as RLImage
#             import urllib.request
#             with urllib.request.urlopen(logo_url, timeout=5) as response:
#                 logo_data = io.BytesIO(response.read())
#             logo = RLImage(logo_data, width=3*cm, height=3*cm)
#             logo.hAlign = "CENTER"
#             elements.append(logo)
#             elements.append(Spacer(1, 0.3*cm))
#         except:
#             pass

#     # ── BUSINESS NAME ──
#     elements.append(Paragraph(business_name, header_style))
#     elements.append(Paragraph("Payment Receipt", sub_style))
#     elements.append(Spacer(1, 0.3*cm))
#     elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e5e7eb")))
#     elements.append(Spacer(1, 0.5*cm))

#     # ── AMOUNT ──
#     elements.append(Paragraph("Amount Paid", ParagraphStyle("al", fontSize=10, textColor=colors.HexColor("#6b7280"), alignment=TA_CENTER)))
#     elements.append(Paragraph(f"₦{amount:,.0f}", amount_style))
#     elements.append(Spacer(1, 0.5*cm))

#     # ── STATUS BADGE ──
#     status_color = colors.HexColor("#16a34a") if status == "Successful" else colors.HexColor("#dc2626")
#     status_data = [[Paragraph(f"✓  {status}", ParagraphStyle("s", fontSize=10, textColor=status_color, fontName="Helvetica-Bold", alignment=TA_CENTER))]]
#     status_table = Table(status_data, colWidths=[8*cm])
#     status_table.setStyle(TableStyle([
#         ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#f0fdf4")),
#         ("ROUNDEDCORNERS", [8]),
#         ("ALIGN", (0,0), (-1,-1), "CENTER"),
#         ("TOPPADDING", (0,0), (-1,-1), 8),
#         ("BOTTOMPADDING", (0,0), (-1,-1), 8),
#         ("BOX", (0,0), (-1,-1), 0.5, colors.HexColor("#86efac")),
#     ]))
#     status_table.hAlign = "CENTER"
#     elements.append(status_table)
#     elements.append(Spacer(1, 0.8*cm))

#     # ── TRANSACTION DETAILS TABLE ──
#     details = [
#         ["Reference", reference],
#         ["Customer Email", customer_email],
#         ["Business", business_name],
#         ["Purpose", purpose or "—"],
#         ["Payment Method", payment_method.title()],
#         ["Date", date],
#         ["Status", status],
#     ]

#     detail_table_data = []
#     for key, val in details:
#         detail_table_data.append([
#             Paragraph(key, ParagraphStyle("k", fontSize=9, textColor=colors.HexColor("#6b7280"), fontName="Helvetica")),
#             Paragraph(str(val), ParagraphStyle("v", fontSize=10, textColor=colors.HexColor("#111827"), fontName="Helvetica-Bold")),
#         ])

#     detail_table = Table(detail_table_data, colWidths=[5*cm, 11*cm])
#     detail_table.setStyle(TableStyle([
#         ("BACKGROUND", (0,0), (-1,-1), colors.white),
#         ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.HexColor("#f9fafb"), colors.white]),
#         ("TOPPADDING", (0,0), (-1,-1), 10),
#         ("BOTTOMPADDING", (0,0), (-1,-1), 10),
#         ("LEFTPADDING", (0,0), (-1,-1), 12),
#         ("RIGHTPADDING", (0,0), (-1,-1), 12),
#         ("BOX", (0,0), (-1,-1), 0.5, colors.HexColor("#e5e7eb")),
#         ("LINEBELOW", (0,0), (-1,-2), 0.5, colors.HexColor("#f3f4f6")),
#         ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
#     ]))
#     elements.append(detail_table)
#     elements.append(Spacer(1, 1*cm))

#     # ── FOOTER ──
#     elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e5e7eb")))
#     elements.append(Spacer(1, 0.3*cm))
#     elements.append(Paragraph("This is an official receipt generated by Payvora.", footer_style))
#     elements.append(Paragraph("Keep this document as proof of your payment.", footer_style))
#     elements.append(Spacer(1, 0.2*cm))
#     elements.append(Paragraph("Powered by Payvora — Secure Payment Infrastructure", ParagraphStyle("fp", fontSize=8, textColor=colors.HexColor("#6366f1"), alignment=TA_CENTER)))

#     doc.build(elements)
#     buffer.seek(0)
#     return buffer.read()





from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
import io

W, H = A4

INDIGO_DARK  = colors.HexColor("#4338ca")
INDIGO       = colors.HexColor("#6366f1")
INDIGO_LIGHT = colors.HexColor("#eef2ff")
GREEN        = colors.HexColor("#16a34a")
GREEN_LIGHT  = colors.HexColor("#f0fdf4")
GREEN_BORDER = colors.HexColor("#86efac")
GRAY_100     = colors.HexColor("#f3f4f6")
GRAY_200     = colors.HexColor("#e5e7eb")
GRAY_400     = colors.HexColor("#9ca3af")
GRAY_800     = colors.HexColor("#1f2937")
WHITE        = colors.white


def draw_page(c, data):
    page_w, page_h = A4

    # ── HEADER BAND ──
    header_h = 7.2 * cm
    c.setFillColor(INDIGO_DARK)
    c.rect(0, page_h - header_h, page_w, header_h, fill=1, stroke=0)

    # Diagonal stripe decoration
    c.setFillColor(colors.HexColor("#4f46e5"))
    for i in range(8):
        x = page_w - (i * 1.8 * cm) - 2 * cm
        c.setFillAlpha(0.08)
        c.rect(x, page_h - header_h, 0.9 * cm, header_h, fill=1, stroke=0)
    c.setFillAlpha(1)

    # ── BUSINESS NAME ──
    biz = data.get("business_name", "Business")
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(1.8 * cm, page_h - 2.4 * cm, biz.upper())

    c.setFont("Helvetica", 10)
    c.setFillColor(colors.HexColor("#c7d2fe"))
    c.drawString(1.8 * cm, page_h - 3.1 * cm, "OFFICIAL PAYMENT RECEIPT")

    # ── LOGO (right side) ──
    logo_url = data.get("logo_url", "")
    logo_drawn = False
    logo_size = 2.8 * cm
    logo_x = page_w - logo_size - 1.8 * cm
    logo_y = page_h - header_h + (header_h - logo_size) / 2
    cx = logo_x + logo_size / 2
    cy = logo_y + logo_size / 2

    if logo_url:
        try:
            import urllib.request, io as _io
            from PIL import Image as PILImage
            from reportlab.lib.utils import ImageReader
            req = urllib.request.Request(logo_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                img_data = _io.BytesIO(resp.read())
            pil_img = PILImage.open(img_data).convert("RGBA")
            c.setFillColor(WHITE)
            c.circle(cx, cy, logo_size / 2 + 4, fill=1, stroke=0)
            img_buffer = _io.BytesIO()
            pil_img.save(img_buffer, format="PNG")
            img_buffer.seek(0)
            c.drawImage(ImageReader(img_buffer), logo_x, logo_y,
                        width=logo_size, height=logo_size, mask="auto")
            logo_drawn = True
        except:
            pass

    if not logo_drawn:
        c.setFillColor(WHITE)
        c.circle(cx, cy, logo_size / 2, fill=1, stroke=0)
        c.setFillColor(INDIGO)
        c.setFont("Helvetica-Bold", 22)
        c.drawCentredString(cx, cy - 8, biz[0].upper() if biz else "P")

    # ── AMOUNT BAND ──
    amt_y = page_h - header_h - 2.8 * cm
    c.setFillColor(GREEN_LIGHT)
    c.setStrokeColor(GREEN_BORDER)
    c.roundRect(1.5*cm, amt_y, page_w - 3*cm, 2.2*cm, 8, fill=1, stroke=1)

    amt = data.get("amount", 0)
    c.setFillColor(GREEN)
    c.setFont("Helvetica", 8)
    c.drawCentredString(page_w / 2, amt_y + 1.55*cm, "AMOUNT PAID")
    c.setFont("Helvetica-Bold", 28)
    c.setFillColor(colors.HexColor("#14532d"))
    c.drawCentredString(page_w / 2, amt_y + 0.5*cm, f"\u20a6{amt:,.2f}")

    # ── STATUS PILL ──
    pill_y = page_h - header_h - 4.5*cm
    pill_w = 3.5*cm
    pill_x = (page_w - pill_w) / 2
    status = data.get("status", "Successful")
    c.setFillColor(GREEN)
    c.roundRect(pill_x, pill_y, pill_w, 0.7*cm, 10, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(page_w / 2, pill_y + 0.18*cm, f"\u2713  {status.upper()}")

    # ── DIVIDER ──
    div_y = page_h - header_h - 5.5*cm
    c.setStrokeColor(GRAY_200)
    c.setLineWidth(0.5)
    c.line(1.5*cm, div_y, page_w - 1.5*cm, div_y)

    # ── DETAILS TABLE ──
    details = [
        ("Reference",      data.get("reference", "—")),
        ("Customer",       data.get("customer_email", "—")),
        ("Purpose",        data.get("purpose", "—") or "—"),
        ("Payment Method", data.get("payment_method", "—").replace("_", " ").title()),
        ("Business",       data.get("business_name", "—")),
        ("Date & Time",    data.get("date", "—")),
        ("Status",         status),
    ]

    row_h = 0.85*cm
    table_x = 1.5*cm
    table_w = page_w - 3*cm
    col1_w = 4.5*cm
    start_y = div_y - 0.4*cm

    for idx, (key, val) in enumerate(details):
        row_y = start_y - (idx * row_h)
        if idx % 2 == 0:
            c.setFillColor(GRAY_100)
            c.setFillAlpha(0.6)
            c.rect(table_x, row_y - row_h + 0.15*cm, table_w, row_h, fill=1, stroke=0)
            c.setFillAlpha(1)
        c.setFillColor(GRAY_400)
        c.setFont("Helvetica", 8.5)
        c.drawString(table_x + 0.3*cm, row_y - 0.52*cm, key.upper())
        c.setFillColor(GREEN if key == "Status" else GRAY_800)
        c.setFont("Helvetica-Bold", 9.5)
        display_val = str(val)
        if len(display_val) > 55:
            display_val = display_val[:52] + "..."
        c.drawString(table_x + col1_w, row_y - 0.52*cm, display_val)

    # ── BOTTOM LINE ──
    bottom_y = start_y - (len(details) * row_h)
    c.setStrokeColor(GRAY_200)
    c.setLineWidth(0.5)
    c.line(table_x, bottom_y, page_w - 1.5*cm, bottom_y)

    # ── PAYVORA BRAND STRIP ──
    brand_y = bottom_y - 1.4*cm
    c.setFillColor(INDIGO_LIGHT)
    c.setStrokeColor(colors.HexColor("#c7d2fe"))
    c.roundRect(1.5*cm, brand_y, page_w - 3*cm, 1*cm, 6, fill=1, stroke=1)
    c.setFillColor(INDIGO)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(page_w / 2, brand_y + 0.32*cm,
                        "\u26a1  Secured & Processed by Payvora  \u26a1")

    # ── FOOTER ──
    footer_y = 1.5*cm
    c.setStrokeColor(GRAY_200)
    c.setLineWidth(0.5)
    c.line(1.5*cm, footer_y + 0.8*cm, page_w - 1.5*cm, footer_y + 0.8*cm)
    c.setFillColor(GRAY_400)
    c.setFont("Helvetica", 7.5)
    c.drawCentredString(page_w / 2, footer_y + 0.4*cm,
        "This is an official receipt. Keep it as proof of payment.")
    c.drawCentredString(page_w / 2, footer_y + 0.1*cm,
        "Payvora \u2014 Secure Payment Infrastructure  |  support@payvora.ng")


def generate_receipt_pdf(
    reference: str,
    business_name: str,
    logo_url: str,
    customer_email: str,
    amount: float,
    payment_method: str,
    date: str,
    purpose: str = "",
    status: str = "Successful",
) -> bytes:
    buffer = io.BytesIO()
    data = {
        "reference": reference,
        "business_name": business_name,
        "logo_url": logo_url,
        "customer_email": customer_email,
        "amount": amount,
        "payment_method": payment_method,
        "date": date,
        "purpose": purpose,
        "status": status,
    }
    c = canvas.Canvas(buffer, pagesize=A4)
    draw_page(c, data)
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.read()