import os
from datetime import datetime
from flask import Flask, jsonify, render_template_string, request
import google.generativeai as genai
import psycopg2  # المكتبة المسؤولة عن الاتصال بـ PostgreSQL

app = Flask(__name__)

# 1. إعداد مفتاح جيمني من البيئة
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# 2. الحصول على رابط قاعدة بيانات Supabase من البيئة
DATABASE_URL = os.environ.get("DATABASE_URL")


# دالة الاتصال الآمن بـ Supabase
def get_db_connection():
    # يتصل بالسيرفر السحابي مباشرة باستخدام الـ URI
    return psycopg2.connect(DATABASE_URL)


# 3. دالة حفظ البيانات في Supabase
def save_interaction(question, response):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # هنا الـ SQL مخصص لـ PostgreSQL
        cursor.execute(
            "INSERT INTO conversations (user_question, ai_response) VALUES (%s, %s)",
            (question, response),
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Database Error: {e}")


# 4. واجهات العرض (نفس ثيم Synapse الاحترافي الغامق)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Synapse AI - التفكير العصبي الرقمي</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        :root { --bg-dark: #0d1117; --card-dark: #161b22; --neon-blue: #00d2ff; --neon-purple: #a855f7; --text-light: #c9d1d9; --text-bright: #ffffff; --border-color: #30363d; }
        body { font-family: 'Cairo', sans-serif; background-color: var(--bg-dark); background-image: radial-gradient(circle at 50% 50%, #161b33 0%, #0d1117 100%); margin: 0; padding: 0; display: flex; justify-content: center; align-items: center; min-height: 100vh; color: var(--text-light); }
        .container { width: 90%; max-width: 700px; background: var(--card-dark); padding: 40px; border-radius: 24px; box-shadow: 0 20px 50px rgba(0, 210, 255, 0.05), 0 0 0 1px var(--border-color); position: relative; overflow: hidden; }
        .container::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 4px; background: linear-gradient(90deg, var(--neon-blue), var(--neon-purple)); }
        .header { text-align: center; margin-bottom: 35px; }
        .header .logo-icon { font-size: 55px; background: linear-gradient(45deg, var(--neon-blue), var(--neon-purple)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 15px; filter: drop-shadow(0 0 10px rgba(0, 210, 255, 0.3)); }
        .header h1 { color: var(--text-bright); margin: 0; font-size: 32px; font-weight: 800; }
        .header p { color: #8b949e; font-size: 15px; margin-top: 8px; }
        textarea { width: 100%; height: 130px; padding: 20px; border-radius: 16px; border: 2px solid var(--border-color); font-family: 'Cairo', sans-serif; font-size: 16px; resize: none; outline: none; box-sizing: border-box; background: #090d13; color: var(--text-bright); }
        textarea:focus { border-color: var(--neon-blue); box-shadow: 0 0 15px rgba(0, 210, 255, 0.2); }
        button { width: 100%; background: linear-gradient(90deg, var(--neon-blue), var(--neon-purple)); color: white; border: none; padding: 16px; border-radius: 16px; font-family: 'Cairo', sans-serif; font-size: 18px; font-weight: bold; cursor: pointer; display: flex; justify-content: center; align-items: center; gap: 12px; margin-top: 15px; }
        button:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(0, 210, 255, 0.4); }
        .loading { display: none; margin: 25px 0; color: var(--neon-blue); font-weight: 600; text-align: center; }
        .response-card { margin-top: 30px; padding: 25px; background: #1f242c; border-radius: 16px; color: #e6edf3; line-height: 1.8; display: none; border-left: 4px solid var(--neon-purple); border-right: 4px solid var(--neon-blue); white-space: pre-wrap; text-align: right; }
        .footer { margin-top: 35px; text-align: center; font-size: 13px; color: #58a6ff; }
        .footer a { color: var(--neon-blue); text-decoration: none; margin-right: 10px; font-weight: bold; }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <i class="fas fa-brain logo-icon"></i>
        <h1>SYNAPSE</h1>
        <p>بوابة التفكير العصبي الاصطناعي - متصل بـ Supabase Cloud</p>
    </div>
    <div class="input-group">
        <textarea id="questionInput" placeholder="أدخل استعلامك هنا المحفوظ سحابياً للأبد..."></textarea>
    </div>
    <button onclick="askQuestion()">
        <span>إرسال النبضة العصبية</span>
        <i class="fas fa-bolt"></i>
    </button>
    <div id="loadingArea" class="loading"><i class="fas fa-spinner fa-spin"></i> جاري معالجة البيانات وتخزين الاستعلام...</div>
    <div id="responseCard" class="response-card"></div>
    <div class="footer">
        <i class="fas fa-cloud"></i> متصل بقاعدة بيانات سحابية آمنة | <a href="/logs" target="_blank">عرض السجلات <i class="fas fa-external-link-alt"></i></a>
    </div>
</div>
<script>
async function askQuestion() {
    const input = document.getElementById('questionInput');
    const responseCard = document.getElementById('responseCard');
    const loadingArea = document.getElementById('loadingArea');
    if (!input.value.trim()) { alert('من فضلك أدخل استعلامك أولاً!'); return; }
    loadingArea.style.display = 'block'; responseCard.style.display = 'none';
    try {
        const res = await fetch('/ask', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: input.value }) });
        const data = await res.json();
        if (data.answer) { responseCard.innerText = data.answer; responseCard.style.display = 'block'; }
        else { responseCard.innerText = "خطأ: " + data.error; responseCard.style.display = 'block'; }
    } catch (e) { responseCard.innerText = "فشل في الاتصال بالخادم."; responseCard.style.display = 'block'; }
    finally { loadingArea.style.display = 'none'; }
}
</script>
</body>
</html>
"""

LOGS_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>سجل Supabase - Synapse</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        body { font-family: 'Cairo', sans-serif; background-color: #0d1117; color: #c9d1d9; padding: 30px; }
        .table-container { max-width: 1000px; margin: 0 auto; background: #161b22; padding: 30px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); border: 1px solid #30363d; }
        h2 { color: #fff; border-bottom: 2px solid #30363d; padding-bottom: 15px; display: flex; justify-content: space-between; align-items: center; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 15px; text-align: right; border-bottom: 1px solid #30363d; }
        th { background-color: #21262d; color: #00d2ff; }
        tr:hover { background-color: #1f242c; }
        .btn-delete { background: #f85149; color: white; border: none; padding: 8px 15px; border-radius: 6px; cursor: pointer; font-family: 'Cairo'; }
        .empty { text-align: center; padding: 30px; color: #8b949e; }
    </style>
</head>
<body>
<div class="table-container">
    <h2>
        <span><i class="fas fa-cloud-upload-alt"></i> سجل السحابة الدائم (Supabase)</span>
        <form action="/clear-logs" method="POST" style="margin:0;" onsubmit="return confirm('هل أنت متأكد من مسح الجدول سحابياً؟');">
            <button type="submit" class="btn-delete"><i class="fas fa-trash"></i> تصفير الداتابيز</button>
        </form>
    </h2>
    <table>
        <thead>
            <tr>
                <th style="width: 5%;">ID</th>
                <th style="width: 35%;">السؤال</th>
                <th style="width: 45%;">إجابة الـ AI</th>
                <th style="width: 15%;">التاريخ والوقت</th>
            </tr>
        </thead>
        <tbody>
            {% for row in rows %}
            <tr>
                <td>{{ row[0] }}</td>
                <td style="white-space: pre-wrap;">{{ row[1] }}</td>
                <td style="white-space: pre-wrap;">{{ row[2] }}</td>
                <td>{{ row[3] }}</td>
            </tr>
            {% else %}
            <tr>
                <td colspan="4" class="empty">لا توجد سجلات مخزنة حتى الآن.</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
</body>
</html>
"""


@app.route("/")
def home():
    return render_template_string(HTML_TEMPLATE)


@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    user_question = data.get("question", "")
    if not user_question:
        return jsonify({"error": "الاستعلام فارغ"}), 400
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(user_question)
        ai_response = response.text

        # الحفظ السحابي
        save_interaction(user_question, ai_response)

        return jsonify({"answer": ai_response})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/logs")
def show_logs():
    rows = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, user_question, ai_response, created_at FROM conversations ORDER BY id DESC"
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        print(e)
    return render_template_string(LOGS_TEMPLATE, rows=rows)


@app.route("/clear-logs", methods=["POST"])
def clear_logs():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("TRUNCATE TABLE conversations RESTART IDENTITY;")
        conn.commit()
        cursor.close()
        conn.close()
    except:
        pass
    return "<script>alert('تم تصفير الداتابيز سحابياً بنجاح'); window.location.href='/logs';</script>"


if __name__ == "__main__":
    app.run(debug=True, port=5000)
