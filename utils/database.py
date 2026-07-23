"""
Database helpers — SQLite with WAL mode.
"""

import sqlite3
from flask import g


DATABASE_PATH = None  # Set by init_app()


def init_app(app):
    """Configure database path from app config."""
    global DATABASE_PATH
    DATABASE_PATH = app.config['DATABASE']


def get_db():
    """Get or create a database connection for the current request."""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db


def close_db(exception):
    """Close the database connection at end of request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """Create tables and seed menu data if empty."""
    db = sqlite3.connect(DATABASE_PATH)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")

    db.executescript("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            icon TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS menu_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            price INTEGER NOT NULL,
            category_id INTEGER NOT NULL,
            image_url TEXT DEFAULT '',
            available INTEGER DEFAULT 1,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_number INTEGER NOT NULL,
            customer_name TEXT DEFAULT '',
            status TEXT DEFAULT 'pending' CHECK(status IN ('pending','preparing','ready','served')),
            total_price INTEGER DEFAULT 0,
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            menu_item_id INTEGER NOT NULL,
            quantity INTEGER DEFAULT 1,
            item_price INTEGER NOT NULL,
            notes TEXT DEFAULT '',
            FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
            FOREIGN KEY (menu_item_id) REFERENCES menu_items(id)
        );
    """)
    db.commit()

    # Seed categories + menu if empty
    cursor = db.execute("SELECT COUNT(*) FROM categories")
    if cursor.fetchone()[0] == 0:
        seed_menu(db)

    db.close()


def seed_menu(db):
    """Insert default categories and menu items."""
    categories = [
        ('Grill & BBQ', 'flame'),
        ('Nasi & Mie', 'utensils'),
        ('Minuman', 'cup-soda'),
        ('Snack & Appetizer', 'popcorn'),
        ('Dessert', 'ice-cream'),
    ]
    for name, icon in categories:
        db.execute("INSERT INTO categories (name, icon) VALUES (?, ?)", (name, icon))

    menu = [
        # Grill & BBQ (category_id=1)
        ('Ayam Bakar Madu', 'Ayam bakar dengan olesan madu, disajikan dengan sambal dan lalapan', 35000, 1, 'https://images.unsplash.com/photo-1598515214211-89d3c73ae83b?w=600&q=80'),
        ('Sapi Panggang Special', 'Daging sapi premium dipanggang dengan bumbu rahasia, served with BBQ sauce', 65000, 1, 'https://images.unsplash.com/photo-1558030006-450675393462?w=600&q=80'),
        ('Ikan Gurame Bakar', 'Gurame segar dibakar dengan bumbu kecap pedas manis', 55000, 1, 'https://images.unsplash.com/photo-1580476262798-bddd9f4b7369?w=600&q=80'),
        ('Sate Ayam (10 tusuk)', 'Sate ayam dengan bumbu kacang dan lontong', 30000, 1, 'https://images.unsplash.com/photo-1529563021893-cc83c992d75d?w=600&q=80'),
        ('Sate Kambing (10 tusuk)', 'Sate kambing premium dengan bumbu kecap', 45000, 1, 'https://images.unsplash.com/photo-1603360946369-dc9bb6a5032c?w=600&q=80'),
        ('Udang Bakar Madu', 'Udang segar dibakar dengan olesan madu dan butter', 50000, 1, 'https://images.unsplash.com/photo-1565557623262-b51c2513a641?w=600&q=80'),

        # Nasi & Mie (category_id=2)
        ('Nasi Goreng Spesial', 'Nasi goreng dengan telur, ayam, dan kerupuk', 25000, 2, 'https://images.unsplash.com/photo-1512058564366-18510be2db19?w=600&q=80'),
        ('Mie Goreng Tek-Tek', 'Mie goreng dengan sayuran dan telur', 22000, 2, 'https://images.unsplash.com/photo-1585032226651-759b368d7246?w=600&q=80'),
        ('Nasi Campur Bali', 'Nasi dengan lauk lengkap khas Bali', 35000, 2, 'https://images.unsplash.com/photo-1604908176997-125f25cc6f3d?w=600&q=80'),
        ('Kwetiau Goreng', 'Kwetiau goreng seafood dengan telur', 28000, 2, 'https://images.unsplash.com/photo-1555126634-323283e090fa?w=600&q=80'),

        # Minuman (category_id=3)
        ('Es Teh Manis', 'Teh manis dingin segar', 8000, 3, 'https://images.unsplash.com/photo-1499638673689-79a0b5115d87?w=600&q=80'),
        ('Es Jeruk Segar', 'Jeruk peras segar dengan es', 12000, 3, 'https://images.unsplash.com/photo-1621506289937-a8e4df240d0b?w=600&q=80'),
        ('Kopi Susu', 'Kopi robusta dengan susu segar', 15000, 3, 'https://images.unsplash.com/photo-1461023058943-07fcbe16d735?w=600&q=80'),
        ('Jus Alpukat', 'Jus alpukat segar dengan susu coklat', 18000, 3, 'https://images.unsplash.com/photo-1623065422902-30a2d299bbe4?w=600&q=80'),
        ('Air Mineral', 'Air mineral botol', 5000, 3, 'https://images.unsplash.com/photo-1548839140-29a749e1cf4d?w=600&q=80'),

        # Snack & Appetizer (category_id=4)
        ('Pisang Goreng Crispy', 'Pisang goreng tepung renyah (5 pcs)', 15000, 4, 'https://images.unsplash.com/photo-1587132137056-bfbf0166836e?w=600&q=80'),
        ('Tempe Mendoan', 'Tempe mendoan dengan sambal kecap (5 pcs)', 12000, 4, 'https://images.unsplash.com/photo-1585032226651-759b368d7246?w=600&q=80'),
        ('Tahu Crispy', 'Tahu goreng crispy dengan sambal (5 pcs)', 12000, 4, 'https://images.unsplash.com/photo-1585032226651-759b368d7246?w=600&q=80'),
        ('Roti Bakar', 'Roti bakar dengan butter dan meses', 15000, 4, 'https://images.unsplash.com/photo-1509440159596-0249088772ff?w=600&q=80'),

        # Dessert (category_id=5)
        ('Es Campur', 'Es campur dengan berbagai topping', 18000, 5, 'https://images.unsplash.com/photo-1563805042-7684c019e1cb?w=600&q=80'),
        ('Pisang Ijo', 'Pisang ijo khas Makassar', 15000, 5, 'https://images.unsplash.com/photo-1571091718767-18b5b1457add?w=600&q=80'),
        ('Klepon', 'Klepon isi gula merah (5 pcs)', 10000, 5, 'https://images.unsplash.com/photo-1558961363-fa8fdf82db35?w=600&q=80'),
    ]
    for name, desc, price, cat_id, img in menu:
        db.execute(
            "INSERT INTO menu_items (name, description, price, category_id, image_url) VALUES (?, ?, ?, ?, ?)",
            (name, desc, price, cat_id, img)
        )
    db.commit()
