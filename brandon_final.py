# """
# Combined OnlyFans Tool
# - Single-file Tkinter app that combines:
#   1) Scrolling + network-capture + cleaning
#   2) Per-username info fetch + filter
#   3) Profile selection & save
#   4) Scroll control and first-time manual login flow

# USAGE:
# - Install dependencies: selenium, pandas, python-dateutil, pytz
# - Place ChromeDriver on PATH or in same folder.
# - Run this script: python combined_onlyfans_tool.py

# """

# import os
# import json
# import time
# import csv
# import base64
# import threading
# from pathlib import Path
# from datetime import datetime

# import tkinter as tk
# from tkinter import ttk, messagebox, filedialog, scrolledtext

# # Third-party libs used in filters/info
# import pandas as pd
# import numpy as np
# import pytz
# from dateutil import parser

# # Selenium
# from selenium import webdriver
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.chrome.options import Options

# # -------------------------
# # Config & Paths
# # -------------------------
# CONFIG_FILE = "of_tool_config.json"
# DEFAULT_PROFILE_ROOT = os.path.join(os.getcwd(), "chrome_profile_data")
# INPUT_FILE_SCROLL_JSON = "onlyfans_posts.json"
# CLEANED_JSON = "cleaned_users.json"
# CLEANED_CSV = "username.csv"
# USERNAMES_CSV = "usernames.csv"
# OUTPUT_JSON_DIR = "json_data"
# RESULTS_CSV = "results_onlyfans.csv"
# FILTERED_CSV = "filtered_onlyfans.csv"

# # Ensure folders exist
# os.makedirs(DEFAULT_PROFILE_ROOT, exist_ok=True)
# os.makedirs(OUTPUT_JSON_DIR, exist_ok=True)

# # -------------------------
# # Utilities
# # -------------------------

# def load_config():
#     if os.path.exists(CONFIG_FILE):
#         try:
#             with open(CONFIG_FILE, "r", encoding="utf-8") as f:
#                 return json.load(f)
#         except Exception:
#             return {}
#     return {}


# def save_config(cfg):
#     with open(CONFIG_FILE, "w", encoding="utf-8") as f:
#         json.dump(cfg, f, indent=2)


# # -------------------------
# # Part 1: Scrolling + capture + cleaning
# # -------------------------

# def setup_driver_for_scrolling(profile_dir=None):
#     opts = Options()
#     if profile_dir:
#         # use explicit user-data-dir so login persists
#         opts.add_argument(f"--user-data-dir={profile_dir}")
#         # don't force profile-directory unless user set a subdir name
#     opts.add_argument("--remote-debugging-port=9222")
#     opts.add_argument("--disable-blink-features=AutomationControlled")
#     opts.add_argument("--start-maximized")
#     opts.set_capability("goog:loggingPrefs", {"performance": "ALL"})
#     service = Service()
#     driver = webdriver.Chrome(service=service, options=opts)
#     try:
#         driver.execute_cdp_cmd("Network.enable", {})
#     except Exception:
#         pass
#     return driver


# def extract_onlyfans_responses(driver):
#     logs = []
#     try:
#         raw = driver.get_log("performance")
#     except Exception:
#         raw = []
#     posts_data = []
#     for entry in raw:
#         try:
#             msg = json.loads(entry["message"])['message']
#             params = msg.get("params", {})
#             response = params.get("response", {})
#             url = response.get("url", "")
#             if "https://onlyfans.com/api2/v2/posts" in url and response.get("mimeType"):
#                 request_id = params.get("requestId")
#                 try:
#                     res_body = driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": request_id})
#                     text = res_body.get("body", "")
#                     if text:
#                         try:
#                             data = json.loads(text)
#                             posts_data.append(data)
#                         except Exception:
#                             pass
#                 except Exception:
#                     pass
#         except Exception:
#             pass

#     if posts_data:
#         # append to file safely
#         save_json_entries(posts_data, INPUT_FILE_SCROLL_JSON)
#     return len(posts_data)


# def save_json_entries(data, filename):
#     # load existing
#     existing = []
#     if os.path.exists(filename):
#         try:
#             with open(filename, "r", encoding="utf-8") as f:
#                 content = f.read().strip()
#                 if content:
#                     existing = json.loads(content)
#         except Exception:
#             existing = []
#     existing.extend(data)
#     with open(filename, "w", encoding="utf-8") as f:
#         json.dump(existing, f, indent=2, ensure_ascii=False)


# def clean_users_from_posts(input_file=INPUT_FILE_SCROLL_JSON, out_json=CLEANED_JSON, out_csv=CLEANED_CSV):
#     try:
#         with open(input_file, "r", encoding="utf-8") as f:
#             data = json.load(f)
#     except Exception:
#         return 0
#     linked_users = {}
#     mentioned_users = {}
#     linked_seen = 0
#     mentioned_seen = 0
#     for block in data:
#         if isinstance(block, dict) and "list" in block:
#             for item in block["list"]:
#                 for user in item.get("linkedUsers", []):
#                     linked_seen += 1
#                     linked_users[user.get("id")] = user
#                 for user in item.get("mentionedUsers", []):
#                     mentioned_seen += 1
#                     mentioned_users[user.get("id")] = user
#     combined = {"linked_users": list(linked_users.values()), "mentioned_users": list(mentioned_users.values())}
#     with open(out_json, "w", encoding="utf-8") as f:
#         json.dump(combined, f, indent=2, ensure_ascii=False)
#     # save csv
#     rows = []
#     for u in linked_users.values():
#         r = {**u}
#         r["type"] = "linked"
#         rows.append(r)
#     for u in mentioned_users.values():
#         r = {**u}
#         r["type"] = "mentioned"
#         rows.append(r)
#     if rows:
#         fieldnames = sorted(set().union(*(r.keys() for r in rows)))
#         with open(out_csv, "w", newline="", encoding="utf-8") as f:
#             writer = csv.DictWriter(f, fieldnames=fieldnames)
#             writer.writeheader()
#             writer.writerows(rows)
#     return len(rows)

# # -------------------------
# # Part 2: Per-username info fetch + filter
# # -------------------------

# def setup_driver_for_info(profile_dir=None):
#     opts = webdriver.ChromeOptions()
#     if profile_dir:
#         opts.add_argument(f"--user-data-dir={profile_dir}")
#     opts.add_experimental_option("excludeSwitches", ["enable-automation"])
#     opts.add_experimental_option("useAutomationExtension", False)
#     opts.set_capability("goog:loggingPrefs", {"performance": "ALL"})
#     service = Service()
#     driver = webdriver.Chrome(service=service, options=opts)
#     try:
#         driver.execute_cdp_cmd("Network.enable", {})
#     except Exception:
#         pass
#     return driver


# def get_perf_logs(driver):
#     entries = []
#     try:
#         for item in driver.get_log("performance"):
#             msg = json.loads(item["message"])['message']
#             entries.append(msg)
#     except Exception:
#         pass
#     return entries


# def find_user_api_request(driver, username, timeout=15, poll_interval=0.5):
#     target_fragment = f"/api2/v2/users/{username}"
#     deadline = time.time() + timeout
#     while time.time() < deadline:
#         msgs = get_perf_logs(driver)
#         for m in msgs:
#             if m.get("method") == "Network.responseReceived":
#                 params = m.get("params", {})
#                 response = params.get("response", {})
#                 url = response.get("url", "")
#                 if target_fragment in url:
#                     return params.get("requestId")
#         time.sleep(poll_interval)
#     return None


# def get_response_body_by_request_id(driver, request_id):
#     try:
#         body_info = driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": request_id})
#         body = body_info.get("body", "")
#         if body_info.get("base64Encoded"):
#             raw = base64.b64decode(body)
#             return raw.decode("utf-8", errors="ignore")
#         else:
#             return body
#     except Exception:
#         return None


# def run_scraper_for_usernames(profile_dir, progress_callback=None):
#     os.makedirs(OUTPUT_JSON_DIR, exist_ok=True)
#     if not os.path.exists(USERNAMES_CSV):
#         raise FileNotFoundError(f"{USERNAMES_CSV} not found")
#     df = pd.read_csv(USERNAMES_CSV)
#     if "id" not in df.columns:
#         raise ValueError("id column required in usernames.csv")
#     usernames = df["id"].dropna().astype(str).tolist()
#     driver = setup_driver_for_info(profile_dir)
#     results = []
#     try:
#         for username in usernames:
#             profile_url = f"https://onlyfans.com/{username}"
#             if progress_callback:
#                 progress_callback(f"Visiting {profile_url}")
#             # clear logs
#             try:
#                 driver.get("about:blank")
#             except Exception:
#                 pass
#             try:
#                 driver.get(profile_url)
#             except Exception as e:
#                 results.append({"username": username, "status": "nav_error"})
#                 if progress_callback:
#                     progress_callback(f"Navigation error for {username}: {e}")
#                 continue
#             request_id = find_user_api_request(driver, username)
#             if not request_id:
#                 results.append({"username": username, "status": "no_api_response"})
#                 if progress_callback:
#                     progress_callback(f"API response not found for {username}")
#                 continue
#             raw_text = get_response_body_by_request_id(driver, request_id)
#             if not raw_text:
#                 results.append({"username": username, "status": "no_body"})
#                 if progress_callback:
#                     progress_callback(f"No body for requestId {request_id} ({username})")
#                 continue
#             try:
#                 data = json.loads(raw_text)
#             except Exception as e:
#                 results.append({"username": username, "status": "json_error"})
#                 if progress_callback:
#                     progress_callback(f"JSON parse error for {username}: {e}")
#                 continue
#             json_path = os.path.join(OUTPUT_JSON_DIR, f"{username}.json")
#             with open(json_path, "w", encoding="utf-8") as jf:
#                 json.dump(data, jf, ensure_ascii=False, indent=2)
#             rec = {
#                 "username": data.get("username"),
#                 "id": data.get("id"),
#                 "name": data.get("name"),
#                 "joinDate": data.get("joinDate"),
#                 "firstPublishedPostDate": data.get("firstPublishedPostDate"),
#                 "postsCount": data.get("postsCount"),
#                 "photosCount": data.get("photosCount"),
#                 "videosCount": data.get("videosCount"),
#                 "favoritedCount": data.get("favoritedCount"),
#                 "favoritesCount": data.get("favoritesCount"),
#                 "subscribePrice": data.get("subscribePrice"),
#                 "isVerified": data.get("isVerified"),
#                 "isPerformer": data.get("isPerformer"),
#                 "raw_json_path": json_path,
#                 "status": "ok"
#             }
#             results.append(rec)
#             if progress_callback:
#                 progress_callback(f"Saved JSON for {username}")
#     finally:
#         try:
#             out_df = pd.DataFrame(results)
#             out_df.to_csv(RESULTS_CSV, index=False, encoding="utf-8-sig")
#             if progress_callback:
#                 progress_callback(f"Results CSV saved to {RESULTS_CSV}")
#         except Exception as e:
#             if progress_callback:
#                 progress_callback(f"Error saving results CSV: {e}")
#         try:
#             driver.quit()
#         except Exception:
#             pass
#     return results

# # Filters

# def parse_datetime_safe(s):
#     if pd.isna(s):
#         return None
#     s = str(s).strip()
#     if s == "" or s.lower() == "nan":
#         return None
#     try:
#         dt = parser.parse(s)
#         if dt.tzinfo is None:
#             dt = dt.replace(tzinfo=pytz.UTC)
#         tz = pytz.timezone("Asia/Karachi")
#         dt = dt.astimezone(tz)
#         return dt
#     except Exception:
#         return None


# def months_between(dt):
#     if dt is None:
#         return np.nan
#     delta_days = (datetime.now(pytz.timezone("Asia/Karachi")) - dt).total_seconds() / (3600*24)
#     return delta_days / 30.44


# def run_filter(filters, progress_callback=None):
#     if not os.path.exists(RESULTS_CSV):
#         raise FileNotFoundError(f"{RESULTS_CSV} not found")
#     df = pd.read_csv(RESULTS_CSV, dtype=str)
#     if df.empty:
#         if progress_callback:
#             progress_callback("Results CSV is empty")
#         return 0
#     df.columns = [c.strip() for c in df.columns]
#     join_col = None
#     for c in df.columns:
#         if "join" in c.lower() or "date" in c.lower() or "created" in c.lower():
#             join_col = c
#             break
#     if not join_col:
#         if "joinDate" in df.columns:
#             join_col = "joinDate"
#     if not join_col:
#         raise ValueError("No join date column found in results CSV")
#     df["_parsed_join"] = df[join_col].apply(parse_datetime_safe)
#     df["_age_months"] = df["_parsed_join"].apply(months_between)
#     likes_field = None
#     for c in df.columns:
#         if "favor" in c.lower() or "like" in c.lower():
#             likes_field = c
#             break
#     if likes_field:
#         df["_likes_val"] = pd.to_numeric(df[likes_field], errors="coerce")
#     else:
#         df["_likes_val"] = np.nan
#     posts_field = None
#     for c in df.columns:
#         if "post" in c.lower():
#             posts_field = c
#             break
#     if posts_field:
#         df["_posts_val"] = pd.to_numeric(df[posts_field], errors="coerce")
#     else:
#         df["_posts_val"] = np.nan
#     mask = pd.Series(True, index=df.index)
#     if filters.get("age_enabled"):
#         if filters.get("min_age") is not None:
#             mask &= df["_age_months"] >= filters["min_age"]
#         if filters.get("max_age") is not None:
#             mask &= df["_age_months"] <= filters["max_age"]
#     if filters.get("likes_enabled"):
#         if filters.get("min_likes") is not None:
#             mask &= df["_likes_val"].fillna(-np.inf) >= filters["min_likes"]
#         if filters.get("max_likes") is not None:
#             mask &= df["_likes_val"].fillna(np.inf) <= filters["max_likes"]
#     if filters.get("posts_enabled"):
#         if filters.get("min_posts") is not None:
#             mask &= df["_posts_val"].fillna(-np.inf) >= filters["min_posts"]
#         if filters.get("max_posts") is not None:
#             mask &= df["_posts_val"].fillna(np.inf) <= filters["max_posts"]
#     filtered = df[mask].copy()
#     cols_to_keep = [c for c in df.columns if not c.startswith("_")]
#     out_df = filtered[cols_to_keep].copy()
#     out_df["_age_months"] = filtered["_age_months"].round(2)
#     out_df["_likes_val"] = filtered["_likes_val"]
#     out_df["_posts_val"] = filtered["_posts_val"]
#     out_df.to_csv(FILTERED_CSV, index=False, encoding="utf-8-sig")
#     if progress_callback:
#         progress_callback(f"Filtered {len(out_df)} rows (from {len(df)}). Saved to {FILTERED_CSV}")
#     return len(out_df)

# # -------------------------
# # Tkinter GUI - Tabs
# # -------------------------
# class App:
#     def __init__(self, master):
#         self.master = master
#         master.title("OnlyFans Tool — Combined")
#         self.cfg = load_config()
#         self.profile_dir = self.cfg.get("profile_dir")

#         self.notebook = ttk.Notebook(master)
#         self.notebook.pack(fill="both", expand=True, padx=6, pady=6)

#         self.build_profile_tab()
#         self.build_scrape_tab()
#         self.build_info_tab()
#         self.build_filter_tab()
#         self.build_logs_tab()

#         # status
#         self.log_lock = threading.Lock()

#     def build_profile_tab(self):
#         frame = ttk.Frame(self.notebook)
#         self.notebook.add(frame, text="Profile")

#         ttk.Label(frame, text="Chrome profile directory:").grid(row=0, column=0, sticky="w", pady=4)
#         self.profile_var = tk.StringVar(value=self.profile_dir or "")
#         self.profile_entry = ttk.Entry(frame, textvariable=self.profile_var, width=60)
#         self.profile_entry.grid(row=1, column=0, columnspan=2, sticky="w")

#         btn_choose = ttk.Button(frame, text="Choose Folder", command=self.choose_profile_folder)
#         btn_choose.grid(row=2, column=0, sticky="w", pady=6)
#         btn_save = ttk.Button(frame, text="Save Profile (use this)", command=self.save_profile_choice)
#         btn_save.grid(row=2, column=1, sticky="w", padx=6)

#         ttk.Label(frame, text="Notes:").grid(row=3, column=0, sticky="w", pady=(10,0))
#         notes = tk.Text(frame, height=4, width=80)
#         notes.insert("1.0", "If you don't have a profile dir yet, choose a folder to store a new Chrome profile (it will contain browser state). On first run you'll be prompted to open the browser and login manually.")
#         notes.configure(state="disabled")
#         notes.grid(row=4, column=0, columnspan=2, pady=(0,10))

#     def choose_profile_folder(self):
#         chosen = filedialog.askdirectory(initialdir=DEFAULT_PROFILE_ROOT)
#         if chosen:
#             # create a dedicated subfolder pattern: chrome_profile_data/<foldername>
#             dest = os.path.join(DEFAULT_PROFILE_ROOT, os.path.basename(chosen))
#             # if user chose inside DEFAULT_PROFILE_ROOT, keep it.
#             if not chosen.startswith(DEFAULT_PROFILE_ROOT):
#                 # copy or reference chosen path directly. we'll let user decide.
#                 dest = chosen
#             self.profile_var.set(dest)

#     def save_profile_choice(self):
#         path = self.profile_var.get().strip()
#         if not path:
#             messagebox.showwarning("Warning", "Please choose a folder for Chrome profile.")
#             return
#         os.makedirs(path, exist_ok=True)
#         self.cfg["profile_dir"] = path
#         save_config(self.cfg)
#         self.profile_dir = path
#         messagebox.showinfo("Saved", f"Profile directory saved: {path}")

#     def build_scrape_tab(self):
#         frame = ttk.Frame(self.notebook)
#         self.notebook.add(frame, text="Scrape & Clean")

#         ttk.Label(frame, text="Scroll count:").grid(row=0, column=0, sticky="w", pady=6)
#         self.scroll_entry = ttk.Entry(frame, width=8)
#         self.scroll_entry.insert(0, "10")
#         self.scroll_entry.grid(row=0, column=1, sticky="w")

#         self.manual_login_var = tk.BooleanVar(value=True)
#         ttk.Checkbutton(frame, text="Manual login on first run", variable=self.manual_login_var).grid(row=1, column=0, columnspan=2, sticky="w")

#         ttk.Button(frame, text="Start Scrolling (run part 1)", command=self.start_scrolling_thread).grid(row=2, column=0, pady=8)
#         ttk.Button(frame, text="Clean extracted data", command=self.clean_extracted_data).grid(row=2, column=1, padx=6)

#     def build_info_tab(self):
#         frame = ttk.Frame(self.notebook)
#         self.notebook.add(frame, text="Get Info")

#         ttk.Label(frame, text=f"Usernames CSV (must contain column 'username'):").grid(row=0, column=0, sticky="w", pady=6)
#         ttk.Button(frame, text="Choose usernames.csv", command=self.choose_usernames_csv).grid(row=0, column=1, sticky="w")
#         self.username_label = ttk.Label(frame, text=USERNAMES_CSV)
#         self.username_label.grid(row=1, column=0, columnspan=2, sticky="w")

#         ttk.Button(frame, text="Run Scraper (user info)", command=self.start_userinfo_thread).grid(row=2, column=0, pady=8)

#     def build_filter_tab(self):
#         frame = ttk.Frame(self.notebook)
#         self.notebook.add(frame, text="Filter")

#         # Age
#         self.age_var = tk.BooleanVar()
#         ttk.Checkbutton(frame, text="Filter by Age (months)", variable=self.age_var).grid(row=0, column=0, sticky="w")
#         ttk.Label(frame, text="Min").grid(row=0, column=1)
#         self.min_age_entry = ttk.Entry(frame, width=6)
#         self.min_age_entry.grid(row=0, column=2)
#         ttk.Label(frame, text="Max").grid(row=0, column=3)
#         self.max_age_entry = ttk.Entry(frame, width=6)
#         self.max_age_entry.grid(row=0, column=4)

#         # Likes
#         self.likes_var = tk.BooleanVar()
#         ttk.Checkbutton(frame, text="Filter by Likes", variable=self.likes_var).grid(row=1, column=0, sticky="w")
#         ttk.Label(frame, text="Min").grid(row=1, column=1)
#         self.min_likes_entry = ttk.Entry(frame, width=6)
#         self.min_likes_entry.grid(row=1, column=2)
#         ttk.Label(frame, text="Max").grid(row=1, column=3)
#         self.max_likes_entry = ttk.Entry(frame, width=6)
#         self.max_likes_entry.grid(row=1, column=4)

#         # Posts
#         self.posts_var = tk.BooleanVar()
#         ttk.Checkbutton(frame, text="Filter by Posts", variable=self.posts_var).grid(row=2, column=0, sticky="w")
#         ttk.Label(frame, text="Min").grid(row=2, column=1)
#         self.min_posts_entry = ttk.Entry(frame, width=6)
#         self.min_posts_entry.grid(row=2, column=2)
#         ttk.Label(frame, text="Max").grid(row=2, column=3)
#         self.max_posts_entry = ttk.Entry(frame, width=6)
#         self.max_posts_entry.grid(row=2, column=4)

#         ttk.Button(frame, text="Apply Filter (on results CSV)", command=self.apply_filter_thread).grid(row=3, column=0, pady=8)

#     def build_logs_tab(self):
#         frame = ttk.Frame(self.notebook)
#         self.notebook.add(frame, text="Logs")
#         self.log_widget = scrolledtext.ScrolledText(frame, width=100, height=30, state="disabled")
#         self.log_widget.pack(fill="both", expand=True, padx=6, pady=6)

#     # --------------------
#     # Actions
#     # --------------------
#     def log(self, msg):
#         ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#         s = f"[{ts}] {msg}\n"
#         with self.log_lock:
#             self.log_widget.configure(state="normal")
#             self.log_widget.insert("end", s)
#             self.log_widget.see("end")
#             self.log_widget.configure(state="disabled")
#         print(s, end="")

#     def start_scrolling_thread(self):
#         t = threading.Thread(target=self.worker_scrolling, daemon=True)
#         t.start()

#     def worker_scrolling(self):
#         profile_dir = self.profile_var.get().strip() or None
#         if not profile_dir:
#             self.log("No profile directory selected. Please set it in Profile tab.")
#             return
#         # Check manual login flow
#         first_login_required = self.manual_login_var.get()
#         # Launch browser with profile to allow manual login
#         driver = setup_driver_for_scrolling(profile_dir)
#         try:
#             driver.get("https://onlyfans.com/")
#             if first_login_required:
#                 # Let user login manually. Show dialog in GUI
#                 self.log("Please login manually in the opened browser. After logging in, press OK in this dialog.")
#                 # open a simple modal dialog
#                 ok = messagebox.askokcancel("Manual login", "A browser window opened. Please log in, then click OK to continue.")
#                 if not ok:
#                     self.log("User cancelled login flow.")
#                     driver.quit()
#                     return
#             # Now perform scrolling
#             try:
#                 scroll_count = int(self.scroll_entry.get())
#             except Exception:
#                 self.log("Invalid scroll count; defaulting to 10")
#                 scroll_count = 10
#             self.log(f"Starting auto-scrolling x{scroll_count}")
#             for i in range(1, scroll_count + 1):
#                 self.log(f"Scroll {i}/{scroll_count}")
#                 try:
#                     driver.execute_script("window.scrollBy(0, document.body.scrollHeight);")
#                 except Exception as e:
#                     self.log(f"Scroll script error: {e}")
#                 time.sleep(3)
#                 new_posts = extract_onlyfans_responses(driver)
#                 if new_posts:
#                     self.log(f"Captured {new_posts} API post blocks during this scroll")
#             self.log("Scrolling finished. Closing browser.")
#         finally:
#             try:
#                 driver.quit()
#             except Exception:
#                 pass
#         # Auto-clean
#         cnt = clean_users_from_posts()
#         self.log(f"Cleaning done. {cnt} user rows extracted and saved to {CLEANED_JSON} / {CLEANED_CSV}")

#     def clean_extracted_data(self):
#         cnt = clean_users_from_posts()
#         messagebox.showinfo("Cleaned", f"Extracted and saved {cnt} rows to {CLEANED_JSON} / {CLEANED_CSV}")

#     def choose_usernames_csv(self):
#         chosen = filedialog.askopenfilename(filetypes=[("CSV files","*.csv")], initialdir=os.getcwd())
#         if chosen:
#             # copy or set path
#             global USERNAMES_CSV
#             USERNAMES_CSV = chosen
#             self.username_label.configure(text=USERNAMES_CSV)

#     def start_userinfo_thread(self):
#         t = threading.Thread(target=self.worker_userinfo, daemon=True)
#         t.start()

#     def worker_userinfo(self):
#         profile_dir = self.profile_var.get().strip() or None
#         if not profile_dir:
#             self.log("No profile directory selected. Please set it in Profile tab.")
#             return
#         try:
#             self.log("Starting user-info scraper...")
#             results = run_scraper_for_usernames(profile_dir, progress_callback=self.log)
#             self.log(f"User-info scraper finished: {len(results)} usernames processed. Results saved to {RESULTS_CSV}")
#         except Exception as e:
#             self.log(f"Error in user-info scraper: {e}")
#             messagebox.showerror("Error", str(e))

#     def apply_filter_thread(self):
#         t = threading.Thread(target=self.worker_filter_apply, daemon=True)
#         t.start()

#     def worker_filter_apply(self):
#         filters = {
#             "age_enabled": bool(self.age_var.get()),
#             "min_age": int(self.min_age_entry.get()) if self.min_age_entry.get() else None,
#             "max_age": int(self.max_age_entry.get()) if self.max_age_entry.get() else None,
#             "likes_enabled": bool(self.likes_var.get()),
#             "min_likes": int(self.min_likes_entry.get()) if self.min_likes_entry.get() else None,
#             "max_likes": int(self.max_likes_entry.get()) if self.max_likes_entry.get() else None,
#             "posts_enabled": bool(self.posts_var.get()),
#             "min_posts": int(self.min_posts_entry.get()) if self.min_posts_entry.get() else None,
#             "max_posts": int(self.max_posts_entry.get()) if self.max_posts_entry.get() else None,
#         }
#         try:
#             self.log("Applying filters...")
#             count = run_filter(filters, progress_callback=self.log)
#             self.log(f"Filtering finished. {count} rows saved to {FILTERED_CSV}")
#             messagebox.showinfo("Filter Done", f"Filtered {count} rows. See {FILTERED_CSV}")
#         except Exception as e:
#             self.log(f"Filter error: {e}")
#             messagebox.showerror("Filter error", str(e))

# # -------------------------
# # Run
# # -------------------------

# def main():
#     root = tk.Tk()
#     app = App(root)
#     root.mainloop()

# if __name__ == "__main__":
#     main()


































"""
Combined OnlyFans Tool - Single Window (Layout B)
- Single-file Tkinter app that:
  * Option to perform initial scrolling (captures network responses)
  * Auto-cleaning of scraped posts -> username CSV (id-based)
  * Option to use scraped usernames OR use provided usernames.csv (reads 'id' column)
  * Per-username info fetch (saves results CSV)
  * Filtering (age/likes/posts) -> final output "Final data.csv"
  * Final CSV includes a profile_link column: https://onlyfans.com/{id}
  * Manual login option (checkbox). If checked, user will be prompted to login in opened browser.
  * All options on one window (Layout B style). Start button runs entire automated pipeline.
  * Logs shown in window.
USAGE:
- Install dependencies: pip install selenium pandas python-dateutil pytz
- Put chromedriver on PATH or same folder.
- Run: python combined_onlyfans_tool_single_window.py
"""
import itertools    
import os
import json
import time
import csv
import base64
import threading
from pathlib import Path
from datetime import datetime
import csv
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import pandas as pd
import numpy as np
import pytz
from dateutil import parser

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# -------------------------
# Config & Paths
# -------------------------
CONFIG_FILE = "of_tool_config.json"
DEFAULT_PROFILE_ROOT = os.path.join(os.getcwd(), "chrome_profile_data")
INPUT_FILE_SCROLL_JSON = "onlyfans_posts.json"
CLEANED_JSON = "cleaned_users.json"
CLEANED_CSV = "username.csv"           # produced by cleaning step (contains 'id')
USER_PROVIDED_CSV = "usernames.csv"   # fallback / user-provided (must contain 'id' column)
OUTPUT_JSON_DIR = "json_data"
RESULTS_CSV = "results_onlyfans.csv"
FINAL_CSV = "Final data.csv"           # final requested filename

os.makedirs(DEFAULT_PROFILE_ROOT, exist_ok=True)
os.makedirs(OUTPUT_JSON_DIR, exist_ok=True)


# -------------------------
# Simple config read/save
# -------------------------
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


# -------------------------
# Scrolling + capture + cleaning
# -------------------------
def setup_driver_for_scrolling(profile_dir=None):
    opts = Options()
    if profile_dir:
        opts.add_argument(f"--user-data-dir={profile_dir}")
    opts.add_argument("--remote-debugging-port=9222")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    # opts.add_argument("--start-maximized")
    # opts.add_argument("-headless=new")
    opts.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    service = Service()
    driver = webdriver.Chrome(service=service, options=opts)
    try:
        driver.execute_cdp_cmd("Network.enable", {})
    except Exception:
        pass
    return driver


def extract_onlyfans_responses(driver):
    try:
        raw = driver.get_log("performance")
    except Exception:
        raw = []
    posts_data = []
    for entry in raw:
        try:
            msg = json.loads(entry["message"])['message']
            params = msg.get("params", {})
            response = params.get("response", {})
            url = response.get("url", "")
            # capture posts API responses
            if "https://onlyfans.com/api2/v2/posts" in url and response.get("mimeType"):
                request_id = params.get("requestId")
                try:
                    res_body = driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": request_id})
                    text = res_body.get("body", "")
                    if text:
                        try:
                            data = json.loads(text)
                            posts_data.append(data)
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass
    if posts_data:
        save_json_entries(posts_data, INPUT_FILE_SCROLL_JSON)
    return len(posts_data)


def save_json_entries(data, filename):
    existing = []
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    existing = json.loads(content)
        except Exception:
            existing = []
    existing.extend(data)
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)

def clean_users_from_posts(input_file=INPUT_FILE_SCROLL_JSON, out_json=CLEANED_JSON, out_csv=CLEANED_CSV):
    """
    Extract linkedUsers and mentionedUsers from saved posts JSON.
    Saves combined JSON and a CSV with 'id' for each user (keeps fields present in objects).
    Removes duplicates between linked and mentioned users.
    Returns number of unique rows saved.
    """
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        print(f"[!] Could not read input file: {input_file}")
        return 0

    linked_users = {}
    mentioned_users = {}

    for block in data:
        if isinstance(block, dict) and "list" in block:
            for item in block["list"]:
                for user in item.get("linkedUsers", []):
                    uid = user.get("id")
                    if uid is not None:
                        linked_users[str(uid)] = user

                for user in item.get("mentionedUsers", []):
                    uid = user.get("id")
                    if uid is not None:
                        mentioned_users[str(uid)] = user

    # Combine and remove duplicates
    unique_users = {}
    for u in list(linked_users.values()) + list(mentioned_users.values()):
        uid = str(u.get("id"))
        if uid and uid not in unique_users:
            unique_users[uid] = u

    # Prepare rows for CSV
    rows = []
    for uid, u in unique_users.items():
        user_type = []
        if uid in linked_users:
            user_type.append("linked")
        if uid in mentioned_users:
            user_type.append("mentioned")
        u["type"] = ",".join(user_type)
        rows.append(u)

    # Save combined JSON
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({"users": list(unique_users.values())}, f, indent=2, ensure_ascii=False)

    # Save CSV
    if rows:
        fieldnames = sorted(set().union(*(r.keys() for r in rows)))
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    # Log results
    total_before = len(linked_users) + len(mentioned_users)
    total_after = len(unique_users)
    removed = total_before - total_after
    print(f"[✔] Saved {total_after} unique users to '{out_csv}' (removed {removed} duplicates).")

    return total_after



# -------------------------
# Per-username info fetch + filter
# -------------------------
def setup_driver_for_info(profile_dir=None):
    opts = Options()
    if profile_dir:
        opts.add_argument(f"--user-data-dir={profile_dir}")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    # opts.add_argument("-headless=new")

    service = Service()
    driver = webdriver.Chrome(service=service, options=opts)
    try:
        driver.execute_cdp_cmd("Network.enable", {})
    except Exception:
        pass
    return driver


def get_perf_logs(driver):
    entries = []
    try:
        for item in driver.get_log("performance"):
            msg = json.loads(item["message"])['message']
            entries.append(msg)
    except Exception:
        pass
    return entries


def find_user_api_request(driver, username, timeout=15, poll_interval=0.5):
    target_fragment = f"/api2/v2/users/{username}"
    deadline = time.time() + timeout
    while time.time() < deadline:
        msgs = get_perf_logs(driver)
        for m in msgs:
            if m.get("method") == "Network.responseReceived":
                params = m.get("params", {})
                response = params.get("response", {})
                url = response.get("url", "")
                if target_fragment in url:
                    return params.get("requestId")
        time.sleep(poll_interval)
    return None


def get_response_body_by_request_id(driver, request_id):
    try:
        body_info = driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": request_id})
        body = body_info.get("body", "")
        if body_info.get("base64Encoded"):
            raw = base64.b64decode(body)
            return raw.decode("utf-8", errors="ignore")
        else:
            return body
    except Exception:
        return None


def run_scraper_for_usernames(profile_dir, usernames_csv_path, progress_callback=None):
    """
    Reads usernames_csv_path (expects column 'id'), visits each profile, captures /api2/v2/users/{id},
    saves per-username JSON into OUTPUT_JSON_DIR and creates RESULTS_CSV.
    """
    os.makedirs(OUTPUT_JSON_DIR, exist_ok=True)
    if not os.path.exists(usernames_csv_path):
        raise FileNotFoundError(f"{usernames_csv_path} not found")
    df = pd.read_csv(usernames_csv_path, dtype=str)
    if "id" not in df.columns:
        raise ValueError("id column required in usernames CSV")
    usernames = df["id"].dropna().astype(str).tolist()
    driver = setup_driver_for_info(profile_dir)
    results = []
    try:
        for username in usernames:
            profile_url = f"https://onlyfans.com/{username}"
            if progress_callback:
                progress_callback(f"Visiting {profile_url}")
            try:
                driver.get("about:blank")
            except Exception:
                pass
            try:
                driver.get(profile_url)
            except Exception as e:
                results.append({"username": username, "status": "nav_error"})
                if progress_callback:
                    progress_callback(f"Navigation error for {username}: {e}")
                continue
            request_id = find_user_api_request(driver, username)
            if not request_id:
                results.append({"username": username, "status": "no_api_response"})
                if progress_callback:
                    progress_callback(f"API response not found for {username}")
                continue
            raw_text = get_response_body_by_request_id(driver, request_id)
            if not raw_text:
                results.append({"username": username, "status": "no_body"})
                if progress_callback:
                    progress_callback(f"No body for requestId {request_id} ({username})")
                continue
            try:
                data = json.loads(raw_text)
            except Exception as e:
                results.append({"username": username, "status": "json_error"})
                if progress_callback:
                    progress_callback(f"JSON parse error for {username}: {e}")
                continue
            json_path = os.path.join(OUTPUT_JSON_DIR, f"{username}.json")
            with open(json_path, "w", encoding="utf-8") as jf:
                json.dump(data, jf, ensure_ascii=False, indent=2)
            rec = {
                "username": data.get("username"),
                "id": data.get("id"),
                "name": data.get("name"),
                "joinDate": data.get("joinDate"),
                "firstPublishedPostDate": data.get("firstPublishedPostDate"),
                "postsCount": data.get("postsCount"),
                "photosCount": data.get("photosCount"),
                "videosCount": data.get("videosCount"),
                "favoritedCount": data.get("favoritedCount"),
                "favoritesCount": data.get("favoritesCount"),
                "subscribePrice": data.get("subscribePrice"),
                "isVerified": data.get("isVerified"),
                "isPerformer": data.get("isPerformer"),
                "raw_json_path": json_path,
                "status": "ok"
            }
            results.append(rec)
            if progress_callback:
                progress_callback(f"Saved JSON for {username}")
    finally:
        try:
            out_df = pd.DataFrame(results)
            out_df.to_csv(RESULTS_CSV, index=False, encoding="utf-8-sig")
            if progress_callback:
                progress_callback(f"Results CSV saved to {RESULTS_CSV}")
        except Exception as e:
            if progress_callback:
                progress_callback(f"Error saving results CSV: {e}")
        try:
            driver.quit()
        except Exception:
            pass
    return results


# -------------------------
# Filters
# -------------------------
def parse_datetime_safe(s):
    if pd.isna(s):
        return None
    s = str(s).strip()
    if s == "" or s.lower() == "nan":
        return None
    try:
        dt = parser.parse(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=pytz.UTC)
        tz = pytz.timezone("Asia/Karachi")
        dt = dt.astimezone(tz)
        return dt
    except Exception:
        return None


def months_between(dt):
    if dt is None:
        return np.nan
    delta_days = (datetime.now(pytz.timezone("Asia/Karachi")) - dt).total_seconds() / (3600*24)
    return delta_days / 30.44


def run_filter_and_save(final_csv_path, filters, progress_callback=None):
    """
    Reads RESULTS_CSV (produced by username scraper), applies filters, saves final CSV
    and adds a profile_link column.
    """
    if not os.path.exists(RESULTS_CSV):
        raise FileNotFoundError(f"{RESULTS_CSV} not found")
    df = pd.read_csv(RESULTS_CSV, dtype=str)
    if df.empty:
        if progress_callback:
            progress_callback("Results CSV is empty")
        return 0
    df.columns = [c.strip() for c in df.columns]
    join_col = None
    for c in df.columns:
        if "join" in c.lower() or "date" in c.lower() or "created" in c.lower():
            join_col = c
            break
    if not join_col and "joinDate" in df.columns:
        join_col = "joinDate"
    if not join_col:
        raise ValueError("No join date column found in results CSV")
    df["_parsed_join"] = df[join_col].apply(parse_datetime_safe)
    df["_age_months"] = df["_parsed_join"].apply(months_between)

    likes_field = None
    for c in df.columns:
        if "favor" in c.lower() or "like" in c.lower():
            likes_field = c
            break
    if likes_field:
        df["_likes_val"] = pd.to_numeric(df[likes_field], errors="coerce")
    else:
        df["_likes_val"] = np.nan

    posts_field = None
    for c in df.columns:
        if "post" in c.lower():
            posts_field = c
            break
    if posts_field:
        df["_posts_val"] = pd.to_numeric(df[posts_field], errors="coerce")
    else:
        df["_posts_val"] = np.nan

    mask = pd.Series(True, index=df.index)
    if filters.get("age_enabled"):
        if filters.get("min_age") is not None:
            mask &= df["_age_months"] >= filters["min_age"]
        if filters.get("max_age") is not None:
            mask &= df["_age_months"] <= filters["max_age"]
    if filters.get("likes_enabled"):
        if filters.get("min_likes") is not None:
            mask &= df["_likes_val"].fillna(-np.inf) >= filters["min_likes"]
        if filters.get("max_likes") is not None:
            mask &= df["_likes_val"].fillna(np.inf) <= filters["max_likes"]
    if filters.get("posts_enabled"):
        if filters.get("min_posts") is not None:
            mask &= df["_posts_val"].fillna(-np.inf) >= filters["min_posts"]
        if filters.get("max_posts") is not None:
            mask &= df["_posts_val"].fillna(np.inf) <= filters["max_posts"]

    filtered = df[mask].copy()
    # keep original columns, add age/likes/posts columns, and add profile link
    cols_to_keep = [c for c in df.columns if not c.startswith("_")]
    out_df = filtered[cols_to_keep].copy()
    out_df["_age_months"] = filtered["_age_months"].round(2)
    out_df["_likes_val"] = filtered["_likes_val"]
    out_df["_posts_val"] = filtered["_posts_val"]

    # add clickable link column (plain URL; Excel will auto-link)
    def make_link(row):
        uid = row.get("id") or row.get("username") or ""
        return f"https://onlyfans.com/{uid}" if uid else ""

    out_df["profile_link"] = out_df.apply(make_link, axis=1)

    out_df.to_csv(final_csv_path, index=False, encoding="utf-8-sig")
    if progress_callback:
        progress_callback(f"Filtered {len(out_df)} rows (from {len(df)}). Saved to {final_csv_path}")
    return len(out_df)


# -------------------------
# Tkinter GUI - Single Window (Layout B)
# -------------------------
class App:
    def __init__(self, master):
        self.master = master
        master.title("OnlyFans Tool — Single Window (Auto)")
        self.cfg = load_config()
        self.profile_dir = self.cfg.get("profile_dir", "")
        frm_search = ttk.LabelFrame(master, text="Search Combination Settings")
        frm_search.pack(fill="x", padx=8, pady=(4,4))
        ttk.Label(frm_search, text="Combination length:").grid(row=0, column=0, padx=6, pady=6)
        self.combo_length_entry = ttk.Entry(frm_search, width=5)
        self.combo_length_entry.insert(0, "2")  # default 'aa'
        self.combo_length_entry.grid(row=0, column=1, padx=6)
        ttk.Label(frm_search, text="Letters to use (a-z default):").grid(row=0, column=2, padx=6)
        self.letters_entry = ttk.Entry(frm_search, width=20)
        self.letters_entry.insert(0, "abcdefghijklmnopqrstuvwxyz")
        self.letters_entry.grid(row=0, column=3, padx=6)

        # top frame: Browser profile / manual login
        frm_profile = ttk.LabelFrame(master, text="Browser Profile")
        frm_profile.pack(fill="x", padx=8, pady=(8,4))
        ttk.Label(frm_profile, text="Chrome profile directory:").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        self.profile_var = tk.StringVar(value=self.profile_dir or "")
        self.profile_entry = ttk.Entry(frm_profile, textvariable=self.profile_var, width=60)
        self.profile_entry.grid(row=1, column=0, columnspan=3, sticky="w", padx=6)
        btn_choose = ttk.Button(frm_profile, text="Browse", command=self.choose_profile_folder)
        btn_choose.grid(row=1, column=3, sticky="w", padx=6)
        self.manual_login_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frm_profile, text="Manual login on first run", variable=self.manual_login_var).grid(row=2, column=0, sticky="w", padx=6, pady=(0,6))
        ttk.Button(frm_profile, text="Save profile", command=self.save_profile_choice).grid(row=2, column=3, sticky="e", padx=6)

        # input files / controls
        frm_input = ttk.LabelFrame(master, text="Input Files & Controls")
        frm_input.pack(fill="x", padx=8, pady=(4,4))
        ttk.Label(frm_input, text="Use scraped usernames (from scroll+clean) if available:").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        self.use_scraped_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frm_input, variable=self.use_scraped_var).grid(row=0, column=1, sticky="w")
        ttk.Label(frm_input, text="Or choose a usernames CSV (must contain 'id' column):").grid(row=1, column=0, sticky="w", padx=6, pady=6)
        ttk.Button(frm_input, text="Browse usernames CSV", command=self.choose_usernames_csv).grid(row=1, column=1, sticky="w")
        self.username_label = ttk.Label(frm_input, text=USER_PROVIDED_CSV)
        self.username_label.grid(row=1, column=2, sticky="w", padx=6)
        ttk.Label(frm_input, text="Scroll count (for scraping):").grid(row=2, column=0, sticky="w", padx=6, pady=6)
        self.scroll_entry = ttk.Entry(frm_input, width=6)
        self.scroll_entry.insert(0, "10")
        self.scroll_entry.grid(row=2, column=1, sticky="w")

        # Filters area
        frm_filters = ttk.LabelFrame(master, text="Filters (will be applied automatically)")
        frm_filters.pack(fill="x", padx=8, pady=(4,4))
        # Age
        self.age_var = tk.BooleanVar()
        ttk.Checkbutton(frm_filters, text="Filter by Age (months)", variable=self.age_var).grid(row=0, column=0, sticky="w", padx=6, pady=4)
        ttk.Label(frm_filters, text="Min").grid(row=0, column=1)
        self.min_age_entry = ttk.Entry(frm_filters, width=6)
        self.min_age_entry.grid(row=0, column=2)
        ttk.Label(frm_filters, text="Max").grid(row=0, column=3)
        self.max_age_entry = ttk.Entry(frm_filters, width=6)
        self.max_age_entry.grid(row=0, column=4)

        # Likes
        self.likes_var = tk.BooleanVar()
        ttk.Checkbutton(frm_filters, text="Filter by Likes", variable=self.likes_var).grid(row=1, column=0, sticky="w", padx=6, pady=4)
        ttk.Label(frm_filters, text="Min").grid(row=1, column=1)
        self.min_likes_entry = ttk.Entry(frm_filters, width=6)
        self.min_likes_entry.grid(row=1, column=2)
        ttk.Label(frm_filters, text="Max").grid(row=1, column=3)
        self.max_likes_entry = ttk.Entry(frm_filters, width=6)
        self.max_likes_entry.grid(row=1, column=4)

        # Posts
        self.posts_var = tk.BooleanVar()
        ttk.Checkbutton(frm_filters, text="Filter by Posts", variable=self.posts_var).grid(row=2, column=0, sticky="w", padx=6, pady=4)
        ttk.Label(frm_filters, text="Min").grid(row=2, column=1)
        self.min_posts_entry = ttk.Entry(frm_filters, width=6)
        self.min_posts_entry.grid(row=2, column=2)
        ttk.Label(frm_filters, text="Max").grid(row=2, column=3)
        self.max_posts_entry = ttk.Entry(frm_filters, width=6)
        self.max_posts_entry.grid(row=2, column=4)

        # Start button & status
        frm_start = ttk.Frame(master)
        frm_start.pack(fill="x", padx=8, pady=(6,4))
        self.start_btn = ttk.Button(frm_start, text="START (run entire pipeline)", command=self.start_pipeline_thread)
        self.start_btn.pack(side="left", padx=6)
        ttk.Button(frm_start, text="Open output folder", command=self.open_output_folder).pack(side="left", padx=6)
        ttk.Label(frm_start, text=f"Final CSV: {FINAL_CSV}").pack(side="right", padx=6)

        # Logs
        frm_logs = ttk.LabelFrame(master, text="Logs")
        frm_logs.pack(fill="both", expand=True, padx=8, pady=(4,8))
        self.log_widget = scrolledtext.ScrolledText(frm_logs, width=120, height=20, state="disabled")
        self.log_widget.pack(fill="both", expand=True, padx=6, pady=6)

        self.log_lock = threading.Lock()

    # -------------------- UI helpers --------------------
    
    
    def generate_combinations(self):
        letters = self.letters_entry.get().strip() or "abcdefghijklmnopqrstuvwxyz"
        length = int(self.combo_length_entry.get().strip() or 2)
        combos = [''.join(c) for c in itertools.product(letters, repeat=length)]
        self.log(f"Generated {len(combos)} combinations: sample -> {combos[:5]}")
        return combos

    def log(self, msg):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        s = f"[{ts}] {msg}\n"
        with self.log_lock:
            self.log_widget.configure(state="normal")
            self.log_widget.insert("end", s)
            self.log_widget.see("end")
            self.log_widget.configure(state="disabled")
        print(s, end="")

    def open_output_folder(self):
        folder = os.getcwd()
        try:
            if os.name == "nt":
                os.startfile(folder)
            elif os.uname().sysname == "Darwin":
                os.system(f'open "{folder}"')
            else:
                os.system(f'xdg-open "{folder}"')
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder: {e}")

    def choose_profile_folder(self):
        chosen = filedialog.askdirectory(initialdir=DEFAULT_PROFILE_ROOT)
        if chosen:
            dest = os.path.join(DEFAULT_PROFILE_ROOT, os.path.basename(chosen)) if chosen.startswith(DEFAULT_PROFILE_ROOT) else chosen
            self.profile_var.set(dest)

    def save_profile_choice(self):
        path = self.profile_var.get().strip()
        if not path:
            messagebox.showwarning("Warning", "Please choose a folder for Chrome profile.")
            return
        os.makedirs(path, exist_ok=True)
        self.cfg["profile_dir"] = path
        save_config(self.cfg)
        self.profile_dir = path
        messagebox.showinfo("Saved", f"Profile directory saved: {path}")

    def choose_usernames_csv(self):
        chosen = filedialog.askopenfilename(filetypes=[("CSV files","*.csv")], initialdir=os.getcwd())
        if chosen:
            global USER_PROVIDED_CSV
            USER_PROVIDED_CSV = chosen
            self.username_label.configure(text=USER_PROVIDED_CSV)

    # -------------------- Pipeline --------------------
    def start_pipeline_thread(self):
        self.start_btn.configure(state="disabled")
        t = threading.Thread(target=self.worker_pipeline, daemon=True)
        t.start()

    def worker_pipeline(self):
        try:
            profile_dir = self.profile_var.get().strip() or None
            if not profile_dir:
                self.log("No profile directory selected. Please choose one.")
                self.start_btn.configure(state="normal")
                return

            # Save profile choice
            self.cfg["profile_dir"] = profile_dir
            save_config(self.cfg)

            # Step 1: Scrolling (optional but default on)
            # Step 1: Query-based Scrolling
            scroll_count = 10
            try:
                scroll_count = int(self.scroll_entry.get())
            except Exception:
                self.log("Invalid scroll count; defaulting to 10")

            self.log("Starting browser for search-based scrolling (to capture posts API).")
            driver = setup_driver_for_scrolling(profile_dir)

            try:
                driver.get("https://onlyfans.com/")
                if self.manual_login_var.get():
                    self.log("Manual login required: please login in the opened browser and click OK to continue.")
                    ok = messagebox.askokcancel("Manual login", "Please log in, then click OK to continue.")
                    if not ok:
                        self.log("User cancelled manual login flow.")
                        driver.quit()
                        self.start_btn.configure(state="normal")
                        return

                combos = self.generate_combinations()
                for idx, combo in enumerate(combos, 1):
                    search_url = f"https://onlyfans.com/search?type=posts&q={combo}"
                    self.log(f"[{idx}/{len(combos)}] Searching posts for '{combo}' -> {search_url}")

                    try:
                        driver.get(search_url)
                    except Exception as e:
                        self.log(f"Failed to open {search_url}: {e}")
                        continue

                    time.sleep(3)

                    # --- auto-skip logic added ---
                    max_no_results = 3  # if 3 consecutive scrolls have no new posts, skip to next query
                    no_results_streak = 0
                    last_post_count = 0

                    for i in range(1, scroll_count + 1):
                        self.log(f"Scroll {i}/{scroll_count} for query '{combo}'")
                        try:
                            driver.execute_script("window.scrollBy(0, document.body.scrollHeight);")
                        except Exception as e:
                            self.log(f"Scroll error: {e}")
                            continue

                        time.sleep(3)
                        new_posts = extract_onlyfans_responses(driver)

                        if new_posts:
                            self.log(f"Captured {new_posts} posts-block(s) for '{combo}'")
                            no_results_streak = 0
                            last_post_count += new_posts
                        else:
                            no_results_streak += 1
                            self.log(f"No new posts found ({no_results_streak}/{max_no_results})")

                            if no_results_streak >= max_no_results:
                                self.log(f"No more results for '{combo}', moving to next query...")
                                break
                    # --- end of auto-skip logic ---

                self.log("All queries processed. Scrolling finished.")

            finally:
                try:
                    driver.quit()
                except Exception:
                    pass


            # Step 2: Auto-cleaning
            self.log("Cleaning extracted posts -> extracting users...")
            rows = clean_users_from_posts()
            if rows:
                self.log(f"Cleaning done. Extracted {rows} user rows and saved to {CLEANED_JSON} / {CLEANED_CSV}")
            else:
                self.log("No user rows extracted during cleaning (check that onlyfans_posts.json exists and has data).")

            # Step 3: Choose usernames source
            if self.use_scraped_var.get() and os.path.exists(CLEANED_CSV):
                usernames_source = CLEANED_CSV
                self.log(f"Using scraped usernames from {CLEANED_CSV}")
            else:
                usernames_source = USER_PROVIDED_CSV
                self.log(f"Using provided usernames file: {usernames_source}")

            # Validate usernames file
            if not os.path.exists(usernames_source):
                messagebox.showerror("Error", f"Usernames file not found: {usernames_source}")
                self.start_btn.configure(state="normal")
                return

            # Step 4: Run per-username scraper
            self.log("Starting per-username info scraper...")
            try:
                results = run_scraper_for_usernames(profile_dir, usernames_source, progress_callback=self.log)
                self.log(f"User-info scraper finished: {len(results)} entries. Results saved to {RESULTS_CSV}")
            except Exception as e:
                self.log(f"Error in user-info scraper: {e}")
                messagebox.showerror("Error", f"User-info scraper failed: {e}")
                self.start_btn.configure(state="normal")
                return

            # Step 5: Apply filters -> Final CSV
            filters = {
                "age_enabled": bool(self.age_var.get()),
                "min_age": int(self.min_age_entry.get()) if self.min_age_entry.get() else None,
                "max_age": int(self.max_age_entry.get()) if self.max_age_entry.get() else None,
                "likes_enabled": bool(self.likes_var.get()),
                "min_likes": int(self.min_likes_entry.get()) if self.min_likes_entry.get() else None,
                "max_likes": int(self.max_likes_entry.get()) if self.max_likes_entry.get() else None,
                "posts_enabled": bool(self.posts_var.get()),
                "min_posts": int(self.min_posts_entry.get()) if self.min_posts_entry.get() else None,
                "max_posts": int(self.max_posts_entry.get()) if self.max_posts_entry.get() else None,
            }
            self.log("Applying filters and creating final CSV...")
            try:
                count = run_filter_and_save(FINAL_CSV, filters, progress_callback=self.log)
                self.log(f"All done. Final filtered results: {count} rows -> {FINAL_CSV}")
                messagebox.showinfo("Done", f"Pipeline finished. Final file: {FINAL_CSV} ({count} rows).")
            except Exception as e:
                self.log(f"Filter error: {e}")
                messagebox.showerror("Filter error", str(e))
        finally:
            self.start_btn.configure(state="normal")


# -------------------------
# Run
# -------------------------
def main():
    root = tk.Tk()
    app = App(root)
    root.mainloop()


if __name__ == "__main__":
    main()








INPUT_CSV = "Final data.csv"
OUTPUT_CSV = "cleaned_users_fixed.csv"

def clean_csv(input_file, output_file):
    seen = set()
    cleaned_rows = []

    with open(input_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # 🔹 Clean ID (.0 remove)
            if row.get("id"):
                try:
                    # Convert safely to int (even if it’s a float string like '519306272.0')
                    row["id"] = str(int(float(row["id"])))
                except ValueError:
                    row["id"] = row["id"].strip()

            # 🔹 Clean link (remove .0 from the end if present)
            if row.get("profile_link"):
                row["profile_link"] = row["profile_link"].replace(".0", "")

            # 🔹 Deduplicate by ID
            if row["id"] not in seen:
                seen.add(row["id"])
                cleaned_rows.append(row)

    # 🔹 Write cleaned data back
    fieldnames = cleaned_rows[0].keys() if cleaned_rows else []
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(cleaned_rows)

    print(f"✅ Cleaned {len(cleaned_rows)} unique rows saved to {output_file}")

clean_csv(INPUT_CSV, OUTPUT_CSV)