# BrewLog ☕

BrewLog is a full-stack web application that allows users to track and analyze coffee brewing experiments.

## Features
- User signup and login
- Brew logging system
- Brew history tracking
- Analytics dashboard
- Coffee ratio calculator
- Image uploads

## Tech Stack
- Python (Flask)
- SQLite
- HTML / CSS / JavaScript

## Run Locally
`pip install -r requirements.txt`

Create a `.env` file from `.env.example` if you want to customize the app secret or database file location:

- `DATABASE_PATH=brewlog.db`
- `SECRET_KEY=brewlog_secret`

Then run:

`python app.py`
