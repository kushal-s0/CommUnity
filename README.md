College Clubs & Committees Management System

🌟 Overview

The College Clubs & Committees Management System is a web-based platform built using Django, SQLite, HTML, CSS, and JavaScript that allows users to manage and organize college clubs and committees efficiently. The system provides role-based access, enabling Core Members, Faculty, and Associate Members to perform specific actions such as creating club profiles, making announcements, scheduling events, and handling approvals.

🎯 Features

👥 User Roles & Authentication

Google Authentication: Secure login with Google authentication.

Restricted Login: Only @somaiya.edu email addresses can sign up and access the platform.

Role-Based Access:

Core Members: Create and manage club profiles, request faculty approval for edits.

Faculty: Approve club modifications, manage the academic calendar, and oversee event scheduling.

Associate Members: Publish announcements, messages, upcoming events, and registration details.

🏛️ Club & Committee Management

Core Members can create club profiles with a name, description, and optional image.

Clubs and Committees require faculty approval for any modifications.

List of all approved clubs and committees is displayed on the webpage.

📢 Noticeboard & Event Management

Associate Members can post announcements, upcoming events, and messages.

Events are integrated with Google Calendar.

Users can register for events directly from the platform.

📅 Smart Scheduling & Conflict Management

Faculty can add academic schedules (e.g., exams, holidays).

Reverse Day Rule: No events can be scheduled on certain academic days.

Time & Location-Based Slot Booking:

If a time slot and location are already booked, no other event can be scheduled at the same time.

🚀 Tech Stack

Backend: Django, Python, SQLite

Frontend: HTML, CSS, JavaScript

Authentication: Google OAuth (via Django)

Database: SQLite

API Integrations: Google Calendar API

🛠️ Setup & Installation

1️⃣ Clone the Repository

2️⃣ Create & Activate a Virtual Environment

3️⃣ Install Dependencies

4️⃣ Set Up Environment Variables

Create a .env file and configure the required Google API credentials and Django settings.

5️⃣ Run Migrations & Start Server

Visit http://127.0.0.1:8000/ to access the platform.

🎨 UI Preview



📌 Future Enhancements

Notifications for event approvals and announcements.

More granular role-based permissions.

Improved event filtering and search functionality.

📜 License

This project is licensed under the MIT License.

Developed by Sagar, Kushal, Pragati, Aditya ✨

