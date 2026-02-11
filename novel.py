import tkinter as tk
from tkinter import messagebox, filedialog
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from fpdf import FPDF
import threading
import time
import re
import os

class ScraperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Unicode-Safe Story Scraper")
        self.root.geometry("800x800") # Increased height slightly

        # Data Storage
        self.everything = {}

        # Control Variables
        self.is_paused = False
        self.pause_condition = threading.Event()
        self.pause_condition.set()
        
        # Variable for the save path
        self.save_path_var = tk.StringVar()
        self.save_path_var.set(os.getcwd()) # Default to current folder

        # --- UI Setup ---

        # 1. URLs
        tk.Label(root, text="Story Metadata URL:", font=('Arial', 10, 'bold')).pack(pady=5)
        self.story_url_entry = tk.Entry(root, width=90)
        self.story_url_entry.pack(pady=2)

        tk.Label(root, text="First Chapter URL:", font=('Arial', 10, 'bold')).pack(pady=5)
        self.chapter_url_entry = tk.Entry(root, width=90)
        self.chapter_url_entry.pack(pady=2)

        # 2. Save Location (NEW)
        tk.Label(root, text="Save Folder Location:", font=('Arial', 10, 'bold')).pack(pady=5)
        
        path_frame = tk.Frame(root)
        path_frame.pack(pady=2)
        
        self.path_entry = tk.Entry(path_frame, textvariable=self.save_path_var, width=75)
        self.path_entry.pack(side=tk.LEFT, padx=5)
        
        self.browse_btn = tk.Button(path_frame, text="Browse Folder", command=self.browse_folder, bg="#95a5a6", fg="white")
        self.browse_btn.pack(side=tk.LEFT)

        # 3. Action Buttons
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=15)

        self.start_btn = tk.Button(btn_frame, text="🚀 Start Full Scrape", command=self.start_thread,
                                   bg="#27ae60", fg="white", font=('Arial', 12, 'bold'), height=2, width=18)
        self.start_btn.grid(row=0, column=0, padx=5)

        self.pause_btn = tk.Button(btn_frame, text="⏸ Pause", command=self.toggle_pause,
                                   bg="#f39c12", fg="white", font=('Arial', 12, 'bold'), height=2, width=12, state='disabled')
        self.pause_btn.grid(row=0, column=1, padx=5)

        self.pdf_btn = tk.Button(btn_frame, text="📄 Make PDF", command=self.generate_pdf,
                                 bg="#e74c3c", fg="white", font=('Arial', 12, 'bold'), height=2, width=12)
        self.pdf_btn.grid(row=0, column=2, padx=5)

        # 4. Log Box
        self.log_box = tk.Text(root, height=30, width=95, state='disabled', bg="#1e1e1e", fg="#ecf0f1", wrap='word')
        self.log_box.pack(pady=10, padx=10)

    def browse_folder(self):
        """Open dialog to select a folder"""
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.save_path_var.set(folder_selected)

    def log(self, message, is_header=False):
        self.log_box.config(state='normal')
        if is_header:
            self.log_box.insert(tk.END, f"\n{'=' * 60}\n{message.upper()}\n{'=' * 60}\n")
        else:
            self.log_box.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.log_box.see(tk.END)
        self.log_box.config(state='disabled')

    def clean_text(self, text):
        """Standardizes text for PDF compatibility"""
        if not text:
            return "N/A"
        
        # Replace common unicode characters that crash PDF generation
        text = text.replace('\u2014', '--').replace('\u2013', '-')
        text = text.replace('\u201c', '"').replace('\u201d', '"')
        text = text.replace('\u2018', "'").replace('\u2019', "'")
        text = text.replace('\u2026', '...')
        text = text.replace('\n', ' ')
        text = text.replace('\xa0', ' ').replace('&nbsp;', ' ')
        
        # Final safety encoding
        return text.encode('latin-1', 'replace').decode('latin-1').strip()

    def toggle_pause(self):
        if not self.is_paused:
            self.is_paused = True
            self.pause_condition.clear()
            self.pause_btn.config(text="▶ Resume", bg="#2980b9")
            self.log("Scraping Paused...")
        else:
            self.is_paused = False
            self.pause_condition.set()
            self.pause_btn.config(text="⏸ Pause", bg="#f39c12")
            self.log("Scraping Resumed...")

    def generate_pdf(self):
        if not self.everything:
            messagebox.showwarning("Empty", "Nothing to save! Scrape some content first.")
            return

        try:
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            
            first_key = list(self.everything.keys())[0]

            for index, (key, value) in enumerate(self.everything.items()):
                pdf.add_page()
                
                safe_key = self.clean_text(key)
                safe_val = self.clean_text(value)

                if index == 0:
                    # Title Page
                    pdf.set_font("helvetica", 'B', 24)
                    pdf.multi_cell(0, 15, text=safe_key, align='C')
                    pdf.ln(10)
                    pdf.set_font("helvetica", size=12)
                    pdf.multi_cell(0, 7, text=safe_val)
                else:
                    # Chapter Page
                    pdf.set_font("helvetica", 'B', 16)
                    pdf.cell(0, 10, text=safe_key, ln=True)
                    pdf.set_font("helvetica", size=11)
                    pdf.multi_cell(0, 6, text=safe_val)

            # --- PATH LOGIC START ---
            base_path = self.save_path_var.get()
            
            # Clean title for filename/folder name usage
            safe_name = re.sub(r'[\\/*?:"<>|]', "", first_key).strip()
            safe_name = safe_name.replace(' ', '-')
            
            # Define full file path
            full_path = os.path.join(base_path, f"{safe_name}.pdf")
            # --- PATH LOGIC END ---

            pdf.output(full_path)
            
            messagebox.showinfo("Success", f"PDF Saved at:\n{full_path}")
            self.log(f"PDF Generated: {full_path}", is_header=True)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to make PDF: {str(e)}")

    def start_thread(self):
        self.start_btn.config(state='disabled')
        self.pause_btn.config(state='normal')
        t = threading.Thread(target=self.run_scraper)
        t.daemon = True
        t.start()

    def run_scraper(self):
        self.everything = {}
        story_url = self.story_url_entry.get()
        chapter_url = self.chapter_url_entry.get()

        if not story_url or not chapter_url:
            messagebox.showerror("Error", "Please provide both URLs")
            self.start_btn.config(state='normal')
            return

        driver = None
        try:
            options = Options()
            # options.add_argument("--headless")
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

            # --- METADATA ---
            self.log("Scraping Story Metadata...", is_header=True)
            driver.get(story_url)
            time.sleep(15)

            try: title = driver.find_element(By.ID, "book_name").text
            except: title = "Untitled Story"

            try: description = driver.find_element(By.ID, "description").text
            except: description = "No description."

            self.log(f"TITLE: {title}")
            self.everything[title] = description

            # --- CHAPTERS ---
            self.log("Starting Chapter Scrape...", is_header=True)
            current_url = chapter_url

            while current_url:
                self.pause_condition.wait()
                driver.get(current_url)
                time.sleep(3)

                try:
                    ch_title = driver.find_element(By.ID, 'chapter_title').text
                    ch_body = driver.find_element(By.ID, 'chapter_content').text
                    self.everything[ch_title] = ch_body

                    self.log(f"Scraped: {ch_title}\n")
                    self.log(f"Scraped: {ch_body[:200]}\n\n{'-' * 60}")

                    
                    next_link = driver.find_element(By.ID, "next-chap")
                    if 'disabled' not in next_link.get_attribute("class"):
                        current_url = next_link.get_attribute("href")
                    else:
                        self.log("--- COMPLETED ---", is_header=True)
                        current_url = False
                except NoSuchElementException:
                    self.log("End of chapters reached.")
                    current_url = None
                except Exception as e:
                    self.log(f"Chapter Error: {str(e)}")
                    current_url = None
        
        finally:
            if driver: driver.quit()
            self.start_btn.config(state='normal')
            self.pause_btn.config(state='disabled', text="⏸ Pause", bg="#f39c12")
            self.is_paused = False
            self.pause_condition.set()

if __name__ == "__main__":
    root = tk.Tk()
    app = ScraperApp(root)
    root.mainloop()