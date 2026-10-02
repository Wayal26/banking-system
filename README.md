
# Banking System – Streamlit Mini Project

## Features

### Customer
1. Create Account
   - Full Name
   - 10-digit phone number
   - 4-digit PIN
   - Generates Application ID + Account Number
   - Starts as Pending

2. Customer Login
   - Account Number + 4-digit PIN
   - Only Approved accounts can login

3. Application Status
   - Search by Account Number or Application ID
   - Pending / Approved / Rejected
   - Rejected applications show admin reason
   - Rejected applications can be edited and resubmitted
   - Previous rejection is preserved in history

4. Customer Dashboard
   - Balance
   - Transaction count
   - Pending deposits
   - Deposit / Withdraw / Transfer
   - Transaction history
   - Account information
   - Logout

### Admin
The admin sidebar contains exactly:
1. Dashboard
2. Approval Requests
3. Deposit Requests
4. Rejected Requests
5. Customer Accounts

Admin can:
- Approve/reject customer applications
- Approve/reject deposits
- Enter rejection reasons
- View rejected account/deposit history
- View customers
- Open a customer's transactions from Customer Accounts

### Deposit rule
A deposit does NOT increase the customer's balance when submitted.
The balance is increased only after an admin approves the pending deposit.
A rejected deposit can be resubmitted as a new pending request.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

The SQLite database file `banking_system.db` is created automatically.

## Admin credentials

The application reads:
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`

Environment variables are supported. If they are not supplied, the demo defaults configured in `app.py` are used.

For a hosted deployment, set the credentials as Streamlit secrets or environment variables rather than displaying them in the UI.

## Streamlit Cloud

Upload `app.py` and `requirements.txt` to GitHub and deploy the repository as a Streamlit app.

For Streamlit secrets, use:

```toml
ADMIN_USERNAME = "your-admin-username"
ADMIN_PASSWORD = "your-admin-password"
```

Then update the credential lookup in `app.py` to read from `st.secrets` if you want secrets-only deployment.

## Important
This is an educational/college project, not production banking software. Do not use real money, real customer information, or real banking credentials.
