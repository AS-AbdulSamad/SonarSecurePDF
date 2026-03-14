# SonarSecurePDF 🛡️
Automatically generate professional PDF security reports from SonarQube security hotspots.

## Features
* 🔐 Auto-login	No manual token copying – just enter username/password
* 📊 Professional PDF Reports	Title page, summaries, charts, and detailed findings
* 🎨 Color-coded Severities	HIGH (red), MEDIUM (orange), LOW (green)
* 🔍 Code Snippets	Vulnerable lines highlighted in red
* 🖼️ Company Logo	Automatically adds your logo to reports
* 📈 Summary Statistics	Tables and charts for quick overview
* 🛡️ Zero Vulnerabilities	Clean report when no issues found
* 📱 Interactive Prompts	Simple step-by-step guided process
* 📦 Requirements

## Minimum Requirements
* Python: Version 3.6 or higher
* SonarQube: Server version 7.9+ (local or remote)
* Memory: 512MB RAM minimum
* Disk Space: 100MB for reports

## Installation
* Step 1: Install Python
 Download and install Python from: https://www.python.org/downloads/
* Step 2: Run the following commands
```
git clone https://github.com/AS-AbdulSamad/SonarSecurePDF.git
mkdir sonar-reports
cd sonar-reports
pip install -r requirements.txt
# if this will not work, run the following
python -m pip install requests fpdf2
```
* Step 3: Run the script
```
python sonarsecurepdf.py
```
If everything is installed correctly, the script will start asking for:
SonarQube URL
Username
Password / Token
Project Key

## Adding Your Logo
To add your company logo to reports:
* Place your logo file in the project folder.
* Example:
logo.png
* The script will automatically detect and add it to the report header.

## Troubleshooting
* Problem: Module Not Found
```
ModuleNotFoundError: requests
Solution:
pip install requests
```
* Problem: Cannot Connect to SonarQube
```
Check:
SonarQube server is running
URL is correct
Firewall is not blocking port 9000
Example:
http://localhost:9000
```
* Problem: Unauthorized Error
```
Use a SonarQube Token instead of password.
Generate token:
SonarQube → My Account → Security → Generate Token
```
## FAQ
* Does this work with SonarQube Community Edition?
```
Yes, but Security Hotspots API may be limited.
```
* Can this scan multiple projects?
```
Yes. Run the script multiple times with different Project Keys.
```
* Can I customize the report?
```
Yes.
```

### Built for Security Engineers & Pentesters
