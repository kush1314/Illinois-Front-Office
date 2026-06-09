from __future__ import annotations

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def build_scouting_pdf(player_name: str, report: dict[str, str]) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER, title=f"Scouting Report - {player_name}")
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Illinois Front Office AI", styles["Title"]))
    story.append(Paragraph(f"Scouting Center Report: {player_name}", styles["Heading2"]))
    story.append(Spacer(1, 12))

    sections = [
        ("Executive Summary", report["executive_summary"]),
        ("Strengths", report["strengths"]),
        ("Weaknesses", report["weaknesses"]),
        ("Projected Role", report["projected_role"]),
        ("Development Areas", report["development_areas"]),
        ("Illinois Fit", report["illinois_fit"]),
        ("Recruiting Recommendation", report["recruiting_recommendation"]),
        ("Coach Notes", report["coach_notes"]),
    ]

    for title, content in sections:
        story.append(Paragraph(title, styles["Heading3"]))
        story.append(Paragraph(content.replace("\n", "<br/>"), styles["BodyText"]))
        story.append(Spacer(1, 10))

    quick_table = Table(
        [["Report Engine", "Illinois Front Office AI"], ["Generated For", player_name], ["Use Case", "Recruiting and roster meetings"]],
        colWidths=[170, 330],
    )
    quick_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#13294B")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F8FAFC")),
            ]
        )
    )
    story.append(quick_table)

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
