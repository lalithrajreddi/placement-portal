# Placement Portal 🎓

A modern, full-stack placement tracking system designed for universities and colleges. This application allows Administration to manage organizations and students, enables Companies to list placement drives and review applications, and empowers Students to apply for opportunities and track their application lifecycle. 

## Features

*   **Role-Based Access Control**: Tailored dashboards and functionality specifically restricted to **Admin**, **Company**, and **Student** accounts.
*   **Aesthetic & Modern UI**: Features a sleek glassmorphism design, animated interactivity, and a cohesive premium visual foundation built directly on Bootstrap 5 and the Inter Google font.
*   **Resume Upload System**: Secure localized document uploads enabling companies to easily pull and view direct candidate profiles.
*   **Smart Search & Filtering**: Students and Admins can instantly search through placement drives and accounts.
*   **Dynamic Data Statistics**: Real-time analytical dashboards mapping applications locally, showing available drives, and individual success rates.
*   **Application Lifecycle History**: Logs systematic historical updates (Applied → Shortlisted → Selected/Rejected) to maintain a transparent historical track for each student.
*   **Data API Integrations**: `/api/drives` and `api/stats` backend endpoints natively exposing parsed JSON datasets.

## Technology Stack

*   **Backend Application**: Python, Flask, Flask-Login
*   **Database ORM**: Flask-SQLAlchemy (using SQLite)
*   **Frontend Ecosystem**: HTML5, CSS3, Jinja2 Templating, Bootstrap 5.3
*   **File Handling / Security**: Werkzeug

## Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone <repository_url>
   cd placement_portal
   ```

2. **Create a Virtual Environment** *(Highly Recommended)*:
   ```bash
   python -m venv venv
   
   # Windows:
   .\venv\Scripts\activate
   
   # macOS/Linux:
   source venv/bin/activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   *(If you don't have a requirements.txt, you can install the stack manually: `pip install Flask Flask-SQLAlchemy Flask-Login Werkzeug`)*

4. **Initialize & Run the Application:**
   On the first run, the SQLite database `placement.db` is dynamically generated in the background, which includes an initial core administrator account.
   ```bash
   python app.py
   ```
   *The local server will mount to `http://127.0.0.1:8000/`.*

## System Database Schema

*   **User**: Base abstract entity handling secure authentication flags (Admin / Company / Student).
*   **StudentProfile**: Correlates to a user; records student degree details and localized `.pdf/.docx` `resume_url`.
*   **CompanyProfile**: Correlates to a user; handles organizational identity and points of contact.
*   **PlacementDrive**: Live job listings submitted by companies needing admin approval.
*   **Application**: A student's interaction submitting core interest (and files) to a specific Placement Drive.
*   **ApplicationHistory**: Sub-table structurally detailing timestamp metadata every time an Application's conditional status is securely modified.

## Base Usage Guide 🚀
*   **Admin Login**: To configure the platform for the first time, use the auto-generated core account: 
    * `Username:` **admin**
    * `Password:` **admin123**
*   **New Companies**: Company registrations will be restricted until the Admin user explicitly approves their domain inside the "Manage Companies" module.
