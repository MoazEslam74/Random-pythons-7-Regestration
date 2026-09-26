import os
import time
import socket
import csv
from flask import Flask, render_template, request, make_response
import secrets
from datetime import datetime, timedelta, date
import webbrowser
import sys
import threading
import tkinter as tk
from tkinter import messagebox

# --------- Setup paths ----------
def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

template_dir = resource_path("templates")
app = Flask(__name__, template_folder=template_dir)

# --------- Global Variables ----------
TOKEN_VALIDITY_SECONDS = 60 

# --------- Local IP Finder ----------
def get_local_ip():
    """Get the IP address of your device on the hotspot network."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

# --------- GUI Interface ----------
def get_startup_settings():
    """Simple interface that requests only the duration for local mode."""
    user_data = {"time": 60}

    root = tk.Tk()
    root.title("Local System Settings")
    
    w, h = 350, 180
    ws, hs = root.winfo_screenwidth(), root.winfo_screenheight()
    x, y = (ws/2) - (w/2), (hs/2) - (h/2)
    root.geometry('%dx%d+%d+%d' % (w, h, x, y))
    
    tk.Label(root, text="Session Duration (Seconds):", font=("Arial", 12, "bold")).pack(pady=(20, 5))
    
    entry_time = tk.Entry(root, width=15, font=("Arial", 12), justify='center')
    entry_time.insert(0, "60") 
    entry_time.pack(pady=10)

    def on_confirm():
        time_val = entry_time.get().strip()
        if not time_val.isdigit():
            messagebox.showerror("Error", "Time must be a number (seconds).", parent=root)
            return
        
        user_data["time"] = int(time_val)
        root.destroy()

    def on_cancel():
        root.destroy()
        sys.exit()

    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=10)
    tk.Button(btn_frame, text="✅ Start Local System", command=on_confirm, bg="#4CAF50", fg="white", width=18).pack(side=tk.LEFT, padx=10)

    root.protocol("WM_DELETE_WINDOW", on_cancel)
    root.mainloop()
    return user_data

# --------- Token System ----------
tokens = {}

def generate_token():
    token = secrets.token_hex(4)
    tokens[token] = {"created_at": datetime.now(), "used": False}
    return token

def is_token_valid(token):
    global TOKEN_VALIDITY_SECONDS
    data = tokens.get(token)
    if not data: return False
    
    if datetime.now() - data["created_at"] > timedelta(seconds=TOKEN_VALIDITY_SECONDS):
        return False
    return True

# --------- Routes ----------
@app.route("/")
def qr_page():
    token = generate_token()
    # Use the local IP so students can access the system.
    public_url = app.config.get('PUBLIC_URL', f'http://{get_local_ip()}:5000')
    
    return render_template("index.html", 
                           token=token, 
                           public_url=public_url, 
                           time_limit=TOKEN_VALIDITY_SECONDS)

@app.route("/enter")
def enter():
    today_str = date.today().isoformat()
    cookie_name = f"attended_{today_str}"

    if request.cookies.get(cookie_name):
        return """<div style="text-align:center; margin-top:50px; font-family:Arial;">
                  <h1 style="color:red;">⛔ Sorry!</h1>
                  <h3>You have already registered for today.</h3></div>""", 403

    token = request.args.get("token")
    if not is_token_valid(token):
        return "<h1 style='color:red;text-align:center;'>❌ The QR Code has expired</h1>", 403
    
    # Redirect the student to the local registration page instead of an external form.
    return render_template("register.html", token=token)

@app.route("/submit", methods=["POST"])
def submit():
    token = request.form.get("token")
    # Ensure the student has not exceeded the time limit while filling in the form.
    if not is_token_valid(token):
        return "<h1 style='color:red;text-align:center;'>❌ The time limit for registration has been exceeded</h1>", 403
    
    name = request.form.get("name")
    student_id = request.form.get("student_id")
    group = request.form.get("group")
    
    # Save the data to a CSV file.
    excel_file = os.path.join(get_base_path(), "students_attendance.csv")
    file_exists = os.path.isfile(excel_file)
    
    # Use utf-8-sig so Arabic text displays correctly in Excel.
    with open(excel_file, mode='a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Date", "Time", "Name", "Student ID", "Group"])
        writer.writerow([date.today().isoformat(), datetime.now().strftime("%H:%M:%S"), name, student_id, group])
        
    # Set a cookie to prevent the student from registering again.
    today_str = date.today().isoformat()
    cookie_name = f"attended_{today_str}"
    
    resp = make_response("""<div style='text-align:center; margin-top:50px; font-family:Arial;'>
                            <h1 style='color:green;'>✅ Registration Successful!</h1>
                            <h3>You can close this page now.</h3></div>""")
    resp.set_cookie(cookie_name, 'true', max_age=43200)
    return resp

# --------- Main Execution ----------
if __name__ == "__main__":
    settings = get_startup_settings()
    TOKEN_VALIDITY_SECONDS = settings["time"]
    
    local_ip = get_local_ip()
    app.config['PUBLIC_URL'] = f"http://{local_ip}:5000"
    
    print(f"✅ Local System Ready: http://{local_ip}:5000")
    print(f"✅ Duration = {TOKEN_VALIDITY_SECONDS}s")

    # Run flask on 0.0.0.0 to accept connections from the hotspot
    flask_thread = threading.Thread(target=lambda: app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False))
    flask_thread.daemon = True 
    flask_thread.start()
    
    time.sleep(2)
    webbrowser.open(f"http://127.0.0.1:5000/") 
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt: 
        pass