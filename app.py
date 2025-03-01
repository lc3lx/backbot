from flask import Flask, request, jsonify
import imaplib
import email
from email.header import decode_header
from bs4 import BeautifulSoup
import re
import time



# Flask setup
app = Flask(__name__)


# Email handling
EMAIL = "aslam.filex@gmail.com"
PASSWORD = "urfz fxzi pljl iqxa"
IMAP_SERVER = "imap.gmail.com"
def retry_imap_connection():
    global mail
    for attempt in range(3):
        try:
            mail = imaplib.IMAP4_SSL(IMAP_SERVER)
            mail.login(EMAIL, PASSWORD)
            print("✅ اتصال IMAP ناجح.")
            return
        except Exception as e:
            print(f"❌ فشل الاتصال (المحاولة {attempt + 1}): {e}")
            time.sleep(2)
    print("❌ فشل إعادة الاتصال بعد عدة محاولات.")

def retry_on_error(func):
    """ديكورتر لإعادة المحاولة عند حدوث خطأ في جلب الرسائل."""
    def wrapper(*args, **kwargs):
        retries = 3
        for attempt in range(retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if "EOF occurred" in str(e) or "socket" in str(e):
                    time.sleep(2)
                    print(f"Retrying... Attempt {attempt + 1}/{retries}")
                else:
                    return f"Error fetching emails: {e}"
        return "Error: Failed after multiple retries."
    return wrapper

@retry_on_error
def fetch_email_with_link(account, subject_keywords, button_text):
    retry_imap_connection()
    try:
        mail.select("inbox")
        _, data = mail.search(None, 'ALL')
        mail_ids = data[0].split()[-17:]

        for mail_id in reversed(mail_ids):
            _, msg_data = mail.fetch(mail_id, "(RFC822)")
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            subject, encoding = decode_header(msg["Subject"])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding or "utf-8")

            # التحقق مما إذا كانت الكلمات المفتاحية موجودة في الموضوع
            if any(keyword in subject for keyword in subject_keywords):
                for part in msg.walk():
                    if part.get_content_type() == "text/html":
                        payload = part.get_payload(decode=True)
                        if payload:
                            html_content = payload.decode('utf-8', errors='ignore')

                            # التحقق من وجود الحساب بدقة باستخدام regex
                            if re.search(rf'\b{re.escape(account)}\b', html_content, re.IGNORECASE):
                                soup = BeautifulSoup(html_content, 'html.parser')
                                for a in soup.find_all('a', href=True):
                                    if button_text in clean_text(a.get_text()):
                                        return a['href']

        return "طلبك غير موجود."
    except Exception as e:
        return f"Error fetching emails: {e}"

@retry_on_error
def fetch_email_with_code(account, subject_keywords):
    retry_imap_connection()
    try:
        mail.select("inbox")
        _, data = mail.search(None, 'ALL')
        mail_ids = data[0].split()[-17:]

        for mail_id in reversed(mail_ids):
            _, msg_data = mail.fetch(mail_id, "(RFC822)")
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            subject, encoding = decode_header(msg["Subject"])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding or "utf-8")

            # التحقق مما إذا كانت الكلمات المفتاحية موجودة في الموضوع
            if any(keyword in subject for keyword in subject_keywords):
                for part in msg.walk():
                    if part.get_content_type() == "text/html":
                        payload = part.get_payload(decode=True)
                        if payload:
                            html_content = payload.decode('utf-8', errors='ignore')

                            # التحقق من وجود الحساب بدقة باستخدام regex
                            if re.search(rf'\b{re.escape(account)}\b', html_content, re.IGNORECASE):
                                code_match = re.search(r'\b\d{4}\b', BeautifulSoup(html_content, 'html.parser').get_text())
                                if code_match:
                                    return code_match.group(0)

        return "طلبك غير موجود."
    except Exception as e:
        return f"Error fetching emails: {e}"

@retry_on_error
def fetch_email_with_code(account, subject_keywords):
    retry_imap_connection()
    try:
        mail.select("inbox")
        _, data = mail.search(None, 'ALL')
        mail_ids = data[0].split()[-17:]

        for mail_id in reversed(mail_ids):
            _, msg_data = mail.fetch(mail_id, "(RFC822)")
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            subject, encoding = decode_header(msg["Subject"])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding or "utf-8")

            # التحقق مما إذا كانت الكلمات المفتاحية موجودة في الموضوع
            if any(keyword in subject for keyword in subject_keywords):
                for part in msg.walk():
                    if part.get_content_type() == "text/html":
                        payload = part.get_payload(decode=True)
                        if payload:
                            html_content = payload.decode('utf-8', errors='ignore')

                            # التحقق من وجود الحساب بدقة باستخدام regex
                            if re.search(rf'\b{re.escape(account)}\b', html_content, re.IGNORECASE):
                                code_match = re.search(r'\b\d{4}\b', BeautifulSoup(html_content, 'html.parser').get_text())
                                if code_match:
                                    return code_match.group(0)

        return "طلبك غير موجود."
    except Exception as e:
        return f"Error fetching emails: {e}"

# ----------------------------------
# User APIs
# ----------------------------------

# /api/fetch-residence-update-link
@app.route('/api/fetch-residence-update-link', methods=['POST'])
def fetch_residence_update_link():
    data = request.get_json()
    account = data.get('account')

    if not account:
        return jsonify(error="Account is required"), 400

    link = fetch_email_with_link(account, ["تحديث السكن"], "نعم، أنا قدمت الطلب")
    return jsonify(link=link), 200

# /api/fetch-residence-code
@app.route('/api/fetch-residence-code', methods=['POST'])
def fetch_residence_code():
    data = request.get_json()
    account = data.get('account')

    if not account:
        return jsonify(error="Account is required"), 400

    code = fetch_email_with_code(account, ["رمز الوصول المؤقت"])
    return jsonify(code=code), 200

# /api/fetch-password-reset-link
@app.route('/api/fetch-password-reset-link', methods=['POST'])
def fetch_password_reset_link():
    data = request.get_json()
    account = data.get('account')

    if not account:
        return jsonify(error="Account is required"), 400

    link = fetch_email_with_link(account, ["إعادة تعيين كلمة المرور"], "إعادة تعيين كلمة المرور")
    return jsonify(link=link), 200

# ----------------------------------
# Admin APIs
# ----------------------------------

# /api/fetch-login-code
@app.route('/api/fetch-login-code', methods=['POST'])
def fetch_login_code():
    data = request.get_json()
    account = data.get('account')

    if not account:
        return jsonify(error="Account is required"), 400

    code = fetch_email_with_code(account, ["رمز تسجيل الدخول"])
    return jsonify(code=code), 200

# /api/fetch-suspended-account-link
@app.route('/api/fetch-suspended-account-link', methods=['POST'])
def fetch_suspended_account_link():
    data = request.get_json()
    account = data.get('account')

    if not account:
        return jsonify(error="Account is required"), 400

    link = fetch_email_with_link(account, ["عضويتك في Netflix معلّقة"], "إضافة معلومات الدفع")
    return jsonify(link=link), 200



# Run the server
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
