import requests
import urllib.parse
import re
from fpdf import FPDF
from fpdf.enums import XPos, YPos
import os
import io
import tempfile
from datetime import datetime
import getpass
from collections import Counter

# Matplotlib for professional charts
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("WARNING: matplotlib not available. Charts will be skipped.")

# =========================
# Global Variables
# =========================
PROJECT_KEY  = ""
COMPANY_NAME = ""
CLIENT_NAME  = ""
PROJECT_NAME = ""
ASSET_TYPE   = ""
REPORT_DATE  = ""   # set once at start of main()

# =========================
# Resolution / Severity label maps
# =========================
RESOLUTION_LABELS = {
    'SAFE':         'False Positive',
    'FIXED':        'Fixed',
    'ACKNOWLEDGED': 'Valid',
}

# Human-readable severity labels kept consistent throughout
SEVERITY_LABEL = {
    'HIGH':   'High',
    'MEDIUM': 'Medium',
    'LOW':    'Low',
}

RESOLUTION_DEFINITIONS = {
    'False Positive': (
        "The code has been reviewed and determined not to pose a security risk. "
        "No modification or remediation is required. The identified finding was "
        "a false alarm and does not require any corrective action."
    ),
    'Fixed': (
        "A remediation has been applied to the identified vulnerability. The code "
        "has been modified to eliminate the security risk, and the fix has been "
        "verified by the reviewing team."
    ),
    'Valid': (
        "The code has been reviewed and confirmed to pose a genuine security risk. "
        "This finding requires remediation. A fix must be planned, prioritised, "
        "and implemented by the development team before the next release."
    ),
}

def resolution_display(raw):
    return RESOLUTION_LABELS.get(raw, raw)

def severity_display(raw):
    return SEVERITY_LABEL.get(str(raw).upper(), raw)


# =========================
# Colour palette
# =========================
C_PRIMARY  = (21,  101, 192)
C_ACCENT   = (30,  136, 229)
C_DARK     = (33,  33,  33)
C_MID      = (96,  125, 139)
C_LIGHT_BG = (245, 248, 252)
C_WHITE    = (255, 255, 255)
C_RED      = (198, 40,  40)
C_ORANGE   = (230, 120,  0)
C_GREEN    = (46,  125,  50)
C_GREY     = (120, 120, 120)


# =========================
# Chart helpers
# =========================

def _save_png_tmp(png_bytes):
    if not png_bytes:
        return None
    fd, path = tempfile.mkstemp(suffix='.png')
    with os.fdopen(fd, 'wb') as f:
        f.write(png_bytes)
    return path


def make_severity_pie(severity_counts):
    """Pie chart sized to fit 87mm column. Returns PNG bytes."""
    if not MATPLOTLIB_AVAILABLE:
        return None

    order  = ['HIGH', 'MEDIUM', 'LOW']
    colors = ['#C62828', '#E67800', '#2E7D32']
    labels_out = []
    sizes  = []
    cols   = []

    for s, c in zip(order, colors):
        v = severity_counts.get(s, 0)
        if v > 0:
            labels_out.append(s.capitalize())
            sizes.append(v)
            cols.append(c)

    if not sizes:
        return None

    total = sum(sizes)

    # 3.4 x 3.4 inch => at 150dpi = 510x510px; at 87mm in PDF => near square
    fig, ax = plt.subplots(figsize=(3.4, 3.4), dpi=150, facecolor='white')
    fig.subplots_adjust(left=0.05, right=0.95, top=0.88, bottom=0.20)

    def autopct_fmt(pct):
        count = int(round(pct * total / 100))
        return f'{pct:.1f}%\n({count})'

    wedges, texts, autotexts = ax.pie(
        sizes,
        colors=cols,
        autopct=autopct_fmt,
        startangle=90,
        pctdistance=0.65,
        wedgeprops=dict(edgecolor='white', linewidth=2),
    )
    for at in autotexts:
        at.set_fontsize(8)
        at.set_color('white')
        at.set_fontweight('bold')
    for t in texts:
        t.set_text('')

    patches = [mpatches.Patch(facecolor=cols[i],
                              label=f'{labels_out[i]}  ({sizes[i]})',
                              edgecolor='white')
               for i in range(len(labels_out))]
    ax.legend(handles=patches, loc='lower center',
              bbox_to_anchor=(0.5, -0.20), ncol=len(labels_out),
              fontsize=8, frameon=False, handlelength=1.2)

    ax.set_title('Severity Distribution', fontsize=10, fontweight='bold',
                 color='#1a1a1a', pad=8)

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, facecolor='white',
                bbox_inches='tight', pad_inches=0.12)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def make_findings_bar(severity_counts, status_counts, resolution_counts_raw):
    """
    Vertical bar chart sized to fit 87mm column.
    Groups: Severity | Review Status | Resolution. Returns PNG bytes.
    """
    if not MATPLOTLIB_AVAILABLE:
        return None

    total      = sum(severity_counts.values())
    high       = severity_counts.get('HIGH',   0)
    medium     = severity_counts.get('MEDIUM', 0)
    low        = severity_counts.get('LOW',    0)
    to_review  = status_counts.get('TO_REVIEW', 0)
    reviewed   = status_counts.get('REVIEWED',  0)
    fixed      = resolution_counts_raw.get('FIXED', 0)
    false_pos  = resolution_counts_raw.get('SAFE',  0)
    valid      = resolution_counts_raw.get('ACKNOWLEDGED', 0)

    show_res = (fixed + false_pos + valid) > 0

    if show_res:
        labels = ['Total', 'High', 'Medium', 'Low',
                  'To\nReview', 'Reviewed', 'Fixed', 'False\nPos.', 'Valid']
        values = [total, high, medium, low,
                  to_review, reviewed, fixed, false_pos, valid]
        colors = ['#1565C0', '#C62828', '#E67800', '#2E7D32',
                  '#B71C1C', '#1565C0', '#1565C0', '#2E7D32', '#E67800']
        separators = [3.5, 5.5]
    else:
        labels = ['Total', 'High', 'Medium', 'Low', 'To\nReview', 'Reviewed']
        values = [total, high, medium, low, to_review, reviewed]
        colors = ['#1565C0', '#C62828', '#E67800', '#2E7D32', '#B71C1C', '#1565C0']
        separators = [3.5]

    # 3.4 wide x 3.0 tall => fits 87mm column, near same height as pie
    fig, ax = plt.subplots(figsize=(3.4, 3.0), dpi=150, facecolor='white')
    fig.subplots_adjust(left=0.04, right=0.98, top=0.84, bottom=0.24)

    x = range(len(labels))
    bars = ax.bar(x, values, color=colors, edgecolor='white',
                  linewidth=1.2, width=0.6)

    max_v = max(values) if any(v > 0 for v in values) else 1
    ax.set_ylim(0, max_v * 1.38)

    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max_v * 0.03,
                str(val),
                ha='center', va='bottom',
                fontsize=8, fontweight='bold', color='#1a1a1a')

    for sx in separators:
        ax.axvline(x=sx, color='#cccccc', linewidth=1, linestyle='--')

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=7.5)
    ax.tick_params(axis='x', length=0, pad=3)
    ax.spines[['top', 'right', 'left']].set_visible(False)
    ax.spines['bottom'].set_color('#cccccc')
    ax.yaxis.set_visible(False)
    ax.set_facecolor('white')
    ax.set_title('Findings Overview', fontsize=10, fontweight='bold',
                 color='#1a1a1a', pad=8)

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, facecolor='white',
                bbox_inches='tight', pad_inches=0.1)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# =========================
# PDF Class
# =========================

class SonarQubePDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_left_margin(15)
        self.set_right_margin(15)

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------
    def header(self):
        if self.page_no() <= 1:
            return

        # Top accent bar
        self.set_fill_color(*C_PRIMARY)
        self.rect(0, 0, 210, 3, 'F')

        script_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path  = os.path.join(script_dir, "logo.png")
        if os.path.exists(logo_path):
            self.image(logo_path, x=10, y=5, w=28)
            self.set_xy(42, 4)
        else:
            self.set_xy(15, 4)

        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(*C_PRIMARY)
        self.cell(0, 6, f'{COMPANY_NAME}  |  SOURCE CODE SECURITY REVIEW REPORT',
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')

        self.set_x(42 if os.path.exists(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.png")) else 15)
        self.set_font('Helvetica', '', 7)
        self.set_text_color(*C_MID)
        self.cell(0, 4,
                  f'Project: {PROJECT_KEY}   |   Client: {CLIENT_NAME}   |   '
                  f'Date: {REPORT_DATE}',
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')

        self.set_draw_color(*C_ACCENT)
        self.set_line_width(0.4)
        self.line(10, self.get_y() + 1, 200, self.get_y() + 1)
        self.ln(5)

    # ------------------------------------------------------------------
    # Footer
    # ------------------------------------------------------------------
    def footer(self):
        self.set_y(-13)
        self.set_draw_color(*C_PRIMARY)
        self.set_line_width(0.3)
        self.line(10, self.get_y() - 1, 200, self.get_y() - 1)

        self.set_font('Helvetica', 'I', 7)
        self.set_text_color(*C_MID)
        self.set_x(15)
        self.cell(90, 5, 'CONFIDENTIAL', align='L',
                  new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.cell(0, 5, f'Page {self.page_no()}', align='R',
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    def safe_text(self, text):
        if not text:
            return ""
        text = str(text)
        replacements = {
            '\u2022': '-',  '\u2014': '-',  '\u2013': '-',
            '\u2018': "'",  '\u2019': "'",
            '\u201c': '"',  '\u201d': '"',
            '\u2026': '...', '\u00a9': '(c)', '\u00ae': '(R)',
            '\u2122': '(TM)', '\u00b0': ' deg', '\u00b1': '+/-',
            '\u00d7': 'x',  '\u00f7': '/',  '\u2713': 'OK',
            '\u2717': 'NO', '\u2192': '->',  '\u2190': '<-',
            '\u2191': '^',  '\u2193': 'v',
        }
        for uc, ac in replacements.items():
            text = text.replace(uc, ac)
        return text.encode('ascii', 'ignore').decode('ascii')

    def safe_multi_cell(self, w, h, txt, border=0, align='L', fill=False):
        self.set_x(self.l_margin)
        self.multi_cell(w, h, txt, border=border, align=align, fill=fill,
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def section_title(self, text, size=16):
        self.set_font('Helvetica', 'B', size)
        self.set_text_color(*C_PRIMARY)
        self.set_x(self.l_margin)
        self.cell(0, 10, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        self.set_draw_color(*C_ACCENT)
        self.set_line_width(0.7)
        self.line(self.l_margin, self.get_y(),
                  self.l_margin + 90, self.get_y())
        self.set_line_width(0.2)
        self.ln(5)

    def sub_section_title(self, text):
        self.set_font('Helvetica', 'B', 11)
        self.set_text_color(*C_PRIMARY)
        self.set_x(self.l_margin)
        self.cell(0, 7, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        self.ln(2)

    def kv_row(self, key, value, key_w=42, row_h=6.5):
        """Grey label | dark value, thin bottom border."""
        self.set_x(self.l_margin)
        self.set_font('Helvetica', 'B', 9)
        self.set_fill_color(*C_LIGHT_BG)
        self.set_text_color(*C_MID)
        self.cell(key_w, row_h, key, border='B', fill=True,
                  new_x=XPos.RIGHT, new_y=YPos.TOP, align='L')
        self.set_font('Helvetica', '', 9)
        self.set_text_color(*C_DARK)
        self.set_fill_color(*C_WHITE)
        self.cell(0, row_h, self.safe_text(str(value)), border='B', fill=True,
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')

    def status_pill(self, label_text, value_text, pill_r, pill_g, pill_b,
                    key_w=42, row_h=7):
        """
        Render a metadata row where the value is a plain-text coloured word
        (no filled background box) - professional, clean look.
        """
        self.set_x(self.l_margin)
        self.set_font('Helvetica', 'B', 9)
        self.set_fill_color(*C_LIGHT_BG)
        self.set_text_color(*C_MID)
        self.cell(key_w, row_h, label_text, border='B', fill=True,
                  new_x=XPos.RIGHT, new_y=YPos.TOP, align='L')
        self.set_font('Helvetica', 'B', 9)
        self.set_text_color(pill_r, pill_g, pill_b)
        self.set_fill_color(*C_WHITE)
        self.cell(0, row_h, value_text, border='B', fill=True,
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        self.set_text_color(*C_DARK)

    # ------------------------------------------------------------------
    # Title Page
    # ------------------------------------------------------------------
    def title_page(self):
        self.add_page()

        # Header band
        self.set_fill_color(*C_PRIMARY)
        self.rect(0, 0, 210, 62, 'F')

        script_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path  = os.path.join(script_dir, "logo.png")
        if os.path.exists(logo_path):
            self.image(logo_path, x=15, y=10, w=40)

        self.set_xy(15, 24)
        self.set_font('Helvetica', 'B', 22)
        self.set_text_color(*C_WHITE)
        self.cell(0, 10, self.safe_text(COMPANY_NAME),
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')

        self.set_xy(15, 38)
        self.set_font('Helvetica', '', 12)
        self.set_text_color(179, 212, 255)
        self.cell(0, 6, 'Source Code Security Review Report',
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')

        # Report Details section
        self.set_y(78)
        self.set_font('Helvetica', 'B', 16)
        self.set_text_color(*C_PRIMARY)
        self.set_x(self.l_margin)
        self.cell(0, 9, 'Report Details',
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        self.set_draw_color(*C_ACCENT)
        self.set_line_width(0.7)
        self.line(self.l_margin, self.get_y(),
                  self.l_margin + 60, self.get_y())
        self.ln(6)

        info_rows = [
            ('Client Name',    CLIENT_NAME),
            ('Project Name',   PROJECT_NAME),
            ('Asset Type',     ASSET_TYPE),
            ('Project',        PROJECT_KEY),
            ('Report Date',    REPORT_DATE),
        ]
        for label, val in info_rows:
            self.set_x(self.l_margin)
            self.set_font('Helvetica', 'B', 10)
            self.set_text_color(*C_MID)
            self.cell(48, 8, label + ':', new_x=XPos.RIGHT, new_y=YPos.TOP, align='L')
            self.set_font('Helvetica', '', 10)
            self.set_text_color(*C_DARK)
            self.cell(0, 8, self.safe_text(val),
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')

        # Confidential stamp at bottom
        self.set_y(-38)
        self.set_draw_color(*C_MID)
        self.set_line_width(0.3)
        self.set_dash_pattern(dash=3, gap=2)
        self.rect(self.l_margin, self.get_y(), 180, 9)
        self.set_dash_pattern()
        self.set_font('Helvetica', 'I', 9)
        self.set_text_color(*C_MID)
        self.set_x(self.l_margin)
        self.cell(0, 9, 'CONFIDENTIAL - FOR AUTHORISED RECIPIENTS ONLY',
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')

    # ------------------------------------------------------------------
    # Executive Summary
    # ------------------------------------------------------------------
    def executive_summary(self, hotspots_data, sev_png, bar_png):
        # -- PAGE 1: Title + Intro + Metric Cards ----------------------
        self.add_page()
        self.section_title('EXECUTIVE SUMMARY', size=18)

        self.set_font('Helvetica', '', 10)
        self.set_text_color(*C_DARK)
        intro = (
            f"This report presents the findings of the source code security review "
            f"conducted by {COMPANY_NAME} for {CLIENT_NAME}. The assessment focused on "
            f"identifying security hotspots and potential vulnerabilities within the "
            f"{PROJECT_NAME} project ({ASSET_TYPE})."
        )
        self.safe_multi_cell(0, 5.5, self.safe_text(intro))
        self.ln(8)

        # Compute all stats once
        total = len(hotspots_data)
        severity_counts   = Counter()
        status_counts     = Counter()
        resolution_counts = Counter()
        for d in hotspots_data:
            severity_counts[d.get('vulnerability_probability', 'UNKNOWN')] += 1
            status_counts[d.get('status', 'UNKNOWN')] += 1
            res = d.get('resolution', 'NONE')
            if res != 'NONE':
                resolution_counts[res] += 1

        high      = severity_counts.get('HIGH',   0)
        medium    = severity_counts.get('MEDIUM', 0)
        low       = severity_counts.get('LOW',    0)
        reviewed  = status_counts.get('REVIEWED',  0)
        to_review = status_counts.get('TO_REVIEW', 0)
        fixed     = resolution_counts.get('FIXED', 0)
        false_pos = resolution_counts.get('SAFE',  0)
        valid     = resolution_counts.get('ACKNOWLEDGED', 0)

        # Layout constants
        # Two columns, each 87mm wide, 6mm gap
        COL_W  = 87
        GAP    = 6
        x_left  = self.l_margin       # 15
        x_right = x_left + COL_W + GAP  # 108

        # -- TABLE helper ---------------------------------------------
        def draw_table(x, title, headers, rows, col_widths):
            """Draw a titled table at absolute x, returning bottom y."""
            y = self.get_y()
            # Table title
            self.set_xy(x, y)
            self.set_font('Helvetica', 'B', 10)
            self.set_text_color(*C_PRIMARY)
            self.cell(COL_W, 7, title, align='L',
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.set_xy(x, self.get_y())
            # Header row
            self.set_font('Helvetica', 'B', 8)
            self.set_fill_color(*C_PRIMARY)
            self.set_text_color(*C_WHITE)
            cx = x
            for h, w in zip(headers, col_widths):
                self.set_xy(cx, self.get_y())
                self.cell(w, 7, h, border=0, fill=True, align='C',
                          new_x=XPos.RIGHT, new_y=YPos.TOP)
                cx += w
            self.set_xy(x, self.get_y() + 7)
            # Data rows
            for idx, (cells, color) in enumerate(rows):
                bg = C_LIGHT_BG if idx % 2 == 0 else C_WHITE
                self.set_fill_color(*bg)
                cx = x
                row_y2 = self.get_y()
                for ci, (cell_txt, cw) in enumerate(zip(cells, col_widths)):
                    self.set_xy(cx, row_y2)
                    if ci == 0:
                        self.set_font('Helvetica', '', 8)
                        self.set_text_color(*C_DARK)
                    else:
                        self.set_font('Helvetica', 'B', 8)
                        self.set_text_color(*color)
                    self.cell(cw, 6.5, str(cell_txt), border=0, fill=True,
                              align='C', new_x=XPos.RIGHT, new_y=YPos.TOP)
                    cx += cw
                self.set_xy(x, row_y2 + 6.5)
            return self.get_y()

        # -- CHART embed helper ----------------------------------------
        def embed_chart_at(png_bytes, x, y, w, caption):
            """Place a chart image at absolute (x,y), return bottom y."""
            if not png_bytes:
                return y
            tmp = _save_png_tmp(png_bytes)
            if not tmp:
                return y
            try:
                self.image(tmp, x=x, y=y, w=w)
                # Estimate height from aspect ratio stored in png
                # Pie is 4x4 => ratio 1.0; Bar is 7x4 => ratio 1.75
                # We'll read actual size via a quick PIL check if available
                try:
                    import struct, zlib
                    # Read PNG IHDR for width/height
                    with open(tmp, 'rb') as f2:
                        f2.read(8)   # PNG signature
                        f2.read(4)   # chunk length
                        f2.read(4)   # 'IHDR'
                        pw = struct.unpack('>I', f2.read(4))[0]
                        ph = struct.unpack('>I', f2.read(4))[0]
                    aspect = ph / pw
                except Exception:
                    aspect = 1.0
                img_h_mm = w * aspect
                cap_y = y + img_h_mm + 1
                self.set_xy(x, cap_y)
                self.set_font('Helvetica', 'I', 7)
                self.set_text_color(*C_MID)
                self.cell(w, 4, caption, align='C',
                          new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                return cap_y + 5
            finally:
                os.unlink(tmp)

        # -- LEFT COLUMN: Severity Distribution -----------------------
        sev_table_rows = [
            (['High',   str(high)],   C_RED),
            (['Medium', str(medium)], C_ORANGE),
            (['Low',    str(low)],    C_GREEN),
            (['Total',  str(total)],  C_ACCENT),
        ]
        section_top = self.get_y()

        bottom_sev_table = draw_table(
            x_left, 'Severity Distribution',
            ['Severity', 'Count'],
            sev_table_rows,
            [55, 32]
        )

        self.set_y(bottom_sev_table + 3)
        left_chart_y = self.get_y()
        bottom_sev_chart = embed_chart_at(
            sev_png, x_left, left_chart_y, COL_W,
            'Figure 1 - Severity Distribution'
        )

        # -- RIGHT COLUMN: Findings Overview --------------------------
        findings_rows = [
            (['Total Findings',  str(total)],     C_ACCENT),
            (['To Review',       str(to_review)], C_RED),
            (['Reviewed',        str(reviewed)],  C_GREEN),
            (['Fixed',           str(fixed)],     C_ACCENT),
            (['False Positive',  str(false_pos)], C_GREEN),
            (['Valid',           str(valid)],     C_ORANGE),
        ]

        # Position right column at same top as left
        self.set_y(section_top)
        bottom_findings_table = draw_table(
            x_right, 'Findings Overview',
            ['Category', 'Count'],
            findings_rows,
            [55, 32]
        )

        self.set_y(bottom_findings_table + 3)
        right_chart_y = self.get_y()
        bottom_findings_chart = embed_chart_at(
            bar_png, x_right, right_chart_y, COL_W,
            'Figure 2 - Findings Overview'
        )

        # Advance below both columns (whichever is lower)
        self.set_y(max(bottom_sev_chart, bottom_findings_chart) + 6)
        self.set_text_color(*C_DARK)

        # -- METHODOLOGY -----------------------------------------------
        self.sub_section_title('Assessment Methodology')
        self.set_font('Helvetica', '', 10)
        self.set_text_color(*C_DARK)

        methodology_intro = (
            "The source code security review was conducted using a combination of "
            "industry-recognised frameworks, standards, and best practices. The "
            "following methodologies were applied during this assessment:"
        )
        self.safe_multi_cell(0, 5.5, self.safe_text(methodology_intro))
        self.ln(5)

        methodologies = [
            (
                "OWASP Top 10",
                "The Open Web Application Security Project (OWASP) Top 10 is a "
                "standard awareness document representing the most critical security "
                "risks to web applications. Findings were cross-referenced against "
                "categories including Injection, Broken Authentication, Security "
                "Misconfiguration, Cryptographic Failures, and Insecure Design, among others."
            ),
            (
                "OWASP Application Security Verification Standard (ASVS)",
                "The ASVS provides a basis for testing technical "
                "security controls. It defines three levels of security verification "
                "depth, and was used as a reference checklist during the code review "
                "to verify security requirements across authentication, session management, "
                "access control, cryptography, and error handling."
            ),
            (
                "NIST SP 800-64 - Security Considerations in the SDLC",
                "NIST 800-64 outlines security activities that should be integrated "
                "throughout the Software Development Life Cycle (SDLC). This assessment "
                "evaluated the extent to which secure coding practices have been embedded "
                "within the development process, including secure design, code analysis, "
                "and verification phases."
            ),
            (
                "Static Application Security Testing (SAST)",
                "Automated static analysis was performed across the full source code "
                "base to identify security hotspots, insecure coding patterns, and "
                "potential vulnerabilities without executing the application. Results "
                "were subsequently reviewed and validated manually to reduce false "
                "positives and confirm the severity of each finding."
            ),
            (
                "Manual Code Review",
                "A targeted manual review was conducted on high-risk components and "
                "areas flagged by automated analysis. This included examination of "
                "authentication and authorisation logic, cryptographic implementations, "
                "input validation routines, error handling, and third-party dependency "
                "usage, complementing the automated findings with expert judgement."
            ),
        ]

        for i, (title, body) in enumerate(methodologies):
            item_y = self.get_y()
            # Number bubble
            self.set_fill_color(*C_PRIMARY)
            self.rect(self.l_margin, item_y, 6, 6, 'F')
            self.set_xy(self.l_margin, item_y)
            self.set_font('Helvetica', 'B', 7)
            self.set_text_color(*C_WHITE)
            self.cell(6, 6, str(i + 1), align='C',
                      new_x=XPos.RIGHT, new_y=YPos.TOP)
            # Title
            self.set_font('Helvetica', 'B', 9)
            self.set_text_color(*C_PRIMARY)
            self.cell(0, 6, self.safe_text(title),
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
            # Body
            self.set_x(self.l_margin + 6)
            self.set_font('Helvetica', '', 9)
            self.set_text_color(*C_DARK)
            self.multi_cell(174, 5, self.safe_text(body),
                            new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.ln(4)

        self.ln(2)

        # -- KEY RECOMMENDATIONS ---------------------------------------
        self.sub_section_title('Key Recommendations')
        self.set_font('Helvetica', '', 10)
        recs = []
        if high > 0:
            recs.append(f"Prioritise immediate remediation of {high} High severity finding(s).")
        if to_review > 0:
            recs.append(f"Complete the review of {to_review} outstanding finding(s) currently pending assessment.")
        if medium > 0:
            recs.append(f"Address {medium} Medium severity finding(s) within the next development cycle.")
        recs.append("Provide targeted security training for developers based on the identified vulnerability categories.")
        recs.append("Incorporate periodic security code reviews as a mandatory step within the Software Development Life Cycle (SDLC).")

        for rec in recs:
            self.set_x(self.l_margin)
            self.set_fill_color(*C_ACCENT)
            self.rect(self.l_margin, self.get_y() + 1.5, 2, 4, 'F')
            self.set_x(self.l_margin + 5)
            self.set_text_color(*C_DARK)
            self.multi_cell(0, 5.5, self.safe_text(rec),
                            new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.ln(1.5)

    # ------------------------------------------------------------------
    # Resolution Definitions Page
    # ------------------------------------------------------------------
    def resolution_definitions_page(self):
        self.section_title('REVIEW STATUS DEFINITIONS', size=16)

        self.set_font('Helvetica', '', 10)
        self.set_text_color(*C_DARK)
        self.safe_multi_cell(
            0, 5.5,
            "The table below defines each review status applied to findings "
            "identified during this security assessment."
        )
        self.ln(8)

        defs = [
            ('False Positive', C_GREEN,  RESOLUTION_DEFINITIONS['False Positive']),
            ('Fixed',          C_ACCENT, RESOLUTION_DEFINITIONS['Fixed']),
            ('Valid',          C_ORANGE, RESOLUTION_DEFINITIONS['Valid']),
        ]

        for title, col, body in defs:
            bar_y = self.get_y()
            # Left colour bar
            self.set_fill_color(*col)
            self.rect(self.l_margin, bar_y, 3, 24, 'F')
            # Card bg - very light tint
            bg = (min(col[0]+215,255), min(col[1]+215,255), min(col[2]+215,255))
            self.set_fill_color(*bg)
            self.rect(self.l_margin + 3, bar_y, 177, 24, 'F')
            # Title
            self.set_xy(self.l_margin + 7, bar_y + 3)
            self.set_font('Helvetica', 'B', 11)
            self.set_text_color(*col)
            self.cell(0, 6, title,
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
            # Body
            self.set_x(self.l_margin + 7)
            self.set_font('Helvetica', '', 9)
            self.set_text_color(*C_DARK)
            self.multi_cell(173, 5, self.safe_text(body),
                            new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.ln(7)

    # ------------------------------------------------------------------
    # Summary Table
    # ------------------------------------------------------------------
    def summary_table(self, hotspots_data):
        self.add_page()
        self.section_title('VULNERABILITY SUMMARY', size=16)

        total = len(hotspots_data)
        severity_counts   = Counter()
        category_counts   = Counter()
        status_counts     = Counter()
        resolution_counts = Counter()

        for d in hotspots_data:
            severity_counts[d.get('vulnerability_probability', 'UNKNOWN')] += 1
            category_counts[d.get('security_category', 'Unknown')] += 1
            status_counts[d.get('status', 'UNKNOWN')] += 1
            res = d.get('resolution', 'NONE')
            if res != 'NONE':
                resolution_counts[res] += 1

        reviewed = status_counts.get('REVIEWED',  0)
        unreview = status_counts.get('TO_REVIEW', 0)

        def tbl_header(col1, col2, w1=100, w2=80):
            self.set_x(self.l_margin)
            self.set_font('Helvetica', 'B', 9)
            self.set_fill_color(*C_PRIMARY)
            self.set_text_color(*C_WHITE)
            self.cell(w1, 8, col1, border=0, fill=True,
                      new_x=XPos.RIGHT, new_y=YPos.TOP, align='L')
            self.cell(w2, 8, col2, border=0, fill=True,
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
            self.set_text_color(*C_DARK)

        def tbl_row(col1, col2, w1=100, w2=80, col1_color=None, even=True):
            self.set_x(self.l_margin)
            self.set_font('Helvetica', '', 9)
            bg = C_LIGHT_BG if even else C_WHITE
            self.set_fill_color(*bg)
            self.set_text_color(*(col1_color if col1_color else C_DARK))
            self.cell(w1, 7, self.safe_text(str(col1)), border=0, fill=True,
                      new_x=XPos.RIGHT, new_y=YPos.TOP, align='L')
            self.set_text_color(*C_DARK)
            self.cell(w2, 7, str(col2), border=0, fill=True,
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')

        # Review Status
        self.sub_section_title('Review Status')
        tbl_header('Status', 'Count')
        r_pct = f"{reviewed / total * 100:.1f}%" if total else "0%"
        u_pct = f"{unreview / total * 100:.1f}%" if total else "0%"
        tbl_row(f'Reviewed ({r_pct})',  reviewed, col1_color=C_GREEN, even=True)
        tbl_row(f'To Review ({u_pct})', unreview, col1_color=C_RED,   even=False)
        self.ln(8)

        # Resolution Breakdown
        if resolution_counts:
            self.sub_section_title('Resolution Breakdown')
            tbl_header('Resolution', 'Count')
            res_cfg = [
                ('SAFE',         'False Positive', C_GREEN),
                ('FIXED',        'Fixed',          C_ACCENT),
                ('ACKNOWLEDGED', 'Valid',          C_ORANGE),
            ]
            for idx, (raw, lbl, col) in enumerate(res_cfg):
                cnt = resolution_counts.get(raw, 0)
                if cnt:
                    tbl_row(lbl, cnt, col1_color=col, even=(idx % 2 == 0))
            self.ln(8)

        # Severity
        self.sub_section_title('Severity')
        tbl_header('Severity', 'Count')
        sev_cfg = [
            ('HIGH',   'High',   C_RED),
            ('MEDIUM', 'Medium', C_ORANGE),
            ('LOW',    'Low',    C_GREEN),
        ]
        for idx, (raw, lbl, col) in enumerate(sev_cfg):
            tbl_row(lbl, severity_counts.get(raw, 0),
                    col1_color=col, even=(idx % 2 == 0))
        self.ln(8)

        # Top Categories
        self.sub_section_title('Top Security Categories')
        tbl_header('Security Category', 'Count')
        for idx, (cat, cnt) in enumerate(category_counts.most_common(10)):
            tbl_row(cat[:48], cnt, even=(idx % 2 == 0))

    # ------------------------------------------------------------------
    # No Vulnerabilities
    # ------------------------------------------------------------------
    def no_vulnerabilities_page(self):
        self.add_page()
        self.set_y(110)
        self.set_fill_color(*C_GREEN)
        self.rect(self.l_margin, self.get_y(), 180, 38, 'F')
        self.set_xy(self.l_margin, self.get_y() + 8)
        self.set_font('Helvetica', 'B', 18)
        self.set_text_color(*C_WHITE)
        self.cell(0, 10, 'NO VULNERABILITIES FOUND',
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
        self.set_font('Helvetica', '', 11)
        self.cell(0, 8, 'No security hotspots were detected in this assessment.',
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
        self.set_text_color(*C_DARK)

    # ------------------------------------------------------------------
    # Individual Finding
    # ------------------------------------------------------------------
    def hotspot_section(self, hotspot_data, finding_num, total_findings):
        try:
            # "Finding # N of M" counter line (top-right)
            self.set_font('Helvetica', '', 8)
            self.set_text_color(*C_MID)
            self.set_x(self.l_margin)
            self.cell(0, 4, f'Finding {finding_num} of {total_findings}',
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='R')
            self.ln(1)

            # Finding title bar: "Finding #N  <name>"
            vp      = hotspot_data.get('vulnerability_probability', 'UNKNOWN')
            vp_disp = severity_display(vp)
            vp_col  = C_RED if vp == 'HIGH' else (C_ORANGE if vp == 'MEDIUM' else C_GREEN)

            # Left accent bar colour = severity colour
            title_y = self.get_y()
            self.set_fill_color(*vp_col)
            self.rect(self.l_margin, title_y, 3, 10, 'F')
            self.set_fill_color(240, 244, 250)
            self.rect(self.l_margin + 3, title_y, 177, 10, 'F')

            self.set_xy(self.l_margin + 6, title_y + 1.5)
            self.set_font('Helvetica', 'B', 11)
            self.set_text_color(*C_PRIMARY)
            self.cell(20, 7, f'Finding #{finding_num}',
                      new_x=XPos.RIGHT, new_y=YPos.TOP, align='L')
            self.set_text_color(*C_DARK)
            name_str = self.safe_text(hotspot_data.get('name', 'Unnamed')[:80])
            self.cell(0, 7, f'  {name_str}',
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')

            self.ln(4)

            # --- Recommendation / Solution block (was "Message") ---
            if hotspot_data.get('message'):
                self.set_x(self.l_margin)
                self.set_font('Helvetica', 'B', 9)
                self.set_text_color(*C_PRIMARY)
                self.cell(0, 5, 'Recommendation / Solution:',
                          new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
                self.set_x(self.l_margin)
                self.set_font('Helvetica', 'B', 9)
                self.set_text_color(*C_DARK)
                self.multi_cell(0, 5.5,
                                self.safe_text(hotspot_data['message']),
                                new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                self.ln(3)

            # --- Metadata table ---
            self.kv_row('Category:', hotspot_data.get('security_category', '')[:60])

            # Severity - coloured text, no background pill
            self.status_pill('Severity:', vp_disp, *vp_col)

            # Review Status
            status  = hotspot_data.get('status', 'UNKNOWN')
            st_map  = {'REVIEWED': 'Reviewed', 'TO_REVIEW': 'Pending Review'}
            st_disp = st_map.get(status, status.replace('_', ' ').title())
            st_col  = C_GREEN if status == 'REVIEWED' else (C_RED if status == 'TO_REVIEW' else C_GREY)
            self.status_pill('Review Status:', st_disp, *st_col)

            # Resolution Status (only when reviewed and set)
            resolution = hotspot_data.get('resolution', 'NONE')
            if status == 'REVIEWED' and resolution != 'NONE':
                disp    = resolution_display(resolution)
                if resolution == 'SAFE':
                    res_col = C_GREEN
                elif resolution == 'FIXED':
                    res_col = C_ACCENT
                elif resolution == 'ACKNOWLEDGED':
                    res_col = C_ORANGE
                else:
                    res_col = C_GREY
                self.status_pill('Resolution Status:', disp, *res_col)

            # Reviewed by
            if status == 'REVIEWED':
                self.kv_row('Reviewed by:', COMPANY_NAME)

            # Assignee
            if hotspot_data.get('assignee') and hotspot_data['assignee'] != 'Unassigned':
                self.kv_row('Assigned to:', hotspot_data['assignee'])

            # File & Line
            self.kv_row('File:', hotspot_data.get('file', '')[:80])
            self.kv_row('Line:', hotspot_data.get('line', ''))

            # Comments
            if hotspot_data.get('comments'):
                self.ln(2)
                self.set_font('Helvetica', 'B', 8)
                self.set_text_color(*C_PRIMARY)
                self.set_x(self.l_margin)
                self.cell(0, 5, 'Comments:',
                          new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
                self.set_font('Helvetica', '', 8)
                self.set_text_color(*C_DARK)
                for comment in hotspot_data['comments'][:2]:
                    txt  = comment.get('text', '')[:100]
                    user = comment.get('user', 'Unknown')
                    if txt:
                        self.set_x(self.l_margin + 4)
                        self.multi_cell(0, 4,
                                        self.safe_text(f"- {user}: {txt}"),
                                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                if len(hotspot_data['comments']) > 2:
                    self.set_x(self.l_margin + 4)
                    extra = len(hotspot_data['comments']) - 2
                    self.cell(0, 4, f"... and {extra} more comment(s).",
                              new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')

            self.ln(4)

            # --- Code Snippet ---
            self.set_font('Helvetica', 'B', 9)
            self.set_text_color(*C_PRIMARY)
            self.set_x(self.l_margin)
            self.cell(0, 6, 'CODE SNIPPET',
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
            self.set_draw_color(*C_ACCENT)
            self.set_line_width(0.3)
            self.line(self.l_margin, self.get_y(),
                      self.l_margin + 44, self.get_y())
            self.ln(2)

            for src_line in hotspot_data.get('code_snippet', []):
                ln_num = str(src_line['line'])
                code   = src_line['code'][:72]
                is_hot = int(src_line['line']) == hotspot_data.get('line', -1)
                try:
                    self.set_x(self.l_margin)
                    if is_hot:
                        self.set_fill_color(253, 236, 236)
                        self.set_text_color(*C_RED)
                        self.set_font('Courier', 'B', 8)
                    else:
                        self.set_fill_color(248, 249, 250)
                        self.set_text_color(80, 80, 80)
                        self.set_font('Courier', '', 8)

                    self.cell(12, 5, ln_num, fill=True,
                              new_x=XPos.RIGHT, new_y=YPos.TOP, align='R')
                    self.cell(0, 5, '  ' + self.safe_text(code), fill=True,
                              new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
                except Exception:
                    continue

            self.set_text_color(*C_DARK)
            self.set_fill_color(*C_WHITE)
            self.ln(5)

        except Exception as e:
            print(f"  PDF generation error: {e}")
            raise


# =========================
# Helper Functions
# =========================

def clean_code(html_code):
    text = re.sub('<.*?>', '', html_code)
    return ''.join(c for c in text if ord(c) >= 32 or c == '\n')


def login_to_sonarqube(base_url, username, password):
    session = requests.Session()
    try:
        resp = session.post(
            f"{base_url}/api/authentication/login",
            data={'login': username, 'password': password},
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
        )
        if resp.status_code == 200:
            print("Login successful!")
            return session
        print(f"Login failed: {resp.status_code}")
    except Exception as e:
        print(f"Login error: {e}")
    return None


def get_available_projects(session, base_url):
    try:
        resp = session.get(f"{base_url}/api/projects/search?ps=500")
        if resp.status_code == 200:
            return resp.json().get('components', [])
    except Exception as e:
        print(f"Error fetching projects: {e}")
    return []


def validate_project_key(session, base_url, project_key):
    try:
        encoded = urllib.parse.quote(project_key, safe='')
        resp = session.get(f"{base_url}/api/projects/search?projects={encoded}")
        if resp.status_code == 200:
            comps = resp.json().get('components', [])
            if comps:
                key = comps[0].get('key', project_key)
                print(f"Project validated: {key}")
                return key
    except Exception as e:
        print(f"Error validating project: {e}")
    return None


def get_hotspot_details(session, base_url, hotspot_key):
    try:
        resp = session.get(f"{base_url}/api/hotspots/show?hotspot={hotspot_key}")
        if resp.status_code == 200:
            data = resp.json()
            assignee = "Unassigned"
            if data.get("assignee"):
                assignee = data["assignee"].get("name", "Unassigned")
            return {
                'status':        data.get("status", "UNKNOWN"),
                'resolution':    data.get("resolution", "NONE") or "NONE",
                'comments':      data.get("comments", []),
                'assignee':      assignee,
                'creation_date': data.get("creationDate", ""),
            }
    except Exception as e:
        print(f"  Error fetching hotspot details: {e}")
    return {
        'status': 'UNKNOWN', 'resolution': 'NONE',
        'comments': [], 'assignee': 'Unassigned', 'creation_date': '',
    }


# =========================
# Main
# =========================

def main():
    global COMPANY_NAME, CLIENT_NAME, PROJECT_NAME, ASSET_TYPE, PROJECT_KEY, REPORT_DATE

    REPORT_DATE = datetime.now().strftime('%B %d, %Y')

    print("\n" + "="*60)
    print("SONARQUBE SECURITY HOTSPOTS REPORT GENERATOR v4.0 by AS")
    print("="*60)

    print("\n--- YOUR COMPANY ---")
    COMPANY_NAME = (input("Your Company Name: ").strip() or "COMMTEL").upper()

    print("\n--- CLIENT INFORMATION ---")
    CLIENT_NAME  = input("Client Name: ").strip() or "CLIENT"
    PROJECT_NAME = input("Project Name: ").strip() or "PROJECT"

    print("\nAsset Type:")
    print("  1. Web Application  2. Mobile Application  3. API")
    print("  4. Desktop Application  5. Cloud Service  6. Other")
    asset_choice = input("Enter choice (1-6) [1]: ").strip() or "1"
    asset_map = {
        "1": "Web Application", "2": "Mobile Application",
        "3": "API", "4": "Desktop Application",
        "5": "Cloud Service", "6": "Other",
    }
    ASSET_TYPE = asset_map.get(asset_choice, "Web Application")
    if asset_choice == "6":
        custom = input("Enter custom asset type: ").strip()
        if custom:
            ASSET_TYPE = custom

    sonar_url = (input("\nSonarQube URL [http://localhost:9000]: ").strip()
                 or "http://localhost:9000").rstrip('/')

    print("\n--- LOGIN CREDENTIALS ---")
    username = input("Username: ").strip()
    password = getpass.getpass("Password: ")

    session = login_to_sonarqube(sonar_url, username, password)
    if not session:
        print("Exiting due to login failure.")
        return

    print("\n--- PROJECT INFORMATION ---")
    if input("List available projects? (y/n) [n]: ").strip().lower() == 'y':
        projects = get_available_projects(session, sonar_url)
        if projects:
            print(f"\nFound {len(projects)} projects:")
            for i, p in enumerate(projects[:20], 1):
                print(f"  {i}. {p.get('name')} (Key: {p.get('key')})")
            if len(projects) > 20:
                print(f"  ... and {len(projects)-20} more")

    project_key_input = input("\nProject Key/ID: ").strip().strip('"\'')
    if not project_key_input:
        print("Project key is required. Exiting.")
        return

    actual_project_key = validate_project_key(session, sonar_url, project_key_input)
    if not actual_project_key:
        print(f"Project key '{project_key_input}' not found.")
        projects = get_available_projects(session, sonar_url)
        similar  = [p for p in projects
                    if project_key_input.lower() in p.get('key', '').lower()
                    or project_key_input.lower() in p.get('name', '').lower()]
        if similar:
            print("\nSimilar projects:")
            for i, p in enumerate(similar, 1):
                print(f"  {i}. {p.get('name')}  (Key: {p.get('key')})")
            choice = input("\nUse one? Enter number or Enter to exit: ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(similar):
                actual_project_key = similar[int(choice)-1].get('key')
            else:
                return
        else:
            print("No similar projects found. Exiting.")
            return

    PROJECT_KEY = actual_project_key

    print(f"\nFetching hotspots for: {PROJECT_KEY}...")
    hotspot_api = (
        f"{sonar_url}/api/hotspots/search"
        f"?projectKey={urllib.parse.quote(PROJECT_KEY, safe='')}&ps=500"
    )
    try:
        resp = session.get(hotspot_api)
        resp.raise_for_status()
    except Exception as e:
        print(f"Error fetching hotspots: {e}")
        return

    hotspots = resp.json().get("hotspots", [])
    print(f"Found {len(hotspots)} hotspots\n")

    pdf = SonarQubePDF()
    pdf.set_auto_page_break(auto=True, margin=20)

    clean_pk = re.sub(r'[^\w\-_]', '_', PROJECT_KEY)
    clean_cn = re.sub(r'[^\w\-_]', '_', CLIENT_NAME)
    pdf_filename = (
        f"{COMPANY_NAME}_SecurityReview_{clean_cn}_"
        f"{clean_pk}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    )

    pdf.title_page()

    if not hotspots:
        pdf.no_vulnerabilities_page()
        pdf.output(pdf_filename)
        print(f"\nReport saved: {pdf_filename}  (no vulnerabilities found)")
        return

    all_hotspot_data = []
    successful = failed = 0

    print("Processing hotspots...")
    for i, hotspot in enumerate(hotspots, 1):
        try:
            hkey      = hotspot.get("key")
            component = hotspot.get("component")
            line      = hotspot.get("line", 1)
            sec_cat   = hotspot.get("securityCategory", "Unknown")

            print(f"  {i}/{len(hotspots)}: {hkey[-8:]}...", end="", flush=True)

            details    = get_hotspot_details(session, sonar_url, hkey)
            status     = details['status']
            resolution = details['resolution']
            assignee   = details['assignee']
            cdate      = details['creation_date']
            comments   = details['comments']

            rule_resp = session.get(f"{sonar_url}/api/hotspots/show?hotspot={hkey}")
            rule_key = name = message = severity = vuln_prob = ""
            if rule_resp.status_code == 200:
                rd        = rule_resp.json()
                rule      = rd.get("rule", {})
                message   = rd.get("message", "")
                rule_key  = rule.get("key", "")
                severity  = rule.get("severity", "")
                name      = rule.get("name", "")
                vuln_prob = (rule.get("vulnerabilityProbability") or
                             hotspot.get("vulnerabilityProbability") or
                             severity)

            start     = max(1, line - 5)
            end       = line + 5
            enc       = urllib.parse.quote(component, safe="")
            code_resp = session.get(
                f"{sonar_url}/api/sources/lines?key={enc}&from={start}&to={end}"
            )
            code_snippet = []
            if code_resp.status_code == 200:
                for src in code_resp.json().get("sources", []):
                    cl = clean_code(src["code"])
                    if cl.strip():
                        code_snippet.append({'line': src['line'], 'code': cl})

            all_hotspot_data.append({
                'key': hkey, 'file': component, 'line': line,
                'status': status, 'resolution': resolution,
                'assignee': assignee, 'creation_date': cdate,
                'rule_key': rule_key, 'severity': severity,
                'vulnerability_probability': vuln_prob,
                'security_category': sec_cat,
                'name': name, 'message': message,
                'code_snippet': code_snippet, 'comments': comments,
            })
            successful += 1
            print(f" OK [{status}]")
        except Exception as e:
            print(f" ERROR: {e}")
            failed += 1

    # Build charts
    print("\nGenerating charts...")
    severity_counts   = Counter()
    status_counts     = Counter()
    resolution_counts = Counter()
    category_counts   = Counter()

    for d in all_hotspot_data:
        severity_counts[d.get('vulnerability_probability', 'UNKNOWN')] += 1
        status_counts[d.get('status', 'UNKNOWN')] += 1
        res = d.get('resolution', 'NONE')
        if res != 'NONE':
            resolution_counts[res] += 1
        category_counts[d.get('security_category', 'Unknown')] += 1

    sev_png = make_severity_pie(severity_counts)
    bar_png = make_findings_bar(severity_counts, status_counts, resolution_counts)

    # Assemble PDF
    pdf.executive_summary(all_hotspot_data, sev_png, bar_png)
    pdf.resolution_definitions_page()
    pdf.summary_table(all_hotspot_data)

    print("Adding findings...")
    total_findings = len(all_hotspot_data)
    for i, hd in enumerate(all_hotspot_data, 1):
        try:
            pdf.add_page()
            pdf.hotspot_section(hd, i, total_findings)
        except Exception as e:
            print(f"  Error adding finding {i}: {e}")

    # Save
    try:
        pdf.output(pdf_filename)
        print(f"\n{'='*70}")
        print("REPORT GENERATED SUCCESSFULLY")
        print(f"File     : {pdf_filename}")
        print(f"Findings : {successful}  (failed: {failed})")
        sev_order = [('HIGH','High'), ('MEDIUM','Medium'), ('LOW','Low')]
        for raw, lbl in sev_order:
            if severity_counts.get(raw):
                print(f"  {lbl}: {severity_counts[raw]}")
        if resolution_counts:
            print("Resolutions:")
            for raw, cnt in resolution_counts.items():
                print(f"  {resolution_display(raw)}: {cnt}")
        print(f"{'='*70}\n")
    except Exception as e:
        print(f"Error saving PDF: {e}")


if __name__ == "__main__":
    main()
