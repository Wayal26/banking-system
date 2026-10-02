
import os
import re
import sqlite3
import hashlib
import secrets
from datetime import datetime

import streamlit as st

DB_FILE = "banking_system.db"
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "Pruthvi")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Way@2007")

st.set_page_config(
    page_title="Banking System",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------- Styling -----------------------------
st.markdown("""
<style>
    .stApp {
        background: #080e1d;
        color: #f4f7fb;
    }
    [data-testid="stHeader"] { background: rgba(8,14,29,0.95); }
    [data-testid="stSidebar"] {
        background: #0d1426;
        border-right: 1px solid #202b45;
    }
    .hero {
        background: linear-gradient(135deg,#131e36,#0d1527);
        border: 1px solid #273452;
        border-radius: 18px;
        padding: 24px;
        margin-bottom: 18px;
    }
    .hero h1 { margin: 0 0 8px 0; }
    .muted { color:#9aa8c2; }
    .card {
        background:#111a2f;
        border:1px solid #263452;
        border-radius:16px;
        padding:18px;
        min-height:120px;
    }
    .card h3 { margin:0 0 8px 0; }
    .metric-value { font-size:28px; font-weight:800; }
    .success-box {
        background:#0d2b20;
        border:1px solid #1d6a4c;
        border-radius:12px;
        padding:14px;
    }
    .warning-box {
        background:#30280e;
        border:1px solid #7a6517;
        border-radius:12px;
        padding:14px;
    }
    .danger-box {
        background:#35151a;
        border:1px solid #7c2b35;
        border-radius:12px;
        padding:14px;
    }
    .info-box {
        background:#10233e;
        border:1px solid #28507e;
        border-radius:12px;
        padding:14px;
    }
    div[data-testid="stForm"] {
        background:#0e1629;
        border:1px solid #273452;
        border-radius:14px;
        padding:18px;
    }
    .small { font-size:13px; color:#9aa8c2; }
    .status-pill {
        display:inline-block;
        padding:5px 10px;
        border-radius:999px;
        font-size:12px;
        font-weight:700;
        background:#1c2943;
    }
    .footer {
        text-align:center;
        color:#65738e;
        font-size:12px;
        padding:30px 0 10px;
    }
</style>
""", unsafe_allow_html=True)


# ----------------------------- Database -----------------------------
def get_conn():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
    PRAGMA foreign_keys = ON;

    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id TEXT UNIQUE NOT NULL,
        account_number TEXT UNIQUE NOT NULL,
        full_name TEXT NOT NULL,
        phone TEXT NOT NULL,
        pin_hash TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Pending',
        rejection_reason TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        balance REAL NOT NULL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS account_rejection_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        full_name TEXT NOT NULL,
        phone TEXT NOT NULL,
        reason TEXT NOT NULL,
        rejected_at TEXT NOT NULL,
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    );

    CREATE TABLE IF NOT EXISTS deposits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'Pending',
        rejection_reason TEXT,
        requested_at TEXT NOT NULL,
        decided_at TEXT,
        previous_request_id INTEGER,
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    );

    CREATE TABLE IF NOT EXISTS deposit_rejection_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        deposit_id INTEGER NOT NULL,
        customer_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        reason TEXT NOT NULL,
        rejected_at TEXT NOT NULL,
        FOREIGN KEY(deposit_id) REFERENCES deposits(id),
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    );

    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        transaction_type TEXT NOT NULL,
        amount REAL NOT NULL,
        description TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    );

    CREATE INDEX IF NOT EXISTS idx_customers_status ON customers(status);
    CREATE INDEX IF NOT EXISTS idx_deposits_status ON deposits(status);
    CREATE INDEX IF NOT EXISTS idx_transactions_customer ON transactions(customer_id);
    """)
    conn.commit()
    conn.close()


init_db()


# ----------------------------- Helpers -----------------------------
def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def hash_pin(pin):
    return hashlib.sha256(pin.encode("utf-8")).hexdigest()


def verify_pin(pin, pin_hash):
    return secrets.compare_digest(hash_pin(pin), pin_hash)


def valid_phone(phone):
    return bool(re.fullmatch(r"[6-9]\d{9}", phone))


def valid_pin(pin):
    return bool(re.fullmatch(r"\d{4}", pin))


def money(v):
    return f"₹{float(v):,.2f}"


def generate_application_id(conn):
    while True:
        value = "APP" + datetime.now().strftime("%Y%m%d") + secrets.token_hex(3).upper()
        if conn.execute("SELECT 1 FROM customers WHERE application_id=?", (value,)).fetchone() is None:
            return value


def generate_account_number(conn):
    while True:
        value = "AC" + "".join(str(secrets.randbelow(10)) for _ in range(10))
        if conn.execute("SELECT 1 FROM customers WHERE account_number=?", (value,)).fetchone() is None:
            return value


def get_customer(customer_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM customers WHERE id=?", (customer_id,)).fetchone()
    conn.close()
    return row


def status_message(status):
    return {
        "Pending": "Your application is waiting for admin approval.",
        "Approved": "Your account has been approved. You can now login.",
        "Rejected": "Your application was rejected.",
    }.get(status, "")


def reset_customer_session():
    for key in ["customer_id", "customer_logged_in", "customer_section"]:
        st.session_state.pop(key, None)


def reset_admin_session():
    for key in ["admin_logged_in", "admin_section"]:
        st.session_state.pop(key, None)


# ----------------------------- Header -----------------------------
def header():
    st.markdown("""
    <div class="hero">
        <h1>🏦 Banking System</h1>
        <div class="muted">A modern banking management mini project with customer and admin portals.</div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="card"><div class="small">STORAGE</div><h3>SQLite</h3><div class="small">Local database</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="card"><div class="small">FRONTEND</div><h3>Streamlit</h3><div class="small">Responsive web interface</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="card"><div class="small">LANGUAGE</div><h3>Python</h3><div class="small">Simple and maintainable</div></div>', unsafe_allow_html=True)


# ----------------------------- Create Account -----------------------------
def create_account():
    st.subheader("📝 Create Account")
    st.info("Create an account, wait for admin approval, then use the generated account number to login.")

    with st.form("create_account_form"):
        name = st.text_input("Full Name")
        phone = st.text_input("10-digit Phone Number", max_chars=10)
        pin = st.text_input("4-digit PIN", type="password", max_chars=4)
        submitted = st.form_submit_button("Create Account", use_container_width=True)

    if submitted:
        name = name.strip()
        phone = phone.strip()
        pin = pin.strip()

        if not name:
            st.error("Please enter your full name.")
            return
        if not valid_phone(phone):
            st.error("Enter a valid 10-digit Indian phone number.")
            return
        if not valid_pin(pin):
            st.error("PIN must contain exactly 4 digits.")
            return

        conn = get_conn()
        if conn.execute("SELECT 1 FROM customers WHERE phone=? AND status!='Rejected'", (phone,)).fetchone():
            conn.close()
            st.error("An active application/account already exists for this phone number.")
            return

        application_id = generate_application_id(conn)
        account_number = generate_account_number(conn)
        created = now()
        conn.execute("""
            INSERT INTO customers
            (application_id, account_number, full_name, phone, pin_hash, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 'Pending', ?, ?)
        """, (application_id, account_number, name, phone, hash_pin(pin), created, created))
        conn.commit()
        conn.close()

        st.success("Your account has been created successfully. Please wait for admin approval.")
        st.markdown(f"""
        <div class="info-box">
            <b>Application ID:</b> {application_id}<br>
            <b>Account Number:</b> {account_number}<br>
            <b>Status:</b> Pending
        </div>
        """, unsafe_allow_html=True)


# ----------------------------- Customer Login -----------------------------
def customer_login():
    st.subheader("👤 Customer Login")

    with st.form("customer_login_form"):
        account = st.text_input("Account Number")
        pin = st.text_input("4-digit PIN", type="password", max_chars=4)
        submitted = st.form_submit_button("Login", use_container_width=True)

    if submitted:
        account = account.strip()
        pin = pin.strip()
        conn = get_conn()
        row = conn.execute("SELECT * FROM customers WHERE account_number=?", (account,)).fetchone()
        conn.close()

        if row is None or not verify_pin(pin, row["pin_hash"]):
            st.error("Invalid account number or PIN.")
            return

        if row["status"] != "Approved":
            st.warning(f"Account status: {row['status']}. {status_message(row['status'])}")
            return

        st.session_state.customer_logged_in = True
        st.session_state.customer_id = row["id"]
        st.session_state.customer_section = "🏠 Dashboard"
        st.rerun()


# ----------------------------- Application Status -----------------------------
def application_status():
    st.subheader("🔎 Application Status")

    with st.form("status_form"):
        lookup = st.text_input("Account Number or Application ID")
        submitted = st.form_submit_button("Check Status", use_container_width=True)

    if submitted:
        lookup = lookup.strip()
        conn = get_conn()
        row = conn.execute("""
            SELECT * FROM customers
            WHERE account_number=? OR application_id=?
            ORDER BY id DESC LIMIT 1
        """, (lookup, lookup)).fetchone()
        conn.close()

        if row is None:
            st.error("No application/account found.")
            return
        st.session_state.status_customer_id = row["id"]

    customer_id = st.session_state.get("status_customer_id")
    if not customer_id:
        return

    row = get_customer(customer_id)
    if not row:
        return

    st.markdown(f"""
    <div class="card">
        <h3>👤 {row['full_name']}</h3>
        <p><b>Account Number:</b> {row['account_number']}</p>
        <p><b>Application ID:</b> {row['application_id']}</p>
        <p><b>Application Date:</b> {row['created_at']}</p>
        <p><b>Current Status:</b> <span class="status-pill">{row['status']}</span></p>
    </div>
    """, unsafe_allow_html=True)

    if row["status"] == "Pending":
        st.info("⏳ Pending\n\nYour application is waiting for admin approval.")
    elif row["status"] == "Approved":
        st.success("✅ Approved\n\nYour account has been approved. You can now login.")
    elif row["status"] == "Rejected":
        st.error("❌ Rejected\n\nYour application was rejected.")
        st.markdown(f"""
        <div class="danger-box">
            <b>Reason:</b> {row['rejection_reason'] or 'No reason provided.'}
        </div>
        """, unsafe_allow_html=True)

        st.markdown("### 🔄 Resubmit Application")
        st.caption("Previous rejection remains in admin history. Resubmission creates a new pending review while keeping the same account number.")

        with st.form("resubmit_account_form"):
            new_name = st.text_input("👤 Full Name", value=row["full_name"])
            new_phone = st.text_input("📱 Phone Number", value=row["phone"], max_chars=10)
            new_pin = st.text_input("🔐 New 4-digit PIN", type="password", max_chars=4)
            submit_resubmit = st.form_submit_button("🔄 Resubmit Application", use_container_width=True)

        if submit_resubmit:
            new_name = new_name.strip()
            new_phone = new_phone.strip()
            new_pin = new_pin.strip()

            if not new_name or not valid_phone(new_phone) or not valid_pin(new_pin):
                st.error("Enter a valid name, 10-digit phone number and 4-digit PIN.")
                return

            conn = get_conn()
            duplicate = conn.execute("""
                SELECT id FROM customers
                WHERE phone=? AND id!=? AND status IN ('Pending','Approved')
            """, (new_phone, row["id"])).fetchone()

            if duplicate:
                conn.close()
                st.error("That phone number is already linked to another active application/account.")
                return

            conn.execute("""
                INSERT INTO account_rejection_history
                (customer_id, full_name, phone, reason, rejected_at)
                VALUES (?, ?, ?, ?, ?)
            """, (row["id"], row["full_name"], row["phone"], row["rejection_reason"] or "Rejected", now()))

            conn.execute("""
                UPDATE customers
                SET full_name=?, phone=?, pin_hash=?, status='Pending',
                    rejection_reason=NULL, updated_at=?
                WHERE id=?
            """, (new_name, new_phone, hash_pin(new_pin), now(), row["id"]))
            conn.commit()
            conn.close()

            st.success("Application resubmitted successfully. Status changed from Rejected → Pending.")
            st.rerun()


# ----------------------------- Customer Portal -----------------------------
def customer_dashboard(customer):
    st.sidebar.markdown("## 👤 Customer Portal")
    section = st.sidebar.radio(
        "Customer Menu",
        ["🏠 Dashboard", "💰 Deposit", "💸 Withdraw", "🔄 Transfer",
         "📜 Transaction History", "👤 Account Information", "🚪 Logout"],
        key="customer_section"
    )

    if section == "🚪 Logout":
        reset_customer_session()
        st.rerun()

    customer = get_customer(customer["id"])
    if not customer:
        reset_customer_session()
        st.rerun()

    conn = get_conn()
    transaction_count = conn.execute(
        "SELECT COUNT(*) AS c FROM transactions WHERE customer_id=?", (customer["id"],)
    ).fetchone()["c"]
    pending_deposits = conn.execute(
        "SELECT COUNT(*) AS c FROM deposits WHERE customer_id=? AND status='Pending'", (customer["id"],)
    ).fetchone()["c"]
    conn.close()

    if section == "🏠 Dashboard":
        st.title(f"🏠 Welcome, {customer['full_name']}")
        a,b,c,d = st.columns(4)
        with a:
            st.metric("Account Number", customer["account_number"])
        with b:
            st.metric("Account Status", customer["status"])
        with c:
            st.metric("Available Balance", money(customer["balance"]))
        with d:
            st.metric("Transaction Count", transaction_count)

        st.markdown(f"""
        <div class="info-box">
            <b>Pending deposits:</b> {pending_deposits}<br>
            <span class="small">Deposits are added to your balance only after admin approval.</span>
        </div>
        """, unsafe_allow_html=True)

    elif section == "💰 Deposit":
        deposit_section(customer)

    elif section == "💸 Withdraw":
        withdraw_section(customer)

    elif section == "🔄 Transfer":
        transfer_section(customer)

    elif section == "📜 Transaction History":
        transaction_history(customer)

    elif section == "👤 Account Information":
        st.title("👤 Account Information")
        st.write(f"**Name:** {customer['full_name']}")
        st.write(f"**Phone:** {customer['phone']}")
        st.write(f"**Account Number:** {customer['account_number']}")
        st.write(f"**Account Status:** {customer['status']}")
        st.write(f"**Account Creation Date:** {customer['created_at']}")
        st.write(f"**Available Balance:** {money(customer['balance'])}")

    st.markdown('<div class="footer">Educational/college mini project. Do not use real financial information.</div>', unsafe_allow_html=True)


# ----------------------------- Deposit -----------------------------
def deposit_section(customer):
    st.title("💰 Deposit")

    with st.form("deposit_form"):
        amount = st.number_input("Enter amount", min_value=1.0, step=100.0, format="%.2f")
        submit = st.form_submit_button("Submit Deposit Request", use_container_width=True)

    if submit:
        conn = get_conn()
        conn.execute("""
            INSERT INTO deposits (customer_id, amount, status, requested_at)
            VALUES (?, ?, 'Pending', ?)
        """, (customer["id"], amount, now()))
        conn.commit()
        conn.close()
        st.success("Your deposit request is waiting for admin approval.")
        st.rerun()

    st.markdown("### Deposit Requests")
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM deposits
        WHERE customer_id=?
        ORDER BY id DESC
    """, (customer["id"],)).fetchall()
    conn.close()

    for row in rows:
        st.markdown(f"**{money(row['amount'])}** — {row['status']} — {row['requested_at']}")
        if row["status"] == "Pending":
            st.info("⏳ Pending\n\nYour deposit request is waiting for admin approval.")
        elif row["status"] == "Approved":
            st.success("✅ Approved\n\nYour deposit has been approved and added to your account balance.")
        elif row["status"] == "Rejected":
            st.error("❌ Rejected\n\nYour deposit request was rejected.")
            st.markdown(f"**Reason:** {row['rejection_reason'] or 'No reason provided.'}")

            with st.form(f"resubmit_deposit_{row['id']}"):
                new_amount = st.number_input(
                    "Resubmit Deposit Request — Amount",
                    min_value=1.0,
                    value=float(row["amount"]),
                    step=100.0,
                    format="%.2f",
                    key=f"dep_amt_{row['id']}"
                )
                resubmit = st.form_submit_button("🔄 Resubmit Deposit Request", use_container_width=True)

            if resubmit:
                conn = get_conn()
                conn.execute("""
                    INSERT INTO deposits
                    (customer_id, amount, status, requested_at, previous_request_id)
                    VALUES (?, ?, 'Pending', ?, ?)
                """, (customer["id"], new_amount, now(), row["id"]))
                conn.commit()
                conn.close()
                st.success("Deposit request resubmitted. Balance will NOT increase until admin approves it.")
                st.rerun()


# ----------------------------- Withdraw -----------------------------
def withdraw_section(customer):
    st.title("💸 Withdraw")
    st.info(f"Available balance: {money(customer['balance'])}")

    with st.form("withdraw_form"):
        amount = st.number_input("Enter amount", min_value=1.0, step=100.0, format="%.2f")
        submit = st.form_submit_button("Withdraw Money", use_container_width=True)

    if submit:
        conn = get_conn()
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT balance FROM customers WHERE id=?", (customer["id"],)).fetchone()

        if row is None or amount > row["balance"]:
            conn.rollback()
            conn.close()
            st.error("Insufficient available balance.")
            return

        conn.execute("UPDATE customers SET balance=?, updated_at=? WHERE id=?",
                     (row["balance"] - amount, now(), customer["id"]))
        conn.execute("""
            INSERT INTO transactions
            (customer_id, transaction_type, amount, description, created_at)
            VALUES (?, 'Withdrawal', ?, ?, ?)
        """, (customer["id"], amount, "Cash withdrawal", now()))
        conn.commit()
        conn.close()
        st.success(f"Withdrawal successful: {money(amount)}")
        st.rerun()


# ----------------------------- Transfer -----------------------------
def transfer_section(customer):
    st.title("🔄 Transfer")
    st.info(f"Available balance: {money(customer['balance'])}")

    with st.form("transfer_form"):
        receiver_account = st.text_input("Receiver account number")
        amount = st.number_input("Transfer amount", min_value=1.0, step=100.0, format="%.2f")
        submit = st.form_submit_button("Transfer Money", use_container_width=True)

    if submit:
        receiver_account = receiver_account.strip()
        conn = get_conn()
        conn.execute("BEGIN IMMEDIATE")

        sender = conn.execute("SELECT * FROM customers WHERE id=?", (customer["id"],)).fetchone()
        receiver = conn.execute("""
            SELECT * FROM customers WHERE account_number=? AND status='Approved'
        """, (receiver_account,)).fetchone()

        if receiver is None:
            conn.rollback()
            conn.close()
            st.error("Receiver account was not found or is not approved.")
            return

        if receiver["id"] == sender["id"]:
            conn.rollback()
            conn.close()
            st.error("You cannot transfer money to your own account.")
            return

        if amount > sender["balance"]:
            conn.rollback()
            conn.close()
            st.error("Insufficient available balance.")
            return

        timestamp = now()
        conn.execute("UPDATE customers SET balance=balance-?, updated_at=? WHERE id=?",
                     (amount, timestamp, sender["id"]))
        conn.execute("UPDATE customers SET balance=balance+?, updated_at=? WHERE id=?",
                     (amount, timestamp, receiver["id"]))

        conn.execute("""
            INSERT INTO transactions
            (customer_id, transaction_type, amount, description, created_at)
            VALUES (?, 'Transfer', ?, ?, ?)
        """, (sender["id"], amount, f"Transfer to {receiver['account_number']}", timestamp))

        conn.execute("""
            INSERT INTO transactions
            (customer_id, transaction_type, amount, description, created_at)
            VALUES (?, 'Transfer', ?, ?, ?)
        """, (receiver["id"], amount, f"Transfer received from {sender['account_number']}", timestamp))

        conn.commit()
        conn.close()
        st.success(f"Transfer successful: {money(amount)} to {receiver['account_number']}")
        st.rerun()


# ----------------------------- Transaction History -----------------------------
def transaction_history(customer):
    st.title("📜 Transaction History")
    conn = get_conn()
    rows = conn.execute("""
        SELECT transaction_type, amount, description, created_at
        FROM transactions
        WHERE customer_id=?
        ORDER BY id DESC
    """, (customer["id"],)).fetchall()
    conn.close()

    if not rows:
        st.info("No transactions yet.")
        return

    for row in rows:
        st.markdown(f"""
        <div class="card" style="margin-bottom:10px;min-height:auto;">
            <b>{row['transaction_type']}</b> — {money(row['amount'])}<br>
            <span class="small">{row['description'] or ''} · {row['created_at']}</span>
        </div>
        """, unsafe_allow_html=True)


# ----------------------------- Admin Login -----------------------------
def admin_login():
    st.subheader("🛡️ Admin Login")

    with st.form("admin_login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login", use_container_width=True)

    if submit:
        if secrets.compare_digest(username, ADMIN_USERNAME) and secrets.compare_digest(password, ADMIN_PASSWORD):
            st.session_state.admin_logged_in = True
            st.session_state.admin_section = "📊 Dashboard"
            st.rerun()
        else:
            st.error("Invalid admin credentials.")


# ----------------------------- Admin Portal -----------------------------
def admin_portal():
    st.sidebar.markdown("## 🛡️ Admin Portal")
    section = st.sidebar.radio(
        "Admin Menu",
        ["📊 Dashboard", "🛡️ Approval Requests", "💰 Deposit Requests",
         "❌ Rejected Requests", "👥 Customer Accounts"],
        key="admin_section"
    )
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        reset_admin_session()
        st.rerun()

    if section == "📊 Dashboard":
        admin_dashboard()
    elif section == "🛡️ Approval Requests":
        admin_approval_requests()
    elif section == "💰 Deposit Requests":
        admin_deposit_requests()
    elif section == "❌ Rejected Requests":
        admin_rejected_requests()
    elif section == "👥 Customer Accounts":
        admin_customer_accounts()


def admin_dashboard():
    st.title("📊 Dashboard")
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) c FROM customers").fetchone()["c"]
    approved = conn.execute("SELECT COUNT(*) c FROM customers WHERE status='Approved'").fetchone()["c"]
    pending_accounts = conn.execute("SELECT COUNT(*) c FROM customers WHERE status='Pending'").fetchone()["c"]
    pending_deposits = conn.execute("SELECT COUNT(*) c FROM deposits WHERE status='Pending'").fetchone()["c"]
    total_balance = conn.execute("SELECT COALESCE(SUM(balance),0) b FROM customers WHERE status='Approved'").fetchone()["b"]
    conn.close()

    a,b,c,d = st.columns(4)
    with a: st.metric("Total Customers", total)
    with b: st.metric("Approved Customers", approved)
    with c: st.metric("Pending Accounts", pending_accounts)
    with d: st.metric("Pending Deposit Requests", pending_deposits)

    st.markdown("### Overall System Summary")
    st.markdown(f"""
    <div class="card">
        <b>Total customers:</b> {total}<br>
        <b>Approved customers:</b> {approved}<br>
        <b>Pending account applications:</b> {pending_accounts}<br>
        <b>Pending deposit requests:</b> {pending_deposits}<br>
        <b>Total approved-account balance:</b> {money(total_balance)}
    </div>
    """, unsafe_allow_html=True)


def admin_approval_requests():
    st.title("🛡️ Approval Requests")
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM customers WHERE status='Pending' ORDER BY id DESC
    """).fetchall()
    conn.close()

    if not rows:
        st.info("No pending customer applications.")
        return

    for row in rows:
        with st.container(border=True):
            st.markdown(f"### 👤 {row['full_name']}")
            st.write(f"**Phone:** {row['phone']}")
            st.write(f"**Account Number:** {row['account_number']}")
            st.write(f"**Application ID:** {row['application_id']}")
            st.write(f"**Date:** {row['created_at']}")

            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Approve", key=f"approve_acc_{row['id']}", use_container_width=True):
                    conn = get_conn()
                    conn.execute("""
                        UPDATE customers
                        SET status='Approved', rejection_reason=NULL, updated_at=?
                        WHERE id=? AND status='Pending'
                    """, (now(), row["id"]))
                    conn.commit()
                    conn.close()
                    st.success("Customer account approved.")
                    st.rerun()

            with c2:
                with st.form(f"reject_acc_form_{row['id']}"):
                    reason = st.text_input("Rejection reason", key=f"acc_reason_{row['id']}")
                    reject = st.form_submit_button("❌ Reject", use_container_width=True)
                    if reject:
                        if not reason.strip():
                            st.error("Enter a rejection reason.")
                        else:
                            conn = get_conn()
                            conn.execute("""
                                INSERT INTO account_rejection_history
                                (customer_id, full_name, phone, reason, rejected_at)
                                VALUES (?, ?, ?, ?, ?)
                            """, (row["id"], row["full_name"], row["phone"], reason.strip(), now()))
                            conn.execute("""
                                UPDATE customers
                                SET status='Rejected', rejection_reason=?, updated_at=?
                                WHERE id=? AND status='Pending'
                            """, (reason.strip(), now(), row["id"]))
                            conn.commit()
                            conn.close()
                            st.success("Application rejected.")
                            st.rerun()


def admin_deposit_requests():
    st.title("💰 Deposit Requests")
    conn = get_conn()
    rows = conn.execute("""
        SELECT d.*, c.full_name, c.account_number
        FROM deposits d
        JOIN customers c ON c.id=d.customer_id
        WHERE d.status='Pending'
        ORDER BY d.id DESC
    """).fetchall()
    conn.close()

    if not rows:
        st.info("No pending deposit requests.")
        return

    for row in rows:
        with st.container(border=True):
            st.markdown(f"### 👤 {row['full_name']}")
            st.write(f"**Account Number:** {row['account_number']}")
            st.write(f"**Deposit Amount:** {money(row['amount'])}")
            st.write(f"**Request Date:** {row['requested_at']}")
            st.warning("⏳ Pending")

            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Approve", key=f"approve_dep_{row['id']}", use_container_width=True):
                    conn = get_conn()
                    conn.execute("BEGIN IMMEDIATE")
                    deposit = conn.execute("SELECT * FROM deposits WHERE id=?", (row["id"],)).fetchone()
                    if deposit and deposit["status"] == "Pending":
                        timestamp = now()
                        conn.execute("""
                            UPDATE deposits SET status='Approved', decided_at=?, rejection_reason=NULL
                            WHERE id=? AND status='Pending'
                        """, (timestamp, row["id"]))
                        conn.execute("""
                            UPDATE customers SET balance=balance+?, updated_at=?
                            WHERE id=?
                        """, (deposit["amount"], timestamp, deposit["customer_id"]))
                        conn.execute("""
                            INSERT INTO transactions
                            (customer_id, transaction_type, amount, description, created_at)
                            VALUES (?, 'Deposit', ?, ?, ?)
                        """, (deposit["customer_id"], deposit["amount"], "Admin-approved deposit", timestamp))
                        conn.commit()
                        conn.close()
                        st.success("Deposit approved and balance updated.")
                        st.rerun()
                    else:
                        conn.rollback()
                        conn.close()
                        st.error("This deposit is no longer pending.")

            with c2:
                with st.form(f"reject_dep_form_{row['id']}"):
                    reason = st.text_input("Rejection reason", key=f"dep_reason_{row['id']}")
                    reject = st.form_submit_button("❌ Reject", use_container_width=True)
                    if reject:
                        if not reason.strip():
                            st.error("Enter a rejection reason.")
                        else:
                            conn = get_conn()
                            conn.execute("BEGIN IMMEDIATE")
                            deposit = conn.execute("SELECT * FROM deposits WHERE id=?", (row["id"],)).fetchone()
                            if deposit and deposit["status"] == "Pending":
                                timestamp = now()
                                conn.execute("""
                                    INSERT INTO deposit_rejection_history
                                    (deposit_id, customer_id, amount, reason, rejected_at)
                                    VALUES (?, ?, ?, ?, ?)
                                """, (deposit["id"], deposit["customer_id"], deposit["amount"], reason.strip(), timestamp))
                                conn.execute("""
                                    UPDATE deposits SET status='Rejected', rejection_reason=?, decided_at=?
                                    WHERE id=? AND status='Pending'
                                """, (reason.strip(), timestamp, row["id"]))
                                conn.commit()
                                conn.close()
                                st.success("Deposit rejected.")
                                st.rerun()
                            else:
                                conn.rollback()
                                conn.close()
                                st.error("This deposit is no longer pending.")


def admin_rejected_requests():
    st.title("❌ Rejected Requests")

    st.markdown("### Rejected Account Requests")
    conn = get_conn()
    accounts = conn.execute("""
        SELECT h.*, c.account_number
        FROM account_rejection_history h
        JOIN customers c ON c.id=h.customer_id
        ORDER BY h.id DESC
    """).fetchall()
    conn.close()

    if not accounts:
        st.info("No rejected account requests.")
    else:
        for row in accounts:
            st.markdown(f"""
            <div class="danger-box" style="margin-bottom:10px;">
                <b>Customer:</b> {row['full_name']}<br>
                <b>Account Number:</b> {row['account_number']}<br>
                <b>Phone:</b> {row['phone']}<br>
                <b>Rejection reason:</b> {row['reason']}<br>
                <b>Date:</b> {row['rejected_at']}
            </div>
            """, unsafe_allow_html=True)

    st.markdown("### Rejected Deposit Requests")
    conn = get_conn()
    deposits = conn.execute("""
        SELECT h.*, c.full_name, c.account_number
        FROM deposit_rejection_history h
        JOIN customers c ON c.id=h.customer_id
        ORDER BY h.id DESC
    """).fetchall()
    conn.close()

    if not deposits:
        st.info("No rejected deposit requests.")
    else:
        for row in deposits:
            st.markdown(f"""
            <div class="danger-box" style="margin-bottom:10px;">
                <b>Customer:</b> {row['full_name']}<br>
                <b>Account Number:</b> {row['account_number']}<br>
                <b>Amount:</b> {money(row['amount'])}<br>
                <b>Rejection reason:</b> {row['reason']}<br>
                <b>Date:</b> {row['rejected_at']}
            </div>
            """, unsafe_allow_html=True)


def admin_customer_accounts():
    st.title("👥 Customer Accounts")
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM customers ORDER BY id DESC
    """).fetchall()
    conn.close()

    if not rows:
        st.info("No customers yet.")
        return

    for row in rows:
        with st.expander(f"{row['full_name']} — {row['account_number']} — {row['status']}"):
            st.write(f"**Name:** {row['full_name']}")
            st.write(f"**Account Number:** {row['account_number']}")
            st.write(f"**Phone:** {row['phone']}")
            st.write(f"**Balance:** {money(row['balance'])}")
            st.write(f"**Status:** {row['status']}")
            st.write(f"**Created:** {row['created_at']}")

            if st.button("📜 View Transactions", key=f"view_tx_{row['id']}", use_container_width=True):
                st.session_state[f"show_tx_{row['id']}"] = not st.session_state.get(f"show_tx_{row['id']}", False)

            if st.session_state.get(f"show_tx_{row['id']}", False):
                conn = get_conn()
                txs = conn.execute("""
                    SELECT transaction_type, amount, description, created_at
                    FROM transactions
                    WHERE customer_id=?
                    ORDER BY id DESC
                """, (row["id"],)).fetchall()
                conn.close()

                if not txs:
                    st.info("No transactions for this customer.")
                else:
                    for tx in txs:
                        st.write(
                            f"**{tx['transaction_type']}** — {money(tx['amount'])} — "
                            f"{tx['description'] or ''} — {tx['created_at']}"
                        )


# ----------------------------- Main Navigation -----------------------------
def main():
    if st.session_state.get("customer_logged_in"):
        customer = get_customer(st.session_state["customer_id"])
        if customer:
            customer_dashboard(customer)
            return
        reset_customer_session()

    if st.session_state.get("admin_logged_in"):
        admin_portal()
        return

    header()

    tab = st.radio(
        "",
        ["📝 Create Account", "👤 Customer Login", "🔎 Application Status", "🛡️ Admin"],
        horizontal=True
    )

    if tab == "📝 Create Account":
        create_account()
    elif tab == "👤 Customer Login":
        customer_login()
    elif tab == "🔎 Application Status":
        application_status()
    elif tab == "🛡️ Admin":
        admin_login()

    st.markdown('<div class="footer">Demo project for educational/college use. Do not enter real financial information.</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
