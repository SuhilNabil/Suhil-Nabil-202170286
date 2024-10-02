import re
import cv2
import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox
import openai
import sqlite3
import long_responses as long
import textwrap  # مكتبة لتقسيم النصوص الطويلة
import random
import csv

# إعدادات OpenAI
openai.api_key = 'sk-proj-ZO8YvX2VDHtODBKD4Z9ZGnf6fYbIp5rR-guZmPtN1DiOX7RRnPUaLR4_Z_8KgwM3QODVyhe1TT3BlbkFJdGCoDuqWWIy0KwG0L5z2WX-CKcBemEoCaow35Qhsw6kfMVPeHn_N0lrI5ATeVHFUrMoogS17sA'

conn = sqlite3.connect('chatbot_responses.db')
c = conn.cursor()

# إنشاء جدول لتخزين الرسائل إذا لم يكن موجوداً بالفعل
c.execute('''CREATE TABLE IF NOT EXISTS responses 
             (prompt TEXT PRIMARY KEY, response TEXT)''')
conn.commit()


# وظيفة للتحقق من وجود رد محفوظ مسبقًا في قاعدة البيانات
def get_stored_response(prompt):
    c.execute("SELECT response FROM responses WHERE prompt = ?", (prompt,))
    result = c.fetchone()
    if result:
        return result[0]
    return None

# وظيفة لحفظ الردود في قاعدة البيانات
def store_response(prompt, response):
    try:
        c.execute("INSERT INTO responses (prompt, response) VALUES (?, ?)", (prompt, response))
        conn.commit()
    except sqlite3.IntegrityError:
        pass


# تقسيم النص الطويل إلى أجزاء صغيرة للتعامل مع الحدود
def split_prompt(prompt, max_length=4096):
    return textwrap.wrap(prompt, max_length)

# وظيفة لاستخدام GPT للحصول على الرد
def get_gpt_response(prompt):
    try:
        # تقسيم النص إذا كان طويلاً
        if len(prompt) > 4096:
            prompt_chunks = split_prompt(prompt)
        else:
            prompt_chunks = [prompt]
        
        gpt_responses = []
        for chunk in prompt_chunks:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant who provides detailed and accurate responses."},
                    {"role": "user", "content": chunk}
                ]
            )
            gpt_responses.append(response['choices'][0]['message']['content'].strip())
        
        gpt_response = " ".join(gpt_responses)  # دمج الردود المتعددة
        store_response(prompt, gpt_response)  # تخزين الرد المقدم من GPT
        return gpt_response
    except Exception as e:
        return f"Error: {str(e)}"

# إعداد ردود يدوية مع مجموعة متنوعة من الردود
manual_responses = [
    {"response": "Hello! How can I help you today? 😊", "keywords": ["hello", "hi", "hey"]},
    {"response": "What can I do for you? 💁‍♂️", "keywords": ["help", "assist", "support"]},
    {"response": "Goodbye! Have a great day! 👋", "keywords": ["bye", "goodbye"]},
    {"response": "I'm just a chatbot, but I'm here to assist! 🤖", "keywords": ["who", "are", "you"]},
    {"response": "I'm doing well, thank you! How about you? 😊", "keywords": ["how", "are", "you"]},
    {"response": "Sure! What would you like to know? 🤔", "keywords": ["question"]},
    {"response": "I'm here to help you with coding questions! 💻", "keywords": ["coding", "programming"]},
    {"response": "That's interesting! Tell me more! 👀", "keywords": ["tell", "more"]},
    {"response": "You’re welcome! If you have any more questions, feel free to ask! 🙌", "keywords": ["thank", "thanks"]},
    {"response": "I'm happy to assist you! Just let me know what you need. 😊", "keywords": ["need", "help"]},
    {"response": "Can you please clarify that? 🤔", "keywords": ["clarify", "explain"]},
    {"response": "I'm not sure about that. Maybe try asking in a different way. 🤷‍♂️", "keywords": ["not sure", "don't know"]},
    {"response": "That's a great question! Let me think... 🤔", "keywords": ["great question", "think"]},
    {"response": "I can provide resources for learning programming! 📚", "keywords": ["learning", "resources", "programming"]},
    {"response": "Do you have any specific topics in mind? 🧐", "keywords": ["specific", "topic", "mind"]},
    {"response": "I'm here to listen! What’s on your mind? 🗣️", "keywords": ["listen", "mind"]},
    {"response": "Thank you for chatting with me! 😊", "keywords": ["thank you", "appreciate"]},
    {"response": "I'm learning from our conversation! Keep talking! 🤖", "keywords": ["learning", "conversation"]},
    {"response": "Let's keep this conversation going! What else would you like to know? 💬", "keywords": ["continue", "more questions"]},
]

# وظيفة لتوليد ردود يدوية عشوائية
def generate_manual_responses(num_responses):
    for i in range(num_responses):
        manual_responses.append({
            "response": f"Response {i + 1}: This is a sample response. 🤖",
            "keywords": [f"keyword{i + 1}", f"sample{i + 1}"]
        })

# توليد 1000 رد يدوي
generate_manual_responses(1000)

# تحسين وظيفة حساب احتمالية الرد
def message_probability(user_message, recognised_words, single_response=False, required_words=[]):
    message_certainty = 0
    has_required_words = True

    for word in user_message:
        if word in recognised_words:
            message_certainty += 1

    percentage = float(message_certainty) / float(len(recognised_words)) if recognised_words else 0

    for word in required_words:
        if word not in user_message:
            has_required_words = False
            break

    if has_required_words or single_response:
        return int(percentage * 100)
    else:
        return 0

# تحسين الردود اليدوية
def check_all_messages(message):
    highest_prob_list = {}

    def response(bot_response, list_of_words, single_response=False, required_words=[]):
        nonlocal highest_prob_list
        highest_prob_list[bot_response] = message_probability(message, list_of_words, single_response, required_words)

    for entry in manual_responses:
        response(entry["response"], entry["keywords"])

    best_match = max(highest_prob_list, key=highest_prob_list.get)

    return long.unknown() if highest_prob_list[best_match] < 20 else best_match

# استرجاع الرد
def get_response(user_input):
    split_message = re.split(r'\s+|[,;?!.-]\s*', user_input.lower())
    return check_all_messages(split_message)


# واجهة المستخدم الرسومية GUI باستخدام tkinter مع إيموجي
def send_message():
    global username

    if not username:  # تأكد من أن المستخدم قد أدخل اسمًا
        messagebox.showwarning("Warning", "Please enter your name.")
        return

    user_message = user_input.get("1.0", "end").strip()
    if not user_message:
        messagebox.showwarning("Warning", "Please enter a message.")
        return

    chat_history.config(state=tk.NORMAL)
    chat_history.insert(tk.END, f"{username}: " + user_message + " 💬\n")

    # تحقق من وجود الرد في قاعدة البيانات أولاً
    stored_response = get_stored_response(user_message)
    if stored_response:
        bot_response = stored_response
    else:
        gpt_response = get_gpt_response(user_message)
        if "Error" in gpt_response:
            bot_response = get_response(user_message)  # استخدام الردود اليدوية إذا حدث خطأ
        else:
            bot_response = gpt_response  # تخزين الرد من GPT عند عدم وجود خطأ

    chat_history.insert(tk.END, "Bot: " + bot_response + " 🤖\n\n")
    chat_history.config(state=tk.DISABLED)

    user_input.delete("1.0", "end")




    # طلب ملاحظات المستخدم إذا لم يكن هناك رد مناسب
    if bot_response ==long.unknown():
        feedback = simpledialog.askstring("Feedback", "No suitable response found. Please provide the correct response:")
        if feedback:
            # تخزين الرد الصحيح
            store_response(user_message, feedback)



def unknown():
    response = ["Could you please re-phrase that? ",
                "...",
                "Sounds about right.",
                "What does that mean?"][
        random.randrange(4)]
                
    return response



# وظيفة لإدخال اسم المستخدم
def enter_username():
    global username

    username = user_input.get("1.0", "end").strip()
    if not username:
        messagebox.showwarning("Warning", "Name cannot be empty!")
        return
    
    # إضافة الرسالة الترحيبية إلى صندوق النص
    chat_history.config(state=tk.NORMAL)
    welcome_message = f"Welcome, {username}! 🌟 How can I assist you today?\n\n"
    chat_history.insert(tk.END, welcome_message)
    chat_history.config(state=tk.DISABLED)

    # إخفاء حقل الإدخال
    user_input.delete("1.0", "end")
    #user_input.config(state=tk.DISABLED)
    enter_button.pack_forget()  # إخفاء زر إدخال الاسم

# إنشاء نافذة GUI
window = tk.Tk()
window.title("AI Chatbot with Emoji")

# متغير لتخزين اسم المستخدم
username = ""

# صندوق النص لعرض المحادثة
chat_history = scrolledtext.ScrolledText(window, wrap=tk.WORD, state=tk.DISABLED)
chat_history.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

# رسالة توجيه لإدخال اسم المستخدم
prompt_message = "Please enter your name:"
chat_history.config(state=tk.NORMAL)
chat_history.insert(tk.END, prompt_message + "\n\n")
chat_history.config(state=tk.DISABLED)

# إدخال المستخدم لإدخال الاسم
user_input = tk.Text(window, height=3)
user_input.pack(padx=10, pady=(0, 10), fill=tk.X)

# زر الإدخال
enter_button = tk.Button(window, text="Enter Name", command=enter_username)
enter_button.pack(pady=(0, 10))

# زر الإرسال
send_button = tk.Button(window, text="Send", command=send_message)
send_button.pack(pady=(0, 10))

# تشغيل نافذة GUI
window.geometry("400x500")
window.mainloop()



def load_responses_from_csv(file_path):
    try:
        with open(file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            next(reader)  # تخطي رؤوس الأعمدة
            for row in reader:
                prompt, response = row
                # إضافة الرد إلى قاعدة البيانات
                store_response(prompt, response)
        print("Responses loaded successfully from CSV.")
    except Exception as e:
        print(f"Error loading CSV: {str(e)}")

# استدعاء دالة تحميل الردود من CSV عند بدء تشغيل البرنامج
csv_file_path = 'chatbot_responses.csv'  # مسار ملف الردود
#load_responses_from_csv(r'C:\Users\Suhil\Desktop\text_recogniton_chat-master\text_recogniton_chat-master\2.csv')
load_responses_from_csv(r'C:\Users\Suhil\Desktop\text_recogniton_chat-master\text_recogniton_chat-master\1.csv')


# إغلاق الاتصال بقاعدة البيانات عند إغلاق البرنامج
conn.close()




