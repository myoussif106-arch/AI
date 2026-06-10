import os
from flask import Flask, jsonify, render_template_string, request, redirect, url_for
import google.generativeai as genai
import psycopg2

app = Flask(__name__)

# تجميع كل الاحتمالات لأسماء المفاتيح لتفادي الـ Limit
API_KEYS = [
    os.environ.get("GEMINI_KEY_1"),
    os.environ.get("GEMINI_KEY_2"),
    os.environ.get("GEMINI_KEY_3"),
    os.environ.get("GEMINI_API_KEY")
]
API_KEYS = [key for key in API_KEYS if key]

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True  # حفظ التعديلات فوراً سحابياً
    return conn

def save_interaction(question, response):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO conversations (user_question, ai_response) VALUES (%s, %s)",
            (question, response)
        )
        cursor.close()
        conn.close()
    except Exception as e:
        # خطأ الداتابيز صامت تماماً ولا يظهر للمستخدم
        print(f"Silent DB Error: {e}")

def get_feedback_counts():
    likes = 0
    dislikes = 0
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM site_feedback WHERE action_type = 'like'")
        likes = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM site_feedback WHERE action_type = 'dislike'")
        dislikes = cursor.fetchone()[0]
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Silent Feedback Fetch Error: {e}")
    return likes, dislikes

# واجهة المستخدم المحدثة بالعدادات الذكية والـ LocalStorage
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
        button.btn-main { width: 100%; background: linear-gradient(90deg, var(--neon-blue), var(--neon-purple)); color: white; border: none; padding: 16px; border-radius: 16px; font-family: 'Cairo', sans-serif; font-size: 18px; font-weight: bold; cursor: pointer; display: flex; justify-content: center; align-items: center; gap: 12px; margin-top: 15px; }
        button.btn-main:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(0, 210, 255, 0.4); }
        .loading { display: none; margin: 25px 0; color: var(--neon-blue); font-weight: 600; text-align: center; }
        .response-card { margin-top: 30px; padding: 25px; background: #1f242c; border-radius: 16px; color: #e6edf3; line-height: 1.8; display: none; border-left: 4px solid var(--neon-purple); border-right: 4px solid var(--neon-blue); white-space: pre-wrap; text-align: right; }
        
        /* استايل منطقة أزرار التقييم بالعدادات */
        .feedback-section { margin-top: 40px; display: flex; flex-direction: column; align-items: center; gap: 12px; padding-top: 25px; border-top: 1px solid var(--border-color); }
        .feedback-title { font-size: 14px; color: #8b949e; font-weight: 600; }
        .feedback-buttons { display: flex; gap: 20px; }
        .feedback-btn { background: #090d13; border: 1px solid var(--border-color); color: var(--text-light); padding: 10px 22px; border-radius: 12px; cursor: pointer; font-family: 'Cairo'; font-size: 14px; display: flex; align-items: center; gap: 8px; transition: all 0.3s ease; }
        .feedback-btn .count { font-weight: bold; background: #21262d; padding: 2px 8px; border-radius: 20px; font-size: 12px; }
        .feedback-btn.like:hover { border-color: #2ea043; color: #2ea043; box-shadow: 0 0 10px rgba(46, 160, 67, 0.2); }
        .feedback-btn.dislike:hover { border-color: #f85149; color: #f85149; box-shadow: 0 0 10px rgba(248, 81, 73, 0.2); }
        .feedback-btn:disabled { opacity: 0.6; cursor: not-allowed; pointer-events: none; }
        .feedback-btn.voted { border-color: #58a6ff !important; color: #58a6ff !important; }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <i class="fas fa-brain logo-icon"></i>
        <h1>SYNAPSE</h1>
        <p>بوابة التفكير العصبي الاصطناعي</p>
    </div>
    <div class="input-group">
        <textarea id="questionInput" placeholder="أدخل استعلامك هنا وسيقوم النظام بالمعالجة اللامتناهية..."></textarea>
    </div>
    <button class="btn-main" onclick="askQuestion()">
        <span>إرسال النبضة العصبية</span>
        <i class="fas fa-bolt"></i>
    </button>
    <div id="loadingArea" class="loading"><i class="fas fa-spinner fa-spin"></i> جاري معالجة البيانات وتوليد الاستجابة العصبية...</div>
    <div id="responseCard" class="response-card"></div>
    
    <div class="feedback-section">
        <div class="feedback-title" id="feedbackTitle">ما هو تقييمك للمنصة؟</div>
        <div class="feedback-buttons">
            <button class="feedback-btn like" id="likeBtn" onclick="sendFeedback('like')">
                <i class="far fa-thumbs-up"></i> أعجبني <span class="count" id="likeCount">{{ likes }}</span>
            </button>
            <button class="feedback-btn dislike" id="dislikeBtn" onclick="sendFeedback('dislike')">
                <i class="far fa-thumbs-down"></i> لم يعجبني <span class="count" id="dislikeCount">{{ dislikes }}</span>
            </button>
        </div>
    </div>
</div>
<script>
// فحص هل المستخدم قّيم الموقع قبل كده أول ما الصفحة تفتح
document.addEventListener("DOMContentLoaded", () => {
    const hasVoted = localStorage.getItem("synapse_voted");
    if (hasVoted) {
        disableFeedbackButtons(hasVoted);
    }
});

function disableFeedbackButtons(votedType) {
    const likeBtn = document.getElementById('likeBtn');
    const dislikeBtn = document.getElementById('dislikeBtn');
    const title = document.getElementById('feedbackTitle');
    
    likeBtn.disabled = true;
    dislikeBtn.disabled = true;
    title.innerText = "شكراً لتقييمك المنصة!";
    
    if (votedType === 'like') {
        likeBtn.classList.add('voted');
        likeBtn.innerHTML = '<i class="fas fa-thumbs-up"></i> تم الإعجاب <span class="count">' + document.getElementById('likeCount').innerText + '</span>';
    } else if (votedType === 'dislike') {
        dislikeBtn.classList.add('voted');
        dislikeBtn.innerHTML = '<i class="fas fa-thumbs-down"></i> تم التقييم <span class="count">' + document.getElementById('dislikeCount').innerText + '</span>';
    }
}

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
        else { responseCard.innerText = "عذراً: " + data.error; responseCard.style.display = 'block'; }
    } catch (e) { responseCard.innerText = "فشل في الاتصال بالخادم الذكي."; responseCard.style.display = 'block'; }
    finally { loadingArea.style.display = 'none'; }
}

async function sendFeedback(type) {
    if (localStorage.getItem("synapse_voted")) return;
    
    const likeBtn = document.getElementById('likeBtn');
    const dislikeBtn = document.getElementById('dislikeBtn');
    const likeCountSpan = document.getElementById('likeCount');
    const dislikeCountSpan = document.getElementById('dislikeCount');
    
    likeBtn.disabled = true;
    dislikeBtn.disabled = true;
    
    try {
        const res = await fetch('/feedback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type: type })
        });
        const data = await res.json();
        
        if (data.status === 'success') {
            localStorage.setItem("synapse_voted", type);
            
            if (type === 'like') {
                likeCountSpan.innerText = parseInt(likeCountSpan.innerText) + 1;
            } else {
                dislikeCountSpan.innerText = parseInt(dislikeCountSpan.innerText) + 1;
            }
            disableFeedbackButtons(type);
        }
    } catch (e) {
        likeBtn.disabled = false;
        dislikeBtn.disabled = false;
    }
}
</script>
</body>
</html>
"""

# لوحة السجلات السرية
LOGS_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>لوحة التحكم السرية - Synapse</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        body { font-family: 'Cairo', sans-serif; background-color: #0d1117; color: #c9d1d9; padding: 30px; }
        .table-container { max-width: 1000px; margin: 0 auto; background: #161b22; padding: 30px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); border: 1px solid #30363d; margin-bottom: 30px; }
        h2 { color: #fff; border-bottom: 2px solid #30363d; padding-bottom: 15px; display: flex; justify-content: space-between; align-items: center; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 15px; text-align: right; border-bottom: 1px solid #30363d; }
        th { background-color: #21262d; color: #00d2ff; }
        tr:hover { background-color: #1f242c; }
        .btn-delete { background: #f85149; color: white; border: none; padding: 8px 15px; border-radius: 6px; cursor: pointer; font-family: 'Cairo'; }
        .empty { text-align: center; padding: 30px; color: #8b949e; }
        .stats-box { display: flex; gap: 20px; margin-top: 15px; }
        .stat-card { background: #090d13; border: 1px solid #30363d; padding: 10px 20px; border-radius: 10px; font-size: 16px; }
        .stat-card.likes { color: #2ea043; }
        .stat-card.dislikes { color: #f85149; }
    </style>
</head>
<body>
<div class="table-container">
    <h2>
        <span><i class="fas fa-chart-bar"></i> إحصائيات تفاعل الموقع الإجمالية</span>
    </h2>
    <div class="stats-box">
        <div class="stat-card likes"><i class="fas fa-thumbs-up"></i> إجمالي الإعجابات: <strong>{{ likes_count }}</strong></div>
        <div class="stat-card dislikes"><i class="fas fa-thumbs-down"></i> إجمالي عدم الإعجاب: <strong>{{ dislikes_count }}</strong></div>
    </div>
</div>

<div class="table-container">
    <h2>
        <span><i class="fas fa-cloud-upload-alt"></i> السجل السحابي الداخلي للتطوير</span>
        <form action="/clear-logs" method="POST" style="margin:0;" onsubmit="return confirm('هل أنت متأكد من تصفير السجل؟');">
            <button type="submit" class="btn-delete"><i class="fas fa-trash"></i> تصفير البيانات</button>
        </form>
    </h2>
    <table>
        <thead>
            <tr>
                <th style="width: 10%;">ID</th>
                <th style="width: 40%;">السؤال</th>
                <th style="width: 50%;">إجابة الـ AI</th>
            </tr>
        </thead>
        <tbody>
            {% for row in rows %}
            <tr>
                <td>{{ row[0] }}</td>
                <td style="white-space: pre-wrap;">{{ row[1] }}</td>
                <td style="white-space: pre-wrap;">{{ row[2] }}</td>
            </tr>
            {% else %}
            <tr>
                <td colspan="3" class="empty">لا توجد محادثات مسجلة حالياً.</td>
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
    likes, dislikes = get_feedback_counts()
    # استخدام render_template_string الصحيحة والمضمونة للعمل صامتاً
    return render_template_string(HTML_TEMPLATE, likes=likes, dislikes=dislikes)

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    user_question = data.get("question", "")
    if not user_question:
        return jsonify({"error": "الاستعلام فارغ"}), 400

    if not API_KEYS:
        return jsonify({"error": "النظام يمر بفترة صيانة للمفاتيح، يرجى المحاولة لاحقاً."}), 500

    last_error = ""
    for current_key in API_KEYS:
        try:
            genai.configure(api_key=current_key)
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(user_question)
            ai_response = response.text
            
            save_interaction(user_question, ai_response)
            return jsonify({"answer": ai_response})
            
        except Exception as e:
            last_error = str(e)
            continue
            
    return jsonify({"error": "الخادم مضغوط حالياً، يرجى إعادة إرسال النبضة بعد ثوانٍ."}), 500

@app.route("/feedback", methods=["POST"])
def feedback():
    data = request.get_json()
    action_type = data.get("type", "")
    if action_type in ['like', 'dislike']:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO site_feedback (action_type) VALUES (%s)", (action_type,))
            cursor.close()
            conn.close()
            return jsonify({"status": "success"})
        except Exception as e:
            print(f"Feedback Save Error: {e}")
    return jsonify({"status": "ignored"}), 400

@app.route("/logs")
def show_logs():
    rows = []
    likes_count, dislikes_count = get_feedback_counts()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, user_question, ai_response FROM conversations ORDER BY id DESC")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        return f"Error: {e}"
    return render_template_string(LOGS_TEMPLATE, rows=rows, likes_count=likes_count, dislikes_count=dislikes_count)

@app.route("/clear-logs", methods=["POST"])
def clear_logs():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("TRUNCATE TABLE conversations RESTART IDENTITY;")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Clear Error: {e}")
    return redirect("/logs")

if __name__ == "__main__":
    app.run(debug=True, port=5000)
