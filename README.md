# VoiceKhata - AI English Voice-Driven Accounting & Ledger Web Application

VoiceKhata is a production-level, voice-driven credit ledger web application built with **AngularJS (1.8)**, **Django REST Framework (DRF)**, **PostgreSQL**, **JWT Authentication**, and **Google Gemini AI English Speech Parsing**.

---

## 🌟 Table of Contents
1. [Project Overview](#-project-overview)
2. [Technology Stack](#-technology-stack)
3. [Folder Structure](#-folder-structure)
4. [Prerequisites](#-prerequisites)
5. [PostgreSQL Installation & Database Setup](#-postgresql-installation--database-setup)
6. [Backend Setup (Django + DRF)](#-backend-setup-django--drf)
7. [Frontend Setup (AngularJS)](#-frontend-setup-angularjs)
8. [Configuring the Gemini API Key](#-configuring-the-gemini-api-key)
9. [JWT Authentication Flow](#-jwt-authentication-flow)
10. [Ports & Frontend-Backend Communication](#-ports--frontend-backend-communication)
11. [Sample API Endpoints & Request/Response Formats](#-sample-api-endpoints--requestresponse-formats)
12. [How to Run the Project (Daily Usage)](#-how-to-run-the-project-daily-usage)
13. [Troubleshooting Guide](#-troubleshooting-guide)
14. [Production Deployment Guide](#-production-deployment-guide)
15. [Future Enhancement Suggestions](#-future-enhancement-suggestions)

---

## 🚀 Project Overview

VoiceKhata enables business owners, shopkeepers, and service providers to manage customer credit, payments, sales, and dues by speaking naturally in **English**.

### Key Application Workflow:
1. **Landing Page**: Overview of features, CTA buttons, and interactive English voice examples.
2. **JWT Authentication**: Secure Register, Login, Refresh Token, Password Change, and AngularJS Route Guards.
3. **Dashboard**: Summary metrics for Total Customers, Total Credit, Total Payments, Pending Balance, and Recent Transactions.
4. **Voice Recording Screen**: Real-time browser Speech Recognition API locked to English (`en-US`).
5. **AI Parsing & Fallback Engine**: Dual-stage transaction extraction (Google Gemini API with a robust rule-based Regex fallback engine for English).
6. **Confirmation Screen**: Preview extracted details (Customer Name, Amount, Type, Due Date, Notes) with full inline editing before saving.
7. **Customer Ledger Directory**: Detailed customer ledger profiles, searching, sorting, outstanding balance summaries, and transaction history modals.
8. **Transaction Management**: Filter by Credit, Payment, Sales, Expense, search, add, edit, and delete transactions.
9. **Financial Insights**: Dynamic Chart.js visualizations (Monthly trends bar chart, Credit recovery doughnut chart).
10. **Reminders Module**: Track Today's Due, Upcoming Due Dates, and Overdue/Missed reminders with status toggles.
11. **Settings Module**: Profile details, security settings, notification preferences, terms, and privacy policy.

---

## 🛠 Technology Stack

### Frontend
- **Framework**: AngularJS (1.8.2)
- **Routing**: `angular-route` (`ngRoute`)
- **Styling**: Vanilla CSS3 + Bootstrap 5 + FontAwesome 6
- **Charts**: Chart.js
- **Speech API**: Web Speech API (`SpeechRecognition` / `webkitSpeechRecognition`) locked to English (`en-US`)

### Backend
- **Framework**: Django 4.2+ & Django REST Framework (DRF)
- **Database**: PostgreSQL (with SQLite fallback for instant setup)
- **Authentication**: JWT (`djangorestframework-simplejwt`)
- **CORS**: `django-cors-headers`
- **AI Engine**: Google Gemini API (`google-genai`) + Rule-Based Regex Parser Fallback

---

## 📁 Folder Structure

```
voicekhata/
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── .env
│   ├── voicekhata_backend/
│   │   ├── settings.py           # Django & Database configuration
│   │   ├── urls.py               # Main API routes & SPA fallback
│   │   └── wsgi.py
│   ├── authentication/           # JWT auth, registration, profile, password change
│   ├── customers/                # Customer ledger CRUD & balances
│   ├── transactions/             # Transaction CRUD (Credit, Payment, Sales, Expense)
│   ├── voice/                    # English speech parser (Gemini API + Rule fallback)
│   ├── insights/                 # Analytics summary metrics & chart data
│   ├── reminders/                # Payment due reminders
│   └── settings_app/             # User settings & preferences
└── frontend/
    ├── index.html                # Single Page Application shell
    ├── css/
    │   └── style.css             # Modern Blue/White design system
    ├── js/
    │   ├── app.js                # AngularJS module, route config, JWT interceptor
    │   ├── services/             # authService, apiService, voiceService, etc.
    │   └── controllers/          # DashboardController, VoiceInputController, etc.
    └── views/                    # HTML views (landing, dashboard, voice, etc.)
```

---

## 📋 Prerequisites

Ensure you have the following installed on your machine:
- **Python**: 3.9 or higher (`python --version`)
- **PostgreSQL**: 13 or higher (`psql --version`)
- **Node.js / HTTP Server**: (Optional) For serving the frontend independently, or Python's built-in HTTP server.

---

## 🐘 PostgreSQL Installation & Database Setup

### Step 1: Install PostgreSQL
- **Windows**: Download and install from [PostgreSQL Official Installer](https://www.postgresql.org/download/windows/).
- **Linux (Ubuntu/Debian)**: `sudo apt update && sudo apt install postgresql postgresql-contrib`
- **macOS**: `brew install postgresql`

### Step 2: Create Database & User
Open `sql shell (psql)` or terminal:

```sql
CREATE DATABASE voicekhata_db;
CREATE USER postgres WITH PASSWORD 'postgres';
GRANT ALL PRIVILEGES ON DATABASE voicekhata_db TO postgres;
```

---

## ⚙️ Backend Setup (Django + DRF)

### Step 1: Navigate to Backend Directory
```bash
cd voicekhata/backend
```

### Step 2: Create & Activate Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Ensure `.env` contains your PostgreSQL settings:
```env
DB_ENGINE=django.db.backends.postgresql
DB_NAME=voicekhata_db
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
GEMINI_API_KEY=your_gemini_api_key_here
```
> *Note: If PostgreSQL parameters are left empty, the application automatically falls back to an SQLite database (`db.sqlite3`) for instant zero-config testing.*

### Step 5: Run Database Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### Step 6: Create Superuser (Admin Account)
```bash
python manage.py createsuperuser
```

### Step 7: Start Django Backend Server
```bash
python manage.py runserver 8000
```
Backend API will be live at `http://127.0.0.1:8000/api/`.

---

## 💻 Frontend Setup (AngularJS)

### Option A: Unified Server (Recommended)
Because Django serves the `frontend` folder as static files, simply navigate to `http://127.0.0.1:8000/` in your browser to run the full VoiceKhata application!

### Option B: Independent Frontend Server
If you prefer running the frontend on a separate web server (e.g., Live Server or Node `http-server`):
```bash
cd voicekhata/frontend
npx http-server -p 3000
```
Open `http://localhost:3000/` in Google Chrome or Microsoft Edge.

---

## 🔑 Configuring the Gemini API Key

1. Obtain a free API key from [Google AI Studio](https://aistudio.google.com/).
2. Open `backend/.env`.
3. Set your key:
   ```env
   GEMINI_API_KEY=AIzaSyYourActualKeyHere
   ```
4. Restart the Django server.

> **Fallback Guarantee**: If no Gemini API key is provided or if network fails, VoiceKhata automatically uses its built-in rule-based Regex parser to extract customer names, amounts, dues, and transaction types.

---

## 🔒 JWT Authentication Flow

1. **Login Request**: User submits credentials to `POST /api/auth/login/`.
2. **Tokens Returned**: Server responds with `{ "access": "<access_token>", "refresh": "<refresh_token>" }`.
3. **Storage**: Access and refresh tokens are stored securely in browser `localStorage`.
4. **Header Interceptor**: AngularJS `jwtInterceptor` in `js/app.js` attaches `Authorization: Bearer <access_token>` to every subsequent `/api/` HTTP request.
5. **Route Guard**: AngularJS listens to `$routeChangeStart` events to block unauthenticated users from reaching protected routes (`/dashboard`, `/voice`, `/customers`, etc.).

---

## 📡 Ports & Frontend-Backend Communication

- **Backend API Port**: `http://127.0.0.1:8000/api/`
- **Frontend Port**: `http://127.0.0.1:8000/` (Unified) or `http://localhost:3000/` (Independent)
- Communication happens via standard CORS-enabled REST APIs JSON payloads.

---

## 📑 Sample API Endpoints & Request/Response Formats

### 1. Register User
`POST /api/auth/register/`
**Request Payload**:
```json
{
  "username": "shopkeeper1",
  "email": "shop@example.com",
  "password": "Password123",
  "confirm_password": "Password123",
  "business_name": "Metro General Store",
  "phone": "+91 9876543210"
}
```

### 2. Parse Voice Transcript
`POST /api/voice/parse/`
**Request Payload**:
```json
{
  "transcript": "Alex borrowed 2500 rupees and will pay in 5 days"
}
```
**Response Payload**:
```json
{
  "customer_name": "Alex",
  "amount": 2500.0,
  "transaction_type": "credit",
  "due_date": "2026-08-12",
  "notes": "Alex borrowed 2500 rupees and will pay in 5 days",
  "date": "2026-08-07",
  "status": "pending",
  "parser_used": "gemini-ai"
}
```

### 3. Create Transaction
`POST /api/transactions/`
**Request Payload**:
```json
{
  "customer_name": "Alex",
  "amount": 2500.0,
  "transaction_type": "credit",
  "due_date": "2026-08-12",
  "description": "Alex borrowed 2500 rupees",
  "status": "pending"
}
```

---

## ▶️ How to Run the Project (Daily Usage)

Whenever you want to start the project for development or usage on your local machine, follow these simple steps:

### 1. Start the Backend Server
Open a terminal (or command prompt), navigate to the backend folder, activate the virtual environment, and run the server:

```bash
cd backend
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
# source venv/bin/activate

python manage.py runserver
```

### 2. Access the Application
Since the frontend is integrated with the Django backend, you do not need to run a separate frontend server! 

Simply open your web browser and navigate to:
**[http://127.0.0.1:8000/](http://127.0.0.1:8000/)**

*(Optional: If you prefer to run the frontend independently, open another terminal in the `frontend` folder and run `npx http-server -p 3000`)*

---

## ❓ Troubleshooting Guide

### 1. Database Connection Error (`psycopg2.OperationalError`)
- Ensure PostgreSQL service is running (`services.msc` on Windows or `sudo systemctl status postgresql` on Linux).
- Verify database credentials in `backend/.env`.

### 2. Speech Recognition Not Working
- Web Speech API requires browser permission. Ensure microphone permission is granted.
- Use Google Chrome, Microsoft Edge, or Safari.

### 3. CORS Error
- Ensure `django-cors-headers` is listed in `INSTALLED_APPS` and `MIDDLEWARE` in `settings.py`.

### 4. Gemini API Error
- Verify key validity in `.env`. The fallback rule-based parser will automatically execute if API fails.

---

## 🚢 Production Deployment Guide

### Backend Deployment (Gunicorn + Nginx + PostgreSQL)
1. Install Gunicorn: `pip install gunicorn`
2. Set `DEBUG=False` in `backend/.env`.
3. Collect static files: `python manage.py collectstatic`
4. Run Gunicorn: `gunicorn voicekhata_backend.wsgi:application --bind 0.0.0.0:8000`

### Frontend Deployment
Serve `frontend/` files via Nginx or Cloudflare Pages.

---

## 🔮 Future Enhancement Suggestions
1. **SMS & WhatsApp Reminders**: Integrate Twilio or WhatsApp Business API to send automated due reminders.
2. **PDF Receipt Generation**: Download printable customer ledger PDF statements.
3. **Offline PWA Support**: Add Progressive Web App service workers for offline caching.



## API Limit Exceed Error Solution
That's a great question!

Here is what you need to know about this error and how the application will handle it going forward:

Will the error happen again?
The "Quota Exceeded" error itself will technically still happen in the background whenever you hit the limit of your free-tier Gemini API key. Google limits how many requests you can make per minute/day on the free plan.

Do you need to worry about it?
No, you don't! Thanks to the fallback system we just implemented, this error will never break your app again.

From now on, if you hit the Gemini API quota limit, the application will silently handle the error. You will just see a small yellow warning that says "Audio API failed. Falling back to text parser..." and your transaction will still be saved successfully using the built-in offline parser. Your workflow will not be interrupted.

How to permanently stop the background error:
If you want to stop hitting the quota limits entirely and rely 100% on the Gemini AI without seeing the fallback warning, you have two options:

Upgrade your Gemini Plan: Go to Google AI Studio and set up billing to remove the free-tier limits.
Use a New Key: You can generate a fresh API key from a different Google account and replace the GEMINI_API_KEY in your backend/.env file.
For now, you are completely fine to just keep using the app as is! The fallback system has your back.