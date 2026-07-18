import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import threading
import time
import requests
import sqlite3
import pandas as pd
import os
import logging
from queue import Queue

# --- LOGGING SYSTEM ---
logging.basicConfig(
    filename="sniper_bot.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

CONFIG_FILE = "config.json"
DB_FILE = "leads_database.db"

def setup_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id TEXT PRIMARY KEY,
            business_name TEXT,
            phone TEXT,
            website TEXT,
            status TEXT,
            speed_score TEXT,
            infrastructure TEXT,
            address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

class OSINTLeadGenerator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🎯 Geo-OSINT B2B Lead Generator v2.0")
        self.geometry("1150x700")
        
        setup_database()
        self.config_data = self.load_config()
        self.is_scanning = False
        self.pagespeed_queue = Queue()

        self.setup_ui()
        self.populate_table_from_db()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"api_key": "", "pagespeed_key": "", "cities": [], "sectors": [], "variations": []}

    def setup_ui(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_scan = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_scan, text="🚀 Advanced Scanning Pipeline")

        f_control = ttk.Frame(self.tab_scan)
        f_control.pack(fill="x", padx=10, pady=10)

        self.btn_start = ttk.Button(f_control, text="▶️ Start Mining", command=self.start_pipeline)
        self.btn_start.pack(side="left", padx=5)

        self.btn_stop = ttk.Button(f_control, text="🛑 Stop", state="disabled", command=self.stop_pipeline)
        self.btn_stop.pack(side="left", padx=5)

        self.btn_export = ttk.Button(f_control, text="📂 Export to Excel", command=self.export_to_excel)
        self.btn_export.pack(side="left", padx=5)

        self.lbl_status = ttk.Label(f_control, text="Status: Ready", font=("Helvetica", 10, "bold"))
        self.lbl_status.pack(side="right", padx=10)

        f_table = ttk.Frame(self.tab_scan)
        f_table.pack(fill="both", expand=True, padx=10, pady=5)

        s_y = ttk.Scrollbar(f_table, orient="vertical")
        self.tree = ttk.Treeview(f_table, columns=("name", "phone", "site", "status", "score", "tech", "address"), 
                                 show="headings", selectmode="extended", yscrollcommand=s_y.set)
        
        s_y.config(command=self.tree.yview)
        s_y.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)

        headers = ["Business Name", "Phone", "Website", "Status / Diagnostic", "Speed Score", "Tech Stack", "Address"]
        for col, text in zip(self.tree["columns"], headers):
            self.tree.heading(col, text=text)
            self.tree.column(col, width=150)

    def populate_table_from_db(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT business_name, phone, website, status, speed_score, infrastructure, address FROM leads ORDER BY created_at DESC")
        for row in cursor.fetchall():
            self.tree.insert("", "end", values=row)
        conn.close()

    def upsert_database(self, uid, name, phone, site, status, score, tech, address):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO leads (id, business_name, phone, website, status, speed_score, infrastructure, address)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (uid, name, phone, site if site else "NONE", status, str(score), tech, address))
            conn.commit()
        except Exception as e:
            logging.error(f"SQLite Upsert Error: {e}")
        finally:
            conn.close()

    def start_pipeline(self):
        self.is_scanning = True
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        
        threading.Thread(target=self.maps_mining_engine, daemon=True).start()
        threading.Thread(target=self.pagespeed_audit_engine, daemon=True).start()

    def stop_pipeline(self):
        self.is_scanning = False
        self.lbl_status.config(text="Status: Halting operations...")
        with self.pagespeed_queue.mutex:
            self.pagespeed_queue.queue.clear()

    # --- ENGINE 1: GEO-OSINT MINER ---
    def maps_mining_engine(self):
        queries = [f"{c} {s} {v}".strip() for c in self.config_data["cities"] 
                   for s in self.config_data["sectors"] for v in self.config_data["variations"]]

        for idx, query in enumerate(queries):
            if not self.is_scanning: break
            self.lbl_status.config(text=f"Mining: {idx+1}/{len(queries)} ({query})")
            
            headers = {'X-API-KEY': self.config_data["api_key"], 'Content-Type': 'application/json'}
            try:
                res = requests.post("https://google.serper.dev/places", headers=headers, json={"q": query})
                places = res.json().get('places', [])
            except Exception as e:
                logging.error(f"Serper API Error: {e}")
                continue

            for place in places:
                if not self.is_scanning: break
                uid = place.get('cid') or place.get('title')
                name, phone = place.get('title'), place.get('phoneNumber', 'N/A')
                site, address = place.get('website'), place.get('address', 'N/A')

                if not site:
                    self.upsert_database(uid, name, phone, site, "🚨 NO WEBSITE", "N/A", "N/A", address)
                    self.tree.insert("", "end", values=(name, phone, "NONE", "🚨 NO WEBSITE", "N/A", "N/A", address))
                else:
                    self.upsert_database(uid, name, phone, site, "⏳ Auditing...", "Pending", "Analyzing", address)
                    row_id = self.tree.insert("", "end", values=(name, phone, site, "⏳ Auditing...", "Pending", "Analyzing", address))
                    self.pagespeed_queue.put((uid, row_id, site, name, phone, address))
                time.sleep(0.1)

    # --- ENGINE 2: PERFORMANCE AUDITOR ---
    def pagespeed_audit_engine(self):
        ps_key = self.config_data.get("pagespeed_key", "")
        
        while self.is_scanning or not self.pagespeed_queue.empty():
            if self.pagespeed_queue.empty():
                time.sleep(1)
                continue
            
            uid, row_id, site, name, phone, address = self.pagespeed_queue.get()
            url = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url={site}&strategy=mobile&key={ps_key}"
            
            score, status, tech = "N/A", "⚠️ Audit Failed", "Unknown"
            try:
                res = requests.get(url, timeout=90)
                if res.status_code == 200:
                    data = res.json()
                    score = int(data['lighthouseResult']['categories']['performance']['score'] * 100)
                    status = f"🎯 TARGET! Slow ({score}/100)" if score < 70 else "Fast (Good)"
                    raw_html = str(data).lower()
                    tech = "WordPress" if "wp-content" in raw_html else "Wix" if "wix.com" in raw_html else "Custom/Other"
                else:
                    status, tech = "🚨 DEAD SITE", "Offline"
            except Exception:
                pass

            self.upsert_database(uid, name, phone, site, status, score, tech, address)
            try:
                self.tree.item(row_id, values=(name, phone, site, status, score, tech, address))
            except: pass
            self.pagespeed_queue.task_done()

    def export_to_excel(self):
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
        if path:
            conn = sqlite3.connect(DB_FILE)
            df = pd.read_sql_query("SELECT * FROM leads", conn)
            df.to_excel(path, index=False)
            conn.close()

if __name__ == "__main__":
    app = OSINTLeadGenerator()
    app.mainloop()