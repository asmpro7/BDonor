# 🩸 BDonor

**BDonor** is a Telegram-based blood donation management system built using **Python**.  
It connects blood donors with recipients through a **moderated, admin-verified workflow**, ensuring reliability, privacy, and fast response during emergencies.

---

## 🚀 Features

### 👤 Donor
- Register as a blood donor
- Choose blood group
- Save phone number securely
- Receive notifications for matching blood requests
- Receive platelet donation requests (sent to all donors)

---

### 🏥 Recipient
- Submit blood or platelet donation requests
- Provide patient details (name, place, phone, required donors)
- Track request status (under review → approved → completed)
- Communicate with admins through the bot

---

### 🛡 Admin Panel (Telegram Group)
- Verify blood donation requests (Approve / Reject)
- Mark requests as completed
- Two-way moderated communication between admins and recipients
- Live dashboard:
  - Total donors
  - Donors per blood group
- Export full donors database to CSV

---

### 📢 Channel Integration
- Approved blood requests are posted to a Telegram channel
- Requests are edited automatically when marked as **COMPLETED**
- Platelet requests are **not posted to the channel** (sent only to donors)

---

## 🔄 Workflow Overview

1. User starts the bot
2. Chooses **Donor** or **Recipient**
3. Donor data is saved in the database
4. Recipient request is sent to admin group for verification
5. Admins approve / reject the request
6. Approved requests are sent to matching donors
7. Request can be marked as **COMPLETED** by user or admin
8. User is unlocked and can submit a new request

---

## 🧠 Smart Features
- Prevents duplicate completion
- Locks user while request is under review
- Unlocks user after completion
- Bidirectional message relay (Admin ↔ Recipient)
- Safe async handling (no event loop conflicts)

---

## 🗃 Database Schema (SQLite)

### Donors Table
| Column       | Type   | Description              |
|-------------|--------|--------------------------|
| userid      | INTEGER| Telegram user ID         |
| blood_group | TEXT   | Blood group              |
| phone       | TEXT   | Donor phone number       |

---

## 🛠 Tech Stack

- **Python 3.10+**
- **Kurigram** (Telegram Bot API)
- **SQLite**
- **AsyncIO**

---

## 📦 Installation

```bash
git clone https://github.com/asmpro7/BDonor.git
cd BDonor
pip install -r requirements.txt
```

---

## APIs
Make sure to set:

- api_id 
- api_hash 
- BOT_TOKEN 
- ADMIN_GROUP_ID 
- CHANNEL_ID 
- BOT_CHANNEL_LINK

---

## ▶️ Run the Bot

```bash
python BDonor.py
```

---
## 🔐 Security Notes

- Admin commands are restricted to admin group
- Phone numbers are never exposed publicly
- CSV export is admin-only
- Channel posting requires bot admin permissions

---

## 📄 License

This project is licensed under the MIT License.

---

## ❤️ Acknowledgments

Built to support life-saving blood donations and help communities respond faster in emergencies.
