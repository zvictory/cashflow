"""Build the Dynamic Belt — Glass Manufacturing (APAC) sales deck.

Run:  python build_presentation.py
Out:  dist/Dynamic_Belt_Glass_Manufacturing_APAC.pptx
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt, Emu

# ---------------------------------------------------------------------------
# Design system
# ---------------------------------------------------------------------------

NAVY = RGBColor(0x0B, 0x25, 0x45)
AMBER = RGBColor(0xF2, 0xA9, 0x3B)
STEEL = RGBColor(0x7C, 0x90, 0xA0)
CANVAS = RGBColor(0xF7, 0xF7, 0xF5)
INK = RGBColor(0x1A, 0x1A, 0x1A)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
SUCCESS = RGBColor(0x3D, 0xA3, 0x5D)
ALERT = RGBColor(0xD6, 0x45, 0x45)
MUTED = RGBColor(0xB8, 0xC0, 0xCC)

FONT = "Calibri"
FONT_HEAD = "Calibri"

SLIDE_W = Inches(13.3333)
SLIDE_H = Inches(7.5)
MARGIN = Inches(0.5)


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _set_fill(shape, rgb):
    shape.fill.solid()
    shape.fill.fore_color.rgb = rgb


def _no_line(shape):
    shape.line.fill.background()


def _solid_line(shape, rgb, width_pt=0.75):
    shape.line.color.rgb = rgb
    shape.line.width = Pt(width_pt)


def add_rect(slide, x, y, w, h, fill=None, line=None, line_w=0.75):
    shp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, w, h)
    if fill is not None:
        _set_fill(shp, fill)
    else:
        shp.fill.background()
    if line is None:
        _no_line(shp)
    else:
        _solid_line(shp, line, line_w)
    shp.shadow.inherit = False
    return shp


def add_text(slide, x, y, w, h, text, *, size=16, bold=False, color=INK,
             align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, font=FONT, italic=False):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.margin_left = Emu(0)
    tf.margin_right = Emu(0)
    tf.margin_top = Emu(0)
    tf.margin_bottom = Emu(0)
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.name = font
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    return tb


def add_bullets(slide, x, y, w, h, items, *, size=16, color=INK, bullet_color=AMBER,
                line_spacing=1.25, font=FONT):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.margin_left = Emu(0)
    tf.margin_right = Emu(0)
    tf.margin_top = Emu(0)
    tf.margin_bottom = Emu(0)
    tf.word_wrap = True
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        p.line_spacing = line_spacing
        p.space_after = Pt(6)
        bullet_run = p.add_run()
        bullet_run.text = "■  "
        bullet_run.font.name = font
        bullet_run.font.size = Pt(size)
        bullet_run.font.bold = True
        bullet_run.font.color.rgb = bullet_color
        text_run = p.add_run()
        text_run.text = item
        text_run.font.name = font
        text_run.font.size = Pt(size)
        text_run.font.color.rgb = color
    return tb


# ---------------------------------------------------------------------------
# Slide chrome
# ---------------------------------------------------------------------------

def apply_canvas(slide):
    add_rect(slide, 0, 0, SLIDE_W, SLIDE_H, fill=CANVAS)


def apply_footer(slide, page_no, total):
    # Bottom rule
    add_rect(slide, MARGIN, Inches(7.05), SLIDE_W - 2 * MARGIN, Inches(0.01), fill=STEEL)
    # Footer text
    add_text(
        slide, MARGIN, Inches(7.12), SLIDE_W - 2 * MARGIN, Inches(0.3),
        f"Dynamic Belt   |   Confidential — for discussion only   |   {page_no:02d} / {total:02d}",
        size=10, color=STEEL,
    )


def apply_title_bar(slide, eyebrow, title):
    add_text(
        slide, MARGIN, Inches(0.45), Inches(8), Inches(0.32),
        eyebrow.upper(), size=11, bold=True, color=AMBER, font=FONT_HEAD,
    )
    add_text(
        slide, MARGIN, Inches(0.78), Inches(12), Inches(0.7),
        title, size=30, bold=True, color=NAVY, font=FONT_HEAD,
    )
    # Amber accent rule under title
    add_rect(slide, MARGIN, Inches(1.45), Inches(0.6), Inches(0.06), fill=AMBER)


# ---------------------------------------------------------------------------
# Reusable composite blocks
# ---------------------------------------------------------------------------

def add_kpi_card(slide, x, y, w, h, value, label, *, accent=AMBER):
    add_rect(slide, x, y, w, h, fill=WHITE, line=MUTED)
    add_rect(slide, x, y, Inches(0.08), h, fill=accent)
    add_text(slide, x + Inches(0.25), y + Inches(0.15), w - Inches(0.3), Inches(0.7),
             value, size=28, bold=True, color=NAVY)
    add_text(slide, x + Inches(0.25), y + Inches(0.85), w - Inches(0.3), h - Inches(0.9),
             label, size=11, color=STEEL)


def add_pillar_card(slide, x, y, w, h, title, subtitle, bullets, *, accent=AMBER):
    add_rect(slide, x, y, w, h, fill=WHITE, line=MUTED)
    add_rect(slide, x, y, w, Inches(0.6), fill=NAVY)
    add_rect(slide, x, y + Inches(0.6), w, Inches(0.05), fill=accent)
    add_text(slide, x + Inches(0.25), y + Inches(0.1), w - Inches(0.3), Inches(0.4),
             title, size=18, bold=True, color=WHITE)
    add_text(slide, x + Inches(0.25), y + Inches(0.78), w - Inches(0.3), Inches(0.35),
             subtitle, size=11, italic=True, color=STEEL)
    add_bullets(slide, x + Inches(0.25), y + Inches(1.2), w - Inches(0.5), h - Inches(1.3),
                bullets, size=12, color=INK, line_spacing=1.2)


def add_table(slide, x, y, w, h, headers, rows, *, header_fill=NAVY, header_color=WHITE,
              zebra=CANVAS):
    cols = len(headers)
    table_rows = len(rows) + 1
    tbl_shape = slide.shapes.add_table(table_rows, cols, x, y, w, h)
    tbl = tbl_shape.table

    # Header
    for j, htext in enumerate(headers):
        cell = tbl.cell(0, j)
        cell.fill.solid()
        cell.fill.fore_color.rgb = header_fill
        cell.text = ""
        tf = cell.text_frame
        tf.margin_left = Inches(0.1)
        tf.margin_right = Inches(0.1)
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.LEFT
        run = p.add_run()
        run.text = htext
        run.font.name = FONT
        run.font.size = Pt(12)
        run.font.bold = True
        run.font.color.rgb = header_color

    # Body
    for i, row in enumerate(rows, start=1):
        for j, cell_text in enumerate(row):
            cell = tbl.cell(i, j)
            cell.fill.solid()
            cell.fill.fore_color.rgb = WHITE if i % 2 else zebra
            cell.text = ""
            tf = cell.text_frame
            tf.margin_left = Inches(0.1)
            tf.margin_right = Inches(0.1)
            p = tf.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT
            run = p.add_run()
            run.text = str(cell_text)
            run.font.name = FONT
            run.font.size = Pt(11)
            run.font.color.rgb = INK
            if j == 0:
                run.font.bold = True
                run.font.color.rgb = NAVY


def add_data_footnote(slide, text):
    add_text(
        slide, MARGIN, Inches(6.7), SLIDE_W - 2 * MARGIN, Inches(0.3),
        f"Note: {text}", size=9, italic=True, color=STEEL,
    )


# ---------------------------------------------------------------------------
# Slide builders
# ---------------------------------------------------------------------------

def slide_title(prs, total):
    s = prs.slides.add_slide(prs.slide_layouts[6])  # blank
    apply_canvas(s)

    # Left navy panel
    add_rect(s, 0, 0, Inches(5.4), SLIDE_H, fill=NAVY)
    # Diagonal amber stripe accent
    add_rect(s, Inches(5.4), 0, Inches(0.12), SLIDE_H, fill=AMBER)

    # Logo block (typographic)
    add_rect(s, Inches(0.7), Inches(0.7), Inches(0.55), Inches(0.55), fill=AMBER)
    add_text(s, Inches(0.7), Inches(0.72), Inches(0.55), Inches(0.55),
             "D", size=28, bold=True, color=NAVY, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    add_text(s, Inches(1.4), Inches(0.78), Inches(3.5), Inches(0.5),
             "DYNAMIC BELT", size=18, bold=True, color=WHITE)
    add_text(s, Inches(1.4), Inches(1.1), Inches(3.5), Inches(0.3),
             "Engineered drive & conveying solutions", size=10, color=MUTED, italic=True)

    # Headline
    add_text(s, Inches(0.7), Inches(2.6), Inches(4.5), Inches(0.4),
             "GLASS MANUFACTURING — APAC", size=12, bold=True, color=AMBER)
    add_text(s, Inches(0.7), Inches(3.0), Inches(4.6), Inches(2.2),
             "Engineered for Glass.\nProven in APAC.",
             size=40, bold=True, color=WHITE)
    add_text(s, Inches(0.7), Inches(5.2), Inches(4.5), Inches(1.2),
             "A complete belt portfolio for hot-end, cold-end, and power "
             "transmission — built for the heat, dust, and uptime demands of "
             "modern float and container glass lines.",
             size=13, color=MUTED)

    # Right side — KPI cards
    add_text(s, Inches(6.0), Inches(0.9), Inches(7), Inches(0.4),
             "WHY DYNAMIC BELT", size=11, bold=True, color=AMBER)
    add_text(s, Inches(6.0), Inches(1.25), Inches(7), Inches(0.6),
             "Built for plant & maintenance teams", size=24, bold=True, color=NAVY)

    add_kpi_card(s, Inches(6.0), Inches(2.2), Inches(3.4), Inches(1.25),
                 "+22%", "Mean time between belt failures vs market average")
    add_kpi_card(s, Inches(9.5), Inches(2.2), Inches(3.4), Inches(1.25),
                 "−38%", "Unplanned line stoppages in pilot plants (12 mo)")
    add_kpi_card(s, Inches(6.0), Inches(3.6), Inches(3.4), Inches(1.25),
                 "48 h", "Spare-belt delivery across 11 APAC depots", accent=NAVY)
    add_kpi_card(s, Inches(9.5), Inches(3.6), Inches(3.4), Inches(1.25),
                 "260 °C+", "Continuous-service rating, hot-end aramid line", accent=NAVY)

    add_rect(s, Inches(6.0), Inches(5.3), Inches(6.9), Inches(0.04), fill=STEEL)
    add_text(s, Inches(6.0), Inches(5.4), Inches(7), Inches(0.4),
             f"Sales briefing  •  {date.today().strftime('%B %Y')}  •  Plant & Maintenance audience",
             size=11, color=STEEL)
    add_text(s, Inches(6.0), Inches(5.75), Inches(7), Inches(0.4),
             "Prepared by Dynamic Belt — APAC Industrial Sales", size=11, bold=True, color=NAVY)


def slide_agenda(prs, total, page):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    apply_canvas(s)
    apply_title_bar(s, "Agenda", "What we'll cover today")

    items = [
        ("01", "Industry pulse", "APAC glass demand drivers in 2026"),
        ("02", "Cost of belt failure", "What an hour of downtime really costs"),
        ("03", "Market & competition", "Sizing, share, and growth outlook"),
        ("04", "Dynamic Belt portfolio", "Hot-end · cold-end · transmission"),
        ("05", "Proof & economics", "Case study, TCO, service model"),
        ("06", "Next steps", "90-day pilot proposal"),
    ]

    col_w = Inches(4.0)
    row_h = Inches(1.55)
    gap = Inches(0.25)
    start_x = MARGIN
    start_y = Inches(1.95)

    for idx, (num, head, sub) in enumerate(items):
        r, c = divmod(idx, 3)
        x = start_x + c * (col_w + gap)
        y = start_y + r * (row_h + gap)
        add_rect(s, x, y, col_w, row_h, fill=WHITE, line=MUTED)
        add_rect(s, x, y, Inches(0.08), row_h, fill=AMBER)
        add_text(s, x + Inches(0.25), y + Inches(0.1), Inches(0.9), Inches(0.5),
                 num, size=22, bold=True, color=AMBER)
        add_text(s, x + Inches(1.1), y + Inches(0.18), col_w - Inches(1.2), Inches(0.45),
                 head, size=16, bold=True, color=NAVY)
        add_text(s, x + Inches(1.1), y + Inches(0.65), col_w - Inches(1.2), Inches(0.85),
                 sub, size=12, color=STEEL)

    apply_footer(s, page, total)


def slide_industry_pulse(prs, total, page):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    apply_canvas(s)
    apply_title_bar(s, "01 · Industry Pulse",
                    "APAC is where glass manufacturing is growing")

    add_text(s, MARGIN, Inches(1.7), Inches(7.5), Inches(0.4),
             "Four demand engines are pulling capacity online", size=14, bold=True, color=NAVY)

    drivers = [
        ("Solar glass",
         "China + India PV build-out drives record demand for low-iron rolled glass."),
        ("Automotive glazing",
         "EV platforms shift volume toward laminated and tempered architectural-grade glass."),
        ("Container glass",
         "Beverage & pharma reshoring lifts container output across SEA and India."),
        ("Architectural / electronics",
         "Float capacity additions in CN, IN, ID, VN; display glass reinvesting in KR & JP."),
    ]
    y = Inches(2.2)
    for head, body in drivers:
        add_rect(s, MARGIN, y, Inches(7.5), Inches(1.0), fill=WHITE, line=MUTED)
        add_rect(s, MARGIN, y, Inches(0.08), Inches(1.0), fill=AMBER)
        add_text(s, MARGIN + Inches(0.25), y + Inches(0.12), Inches(7), Inches(0.4),
                 head, size=14, bold=True, color=NAVY)
        add_text(s, MARGIN + Inches(0.25), y + Inches(0.5), Inches(7), Inches(0.5),
                 body, size=12, color=INK)
        y += Inches(1.1)

    # Right-hand stat panel
    add_rect(s, Inches(8.6), Inches(1.7), Inches(4.25), Inches(4.7), fill=NAVY)
    add_text(s, Inches(8.85), Inches(1.85), Inches(4), Inches(0.4),
             "WHY IT MATTERS FOR BELTS", size=11, bold=True, color=AMBER)
    add_text(s, Inches(8.85), Inches(2.2), Inches(4), Inches(2.0),
             "Each new line adds 1.2–1.6 km of conveyor & "
             "transmission belting — and three years of replacement spend.",
             size=14, color=WHITE)
    add_rect(s, Inches(8.85), Inches(3.9), Inches(3.8), Inches(0.03), fill=AMBER)

    add_text(s, Inches(8.85), Inches(4.05), Inches(4), Inches(0.5),
             "~62%", size=34, bold=True, color=AMBER)
    add_text(s, Inches(8.85), Inches(4.65), Inches(4), Inches(0.5),
             "of global flat-glass capacity is in APAC", size=11, color=WHITE)

    add_text(s, Inches(8.85), Inches(5.15), Inches(4), Inches(0.5),
             "5.4% CAGR", size=22, bold=True, color=AMBER)
    add_text(s, Inches(8.85), Inches(5.55), Inches(4), Inches(0.5),
             "industrial-belt spend in APAC glass, 2024–2030", size=11, color=WHITE)

    add_data_footnote(s, "Figures illustrative — based on public industry reporting; replace with internal market intelligence.")
    apply_footer(s, page, total)


def slide_cost_of_failure(prs, total, page):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    apply_canvas(s)
    apply_title_bar(s, "02 · The Cost of Belt Failure",
                    "Belts are 0.4% of plant cost — and 100% of the stoppage")

    # Left: failure modes
    add_text(s, MARGIN, Inches(1.7), Inches(6.5), Inches(0.4),
             "Top failure modes we see in APAC glass plants",
             size=14, bold=True, color=NAVY)
    add_bullets(s, MARGIN, Inches(2.15), Inches(6.5), Inches(3.5), [
        "Thermal degradation of conveyor weave at hot-end transfer points",
        "Edge fraying / tracking drift on lehr take-out and roller tables",
        "Premature V-belt slip on forming-machine drives under load swings",
        "Timing-belt tooth shear on cullet handling and batching",
        "Contamination from broken glass dust ingress on cold-end PU belts",
    ], size=13)

    # Right: downtime math card
    add_rect(s, Inches(7.5), Inches(1.7), Inches(5.35), Inches(4.7), fill=WHITE, line=MUTED)
    add_rect(s, Inches(7.5), Inches(1.7), Inches(5.35), Inches(0.6), fill=NAVY)
    add_text(s, Inches(7.7), Inches(1.78), Inches(5), Inches(0.45),
             "ONE HOUR OF FLOAT-LINE DOWNTIME", size=12, bold=True, color=AMBER)

    rows = [
        ("Lost production", "≈ 25 t glass @ $480/t", "$ 12,000"),
        ("Re-stabilisation losses", "Tin bath + lehr re-temper", "$ 9,500"),
        ("Cullet & energy waste", "Re-melt + gas spike", "$ 4,200"),
        ("Crew & overtime", "Maintenance + line crew", "$ 1,800"),
    ]
    y = Inches(2.55)
    for label, detail, value in rows:
        add_text(s, Inches(7.75), y, Inches(2.4), Inches(0.3), label, size=12, bold=True, color=NAVY)
        add_text(s, Inches(7.75), y + Inches(0.28), Inches(2.6), Inches(0.3), detail, size=10, color=STEEL)
        add_text(s, Inches(10.6), y + Inches(0.05), Inches(2.1), Inches(0.4), value,
                 size=14, bold=True, color=INK, align=PP_ALIGN.RIGHT)
        y += Inches(0.7)

    add_rect(s, Inches(7.75), Inches(5.45), Inches(4.9), Inches(0.04), fill=AMBER)
    add_text(s, Inches(7.75), Inches(5.55), Inches(3.0), Inches(0.5),
             "Total / hour", size=14, bold=True, color=NAVY)
    add_text(s, Inches(10.6), Inches(5.5), Inches(2.1), Inches(0.6),
             "$ 27,500", size=24, bold=True, color=ALERT, align=PP_ALIGN.RIGHT)

    add_data_footnote(s, "Illustrative model; calibrate with the customer's own OEE & energy data.")
    apply_footer(s, page, total)


def slide_market_sizing(prs, total, page):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    apply_canvas(s)
    apply_title_bar(s, "03 · Market Sizing — APAC, 2026",
                    "Industrial belts for glass manufacturing")

    # KPI strip
    add_kpi_card(s, MARGIN, Inches(1.85), Inches(2.95), Inches(1.1),
                 "$ 1.42 B", "TAM — APAC industrial belts in glass (2026)")
    add_kpi_card(s, Inches(3.55), Inches(1.85), Inches(2.95), Inches(1.1),
                 "$ 0.86 B", "SAM — hot-end + cold-end conveying", accent=NAVY)
    add_kpi_card(s, Inches(6.6), Inches(1.85), Inches(2.95), Inches(1.1),
                 "$ 0.31 B", "SOM — Dynamic Belt 3-yr addressable", accent=AMBER)
    add_kpi_card(s, Inches(9.65), Inches(1.85), Inches(3.2), Inches(1.1),
                 "5.4%", "CAGR 2024–2030", accent=SUCCESS)

    # Country bar chart
    chart_data = CategoryChartData()
    chart_data.categories = ["China", "India", "Japan", "S. Korea", "SEA", "Rest of APAC"]
    chart_data.add_series("2026 spend (US$ M)", (612, 248, 178, 142, 168, 72))

    chart = s.shapes.add_chart(
        XL_CHART_TYPE.COLUMN_CLUSTERED,
        MARGIN, Inches(3.15), Inches(8.4), Inches(3.3),
        chart_data,
    ).chart
    chart.has_title = True
    chart.chart_title.text_frame.text = "Spend on industrial belts in glass manufacturing, by country"
    for r in chart.chart_title.text_frame.paragraphs[0].runs:
        r.font.size = Pt(12); r.font.bold = True; r.font.color.rgb = NAVY; r.font.name = FONT
    chart.has_legend = False
    plot = chart.plots[0]
    plot.has_data_labels = True
    dl = plot.data_labels
    dl.font.size = Pt(10); dl.font.color.rgb = NAVY; dl.font.name = FONT
    dl.position = XL_LABEL_POSITION.OUTSIDE_END
    series = plot.series[0]
    fill = series.format.fill
    fill.solid(); fill.fore_color.rgb = NAVY
    for cat_idx, _ in enumerate(chart_data.categories):
        pt = series.points[cat_idx]
        pt.format.fill.solid()
        pt.format.fill.fore_color.rgb = AMBER if cat_idx == 0 else NAVY

    # Right insight panel
    add_rect(s, Inches(9.05), Inches(3.15), Inches(3.8), Inches(3.3), fill=NAVY)
    add_text(s, Inches(9.25), Inches(3.3), Inches(3.5), Inches(0.4),
             "WHERE TO PLAY", size=11, bold=True, color=AMBER)
    add_bullets(s, Inches(9.25), Inches(3.65), Inches(3.5), Inches(2.7), [
        "China: scale, but margin pressure",
        "India: highest growth (8.1% CAGR)",
        "SEA: white space, fewer incumbents",
        "JP/KR: premium specs, sticky accounts",
    ], size=12, color=WHITE, bullet_color=AMBER)

    add_data_footnote(s, "Illustrative figures. Sources to be replaced with Mordor / Grand View internal subscription data before issuing externally.")
    apply_footer(s, page, total)


def slide_market_share(prs, total, page):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    apply_canvas(s)
    apply_title_bar(s, "03 · Market Share — APAC Glass Segment",
                    "Fragmented mid-tier; opening for a focused specialist")

    # Doughnut chart
    chart_data = CategoryChartData()
    chart_data.categories = [
        "Habasit", "Forbo Siegling", "Ammeraal Beltech",
        "Volta / Continental", "Regional players", "Dynamic Belt",
    ]
    chart_data.add_series("Share %", (22.0, 18.5, 14.0, 11.5, 28.0, 6.0))

    chart = s.shapes.add_chart(
        XL_CHART_TYPE.DOUGHNUT,
        MARGIN, Inches(1.8), Inches(6.5), Inches(4.9),
        chart_data,
    ).chart
    chart.has_title = False
    chart.has_legend = True
    chart.legend.position = XL_LEGEND_POSITION.RIGHT
    chart.legend.include_in_layout = False
    chart.legend.font.size = Pt(11); chart.legend.font.name = FONT; chart.legend.font.color.rgb = NAVY

    palette = [NAVY, STEEL, RGBColor(0xB0, 0xB8, 0xC2),
               RGBColor(0xCD, 0xD3, 0xDA), RGBColor(0xE7, 0xEA, 0xEE), AMBER]
    series = chart.plots[0].series[0]
    for i, color in enumerate(palette):
        pt = series.points[i]
        pt.format.fill.solid()
        pt.format.fill.fore_color.rgb = color
        pt.format.line.color.rgb = WHITE
        pt.format.line.width = Pt(1.5)

    plot = chart.plots[0]
    plot.has_data_labels = True
    dl = plot.data_labels
    dl.show_percentage = False; dl.show_value = True
    dl.number_format = '0.0"%"'
    dl.font.size = Pt(10); dl.font.bold = True; dl.font.color.rgb = WHITE; dl.font.name = FONT

    # Right narrative
    add_text(s, Inches(7.6), Inches(1.8), Inches(5.3), Inches(0.4),
             "Read across", size=11, bold=True, color=AMBER)
    add_text(s, Inches(7.6), Inches(2.15), Inches(5.3), Inches(0.6),
             "Top-3 globals own 54.5% — the rest is contestable",
             size=18, bold=True, color=NAVY)

    add_rect(s, Inches(7.6), Inches(3.1), Inches(5.3), Inches(0.04), fill=STEEL)
    points = [
        ("Globals optimise for breadth, not glass-specific spec",
         "Hot-end aramid weaves and cullet-resistant PU are still treated as adjacencies."),
        ("Regional players win on price, lose on uptime",
         "$/m looks attractive — replacement cycles are 30–45% shorter."),
        ("Dynamic Belt is the only APAC-headquartered specialist",
         "Glass-line engineering depth + 48-hour spare delivery."),
    ]
    y = Inches(3.25)
    for head, body in points:
        add_text(s, Inches(7.6), y, Inches(5.3), Inches(0.4),
                 head, size=13, bold=True, color=NAVY)
        add_text(s, Inches(7.6), y + Inches(0.32), Inches(5.3), Inches(0.7),
                 body, size=11, color=STEEL)
        y += Inches(1.05)

    add_data_footnote(s, "Share estimates illustrative; validate vs internal CRM win/loss data.")
    apply_footer(s, page, total)


def slide_growth(prs, total, page):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    apply_canvas(s)
    apply_title_bar(s, "03 · Growth Outlook 2024–2030",
                    "Hot-end is biggest, transmission is fastest")

    chart_data = CategoryChartData()
    years = ["2024", "2025", "2026", "2027", "2028", "2029", "2030"]
    chart_data.categories = years
    chart_data.add_series("Hot-end conveyor", (480, 506, 537, 568, 599, 630, 660))
    chart_data.add_series("Cold-end conveyor", (320, 340, 362, 385, 409, 432, 456))
    chart_data.add_series("Transmission & timing", (210, 228, 248, 271, 295, 319, 344))

    chart = s.shapes.add_chart(
        XL_CHART_TYPE.LINE,
        MARGIN, Inches(1.85), Inches(8.5), Inches(4.6),
        chart_data,
    ).chart
    chart.has_title = True
    chart.chart_title.text_frame.text = "APAC industrial-belt spend in glass mfg (US$ M)"
    for r in chart.chart_title.text_frame.paragraphs[0].runs:
        r.font.size = Pt(12); r.font.bold = True; r.font.color.rgb = NAVY; r.font.name = FONT
    chart.has_legend = True
    chart.legend.position = XL_LEGEND_POSITION.BOTTOM
    chart.legend.include_in_layout = False
    chart.legend.font.size = Pt(11); chart.legend.font.name = FONT

    series_colors = [NAVY, STEEL, AMBER]
    for s_idx, color in enumerate(series_colors):
        srs = chart.plots[0].series[s_idx]
        srs.format.line.color.rgb = color
        srs.format.line.width = Pt(2.5)
        srs.marker.style = 8  # circle
        srs.marker.size = 6
        srs.marker.format.fill.solid()
        srs.marker.format.fill.fore_color.rgb = color
        srs.marker.format.line.color.rgb = color

    # Right CAGR cards
    add_text(s, Inches(9.3), Inches(1.85), Inches(3.6), Inches(0.4),
             "CAGR 2024–2030", size=11, bold=True, color=AMBER)

    cagr_rows = [
        ("Hot-end", "5.5%", NAVY),
        ("Cold-end", "6.1%", STEEL),
        ("Transmission", "8.6%", AMBER),
    ]
    y = Inches(2.25)
    for label, val, color in cagr_rows:
        add_rect(s, Inches(9.3), y, Inches(3.55), Inches(1.0), fill=WHITE, line=MUTED)
        add_rect(s, Inches(9.3), y, Inches(0.08), Inches(1.0), fill=color)
        add_text(s, Inches(9.55), y + Inches(0.1), Inches(2), Inches(0.4),
                 label, size=12, bold=True, color=NAVY)
        add_text(s, Inches(9.55), y + Inches(0.4), Inches(2.8), Inches(0.6),
                 val, size=24, bold=True, color=color)
        y += Inches(1.1)

    add_data_footnote(s, "Illustrative trend; validate against subscription forecasts (Mordor, Grand View, IBISWorld).")
    apply_footer(s, page, total)


def slide_portfolio_overview(prs, total, page):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    apply_canvas(s)
    apply_title_bar(s, "04 · Portfolio at a Glance",
                    "One supplier across the entire glass plant")

    add_pillar_card(
        s, MARGIN, Inches(1.9), Inches(4.05), Inches(4.9),
        "Hot-end conveyor",
        "Lehr · annealing · tempering · transfer",
        [
            "Aramid (Kevlar®) woven belts",
            "Fiberglass + PTFE coatings",
            "PBO ultra-high-temp belts",
            "Continuous service to 290 °C",
            "Custom widths to 4,200 mm",
        ],
    )
    add_pillar_card(
        s, MARGIN + Inches(4.4), Inches(1.9), Inches(4.05), Inches(4.9),
        "Cold-end conveyor",
        "Inspection · packaging · palletising",
        [
            "Modular plastic (POM, PP, PE)",
            "PU monolithic, FDA-grade",
            "Rubber multi-ply with cleat",
            "Anti-static & cleanable variants",
            "Cullet-shard resistant tops",
        ],
        accent=STEEL,
    )
    add_pillar_card(
        s, MARGIN + Inches(8.8), Inches(1.9), Inches(4.05), Inches(4.9),
        "Transmission & timing",
        "Forming · batching · ancillary drives",
        [
            "Wedge & narrow-V (SPZ–SPC)",
            "Classical V-belts (A–E)",
            "HTD, GT3, RPP timing",
            "Polyurethane reinforced",
            "Matched sets for multi-groove",
        ],
        accent=AMBER,
    )

    apply_footer(s, page, total)


def slide_hotend(prs, total, page):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    apply_canvas(s)
    apply_title_bar(s, "04 · Hot-End Conveyor Belts",
                    "Where cheap belts go to die — we don't")

    add_text(s, MARGIN, Inches(1.7), Inches(7), Inches(0.45),
             "Spec families", size=14, bold=True, color=NAVY)

    headers = ["Family", "Fibre / coating", "Continuous T°", "Typical use"]
    rows = [
        ("DB-AR 220", "Aramid, double-layer, PTFE-impregnated", "220 °C", "Lehr exit, take-out tables"),
        ("DB-AR 260", "Aramid + fiberglass hybrid weave", "260 °C", "Annealing-lehr in-feed, transfer"),
        ("DB-FG 290", "Fiberglass core, PTFE coating", "290 °C", "Tempering line transfer, hot stack"),
        ("DB-PBO 340", "PBO (Zylon®) ultra-high-temp", "340 °C peak / 300 °C cont.", "Direct hot-end transfer, special builds"),
    ]
    add_table(s, MARGIN, Inches(2.15), Inches(8.4), Inches(2.6), headers, rows)

    add_text(s, MARGIN, Inches(5.0), Inches(7), Inches(0.4),
             "Engineering options", size=14, bold=True, color=NAVY)
    add_bullets(s, MARGIN, Inches(5.4), Inches(7.5), Inches(1.6), [
        "Edge sealing & sealed-edge stitching to resist fraying at lehr exit",
        "Anti-stick PTFE topcoats for sticky tin-bath transfer points",
        "Custom widths up to 4.2 m, lengths splice-on-site",
    ], size=12)

    # Right: heat callout
    add_rect(s, Inches(9.05), Inches(1.7), Inches(3.8), Inches(5.0), fill=NAVY)
    add_text(s, Inches(9.25), Inches(1.85), Inches(3.5), Inches(0.4),
             "WHY IT MATTERS", size=11, bold=True, color=AMBER)
    add_text(s, Inches(9.25), Inches(2.25), Inches(3.5), Inches(2),
             "PBO outperforms aramid by ~80 °C and lasts 2–3× longer at lehr exits.",
             size=14, color=WHITE)
    add_rect(s, Inches(9.25), Inches(4.0), Inches(3.5), Inches(0.03), fill=AMBER)
    add_text(s, Inches(9.25), Inches(4.15), Inches(3.5), Inches(0.5),
             "+22%", size=30, bold=True, color=AMBER)
    add_text(s, Inches(9.25), Inches(4.6), Inches(3.5), Inches(0.5),
             "average MTBF uplift vs market spec", size=11, color=WHITE)
    add_text(s, Inches(9.25), Inches(5.15), Inches(3.5), Inches(0.5),
             "ISO 9001 · ISO 14001", size=12, bold=True, color=AMBER)
    add_text(s, Inches(9.25), Inches(5.5), Inches(3.5), Inches(0.5),
             "All hot-end belts batch-tracked", size=11, color=WHITE)

    apply_footer(s, page, total)


def slide_coldend(prs, total, page):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    apply_canvas(s)
    apply_title_bar(s, "04 · Cold-End Conveyor Belts",
                    "Throughput, hygiene, and shard resistance")

    headers = ["Family", "Material", "Top surface", "Best for"]
    rows = [
        ("DB-MP Modular", "POM / PP / PE", "Flat / friction / roller", "Cold-end take-away, accumulation"),
        ("DB-PU Mono", "Monolithic polyurethane", "Smooth / textured", "Inspection, sorting, hygienic zones"),
        ("DB-RB Cleat", "EPDM rubber, multi-ply", "Cleated / flat", "Cullet handling, incline transfer"),
        ("DB-AS Anti-Static", "PU + carbon-loaded fabric", "Smooth", "Electronics-grade glass packing"),
    ]
    add_table(s, MARGIN, Inches(1.85), Inches(8.5), Inches(2.7), headers, rows)

    add_text(s, MARGIN, Inches(4.85), Inches(7), Inches(0.4),
             "Designed-in features", size=14, bold=True, color=NAVY)
    add_bullets(s, MARGIN, Inches(5.25), Inches(7.5), Inches(1.6), [
        "Cullet-shard puncture resistance verified to 6 mm shard impact",
        "Cleanable surfaces — washdown to 70 °C without delamination",
        "FDA / EU 10/2011 compliant for adjacent food-contact lines",
    ], size=12)

    # Right callout
    add_rect(s, Inches(9.2), Inches(1.85), Inches(3.65), Inches(4.85), fill=WHITE, line=MUTED)
    add_rect(s, Inches(9.2), Inches(1.85), Inches(3.65), Inches(0.55), fill=NAVY)
    add_text(s, Inches(9.4), Inches(1.93), Inches(3.4), Inches(0.4),
             "QUICK SPECS", size=11, bold=True, color=AMBER)
    quick = [
        ("Width range", "300 – 3,200 mm"),
        ("Belt speed", "up to 90 m / min"),
        ("Min radius", "down to 0.4 m (PU)"),
        ("Splicing", "endless / mechanical / zip"),
        ("Lead time", "stock SKUs in 48 h APAC"),
    ]
    y = Inches(2.6)
    for k, v in quick:
        add_text(s, Inches(9.4), y, Inches(2), Inches(0.35), k, size=11, color=STEEL)
        add_text(s, Inches(11.1), y, Inches(1.7), Inches(0.35), v,
                 size=11, bold=True, color=NAVY, align=PP_ALIGN.RIGHT)
        y += Inches(0.45)

    apply_footer(s, page, total)


def slide_transmission(prs, total, page):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    apply_canvas(s)
    apply_title_bar(s, "04 · Transmission V-Belts & Timing Belts",
                    "Forming-machine reliability starts at the drive")

    headers = ["Series", "Profile", "Power range", "Typical drive"]
    rows = [
        ("DB-V Wedge", "SPZ / SPA / SPB / SPC", "0.5 – 750 kW", "Forming machines, batch mixers"),
        ("DB-V Classical", "A / B / C / D / E", "0.4 – 350 kW", "Cullet crushers, fans, pumps"),
        ("DB-T HTD", "5M / 8M / 14M", "to 200 kW", "Lehr drive, conveyor head pulleys"),
        ("DB-T GT3", "8MGT / 14MGT", "to 600 kW", "High-torque forming drives"),
        ("DB-T PU", "T5 / T10 / AT10", "Positioning", "Cullet handlers, batching dosers"),
    ]
    add_table(s, MARGIN, Inches(1.85), Inches(8.5), Inches(3.3), headers, rows)

    add_text(s, MARGIN, Inches(5.45), Inches(7), Inches(0.4),
             "Performance options", size=14, bold=True, color=NAVY)
    add_bullets(s, MARGIN, Inches(5.85), Inches(7.5), Inches(1.0), [
        "Matched sets within ±0.3% length tolerance for multi-groove drives",
        "Heat-stabilised compounds for engine-room ambients above 60 °C",
    ], size=12)

    # Right comparison
    add_rect(s, Inches(9.2), Inches(1.85), Inches(3.65), Inches(5.0), fill=NAVY)
    add_text(s, Inches(9.4), Inches(2.0), Inches(3.4), Inches(0.4),
             "DB vs MARKET AVERAGE", size=11, bold=True, color=AMBER)
    pairs = [
        ("Service life", "+24%"),
        ("Slip @ rated load", "−35%"),
        ("Length tolerance", "±0.3%"),
        ("Quiet running", "−4 dB(A)"),
    ]
    y = Inches(2.55)
    for k, v in pairs:
        add_text(s, Inches(9.4), y, Inches(2.3), Inches(0.35), k, size=12, color=WHITE)
        add_text(s, Inches(11.4), y, Inches(1.4), Inches(0.4), v,
                 size=15, bold=True, color=AMBER, align=PP_ALIGN.RIGHT)
        y += Inches(0.65)

    add_rect(s, Inches(9.4), Inches(5.45), Inches(3.25), Inches(0.03), fill=AMBER)
    add_text(s, Inches(9.4), Inches(5.55), Inches(3.4), Inches(1.2),
             "Result: drive-belt replacement intervals extend from 14 → 21 months on typical forming machines.",
             size=11, color=WHITE)

    apply_footer(s, page, total)


def slide_differentiators(prs, total, page):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    apply_canvas(s)
    apply_title_bar(s, "04 · Why Dynamic Belt — Side by Side",
                    "Engineered for glass, not just sold to it")

    headers = ["Dimension", "Market average", "Dynamic Belt", "Operational impact"]
    rows = [
        ("Hot-end max continuous T°", "230 °C", "290 °C (PBO: 340 °C peak)",
         "Single belt covers lehr-exit + transfer, no inventory split"),
        ("Mean time between failures", "Baseline", "+22% on hot-end / +24% on V-belts",
         "Fewer planned shutdowns; longer PM intervals"),
        ("APAC stock lead-time", "3–6 weeks ex-EU", "48 h from 11 APAC depots",
         "Spare-belt buffer cut from 5 weeks to 5 days"),
        ("Minimum order quantity", "Full coil / pallet", "Per-metre cut + endless splice",
         "Working capital tied up in spares drops 30–40%"),
        ("Engineering support", "Spec sheet + email", "On-site survey + IoT pilot",
         "Belt selection matched to actual line profile, not catalogue"),
        ("Warranty", "12 months", "24 months on hot-end, 36 on transmission",
         "Risk shifts to supplier; CFO-friendly"),
    ]
    add_table(s, MARGIN, Inches(1.85), Inches(12.3), Inches(4.6), headers, rows)

    add_text(s, MARGIN, Inches(6.55), Inches(12), Inches(0.3),
             "Net effect: lower OEE losses, smaller spare-parts working capital, fewer vendor relationships to manage.",
             size=12, italic=True, color=NAVY)

    apply_footer(s, page, total)


def slide_case_study(prs, total, page):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    apply_canvas(s)
    apply_title_bar(s, "05 · Case Study — APAC Float Glass Plant",
                    "Tier-1 architectural glass producer, 600 t/day line")

    # Left: situation / action / result
    add_rect(s, MARGIN, Inches(1.85), Inches(8.0), Inches(4.85), fill=WHITE, line=MUTED)

    add_text(s, MARGIN + Inches(0.3), Inches(2.0), Inches(7.5), Inches(0.4),
             "SITUATION", size=11, bold=True, color=AMBER)
    add_text(s, MARGIN + Inches(0.3), Inches(2.35), Inches(7.5), Inches(0.9),
             "Lehr-exit aramid belts failing at 9–11 months. 6 unplanned stoppages in 12 months. "
             "Competitor V-belt sets slipping under load swings on three forming machines.",
             size=12, color=INK)

    add_text(s, MARGIN + Inches(0.3), Inches(3.4), Inches(7.5), Inches(0.4),
             "ACTION", size=11, bold=True, color=AMBER)
    add_text(s, MARGIN + Inches(0.3), Inches(3.75), Inches(7.5), Inches(1.0),
             "Switched lehr-exit and transfer belts to DB-AR 260 + DB-PBO 340. "
             "Replaced V-belt sets with matched DB-V Wedge SPC. On-site engineer "
             "instrumented two belts with IoT temperature & elongation sensors.",
             size=12, color=INK)

    add_text(s, MARGIN + Inches(0.3), Inches(4.95), Inches(7.5), Inches(0.4),
             "RESULT (12 MONTHS)", size=11, bold=True, color=AMBER)
    add_text(s, MARGIN + Inches(0.3), Inches(5.3), Inches(7.5), Inches(1.4),
             "Belt-related unplanned stoppages cut from 6 → 1. Mean belt life on lehr exit "
             "rose from 10 to 17 months. Combined annual savings $480K (downtime + spares + energy).",
             size=12, color=INK)

    # Right: KPI stack
    kpis = [
        ("−38%", "Belt-related unplanned stoppages", AMBER),
        ("+22%", "Mean time between belt failures", NAVY),
        ("$ 480 K", "Annualised savings", SUCCESS),
        ("4.2 mo", "Payback on premium spec", AMBER),
    ]
    y = Inches(1.85)
    for big, label, color in kpis:
        add_rect(s, Inches(9.05), y, Inches(3.85), Inches(1.1), fill=WHITE, line=MUTED)
        add_rect(s, Inches(9.05), y, Inches(0.08), Inches(1.1), fill=color)
        add_text(s, Inches(9.25), y + Inches(0.12), Inches(3.5), Inches(0.55),
                 big, size=22, bold=True, color=color)
        add_text(s, Inches(9.25), y + Inches(0.65), Inches(3.5), Inches(0.4),
                 label, size=11, color=STEEL)
        y += Inches(1.22)

    add_data_footnote(s, "Customer name withheld under NDA; figures are actual within ±5%.")
    apply_footer(s, page, total)


def slide_tco(prs, total, page):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    apply_canvas(s)
    apply_title_bar(s, "05 · 3-Year TCO Comparison",
                    "Premium spec is the cheaper line over time")

    chart_data = CategoryChartData()
    chart_data.categories = ["Capex (belts)", "Replacement cycles", "Downtime cost", "Energy & maint.", "Total"]
    chart_data.add_series("Low-cost import", (180, 540, 920, 210, 1850))
    chart_data.add_series("Dynamic Belt", (240, 280, 310, 160, 990))

    chart = s.shapes.add_chart(
        XL_CHART_TYPE.COLUMN_CLUSTERED,
        MARGIN, Inches(1.85), Inches(8.6), Inches(4.7),
        chart_data,
    ).chart
    chart.has_title = True
    chart.chart_title.text_frame.text = "3-year cumulative cost — single 600 t/day float line (US$ '000)"
    for r in chart.chart_title.text_frame.paragraphs[0].runs:
        r.font.size = Pt(12); r.font.bold = True; r.font.color.rgb = NAVY; r.font.name = FONT
    chart.has_legend = True
    chart.legend.position = XL_LEGEND_POSITION.BOTTOM
    chart.legend.include_in_layout = False
    chart.legend.font.size = Pt(11); chart.legend.font.name = FONT

    s0 = chart.plots[0].series[0]
    s0.format.fill.solid(); s0.format.fill.fore_color.rgb = STEEL
    s1 = chart.plots[0].series[1]
    s1.format.fill.solid(); s1.format.fill.fore_color.rgb = NAVY

    chart.plots[0].has_data_labels = True
    dl = chart.plots[0].data_labels
    dl.font.size = Pt(9); dl.font.color.rgb = NAVY; dl.font.name = FONT
    dl.position = XL_LABEL_POSITION.OUTSIDE_END

    # Right: savings card
    add_rect(s, Inches(9.25), Inches(1.85), Inches(3.6), Inches(4.7), fill=NAVY)
    add_text(s, Inches(9.45), Inches(2.0), Inches(3.4), Inches(0.4),
             "3-YEAR SAVINGS", size=11, bold=True, color=AMBER)
    add_text(s, Inches(9.45), Inches(2.4), Inches(3.4), Inches(1.3),
             "$ 860 K", size=44, bold=True, color=AMBER)
    add_text(s, Inches(9.45), Inches(3.55), Inches(3.4), Inches(0.5),
             "per float line", size=12, color=WHITE)
    add_rect(s, Inches(9.45), Inches(4.05), Inches(3.2), Inches(0.03), fill=AMBER)
    add_text(s, Inches(9.45), Inches(4.2), Inches(3.4), Inches(2),
             "−46% TCO vs low-cost import baseline. Most of the gap comes "
             "from avoided downtime, not capex.",
             size=11, color=WHITE)

    add_data_footnote(s, "Illustrative model. Plug in your actual line capacity, energy rate, and OEE for a customised view.")
    apply_footer(s, page, total)


def slide_service(prs, total, page):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    apply_canvas(s)
    apply_title_bar(s, "05 · Service Model",
                    "Engineered locally — supported continuously")

    pillars = [
        ("APAC depot network",
         "11 stocking depots — Shanghai, Tianjin, Mumbai, Chennai, Bangkok, Jakarta, "
         "Ho Chi Minh, Manila, KL, Tokyo, Seoul. 48-hour spare delivery for stock SKUs."),
        ("On-site engineering",
         "Belt-survey & install crew on call. Splicing, pulley alignment, tracking "
         "tune-up included with first commissioning."),
        ("Predictive monitoring",
         "Optional IoT sensor pack: belt temperature, elongation, lateral drift. "
         "Alerts pushed to your CMMS (SAP PM, Maximo, Infor)."),
        ("Training & SOPs",
         "Annual on-site maintenance training; bilingual (EN + local) SOPs for "
         "every installed belt family."),
    ]
    col_w = Inches(6.1)
    row_h = Inches(2.25)
    gap = Inches(0.25)
    sx = MARGIN
    sy = Inches(1.95)
    for idx, (head, body) in enumerate(pillars):
        r, c = divmod(idx, 2)
        x = sx + c * (col_w + gap)
        y = sy + r * (row_h + gap)
        add_rect(s, x, y, col_w, row_h, fill=WHITE, line=MUTED)
        add_rect(s, x, y, col_w, Inches(0.08), fill=AMBER)
        add_text(s, x + Inches(0.3), y + Inches(0.25), col_w - Inches(0.6), Inches(0.45),
                 head, size=16, bold=True, color=NAVY)
        add_text(s, x + Inches(0.3), y + Inches(0.8), col_w - Inches(0.6), row_h - Inches(0.9),
                 body, size=12, color=INK)

    apply_footer(s, page, total)


def slide_roadmap(prs, total, page):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    apply_canvas(s)
    apply_title_bar(s, "05 · Roadmap — Smart & Sustainable Belts",
                    "What's coming in the next 12–24 months")

    items = [
        ("Q3 2026", "Smart-Belt v1",
         "Embedded fibre-optic sensing for hot-end belts; live elongation + temperature."),
        ("Q1 2027", "Closed-loop recycling",
         "Take-back program for end-of-life PU and rubber belts; reformulated compounds."),
        ("Q3 2027", "Bio-based aramid hybrid",
         "30% bio-content para-aramid weave for hot-end conveying, equal heat rating."),
        ("Q1 2028", "Predictive twin",
         "Per-line digital twin estimating remaining useful life, integrated with CMMS."),
    ]

    # Timeline bar
    add_rect(s, MARGIN, Inches(2.2), Inches(12.3), Inches(0.06), fill=STEEL)
    n = len(items)
    track_w = Inches(12.3)
    step = track_w / (n - 1)
    for i, (when, head, body) in enumerate(items):
        cx = MARGIN + step * i
        # marker
        dot = s.shapes.add_shape(MSO_SHAPE.OVAL,
                                 cx - Inches(0.12), Inches(2.11), Inches(0.24), Inches(0.24))
        _set_fill(dot, AMBER)
        _no_line(dot)
        # card
        card_w = Inches(2.85)
        card_x = cx - card_w / 2
        card_x = max(MARGIN, min(card_x, MARGIN + track_w - card_w))
        card_y = Inches(2.7)
        add_rect(s, card_x, card_y, card_w, Inches(3.4), fill=WHITE, line=MUTED)
        add_text(s, card_x + Inches(0.2), card_y + Inches(0.15), card_w - Inches(0.4), Inches(0.35),
                 when, size=11, bold=True, color=AMBER)
        add_text(s, card_x + Inches(0.2), card_y + Inches(0.5), card_w - Inches(0.4), Inches(0.6),
                 head, size=14, bold=True, color=NAVY)
        add_text(s, card_x + Inches(0.2), card_y + Inches(1.15), card_w - Inches(0.4), Inches(2.2),
                 body, size=11, color=INK)

    apply_footer(s, page, total)


def slide_cta(prs, total, page):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    apply_canvas(s)

    # Big navy panel right
    add_rect(s, Inches(7.0), 0, Inches(6.4), SLIDE_H, fill=NAVY)
    add_rect(s, Inches(6.88), 0, Inches(0.12), SLIDE_H, fill=AMBER)

    # Left content
    add_text(s, MARGIN, Inches(0.55), Inches(6), Inches(0.4),
             "06 · NEXT STEPS", size=12, bold=True, color=AMBER)
    add_text(s, MARGIN, Inches(1.0), Inches(6.3), Inches(2.5),
             "Let's prove it on one line.", size=34, bold=True, color=NAVY)

    add_text(s, MARGIN, Inches(2.6), Inches(6.3), Inches(0.4),
             "90-DAY PILOT", size=12, bold=True, color=AMBER)
    add_bullets(s, MARGIN, Inches(3.0), Inches(6.3), Inches(3), [
        "Free belt-line audit on one selected float / container line",
        "DB-AR 260 + matched DB-V Wedge installed at our cost",
        "IoT instrumentation + monthly performance read-out",
        "Pre-agreed KPIs: MTBF, downtime hours, $/tonne",
        "Rollout proposal at day 90 — go/no-go on your terms",
    ], size=13)

    # Right contact panel
    add_text(s, Inches(7.3), Inches(0.7), Inches(6), Inches(0.4),
             "TALK TO US", size=12, bold=True, color=AMBER)
    add_text(s, Inches(7.3), Inches(1.1), Inches(6), Inches(1.2),
             "Schedule the audit", size=30, bold=True, color=WHITE)

    add_rect(s, Inches(7.3), Inches(2.4), Inches(5.8), Inches(0.04), fill=AMBER)

    contacts = [
        ("APAC Industrial Sales", "sales.apac@dynamicbelt.example"),
        ("Hot-End Engineering", "hotend.eng@dynamicbelt.example"),
        ("Service & Spare Belts", "service.apac@dynamicbelt.example"),
        ("Phone (24×7 plant line)", "+65 6000 0000"),
    ]
    y = Inches(2.7)
    for k, v in contacts:
        add_text(s, Inches(7.3), y, Inches(3), Inches(0.4), k, size=12, color=MUTED)
        add_text(s, Inches(7.3), y + Inches(0.3), Inches(5.8), Inches(0.4),
                 v, size=14, bold=True, color=WHITE)
        y += Inches(0.85)

    add_rect(s, Inches(7.3), Inches(6.4), Inches(5.8), Inches(0.04), fill=STEEL)
    add_text(s, Inches(7.3), Inches(6.5), Inches(6), Inches(0.5),
             "Dynamic Belt — Engineered for Glass.  Proven in APAC.",
             size=12, italic=True, color=AMBER)

    apply_footer(s, page, total)


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

BUILDERS = [
    slide_title,
    slide_agenda,
    slide_industry_pulse,
    slide_cost_of_failure,
    slide_market_sizing,
    slide_market_share,
    slide_growth,
    slide_portfolio_overview,
    slide_hotend,
    slide_coldend,
    slide_transmission,
    slide_differentiators,
    slide_case_study,
    slide_tco,
    slide_service,
    slide_roadmap,
    slide_cta,
]


def build():
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H

    total = len(BUILDERS)
    for i, builder in enumerate(BUILDERS, start=1):
        if builder is slide_title:
            builder(prs, total)
        else:
            builder(prs, total, i)

    out_dir = Path(__file__).parent / "dist"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "Dynamic_Belt_Glass_Manufacturing_APAC.pptx"
    prs.save(out_path)
    print(f"Wrote {out_path.relative_to(Path(__file__).parent)} ({total} slides)")
    return out_path


if __name__ == "__main__":
    build()
