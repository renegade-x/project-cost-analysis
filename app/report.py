"""In-memory PDF and CSV exports with escaped, formula-safe text."""
import csv
from datetime import datetime, timezone
from io import BytesIO, StringIO
from xml.sax.saxutils import escape

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    KeepTogether, LongTable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from .ai_summary import build_template_summary
from .analysis import aggregate_by_category, compute_rows, compute_totals, detect_anomalies
from .security import sanitize_cell
from .models import Project

GREEN = colors.HexColor("#245b47")
MUTED = colors.HexColor("#5c6b65")
LIGHT = colors.HexColor("#eef3e9")


def safe_text(value: object) -> str:
    return escape(sanitize_cell(str(value)))


def build_report(project: Project) -> BytesIO:
    rows = compute_rows(project.items)
    totals = compute_totals(rows)
    categories = aggregate_by_category(rows)
    anomalies = detect_anomalies(rows)
    output = BytesIO()
    document = SimpleDocTemplate(
        output, pagesize=A4, rightMargin=38, leftMargin=38, topMargin=38, bottomMargin=44,
        title="Cost analysis report", author="Cost Analyzer",
    )
    width = A4[0] - 76
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("ReportTitle", fontName="Helvetica-Bold", fontSize=24, leading=28, textColor=GREEN, spaceAfter=14))
    styles.add(ParagraphStyle("ReportBody", fontSize=9, leading=14, spaceAfter=8))
    styles.add(ParagraphStyle("SmallCell", fontSize=7, leading=10, wordWrap="CJK"))
    styles.add(ParagraphStyle("NumberCell", parent=styles["SmallCell"], alignment=TA_RIGHT))
    styles.add(ParagraphStyle("SectionTitle", fontSize=13, leading=18, fontName="Helvetica-Bold", textColor=GREEN, spaceBefore=18, spaceAfter=10, keepWithNext=True))

    def paragraph(text, style="ReportBody", trusted_number=False):
        # Signed numbers are generated here, not user-controlled spreadsheet text.
        value = escape(str(text)) if trusted_number or style == "NumberCell" else safe_text(text)
        return Paragraph(value, styles[style])

    def heading(text):
        return paragraph(text, "SectionTitle")

    def money(value):
        return f"{value:,.2f}"

    def percent(value):
        return f"{value:+.2f}%" if value is not None else "N/A"

    story = [paragraph("COST ANALYZER", "ReportBody"), paragraph("Cost analysis report", "ReportTitle"),
             paragraph(project.name), paragraph("Generated " + datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")),
             paragraph("All amounts use the same currency units. Variance = Actual - Estimated."), Spacer(1, 8)]
    summary = Table([
        [paragraph(label, "SmallCell") for label in ("TOTAL ESTIMATED", "TOTAL ACTUAL", "VARIANCE", "% VARIANCE")],
        [paragraph(value, trusted_number=True) for value in (money(totals["estimated"]), money(totals["actual"]), f"{totals['variance']:+,.2f}", percent(totals["pct_variance"]))],
    ], colWidths=[width / 4] * 4)
    summary.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), LIGHT), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 10), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
    story.extend([summary, heading("Cost breakdown")])
    table_rows = [[paragraph(label, "SmallCell") for label in ("Category", "Estimated", "Actual", "Variance", "% Var.", "Status")]]
    for row in rows:
        values = [row["category"], money(row["estimated"]), money(row["actual"]), f"{row['variance']:+,.2f}", percent(row["pct_variance"]), row["status"]]
        table_rows.append([paragraph(value, "NumberCell" if 1 <= i <= 4 else "SmallCell") for i, value in enumerate(values)])
    if not rows:
        table_rows.append([paragraph("No cost items yet.", "SmallCell")] + [""] * 5)
    total_values = ["Total", money(totals["estimated"]), money(totals["actual"]), f"{totals['variance']:+,.2f}", percent(totals["pct_variance"]), totals["status"]]
    table_rows.append([paragraph(value, "NumberCell" if 1 <= i <= 4 else "SmallCell") for i, value in enumerate(total_values)])
    table = LongTable(table_rows, colWidths=[width * ratio for ratio in (.23, .15, .15, .15, .12, .20)], repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT), ("BACKGROUND", (0, -1), (-1, -1), LIGHT),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#f8f9f6")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, 0), .5, GREEN),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(table)

    if categories:
        selected = sorted(categories, key=lambda row: max(row["estimated"], row["actual"]), reverse=True)[:10]
        drawing = Drawing(width, 245)
        chart = VerticalBarChart()
        chart.x, chart.y, chart.width, chart.height = 52, 88, width - 70, 130
        chart.data = [[row["estimated"] for row in selected], [row["actual"] for row in selected]]
        chart.valueAxis.valueMin = 0
        chart.valueAxis.labels.fontSize = 6
        chart.categoryAxis.categoryNames = [sanitize_cell(row["category"])[:18] for row in selected]
        chart.categoryAxis.labels.fontSize = 6
        chart.categoryAxis.labels.angle = 35
        chart.categoryAxis.labels.boxAnchor = "ne"
        chart.bars[0].fillColor = colors.HexColor("#bbcab7")
        chart.bars[1].fillColor = GREEN
        drawing.add(chart)
        drawing.add(String(52, 20, "Estimated (light) / Actual (dark) | Cost in currency units", fontSize=8, fillColor=MUTED))
        story.append(KeepTogether([heading("Estimated vs actual by category"), paragraph("Top 10 categories by cost; the full results table includes every item."), drawing]))
    else:
        story.extend([heading("Estimated vs actual by category"), paragraph("No cost data available for a chart.")])
    story.append(heading("Unusual expenses"))
    story.append(paragraph("Review signals use absolute z-score >= 2 with at least 5 values and nonzero spread; otherwise a 25% variance threshold. Spending without an estimate is always flagged."))
    for row in anomalies:
        story.append(paragraph(f"{row['category']}: {row['reason']} ({row['method']})"))
    if not anomalies:
        story.append(paragraph("No unusual expenses detected."))
    source = project.ai_summary_source if project.ai_summary else "template"
    summary_text = project.ai_summary or build_template_summary(totals, categories, anomalies)
    story.extend([heading("AI cost analysis summary"), paragraph("Generated by Gemini" if source == "gemini" else "Generated by built-in template"), paragraph(summary_text)])

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#dce3dc"))
        canvas.line(38, 34, A4[0] - 38, 34)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(38, 22, "Cost Analyzer | Project report")
        canvas.drawRightString(A4[0] - 38, 22, f"Page {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    output.seek(0)
    return output


def build_csv(project: Project) -> BytesIO:
    output = StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["Category", "Estimated", "Actual", "Variance", "% Variance", "Status"])
    for row in compute_rows(project.items):
        writer.writerow([sanitize_cell(row["category"]), f"{row['estimated']:.2f}", f"{row['actual']:.2f}", f"{row['variance']:.2f}", row["pct_variance"] if row["pct_variance"] is not None else "N/A", sanitize_cell(row["status"])])
    return BytesIO(output.getvalue().encode("utf-8-sig"))
