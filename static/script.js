/* ═══════════════════════════════════════════
   CHENDRA GRILL — Frontend JS
   Uber Eats style interactions
   Motion.dev inspired: IntersectionObserver + spring
   ═══════════════════════════════════════════ */

let selectedTable = null;
let cart = [];

// ─── INIT ───
document.addEventListener('DOMContentLoaded', () => {
    // Hamburger
    const hamburger = document.getElementById('hamburger');
    if (hamburger) {
        hamburger.addEventListener('click', () => {
            document.querySelector('.nav-links').classList.toggle('open');
        });
    }

    // Restore state
    const savedCart = localStorage.getItem('cg_cart');
    const savedTable = localStorage.getItem('cg_table');
    if (savedCart) { cart = JSON.parse(savedCart); updateCartUI(); }
    if (savedTable) { selectTable(parseInt(savedTable)); }

    // IntersectionObserver — Motion.dev scroll reveal
    initScrollAnimations();
});

// ─── SCROLL ANIMATIONS (Motion.dev pattern) ───
function initScrollAnimations() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '0px 0px -40px 0px'
    });

    document.querySelectorAll('.reveal, .reveal-stagger').forEach(el => {
        observer.observe(el);
    });
}

// ─── TABLE SELECTION ───
function selectTable(num) {
    selectedTable = num;
    localStorage.setItem('cg_table', num);
    document.querySelectorAll('.table-card').forEach(btn => {
        btn.classList.toggle('selected', parseInt(btn.dataset.table) === num);
    });
    const display = document.getElementById('selectedTableDisplay');
    if (display) {
        display.classList.add('show');
        document.getElementById('selectedTableNum').textContent = num;
    }
}

function clearTable() {
    selectedTable = null;
    localStorage.removeItem('cg_table');
    document.querySelectorAll('.table-card').forEach(btn => btn.classList.remove('selected'));
    const display = document.getElementById('selectedTableDisplay');
    if (display) display.classList.remove('show');
}

// ─── CATEGORY FILTER ───
function filterCategory(catId) {
    document.querySelectorAll('.cat-pill').forEach(btn => {
        btn.classList.toggle('active',
            (catId === 'all' && btn.dataset.cat === 'all') ||
            (catId !== 'all' && parseInt(btn.dataset.cat) === catId)
        );
    });

    // Filter both featured and grid cards
    document.querySelectorAll('.menu-featured, .menu-card').forEach(card => {
        if (catId === 'all') {
            card.classList.remove('hidden');
        } else {
            card.classList.toggle('hidden', parseInt(card.dataset.cat) !== catId);
        }
    });
}

// ─── CART ───
function addToCart(id, name, price) {
    const existing = cart.find(item => item.id === id);
    if (existing) {
        existing.quantity++;
    } else {
        cart.push({ id, name, price, quantity: 1 });
    }
    saveCart();
    updateCartUI();
    showToast(`${name} ditambahkan`, 'success');

    // Spring bounce feedback (Motion.dev cubic-bezier)
    const card = document.querySelector(`[data-id="${id}"] .btn-add, [data-id="${id}"] .btn-primary`);
    if (card) {
        const orig = card.innerHTML;
        card.classList.add('added');
        card.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6 9 17l-5-5"/></svg> Ditambahkan';
        setTimeout(() => {
            card.classList.remove('added');
            card.innerHTML = orig;
        }, 800);
    }
}

function updateQuantity(id, delta) {
    const item = cart.find(i => i.id === id);
    if (!item) return;
    item.quantity += delta;
    if (item.quantity <= 0) cart = cart.filter(i => i.id !== id);
    saveCart();
    updateCartUI();
}

function saveCart() {
    localStorage.setItem('cg_cart', JSON.stringify(cart));
}

function updateCartUI() {
    const badge = document.getElementById('cartBadge');
    const cartFloat = document.getElementById('cartFloat');
    const cartItems = document.getElementById('cartItems');
    const cartEmpty = document.getElementById('cartEmpty');
    const cartFooter = document.getElementById('cartFooter');
    const cartTotal = document.getElementById('cartTotal');

    const totalItems = cart.reduce((s, i) => s + i.quantity, 0);
    const totalPrice = cart.reduce((s, i) => s + (i.price * i.quantity), 0);

    if (badge) badge.textContent = totalItems;
    if (cartFloat) cartFloat.style.display = totalItems > 0 ? 'block' : 'none';
    if (cartEmpty) cartEmpty.style.display = cart.length === 0 ? 'flex' : 'none';
    if (cartFooter) cartFooter.style.display = cart.length > 0 ? 'block' : 'none';

    if (cartItems) {
        cartItems.innerHTML = cart.map(item => `
            <div class="cart-item">
                <div class="cart-item-info">
                    <div class="cart-item-name">${item.name}</div>
                    <div class="cart-item-price">Rp ${(item.price * item.quantity).toLocaleString('id-ID').replace(/,/g, '.')}</div>
                </div>
                <div class="cart-item-controls">
                    <button class="qty-btn" onclick="updateQuantity(${item.id}, -1)">−</button>
                    <span class="qty-value">${item.quantity}</span>
                    <button class="qty-btn" onclick="updateQuantity(${item.id}, 1)">+</button>
                </div>
            </div>
        `).join('');
    }

    if (cartTotal) {
        cartTotal.textContent = `Rp ${totalPrice.toLocaleString('id-ID').replace(/,/g, '.')}`;
    }
}

function toggleCart() {
    const panel = document.getElementById('cartPanel');
    const overlay = document.getElementById('cartOverlay');
    const isOpen = panel.classList.contains('open');
    if (isOpen) {
        panel.classList.remove('open');
        overlay.classList.remove('open');
        document.body.style.overflow = '';
    } else {
        panel.classList.add('open');
        overlay.classList.add('open');
        document.body.style.overflow = 'hidden';
    }
}

// ─── PLACE ORDER ───
async function placeOrder() {
    if (!selectedTable) {
        showToast('Pilih nomor meja terlebih dahulu!', 'error');
        toggleCart();
        document.getElementById('table-section').scrollIntoView({ behavior: 'smooth' });
        return;
    }
    if (cart.length === 0) { showToast('Keranjang kosong!', 'error'); return; }

    const btn = document.getElementById('btnOrder');
    btn.disabled = true;
    btn.textContent = 'Memproses...';

    try {
        const res = await fetch('/api/order', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                table_number: selectedTable,
                customer_name: document.getElementById('customerName').value.trim(),
                items: cart.map(i => ({ id: i.id, quantity: i.quantity })),
                notes: document.getElementById('orderNotes').value.trim()
            })
        });
        const data = await res.json();
        if (data.success) {
            cart = [];
            saveCart();
            updateCartUI();
            toggleCart();

            document.getElementById('modalDesc').textContent =
                `Pesanan #${data.order_id} berhasil dibuat untuk Meja ${selectedTable}. Total: Rp ${data.total_price.toLocaleString('id-ID').replace(/,/g, '.')}`;
            document.getElementById('modalTrackBtn').href = `/track/${data.order_id}`;
            document.getElementById('orderModal').style.display = 'flex';

            document.getElementById('customerName').value = '';
            document.getElementById('orderNotes').value = '';
        } else {
            showToast(data.error || 'Gagal membuat pesanan', 'error');
        }
    } catch (e) {
        showToast('Gagal menghubungi server', 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><path d="m9 11 3 3L22 4"/></svg> Pesan Sekarang';
    }
}

function closeModal() {
    document.getElementById('orderModal').style.display = 'none';
}

// ─── TOAST ───
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
        toast.classList.add('toast-out');
        setTimeout(() => toast.remove(), 200);
    }, 3000);
}
