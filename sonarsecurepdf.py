import requests
import urllib.parse
import re
from fpdf import FPDF
from fpdf.enums import XPos, YPos
import os
from datetime import datetime
import textwrap
import getpass
import sys
from collections import Counter

# =========================
# Global Variables
# =========================
PROJECT_KEY = ""
COMPANY_NAME = ""
CLIENT_NAME = ""
PROJECT_NAME = ""
ASSET_TYPE = ""

# =========================
# Custom PDF Class
# =========================

class SonarQubePDF(FPDF):
    def __init__(self):
        super().__init__()
        # Set margins
        self.set_left_margin(15)
        self.set_right_margin(15)
        
    def header(self):
        # Only show header on pages after title page
        if self.page_no() > 1:
            # Add logo from same folder as script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            logo_path = os.path.join(script_dir, "logo.png")
            
            if os.path.exists(logo_path):
                self.image(logo_path, x=10, y=8, w=30)
                self.set_x(45)  # Move right after logo
            
            self.set_font('Helvetica', 'B', 12)
            self.set_text_color(0, 102, 204)
            self.cell(0, 10, f'{COMPANY_NAME} SOURCE CODE REVIEW REPORT', 
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
            
            # Add project info
            self.set_font('Helvetica', '', 8)
            self.set_text_color(100, 100, 100)
            self.cell(0, 4, f'Project: {PROJECT_KEY} | Client: {CLIENT_NAME} | Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
            self.ln(2)
            
            # Draw a line
            self.set_draw_color(0, 102, 204)
            self.line(10, self.get_y(), 200, self.get_y())
            self.ln(5)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 7)
        self.set_text_color(128, 128, 128)
        
        # Confidential footer on left
        self.set_x(15)
        self.cell(0, 5, 'CONFIDENTIAL', 
                  new_x=XPos.LEFT, new_y=YPos.TOP, align='L')
        
        # Auto-generated message on right
        self.set_x(115)
        self.cell(0, 5, 'Automatically generated using SonarQube', 
                  new_x=XPos.RIGHT, new_y=YPos.TOP, align='R')
        
        # Page number centered
        self.set_y(-10)
        self.cell(0, 5, f'Page {self.page_no()}', 
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    
    def safe_text(self, text):
        """Replace unsupported characters with safe alternatives"""
        if not text:
            return ""
        
        # Convert to string
        text = str(text)
        
        # Replace common Unicode characters with ASCII alternatives
        replacements = {
            '\u2022': '-',
            '\u2014': '-',
            '\u2013': '-',
            '\u2018': "'",
            '\u2019': "'",
            '\u201c': '"',
            '\u201d': '"',
            '\u2026': '...',
            '\u00a9': '(c)',
            '\u00ae': '(R)',
            '\u2122': '(TM)',
            '\u00b0': ' degrees',
            '\u00b1': '+/-',
            '\u00d7': 'x',
            '\u00f7': '/',
            '\u2713': 'OK',
            '\u2717': 'NO',
            '\u2192': '->',
            '\u2190': '<-',
            '\u2191': '^',
            '\u2193': 'v',
        }
        
        for unicode_char, ascii_char in replacements.items():
            text = text.replace(unicode_char, ascii_char)
        
        # Remove any remaining non-ASCII characters
        text = text.encode('ascii', 'ignore').decode('ascii')
        return text
    
    def write_safe_text(self, text, line_height=6):
        """Safely write text using write() method which handles line breaks better"""
        if not text:
            return
        
        safe_text = self.safe_text(text)
        self.write(line_height, safe_text)
    
    def safe_multi_cell(self, w, h, txt, border=0, align='L', fill=False):
        """Wrapper around multi_cell that always resets X to left margin first"""
        self.set_x(self.l_margin)
        self.multi_cell(w, h, txt, border=border, align=align, fill=fill,
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def title_page(self):
        """Create a title page with company and client information"""
        self.add_page()
        
        # Center vertically
        self.set_y(60)
        
        # Add logo (larger on title page)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(script_dir, "logo.png")
        if os.path.exists(logo_path):
            self.image(logo_path, x=80, y=30, w=50)
            self.set_y(85)
        
        self.set_font('Helvetica', 'B', 28)
        self.set_text_color(0, 102, 204)
        self.cell(0, 20, self.safe_text(COMPANY_NAME), new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
        
        self.set_font('Helvetica', 'B', 24)
        self.set_text_color(50, 50, 50)
        self.cell(0, 15, 'Source Code Review Report', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
        
        self.ln(20)
        
        # Client and Project Information
        self.set_font('Helvetica', 'B', 14)
        self.set_text_color(0, 102, 204)
        self.cell(0, 10, 'CLIENT INFORMATION', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
        self.ln(5)
        
        self.set_font('Helvetica', '', 12)
        self.set_text_color(50, 50, 50)
        
        # Create a table-like structure for client info
        self.set_x(40)
        self.cell(50, 10, 'Client Name:', new_x=XPos.RIGHT, new_y=YPos.TOP, align='L')
        self.set_font('Helvetica', 'B', 12)
        self.cell(0, 10, self.safe_text(CLIENT_NAME), new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        
        self.set_x(40)
        self.set_font('Helvetica', '', 12)
        self.cell(50, 10, 'Project Name:', new_x=XPos.RIGHT, new_y=YPos.TOP, align='L')
        self.set_font('Helvetica', 'B', 12)
        self.cell(0, 10, self.safe_text(PROJECT_NAME), new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        
        self.set_x(40)
        self.set_font('Helvetica', '', 12)
        self.cell(50, 10, 'Asset Type:', new_x=XPos.RIGHT, new_y=YPos.TOP, align='L')
        self.set_font('Helvetica', 'B', 12)
        self.cell(0, 10, self.safe_text(ASSET_TYPE), new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        
        self.set_x(40)
        self.set_font('Helvetica', '', 12)
        self.cell(50, 10, 'SonarQube Project:', new_x=XPos.RIGHT, new_y=YPos.TOP, align='L')
        self.set_font('Helvetica', 'B', 12)
        self.cell(0, 10, self.safe_text(PROJECT_KEY), new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        
        self.ln(10)
        
        # Date information
        self.set_font('Helvetica', '', 12)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, f'Report Date: {datetime.now().strftime("%B %d, %Y")}', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
        self.cell(0, 8, f'Report Time: {datetime.now().strftime("%H:%M:%S")}', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
        
        self.ln(15)
        
        # Confidential stamp
        self.set_font('Helvetica', 'I', 12)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, 'CONFIDENTIAL', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    
    def executive_summary(self, hotspots_data):
        """Create an executive summary page with high-level findings"""
        self.add_page()
        
        # Section title
        self.set_font('Helvetica', 'B', 20)
        self.set_text_color(0, 102, 204)
        self.set_x(self.l_margin)
        self.cell(0, 15, 'EXECUTIVE SUMMARY', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        self.ln(5)
        
        # Introduction
        self.set_font('Helvetica', '', 11)
        self.set_text_color(50, 50, 50)
        
        intro_text = (
            f"This report presents the findings of the source code security review "
            f"conducted by {COMPANY_NAME} for {CLIENT_NAME}. The assessment focused on "
            f"identifying security hotspots and vulnerabilities in the {PROJECT_NAME} "
            f"project ({ASSET_TYPE})."
        )
        self.safe_multi_cell(0, 6, self.safe_text(intro_text))
        self.ln(10)
        
        # Calculate statistics
        total_vulns = len(hotspots_data)
        severity_counts = Counter()
        status_counts = Counter()
        resolution_counts = Counter()
        
        for data in hotspots_data:
            severity = data.get('vulnerability_probability', 'UNKNOWN')
            status = data.get('status', 'UNKNOWN')
            resolution = data.get('resolution', 'NONE')
            
            severity_counts[severity] += 1
            status_counts[status] += 1
            if resolution != 'NONE':
                resolution_counts[resolution] += 1
        
        # Key Findings Section
        self.set_font('Helvetica', 'B', 14)
        self.set_text_color(0, 102, 204)
        self.set_x(self.l_margin)
        self.cell(0, 10, 'Key Findings', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        self.ln(2)
        
        self.set_font('Helvetica', '', 11)
        self.set_text_color(50, 50, 50)
        
        self.set_x(self.l_margin)
        self.cell(0, 8, f'Total Security Hotspots: {total_vulns}', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        
        high_count = severity_counts.get('HIGH', 0)
        self.set_text_color(255, 0, 0)
        self.set_x(self.l_margin)
        self.cell(0, 8, f'High Probability Issues: {high_count}', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        
        medium_count = severity_counts.get('MEDIUM', 0)
        self.set_text_color(255, 165, 0)
        self.set_x(self.l_margin)
        self.cell(0, 8, f'Medium Probability Issues: {medium_count}', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        
        low_count = severity_counts.get('LOW', 0)
        self.set_text_color(0, 128, 0)
        self.set_x(self.l_margin)
        self.cell(0, 8, f'Low Probability Issues: {low_count}', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        
        self.set_text_color(50, 50, 50)
        reviewed_count = status_counts.get('REVIEWED', 0)
        to_review_count = status_counts.get('TO_REVIEW', 0)
        
        self.set_x(self.l_margin)
        self.cell(0, 8, f'Reviewed Issues: {reviewed_count}', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        self.set_text_color(255, 0, 0)
        self.set_x(self.l_margin)
        self.cell(0, 8, f'Issues To Review: {to_review_count}', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        
        self.set_text_color(50, 50, 50)
        self.ln(5)
        
        # Resolution Summary (if any)
        if resolution_counts:
            self.set_font('Helvetica', 'B', 14)
            self.set_text_color(0, 102, 204)
            self.set_x(self.l_margin)
            self.cell(0, 10, 'Resolution Status', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
            self.ln(2)
            
            self.set_font('Helvetica', '', 11)
            self.set_text_color(50, 50, 50)
            
            resolution_text = "Of the reviewed issues, the following resolutions have been applied:"
            self.safe_multi_cell(0, 6, self.safe_text(resolution_text))
            self.ln(2)
            
            for resolution in ['SAFE', 'FIXED', 'ACKNOWLEDGED']:
                count = resolution_counts.get(resolution, 0)
                if count > 0:
                    percentage = (count / reviewed_count * 100) if reviewed_count > 0 else 0
                    bullet = f"- {resolution}: {count} issues ({percentage:.1f}% of reviewed issues)"
                    
                    if resolution in ('SAFE', 'FIXED'):
                        self.set_text_color(0, 128, 0)
                    elif resolution == 'ACKNOWLEDGED':
                        self.set_text_color(255, 165, 0)
                    
                    self.safe_multi_cell(0, 6, self.safe_text(bullet))
                    self.set_text_color(50, 50, 50)
        
        self.ln(5)
        
        # Risk Assessment
        self.set_font('Helvetica', 'B', 14)
        self.set_text_color(0, 102, 204)
        self.set_x(self.l_margin)
        self.cell(0, 10, 'Risk Assessment', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        self.ln(2)
        
        self.set_font('Helvetica', '', 11)
        self.set_text_color(50, 50, 50)
        
        # Determine overall risk level
        if high_count > 0:
            risk_level = "HIGH"
            risk_color = (255, 0, 0)
            risk_text = (
                f"The presence of {high_count} high probability issues indicates "
                f"significant security risks that require immediate attention."
            )
        elif medium_count > 5:
            risk_level = "MEDIUM"
            risk_color = (255, 165, 0)
            risk_text = (
                f"The presence of {medium_count} medium probability issues indicates "
                f"moderate security risks that should be addressed."
            )
        else:
            risk_level = "LOW"
            risk_color = (0, 128, 0)
            risk_text = (
                "The low number of security issues indicates a generally secure "
                "codebase with minimal immediate risks."
            )
        
        self.set_font('Helvetica', 'B', 12)
        self.set_text_color(*risk_color)
        self.set_x(self.l_margin)
        self.cell(0, 8, self.safe_text(f'Overall Risk Level: {risk_level}'), new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        
        self.set_font('Helvetica', '', 11)
        self.set_text_color(50, 50, 50)
        self.safe_multi_cell(0, 6, self.safe_text(risk_text))
        self.ln(5)
        
        # Recommendations
        self.set_font('Helvetica', 'B', 14)
        self.set_text_color(0, 102, 204)
        self.set_x(self.l_margin)
        self.cell(0, 10, 'Recommendations', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        self.ln(2)
        
        self.set_font('Helvetica', '', 11)
        self.set_text_color(50, 50, 50)
        
        recommendations = []
        if high_count > 0:
            recommendations.append("- Prioritize remediation of HIGH probability issues immediately")
        if to_review_count > 0:
            recommendations.append("- Complete review of all outstanding security hotspots")
        if medium_count > 0:
            recommendations.append("- Address MEDIUM probability issues in the next development cycle")
        
        recommendations.append("- Implement security training for developers based on findings")
        recommendations.append("- Establish regular security code reviews as part of SDLC")
        
        for rec in recommendations:
            self.safe_multi_cell(0, 6, self.safe_text(rec))
    
    def summary_table(self, hotspots_data):
        """Create a summary table with vulnerability statistics including status"""
        self.add_page()
        
        # Section title
        self.set_font('Helvetica', 'B', 18)
        self.set_text_color(0, 102, 204)
        self.set_x(self.l_margin)
        self.cell(0, 15, 'Vulnerability Summary', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        self.ln(5)
        
        # Calculate statistics
        total_vulns = len(hotspots_data)
        severity_counts = Counter()
        category_counts = Counter()
        status_counts = Counter()
        resolution_counts = Counter()
        reviewed_count = 0
        unreviewed_count = 0
        
        for data in hotspots_data:
            severity = data.get('vulnerability_probability', 'UNKNOWN')
            category = data.get('security_category', 'Unknown')
            status = data.get('status', 'UNKNOWN')
            resolution = data.get('resolution', 'NONE')
            
            severity_counts[severity] += 1
            category_counts[category] += 1
            status_counts[status] += 1
            if resolution != 'NONE':
                resolution_counts[resolution] += 1
            
            if status == 'REVIEWED':
                reviewed_count += 1
            else:
                unreviewed_count += 1
        
        # Overall stats
        self.set_font('Helvetica', 'B', 12)
        self.set_text_color(50, 50, 50)
        self.set_x(self.l_margin)
        self.cell(0, 8, f'Total Vulnerabilities Found: {total_vulns}', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        self.ln(5)
        
        # Status summary
        self.set_x(self.l_margin)
        self.set_font('Helvetica', 'B', 11)
        self.set_fill_color(240, 248, 255)
        self.cell(90, 10, 'Status', border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C', fill=True)
        self.cell(90, 10, 'Count', border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C', fill=True)
        
        self.set_font('Helvetica', '', 10)
        self.set_fill_color(255, 255, 255)
        
        status_order = ['REVIEWED', 'TO_REVIEW', 'UNKNOWN']
        
        for status in status_order:
            count = status_counts.get(status, 0)
            if count > 0 or status == 'TO_REVIEW':
                self.set_x(self.l_margin)
                if status == 'REVIEWED':
                    self.set_text_color(0, 128, 0)
                elif status == 'TO_REVIEW':
                    self.set_text_color(255, 0, 0)
                else:
                    self.set_text_color(100, 100, 100)
                
                self.cell(90, 8, status, border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C')
                self.set_text_color(50, 50, 50)
                self.cell(90, 8, str(count), border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
        
        self.ln(10)
        
        # Resolution summary (for reviewed items)
        if resolution_counts:
            self.set_x(self.l_margin)
            self.set_font('Helvetica', 'B', 11)
            self.set_fill_color(240, 248, 255)
            self.cell(90, 10, 'Resolution', border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C', fill=True)
            self.cell(90, 10, 'Count', border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C', fill=True)
            
            self.set_font('Helvetica', '', 10)
            self.set_fill_color(255, 255, 255)
            
            resolution_order = ['SAFE', 'FIXED', 'ACKNOWLEDGED', 'OTHER']
            
            for resolution in resolution_order:
                count = 0
                if resolution == 'OTHER':
                    for res, res_count in resolution_counts.items():
                        if res not in ['SAFE', 'FIXED', 'ACKNOWLEDGED']:
                            count += res_count
                else:
                    count = resolution_counts.get(resolution, 0)
                
                if count > 0:
                    self.set_x(self.l_margin)
                    if resolution in ['SAFE', 'FIXED']:
                        self.set_text_color(0, 128, 0)
                    elif resolution == 'ACKNOWLEDGED':
                        self.set_text_color(255, 165, 0)
                    else:
                        self.set_text_color(100, 100, 100)
                    
                    self.cell(90, 8, resolution, border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C')
                    self.set_text_color(50, 50, 50)
                    self.cell(90, 8, str(count), border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
            
            self.ln(10)
        
        # Review progress
        self.set_x(self.l_margin)
        self.set_font('Helvetica', 'B', 11)
        self.set_fill_color(240, 248, 255)
        self.cell(90, 10, 'Review Progress', border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C', fill=True)
        self.cell(90, 10, '', border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C', fill=True)
        
        self.set_font('Helvetica', '', 10)
        self.set_fill_color(255, 255, 255)
        
        reviewed_pct = (reviewed_count / total_vulns * 100) if total_vulns > 0 else 0
        unreviewed_pct = (unreviewed_count / total_vulns * 100) if total_vulns > 0 else 0
        
        self.set_x(self.l_margin)
        self.set_text_color(0, 128, 0)
        self.cell(90, 8, f'Reviewed ({reviewed_pct:.1f}%)', border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C')
        self.set_text_color(50, 50, 50)
        self.cell(90, 8, str(reviewed_count), border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
        
        self.set_x(self.l_margin)
        self.set_text_color(255, 0, 0)
        self.cell(90, 8, f'To Review ({unreviewed_pct:.1f}%)', border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C')
        self.set_text_color(50, 50, 50)
        self.cell(90, 8, str(unreviewed_count), border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
        
        self.ln(10)
        
        # Severity breakdown table
        self.set_x(self.l_margin)
        self.set_font('Helvetica', 'B', 11)
        self.set_fill_color(240, 248, 255)
        self.cell(90, 10, 'Vulnerability Probability', border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C', fill=True)
        self.cell(90, 10, 'Count', border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C', fill=True)
        
        self.set_font('Helvetica', '', 10)
        self.set_fill_color(255, 255, 255)
        
        severity_order = ['HIGH', 'MEDIUM', 'LOW']
        for severity in severity_order:
            count = severity_counts.get(severity, 0)
            
            self.set_x(self.l_margin)
            if severity == 'HIGH':
                self.set_text_color(255, 0, 0)
            elif severity == 'MEDIUM':
                self.set_text_color(255, 165, 0)
            else:
                self.set_text_color(0, 128, 0)
            
            self.cell(90, 8, severity, border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C')
            self.set_text_color(50, 50, 50)
            self.cell(90, 8, str(count), border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
        
        other_severities = [s for s in severity_counts.keys() if s not in severity_order]
        for severity in other_severities:
            self.set_x(self.l_margin)
            self.cell(90, 8, severity, border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C')
            self.cell(90, 8, str(severity_counts[severity]), border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
        
        self.ln(10)
        
        # Top categories table
        self.set_x(self.l_margin)
        self.set_font('Helvetica', 'B', 11)
        self.set_fill_color(240, 248, 255)
        self.cell(90, 10, 'Security Category', border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C', fill=True)
        self.cell(90, 10, 'Count', border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C', fill=True)
        
        self.set_font('Helvetica', '', 10)
        self.set_fill_color(255, 255, 255)
        
        for category, count in category_counts.most_common(10):
            self.set_x(self.l_margin)
            self.cell(90, 8, self.safe_text(category[:40]), border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='L')
            self.cell(90, 8, str(count), border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    
    def severity_chart(self, severity_counts):
        """Create a simple bar chart for severity distribution"""
        self.add_page()
        
        # Section title
        self.set_font('Helvetica', 'B', 18)
        self.set_text_color(0, 102, 204)
        self.set_x(self.l_margin)
        self.cell(0, 15, 'Vulnerability Distribution', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        self.ln(10)
        
        # Chart title
        self.set_font('Helvetica', 'B', 12)
        self.set_text_color(50, 50, 50)
        self.set_x(self.l_margin)
        self.cell(0, 8, 'Probability Distribution', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
        self.ln(5)
        
        max_count = max(severity_counts.values()) if severity_counts else 1
        
        chart_start_y = self.get_y()
        bar_width = 40
        spacing = 20
        start_x = 30
        
        severities = ['HIGH', 'MEDIUM', 'LOW']
        colors = [(255, 0, 0), (255, 165, 0), (0, 128, 0)]
        
        for i, severity in enumerate(severities):
            count = severity_counts.get(severity, 0)
            bar_height = (count / max_count) * 50 if max_count > 0 else 0
            
            x = start_x + (i * (bar_width + spacing))
            y = chart_start_y + (50 - bar_height)
            
            self.set_fill_color(*colors[i])
            self.rect(x, y, bar_width, bar_height, style='F')
            
            self.set_xy(x, y - 5)
            self.set_font('Helvetica', 'B', 10)
            self.set_text_color(*colors[i])
            self.cell(bar_width, 5, str(count), new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
            
            self.set_xy(x, chart_start_y + 55)
            self.set_font('Helvetica', '', 10)
            self.set_text_color(50, 50, 50)
            self.cell(bar_width, 5, severity, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
        
        self.ln(30)
        
        self.set_font('Helvetica', 'B', 12)
        self.set_text_color(50, 50, 50)
        self.set_x(self.l_margin)
        self.cell(0, 8, 'Probability Percentage', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
        self.ln(5)
        
        total = sum(severity_counts.values())
        if total > 0:
            start_y = self.get_y()
            for i, severity in enumerate(severities):
                count = severity_counts.get(severity, 0)
                percentage = (count / total) * 100 if total > 0 else 0
                
                self.set_fill_color(*colors[i])
                self.rect(30, start_y + (i * 8), int(percentage * 1.5), 6, style='F')
                
                self.set_xy(35 + int(percentage * 1.5), start_y + (i * 8))
                self.set_font('Helvetica', '', 9)
                self.set_text_color(50, 50, 50)
                self.cell(0, 6, self.safe_text(f'{severity}: {percentage:.1f}% ({count})'), 
                         new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
    
    def no_vulnerabilities_page(self):
        """Add a page indicating no vulnerabilities found"""
        self.add_page()
        
        self.set_y(120)
        self.set_font('Helvetica', 'B', 24)
        self.set_text_color(0, 128, 0)
        self.set_x(self.l_margin)
        self.cell(0, 20, 'NO VULNERABILITIES FOUND', 
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
        
        self.set_font('Helvetica', '', 14)
        self.set_text_color(100, 100, 100)
        self.set_x(self.l_margin)
        self.cell(0, 15, 'The security scan did not detect any hotspots or vulnerabilities.', 
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
        
        self.set_font('Helvetica', '', 12)
        self.set_x(self.l_margin)
        self.cell(0, 10, 'Your code appears to be secure.', 
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    
    def hotspot_section(self, hotspot_data):
        """Display a single hotspot with status and resolution fields"""
        try:
            # Hotspot Key with background (smaller, less prominent)
            self.set_fill_color(240, 248, 255)
            self.set_font('Helvetica', 'I', 8)
            self.set_text_color(100, 100, 100)
            self.set_x(self.l_margin)
            self.cell(0, 5, f"ID: {hotspot_data['key'][:20]}...", 
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L', fill=True)
            self.ln(2)
            
            # Name - Highlighted and Bold
            self.set_fill_color(255, 255, 200)
            self.set_font('Helvetica', 'B', 14)
            self.set_text_color(0, 0, 0)
            self.set_x(self.l_margin)
            self.cell(0, 10, self.safe_text(hotspot_data['name'][:80]), 
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L', fill=True)
            self.ln(2)
            
            # Message
            if hotspot_data.get('message'):
                self.set_x(self.l_margin)
                self.set_font('Helvetica', 'B', 10)
                self.set_fill_color(240, 240, 240)
                self.cell(30, 6, "Message:", new_x=XPos.RIGHT, new_y=YPos.TOP, align='L', fill=True)
                self.set_font('Helvetica', '', 10)
                self.set_fill_color(255, 255, 255)
                self.set_x(self.l_margin + 30)
                self.multi_cell(0, 6, self.safe_text(hotspot_data['message']),
                                new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            
            # Security Category
            self.set_x(self.l_margin)
            self.set_font('Helvetica', 'B', 10)
            self.set_fill_color(240, 240, 240)
            self.cell(30, 6, "Category:", new_x=XPos.RIGHT, new_y=YPos.TOP, align='L', fill=True)
            self.set_font('Helvetica', '', 10)
            self.set_fill_color(255, 255, 255)
            self.cell(0, 6, self.safe_text(hotspot_data['security_category'][:60]), 
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
            
            # Vulnerability Probability
            vulnerability_prob = hotspot_data.get('vulnerability_probability', 'UNKNOWN')
            
            self.set_x(self.l_margin)
            self.set_font('Helvetica', 'B', 10)
            self.set_fill_color(240, 240, 240)
            self.cell(30, 6, "Probability:", new_x=XPos.RIGHT, new_y=YPos.TOP, align='L', fill=True)
            self.set_font('Helvetica', 'B', 10)
            
            if vulnerability_prob == 'HIGH':
                self.set_text_color(255, 0, 0)
                self.set_fill_color(255, 200, 200)
            elif vulnerability_prob == 'MEDIUM':
                self.set_text_color(255, 165, 0)
                self.set_fill_color(255, 235, 200)
            elif vulnerability_prob == 'LOW':
                self.set_text_color(0, 128, 0)
                self.set_fill_color(200, 255, 200)
            else:
                self.set_text_color(100, 100, 100)
                self.set_fill_color(240, 240, 240)
                
            self.cell(0, 6, vulnerability_prob, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L', fill=True)
            self.set_text_color(50, 50, 50)
            self.set_fill_color(255, 255, 255)
            
            # STATUS FIELD
            self.set_x(self.l_margin)
            self.set_font('Helvetica', 'B', 10)
            self.set_fill_color(240, 240, 240)
            self.cell(30, 6, "Status:", new_x=XPos.RIGHT, new_y=YPos.TOP, align='L', fill=True)
            self.set_font('Helvetica', 'B', 10)
            
            status = hotspot_data.get('status', 'UNKNOWN')
            
            if status == 'REVIEWED':
                self.set_text_color(0, 128, 0)
                self.set_fill_color(200, 255, 200)
            elif status == 'TO_REVIEW':
                self.set_text_color(255, 0, 0)
                self.set_fill_color(255, 200, 200)
            else:
                self.set_text_color(100, 100, 100)
                self.set_fill_color(240, 240, 240)
            
            self.cell(0, 6, status, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L', fill=True)
            self.set_text_color(50, 50, 50)
            self.set_fill_color(255, 255, 255)
            
            # RESOLUTION FIELD
            resolution = hotspot_data.get('resolution', 'NONE')
            if status == 'REVIEWED' and resolution != 'NONE':
                self.set_x(self.l_margin)
                self.set_font('Helvetica', 'B', 10)
                self.set_fill_color(240, 240, 240)
                self.cell(30, 6, "Resolution:", new_x=XPos.RIGHT, new_y=YPos.TOP, align='L', fill=True)
                self.set_font('Helvetica', 'B', 10)
                
                if resolution in ('SAFE', 'FIXED'):
                    self.set_text_color(0, 128, 0)
                    self.set_fill_color(200, 255, 200)
                elif resolution == 'ACKNOWLEDGED':
                    self.set_text_color(255, 165, 0)
                    self.set_fill_color(255, 235, 200)
                else:
                    self.set_text_color(100, 100, 100)
                    self.set_fill_color(240, 240, 240)
                
                self.cell(0, 6, resolution, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L', fill=True)
                self.set_text_color(50, 50, 50)
                self.set_fill_color(255, 255, 255)
            
            # REVIEWED BY
            if status == 'REVIEWED':
                self.set_x(self.l_margin)
                self.set_font('Helvetica', 'B', 10)
                self.set_fill_color(240, 240, 240)
                self.cell(30, 6, "Reviewed by:", new_x=XPos.RIGHT, new_y=YPos.TOP, align='L', fill=True)
                self.set_font('Helvetica', '', 10)
                self.set_fill_color(255, 255, 255)
                self.cell(0, 6, COMPANY_NAME, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L', fill=True)
            
            # Assignee
            if hotspot_data.get('assignee') and hotspot_data['assignee'] != 'Unassigned':
                self.set_x(self.l_margin)
                self.set_font('Helvetica', 'B', 10)
                self.set_fill_color(240, 240, 240)
                self.cell(30, 6, "Assigned to:", new_x=XPos.RIGHT, new_y=YPos.TOP, align='L', fill=True)
                self.set_font('Helvetica', '', 10)
                self.set_fill_color(255, 255, 255)
                self.cell(0, 6, self.safe_text(hotspot_data['assignee']), 
                          new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
            
            # File
            self.set_x(self.l_margin)
            self.set_font('Helvetica', 'B', 10)
            self.set_fill_color(240, 240, 240)
            self.cell(30, 6, "File:", new_x=XPos.RIGHT, new_y=YPos.TOP, align='L', fill=True)
            self.set_font('Helvetica', '', 10)
            self.set_fill_color(255, 255, 255)
            self.cell(0, 6, self.safe_text(hotspot_data['file'][:80]), 
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
            
            # Line
            self.set_x(self.l_margin)
            self.set_font('Helvetica', 'B', 10)
            self.set_fill_color(240, 240, 240)
            self.cell(30, 6, "Line:", new_x=XPos.RIGHT, new_y=YPos.TOP, align='L', fill=True)
            self.set_font('Helvetica', '', 10)
            self.set_fill_color(255, 255, 255)
            self.cell(0, 6, str(hotspot_data['line']), 
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
            
            # Creation date
            if hotspot_data.get('creation_date'):
                self.set_x(self.l_margin)
                self.set_font('Helvetica', 'B', 10)
                self.set_fill_color(240, 240, 240)
                self.cell(30, 6, "Created:", new_x=XPos.RIGHT, new_y=YPos.TOP, align='L', fill=True)
                self.set_font('Helvetica', '', 10)
                self.set_fill_color(255, 255, 255)
                self.cell(0, 6, hotspot_data['creation_date'][:10], 
                          new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
            
            # Rule
            if hotspot_data.get('rule_key'):
                self.set_x(self.l_margin)
                self.set_font('Helvetica', 'B', 10)
                self.set_fill_color(240, 240, 240)
                self.cell(30, 6, "Rule:", new_x=XPos.RIGHT, new_y=YPos.TOP, align='L', fill=True)
                self.set_font('Helvetica', '', 10)
                self.set_fill_color(255, 255, 255)
                self.cell(0, 6, self.safe_text(hotspot_data['rule_key'][:80]), 
                          new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
            
            # Comments
            if hotspot_data.get('comments') and len(hotspot_data['comments']) > 0:
                self.ln(2)
                self.set_x(self.l_margin)
                self.set_font('Helvetica', 'B', 9)
                self.set_text_color(0, 102, 204)
                self.cell(0, 5, "Comments:", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
                self.set_font('Helvetica', '', 9)
                self.set_text_color(50, 50, 50)
                for comment in hotspot_data['comments'][:2]:
                    comment_text = comment.get('text', '')[:60]
                    if comment_text:
                        comment_user = comment.get('user', 'Unknown')
                        self.set_x(self.l_margin + 5)
                        self.multi_cell(0, 4, self.safe_text(f"- {comment_user}: {comment_text}"),
                                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                
                if len(hotspot_data['comments']) > 2:
                    self.set_x(self.l_margin + 5)
                    self.cell(0, 4, self.safe_text(f"... and {len(hotspot_data['comments']) - 2} more comments"), 
                             new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
            
            self.ln(3)
            
            # Code snippet
            self.set_x(self.l_margin)
            self.set_font('Helvetica', 'B', 11)
            self.set_text_color(0, 102, 204)
            self.cell(0, 7, "CODE SNIPPET:", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
            self.set_text_color(50, 50, 50)
            
            self.set_font('Courier', '', 9)
            self.set_fill_color(245, 245, 245)
            
            for line in hotspot_data['code_snippet']:
                line_num = str(line['line'])
                code = line['code'][:60]
                try:
                    self.set_x(self.l_margin)
                    if int(line['line']) == hotspot_data['line']:
                        self.set_fill_color(255, 200, 200)
                        self.set_text_color(200, 0, 0)
                    else:
                        self.set_fill_color(245, 245, 245)
                        self.set_text_color(50, 50, 50)
                        
                    self.cell(15, 5, line_num, new_x=XPos.RIGHT, new_y=YPos.TOP, align='R', fill=True)
                    self.cell(0, 5, " " + self.safe_text(code), new_x=XPos.LMARGIN, new_y=YPos.NEXT, 
                             align='L', fill=True)
                except Exception:
                    continue
            
            self.set_text_color(50, 50, 50)
            self.set_fill_color(255, 255, 255)
            self.ln(5)
            
        except Exception as e:
            print(f"  PDF generation error: {str(e)}")
            raise e

# =========================
# Helper Functions
# =========================

def clean_code(html_code):
    """Clean HTML code by removing tags and non-printable characters"""
    text = re.sub('<.*?>', '', html_code)
    text = ''.join(char for char in text if ord(char) >= 32 or char == '\n')
    return text

def login_to_sonarqube(base_url, username, password):
    """Simple login function"""
    session = requests.Session()
    login_url = f"{base_url}/api/authentication/login"
    login_data = {'login': username, 'password': password}
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    
    try:
        response = session.post(login_url, data=login_data, headers=headers)
        if response.status_code == 200:
            print("Login successful!")
            return session
        else:
            print(f"Login failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"Login error: {str(e)}")
        return None

def get_available_projects(session, base_url):
    """Fetch list of available projects from SonarQube"""
    try:
        projects_url = f"{base_url}/api/projects/search?ps=500"
        response = session.get(projects_url)
        if response.status_code == 200:
            data = response.json()
            projects = data.get('components', [])
            return projects
        else:
            print(f"Failed to fetch projects: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error fetching projects: {str(e)}")
        return []

def validate_project_key(session, base_url, project_key):
    """Validate if the project key exists in SonarQube"""
    try:
        encoded_key = urllib.parse.quote(project_key, safe='')
        validate_url = f"{base_url}/api/projects/search?projects={encoded_key}"
        response = session.get(validate_url)
        
        if response.status_code == 200:
            data = response.json()
            components = data.get('components', [])
            if components:
                actual_key = components[0].get('key', project_key)
                print(f"Project validated: {actual_key}")
                return actual_key
        return None
    except Exception as e:
        print(f"Error validating project: {str(e)}")
        return None

def get_hotspot_details(session, base_url, hotspot_key):
    """Fetch detailed hotspot information including status and resolution"""
    try:
        hotspot_details_url = f"{base_url}/api/hotspots/show?hotspot={hotspot_key}"
        response = session.get(hotspot_details_url)
        
        if response.status_code == 200:
            data = response.json()
            
            status = data.get("status", "UNKNOWN")
            resolution = data.get("resolution", "NONE")
            comments = data.get("comments", [])
            
            assignee = "Unassigned"
            if data.get("assignee"):
                assignee = data["assignee"].get("name", "Unassigned")
            
            creation_date = data.get("creationDate", "")
            
            return {
                'status': status,
                'resolution': resolution if resolution else "NONE",
                'comments': comments,
                'assignee': assignee,
                'creation_date': creation_date
            }
        else:
            return {
                'status': 'UNKNOWN',
                'resolution': 'NONE',
                'comments': [],
                'assignee': 'Unassigned',
                'creation_date': ''
            }
    except Exception as e:
        print(f"  Error fetching hotspot details: {str(e)}")
        return {
            'status': 'ERROR',
            'resolution': 'NONE',
            'comments': [],
            'assignee': 'Unassigned',
            'creation_date': ''
        }

# =========================
# Main Program
# =========================

def main():
    print("\n" + "="*60)
    print("SONARQUBE SECURITY HOTSPOTS REPORT GENERATOR v2.4 by AS")
    print("="*60)
    print("Enhanced version with Executive Summary and Client Information")
    
    print("\n" + "-"*30)
    print("YOUR COMPANY INFORMATION")
    print("-"*30)
    global COMPANY_NAME
    company_name = input("Your Company Name: ").strip()
    if not company_name:
        company_name = "COMMTEL"
    COMPANY_NAME = company_name.upper()
    
    print("\n" + "-"*30)
    print("CLIENT INFORMATION")
    print("-"*30)
    global CLIENT_NAME, PROJECT_NAME, ASSET_TYPE
    
    CLIENT_NAME = input("Client Name: ").strip()
    if not CLIENT_NAME:
        CLIENT_NAME = "CLIENT"
    
    PROJECT_NAME = input("Project Name: ").strip()
    if not PROJECT_NAME:
        PROJECT_NAME = "PROJECT"
    
    print("\nAsset Type (Select one):")
    print("  1. Web Application")
    print("  2. Mobile Application")
    print("  3. API")
    print("  4. Desktop Application")
    print("  5. Cloud Service")
    print("  6. Other")
    
    asset_choice = input("Enter choice (1-6) [1]: ").strip() or "1"
    
    asset_types = {
        "1": "Web Application",
        "2": "Mobile Application",
        "3": "API",
        "4": "Desktop Application",
        "5": "Cloud Service",
        "6": "Other"
    }
    
    ASSET_TYPE = asset_types.get(asset_choice, "Web Application")
    
    if asset_choice == "6":
        custom_asset = input("Enter custom asset type: ").strip()
        if custom_asset:
            ASSET_TYPE = custom_asset
    
    sonar_url = input("\nSonarQube URL [http://localhost:9000]: ").strip()
    if not sonar_url:
        sonar_url = "http://localhost:9000"
    sonar_url = sonar_url.rstrip('/')
    
    print("\n" + "-"*30)
    print("LOGIN CREDENTIALS")
    print("-"*30)
    username = input("Username: ").strip()
    password = getpass.getpass("Password: ")
    
    session = login_to_sonarqube(sonar_url, username, password)
    if not session:
        print("Exiting due to login failure.")
        return
    
    print("\n" + "-"*30)
    print("PROJECT INFORMATION")
    print("-"*30)
    
    list_projects = input("List available projects? (y/n) [n]: ").strip().lower()
    if list_projects == 'y':
        print("\nFetching available projects...")
        projects = get_available_projects(session, sonar_url)
        if projects:
            print(f"\nFound {len(projects)} projects:")
            for i, project in enumerate(projects[:20], 1):
                print(f"  {i}. {project.get('name')} (Key: {project.get('key')})")
            if len(projects) > 20:
                print(f"  ... and {len(projects) - 20} more")
        else:
            print("No projects found or unable to fetch projects.")
    
    print("\nEnter the exact Project Key/ID (case-sensitive)")
    print("You can find this in the SonarQube UI under Project Information)")
    project_key_input = input("Project Key/ID: ").strip()
    
    if not project_key_input:
        print("Project key is required. Exiting.")
        return
    
    project_key_input = project_key_input.strip('"\'')
    
    print(f"\nValidating project key: {project_key_input}")
    actual_project_key = validate_project_key(session, sonar_url, project_key_input)
    
    if not actual_project_key:
        print(f"\nProject key '{project_key_input}' not found in SonarQube.")
        
        print("\nSearching for similar projects...")
        projects = get_available_projects(session, sonar_url)
        similar = []
        for project in projects:
            if project_key_input.lower() in project.get('key', '').lower() or \
               project_key_input.lower() in project.get('name', '').lower():
                similar.append(project)
        
        if similar:
            print("\nSimilar projects found:")
            for i, project in enumerate(similar, 1):
                print(f"  {i}. Name: {project.get('name')}")
                print(f"     Key: {project.get('key')}")
            
            use_similar = input("\nUse one of these? Enter number or press Enter to exit: ").strip()
            if use_similar.isdigit() and 1 <= int(use_similar) <= len(similar):
                actual_project_key = similar[int(use_similar)-1].get('key')
                print(f"Using project key: {actual_project_key}")
            else:
                print("Exiting.")
                return
        else:
            print("No similar projects found.")
            return
    
    global PROJECT_KEY
    PROJECT_KEY = actual_project_key
    
    print(f"\nFetching hotspots for project: {PROJECT_KEY}...")
    hotspot_api = f"{sonar_url}/api/hotspots/search?projectKey={urllib.parse.quote(PROJECT_KEY, safe='')}&ps=500"
    
    try:
        response = session.get(hotspot_api)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching hotspots: {str(e)}")
        return
    
    data = response.json()
    hotspots = data.get("hotspots", [])
    
    print(f"Found {len(hotspots)} hotspots\n")
    
    # Initialize PDF
    pdf = SonarQubePDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Generate filename
    clean_project_key = re.sub(r'[^\w\-_]', '_', PROJECT_KEY)
    clean_client_name = re.sub(r'[^\w\-_]', '_', CLIENT_NAME)
    pdf_filename = (
        f"{COMPANY_NAME}_Review_Report_{clean_client_name}_"
        f"{clean_project_key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    )
    
    # Add title page
    pdf.title_page()
    
    if len(hotspots) == 0:
        print("No hotspots found. Generating report with 'no vulnerabilities' message.")
        pdf.no_vulnerabilities_page()
        pdf.output(pdf_filename)
        
        print(f"\n{'='*70}")
        print(f"PDF REPORT GENERATED SUCCESSFULLY!")
        print(f"Filename: {pdf_filename}")
        print(f"Status: NO VULNERABILITIES FOUND")
        print(f"{'='*70}\n")
        return
    
    all_hotspot_data = []
    successful = 0
    failed = 0
    
    print("Processing hotspots (this may take a moment)...")
    
    for i, hotspot in enumerate(hotspots, 1):
        try:
            hotspot_key = hotspot.get("key")
            component = hotspot.get("component")
            line = hotspot.get("line", 1)
            security_category = hotspot.get("securityCategory", "Unknown")
            
            print(f"  Processing {i}/{len(hotspots)}: {hotspot_key[-8:]}...", end="", flush=True)
            
            hotspot_details = get_hotspot_details(session, sonar_url, hotspot_key)
            status = hotspot_details['status']
            resolution = hotspot_details['resolution']
            assignee = hotspot_details['assignee']
            creation_date = hotspot_details['creation_date']
            comments = hotspot_details['comments']
            
            rule_api = f"{sonar_url}/api/hotspots/show?hotspot={hotspot_key}"
            rule_resp = session.get(rule_api)
            
            rule_key = ""
            severity = ""
            name = ""
            message = ""
            vulnerability_prob = ""
            
            if rule_resp.status_code == 200:
                rule_data = rule_resp.json()
                rule = rule_data.get("rule", {})
                message = rule_data.get("message", "")
                rule_key = rule.get("key", "")
                severity = rule.get("severity", "")
                name = rule.get("name", "")
                
                vulnerability_prob = rule.get("vulnerabilityProbability", "")
                if not vulnerability_prob:
                    vulnerability_prob = hotspot.get("vulnerabilityProbability", "")
                if not vulnerability_prob:
                    vulnerability_prob = severity
            
            start = max(1, line - 5)
            end = line + 5
            encoded_file = urllib.parse.quote(component, safe="")
            code_api = f"{sonar_url}/api/sources/lines?key={encoded_file}&from={start}&to={end}"
            code_resp = session.get(code_api)
            
            code_snippet = []
            if code_resp.status_code == 200:
                code_data = code_resp.json()
                for source in code_data.get("sources", []):
                    clean_line = clean_code(source["code"])
                    if clean_line.strip():
                        code_snippet.append({
                            'line': source['line'],
                            'code': clean_line
                        })
            
            hotspot_data = {
                'key': hotspot_key,
                'file': component,
                'line': line,
                'status': status,
                'resolution': resolution,
                'assignee': assignee,
                'creation_date': creation_date,
                'rule_key': rule_key,
                'severity': severity,
                'vulnerability_probability': vulnerability_prob,
                'security_category': security_category,
                'name': name,
                'message': message,
                'code_snippet': code_snippet,
                'comments': comments
            }
            
            all_hotspot_data.append(hotspot_data)
            successful += 1
            
            status_display = f"{status}"
            if resolution != 'NONE':
                status_display += f" (Resolution: {resolution})"
            print(f" OK - {status_display}")
                
        except Exception as e:
            print(f" ERROR: {str(e)}")
            failed += 1
    
    # Add Executive Summary page
    pdf.executive_summary(all_hotspot_data)
    
    # Add summary pages
    if successful > 0:
        severity_counts = Counter()
        status_counts = Counter()
        resolution_counts = Counter()
        
        for data in all_hotspot_data:
            severity_counts[data.get('vulnerability_probability', 'UNKNOWN')] += 1
            status_counts[data.get('status', 'UNKNOWN')] += 1
            resolution = data.get('resolution', 'NONE')
            if resolution != 'NONE':
                resolution_counts[resolution] += 1
        
        pdf.summary_table(all_hotspot_data)
        pdf.severity_chart(severity_counts)
        
        for i, hotspot_data in enumerate(all_hotspot_data, 1):
            try:
                pdf.add_page()
                pdf.set_font('Helvetica', 'B', 10)
                pdf.set_text_color(100, 100, 100)
                pdf.set_x(pdf.l_margin)
                pdf.cell(0, 5, f"Hotspot {i} of {successful}", 
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='R')
                pdf.ln(2)
                pdf.hotspot_section(hotspot_data)
            except Exception as e:
                print(f"Error adding hotspot {i} to PDF: {str(e)}")
    
    # Save PDF
    try:
        pdf.output(pdf_filename)
        print(f"\n{'='*70}")
        print(f"PDF REPORT GENERATED SUCCESSFULLY!")
        print(f"Filename: {pdf_filename}")
        print(f"Total Hotspots: {len(hotspots)}")
        print(f"Successfully Processed: {successful}")
        print(f"Failed: {failed}")
        
        if successful > 0:
            print(f"\nStatus Summary:")
            for status in ['REVIEWED', 'TO_REVIEW', 'UNKNOWN']:
                count = status_counts.get(status, 0)
                if count > 0:
                    percentage = (count / successful * 100)
                    print(f"  {status}: {count} ({percentage:.1f}%)")
            
            if resolution_counts:
                print(f"\nResolution Breakdown:")
                for resolution in ['SAFE', 'FIXED', 'ACKNOWLEDGED']:
                    count = resolution_counts.get(resolution, 0)
                    if count > 0:
                        percentage = (count / successful * 100)
                        print(f"  {resolution}: {count} ({percentage:.1f}%)")
        
        print(f"\nReport Summary:")
        print(f"  Your Company: {COMPANY_NAME}")
        print(f"  Client: {CLIENT_NAME}")
        print(f"  Project: {PROJECT_NAME}")
        print(f"  Asset Type: {ASSET_TYPE}")
        print(f"  SonarQube Project: {PROJECT_KEY}")
        print(f"{'='*70}\n")
        
    except Exception as e:
        print(f"Error saving PDF: {str(e)}")

if __name__ == "__main__":
    main()
