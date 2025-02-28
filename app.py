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
EMAIL = "asalam.filex@gmail.com"
PASSWORD = "urfz fxzi pljl iqxa"
IMAP_SERVER = "imap.gmail.com"
def get_imap_connection():
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL, PASSWORD)
        print("✅ اتصال IMAP ناجح.")
        return mail
    except Exception as e:
        print(f"❌ فشل الاتصال: {e}")
        raise

@retry_on_error
def fetch_email_with_link(account, subject_keywords, button_text):
    try:
        mail = get_imap_connection()  # إنشاء اتصال جديد
        mail.select("inbox")
        search_criteria = f'(OR {" ".join([f"SUBJECT \"{keyword}\"" for keyword in subject_keywords])})'
        _, data = mail.search(None, search_criteria)
        mail_ids = data[0].split()[-10:]

        for mail_id in reversed(mail_ids):
            _, msg_data = mail.fetch(mail_id, "(RFC822)")
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            subject, encoding = decode_header(msg["Subject"])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding or "utf-8", errors="ignore")

            if any(keyword in subject for keyword in subject_keywords):
                for part in msg.walk():
                    if part.get_content_type() == "text/html":
                        payload = part.get_payload(decode=True)
                        if payload:
                            html_content = payload.decode('utf-8', errors='ignore')
                            if account in html_content:
                                soup = BeautifulSoup(html_content, 'html.parser')
                                for a in soup.find_all('a', href=True):
                                    if button_text in clean_text(a.get_text()):
                                        mail.logout()  # إغلاق الجلسة بعد الاستخدام
                                        return a['href']

        mail.logout()  # إغلاق الجلسة إذا لم يتم العثور على النتيجة
        return "طلبك غير موجود."
    except Exception as e:
        return f"Error fetching emails: {str(e).encode('utf-8', errors='ignore').decode('utf-8')}"

@retry_on_error
def fetch_email_with_code(account, subject_keywords):
    try:
        mail = get_imap_connection()  # إنشاء اتصال جديد
        mail.select("inbox")
        search_criteria = f'(OR {" ".join([f"SUBJECT \"{keyword}\"" for keyword in subject_keywords])})'
        _, data = mail.search(None, search_criteria)
        mail_ids = data[0].split()[-10:]

        for mail_id in reversed(mail_ids):
            _, msg_data = mail.fetch(mail_id, "(RFC822)")
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            subject, encoding = decode_header(msg["Subject"])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding or "utf-8", errors="ignore")

            if any(keyword in subject for keyword in subject_keywords):
                for part in msg.walk():
                    if part.get_content_type() == "text/html":
                        payload = part.get_payload(decode=True)
                        if payload:
                            html_content = payload.decode('utf-8', errors='ignore')
                            if account in html_content:
                                code_match = re.search(r'\b\d{4}\b', html_content)
                                if code_match:
                                    mail.logout()  # إغلاق الجلسة بعد الاستخدام
                                    return code_match.group(0)

        mail.logout()  # إغلاق الجلسة إذا لم يتم العثور على النتيجة
        return "طلبك غير موجود."
    except Exception as e:
        return f"Error fetching emails: {str(e).encode('utf-8', errors='ignore').decode('utf-8')}"

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
