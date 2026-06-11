import os
import base64
from flask import Flask, jsonify, render_template_string, request, redirect, session
import google.generativeai as genai
import psycopg2

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "synapse_secret_9988")

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
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
        # خطأ الداتابيز صامت تماماً في الخلفية
        print(f"Silent DB Error: {e}")

def get_feedback_counts():
    likes, dislikes = 0, 0
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM site_feedback WHERE action_type = 'like'")
        likes = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM site_feedback WHERE action_type = 'dislike'")
        dislikes = cursor.fetchone()[0]
        cursor.close()
        conn.close()
    except:
        pass
    return likes, dislikes

# --- قوالب الـ HTML ---

AUTH_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Synapse - تسجيل الدخول</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root { --bg-dark: #0d1117; --card-dark: #161b22; --neon-blue: #00d2ff; --neon-purple: #a855f7; --border-color: #30363d; }
        body { font-family: 'Cairo', sans-serif; background: var(--bg-dark); display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; color: #fff; }
        .box { background: var(--card-dark); padding: 40px; border-radius: 20px; width: 100%; max-width: 400px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); border: 1px solid var(--border-color); text-align: center; }
        h2 { margin-bottom: 25px; color: var(--neon-blue); }
        input { width: 100%; padding: 12px; margin: 10px 0; border-radius: 10px; border: 1px solid var(--border-color); background: #090d13; color: #fff; box-sizing: border-box; font-family: 'Cairo'; }
        button { width: 100%; padding: 12px; border-radius: 10px; border: none; background: linear-gradient(90deg, var(--neon-blue), var(--neon-purple)); color: white; font-weight: bold; cursor: pointer; font-family: 'Cairo'; margin-top: 15px; }
        .toggle-link { margin-top: 20px; display: block; color: #8b949e; text-decoration: none; font-size: 14px; }
        .msg { color: #ff7b72; font-size: 14px; margin-bottom: 10px; }
    </style>
</head>
<body>
<div class="box">
    <h2>SYNAPSE</h2>
    {% if msg %}<div class="msg">{{ msg }}</div>{% endif %}
    
    {% if mode == 'register' %}
    <form method="POST" action="/register">
        <input type="text" name="username" placeholder="اسم المستخدم" required>
        <input type="password" name="password" placeholder="كلمة المرور" required>
        <button type="submit">إنشاء طلب انضمام</button>
    </form>
    <a href="/login" class="toggle-link">لديك حساب بالفعل؟ سجل دخولك</a>
    {% else %}
    <form method="POST" action="/login">
        <input type="text" name="username" placeholder="اسم المستخدم" required>
        <input type="password" name="password" placeholder="كلمة المرور" required>
        <button type="submit">تسجيل الولوج</button>
    </form>
    <a href="/register" class="toggle-link">مستخدم جديد؟ قدم طلب انضمام</a>
    {% endif %}
</div>
</body>
</html>
"""

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Synapse AI - التفكير العصبي الرقمي</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        :root { --bg-dark: #0d1117; --card-dark: #161b22; --neon-blue: #00d2ff; --neon-purple: #a855f7; --text-light: #c9d1d9; --text-bright: #ffffff; --border-color: #30363d; }
        body { font-family: 'Cairo', sans-serif; background-color: var(--bg-dark); background-image: radial-gradient(circle at 50% 50%, #161b33 0%, #0d1117 100%); margin: 0; padding: 0; display: flex; justify-content: center; align-items: center; min-height: 100vh; color: var(--text-light); }
        .container { width: 90%; max-width: 700px; background: var(--card-dark); padding: 40px; border-radius: 24px; box-shadow: 0 20px 50px rgba(0, 210, 255, 0.05), 0 0 0 1px var(--border-color); position: relative; }
        .container::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 4px; background: linear-gradient(90deg, var(--neon-blue), var(--neon-purple)); }
        .header { text-align: center; margin-bottom: 35px; position: relative; }
        .header .logo-icon { font-size: 55px; background: linear-gradient(45deg, var(--neon-blue), var(--neon-purple)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 15px; }
        .header h1 { color: var(--text-bright); margin: 0; font-size: 32px; font-weight: 800; }
        .logout-btn { position: absolute; top: 0; left: 0; color: #ff7b72; text-decoration: none; font-size: 14px; border: 1px solid #30363d; padding: 5px 12px; border-radius: 8px; background: #090d13; }
        
        .input-wrapper { background: #090d13; border: 2px solid var(--border-color); border-radius: 16px; padding: 10px; margin-bottom: 15px; }
        .input-wrapper:focus-within { border-color: var(--neon-blue); }
        textarea { width: 100%; height: 110px; border: none; font-family: 'Cairo'; font-size: 16px; resize: none; outline: none; box-sizing: border-box; background: transparent; color: var(--text-bright); padding: 10px; }
        
        .tools-bar { display: flex; justify-content: space-between; align-items: center; padding: 5px 10px; border-top: 1px solid var(--border-color); margin-top: 5px; }
        .file-upload-btn { color: var(--neon-blue); cursor: pointer; font-size: 14px; display: flex; align-items: center; gap: 6px; background: #161b22; padding: 6px 12px; border-radius: 8px; border: 1px solid var(--border-color); transition: all 0.3s; }
        .file-upload-btn:hover { background: #21262d; box-shadow: 0 0 8px rgba(0, 210, 255, 0.3); }
        #fileInfo { font-size: 12px; color: #8b949e; }
        
        button.btn-main { width: 100%; background: linear-gradient(90deg, var(--neon-blue), var(--neon-purple)); color: white; border: none; padding: 16px; border-radius: 16px; font-weight: bold; cursor: pointer; display: flex; justify-content: center; align-items: center; gap: 12px; font-family: 'Cairo'; font-size: 18px; }
        .loading { display: none; margin: 25px 0; color: var(--neon-blue); text-align: center; font-weight:600; }
        .response-card { margin-top: 30px; padding: 25px; background: #1f242c; border-radius: 16px; display: none; border-left: 4px solid var(--neon-purple); border-right: 4px solid var(--neon-blue); white-space: pre-wrap; text-align: right; }
        .response-card img { max-width: 100%; border-radius: 12px; margin-top: 15px; border: 2px solid var(--border-color); }
        
        .status-msg { background: #21262d; padding: 15px; border-radius: 12px; text-align: center; border: 1px solid #30363d; color: #e6edf3; }
        .feedback-section { margin-top: 40px; display: flex; flex-direction: column; align-items: center; gap: 12px; padding-top: 25px; border-top: 1px solid var(--border-color); }
        .feedback-buttons { display: flex; gap: 20px; }
        .feedback-btn { background: #090d13; border: 1px solid var(--border-color); color: var(--text-light); padding: 10px 22px; border-radius: 12px; cursor: pointer; font-family: 'Cairo'; font-size: 14px; display: flex; align-items: center; gap: 8px; }
        .feedback-btn .count { font-weight: bold; background: #21262d; padding: 2px 8px; border-radius: 20px; font-size: 12px; }
        .feedback-btn:disabled { opacity: 0.6; pointer-events: none; }
        .feedback-btn.voted { border-color: #58a6ff !important; color: #58a6ff !important; }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <a href="/logout" class="logout-btn"><i class="fas fa-sign-out-alt"></i> خروج</a>
        <i class="fas fa-brain logo-icon"></i>
        <h1>SYNAPSE</h1>
        <p>مرحباً بك يا {{ user }} في المنظومة الذكية</p>
    </div>

    {% if status == 'pending' %}
    <div class="status-msg">
        <i class="fas fa-hourglass-half" style="color: #e3b341; font-size: 24px; margin-bottom:10px;"></i>
        <p>طلب الانضمام الخاص بك قيد المراجعة الأمنية حالياً من قِبل إدارة التطبيق. سيتم فتح النظام لك فور قبولك!</p>
    </div>
    {% elif status == 'rejected' %}
    <div class="status-msg" style="border-color: #f85149;">
        <i class="fas fa-times-circle" style="color: #f85149; font-size: 24px; margin-bottom:10px;"></i>
        <p>عذراً، تم رفض طلب انضمام هذا الحساب للمنظومة.</p>
    </div>
    {% else %}
    
    <div class="input-wrapper">
        <textarea id="questionInput" placeholder="اكتب سؤالك، أو ارفع ملف واطلب شرحه، أو اكتب 'ارسم كذا' لتوليد صورة..."></textarea>
        <div class="tools-bar">
            <label class="file-upload-btn" for="fileInput">
                <i class="fas fa-paperclip"></i> رفع صورة / PDF
            </label>
            <input type="file" id="fileInput" accept="image/*, application/pdf" style="display: none;" onchange="handleFileSelect()">
            <span id="fileInfo">لم يتم اختيار ملف</span>
        </div>
    </div>
    
    <button class="btn-main" onclick="askQuestion()">
        <span>إرسال النبضة العصبية</span> <i class="fas fa-bolt"></i>
    </button>
    <div id="loadingArea" class="loading"><i class="fas fa-spinner fa-spin"></i> جاري توليد المعالجة العصبية...</div>
    <div id="responseCard" class="response-card"></div>
    
    <div class="feedback-section">
        <div id="feedbackTitle" style="font-size: 14px; color: #8b949e;">ما هو تقييمك للمنصة؟</div>
        <div class="feedback-buttons">
            <button class="feedback-btn" id="likeBtn" onclick="sendFeedback('like')">
                <i class="far fa-thumbs-up"></i> أعجبني <span class="count" id="likeCount">{{ likes }}</span>
            </button>
            <button class="feedback-btn" id="dislikeBtn" onclick="sendFeedback('dislike')">
                <i class="far fa-thumbs-down"></i> لم يعجبني <span class="count" id="dislikeCount">{{ dislikes }}</span>
            </button>
        </div>
    </div>
    {% endif %}
</div>
<script>
let selectedFileBase64 = "";
let selectedFileType = "";

document.addEventListener("DOMContentLoaded", () => {
    const hasVoted = localStorage.getItem("synapse_voted");
    if (hasVoted && document.getElementById('likeBtn')) { disableFeedbackButtons(hasVoted); }
});

function handleFileSelect() {
    const fileInput = document.getElementById('fileInput');
    const fileInfo = document.getElementById('fileInfo');
    if (!fileInput.files.length) return;
    
    const file = fileInput.files[0];
    fileInfo.innerText = file.name + " (" + (file.size/1024/1024).toFixed(2) + " MB)";
    selectedFileType = file.type;
    
    const reader = new FileReader();
    reader.onload = function(e) {
        selectedFileBase64 = e.target.result.split(',')[1];
    };
    reader.readAsDataURL(file);
}

function disableFeedbackButtons(votedType) {
    const likeBtn = document.getElementById('likeBtn'); const dislikeBtn = document.getElementById('dislikeBtn');
    likeBtn.disabled = true; dislikeBtn.disabled = true;
    document.getElementById('feedbackTitle').innerText = "شكراً لتقييمك المنصة!";
    if (votedType === 'like') { likeBtn.classList.add('voted'); } else { dislikeBtn.classList.add('voted'); }
}

async function askQuestion() {
    const input = document.getElementById('questionInput'); 
    const responseCard = document.getElementById('responseCard'); 
    const loadingArea = document.getElementById('loadingArea');
    
    if (!input.value.trim() && !selectedFileBase64) { alert('من فضلك أدخل استعلامك أو ارفع ملفاً أولاً!'); return; }
    
    loadingArea.style.display = 'block'; responseCard.style.display = 'none';
    
    try {
        const payload = { 
            question: input.value,
            fileData: selectedFileBase64,
            fileType: selectedFileType
        };
        
        const res = await fetch('/ask', { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify(payload) 
        });
        const data = await res.json();
        
        if (data.image) {
            responseCard.innerHTML = (data.text ? "<p>"+data.text+"</p>" : "") + `<img src="data:image/png;base64,${data.image}" />`;
            responseCard.style.display = 'block';
        } else if (data.answer) { 
            responseCard.innerText = data.answer; 
            responseCard.style.display = 'block'; 
        } else if (data.debug_keys_found_in_vercel) {
            // عرض لستة الديباج بشكل منظم لو المصفوفة فاضية
            responseCard.innerHTML = `<p style="color:#ff7b72; font-weight:bold;">${data.error}</p><p>المفاتيح المتاحة بالسيرفر حالياً:</p><pre style="background:#090d13; padding:10px; border-radius:8px; text-align:left; direction:ltr;">${JSON.stringify(data.debug_keys_found_in_vercel, null, 2)}</pre>`;
            responseCard.style.display = 'block';
        } else { 
            responseCard.innerText = data.error; 
            responseCard.style.display = 'block'; 
        }
        
        selectedFileBase64 = "";
        selectedFileType = "";
        document.getElementById('fileInput').value = "";
        document.getElementById('fileInfo').innerText = "لم يتم اختيار ملف";
        
    } catch (e) { 
        responseCard.innerText = "فشل في الاتصال بالخادم العصبي."; 
        responseCard.style.display = 'block'; 
    } finally { 
        loadingArea.style.display = 'none'; 
    }
}

async function sendFeedback(type) {
    if (localStorage.getItem("synapse_voted")) return;
    try {
        const res = await fetch('/feedback', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ type: type }) });
        const data = await res.json();
        if (data.status === 'success') {
            localStorage.setItem("synapse_voted", type);
            const span = document.getElementById(type + 'Count');
            span.innerText = parseInt(span.innerText) + 1;
            disableFeedbackButtons(type);
        }
    } catch (e) {}
}
</script>
</body>
</html>
"""

ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8"><title>لوحة الإشراف والتحكم</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Cairo', sans-serif; background: #0d1117; color: #c9d1d9; padding: 30px; }
        .container { max-width: 900px; margin: 0 auto; background: #161b22; padding: 30px; border-radius: 20px; border: 1px solid #30363d; }
        h2 { border-bottom: 2px solid #30363d; padding-bottom: 10px; display: flex; justify-content: space-between; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 12px; text-align: right; border-bottom: 1px solid #30363d; }
        th { background: #21262d; color: #00d2ff; }
        .btn { padding: 6px 12px; border-radius: 6px; border: none; cursor: pointer; font-family: 'Cairo'; font-weight: bold; text-decoration: none; color: white; margin-left: 5px; }
        .btn-approve { background: #2ea043; }
        .btn-reject { background: #f85149; }
        .badge { padding: 4px 8px; border-radius: 12px; font-size: 12px; }
        .badge-pending { background: #865e00; color: #ffdf7a; }
        .badge-approved { background: #145023; color: #56d364; }
        .badge-rejected { background: #6c1915; color: #ff9492; }
    </style>
</head>
<body>
<div class="container">
    <h2>
        <span><i class="fas fa-users-cog"></i> إدارة طلبات العضوية والتحكم صامتاً</span>
        <a href="/" style="color: #58a6ff; font-size:16px; text-decoration:none;">العودة للرئيسية ←</a>
    </h2>
    <table>
        <thead>
            <tr>
                <th>المستخدم</th>
                <th>تاريخ الطلب</th>
                <th>الحالة</th>
                <th>الإجراء السري</th>
            </tr>
        </thead>
        <tbody>
            {% for u in users %}
            <tr>
                <td><strong>{{ u[1] }}</strong></td>
                <td>{{ u[4] }}</td>
                <td><span class="badge badge-{{ u[3] }}">{{ u[3] }}</span></td>
                <td>
                    {% if u[3] == 'pending' or u[3] == 'rejected' %}
                    <a href="/admin/action/{{ u[0] }}/approved" class="btn btn-approve">قبول</a>
                    {% endif %}
                    {% if u[3] == 'pending' or u[3] == 'approved' %}
                    {% if u[1] != 'admin' %}
                    <a href="/admin/action/{{ u[0] }}/rejected" class="btn btn-reject">رفض</a>
                    {% endif %}
                    {% endif %}
                </td>
            </tr>
            {% else %}
            <tr><td colspan="4" style="text-align:center; color:#8b949e;">لا يوجد مستخدمين مسجلين.</td></tr>
            {% endfor %}
        </tbody>
    </table>
</div>
</body>
</html>
"""

# --- مسارات التطبيق والتحكم بالـ Sessions ---

@app.route("/")
def home():
    if "user" not in session:
        return redirect("/login")
    likes, dislikes = get_feedback_counts()
    return render_template_string(HTML_TEMPLATE, user=session["user"], status=session["status"], likes=likes, dislikes=dislikes)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "").strip()
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, password, status FROM site_users WHERE username = %s", (username,))
            user_row = cursor.fetchone()
            cursor.close()
            conn.close()
            if user_row and user_row[2] == password:
                session["user"] = user_row[1]
                session["status"] = user_row[3]
                return redirect("/")
            else:
                return render_template_string(AUTH_TEMPLATE, mode="login", msg="خطأ في اسم المستخدم أو كلمة المرور.")
        except Exception as e:
            return render_template_string(AUTH_TEMPLATE, mode="login", msg="حدث خطأ أثناء الاتصال بالخادم الداخلي.")
    return render_template_string(AUTH_TEMPLATE, mode="login")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "").strip()
        if len(username) < 3 or len(password) < 4:
            return render_template_string(AUTH_TEMPLATE, mode="register", msg="البيانات المدخلة قصيرة جداً.")
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO site_users (username, password, status) 
                VALUES ('admin', 'Synapse_Admin_2026!#', 'approved')
                ON CONFLICT (username) DO NOTHING;
            """)
            cursor.execute("INSERT INTO site_users (username, password, status) VALUES (%s, %s, 'pending')", (username, password))
            cursor.close()
            conn.close()
            return render_template_string(AUTH_TEMPLATE, mode="login", msg="تم تقديم طلبك بنجاح! يرجى انتظار المراجعة.")
        except psycopg2.errors.UniqueViolation:
            return render_template_string(AUTH_TEMPLATE, mode="register", msg="اسم المستخدم هذا محجوز مسبقاً.")
        except Exception as e:
            return render_template_string(AUTH_TEMPLATE, mode="register", msg="حدث خطأ في معالجة طلب التسجيل.")
    return render_template_string(AUTH_TEMPLATE, mode="register")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/ask", methods=["POST"])
def ask():
    if "user" not in session or session.get("status") != "approved":
        return jsonify({"error": "غير مصرح لك بالاستخدام حالياً."}), 403

    # ربط صريح ومطهر للمفاتيح من متغيرات فيرسال
    possible_keys = [
        os.environ.get("GEMINI_API_KEY"),
        os.environ.get("GEMINI_KEY_1"),
        os.environ.get("GEMINI_KEY_2"),
        os.environ.get("GEMINI_KEY_3")
    ]
    
    current_keys = [key.strip() for key in possible_keys if key and key.strip()]

    data = request.get_json()
    user_question = data.get("question", "").strip()
    file_data = data.get("fileData", "")
    file_type = data.get("fileType", "")

    if not user_question and not file_data:
        return jsonify({"error": "الاستعلام فارغ"}), 400

    is_drawing_request = any(user_question.startswith(p) for p in ["ارسم", "انشئ صورة ل", "صورة ل", "draw", "create image"])

    # عيون الديباج الذكية: لو لستة المفاتيح فاضية، اطبع الأسماء المتاحة في السيرفر حالا
    if not current_keys:
        all_env_names = list(os.environ.keys())
        return jsonify({
            "error": "خطأ مطابقة: السيرفر لم ينجح في العثور على قيم حية للمفاتيح المدخلة.",
            "debug_keys_found_in_vercel": all_env_names
        }), 500

    for current_key in current_keys:
        try:
            genai.configure(api_key=current_key)

            if is_drawing_request:
                prompt = user_question
                for p in ["ارسم", "انشئ صورة ل", "صورة ل", "draw", "create image"]:
                    prompt = prompt.replace(p, "").strip()
                
                imagen_model = genai.GenerativeModel("imagen-3.0-generate-002")
                result = imagen_model.generate_images(prompt=prompt, number_of_images=1)
                
                for img in result.images:
                    encoded_img = base64.b64encode(img.image_bytes).decode('utf-8')
                    save_interaction(user_question, f"[توليد صورة بنجاح لـ: {prompt}]")
                    return jsonify({"image": encoded_img, "text": f"تم معالجة النبضة العصبية البصرية لـ: {prompt}"})

            else:
                model = genai.GenerativeModel("gemini-2.5-flash")
                contents = []

                if file_data and file_type:
                    contents.append({
                        'mime_type': file_type,
                        'data': base64.b64decode(file_data)
                    })
                
                if user_question:
                    contents.append(user_question)

                response = model.generate_content(contents)
                ai_response = response.text
                
                save_interaction(user_question, ai_response)
                return jsonify({"answer": ai_response})

        except Exception as e:
            print(f"Key failed processing: {current_key[:8]}... Error: {e}")
            continue
            
    return jsonify({"error": "السيرفر عليه ضغط حالياً وعليه الانتظار ثواني."}), 500

@app.route("/feedback", methods=["POST"])
def feedback():
    if "user" not in session or session.get("status") != "approved":
        return jsonify({"status": "ignored"}), 403
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
        except:
            pass
    return jsonify({"status": "ignored"}), 400

@app.route("/logs")
def show_logs():
    if "user" not in session or session["user"] != "admin":
        return redirect("/login")
    users_list = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, password, status, created_at FROM site_users ORDER BY id DESC")
        users_list = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        return f"Error: {e}"
    return render_template_string(ADMIN_TEMPLATE, users=users_list)

@app.route("/admin/action/<int:user_id>/<string:new_status>")
def admin_action(user_id, new_status):
    if "user" not in session or session["user"] != "admin":
        return redirect("/login")
    if new_status in ['approved', 'rejected']:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE site_users SET status = %s WHERE id = %s", (new_status, user_id))
            cursor.close()
            conn.close()
        except:
            pass
    return redirect("/logs")

if __name__ == "__main__":
    app.run(debug=True, port=5000)
