import io
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


def set_cell_background(cell, hex_color: str):
    tcPr = cell._element.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), hex_color)
    tcPr.append(shd)


def build_bid_proposal_docx(tender_title: str, requirements: list) -> io.BytesIO:
    doc = Document()

    title = doc.add_heading(tender_title, level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.LEFT

    subtitle = doc.add_paragraph("Bid Defence & Compliance Proposal")
    subtitle.runs[0].font.size = Pt(13)
    subtitle.runs[0].font.color.rgb = RGBColor(100, 100, 100)

    doc.add_paragraph()

    for req in requirements:
        h = doc.add_heading(level=2)
        ref_text = f"{req.section_ref}: " if req.section_ref else ""
        run_h = h.add_run(f"{ref_text}{req.requirement_text[:120]}")
        run_h.font.size = Pt(13)

        table = doc.add_table(rows=2, cols=3)
        table.autofit = False

        headers = ["Compliance Score", "Mandatory Clause", "Evaluator Risk / Fear"]
        for i, header in enumerate(headers):
            cell = table.cell(0, i)
            cell.text = header
            cell.paragraphs[0].runs[0].font.bold = True
            cell.paragraphs[0].runs[0].font.size = Pt(9)
            set_cell_background(cell, "F2F2F2")

        score_cell = table.cell(1, 0)
        score_cell.text = req.audit_score or "Pending"
        score_run = score_cell.paragraphs[0].runs[0]
        score_run.font.bold = True
        score_run.font.size = Pt(10)

        if req.audit_score == "Strong":
            score_run.font.color.rgb = RGBColor(0, 128, 0)
        elif req.audit_score == "Weak":
            score_run.font.color.rgb = RGBColor(178, 34, 34)
        else:
            score_run.font.color.rgb = RGBColor(218, 165, 32)

        mand_cell = table.cell(1, 1)
        mand_cell.text = "PASS/FAIL (Mandatory)" if req.is_mandatory else "Scored Criteria"
        mand_cell.paragraphs[0].runs[0].font.size = Pt(9)

        fear_cell = table.cell(1, 2)
        fear_cell.text = req.evaluator_fear or "Standard Compliance Check"
        fear_cell.paragraphs[0].runs[0].font.size = Pt(9)

        doc.add_paragraph()

        p_gap = doc.add_paragraph()
        run_gap_title = p_gap.add_run("Gap Audit: ")
        run_gap_title.bold = True
        p_gap.add_run(req.gap_analysis or "No audit performed.")

        p_resp_header = doc.add_paragraph()
        run_resp_title = p_resp_header.add_run("Drafted Proposal Response:")
        run_resp_title.bold = True

        p_resp = doc.add_paragraph()
        p_resp.paragraph_format.left_indent = Inches(0.2)
        p_resp.add_run(req.generated_response or "Drafting in progress...")

        doc.add_paragraph("―" * 40)

    file_stream = io.BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)
    return file_stream