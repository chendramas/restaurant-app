# Chendra Grill

Restaurant ordering system. Customers browse the menu, select their table, place orders, and track order status in real-time. Kitchen staff manage orders through an admin dashboard.

## Features

- **Menu browsing** with category filters and food photos
- **Table selection** with visual floor-map style cards
- **Order placement** with cart, notes, and customer name
- **Order tracking** by order ID or table number with progress visualization
- **Kitchen dashboard** (admin-protected) with status management, daily stats, bulk actions
- **Auto-refresh** with countdown indicator on tracking and admin pages
- **Order confirmation sound** via Web Audio API

## Tech Stack

- Python / Flask
- SQLite (WAL mode)
- Vanilla HTML / CSS / JS
- Dark theme with Uber Eats-inspired design tokens

## Quick Start

```bash
cd chendra-grill
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # Edit .env with your secret key and admin password
python app.py
```

Open http://127.0.0.1:5002

See `run.txt` for detailed instructions.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | **Required.** Flask session secret. Generate with: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `ADMIN_PASSWORD` | **Required.** Admin dashboard password |
| `FLASK_DEBUG` | Set to `true` for development auto-reload. Default: `false` |

## Pages

| Route | Description |
|-------|-------------|
| `/` | Menu & ordering |
| `/track` | Order tracking (by ID or table) |
| `/admin/login` | Admin login |
| `/admin` | Kitchen dashboard (auth required) |

## Project Structure

```
chendra-grill/
├── app.py                  # Flask routes & API endpoints
├── utils/
│   ├── __init__.py
│   ├── database.py         # DB connection, schema, seed data
│   └── auth.py             # Admin auth decorator
├── templates/
│   ├── base.html           # Base layout, nav, footer, meta tags
│   ├── index.html          # Menu & ordering page
│   ├── track.html          # Order tracking page
│   ├── admin.html          # Kitchen dashboard
│   └── admin_login.html    # Admin login page
├── static/
│   ├── style.css           # Dark theme, Uber Eats tokens
│   └── script.js           # Cart, ordering, animations
├── requirements.txt
├── .env.example            # Template for environment variables
├── .gitignore
├── run.txt                 # Run instructions
└── README.md
```
