"""
PDF Report Generator Module

Generates a formatted 7-day executive security report PDF from SQLite event records
using the fpdf2 library.
"""

import os
import sys
import datetime
from fpdf import FPDF
from io import BytesIO

# Ensure database imports work cleanly
sys.path.insert(0, os.path.dirname(__file__))
from database import SessionLocal, Event


class WeeklyReportPDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 16)
        self.set_text_color(15, 23, 42) # Slate dark
        self.cell(0, 10, 'Brain of Sensors (BoS) - 7-Day Surveillance Report', border=0, new_x="LMARGIN", new_y="NEXT", align='L')
        self.set_font('Helvetica', '', 10)
        self.set_text_color(100, 116, 139)
        now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.cell(0, 6, f'Generated on: {now_str} | Period: Last 7 Days', border=0, new_x="LMARGIN", new_y="NEXT", align='L')
        self.ln(4)
        # Header underline
        self.set_draw_color(226, 232, 240)
        self.set_line_width(0.5)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(148, 163, 184)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}} - Brain of Sensors Security Command System', border=0, align='C')


def generate_weekly_report() -> bytes:
    """
    Queries the database for all events in the last 7 days and generates a structured PDF report.
    Returns PDF bytes.
    """
    session = SessionLocal()
    try:
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=7)
        events = session.query(Event).filter(Event.timestamp >= cutoff_date).order_by(Event.timestamp.desc()).all()

        # Compute summary stats
        total_events = len(events)
        high_count = sum(1 for e in events if (e.urgency or "").lower() == 'high')
        medium_count = sum(1 for e in events if (e.urgency or "").lower() == 'medium')
        low_count = sum(1 for e in events if (e.urgency or "").lower() == 'low')

        pdf = WeeklyReportPDF(orientation='P', unit='mm', format='A4')
        pdf.alias_nb_pages()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        # Executive Summary Section Box
        pdf.set_font('Helvetica', 'B', 12)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(0, 8, '1. Executive Summary', border=0, new_x="LMARGIN", new_y="NEXT", align='L')
        pdf.ln(2)

        pdf.set_font('Helvetica', '', 10)
        pdf.set_fill_color(248, 250, 252)
        pdf.set_draw_color(226, 232, 240)

        summary_text = (
            f"Total Incidents Logged: {total_events}   |   "
            f"High Urgency: {high_count}   |   "
            f"Medium Urgency: {medium_count}   |   "
            f"Low Urgency: {low_count}"
        )
        pdf.cell(0, 10, summary_text, border=1, fill=True, new_x="LMARGIN", new_y="NEXT", align='C')
        pdf.ln(6)

        # Detailed Event Log Table Header
        pdf.set_font('Helvetica', 'B', 12)
        pdf.cell(0, 8, '2. Detailed Event Log (Last 7 Days)', border=0, new_x="LMARGIN", new_y="NEXT", align='L')
        pdf.ln(2)

        # Table Column Widths (Sum = 190mm)
        col_w = [40, 22, 22, 22, 84]

        # Table Headers
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_fill_color(226, 232, 240)
        pdf.set_text_color(15, 23, 42)

        headers = ['Timestamp', 'Zone', 'Object', 'Urgency', 'Summary / Details']
        for i, h in enumerate(headers):
            pdf.cell(col_w[i], 7, h, border=1, fill=True, align='C')
        pdf.ln()

        # Table Data Rows
        pdf.set_font('Helvetica', '', 8.5)
        pdf.set_text_color(51, 65, 85)

        for idx, ev in enumerate(events[:150]): # Limit table rows for clean PDF sizing
            ts_str = ev.timestamp.strftime('%Y-%m-%d %H:%M') if ev.timestamp else "N/A"
            zone_str = str(ev.zone or "N/A").upper()
            obj_str = str(ev.object or "N/A").capitalize()
            urg_str = str(ev.urgency or "low").upper()
            sum_str = str(ev.summary_text or f"In {zone_str}, {obj_str} detected.").strip()

            # Sanitize Unicode characters for standard FPDF ASCII encoding
            sum_str = sum_str.encode('ascii', 'replace').decode('ascii')

            # Truncate summary if too long for table cell
            if len(sum_str) > 65:
                sum_str = sum_str[:62] + "..."

            # Alternate row background
            fill = (idx % 2 == 1)
            pdf.set_fill_color(248, 250, 252) if fill else pdf.set_fill_color(255, 255, 255)

            # Highlight Urgency color text
            if urg_str == 'HIGH':
                pdf.set_text_color(220, 38, 38)
            elif urg_str == 'MEDIUM':
                pdf.set_text_color(217, 119, 6)
            else:
                pdf.set_text_color(16, 185, 129)

            pdf.cell(col_w[0], 6, ts_str, border=1, fill=fill, align='C')
            pdf.set_text_color(51, 65, 85)
            pdf.cell(col_w[1], 6, zone_str, border=1, fill=fill, align='C')
            pdf.cell(col_w[2], 6, obj_str, border=1, fill=fill, align='C')
            
            # Re-apply urgency color
            if urg_str == 'HIGH':
                pdf.set_text_color(220, 38, 38)
            elif urg_str == 'MEDIUM':
                pdf.set_text_color(217, 119, 6)
            else:
                pdf.set_text_color(16, 185, 129)
            pdf.cell(col_w[3], 6, urg_str, border=1, fill=fill, align='C')

            pdf.set_text_color(51, 65, 85)
            pdf.cell(col_w[4], 6, sum_str, border=1, fill=fill, align='L')
            pdf.ln()

        # Output bytes
        pdf_bytes = pdf.output()
        return bytes(pdf_bytes)

    finally:
        session.close()
