# College Bus Tracking System

A web-based College Bus Tracking System developed to simplify and manage college transportation services for students, drivers, parents, and administrators.

## 🌐 Live Project

**[Visit the Live College Bus Tracking System](https://college-bus-tracking-system-production.up.railway.app)**

## 📌 Project Overview

The College Bus Tracking System is a web application designed to provide an organized and convenient platform for managing college transportation.

The system allows administrators to manage buses, routes, students, drivers, parents, and transportation-related information. Students and parents can access relevant bus and transportation information, while drivers can manage their assigned transportation activities.

## ✨ Key Features

- 🔐 Secure user authentication
- 👨‍🎓 Student management
- 👨‍👩‍👧 Parent management
- 🚌 Bus management
- 🗺️ Route management
- 👨‍✈️ Driver management
- 📍 Bus tracking and location information
- 📜 Travel history
- 🚨 Emergency alert functionality
- 🔔 Notifications
- 📧 Email and OTP functionality
- 🔑 Password reset functionality
- 👤 Profile management
- 🛡️ Admin dashboard
- 🔒 Argon2 password hashing
- 📱 Responsive web interface

## 👥 User Roles

### Admin

- Manage students
- Manage parents
- Manage drivers
- Manage buses
- Manage routes
- View transportation information
- Manage system data

### Student

- Login securely
- View bus and route information
- View travel history
- Access emergency features
- Manage profile
- Receive notifications

### Driver

- Login securely
- View assigned bus and route information
- Manage driver-related activities
- Access notifications and transportation features

### Parent

- Login securely
- View student/bus-related information
- Track relevant transportation information
- Receive notifications
- Access emergency-related information
- Manage profile

## 🛠️ Technologies Used

### Backend

- Python
- Flask

### Frontend

- HTML5
- CSS3
- JavaScript
- Bootstrap

### Database

- MySQL

### Authentication & Security

- Argon2 password hashing
- OTP-based verification
- Secure session management

### Cloud & Services

- Railway
- Firebase

### Development Tools

- Visual Studio Code
- Git
- GitHub

## 🏗️ System Architecture

```text
                    ┌──────────────────────────┐
                    │          Users           │
                    │                          │
                    │ Admin / Student / Parent │
                    │         / Driver         │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │     Web Interface        │
                    │    HTML / CSS / JS       │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │      Flask Backend       │
                    │     Python / Flask       │
                    └────────────┬─────────────┘
                                 │
                   ┌─────────────┴─────────────┐
                   ▼                           ▼
          ┌─────────────────┐         ┌─────────────────┐
          │      MySQL      │         │     Firebase    │
          │     Database    │         │     Services    │
          └─────────────────┘         └─────────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │        Railway           │
                    │       Deployment         │
                    └──────────────────────────┘