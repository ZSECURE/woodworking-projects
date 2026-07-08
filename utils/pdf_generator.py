"""
PDF Instruction Manual Generator
==================================
Produces a multi-page A4 PDF containing:
  • Cover page
  • Project overview and safety notes
  • Tools required
  • Structural timber cut list
  • Pod / insulation cassette cut list
  • OSB cutting schedule
  • Step-by-step assembly instructions with annotated sketches
"""

import io
import math

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    HRFlowable,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.graphics.shapes import (
    Drawing,
    Line,
    Rect,
    String,
    Circle,
    PolyLine,
    Path,
    Group,
)
from reportlab.graphics import renderPDF

# ── Colour palette ────────────────────────────────────────────────────────────
C_DARK  = colors.HexColor("#1a2332")
C_MID   = colors.HexColor("#2d4a6b")
C_LIGHT = colors.HexColor("#e8f0fe")
C_ACCENT= colors.HexColor("#e67e22")
C_GREEN = colors.HexColor("#27ae60")
C_GREY  = colors.HexColor("#95a5a6")
C_WHITE = colors.white
C_BLACK = colors.black
C_AMBER = colors.HexColor("#f39c12")

PAGE_W, PAGE_H = A4
MARGIN = 20 * mm


# ── Style helpers ──────────────────────────────────────────────────────────────

def _styles():
    base = getSampleStyleSheet()

    def add(name, **kw):
        if name not in base:
            base.add(ParagraphStyle(name=name, **kw))
        return base[name]

    add("CoverTitle",
        fontName="Helvetica-Bold", fontSize=28, textColor=C_WHITE,
        alignment=TA_CENTER, spaceAfter=6)
    add("CoverSub",
        fontName="Helvetica", fontSize=14, textColor=C_LIGHT,
        alignment=TA_CENTER, spaceAfter=4)
    add("CoverInfo",
        fontName="Helvetica", fontSize=10, textColor=C_GREY,
        alignment=TA_CENTER, spaceAfter=2)

    add("H1",
        fontName="Helvetica-Bold", fontSize=16, textColor=C_DARK,
        spaceBefore=12, spaceAfter=6)
    add("H2",
        fontName="Helvetica-Bold", fontSize=12, textColor=C_MID,
        spaceBefore=8, spaceAfter=4)
    add("H3",
        fontName="Helvetica-Bold", fontSize=10, textColor=C_DARK,
        spaceBefore=6, spaceAfter=3)
    add("Body",
        fontName="Helvetica", fontSize=9, textColor=C_BLACK,
        leading=14, alignment=TA_JUSTIFY, spaceAfter=4)
    add("Bullet",
        fontName="Helvetica", fontSize=9, textColor=C_BLACK,
        leading=13, leftIndent=12, bulletIndent=0, spaceAfter=2)
    add("Step",
        fontName="Helvetica-Bold", fontSize=9, textColor=C_DARK,
        leading=14, leftIndent=16, spaceAfter=2)
    add("StepBody",
        fontName="Helvetica", fontSize=9, textColor=C_BLACK,
        leading=13, leftIndent=16, spaceAfter=4)
    add("Warning",
        fontName="Helvetica-BoldOblique", fontSize=9,
        textColor=colors.HexColor("#c0392b"),
        leading=13, leftIndent=6, spaceAfter=4)
    add("TableHdr",
        fontName="Helvetica-Bold", fontSize=8, textColor=C_WHITE,
        alignment=TA_CENTER)
    add("TableCell",
        fontName="Helvetica", fontSize=8, textColor=C_BLACK,
        leading=11)
    add("TableNote",
        fontName="Helvetica-Oblique", fontSize=7.5, textColor=C_GREY,
        leading=10)
    add("Caption",
        fontName="Helvetica-Oblique", fontSize=8, textColor=C_GREY,
        alignment=TA_CENTER, spaceAfter=6)
    return base


# ── Table style helpers ────────────────────────────────────────────────────────

_TS_BASE = [
    ("BACKGROUND",  (0, 0), (-1, 0), C_MID),
    ("TEXTCOLOR",   (0, 0), (-1, 0), C_WHITE),
    ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE",    (0, 0), (-1, 0), 8),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_LIGHT]),
    ("FONTNAME",    (0, 1), (-1, -1), "Helvetica"),
    ("FONTSIZE",    (0, 1), (-1, -1), 8),
    ("GRID",        (0, 0), (-1, -1), 0.4, C_GREY),
    ("VALIGN",      (0, 0), (-1, -1), "TOP"),
    ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ("RIGHTPADDING",(0, 0), (-1, -1), 4),
    ("TOPPADDING",  (0, 0), (-1, -1), 3),
    ("BOTTOMPADDING",(0,0), (-1,-1),  3),
]


def _ts(*extra):
    return TableStyle(_TS_BASE + list(extra))


# ── Roof-plan sketch ───────────────────────────────────────────────────────────

def _roof_plan_sketch(r: dict, width: float = 160 * mm) -> Drawing:
    """
    Top-down plan view showing ridge, hips, common and jack rafters.
    All drawing units are in reportlab points (1 pt = 1/72 inch).
    """
    L_mm = r["L_mm"]
    W_mm = r["W_mm"]
    scale = width / L_mm
    H = W_mm * scale
    pad = 6

    d = Drawing(width + 2 * pad, H + 2 * pad)

    def px(x): return pad + x * scale
    def py(y): return pad + y * scale

    # Building outline
    d.add(Rect(pad, pad, width, H, fillColor=colors.HexColor("#f5f0e8"),
               strokeColor=C_DARK, strokeWidth=1.2))

    half_w = W_mm / 2
    ridge_x1 = half_w
    ridge_x2 = L_mm - half_w

    # Ridge (if it exists)
    if ridge_x2 > ridge_x1:
        d.add(Line(px(ridge_x1), py(half_w), px(ridge_x2), py(half_w),
                   strokeColor=C_ACCENT, strokeWidth=2))
        d.add(String(px((ridge_x1 + ridge_x2) / 2), py(half_w) + 3,
                     "RIDGE", fontSize=6, fillColor=C_ACCENT,
                     textAnchor="middle"))

    # Hip rafters (4)
    for cx, cy in [(0, 0), (0, W_mm), (L_mm, 0), (L_mm, W_mm)]:
        hx = ridge_x1 if cx < L_mm / 2 else ridge_x2
        d.add(Line(px(cx), py(cy), px(hx), py(half_w),
                   strokeColor=C_MID, strokeWidth=1.5))

    # Common rafters (dashed lines from front/back wall to ridge)
    spacing_mm = r.get("spacing_mm", 600)
    if "spacing_mm" not in r:
        # infer from first jack run or default
        jacks = r.get("jack_lengths", [])
        spacing_mm = jacks[0]["run_mm"] if jacks else 600

    x = ridge_x1
    while x <= ridge_x2 + 0.5:
        d.add(Line(px(x), py(0), px(x), py(half_w),
                   strokeColor=C_GREEN, strokeWidth=0.6, strokeDashArray=[3, 2]))
        d.add(Line(px(x), py(W_mm), px(x), py(half_w),
                   strokeColor=C_GREEN, strokeWidth=0.6, strokeDashArray=[3, 2]))
        x += spacing_mm

    # Jack rafters (left end)
    jacks = r.get("jack_lengths", [])
    for jk in jacks:
        jx = jk["run_mm"]
        # front-left hip: y = x at 45°
        d.add(Line(px(jx), py(0), px(jx), py(jx),
                   strokeColor=C_AMBER, strokeWidth=0.6, strokeDashArray=[2, 2]))
        d.add(Line(px(jx), py(W_mm), px(jx), py(W_mm - jx),
                   strokeColor=C_AMBER, strokeWidth=0.6, strokeDashArray=[2, 2]))
        # right end mirror
        rx = L_mm - jx
        d.add(Line(px(rx), py(0), px(rx), py(jx),
                   strokeColor=C_AMBER, strokeWidth=0.6, strokeDashArray=[2, 2]))
        d.add(Line(px(rx), py(W_mm), px(rx), py(W_mm - jx),
                   strokeColor=C_AMBER, strokeWidth=0.6, strokeDashArray=[2, 2]))

    # Legend
    lx, ly = pad + 4, 4
    items = [
        (C_ACCENT, 2, "Ridge"),
        (C_MID,    1.5, "Hip rafter"),
        (C_GREEN,  0.6, "Common rafter"),
        (C_AMBER,  0.6, "Jack rafter"),
    ]
    for i, (col, sw, label) in enumerate(items):
        bx = lx + i * 42
        d.add(Line(bx, ly + 4, bx + 12, ly + 4, strokeColor=col, strokeWidth=sw))
        d.add(String(bx + 14, ly + 1, label, fontSize=5.5, fillColor=col))

    return d


# ── Cross-section sketch ───────────────────────────────────────────────────────

def _cross_section_sketch(r: dict, width: float = 120 * mm) -> Drawing:
    """
    Side cross-section showing pitch, rise, run, and wall plate.
    """
    W_mm   = r["W_mm"]
    rise   = r["rise_mm"]
    pitch  = r["pitch_deg"]
    cr_len = r["common_total_mm"]
    ovhng  = 300  # nominal overhang mm for drawing

    scale = (width - 20) / (W_mm + 2 * ovhng)
    H = rise * scale + 40

    d = Drawing(width, H + 20)

    cx = 10  # left pad

    def px(x): return cx + x * scale
    def pr(y): return 15 + y * scale   # y from bottom

    # Ground / wall plate line
    ground_y = pr(0)
    d.add(Line(px(-ovhng), ground_y, px(W_mm + ovhng), ground_y,
               strokeColor=C_GREY, strokeWidth=0.8))

    # Walls (left and right)
    wall_h = pr(rise * 0.15)  # small wall height for illustration
    d.add(Rect(px(0) - 4, ground_y - wall_h,
               8, wall_h,
               fillColor=C_GREY, strokeColor=None))

    # Left rafter (from left eave to ridge)
    x0 = px(-ovhng)
    y0 = ground_y
    x1 = px(W_mm / 2)
    y1 = pr(rise)
    # Right rafter mirror
    x2 = px(W_mm + ovhng)

    d.add(Line(x0, y0, x1, y1, strokeColor=C_MID, strokeWidth=1.8))
    d.add(Line(x2, y0, x1, y1, strokeColor=C_MID, strokeWidth=1.8))

    # Ridge point dot
    d.add(Circle(x1, y1, 3, fillColor=C_ACCENT, strokeColor=None))

    # Dimension: rise (vertical arrow)
    dx = px(W_mm / 2) + 8
    d.add(Line(dx, ground_y, dx, pr(rise),
               strokeColor=C_GREY, strokeWidth=0.5, strokeDashArray=[2, 2]))
    d.add(String(dx + 2, (ground_y + pr(rise)) / 2,
                 f"Rise\n{r['rise_mm']} mm",
                 fontSize=6, fillColor=C_GREY))

    # Dimension: half-span
    dy = ground_y - 8
    d.add(Line(px(0), dy, px(W_mm / 2), dy,
               strokeColor=C_GREY, strokeWidth=0.5))
    d.add(String((px(0) + px(W_mm / 2)) / 2, dy - 8,
                 f"Span/2 = {int(W_mm // 2)} mm",
                 fontSize=6, fillColor=C_GREY, textAnchor="middle"))

    # Pitch label
    mid_x = (px(-ovhng) + px(W_mm / 2)) / 2
    mid_y = (ground_y + pr(rise)) / 2
    d.add(String(mid_x - 20, mid_y,
                 f"{pitch}°",
                 fontSize=8, fillColor=C_ACCENT))

    return d


# ── Pod cross-section sketch ───────────────────────────────────────────────────

def _pod_section_sketch(r: dict, width: float = 110 * mm) -> Drawing:
    """
    Cross-section through one pod bay showing the layer stack.
    """
    pod_w   = r["pod_width_mm"]
    depth_t = r["pod_total_depth_mm"]
    osb_t   = 18
    insul_d = r["insul_depth_mm"]
    air_d   = r["air_gap_mm"]
    raf_w   = 47

    scale_x = (width - 40) / (raf_w * 2 + pod_w)
    scale_y = min(scale_x, (120 * mm) / depth_t)
    H = depth_t * scale_y + 30

    d = Drawing(width, H)
    ox = 10
    oy = 10

    def bx(x): return ox + x * scale_x
    def by(y): return oy + y * scale_y

    total_w = (raf_w * 2 + pod_w) * scale_x

    # Left rafter block
    d.add(Rect(bx(0), by(0), raf_w * scale_x, depth_t * scale_y,
               fillColor=colors.HexColor("#d4a96a"), strokeColor=C_DARK, strokeWidth=0.8))
    d.add(String(bx(raf_w / 2), by(depth_t / 2),
                 f"{raf_w}×{150}",
                 fontSize=5.5, fillColor=C_DARK, textAnchor="middle"))

    # Right rafter block
    rx0 = raf_w + pod_w
    d.add(Rect(bx(rx0), by(0), raf_w * scale_x, depth_t * scale_y,
               fillColor=colors.HexColor("#d4a96a"), strokeColor=C_DARK, strokeWidth=0.8))

    # Pod layers
    px0 = raf_w
    px_w = pod_w

    # Outer OSB (top)
    outer_y = (osb_t + insul_d + air_d)
    d.add(Rect(bx(px0), by(outer_y), px_w * scale_x, osb_t * scale_y,
               fillColor=colors.HexColor("#c8a96e"), strokeColor=C_DARK, strokeWidth=0.5))
    d.add(String(bx(px0 + px_w / 2), by(outer_y + osb_t / 2),
                 f"OSB 18mm (outer deck)",
                 fontSize=5.5, fillColor=C_DARK, textAnchor="middle"))

    # Air gap
    ag_y = osb_t + insul_d
    d.add(Rect(bx(px0), by(ag_y), px_w * scale_x, air_d * scale_y,
               fillColor=colors.HexColor("#dce8f5"), strokeColor=C_GREY, strokeWidth=0.4))
    d.add(String(bx(px0 + px_w / 2), by(ag_y + air_d / 2),
                 f"Air gap {air_d} mm (ventilated)",
                 fontSize=5.5, fillColor=C_MID, textAnchor="middle"))

    # Insulation
    d.add(Rect(bx(px0), by(osb_t), px_w * scale_x, insul_d * scale_y,
               fillColor=colors.HexColor("#f9e4b7"), strokeColor=C_GREY, strokeWidth=0.4))
    d.add(String(bx(px0 + px_w / 2), by(osb_t + insul_d / 2),
                 f"PIR insulation {insul_d} mm",
                 fontSize=5.5, fillColor=C_DARK, textAnchor="middle"))

    # Inner OSB (bottom)
    d.add(Rect(bx(px0), by(0), px_w * scale_x, osb_t * scale_y,
               fillColor=colors.HexColor("#c8a96e"), strokeColor=C_DARK, strokeWidth=0.5))
    d.add(String(bx(px0 + px_w / 2), by(osb_t / 2),
                 f"OSB 18mm (inner face)",
                 fontSize=5.5, fillColor=C_DARK, textAnchor="middle"))

    # Width label
    d.add(Line(bx(px0), oy - 4, bx(px0 + px_w), oy - 4,
               strokeColor=C_GREY, strokeWidth=0.5))
    d.add(String(bx(px0 + px_w / 2), oy - 12,
                 f"Pod width {pod_w} mm",
                 fontSize=6, fillColor=C_GREY, textAnchor="middle"))

    return d


# ── Page templates ─────────────────────────────────────────────────────────────

def _page_header_footer(canvas, doc):
    """Draws header and footer on every non-cover page."""
    canvas.saveState()
    # Header bar
    canvas.setFillColor(C_DARK)
    canvas.rect(MARGIN, PAGE_H - MARGIN - 8 * mm, PAGE_W - 2 * MARGIN, 8 * mm, fill=1, stroke=0)
    canvas.setFillColor(C_WHITE)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(MARGIN + 3 * mm, PAGE_H - MARGIN - 5 * mm,
                      "Conservatory Solid Timber Roof — Construction Manual")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(PAGE_W - MARGIN - 3 * mm, PAGE_H - MARGIN - 5 * mm,
                           f"Page {doc.page}")
    # Footer
    canvas.setFillColor(C_GREY)
    canvas.setFont("Helvetica-Oblique", 7)
    canvas.drawString(MARGIN, MARGIN - 4 * mm,
                      "This document is for guidance only. Always consult a "
                      "structural engineer for buildings requiring building regulations approval.")
    canvas.restoreState()


# ── Main PDF builder ───────────────────────────────────────────────────────────

def generate_pdf(r: dict) -> bytes:
    """
    Generate a complete instruction manual PDF and return it as bytes.

    Parameters
    ----------
    r : dict
        The results dict returned by ConservatoryRoof.calculate().
    """
    buf = io.BytesIO()
    S = _styles()

    # ── Document setup ─────────────────────────────────────────────────────
    doc = BaseDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN + 10 * mm, bottomMargin=MARGIN,
        title="Conservatory Roof Replacement Manual",
        author="Conservatory Roof Calculator",
    )

    cover_frame = Frame(0, 0, PAGE_W, PAGE_H,
                        leftPadding=0, bottomPadding=0,
                        rightPadding=0, topPadding=0, id="cover")
    body_frame  = Frame(MARGIN, MARGIN, PAGE_W - 2 * MARGIN,
                        PAGE_H - 2 * MARGIN - 12 * mm, id="body")

    doc.addPageTemplates([
        PageTemplate(id="cover", frames=[cover_frame]),
        PageTemplate(id="body",  frames=[body_frame],
                     onPage=_page_header_footer),
    ])

    story = []

    # ══════════════════════════════════════════════════════════════════════════
    # COVER PAGE
    # ══════════════════════════════════════════════════════════════════════════
    story.append(NextPageTemplate("cover"))

    # Blue background block (drawn via a canvas callback is easier with a
    # Flowable wrapper).
    story.append(_CoverBackground(
        L=r["L_mm"], W=r["W_mm"],
        pitch=r["pitch_deg"], rise=r["rise_mm"],
    ))
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # BODY PAGES
    # ══════════════════════════════════════════════════════════════════════════
    story.append(NextPageTemplate("body"))

    # ── 1. Project Overview ─────────────────────────────────────────────────
    story += _section_overview(r, S)
    story.append(PageBreak())

    # ── 2. Safety & Tools ───────────────────────────────────────────────────
    story += _section_safety(S)
    story += _section_tools(S)
    story.append(PageBreak())

    # ── 3. Structural Calculations Summary ──────────────────────────────────
    story += _section_calcs(r, S)
    story.append(PageBreak())

    # ── 4. Timber Cut List ──────────────────────────────────────────────────
    story += _section_cut_list(r, S)
    story.append(PageBreak())

    # ── 5. Pod Construction ─────────────────────────────────────────────────
    story += _section_pods(r, S)
    story.append(PageBreak())

    # ── 6. OSB Cutting Schedule ─────────────────────────────────────────────
    story += _section_osb(r, S)
    story.append(PageBreak())

    # ── 7. Assembly Instructions ────────────────────────────────────────────
    story += _section_assembly(r, S)

    doc.build(story)
    return buf.getvalue()


# ── Cover Flowable ─────────────────────────────────────────────────────────────

class _CoverBackground(Flowable):
    def __init__(self, L, W, pitch, rise):
        super().__init__()
        self.L = L; self.W = W; self.pitch = pitch; self.rise = rise
        self.width  = PAGE_W
        self.height = PAGE_H

    def draw(self):
        c = self.canv

        # Dark blue background
        c.setFillColor(C_DARK)
        c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

        # Accent bar
        c.setFillColor(C_ACCENT)
        c.rect(0, PAGE_H * 0.42, PAGE_W, 4, fill=1, stroke=0)

        # Decorative grid lines
        c.setStrokeColor(C_MID)
        c.setLineWidth(0.3)
        for i in range(0, int(PAGE_W), 20):
            c.line(i, 0, i, PAGE_H)
        for i in range(0, int(PAGE_H), 20):
            c.line(0, i, PAGE_W, i)

        # Title area
        c.setFillColor(C_WHITE)
        c.setFont("Helvetica-Bold", 30)
        c.drawCentredString(PAGE_W / 2, PAGE_H * 0.72,
                            "CONSERVATORY TIMBER ROOF")
        c.setFont("Helvetica-Bold", 22)
        c.drawCentredString(PAGE_W / 2, PAGE_H * 0.65,
                            "REPLACEMENT MANUAL")

        c.setFillColor(C_LIGHT)
        c.setFont("Helvetica", 13)
        c.drawCentredString(PAGE_W / 2, PAGE_H * 0.59,
                            "Complete Cut List & Assembly Instructions")

        # Spec box
        c.setFillColor(C_MID)
        c.roundRect(MARGIN * 1.5, PAGE_H * 0.46, PAGE_W - 3 * MARGIN,
                    PAGE_H * 0.11, 6, fill=1, stroke=0)
        c.setFillColor(C_WHITE)
        c.setFont("Helvetica-Bold", 10)
        specs = [
            (f"Length: {self.L / 1000:.2f} m",   PAGE_W * 0.18),
            (f"Width: {self.W / 1000:.2f} m",     PAGE_W * 0.38),
            (f"Pitch: {self.pitch}°",              PAGE_W * 0.58),
            (f"Ridge Rise: {int(self.rise)} mm",  PAGE_W * 0.78),
        ]
        for label, x in specs:
            c.drawCentredString(x, PAGE_H * 0.51, label)

        # Footer
        c.setFillColor(C_GREY)
        c.setFont("Helvetica-Oblique", 8)
        c.drawCentredString(PAGE_W / 2, MARGIN + 10,
                            "Generated by the Conservatory Roof Calculator  |  "
                            "Always verify dimensions on site before cutting")


# ── Section builders ───────────────────────────────────────────────────────────

def _section_overview(r: dict, S) -> list:
    story = []
    story.append(Paragraph("1. Project Overview", S["H1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=C_MID, spaceAfter=6))

    intro = (
        f"This manual describes the full replacement of an aluminium framed "
        f"conservatory roof with a solid insulated timber hip roof. "
        f"The conservatory measures <b>{r['L_mm']/1000:.2f} m × "
        f"{r['W_mm']/1000:.2f} m</b> (length × width) with a "
        f"<b>{r['pitch_deg']}° pitch</b>, giving a ridge rise of "
        f"<b>{r['rise_mm']} mm</b> above wall-plate level."
    )
    story.append(Paragraph(intro, S["Body"]))
    story.append(Spacer(1, 4 * mm))

    # Roof plan diagram
    story.append(Paragraph("Roof Plan (top-down view)", S["H2"]))
    plan = _roof_plan_sketch(r, width=140 * mm)
    story.append(plan)
    story.append(Paragraph(
        "Green dashed = common rafters  |  Amber dashed = jack rafters  |  "
        "Blue = hip rafters  |  Orange = ridge beam",
        S["Caption"]))
    story.append(Spacer(1, 4 * mm))

    # Cross-section diagram
    story.append(Paragraph("Roof Cross-Section (end view)", S["H2"]))
    xs = _cross_section_sketch(r, width=130 * mm)
    story.append(xs)
    story.append(Paragraph(
        f"Pitch {r['pitch_deg']}°  |  Half-span {int(r['W_mm']//2)} mm  |  "
        f"Rise {r['rise_mm']} mm  |  Common rafter {r['common_total_mm']} mm",
        S["Caption"]))

    return story


def _section_safety(S) -> list:
    story = []
    story.append(Paragraph("2. Safety Notes", S["H1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=C_MID, spaceAfter=6))

    story.append(Paragraph(
        "⚠ IMPORTANT — READ BEFORE STARTING",
        S["Warning"]))

    bullets = [
        "Obtain all necessary planning consents and Building Regulations approval "
        "before starting. Structural changes to a conservatory roof typically "
        "require approval under Building Regulations Part A (Structure), Part L "
        "(Energy Efficiency) and Part B (Fire Safety).",
        "Engage a structural engineer to verify the wall-plate fixings, "
        "ridge beam span, and the existing structure's ability to carry the "
        "increased dead load of a timber roof.",
        "Ensure adequate scaffolding or edge-protection is erected before "
        "removing the existing roof.",
        "Work in dry, calm conditions. Timber absorbs moisture; do not leave "
        "structural timbers exposed to rain before the weathertight layer is "
        "complete.",
        "Wear appropriate PPE: hard hat, safety boots, cut-resistant gloves, "
        "eye protection, and dust mask when cutting timber or OSB.",
        "Isolate any electrical cables that run through or near the roof space "
        "before starting. Consult a qualified electrician.",
        "Never stand on unsupported OSB or rafter tails.",
    ]
    for b in bullets:
        story.append(Paragraph(f"• {b}", S["Bullet"]))
    return story


def _section_tools(S) -> list:
    story = []
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("3. Tools Required", S["H1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=C_MID, spaceAfter=6))

    cols = [
        ["Power tools", "Hand tools", "Measuring & marking", "Fixings & adhesives"],
        [
            "• Circular saw with rip fence\n• Mitre saw (compound sliding)\n"
            "• Jigsaw\n• Cordless drill/driver\n• Random orbital sander",
            "• Panel saw\n• Tenon saw\n• Claw hammer\n• Block plane (for backing bevel)\n"
            "• Wood chisel set (25 mm, 50 mm)",
            "• Steel tape (8 m)\n• Builder's square (600 mm)\n"
            "• Digital angle finder / bevel gauge\n• Chalk line\n• Spirit level (1.8 m)\n"
            "• Plumb bob",
            "• Joist hangers & nails\n• M10 coach screws (150 mm)\n"
            "• 3.1 × 90 mm galvanised round-wire nails\n"
            "• 4.0 × 65 mm screws (Torx)\n• Construction adhesive\n"
            "• DPC membrane\n• Vapour-control layer (VCL) tape",
        ],
    ]
    t = Table(cols, colWidths=[(PAGE_W - 2 * MARGIN) / 4] * 4)
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0), C_MID),
        ("TEXTCOLOR",    (0, 0), (-1, 0), C_WHITE),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0), 8),
        ("FONTNAME",     (0, 1), (-1, 1), "Helvetica"),
        ("FONTSIZE",     (0, 1), (-1, 1), 8),
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
        ("GRID",         (0, 0), (-1, -1), 0.4, C_GREY),
        ("LEFTPADDING",  (0, 0), (-1, -1), 4),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0,0),  (-1,-1),  4),
    ]))
    story.append(t)
    return story


def _section_calcs(r: dict, S) -> list:
    story = []
    story.append(Paragraph("4. Structural Dimensions & Angles", S["H1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=C_MID, spaceAfter=6))

    # Key dimensions table
    dims = [
        ["Parameter",           "Value",           "Notes"],
        ["Building length",     f"{r['L_mm']} mm",  f"{r['L_mm']/1000:.3f} m"],
        ["Building width",      f"{r['W_mm']} mm",  f"{r['W_mm']/1000:.3f} m"],
        ["Roof pitch",          f"{r['pitch_deg']}°", "Angle from horizontal"],
        ["Ridge height (rise)", f"{r['rise_mm']} mm", "Above wall-plate datum"],
        ["Ridge beam length",   f"{r['ridge_len_mm']} mm", "Clear span between hip centres"],
        ["Ridge beam (cut)",    f"{r['ridge_full_mm']} mm", "Allow for hip bearing at each end"],
        ["Common rafter (structural)", f"{r['common_struct_mm']} mm", "Wall plate to ridge"],
        ["Common rafter (total)", f"{r['common_total_mm']} mm", "Including overhang tail"],
        ["Hip rafter (structural)", f"{r['hip_struct_mm']} mm", "Corner to ridge end"],
        ["Hip rafter (total)",  f"{r['hip_total_mm']} mm", "Including overhang tail"],
        ["Hip pitch",           f"{r['hip_pitch_deg']}°",  "Hip rafter slope angle"],
    ]
    col_w = [(PAGE_W - 2 * MARGIN) * x for x in [0.40, 0.25, 0.35]]
    t = Table(dims, colWidths=col_w)
    t.setStyle(_ts())
    story.append(t)
    story.append(Spacer(1, 6 * mm))

    # Angles table
    story.append(Paragraph("Cut Angles", S["H2"]))
    angles = [
        ["Cut",                             "Angle",    "Where measured"],
        ["Common rafter plumb cut",         f"{r['plumb_cut_deg']}°",
         "From vertical — set saw bevel to this angle"],
        ["Common rafter seat cut (bird's mouth)", f"{r['seat_cut_deg']}°",
         "From horizontal — 90° − plumb cut"],
        ["Rafter tail plumb cut",           f"{r['plumb_cut_deg']}°",
         "Same as plumb cut — fascia sits vertical"],
        ["Hip rafter plumb cut",            f"{r['hip_plumb_deg']}°",
         "From vertical on the hip rafter face"],
        ["Hip rafter backing bevel",        f"{r['hip_backing_deg']}°",
         "Planed/sawn along the top arris each side"],
        ["Hip ridge compound — mitre",      f"{r['hip_ridge_mitre_deg']}°",
         "Table rotation on mitre saw"],
        ["Hip ridge compound — bevel",      f"{r['hip_ridge_bevel_deg']}°",
         "Blade tilt on mitre saw"],
        ["Jack rafter plumb cut",           f"{r['plumb_cut_deg']}°",
         "Same as common rafter"],
        ["Jack rafter side (cheek) cut",    f"{r['jack_side_cut_deg']}°",
         "Top-edge of rafter where it meets hip"],
        ["Bird's mouth seat depth",         f"{r['bird_mouth_depth_mm']} mm",
         "Max ⅓ × rafter depth"],
        ["Bird's mouth seat width",         f"{r['bird_mouth_width_mm']} mm",
         "Equals wall-plate width"],
    ]
    col_w2 = [(PAGE_W - 2 * MARGIN) * x for x in [0.38, 0.15, 0.47]]
    t2 = Table(angles, colWidths=col_w2)
    t2.setStyle(_ts())
    story.append(t2)

    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(
        "<b>Note on the hip-rafter backing bevel:</b> The top arris of the hip "
        "rafter must be bevelled on both sides so that the roof deck (OSB pods) "
        f"lies flat. Set a sliding bevel or digital angle finder to "
        f"<b>{r['hip_backing_deg']}°</b> and plane or saw a chamfer along the "
        "full length of the top edge on both faces.",
        S["Body"]))

    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(
        "<b>Note on the jack rafter side (cheek) cut:</b> At the head of each "
        "jack rafter (where it meets the side face of the hip rafter), a "
        f"compound cut is required. Set the mitre saw to <b>{r['jack_side_cut_deg']}°</b> "
        f"rotation and <b>{r['plumb_cut_deg']}°</b> blade bevel. Mirror the "
        "angle for the opposing corner.",
        S["Body"]))

    return story


def _section_cut_list(r: dict, S) -> list:
    story = []
    story.append(Paragraph("5. Structural Timber Cut List", S["H1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=C_MID, spaceAfter=6))

    story.append(Paragraph(
        "All lengths include a 5 mm saw-kerf and machining allowance. "
        "Always mark and cut to the nearest whole millimetre. "
        "Timber grade: C24 structural softwood unless noted otherwise.",
        S["Body"]))
    story.append(Spacer(1, 4 * mm))

    # Build table from cut list
    rows = [["#", "Item", "Section", "Length (mm)", "Qty", "Cut notes"]]
    for i, item in enumerate(r["cut_list"], 1):
        rows.append([
            str(i),
            item["item"],
            item["section"],
            str(item["length"]),
            str(item["qty"]),
            item["cuts"],
        ])

    col_w = [(PAGE_W - 2 * MARGIN) * x for x in [0.04, 0.17, 0.14, 0.09, 0.04, 0.52]]
    t = Table(rows, colWidths=col_w, repeatRows=1)
    t.setStyle(_ts(
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
    ))
    story.append(t)

    # Running totals
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph("Timber Order Summary (+ 10 % waste)", S["H2"]))
    tot_rows = [["Section / Grade", "Net linear m", "Order (with 10% waste)"]]
    for item in r["timber_totals"]:
        tot_rows.append([
            item["section"],
            f"{item['total_lm']:.2f} m",
            f"{item['order_lm']:.2f} m",
        ])
    col_w2 = [(PAGE_W - 2 * MARGIN) * x for x in [0.55, 0.22, 0.23]]
    t2 = Table(tot_rows, colWidths=col_w2, repeatRows=1)
    t2.setStyle(_ts())
    story.append(t2)

    return story


def _section_pods(r: dict, S) -> list:
    story = []
    story.append(Paragraph("6. Pod (Insulation Cassette) Construction", S["H1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=C_MID, spaceAfter=6))

    story.append(Paragraph(
        "Each pod is a factory-like cassette assembled on the ground, "
        "then lifted and slotted between adjacent rafters. This approach "
        "ensures consistent insulation, correct air gap, and a flat deck "
        "for the final roof covering — all without working at height for long periods.",
        S["Body"]))

    # Pod cross-section diagram
    story.append(Paragraph("Pod Cross-Section Detail", S["H2"]))
    psec = _pod_section_sketch(r, width=130 * mm)
    story.append(psec)
    story.append(Paragraph(
        f"Pod outer width = {r['pod_width_mm']} mm  |  "
        f"Total depth = {r['pod_total_depth_mm']} mm  |  "
        f"Insulation = {r['insul_depth_mm']} mm PIR  |  "
        f"Air gap = {r['air_gap_mm']} mm",
        S["Caption"]))
    story.append(Spacer(1, 4 * mm))

    # Pod dimensions table
    story.append(Paragraph("Pod Size Schedule", S["H2"]))
    pod_rows = [["Pod type", "Width (mm)", "Length (mm)", "Qty",
                 "OSB panels (2 faces)", "Frame long sides", "Frame end pieces"]]

    pod_w = r["pod_width_mm"]
    pod_end = pod_w - 94   # 2 × 47 mm

    # Common pods
    pod_rows.append([
        "Common rafter pod",
        str(pod_w),
        str(r["common_pod_l_mm"]),
        str(r["n_common_pods"]),
        f"{r['n_common_pods'] * 2} × {pod_w}×{r['common_pod_l_mm']} mm",
        f"{r['n_common_pods'] * 2} × 47×150×{r['common_pod_l_mm']} mm",
        f"{r['n_common_pods'] * 2} × 47×150×{pod_end} mm",
    ])

    for jp in r["jack_pods"]:
        pod_rows.append([
            f"Jack pod (j={jp['j']})",
            str(pod_w),
            str(jp["l_mm"]),
            str(jp["qty"]),
            f"{jp['qty'] * 2} × {pod_w}×{jp['l_mm']} mm",
            f"{jp['qty'] * 2} × 47×150×{jp['l_mm']} mm",
            f"{jp['qty'] * 2} × 47×150×{pod_end} mm",
        ])

    col_w = [(PAGE_W - 2 * MARGIN) / 7] * 7
    t = Table(pod_rows, colWidths=col_w, repeatRows=1)
    t.setStyle(_ts(("FONTSIZE", (0, 0), (-1, -1), 7)))
    story.append(t)

    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph("Pod Assembly Procedure", S["H2"]))

    steps = [
        ("Prepare a flat assembly table", (
            "Lay two 2.4 m scaffold boards side by side on trestles to create "
            "a flat surface. Mark the pod width and length on the table with "
            "a chalk line."
        )),
        ("Cut the frame pieces", (
            "From 47 × 150 mm C24/CLS, cut two long sides to the pod length "
            "and two end pieces to (pod width − 94 mm). Label each piece."
        )),
        ("Assemble the perimeter frame", (
            "Lay the two long sides parallel, separated by the end pieces at "
            "each end. The end pieces sit inside the long sides. "
            "Pre-drill and fix with 4.0 × 90 mm screws through the long sides "
            "into the ends. Check square with a diagonal measurement (both "
            "diagonals must be equal)."
        )),
        ("Fix the inner OSB face", (
            "Place the frame on an 18 mm OSB panel. Mark and cut the OSB to "
            "pod outer width × pod length. Apply construction adhesive to the "
            "bottom face of the frame. Position the OSB and fix with 3.1 × 65 mm "
            "ring-shank nails at 150 mm centres around the perimeter. "
            "This is the interior-facing surface."
        )),
        ("Install the vapour-control layer (optional)", (
            "For a warm roof (insulation at rafter level), a VCL is recommended "
            "on the warm side of the insulation. Staple a 500-gauge polythene "
            "sheet or proprietary VCL over the inner OSB, lapping 150 mm up "
            "the frame sides. Tape all laps."
        )),
        ("Cut and fit the PIR insulation", (
            f"Cut {r['insul_depth_mm']} mm PIR boards (e.g., Kingspan TP10 or "
            "Recticel Eurowall) to fit tightly inside the frame. "
            f"The insulation should sit flush with the frame at "
            f"{r['insul_depth_mm']} mm from the bottom OSB face, leaving a clear "
            f"{r['air_gap_mm']} mm air space above."
        )),
        ("Install air-gap spacer battens", (
            f"To maintain the {r['air_gap_mm']} mm air gap, fix two 47 × 47 mm CLS "
            "noggins across the pod at one-third and two-third points, "
            f"positioned {r['insul_depth_mm']} mm above the bottom OSB. "
            "These sit on top of the insulation and support the outer OSB."
        )),
        ("Fix the outer OSB deck", (
            "Apply construction adhesive to the tops of the frame and spacer "
            "battens. Lay the second OSB panel (same dimensions as the first) "
            "and fix with 3.1 × 65 mm nails at 150 mm centres. "
            "This outer face becomes the structural roof deck."
        )),
        ("Label and stack pods", (
            "Write the pod type (Common / Jack j=1 / etc.) on the side in "
            "marker pen. Stack pods flat, supported at both ends, until needed."
        )),
    ]

    for n, (title, body) in enumerate(steps, 1):
        story.append(Paragraph(f"Step {n}: {title}", S["Step"]))
        story.append(Paragraph(body, S["StepBody"]))

    return story


def _section_osb(r: dict, S) -> list:
    story = []
    story.append(Paragraph("7. OSB Cutting Schedule", S["H1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=C_MID, spaceAfter=6))

    story.append(Paragraph(
        f"Sheet size: <b>{r['osb_sheet_label']}</b>.  "
        f"Pod panel width: <b>{r['osb_pod_w_mm']} mm</b>.  "
        f"Strips per sheet (cut from 1220 mm dimension): "
        f"<b>{r['osb_strips_per_sheet']}</b>.  "
        f"Total OSB panels required: <b>{r['osb_total_panels']}</b>  "
        f"(net area {r['osb_total_area_m2']} m²).  "
        f"Sheets to purchase: <b>{r['osb_sheets_required']}</b>  "
        f"(covers {r['osb_bought_area_m2']} m², "
        f"estimated waste {r['osb_waste_pct']} %).",
        S["Body"]))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph(
        "Cutting method: Set the circular-saw rip fence to "
        f"{r['osb_pod_w_mm']} mm and rip strips along the <i>1220 mm edge</i> "
        "of each sheet first, giving strips of "
        f"{r['osb_pod_w_mm']} mm × 2440 mm. "
        "Then crosscut each strip to the individual panel lengths listed below.",
        S["Body"]))
    story.append(Spacer(1, 4 * mm))

    # Sheet-by-sheet schedule (limit to 10 sheets for brevity)
    schedule = r.get("osb_cutting_schedule", [])
    max_sheets = min(len(schedule), 12)
    if schedule:
        rows = [["Sheet", "Strip", "Cut panels (mm lengths)", "Offcut (mm)"]]
        for sheet in schedule[:max_sheets]:
            for strip in sheet["strips"]:
                rows.append([
                    str(sheet["sheet"]),
                    str(strip["strip"]),
                    "  +  ".join(str(p) for p in strip["panels"]),
                    str(strip["waste_mm"]),
                ])
        col_w = [(PAGE_W - 2 * MARGIN) * x for x in [0.08, 0.08, 0.72, 0.12]]
        t = Table(rows, colWidths=col_w, repeatRows=1)
        t.setStyle(_ts(("FONTSIZE", (0, 0), (-1, -1), 8)))
        story.append(t)
        if len(schedule) > max_sheets:
            story.append(Paragraph(
                f"(Sheets {max_sheets + 1}–{len(schedule)} follow the same pattern.)",
                S["TableNote"]))

    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        "<b>Tip:</b> Always cut strips slightly oversize (+2 mm) first, then "
        "trim to final width with a second pass. Mark panel top faces with a "
        "'T' to ensure consistent orientation during installation.",
        S["Body"]))

    return story


def _section_assembly(r: dict, S) -> list:
    story = []
    story.append(Paragraph("8. Assembly Instructions", S["H1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=C_MID, spaceAfter=6))

    phases = [
        {
            "title": "Phase 1 — Preparatory Work & Removal of Existing Roof",
            "steps": [
                ("Survey and record", (
                    "Photograph all fixings and connections before dismantling. "
                    "Check the masonry walls and existing wall plates for damage. "
                    "Engage a structural engineer to confirm the wall-plate level, "
                    "existing lintel sizes, and new load paths."
                )),
                ("Erect scaffolding", (
                    "Install full perimeter scaffolding with edge boards and "
                    "toe-boards. Ensure a safe working platform at eave level "
                    "and a separate upper lift at ridge level if required."
                )),
                ("Disconnect services", (
                    "Isolate and remove any electrical fittings, gutters, "
                    "downpipes, and cladding attached to the existing roof frame."
                )),
                ("Remove existing roof panels", (
                    "Dismantle the existing aluminium roof sections from the ridge "
                    "downwards, working symmetrically on both sides to avoid "
                    "unbalanced loading. Dispose of aluminium responsibly (it is recyclable)."
                )),
                ("Remove existing ridge and rafters", (
                    "Once panels are clear, remove the existing ridge bar and all "
                    "aluminium rafters. Inspect and clean the existing wall plates; "
                    "replace any that show rot or damage."
                )),
            ],
        },
        {
            "title": "Phase 2 — Wall Plates & Setting Out",
            "steps": [
                ("Lay new wall plates", (
                    f"Bed {r['wp_short_mm']} mm wall plates (47 × 100 mm C16 treated) "
                    "on fresh DPC (damp-proof course) around the full perimeter. "
                    "Level with packing as needed. The long-wall plates run the "
                    f"full {r['wp_long_mm']} mm; mitre or halve at corners."
                )),
                ("Anchor wall plates", (
                    "Fix with M10 × 150 mm coach screws at 600 mm centres into "
                    "rawlbolts set into the masonry. Pre-drill and countersink. "
                    "Check that wall plates are level, square (check diagonals), "
                    "and parallel."
                )),
                ("Mark rafter positions", (
                    f"From each corner, mark the hip rafter position (at 45° to "
                    f"both wall plates). Then mark common rafter positions at "
                    f"{int(r.get('spacing_mm', 600) if 'spacing_mm' in r else r['jack_lengths'][0]['run_mm'] if r['jack_lengths'] else 600)} mm "
                    "centres along the long wall plates between the hip zones. "
                    "Mark jack rafter positions in the hip zones. Use a chalk line."
                )),
            ],
        },
        {
            "title": "Phase 3 — Ridge Beam",
            "steps": [
                ("Build a temporary ridge prop", (
                    "Construct a temporary prop (e.g., from 100 × 100 mm posts "
                    "and a horizontal ledger) to hold the ridge beam at the correct "
                    f"height: wall-plate datum + {r['rise_mm']} mm, aligned on the "
                    "centre line of the building."
                )),
                ("Lift and position the ridge beam", (
                    f"The ridge beam ({r['ridge_full_mm']} mm long × {47} × 200 mm "
                    "C24) is heavy — use two people and lifting straps. "
                    "Set it on the temporary prop, crown side up, centred over "
                    "the building centre line."
                )),
                ("Confirm ridge level", (
                    "Check the ridge is level along its length with a spirit level "
                    "and plumb bob. Adjust the prop until perfect. Mark the ends "
                    f"where the hip rafters will bear (at {int(r['W_mm'] // 2)} mm "
                    "from each building corner on the ridge centre line)."
                )),
            ],
        },
        {
            "title": "Phase 4 — Hip Rafters",
            "steps": [
                ("Cut the ridge-end compound cut", (
                    f"At the head of each hip rafter, set the mitre saw to "
                    f"<b>{r['hip_ridge_mitre_deg']}° rotation</b> and "
                    f"<b>{r['hip_ridge_bevel_deg']}° blade bevel</b>. "
                    "Make the compound cut. Two opposing cuts will butt together "
                    "at each end of the ridge, splitting the ridge width."
                )),
                ("Cut the eave plumb cut and bird's mouth", (
                    f"At the foot of each hip rafter, cut the plumb cut at "
                    f"<b>{r['hip_plumb_deg']}°</b>. Cut the bird's mouth: "
                    f"seat depth <b>{r['bird_mouth_depth_mm']} mm</b>, "
                    f"seat width <b>{r['bird_mouth_width_mm']} mm</b>. "
                    "Test-fit on the wall-plate corner before final fixing."
                )),
                ("Back the hip rafter", (
                    f"Using a block plane or a circular saw set to "
                    f"<b>{r['hip_backing_deg']}°</b>, bevel the top arris on "
                    "both sides of the hip rafter along its full length. "
                    "This allows the roof deck to sit flat on the hip."
                )),
                ("Install hip rafters", (
                    "Offer each hip rafter into position — foot on the wall-plate "
                    "corner, head against the ridge end. Nail through the ridge "
                    "with 3.1 × 90 mm nails (3 per side) and fix the bird's mouth "
                    "to the wall plate with a framing anchor (joist hanger or "
                    "L-bracket). Repeat for all 4 hip rafters."
                )),
            ],
        },
        {
            "title": "Phase 5 — Common Rafters",
            "steps": [
                ("Cut common rafters", (
                    f"Using the mitre saw set to <b>{r['plumb_cut_deg']}° bevel</b>:\n"
                    f"  • Ridge end: plumb cut.\n"
                    f"  • Bird's mouth: plumb cut + horizontal seat cut at "
                    f"{r['bird_mouth_depth_mm']} mm depth.\n"
                    f"  • Tail: plumb cut (so fascia board sits vertical).\n"
                    "Cut all common rafters to "
                    f"{r['common_total_mm']} mm. "
                    "Use the first rafter as a template."
                )),
                ("Install common rafters", (
                    "Nail the ridge end first (skew-nail through the side of the "
                    "rafter into the ridge). Fit the bird's mouth over the wall "
                    "plate; fix with a framing anchor each side. "
                    f"Space at <b>{int(r.get('spacing_mm', 600) if 'spacing_mm' in r else r['jack_lengths'][0]['run_mm'] if r['jack_lengths'] else 600)} mm</b> centres. "
                    "Install front and back rafters opposite each other to keep the "
                    "ridge beam straight."
                )),
                ("Check plumb and position", (
                    "After every four pairs, check that the ridge has not drifted "
                    "and that all rafters are truly plumb (not twisted). Adjust "
                    "before fixing becomes permanent."
                )),
            ],
        },
        {
            "title": "Phase 6 — Jack Rafters",
            "steps": [
                ("Cut jack rafters", (
                    f"Each jack rafter has a plumb cut at the foot (same as common, "
                    f"<b>{r['plumb_cut_deg']}°</b>) and a compound cut at the head "
                    f"where it meets the hip: blade bevel <b>{r['plumb_cut_deg']}°</b>, "
                    f"table rotation <b>{r['jack_side_cut_deg']}°</b>. "
                    "Mirror the rotation for opposing corners. "
                    "The bird's mouth is identical to the common rafter."
                )),
                ("Install jack rafters", (
                    "Offer the jack rafter up so the head sits flush against the "
                    "side face of the hip rafter and the foot bird's mouth sits "
                    "on the wall plate. Nail through the hip with two 3.1 × 90 mm "
                    "nails, and fit a framing anchor at the wall plate."
                )),
                ("Work symmetrically", (
                    "Install jacks in opposing pairs (front and back of each hip "
                    "end simultaneously) to prevent any lateral loading on the hips."
                )),
            ],
        },
        {
            "title": "Phase 7 — Install Pods",
            "steps": [
                ("Weather protection", (
                    "Before installing pods, tack a temporary waterproof membrane "
                    "(breathable roofing felt) over the structural frame to protect "
                    "against rain. Remove bay by bay as pods go in."
                )),
                ("Slide pods into position", (
                    "Working from the ridge downwards, lift each pod and slide it "
                    f"into the {r['pod_width_mm']} mm gap between adjacent rafters. "
                    "The pod should drop until its outer OSB face is flush with the "
                    "top of the rafter. If tight, use a rubber mallet gently."
                )),
                ("Fix pods", (
                    "Screw through the outer OSB into the side of each rafter at "
                    "300 mm centres using 4.0 × 65 mm screws. Alternatively, nail "
                    "through the rafter into the pod frame from the side using "
                    "3.1 × 90 mm nails at 300 mm centres."
                )),
                ("Seal joints between pods", (
                    "At the ridge, cut the top OSB of each pod to the required "
                    "angle and seal with expanding polyurethane foam. At the eave, "
                    "the pod terminates at the wall plate; seal with foam or "
                    "mineral wool draught strip."
                )),
                ("Install tapered wedge pieces at hips", (
                    "At the hip rafter, the triangular gap between the backed hip "
                    "surface and the pod OSB is filled with a tapered cut of OSB "
                    "or flexible insulation, then sealed with adhesive foam. "
                    "This ensures no cold bridges at the hip line."
                )),
            ],
        },
        {
            "title": "Phase 8 — Roof Deck & Weatherproofing",
            "steps": [
                ("Breathable roofing membrane", (
                    "Once all pods are in place, lay a BS 4016 class 1F breathable "
                    "roofing underlay (e.g., Tyvek Supro or Klober Permo Air) over "
                    "the outer OSB deck, starting at the eave and lapping 150 mm "
                    "at horizontal joints, 200 mm at vertical joints. "
                    "Fix with clout nails at 300 mm centres."
                )),
                ("Counter-battens", (
                    "Fix 25 × 50 mm pressure-treated counter-battens directly over "
                    "the rafters (through the membrane and OSB into the rafter) at "
                    "each rafter position. Length = rafter spacing. "
                    "This creates a secondary ventilated zone above the membrane "
                    "and provides a clear drainage channel."
                )),
                ("Tiling battens", (
                    "Fix tiling battens (25 × 50 mm treated) across the counter-battens "
                    "at the gauge required for your chosen tile or slate. "
                    "Use a gauge rod to ensure consistent spacing."
                )),
                ("Hip caps and ridge cap", (
                    "At each hip, fix a hip iron at the eave and bed hip tiles "
                    "(or install a proprietary dry-fix hip system). At the ridge, "
                    "bed a ridge tile or fit a dry-fix ridge. Apply mortar or use "
                    "proprietary bonding compound."
                )),
                ("Gutters, fascia, and soffit", (
                    "Fix fascia boards to the rafter tails (plumb face, matching the "
                    "plumb cut). Fix soffit boards horizontally from fascia to wall. "
                    "Ensure a 10 mm ventilation gap at the eave between soffit and "
                    "breathable membrane to allow the air gap in each pod to vent "
                    "to the outside."
                )),
            ],
        },
        {
            "title": "Phase 9 — Internal Finishing",
            "steps": [
                ("Inspect from inside", (
                    "Once the roof is weathertight, inspect all pod joints from "
                    "inside. There should be no visible light gaps. Seal any gaps "
                    "with flexible sealant or additional insulation strips."
                )),
                ("Vapour control layer", (
                    "If not pre-installed in the pods, fix a 500-gauge polythene "
                    "VCL across the inner OSB faces, lapping and taping all joints. "
                    "This is critical to prevent interstitial condensation."
                )),
                ("Internal lining", (
                    "The inner OSB face of the pods can be left exposed (sanded and "
                    "oiled/painted) or can be lined with plasterboard on resilient "
                    "bar to provide a plastered ceiling. "
                    "Ensure any electrical or lighting cables are routed in conduit."
                )),
            ],
        },
    ]

    for phase in phases:
        story.append(Paragraph(phase["title"], S["H2"]))
        for n, (title, body) in enumerate(phase["steps"], 1):
            story.append(Paragraph(f"  {n}. {title}", S["Step"]))
            story.append(Paragraph(body, S["StepBody"]))
        story.append(Spacer(1, 4 * mm))

    # Final notes
    story.append(HRFlowable(width="100%", thickness=1, color=C_MID, spaceAfter=6))
    story.append(Paragraph("9. Final Checks & Sign-Off", S["H1"]))
    checks = [
        "All rafter birds'-mouths fully bearing on wall plates.",
        "All framing anchors installed and nailed.",
        "All pod-to-rafter fixings complete at 300 mm centres.",
        "All inter-pod joints sealed (no air paths).",
        "Breathable membrane lapped and fixed — no tears.",
        "Counter-battens and tiling battens at correct gauge.",
        "Hip tiles and ridge bedded / dry-fixed.",
        "Ventilation gap maintained at eave soffit.",
        "VCL complete on warm side with all laps taped.",
        "Building Control / LABC inspection booked if applicable.",
    ]
    for chk in checks:
        story.append(Paragraph(f"☐  {chk}", S["Bullet"]))

    return story
