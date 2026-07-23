"""
Chendra Grill - Restaurant Ordering System
Flask backend with SQLite database
"""

import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify, g, session, redirect, url_for
from utils.database import get_db, close_db, init_db, init_app as db_init_app
from utils.auth import admin_required

app = Flask(__name__)

# ── Database path: /tmp on Vercel (writable), project dir locally ──
if os.environ.get('VERCEL'):
    app.config['DATABASE'] = '/tmp/chendra_grill.db'
else:
    app.config['DATABASE'] = os.path.join(os.path.dirname(__file__), 'chendra_grill.db')

# ── Security: require env vars ──
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-vercel')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'chendragrill2026')

# Warn in production if using defaults
if not os.environ.get('VERCEL') and app.secret_key == 'dev-secret-key-change-in-vercel':
    import warnings
    warnings.warn("Using default SECRET_KEY. Set SECRET_KEY env var in production.")

# Initialize database module with app config
db_init_app(app)

# Register teardown
app.teardown_appcontext(close_db)

# Initialize database tables on startup (needed for Vercel serverless)
init_db()


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


@app.route('/api/order/bulk-serve', methods=['POST'])
@admin_required
def bulk_serve_orders():
    """Mark all ready orders as served."""
    db = get_db()
    cursor = db.execute(
        "UPDATE orders SET status = 'served', updated_at = CURRENT_TIMESTAMP WHERE status IN ('pending', 'preparing', 'ready')"
    )
    db.commit()
    return jsonify({'success': True, 'count': cursor.rowcount})


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
@admin_required
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


@app.route('/api/admin/orders')
@admin_required
def admin_orders_api():
    """Get all orders as JSON for short polling."""
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

    return jsonify({
        'orders': [dict(o) for o in orders],
        'served_orders': [dict(o) for o in served_orders]
    })


@app.route('/admin/menu')
@admin_required
def admin_menu():
    db = get_db()
    categories = db.execute("SELECT * FROM categories ORDER BY id").fetchall()
    return render_template('admin_menu.html', categories=categories)


@app.route('/api/admin/menu')
@admin_required
def api_admin_menu():
    """Get all menu items with category names (including unavailable)."""
    db = get_db()
    items = [dict(r) for r in db.execute("""
        SELECT m.*, c.name as category_name
        FROM menu_items m
        JOIN categories c ON m.category_id = c.id
        ORDER BY c.id, m.name
    """).fetchall()]
    return jsonify({'items': items})


@app.route('/api/admin/menu', methods=['POST'])
@admin_required
def api_admin_menu_add():
    """Add a new menu item."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Data tidak valid'}), 400

    name = (data.get('name') or '').strip()
    description = (data.get('description') or '').strip()
    price = data.get('price')
    category_id = data.get('category_id')
    image_url = (data.get('image_url') or '').strip()

    if not name:
        return jsonify({'error': 'Nama menu wajib diisi'}), 400
    if not isinstance(price, (int, float)) or price <= 0:
        return jsonify({'error': 'Harga harus lebih dari 0'}), 400

    db = get_db()
    cat = db.execute("SELECT id FROM categories WHERE id = ?", (category_id,)).fetchone()
    if not cat:
        return jsonify({'error': 'Kategori tidak ditemukan'}), 400

    cursor = db.execute(
        "INSERT INTO menu_items (name, description, price, category_id, image_url) VALUES (?, ?, ?, ?, ?)",
        (name, description, int(price), category_id, image_url)
    )
    db.commit()

    return jsonify({'success': True, 'id': cursor.lastrowid, 'message': f'{name} berhasil ditambahkan'}), 201


@app.route('/api/admin/menu/<int:item_id>', methods=['PUT'])
@admin_required
def api_admin_menu_update(item_id):
    """Update an existing menu item."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Data tidak valid'}), 400

    name = (data.get('name') or '').strip()
    description = (data.get('description') or '').strip()
    price = data.get('price')
    category_id = data.get('category_id')
    image_url = (data.get('image_url') or '').strip()
    available = data.get('available', 1)

    if not name:
        return jsonify({'error': 'Nama menu wajib diisi'}), 400
    if not isinstance(price, (int, float)) or price <= 0:
        return jsonify({'error': 'Harga harus lebih dari 0'}), 400

    db = get_db()
    item = db.execute("SELECT id FROM menu_items WHERE id = ?", (item_id,)).fetchone()
    if not item:
        return jsonify({'error': 'Menu tidak ditemukan'}), 404

    cat = db.execute("SELECT id FROM categories WHERE id = ?", (category_id,)).fetchone()
    if not cat:
        return jsonify({'error': 'Kategori tidak ditemukan'}), 400

    db.execute(
        "UPDATE menu_items SET name=?, description=?, price=?, category_id=?, image_url=?, available=? WHERE id=?",
        (name, description, int(price), category_id, image_url, int(available), item_id)
    )
    db.commit()

    return jsonify({'success': True, 'message': f'{name} berhasil diupdate'})


@app.route('/api/admin/menu/<int:item_id>', methods=['DELETE'])
@admin_required
def api_admin_menu_delete(item_id):
    """Delete a menu item. If it has been ordered, set unavailable instead."""
    db = get_db()
    item = db.execute("SELECT * FROM menu_items WHERE id = ?", (item_id,)).fetchone()
    if not item:
        return jsonify({'error': 'Menu tidak ditemukan'}), 404

    # Check if item has been ordered
    ordered = db.execute(
        "SELECT COUNT(*) as c FROM order_items WHERE menu_item_id = ?", (item_id,)
    ).fetchone()['c']

    if ordered > 0:
        # Has orders — just mark unavailable
        db.execute("UPDATE menu_items SET available = 0 WHERE id = ?", (item_id,))
        db.commit()
        return jsonify({'success': True, 'soft_deleted': True, 'message': f'{item["name"]} dinonaktifkan (memiliki riwayat pesanan)'})
    else:
        db.execute("DELETE FROM menu_items WHERE id = ?", (item_id,))
        db.commit()
        return jsonify({'success': True, 'soft_deleted': False, 'message': f'{item["name"]} berhasil dihapus'})


@app.route('/api/admin/menu/<int:item_id>/toggle', methods=['PUT'])
@admin_required
def api_admin_menu_toggle(item_id):
    """Toggle availability of a menu item."""
    db = get_db()
    item = db.execute("SELECT * FROM menu_items WHERE id = ?", (item_id,)).fetchone()
    if not item:
        return jsonify({'error': 'Menu tidak ditemukan'}), 404

    new_val = 0 if item['available'] else 1
    db.execute("UPDATE menu_items SET available = ? WHERE id = ?", (new_val, item_id))
    db.commit()

    status = 'tersedia' if new_val else 'tidak tersedia'
    return jsonify({'success': True, 'available': new_val, 'message': f'{item["name"]} sekarang {status}'})


@app.template_filter('format_price')
def format_price(value):
    return f"Rp {value:,.0f}".replace(",", ".")


# ──────────────────────────────────────────────
# INIT & RUN
# ──────────────────────────────────────────────

if __name__ == '__main__':
    init_db()
    app.run(
        host='127.0.0.1',
        port=5002,
        debug=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    )
