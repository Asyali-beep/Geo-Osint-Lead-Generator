# 🎯 Geo-OSINT B2B Lead Generator & Web Auditor

![Python](https://img.shields.io/badge/Python-3.x-3776AB.svg?logo=python)
![SQLite](https://img.shields.io/badge/SQLite-Database-003B57.svg?logo=sqlite)
![Threads](https://img.shields.io/badge/Concurrency-Multi--threaded-brightgreen)
![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)

An asynchronous Open-Source Intelligence (OSINT) pipeline and desktop GUI that extracts local business data via Google Maps and automatically audits their web performance using Google PageSpeed Insights. 

This tool is designed to automate B2B lead generation by identifying businesses that either lack a web presence or suffer from poor website performance (slow load times, legacy infrastructure).

## 🧠 System Architecture

The application runs on a dual-engine asynchronous architecture using Python's `threading` and `Queue` modules to ensure the GUI remains responsive while handling heavy I/O operations.

1.  **Maps Mining Engine (Producer):** Queries the Google Places API (via Serper.dev) using matrix combinations of configured Cities, Sectors, and Keywords. Extracts business names, phone numbers, addresses, and URLs.
2.  **Performance Audit Engine (Consumer):** Processes the URLs fetched by the Mining Engine. It queries the Google PageSpeed Insights API to calculate mobile performance scores and performs a lightweight footprint analysis to detect the tech stack (e.g., WordPress, Wix).
3.  **Local Persistence (SQLite):** Acts as the single source of truth. All leads are upserted dynamically to prevent data loss in case of API rate limits or network interruptions.

## 🚀 Key Features
*   **Asynchronous Processing:** Fetches and audits leads concurrently. 
*   **Tech Stack Detection:** Automatically classifies the underlying web infrastructure based on DOM and asset footprints.
*   **Automated Diagnostics:** Tags businesses as `🚨 NO WEBSITE`, `🎯 TARGET! Slow`, or `🚨 DEAD SITE` based on live network analysis.
*   **ETL Pipeline:** Provides a seamless one-click export from the SQLite database to Excel (`.xlsx`) via Pandas.

## 🛠️ Quick Start

**1. Clone and Install Dependencies**
```bash
git clone [https://github.com/Asyali-beep/Geo-Osint-Lead-Generator.git](https://github.com/Asyali-beep/Geo-Osint-Lead-Generator.git)
cd geo-osint-lead-generator
pip install requests pandas openpyxl
```

**2. Configure API Keys**
Rename `config.example.json` to `config.json` and insert your API keys for Serper.dev and Google PageSpeed.

**3. Run the Pipeline**
```bash
python lead_sniper.py
```
