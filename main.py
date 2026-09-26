import os
import time
import socket
import csv
import subprocess
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

# --------- Network Utilities ----------
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

def get_hotspot_name():
    """Retrieve the Windows Mobile Hotspot SSID from the registry."""
    try:
        # Fetch the Mobile Hotspot SSID from Windows Registry using PowerShell
        output = subprocess.check_output(
            ["powershell", "-Command", "(Get-ItemProperty -Path 'HKLM:\\SYSTEM\\CurrentControlSet\\Services\\icssvc\\Settings').SSID"],
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            text=True
        )
        ssid = output.strip()
        return ssid if ssid else "Your Mobile Hotspot"
    except:
        return "Your Mobile Hotspot"

# --------- GUI Interface ----------
def get_startup_settings():
    """Interface that requests duration, then shows a wait screen with the SSID."""
    user_data = {"time": 60}

    root = tk.Tk()
    root.title("Local System Settings")
    
    ws, hs = root.winfo_screenwidth(), root.winfo_screenheight()
    w, h = 350, 180
    x, y = (ws/2) - (w/2), (hs/2) - (h/2)
    root.geometry('%dx%d+%d+%d' % (w, h, x, y))
    
    tk.Label(root, text="Session Duration (Seconds):", font=("Arial", 12, "bold")).pack(pady=(20, 5))
    
    entry_time = tk.Entry(root, width=15, font=("Arial", 12), justify='center')
    entry_time.insert(0, "60") 
    entry_time.pack(pady=10)

    def on_cancel():
        root.destroy()
        sys.exit()

    def on_confirm():
        time_val = entry_time.get().strip()
        if not time_val.isdigit():
            messagebox.showerror("Error", "Time must be a number (seconds).", parent=root)
            return
        
        user_data["time"] = int(time_val)
        
        # Hide the main window to show the Hotspot waiting popup
        root.withdraw()
        hotspot_ssid = get_hotspot_name()
        
        popup = tk.Toplevel()
        popup.title("Waiting for Connections")
        pw, ph = 400, 220
        px, py = (ws/2) - (pw/2), (hs/2) - (ph/2)
        popup.geometry('%dx%d+%d+%d' % (pw, ph, px, py))
        popup.protocol("WM_DELETE_WINDOW", on_cancel)
        
        tk.Label(popup, text="Please ask students to connect to this network:", font=("Arial", 11)).pack(pady=(20, 5))
        tk.Label(popup, text=f"📶 {hotspot_ssid}", font=("Arial", 16, "bold"), fg="#0078D7").pack(pady=10)
        tk.Label(popup, text="Click Continue once everyone is connected.", font=("Arial", 10, "italic"), fg="gray").pack(pady=5)
        
        def on_continue():
            root.destroy()  # This ends the mainloop and returns user_data
            
        tk.Button(popup, text="🚀 Continue", command=on_continue, bg="#008CBA", fg="white", width=15, font=("Arial", 12, "bold")).pack(pady=10)

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
    
    return render_template("register.html", token=token)

@app.route("/submit", methods=["POST"])
def submit():
    token = request.form.get("token")
    if not is_token_valid(token):
        return "<h1 style='color:red;text-align:center;'>❌ The time limit for registration has been exceeded</h1>", 403
    
    name = request.form.get("name")
    student_id = request.form.get("student_id")
    group = request.form.get("group")
    
    excel_file = os.path.join(get_base_path(), "students_attendance.csv")
    file_exists = os.path.isfile(excel_file)
    
    with open(excel_file, mode='a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Date", "Time", "Name", "Student ID", "Group"])
        writer.writerow([date.today().isoformat(), datetime.now().strftime("%H:%M:%S"), name, student_id, group])
        
    today_str = date.today().isoformat()
    cookie_name = f"attended_{today_str}"
    
    # HTML response equipped with JS history-lock (Anti-Back Button Loop)
    html_response = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Registration Completed</title>
        <script>
            // Push the current state to history to create a forward state
            window.history.pushState(null, "", window.location.href);
            
            // Loop back to this page if the user tries to click the back button
            window.onpopstate = function () {
                window.history.pushState(null, "", window.location.href);
            };
            
            // Disable right-click to prevent inspecting or bypassing
            document.addEventListener('contextmenu', event => event.preventDefault());
        </script>
    </head>
    <body style="font-family: Arial, sans-serif; background-color: #f4f7f6; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0;">
        <div style="background: white; padding: 40px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); text-align: center;">
            <h1 style="color: green;">✅ Registration Successful!</h1>
            <h3>You can safely close this page now.</h3>
            <p style="color: gray; font-size: 12px; margin-top: 20px;">Navigating back is disabled for security reasons.</p>
        </div>
    </body>
    </html>
    """
    
    resp = make_response(html_response)
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