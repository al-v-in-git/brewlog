# BrewLog ☕

BrewLog is a robust, **Offline** full-stack web application designed for coffee enthusiasts to meticulously track and analyze their brewing experiments. By operating locally, it ensures your data remains private and accessible without an internet connection.

## Features
- **Secure Local Access:** User signup and login system to keep your logs private.
- **Comprehensive Brew Logging:** Detailed tracking of every brew, including bean types and brewing methods.
- **Brew History & Favorites:** Easily revisit your past successes and mark your favorite recipes.
- **Analytics Dashboard:** Visual insights into your brewing habits and preferences.
- **Coffee Ratio Calculator:** A built-in tool to help you dial in the perfect brew every time.
- **Image Uploads:** Attach photos of your coffee or setup to your logs.

## Tech Stack
- **Backend:** Python (Flask)
- **Database:** SQLite (Local storage)
- **Frontend:** HTML / CSS / JavaScript

## Team Contributions
- **Alvin Mike Jerad** (Team Lead): project direction, frontend design and overall system integration.
- **Aditya Sharma** (Back End Developer): backend logic and database management.

## Run Locally
1. Install dependencies:
   `pip install -r requirements.txt`

2. (Optional) Create a `.env` file to customize settings:
   - `DATABASE_PATH=brewlog.db`
   - `SECRET_KEY=your_secret_key_here`

3. Launch the application:
   `python app.py`

Access the app at `http://127.0.0.1:5000` in your web browser.
