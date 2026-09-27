# Local Network Registration System

A secure, lightweight, and offline-first Python web application designed for university professors and instructors to seamlessly register student attendance using dynamic QR codes over a Local Area Network (LAN) or a PC Wireless Hotspot.

## 🚀 Features & Security Mechanisms

This system is built with high security and strict constraints to prevent cheating, duplicate registrations, and unauthorized access:

*   **Offline-First & Localized:** Runs entirely on a local network (Host PC's Hotspot or LAN). Students must be physically connected to the same network to access the registration page.
*   **Time-Restricted Tokens:** Each QR code generates a unique, cryptographic token with a strictly enforced countdown timer. Once the time expires, the session is invalidated.
*   **Anti-Resubmission & Back-Button Protection:** Utilizes the Post-Redirect-Get (PRG) pattern and strict `Cache-Control` headers to defeat browser BFCache. If a student tries to click the "Back" button to register another person, the browser is forced to re-evaluate the session and blocks them.
*   **Daily Cookie Limits:** Drops an encrypted daily cookie on the student's browser upon successful registration, instantly rejecting any subsequent attempts from the same device on that day.
*   **Dynamic CSV Storage:** Automatically saves attendance records (Date, Time, Name, ID, Group) in a `utf-8-sig` encoded CSV file for flawless Arabic text rendering in Microsoft Excel.

## 📁 Project Structure

```text
📁 Attendance_System/
│
├── 📄 main.py                  # The main Python backend (Flask & Tkinter)
├── 📄 save_path.txt            # (Auto-generated) Saves the last used CSV filename
├── 📄 students_attendance.csv  # (Auto-generated) The default output data file
│
└── 📁 templates/
│   ├── 📄 index.html           # The main page displaying the dynamic QR code
│   └── 📄 register.html        # The form submitted by the students
└── 📁 Static/
    └── 📄 demo.gif             # any additinal files for html file customization 
```
## 🎨 Customizing the Registration Page (`register.html`)

You can fully customize the look and feel of the student registration page. Open `templates/register.html` and look for the following comments:

```HTML
<!-- This is a simple registration page -->
<!-- Build your own style from here -->
```
### ⚠️ CRITICAL WARNING FOR DEVELOPERS:

While you are free to change the CSS, classes, and layout, **you must maintain the exact** `name` attributes of the form inputs. The Flask backend is case-sensitive and explicitly looks for these specific names to capture the data:

* `<input name="name">`

* `<input name="student_id">`

* `<input name="group">`

* `<input type="hidden" name="token" value="{{ token }}">` (Do not remove this line under any circumstances).

## 🛠️ Requirements & Installation

The application heavily utilizes Python's built-in standard libraries (`os`, `socket`, `tkinter`,`threading`, `csv`, `subprocess`) to remain lightweight. The only external dependency required is **Flask**.

1. Ensure you have **Python 3.x** installed on your system.

2. Open your terminal or command prompt in the project directory.

3. Install the required dependency using:

```bash
pip install Flask
```
## 📡 How to Run the System (Network Setup)

The application does not require an active internet connection, but it **requires a shared local network** between the host PC and the other users' devices.

### Mobile Hotspot (Recommended for strictly offline physical presence)

1. Turn on the **Mobile Hotspot** feature from your **Windows settings**.

2. Run the application

3. Enter the Hotspot SSID (Network Name), the session duration, and the target save file.

4. Ask users to connect their phones to your PC's Hotspot.

5. Click **Continue**. The QR code will appear on your screen for students to scan.

