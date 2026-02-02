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
        self.root.geometry("800x850") 

        # Data Storage
        self.everything = {}

        # Control Variables
        self.is_paused = False
        self.pause_condition = threading.Event()
        self.pause_condition.set()
        
        self.save_path_var = tk.StringVar()
        self.save_path_var.set(os.getcwd()) 

        # --- UI Setup ---
        tk.Label(root, text="Story Metadata URL:", font=('Arial', 10, 'bold')).pack(pady=5)
        self.story_url_entry = tk.Entry(root, width=90)
        self.story_url_entry.pack(pady=2)

        tk.Label(root, text="First Chapter URL:", font=('Arial', 10, 'bold')).pack(pady=5)
        self.chapter_url_entry = tk.Entry(root, width=90)
        self.chapter_url_entry.pack(pady=2)

        tk.Label(root, text="Save Folder Location:", font=('Arial', 10, 'bold')).pack(pady=5)
        path_frame = tk.Frame(root)
        path_frame.pack(pady=2)
        self.path_entry = tk.Entry(path_frame, textvariable=self.save_path_var, width=75)
        self.path_entry.pack(side=tk.LEFT, padx=5)
        self.browse_btn = tk.Button(path_frame, text="Browse Folder", command=self.browse_folder, bg="#95a5a6", fg="white")
        self.browse_btn.pack(side=tk.LEFT)

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

        self.log_box = tk.Text(root, height=22, width=95, state='disabled', bg="#1e1e1e", fg="#ecf0f1", wrap='word')
        self.log_box.pack(pady=10, padx=10)

    def browse_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.save_path_var.set(folder_selected)

    def log(self, message, is_header=False, replace_last_line=False):
        """Thread-safe logging with ability to update the last line (for timer)"""
        self.log_box.config(state='normal')
        
        if replace_last_line:
            # Delete the last line before writing the new one (simulate timer update)
            self.log_box.delete("end-2l", "end-1l") 
            
        if is_header:
            self.log_box.insert(tk.END, f"\n{'=' * 60}\n{message.upper()}\n{'=' * 60}\n")
        else:
            timestamp = time.strftime('%H:%M:%S')
            self.log_box.insert(tk.END, f"[{timestamp}] {message}\n")
            
        self.log_box.see(tk.END)
        self.log_box.config(state='disabled')

    def smart_sleep(self, seconds):
        """Visual countdown timer in the log box"""
        for i in range(seconds, 0, -1):
            # Check pause state inside the loop so we don't freeze while counting down
            self.pause_condition.wait()
            
            # Update log with countdown (replace_last_line=True for numbers > start)
            msg = f"Waiting... {i} seconds remaining."
            if i == seconds:
                self.log(msg) # First print
            else:
                self.log(msg, replace_last_line=True) # Overwrite previous second
            
            time.sleep(1)
            
        # Clear the timer line when done
        self.log("Ready! Resuming operations...", replace_last_line=True)

    def clean_text(self, text):
        if not text: return "N/A"
        text = text.replace('\u2014', '--').replace('\u2013', '-')
        text = text.replace('\u201c', '"').replace('\u201d', '"')
        text = text.replace('\u2018', "'").replace('\u2019', "'")
        text = text.replace('\u2026', '...')
        text = text.replace('\xa0', ' ').replace('&nbsp;', ' ')
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
                    pdf.set_font("helvetica", 'B', 24)
                    pdf.multi_cell(0, 15, txt=safe_key, align='C')
                    pdf.ln(10)
                    pdf.set_font("helvetica", size=12)
                    pdf.multi_cell(0, 7, txt=safe_val)
                else:
                    pdf.set_font("helvetica", 'B', 16)
                    pdf.cell(0, 10, txt=safe_key, ln=True)
                    pdf.set_font("helvetica", size=11)
                    pdf.multi_cell(0, 6, txt=safe_val)

            base_path = self.save_path_var.get()
            safe_name = re.sub(r'[\\/*?:"<>|]', "", first_key).strip()
            story_folder = os.path.join(base_path, safe_name)
            
            if not os.path.exists(story_folder):
                try: os.makedirs(story_folder)
                except: story_folder = base_path
            
            full_path = os.path.join(story_folder, f"{safe_name}.pdf")
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
            
            # REPLACED time.sleep(3) WITH SMART TIMER
            self.smart_sleep(30) 

            try: title = driver.find_element(By.ID, "book_name").text
            except: title = "Untitled Story"

            try: description = driver.find_element(By.ID, "description").text
            except: description = "No description."

            self.log(f"TITLE: {title}")
            self.log(f"DEACRIPTION: {description}")
            # self.everything[title] = description

            # --- CHAPTERS ---
            self.log("Starting Chapter Scrape...", is_header=True)
            current_url = chapter_url

            while current_url:
                self.pause_condition.wait()
                driver.get(current_url)
                
                time.sleep(5) 

                try:
                    ch_title = driver.find_element(By.ID, 'chapter_title').text
                    ch_body = driver.find_element(By.ID, 'chapter_content').text
                    # self.everything[ch_title] = ch_body

                    self.log(f"Scraped: {ch_title}")
                    self.log(f"Body: {ch_body[:200]}...\n\n{'-' * 60}\n")
                    
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