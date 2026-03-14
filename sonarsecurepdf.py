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
            
            # Add header title with company name
            self.set_font('Helvetica', 'B', 12)
            self.set_text_color(0, 102, 204)
            self.cell(0, 10, f'{COMPANY_NAME} SOURCE CODE REVIEW REPORT', 
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
            
            # Add project info
            self.set_font('Helvetica', '', 8)
            self.set_text_color(100, 100, 100)
            self.cell(0, 4, f'Project: {PROJECT_KEY} | Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 
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
    
    def title_page(self):
        """Create a title page"""
        self.add_page()
        
        # Center vertically
        self.set_y(80)
        
        # Add logo (larger on title page)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(script_dir, "logo.png")
        if os.path.exists(logo_path):
            self.image(logo_path, x=80, y=40, w=50)
            self.set_y(95)
        
        # Main title with company name
        self.set_font('Helvetica', 'B', 28)
        self.set_text_color(0, 102, 204)
        self.cell(0, 20, COMPANY_NAME, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
        
        self.set_font('Helvetica', 'B', 24)
        self.set_text_color(50, 50, 50)
        self.cell(0, 15, 'Source Code Review Report', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
        
        self.ln(20)
        
        # Project info
        self.set_font('Helvetica', '', 14)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, f'Project: {PROJECT_KEY}', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
        self.cell(0, 10, f'Date: {datetime.now().strftime("%B %d, %Y")}', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
        self.cell(0, 10, f'Time: {datetime.now().strftime("%H:%M:%S")}', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
        
        self.ln(20)
        
        # Confidential stamp
        self.set_font('Helvetica', 'I', 12)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, 'CONFIDENTIAL', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    
    def summary_table(self, hotspots_data):
        """Create a summary table with vulnerability statistics"""
        self.add_page()
        
        # Section title
        self.set_font('Helvetica', 'B', 18)
        self.set_text_color(0, 102, 204)
        self.cell(0, 15, 'Vulnerability Summary', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        self.ln(5)
        
        # Calculate statistics
        total_vulns = len(hotspots_data)
        severity_counts = Counter()
        category_counts = Counter()
        
        for data in hotspots_data:
            severity = data.get('vulnerability_probability', 'UNKNOWN')
            category = data.get('security_category', 'Unknown')
            severity_counts[severity] += 1
            category_counts[category] += 1
        
        # Overall stats
        self.set_font('Helvetica', 'B', 12)
        self.set_text_color(50, 50, 50)
        self.cell(0, 8, f'Total Vulnerabilities Found: {total_vulns}', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        self.ln(5)
        
        # Severity breakdown table
        self.set_font('Helvetica', 'B', 11)
        self.set_fill_color(240, 248, 255)
        self.cell(90, 10, 'Vulnerability Probability', border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C', fill=True)
        self.cell(90, 10, 'Count', border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C', fill=True)
        
        self.set_font('Helvetica', '', 10)
        self.set_fill_color(255, 255, 255)
        
        for severity in ['HIGH', 'MEDIUM', 'LOW']:
            count = severity_counts.get(severity, 0)
            
            # Color-code severity text
            if severity == 'HIGH':
                self.set_text_color(255, 0, 0)
            elif severity == 'MEDIUM':
                self.set_text_color(255, 165, 0)
            else:
                self.set_text_color(0, 128, 0)
            
            self.cell(90, 8, severity, border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C')
            self.set_text_color(50, 50, 50)  # Reset for count
            self.cell(90, 8, str(count), border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
        
        # Add any other severities
        other_severities = [s for s in severity_counts.keys() if s not in ['HIGH', 'MEDIUM', 'LOW']]
        for severity in other_severities:
            self.cell(90, 8, severity, border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C')
            self.cell(90, 8, str(severity_counts[severity]), border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
        
        self.ln(10)
        
        # Top categories table
        self.set_font('Helvetica', 'B', 11)
        self.set_fill_color(240, 248, 255)
        self.cell(90, 10, 'Security Category', border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C', fill=True)
        self.cell(90, 10, 'Count', border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C', fill=True)
        
        self.set_font('Helvetica', '', 10)
        self.set_fill_color(255, 255, 255)
        
        # Show top 10 categories
        for category, count in category_counts.most_common(10):
            self.cell(90, 8, category[:40], border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='L')
            self.cell(90, 8, str(count), border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    
    def severity_chart(self, severity_counts):
        """Create a simple bar chart for severity distribution"""
        self.add_page()
        
        # Section title
        self.set_font('Helvetica', 'B', 18)
        self.set_text_color(0, 102, 204)
        self.cell(0, 15, 'Vulnerability Distribution', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        self.ln(10)
        
        # Chart title
        self.set_font('Helvetica', 'B', 12)
        self.set_text_color(50, 50, 50)
        self.cell(0, 8, 'Probability Distribution', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
        self.ln(5)
        
        # Find max count for scaling
        max_count = max(severity_counts.values()) if severity_counts else 1
        
        # Bar chart
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
            
            # Draw bar
            self.set_fill_color(*colors[i])
            self.rect(x, y, bar_width, bar_height, style='F')
            
            # Add count label
            self.set_xy(x, y - 5)
            self.set_font('Helvetica', 'B', 10)
            self.set_text_color(*colors[i])
            self.cell(bar_width, 5, str(count), new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
            
            # Add severity label
            self.set_xy(x, chart_start_y + 55)
            self.set_font('Helvetica', '', 10)
            self.set_text_color(50, 50, 50)
            self.cell(bar_width, 5, severity, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
        
        self.ln(30)
        
        # Add a simple pie chart representation
        self.set_font('Helvetica', 'B', 12)
        self.set_text_color(50, 50, 50)
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
                self.cell(0, 6, f'{severity}: {percentage:.1f}% ({count})', 
                         new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
    
    def safe_multi_cell(self, w, h, txt, border=0, align='L', fill=False):
        """Safely handle multi_cell with text wrapping"""
        if not txt or txt.isspace():
            return
        
        txt = str(txt).encode('ascii', 'ignore').decode('ascii')
        available_width = w if w > 0 else (self.w - self.l_margin - self.r_margin)
        char_width = self.get_string_width('a')
        max_chars = int(available_width / char_width) - 5
        
        if max_chars > 0 and len(txt) > max_chars:
            lines = textwrap.wrap(txt, width=max_chars)
            for line in lines:
                try:
                    self.multi_cell(w, h, line, border=border, 
                                  new_x=XPos.LMARGIN, new_y=YPos.NEXT, 
                                  align=align, fill=fill)
                except:
                    self.cell(w, h, line[:50] + "...", 
                            new_x=XPos.LMARGIN, new_y=YPos.NEXT, align=align)
        else:
            try:
                self.multi_cell(w, h, txt, border=border, 
                              new_x=XPos.LMARGIN, new_y=YPos.NEXT, 
                              align=align, fill=fill)
            except:
                self.cell(w, h, txt[:80] + "...", 
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT, align=align)
    
    def no_vulnerabilities_page(self):
        """Add a page indicating no vulnerabilities found"""
        self.add_page()
        
        # Add a success message (without special characters)
        self.set_y(120)
        self.set_font('Helvetica', 'B', 24)
        self.set_text_color(0, 128, 0)  # Green
        self.cell(0, 20, 'NO VULNERABILITIES FOUND', 
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
        
        self.set_font('Helvetica', '', 14)
        self.set_text_color(100, 100, 100)
        self.cell(0, 15, 'The security scan did not detect any hotspots or vulnerabilities.', 
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
        
        self.set_font('Helvetica', '', 12)
        self.cell(0, 10, 'Your code appears to be secure.', 
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    
    def hotspot_section(self, hotspot_data):
        try:
            # Hotspot Key with background (smaller, less prominent)
            self.set_fill_color(240, 248, 255)
            self.set_font('Helvetica', 'I', 8)
            self.set_text_color(100, 100, 100)
            self.cell(0, 5, f"ID: {hotspot_data['key'][:20]}...", 
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L', fill=True)
            self.ln(2)
            
            # Name - Highlighted and Bold (now on top)
            self.set_fill_color(255, 255, 200)  # Light yellow background
            self.set_font('Helvetica', 'B', 14)
            self.set_text_color(0, 0, 0)
            self.cell(0, 10, hotspot_data['name'][:80], 
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L', fill=True)
            self.ln(2)
            
            # Message
            if hotspot_data.get('message'):
                self.set_font('Helvetica', 'B', 10)
                self.set_fill_color(240, 240, 240)
                self.cell(30, 6, "Message:", new_x=XPos.RIGHT, new_y=YPos.TOP, align='L', fill=True)
                self.set_font('Helvetica', '', 10)
                self.set_fill_color(255, 255, 255)
                self.safe_multi_cell(0, 6, hotspot_data['message'])
            
            # Security Category
            self.set_font('Helvetica', 'B', 10)
            self.set_fill_color(240, 240, 240)
            self.cell(30, 6, "Category:", new_x=XPos.RIGHT, new_y=YPos.TOP, align='L', fill=True)
            self.set_font('Helvetica', '', 10)
            self.set_fill_color(255, 255, 255)
            self.cell(0, 6, hotspot_data['security_category'][:60], 
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
            
            # Vulnerability Probability (severity) - Color coded
            vulnerability_prob = hotspot_data.get('vulnerability_probability', 'UNKNOWN')
            
            self.set_font('Helvetica', 'B', 10)
            self.set_fill_color(240, 240, 240)
            self.cell(30, 6, "Probability:", new_x=XPos.RIGHT, new_y=YPos.TOP, align='L', fill=True)
            self.set_font('Helvetica', 'B', 10)
            
            # Color-code probability
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
            
            # File
            self.set_font('Helvetica', 'B', 10)
            self.set_fill_color(240, 240, 240)
            self.cell(30, 6, "File:", new_x=XPos.RIGHT, new_y=YPos.TOP, align='L', fill=True)
            self.set_font('Helvetica', '', 10)
            self.set_fill_color(255, 255, 255)
            self.cell(0, 6, hotspot_data['file'][:80], 
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
            
            # Line
            self.set_font('Helvetica', 'B', 10)
            self.set_fill_color(240, 240, 240)
            self.cell(30, 6, "Line:", new_x=XPos.RIGHT, new_y=YPos.TOP, align='L', fill=True)
            self.set_font('Helvetica', '', 10)
            self.set_fill_color(255, 255, 255)
            self.cell(0, 6, str(hotspot_data['line']), 
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
            
            # Rule (optional, can be included if needed)
            if hotspot_data.get('rule_key'):
                self.set_font('Helvetica', 'B', 10)
                self.set_fill_color(240, 240, 240)
                self.cell(30, 6, "Rule:", new_x=XPos.RIGHT, new_y=YPos.TOP, align='L', fill=True)
                self.set_font('Helvetica', '', 10)
                self.set_fill_color(255, 255, 255)
                self.cell(0, 6, hotspot_data['rule_key'][:80], 
                          new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
            
            # Status
            self.set_font('Helvetica', 'B', 10)
            self.set_fill_color(240, 240, 240)
            self.cell(30, 6, "Status:", new_x=XPos.RIGHT, new_y=YPos.TOP, align='L', fill=True)
            self.set_font('Helvetica', '', 10)
            self.set_fill_color(255, 255, 255)
            self.cell(0, 6, hotspot_data['status'], 
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
            
            self.ln(3)
            
            # Code snippet
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
                    if int(line['line']) == hotspot_data['line']:
                        self.set_fill_color(255, 200, 200)
                        self.set_text_color(200, 0, 0)
                    else:
                        self.set_fill_color(245, 245, 245)
                        self.set_text_color(50, 50, 50)
                        
                    self.cell(15, 5, line_num, new_x=XPos.RIGHT, new_y=YPos.TOP, align='R', fill=True)
                    self.cell(0, 5, " " + code, new_x=XPos.LMARGIN, new_y=YPos.NEXT, 
                             align='L', fill=True)
                except:
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
            print("✓ Login successful!")
            return session
        else:
            print(f"✗ Login failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"✗ Login error: {str(e)}")
        return None

# =========================
# Main Program
# =========================

def main():
    print("\n" + "="*60)
    print("SONARQUBE SECURITY HOTSPOTS REPORT GENERATOR v1.1 by AS")
    print("="*60)
    
    # Get Company Name
    print("\n" + "-"*30)
    print("COMPANY INFORMATION")
    print("-"*30)
    global COMPANY_NAME
    company_name = input("Company Name: ").strip()
    if not company_name:
        company_name = "COMMTEL"  # Default fallback
    COMPANY_NAME = company_name.upper()
    
    # Get SonarQube URL
    sonar_url = input("\nSonarQube URL [http://localhost:9000]: ").strip()
    if not sonar_url:
        sonar_url = "http://localhost:9000"
    
    # Get credentials
    print("\n" + "-"*30)
    print("LOGIN CREDENTIALS")
    print("-"*30)
    username = input("Username: ").strip()
    password = getpass.getpass("Password: ")
    
    # Login
    session = login_to_sonarqube(sonar_url, username, password)
    if not session:
        print("Exiting due to login failure.")
        return
    
    # Get project key
    print("\n" + "-"*30)
    print("PROJECT INFORMATION")
    print("-"*30)
    global PROJECT_KEY
    project_key = input("Project Key/ID: ").strip()
    
    if not project_key:
        print("Project key is required. Exiting.")
        return
    
    PROJECT_KEY = project_key
    
    # Fetch hotspots
    print(f"\nFetching hotspots for project: {project_key}...")
    hotspot_api = f"{sonar_url}/api/hotspots/search?projectKey={project_key}&ps=500"
    
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
    pdf_filename = f"{COMPANY_NAME}_Review_Report_{project_key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    # Add title page
    pdf.title_page()
    
    if len(hotspots) == 0:
        print("No hotspots found. Generating report with 'no vulnerabilities' message.")
        pdf.no_vulnerabilities_page()
        pdf.output(pdf_filename)
        
        print(f"\n{'='*70}")
        print(f"✅ PDF REPORT GENERATED SUCCESSFULLY!")
        print(f"Filename: {pdf_filename}")
        print(f"Status: NO VULNERABILITIES FOUND")
        print(f"{'='*70}\n")
        return
    
    # Collect all hotspot data for summary
    all_hotspot_data = []
    
    # Process hotspots
    successful = 0
    failed = 0
    
    for i, hotspot in enumerate(hotspots, 1):
        try:
            hotspot_key = hotspot.get("key")
            component = hotspot.get("component")
            line = hotspot.get("line", 1)
            status = hotspot.get("status")
            security_category = hotspot.get("securityCategory", "Unknown")  # Fetch securityCategory
            
            print(f"Processing {i}/{len(hotspots)}: {hotspot_key[:8]}...")
            
            # Get rule details
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
                
                # Get vulnerability probability (use severity as fallback)
                vulnerability_prob = rule.get("vulnerabilityProbability", "")
                if not vulnerability_prob:
                    vulnerability_prob = hotspot.get("vulnerabilityProbability", "")
                if not vulnerability_prob:
                    vulnerability_prob = severity
            
            # Get code snippet
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
            
            # Prepare data for PDF and summary
            hotspot_data = {
                'key': hotspot_key,
                'file': component,
                'line': line,
                'status': status,
                'rule_key': rule_key,
                'severity': severity,
                'vulnerability_probability': vulnerability_prob,
                'security_category': security_category,  # Add security category
                'name': name,
                'message': message,
                'code_snippet': code_snippet
            }
            
            all_hotspot_data.append(hotspot_data)
            successful += 1
                
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
            failed += 1
    
    # Add summary pages
    if successful > 0:
        # Calculate severity counts for chart (using vulnerability_probability)
        severity_counts = Counter()
        for data in all_hotspot_data:
            severity_counts[data.get('vulnerability_probability', 'UNKNOWN')] += 1
        
        # Add summary table
        pdf.summary_table(all_hotspot_data)
        
        # Add severity chart
        pdf.severity_chart(severity_counts)
        
        # Add individual hotspots
        for i, hotspot_data in enumerate(all_hotspot_data, 1):
            pdf.add_page()
            pdf.hotspot_section(hotspot_data)
    
    # Save PDF
    pdf.output(pdf_filename)
    
    print(f"\n{'='*70}")
    print(f"✅ PDF REPORT GENERATED SUCCESSFULLY!")
    print(f"Filename: {pdf_filename}")
    print(f"Total Hotspots: {len(hotspots)}")
    print(f"Successful: {successful} | Failed: {failed}")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    main()