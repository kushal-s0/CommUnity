<h2 align="center">
  🎓 CommUnity
</h2>

<p align="center">
  A web-based platform built with Django, SQLite, HTML, CSS, and JavaScript to manage college clubs and committees efficiently.
</p>

<p align="center">
  <a href="https://forthebadge.com">
    <img src="https://forthebadge.com/images/badges/built-with-love.svg" alt="Built with Love" />
  </a> &nbsp;
  <a href="https://forthebadge.com">
    <img src="https://forthebadge.com/images/badges/made-with-python.svg" alt="Made with Python" />
  </a> &nbsp;
</p>

---
<h3 align="center">
    🔹
    <a href="https://github.com/kushal-s0/CommUnity/issues">Report Bug</a> &nbsp; &nbsp;
    🔹
    <a href="https://github.com/kushal-s0/CommUnity/issues">Request Feature</a>
</h3>

---

## 🌟 Overview
The **CommUnity** is a dynamic platform that allows **Core Members, Faculty, and Associate Members** to manage clubs, publish announcements, schedule events, and oversee approvals efficiently.

## 🎥 Demo Video

[![Watch the Demo](https://img.shields.io/badge/▶-Watch%20Demo-red)](https://drive.google.com/file/d/1gnXLSHoTurimSiFqCFEbPClosUyVyl-U/view?usp=sharing)
---

## 🏛️ Features

### 👥 User Roles & Authentication
✅ **Google Authentication**: Secure login using Google.  
✅ **Restricted Login**: Only `@somaiya.edu` email addresses can sign up.  
✅ **Role-Based Access**:  
&nbsp;&nbsp;&nbsp;&nbsp;📌 **Core Members**: Create and manage club profiles, request faculty approval.  
&nbsp;&nbsp;&nbsp;&nbsp;📌 **Faculty**: Approve club changes, manage the academic calendar.  
&nbsp;&nbsp;&nbsp;&nbsp;📌 **Associate Members**: Publish announcements, messages, upcoming events, and registrations.  

### 📢 Noticeboard & Event Scheduling
✅ **Post announcements, upcoming events, and messages**.  
✅ **Google Calendar Integration** for event scheduling.  
✅ **Smart Scheduling**: Prevents conflicts by checking time and location availability.  
✅ **Reverse Day Rule**: No events can be scheduled on restricted academic days.  

---

## 🚀 Tech Stack
- **Backend**: Django, Python, SQLite
- **Frontend**: HTML, CSS, JavaScript
- **Authentication**: Google OAuth
- **Database**: SQLite
- **API Integrations**: Google Calendar API

---

## 🛠 Installation & Setup

<h3>1️⃣ Clone the Repository</h3>
```
git clone https://github.com/your-repo-url.git
cd CommUnity
```

<h3>2️⃣ Create & Activate a Virtual Environment</h3>
```
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

<h3>3️⃣ Install Dependencies</h3>
```
pip install -r requirements.txt
```

<h3>4️⃣ Configure Environment Variables</h3>
```
Create a .env file with the required Google API credentials.
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
ALLOWED_HOSTS=yourdomain.com
```

<h3>5️⃣ Run Migrations & Start Server</h3>
```
python manage.py migrate
python manage.py runserver
```
🚀 Visit: http://127.0.0.1:8000/ to access the platform.

<h2 align="center">👨‍💻 Developed By</h2> <p align="center"> <a href="https://github.com/Sagar-Shetty0804">Sagar</a> • <a href="https://github.com/kushal-s0">Kushal</a> • <a href="https://github.com/pTIWARI-20">Pragati</a> • <a href="https://github.com/aditya-s27">Aditya</a> </p> <p align="center"> ⭐ Give this project a star if you like it! </p> 
