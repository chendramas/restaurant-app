"""
Chendra Grill - Restaurant Ordering System
Flask backend with SQLite database
"""

import sqlite3
import os
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, jsonify, g, session, redirect, url_for

app = Flask(__name__)
app.config['DATABASE'] = os.path.join(os.path.dirname(__file__), 'chendra_grill.db')
app.secret_key = os.environ.get('SECRET_KEY', 'chendra-grill-secret-key-change-in-production')

# Admin password — change via env var ADMIN_PASSWORD
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'chendragrill2026')


# ──────────────────────────────────────────────
# DATABASE
# ──────────────────────────────────────────────

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(app.config['DATABASE'])
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


# ──────────────────────────────────────────────
# AUTH HELPERS
# ──────────────────────────────────────────────

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated


# ──────────────────────────────────────────────
# ROUTES - PAGES
# ──────────────────────────────────────────────

@app.route('/')
def index():
    db = get_db()
    categories = db.execute("SELECT * FROM categories ORDER BY id").fetchall()
    menu_items = db.execute("""
        SELECT m.*, c.name as category_name
        FROM menu_items m
        JOIN categories c ON m.category_id = c.id
        WHERE m.available = 1
        ORDER BY c.id, m.name
    """).fetchall()
    tables = list(range(1, 21))  # 20 tables
    return render_template('index.html', categories=categories, menu_items=menu_items, tables=tables)


@app.route('/track')
def track():
    return render_template('track.html')


@app.route('/track/<int:order_id>')
def track_order(order_id):
    return render_template('track.html', order_id=order_id)


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == ADMIN_PASSWORD:
            session['is_admin'] = True
            return redirect(url_for('admin'))
        error = 'Password salah'
    return render_template('admin_login.html', error=error)


@app.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    return redirect(url_for('index'))


@app.route('/admin')
@admin_required
def admin():
    db = get_db()
    orders = db.execute("""
        SELECT o.*, GROUP_CONCAT(m.name || ' x' || oi.quantity, ', ') as items_summary
        FROM orders o
        JOIN order_items oi ON o.id = oi.order_id
        JOIN menu_items m ON oi.menu_item_id = m.id
        WHERE o.status != 'served'
        GROUP BY o.id
        ORDER BY CASE o.status
            WHEN 'pending' THEN 1
            WHEN 'preparing' THEN 2
            WHEN 'ready' THEN 3
        END, o.created_at ASC
    """).fetchall()

    served_orders = db.execute("""
        SELECT o.*, GROUP_CONCAT(m.name || ' x' || oi.quantity, ', ') as items_summary
        FROM orders o
        JOIN order_items oi ON o.id = oi.order_id
        JOIN menu_items m ON oi.menu_item_id = m.id
        WHERE o.status = 'served'
        GROUP BY o.id
        ORDER BY o.updated_at DESC
        LIMIT 20
    """).fetchall()

    return render_template('admin.html', orders=orders, served_orders=served_orders)


# ──────────────────────────────────────────────
# API ENDPOINTS
# ──────────────────────────────────────────────

@app.route('/api/menu')
def api_menu():
    db = get_db()
    categories = [dict(r) for r in db.execute("SELECT * FROM categories ORDER BY id").fetchall()]
    items = [dict(r) for r in db.execute("""
        SELECT m.*, c.name as category_name
        FROM menu_items m
        JOIN categories c ON m.category_id = c.id
        WHERE m.available = 1
        ORDER BY c.id, m.name
    """).fetchall()]
    return jsonify({'categories': categories, 'items': items})


@app.route('/api/order', methods=['POST'])
def create_order():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Data tidak valid'}), 400

    table_number = data.get('table_number')
    customer_name = data.get('customer_name', '').strip()
    items = data.get('items', [])
    notes = data.get('notes', '').strip()

    if not table_number:
        return jsonify({'error': 'Nomor meja wajib diisi'}), 400
    if not items:
        return jsonify({'error': 'Pesanan tidak boleh kosong'}), 400

    db = get_db()
    total = 0
    order_items_data = []

    for item in items:
        menu_item = db.execute("SELECT * FROM menu_items WHERE id = ? AND available = 1", (item['id'],)).fetchone()
        if not menu_item:
            return jsonify({'error': f'Menu item ID {item["id"]} tidak ditemukan'}), 400
        qty = max(1, int(item.get('quantity', 1)))
        item_notes = item.get('notes', '').strip()
        subtotal = menu_item['price'] * qty
        total += subtotal
        order_items_data.append((item['id'], qty, menu_item['price'], item_notes))

    cursor = db.execute(
        "INSERT INTO orders (table_number, customer_name, total_price, notes) VALUES (?, ?, ?, ?)",
        (table_number, customer_name, total, notes)
    )
    order_id = cursor.lastrowid

    for item_id, qty, price, item_notes in order_items_data:
        db.execute(
            "INSERT INTO order_items (order_id, menu_item_id, quantity, item_price, notes) VALUES (?, ?, ?, ?, ?)",
            (order_id, item_id, qty, price, item_notes)
        )

    db.commit()

    return jsonify({
        'success': True,
        'order_id': order_id,
        'total_price': total,
        'message': f'Pesanan #{order_id} berhasil dibuat!'
    }), 201


@app.route('/api/order/<int:order_id>')
def get_order(order_id):
    db = get_db()
    order = db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not order:
        return jsonify({'error': 'Pesanan tidak ditemukan'}), 404

    items = db.execute("""
        SELECT oi.*, m.name, m.description
        FROM order_items oi
        JOIN menu_items m ON oi.menu_item_id = m.id
        WHERE oi.order_id = ?
    """, (order_id,)).fetchall()

    return jsonify({
        'order': dict(order),
        'items': [dict(i) for i in items]
    })


@app.route('/api/order/<int:order_id>/status', methods=['PUT'])
def update_order_status(order_id):
    data = request.get_json()
    new_status = data.get('status')
    valid_statuses = ['pending', 'preparing', 'ready', 'served']

    if new_status not in valid_statuses:
        return jsonify({'error': 'Status tidak valid'}), 400

    db = get_db()
    order = db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not order:
        return jsonify({'error': 'Pesanan tidak ditemukan'}), 404

    db.execute(
        "UPDATE orders SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (new_status, order_id)
    )
    db.commit()

    return jsonify({'success': True, 'status': new_status})


@app.route('/api/table/<int:table_number>/orders')
def get_table_orders(table_number):
    db = get_db()
    orders = db.execute("""
        SELECT o.*,
            GROUP_CONCAT(m.name || ' x' || oi.quantity, ', ') as items_summary
        FROM orders o
        JOIN order_items oi ON o.id = oi.order_id
        JOIN menu_items m ON oi.menu_item_id = m.id
        WHERE o.table_number = ?
        GROUP BY o.id
        ORDER BY o.created_at DESC
    """, (table_number,)).fetchall()

    result = []
    for order in orders:
        items = db.execute("""
            SELECT oi.*, m.name, m.description
            FROM order_items oi
            JOIN menu_items m ON oi.menu_item_id = m.id
            WHERE oi.order_id = ?
        """, (order['id'],)).fetchall()
        result.append({
            'order': dict(order),
            'items': [dict(i) for i in items]
        })

    return jsonify({'orders': result})


@app.route('/api/admin/stats')
def admin_stats():
    db = get_db()
    pending = db.execute("SELECT COUNT(*) as c FROM orders WHERE status='pending'").fetchone()['c']
    preparing = db.execute("SELECT COUNT(*) as c FROM orders WHERE status='preparing'").fetchone()['c']
    ready = db.execute("SELECT COUNT(*) as c FROM orders WHERE status='ready'").fetchone()['c']
    served_today = db.execute("SELECT COUNT(*) as c FROM orders WHERE status='served' AND DATE(created_at)=DATE('now')").fetchone()['c']
    revenue_today = db.execute("SELECT COALESCE(SUM(total_price),0) as r FROM orders WHERE status='served' AND DATE(created_at)=DATE('now')").fetchone()['r']

    return jsonify({
        'pending': pending,
        'preparing': preparing,
        'ready': ready,
        'served_today': served_today,
        'revenue_today': revenue_today
    })


@app.template_filter('format_price')
def format_price(value):
    return f"Rp {value:,.0f}".replace(",", ".")


# ──────────────────────────────────────────────
# INIT & RUN
# ──────────────────────────────────────────────

if __name__ == '__main__':
    init_db()
    app.run(host='127.0.0.1', port=5002, debug=True)
