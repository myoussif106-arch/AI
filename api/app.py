import os
import sqlite3
from datetime import datetime
from flask import Flask, jsonify, render_template_string, request
import google.generativeai as genai

app = Flask(__name__)

# 1. إعداد مفتاح جيمني - يقرأ تلقائياً من الـ Environment Variables في فيرسال بأمان
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)


# 2. الدالة المضمونة لإنشاء الجدول وحفظ البيانات فوراً في بيئة الـ Serverless
def save_interaction(question, response):
    # استخدام المسار /tmp/ المسموح بالكتابة عليه جوه سيرفرات Vercel
    with sqlite3.connect("/tmp/database.db") as conn:
        cursor = conn.cursor()

        # نضمن أولاً إن الجدول موجود في كل مرة بيتبعت فيها سؤال
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_question TEXT NOT NULL,
                ai_response TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """
        )

        # إدخال البيانات وحفظها فوراً
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO conversations (user_question, ai_response, created_at) VALUES (?, ?, ?)",
            (question, response, current_time),
        )
        conn.commit()


# 3. واجهة المستخدم الاحترافية الثيم الغامق (Synapse Dark Tech)
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
        :root {
            --bg-dark: #0d1117;
            --card-dark: #161b22;
            --neon-blue: #00d2ff;
            --neon-purple: #a855f7;
            --text-light: #c9d1d9;
            --text-bright: #ffffff;
            --border-color: #30363d;
        }

        body {
            font-family: 'Cairo', sans-serif;
            background-color: var(--bg-dark);
            background-image: radial-gradient(circle at 50% 50%, #161b33 0%, #0d1117 100%);
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            color: var(--text-light);
        }

        .container {
            width: 90%;
            max-width: 700px;
            background: var(--card-dark);
            padding: 40px;
            border-radius: 24px;
            box-shadow: 0 20px 50px rgba(0, 210, 255, 0.05), 0 0 0 1px var(--border-color);
            position: relative;
            overflow: hidden;
        }

        .container::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, var(--neon-blue), var(--neon-purple));
        }

        .header {
            text-align: center;
            margin-bottom: 35px;
        }

        .header .logo-icon {
            font-size: 55px;
            background: linear-gradient(45deg, var(--neon-blue), var(--neon-purple));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 15px;
            filter: drop-shadow(0 0 10px rgba(0, 210, 255, 0.3));
        }

        .header h1 {
            color: var(--text-bright);
            margin: 0;
            font-size: 32px;
            font-weight: 800;
            letter-spacing: 1px;
        }

        .header p {
            color: #8b949e;
            font-size: 15px;
            margin-top: 8px;
        }

        textarea {
            width: 100%;
            height: 130px;
            padding: 20px;
            border-radius: 16px;
            border: 2px solid var(--border-color);
            font-family: 'Cairo', sans-serif;
            font-size: 16px;
            resize: none;
            outline: none;
            transition: all 0.3s ease;
            box-sizing: border-box;
            background: #090d13;
            color: var(--text-bright);
        }

        textarea:focus {
            border-color: var(--neon-blue);
            box-shadow: 0 0 15px rgba(0, 210, 255, 0.2);
            background: #0d1117;
        }

        button {
            width: 100%;
            background: linear-gradient(90deg, var(--neon-blue), var(--neon-purple));
            color: white;
            border: none;
            padding: 16px;
            border-radius: 16px;
            font-family: 'Cairo', sans-serif;
            font-size: 18px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 12px;
            box-shadow: 0 4px 20px rgba(168, 85, 247, 0.2);
            margin-top: 15px;
        }

        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0, 210, 255, 0.4);
            filter: brightness(1.1);
        }

        .loading {
            display: none;
            margin: 25px 0;
            color: var(--neon-blue);
            font-weight: 600;
            font-size: 15px;
            text-align: center;
        }

        .loading i {
            margin-left: 8px;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(-360deg); }
        }

        .response-card {
            margin-top: 30px;
            padding: 25px;
            background: #1f242c;
            border-radius: 16px;
            color: #e6edf3;
            line-height: 1.8;
            display: none;
            animation: slideUp 0.4s ease;
            border-left: 4px solid var(--neon-purple);
            border-right: 4px solid var(--neon-blue);
            white-space: pre-wrap;
            text-align: right;
        }

        @keyframes slideUp {
            from { opacity: 0; transform: translateY(15px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .footer {
            margin-top: 35px;
            text-align: center;
            font-size: 13px;
            color: #58a6ff;
            font-weight: 600;
        }
    </style>
</head>
<body>

<div class="container">
    <div class="header">
        <i class="fas fa-brain logo-icon"></i>
        <h1>SYNAPSE</h1>
        <p>بوابة التفكير العصبي الاصطناعي - يتم تسجيل المدخلات بأمان</p>
    </div>

    <div class="input-group">
        <textarea id="questionInput" placeholder="أدخل استعلامك أو فكرتك هنا المحفوظة رقمياً..."></textarea>
    </div>

    <button onclick="askQuestion()">
        <span>إرسال النبضة العصبية</span>
        <i class="fas fa-bolt"></i>
    </button>
    
    <div id="loadingArea" class="loading">
        <i class="fas fa-microchip"></i> جاري معالجة البيانات وتخزين الاستعلام...
    </div>

    <div id="responseCard" class="response-card"></div>

    <div class="footer">
        <i class="fas fa-database"></i> متصل بنجاح بقاعدة البيانات المحفوظة ومؤمنة بالكامل
    </div>
</div>

<script>
async function askQuestion() {
    const input = document.getElementById('questionInput');
    const responseCard = document.getElementById('responseCard');
    const loadingArea = document.getElementById('loadingArea');
    
    if (!input.value.trim()) {
        alert('من فضلك أدخل استعلامك أولاً!');
        return;
    }
    
    loadingArea.style.display = 'block';
    responseCard.style.display = 'none';
    
    try {
        const res = await fetch('/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: input.value })
        });
        
        const data = await res.json();
        
        if (data.answer) {
            responseCard.innerText = data.answer;
            responseCard.style.display = 'block';
        } else {
            responseCard.innerText = "خطأ في النظام: " + data.error;
            responseCard.style.display = 'block';
        }
    } catch (e) {
        responseCard.innerText = "فشل في الاتصال بالخادم المركزي.";
        responseCard.style.display = 'block';
    } finally {
        loadingArea.style.display = 'none';
    }
}
</script>

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
        # استدعاء الموديل الأحدث المستقر كلياً
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(user_question)
        ai_response = response.text

        # استدعاء دالة الحفظ المدمجة لـ Vercel
        save_interaction(user_question, ai_response)

        return jsonify({"answer": ai_response})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # محلياً فقط للإحتياط، أما على سيرفر فيرسال فسيتم الإنشاء الفوري أوتوماتيكياً
    try:
        with sqlite3.connect("/tmp/database.db") as conn:
            pass
    except:
        pass
    app.run(debug=True, port=5000)
