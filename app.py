
import os
from datetime import datetime, timedelta
import time
import re
import imaplib
import email
from email.header import decode_header
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify, url_for, render_template, redirect, session
from flask_cors import CORS
import jwt
from functools import wraps

# ----------------------------------
# Configuration
# ----------------------------------
app = Flask(__name__)
CORS(app)
# استخدم متغير بيئة للسرية أو افتراضي
app.secret_key = "aslam2001aslaam23456"

# بيانات الدخول الإدارية
ADMIN_EMAIL = 'aslam.fix'
ADMIN_PASSWORD = '@'

# إعدادات JWT
JWT_SECRET = os.getenv('JWT_SECRET', 'your-jwt-secret')
JWT_ALGORITHM = 'HS256'

# إعدادات البريد الإلكتروني
EMAIL = 'aslam.filex@gmail.com'
PASSWORD =  'urfz fxzi pljl iqxa'
IMAP_SERVER ='imap.gmail.com'

# ----------------------------------
# وظائف مساعدة للبريد
# ----------------------------------
def clean_text(text):
    return text.strip()

def retry_imap_connection():
    global mail
    for _ in range(3):
        try:
            mail = imaplib.IMAP4_SSL(IMAP_SERVER)
            mail.login(EMAIL, PASSWORD)
            mail.select('inbox')  # اختيار صندوق الوارد مباشرة بعد تسجيل الدخول
            return
        except Exception:
            if mail:
                try:
                    mail.logout()
                except:
                    pass
            time.sleep(2)
    raise ConnectionError("Failed to connect to IMAP server")


def retry_on_error(func):
    def wrapper(*args, **kwargs):
        for _ in range(3):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if 'EOF occurred' in str(e) or 'socket' in str(e):
                    time.sleep(2)
                else:
                    raise
        raise RuntimeError('Failed after retries')
    return wrapper

@retry_on_error
def fetch_email_with_link(account, subject_keywords, button_text=None):
    retry_imap_connection()
    mail.select('inbox')
    _, data = mail.search(None, 'ALL')
    for mid in reversed(data[0].split()[-20:]):
        _, msg_data = mail.fetch(mid, '(RFC822)')
        msg = email.message_from_bytes(msg_data[0][1])
        subj, enc = decode_header(msg['Subject'])[0]
        if isinstance(subj, bytes): subj = subj.decode(enc or 'utf-8')
        if not any(k in subj for k in subject_keywords):
            continue
        to_hdr = msg.get('To', '')
        if isinstance(to_hdr, bytes): to_hdr = to_hdr.decode(enc or 'utf-8', errors='ignore')
        if account.lower() not in to_hdr.lower():
            continue
        for part in msg.walk():
            if part.get_content_type() == 'text/html':
                html = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                soup = BeautifulSoup(html, 'html.parser')
                if button_text:
                    for a in soup.find_all('a', href=True):
                        if button_text in clean_text(a.get_text()):
                            return a['href']
                a = soup.find('a', href=True)
                if a:
                    return a['href']
    return None

@retry_on_error
def fetch_email_with_code(account, subject_keywords):
    retry_imap_connection()
    mail.select('inbox')
    _, data = mail.search(None, 'ALL')
    for mid in reversed(data[0].split()[-20:]):
        _, msg_data = mail.fetch(mid, '(RFC822)')
        msg = email.message_from_bytes(msg_data[0][1])
        subj, enc = decode_header(msg['Subject'])[0]
        if isinstance(subj, bytes): subj = subj.decode(enc or 'utf-8')
        if not any(k in subj for k in subject_keywords):
            continue
        to_hdr = msg.get('To', '')
        if isinstance(to_hdr, bytes): to_hdr = to_hdr.decode(enc or 'utf-8', errors='ignore')
        if account.lower() not in to_hdr.lower():
            continue
        for part in msg.walk():
            if part.get_content_type() == 'text/html':
                html = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                text = BeautifulSoup(html, 'html.parser').get_text()
                match = re.search(r'\b\d{4}\b', text)
                if match:
                    return match.group(0)
    return None

# ----------------------------------
# مصادقة المدير
# ----------------------------------
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# ----------------------------------
# المسارات (Routes)
# ----------------------------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email_in = request.form.get('email')
        password_in = request.form.get('password')
        print(f'Login attempt - Email: {email_in}, Password: {password_in}')
        print(f'Expected - Email: {ADMIN_EMAIL}, Password: {ADMIN_PASSWORD}')
        if email_in == ADMIN_EMAIL and password_in == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        return render_template('admin_login.html', error='بيانات الدخول غير صحيحة')
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))

@app.route('/api/generate-subscription-link', methods=['POST'])
@admin_required
def generate_subscription_link():
    data = request.get_json()
    user_id = data.get('user_id')
    role = data.get('role')
    if not user_id or role not in ['normal1', 'normal2']:
        return jsonify(error='Invalid user_id or role'), 400
    expiration = datetime.utcnow() + timedelta(days=30)
    payload = {'user_id': user_id, 'role': role, 'exp': expiration}
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    link = f"{request.host_url}user/{token}"
    return jsonify(link=link), 200

@app.route('/user/<token>')
def user_page(token):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get('user_id')
        role = payload.get('role')
        if datetime.utcnow() > datetime.fromtimestamp(payload['exp']):
            return render_template('expired.html')
        return render_template('user.html', user_id=user_id, role=role)
    except jwt.ExpiredSignatureError:
        return render_template('expired.html')
    except jwt.InvalidTokenError:
        return render_template('invalid.html')

# Email-fetch APIs
@app.route('/api/fetch-residence-update-link', methods=['POST'])
def fetch_residence_update_link():
    account = request.json.get('account')
    if not account: return jsonify(error='Account is required'), 400
    link = fetch_email_with_link(account, ['تحديث السكن'], 'نعم، أنا قدمت الطلب')
    return jsonify(link=link), 200

@app.route('/api/fetch-residence-code', methods=['POST'])
def fetch_residence_code():
    account = request.json.get('account')
    if not account: return jsonify(error='Account is required'), 400
    code = fetch_email_with_code(account, ['رمز الوصول المؤقت'])
    return jsonify(code=code), 200

@app.route('/api/fetch-password-reset-link', methods=['POST'])
def fetch_password_reset_link():
    account = request.json.get('account')
    if not account: return jsonify(error='Account is required'), 400
    link = fetch_email_with_link(account, ['إعادة تعيين كلمة المرور'], 'إعادة تعيين كلمة المرور')
    return jsonify(link=link), 200

@app.route('/api/fetch-login-code', methods=['POST'])
def fetch_login_code():
    account = request.json.get('account')
    if not account: return jsonify(error='Account is required'), 400
    code = fetch_email_with_code(account, ['رمز تسجيل الدخول'])
    return jsonify(code=code), 200

@app.route('/api/fetch-suspended-account-link', methods=['POST'])
def fetch_suspended_account_link():
    account = request.json.get('account')
    if not account: return jsonify(error='Account is required'), 400
    link = fetch_email_with_link(account, ['عضويتك في Netflix معلّقة'], 'إضافة معلومات الدفع')
    return jsonify(link=link), 200

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
