import io
import os
from pathlib import Path
import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Check if NotoSans font exists in backend_flask/assets/fonts
FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
font_regular_path = FONTS_DIR / "NotoSans-Regular.ttf"
font_bold_path = FONTS_DIR / "NotoSans-Bold.ttf"

FONT_REGULAR = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
FONT_SYMBOL = "Helvetica"

if font_regular_path.exists() and font_bold_path.exists():
    try:
        pdfmetrics.registerFont(TTFont("NotoSans", str(font_regular_path)))
        pdfmetrics.registerFont(TTFont("NotoSans-Bold", str(font_bold_path)))
        FONT_REGULAR = "NotoSans"
        FONT_BOLD = "NotoSans-Bold"
    except Exception:
        pass

def format_inr(val):
    """Format Indian Currency (INR) with proper formatting and Rs./₹ symbol."""
    try:
        num = float(val)
    except (ValueError, TypeError):
        return "Rs. 0.00"
    is_neg = num < 0
    abs_num = abs(num)
    formatted = f"{abs_num:,.2f}"
    # Use Rs. or ₹ depending on font support
    curr_symbol = "₹" if FONT_REGULAR == "NotoSans" else "Rs. "
    return f"-{curr_symbol}{formatted}" if is_neg else f"{curr_symbol}{formatted}"

def generate_invoice_pdf(order, items):
    """
    Generates a byte stream of the itemized PDF invoice receipt matching the Node.js implementation.
    """
    buffer = io.BytesIO()
    # A4 size is 595.27 x 841.89 points
    p = canvas.Canvas(buffer, pagesize=A4)
    page_width, page_height = A4

    # 1. Header Squircle & Brand
    p.setFillColor(colors.HexColor("#f97316"))
    p.roundRect(40, page_height - 36 - 36, 36, 36, 8, fill=1, stroke=0)

    # Simple icon inside badge
    p.setStrokeColor(colors.white)
    p.setLineWidth(2)
    p.line(50, page_height - 50, 66, page_height - 66)
    p.line(66, page_height - 50, 50, page_height - 66)

    # Wordmark
    p.setFont(FONT_BOLD, 22)
    p.setFillColor(colors.HexColor("#18181b"))
    p.drawString(86, page_height - 58, "Campus")
    w = p.stringWidth("Campus", FONT_BOLD, 22)
    p.setFillColor(colors.HexColor("#f97316"))
    p.drawString(86 + w, page_height - 58, "Eats")

    p.setFont(FONT_REGULAR, 9.5)
    p.setFillColor(colors.HexColor("#71717a"))
    p.drawString(86, page_height - 74, "Smart Campus Pre-Order & Digital Token System")
    
    canteen_name = order.get("canteen_name", "Cafeteria")
    canteen_loc = order.get("canteen_location") or "Campus"
    p.drawString(40, page_height - 96, f"Canteen: {canteen_name} ({canteen_loc})")

    # 2. Safe QR Code in Top Right
    order_id = order.get("id")
    token_number = order.get("token_number", "")
    safe_url = f"https://campus-eats-ruby.vercel.app/verify?orderId={order_id}&token={token_number}"
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=3,
        border=1,
    )
    qr.add_data(safe_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)
    
    from reportlab.lib.utils import ImageReader
    qr_reader = ImageReader(qr_buffer)
    p.drawImage(qr_reader, 460, page_height - 120, width=85, height=85)

    p.setFont(FONT_REGULAR, 8)
    p.setFillColor(colors.HexColor("#71717a"))
    p.drawCentredString(502, page_height - 130, "Scan to Verify Token")

    # 3. Divider
    p.setStrokeColor(colors.HexColor("#e4e4e7"))
    p.setLineWidth(1)
    p.line(40, page_height - 140, 555, page_height - 140)

    # 4. Order & Customer Metadata Grid
    created_at = str(order.get("created_at", ""))
    p.setFont(FONT_BOLD, 11)
    p.setFillColor(colors.HexColor("#18181b"))
    p.drawString(40, page_height - 160, "DIGITAL TOKEN / INVOICE RECEIPT")

    p.setFont(FONT_REGULAR, 9)
    p.setFillColor(colors.HexColor("#52525b"))
    p.drawString(40, page_height - 180, "Token Number:")
    p.setFont(FONT_BOLD, 13)
    p.setFillColor(colors.HexColor("#ea580c"))
    p.drawString(120, page_height - 180, str(token_number))

    p.setFont(FONT_REGULAR, 9)
    p.setFillColor(colors.HexColor("#52525b"))
    p.drawString(40, page_height - 197, f"Order ID: #{order_id}")
    p.drawString(40, page_height - 211, f"Date & Time: {created_at}")
    p.drawString(40, page_height - 225, f"Student: {order.get('student_name', '')} ({order.get('student_email', '')})")

    p.drawString(320, page_height - 180, f"Payment Method: {str(order.get('payment_method', '')).upper()}")
    p.drawString(320, page_height - 197, f"Payment Status: {str(order.get('payment_status', '')).upper()}")
    p.drawString(320, page_height - 211, f"Txn Ref: {order.get('payment_transaction_id') or 'N/A'}")
    p.drawString(320, page_height - 225, f"Order Status: {str(order.get('status', '')).upper()}")

    # 5. Table Header
    y_pos = page_height - 250
    p.setFillColor(colors.HexColor("#f4f4f5"))
    p.rect(40, y_pos - 16, 515, 22, fill=1, stroke=0)

    p.setFont(FONT_BOLD, 9)
    p.setFillColor(colors.HexColor("#18181b"))
    p.drawString(50, y_pos - 10, "ITEM DESCRIPTION")
    p.drawCentredString(340, y_pos - 10, "QTY")
    p.drawRightString(440, y_pos - 10, "UNIT PRICE")
    p.drawRightString(545, y_pos - 10, "TOTAL")

    y_pos -= 26

    # 6. Items Rows
    subtotal = 0.0
    p.setFont(FONT_REGULAR, 9)
    p.setFillColor(colors.HexColor("#27272a"))

    for item in items:
        price = float(item.get("price", 0))
        qty = int(item.get("quantity", 1))
        line_total = price * qty
        subtotal += line_total

        p.setFont(FONT_BOLD, 9)
        p.drawString(50, y_pos, str(item.get("name", "")))
        p.setFont(FONT_REGULAR, 9)
        p.drawCentredString(340, y_pos, str(qty))
        p.drawRightString(440, y_pos, format_inr(price))
        p.setFont(FONT_BOLD, 9)
        p.drawRightString(545, y_pos, format_inr(line_total))

        if item.get("customization"):
            y_pos -= 13
            p.setFont(FONT_REGULAR, 8)
            p.setFillColor(colors.HexColor("#71717a"))
            p.drawString(58, y_pos, f"Customization: {item.get('customization')}")
            p.setFont(FONT_REGULAR, 9)
            p.setFillColor(colors.HexColor("#27272a"))

        y_pos -= 18
        p.setStrokeColor(colors.HexColor("#f4f4f5"))
        p.setLineWidth(0.5)
        p.line(40, y_pos, 555, y_pos)
        y_pos -= 6

    # 7. Summary Calculations
    total_amount = float(order.get("total_amount", 0))
    discount = max(0.0, subtotal - total_amount)
    taxes = 0.0

    y_pos -= 10
    p.setStrokeColor(colors.HexColor("#e4e4e7"))
    p.setLineWidth(1)
    p.line(300, y_pos, 555, y_pos)
    y_pos -= 14

    p.setFont(FONT_REGULAR, 9)
    p.setFillColor(colors.HexColor("#52525b"))
    p.drawString(320, y_pos, "Subtotal:")
    p.drawRightString(545, y_pos, format_inr(subtotal))

    if discount > 0:
        y_pos -= 15
        p.drawString(320, y_pos, "Special Discount:")
        p.setFillColor(colors.HexColor("#16a34a"))
        p.drawRightString(545, y_pos, f"-{format_inr(discount)}")
        p.setFillColor(colors.HexColor("#52525b"))

    y_pos -= 15
    p.drawString(320, y_pos, "Taxes & Fees:")
    p.drawRightString(545, y_pos, format_inr(taxes))

    y_pos -= 22
    p.setFillColor(colors.HexColor("#fff7ed"))
    p.rect(300, y_pos - 4, 255, 24, fill=1, stroke=0)
    p.setFont(FONT_BOLD, 11)
    p.setFillColor(colors.HexColor("#ea580c"))
    p.drawString(310, y_pos + 3, "Total Paid Amount:")
    p.drawRightString(545, y_pos + 3, format_inr(total_amount))

    # 8. Footer Note
    p.setFont(FONT_REGULAR, 8)
    p.setFillColor(colors.HexColor("#a1a1aa"))
    footer_text = "This is a computer-generated digital receipt and digital token issued by CampusEats.\nPresent your token number at the pickup counter once the kitchen marks your order ready."
    for idx, line in enumerate(footer_text.split("\n")):
        p.drawCentredString(page_width / 2.0, 70 - (idx * 11), line)

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer
