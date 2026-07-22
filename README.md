# Chendra Grill

Restaurant ordering system. Customers browse the menu, select their table, place orders, and track order status in real-time. Kitchen staff manage orders through an admin dashboard.

## Features

- **Menu browsing** with category filters and food photos
- **Table selection** with visual floor-map style cards
- **Order placement** with cart, notes, and customer name
- **Order tracking** by order ID or table number with progress visualization
- **Kitchen dashboard** (admin-protected) with status management and daily stats
- **Auto-refresh** on tracking and admin pages

## Tech Stack

- Python / Flask
- SQLite (WAL mode)
- Vanilla HTML / CSS / JS
- Dark theme with Uber Eats-inspired design tokens

## Run

```bash
cd chendra-grill
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5002

## Pages

| Route | Description |
|-------|-------------|
| `/` | Menu & ordering |
| `/track` | Order tracking (by ID or table) |
| `/admin/login` | Admin login |
| `/admin` | Kitchen dashboard (auth required) |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ADMIN_PASSWORD` | `chendragrill2026` | Admin dashboard password |
| `SECRET_KEY` | `chendra-grill-secret-key...` | Flask session secret |

## Project Structure

```
chendra-grill/
├── app.py                  # Flask app, routes, API, DB
├── requirements.txt
├── .gitignore
├── templates/
│   ├── base.html           # Base layout, nav, footer
│   ├── index.html          # Menu & ordering page
│   ├── track.html          # Order tracking page
│   ├── admin.html          # Kitchen dashboard
│   └── admin_login.html    # Admin login page
└── static/
    ├── style.css           # Dark theme, Uber Eats tokens
    └── script.js           # Cart, ordering, animations
```
