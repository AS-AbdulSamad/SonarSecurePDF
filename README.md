# SonarSecurePDF 🛡️

**Automatically generate professional PDF security reports from SonarQube security hotspots.**

![Python Version](https://img.shields.io/badge/python-3.6%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)

---

# 📋 Table of Contents

* Features
* Requirements
* Installation
* Usage Guide
* Adding Your Logo
* Report Structure
* Troubleshooting
* FAQ
* Contributing
* License

---

# ✨ Features

| Feature                     | Description                                            |
| --------------------------- | ------------------------------------------------------ |
| 🔐 Auto-login               | No manual token copying – just enter username/password |
| 📊 Professional PDF Reports | Title page, summaries, charts, and detailed findings   |
| 🎨 Color-coded Severities   | HIGH (red), MEDIUM (orange), LOW (green)               |
| 🔍 Code Snippets            | Vulnerable lines highlighted in red                    |
| 🖼️ Company Logo            | Automatically adds your logo to reports                |
| 📈 Summary Statistics       | Tables and charts for quick overview                   |
| 🛡️ Zero Vulnerabilities    | Clean report when no issues found                      |
| 📱 Interactive Prompts      | Simple step-by-step guided process                     |

---

# 📦 Requirements

## Minimum Requirements

* **Python**: Version 3.6 or higher
* **SonarQube**: Server version 7.9+ (local or remote)
* **Memory**: 512MB RAM minimum
* **Disk Space**: 100MB for reports

---

## Python Packages

```
requests
fpdf2
```

---

## Check Your Python Version

```bash
python --version
```

---

# 🚀 Installation

## Step 1: Install Python

Download and install Python from:

https://www.python.org/downloads/

---

## Step 2: Run the following commands

```bash
git clone https://github.com/AS-AbdulSamad/SonarSecurePDF.git
mkdir sonar-reports
cd sonar-reports
pip install -r requirements.txt
# if this will not work, run the following
python -m pip install requests fpdf2
```
---

## Step 3: Verify Installation

```bash
python sonarsecurepdf.py
```

If everything is installed correctly, the script will start asking for:

* SonarQube URL
* Username
* Password / Token
* Project Key

---

# 📖 Usage Guide

Run the script:

```bash
python sonarsecurepdf.py
```

You will be prompted to enter:

```
SonarQube URL:
Username:
Password or Token:
Project Key:
```

The script will then:

1. Connect to SonarQube API
2. Fetch Security Hotspots
3. Extract:

   * Vulnerable code
   * File name
   * Line number
   * Severity
4. Generate a **professional PDF report**

---

# 🖼️ Adding Your Logo

To add your company logo to reports:

1. Place your logo file in the project folder.

Example:

```
logo.png
```

2. The script will automatically detect and add it to the report header.

Supported formats:

```
PNG
JPG
JPEG
```

---

# 📑 Report Structure

Generated reports include:

### 1️⃣ Cover Page

* Report Title
* Project Name
* Date
* Company Logo

### 2️⃣ Executive Summary

* Total Vulnerabilities
* Severity Distribution
* Quick overview

### 3️⃣ Statistics Section

Tables showing:

| Severity | Count |
| -------- | ----- |
| High     | X     |
| Medium   | X     |
| Low      | X     |

### 4️⃣ Detailed Findings

Each finding includes:

```
Finding ID
Severity
File Name
Line Number
Description
Code Snippet
Recommendation
```

Vulnerable code lines are highlighted in **red**.

---

# 🛠 Troubleshooting

## Problem: Module Not Found

```
ModuleNotFoundError: requests
```

Solution:

```bash
pip install requests
```

---

## Problem: Cannot Connect to SonarQube

Check:

* SonarQube server is running
* URL is correct
* Firewall is not blocking port **9000**

Example:

```
http://localhost:9000
```

---

## Problem: Unauthorized Error

Use a **SonarQube Token** instead of password.

Generate token:

```
SonarQube → My Account → Security → Generate Token
```

---

# ❓ FAQ

### Does this work with SonarQube Community Edition?

Yes, but **Security Hotspots API may be limited**.

---

### Can this scan multiple projects?

Yes. Run the script multiple times with different **Project Keys**.

---

### Can I customize the report?

Yes. Modify:

```
sonarsecurepdf.py
```

to add:

* More charts
* Additional metadata
* Custom branding

---

# 🤝 Contributing

Contributions are welcome!

You can contribute by:

* Improving PDF layout
* Adding more SonarQube API integrations
* Adding charts and graphs
* Supporting additional vulnerability types

Steps:

```
Fork the repository
Create a new branch
Submit a Pull Request
```

---

# 📄 License

This project is licensed under the **MIT License**.

You are free to:

* Use
* Modify
* Distribute

---

# ⭐ Support

If you find this project helpful, please consider:

⭐ Starring the repository
🐛 Reporting issues
🚀 Contributing improvements

---

**Built for Security Engineers & Pentesters**
