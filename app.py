from flask import Flask, render_template, request, redirect, flash, Response, send_file, url_for
import sqlite3
from PIL import Image,ImageDraw,ImageFont
import os
import time
import pandas as pd
from functools import wraps
from werkzeug.utils import secure_filename
import base64
from io import BytesIO
from langdetect import detect
from twilio.rest import Client

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 
app.secret_key = 'your_secret_key'



def check_auth(username, password):
    return username == 'admin' and password == 'password'

def authenticate():
    return Response(
        'Access denied. Please provide proper credentials.', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# Database setup
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 name TEXT NOT NULL,
                 DOB TEXT NOT NULL,
                 phone TEXT NOT NULL,
                 address TEXT NOT NULL,
                image_path TEXT
                 )''')
    conn.commit()
    conn.close()

init_db()

@app.route('/download_excel')
def download_excel():
    conn = sqlite3.connect('database.db')
    df = pd.read_sql_query("SELECT name, DOB, phone, address FROM users", conn)
    conn.close()
    
    file_path = "static/exports/user_data.xlsx"
    df.to_excel(file_path, index=False)

    return send_file(file_path, as_attachment=True)


LANGUAGE_FONT_MAP = {
    "en": "english.ttf",
    #"en": "/Users/tanmay.ikare/Documents/tanmay-personal/id-card/fonts/english.ttf",
    "hi": "marathi.ttf",
    "mr": "marathi.ttf"
}

def create_id(name, DOB, phone_number, address, photo):
    image = Image.open("id_template.png")
    d= ImageDraw.Draw(image)
    
    def add_text(text,text_pos,font_size):
        try:
        # Detect the language of the input text
            detected_lang = detect(text)
        except Exception:
            detected_lang = "en"
            
        font_file = LANGUAGE_FONT_MAP.get(detected_lang, LANGUAGE_FONT_MAP["en"])
        font_path = os.path.join("fonts", font_file)
        font = ImageFont.truetype(font_path,font_size)
        d.text(text_pos,text,font=font,fill="black")

    add_text(name,(303,303),45)
    add_text(DOB,(269,437),30)
    add_text(phone_number,(479,380),30)
    add_text(address,(161,500),45)
    
    passport_image = Image.open(photo).convert("RGBA")
    passport_image = passport_image.resize((163,182))  # optional
    
    image.paste(passport_image, (948,294), passport_image)
    filename = f"{name}_{int(time.time())}.png"
    output_path = os.path.join("static","output_ids", filename)
    image.save(output_path)
    return output_path
    
    
    
    

@app.route('/', methods=['GET', 'POST'])
def form():
    download_url = None  # Define it at the start

    if request.method == 'POST':
        name = request.form['name']
        DOB = request.form['DOB']
        phone = request.form['phone']
        address = request.form['address']
        photo = request.files.get('photo')

    
    # Save image to static folder
        filename = secure_filename(f"{name.replace(' ', '_')}_photo.png")
        image_path = os.path.join('static/ids', filename)
        photo.save(image_path)

        
        # Save to DB
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT INTO users (name, DOB, phone, address, image_path) VALUES (?, ?, ?, ?, ?)",
                  (name, DOB, phone, address, image_path))
        conn.commit()
        conn.close()

        # Generate ID and get file path
        file_path = create_id(name, DOB, phone, address, image_path)
        download_url = '/' + file_path  # Flask uses static/ prefix by default

        flash('Form submitted successfully! Your ID has been created.', 'success')
        
        #sms service
        account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        client = Client(account_sid, auth_token)
        phone_number = "+91"+str(phone)
        message_body = "Thank you for registration at Mayboli Pratishthan for year 2025-26. For further details join following whatsapp group : https://chat.whatsapp.com/FgIZjeiZc8IHCce1meV2Nh. Download your generated ID card by clicking below : " + "https://demoid-bytanmay.onrender.com/"+download_url
        message = client.messages.create(
            body=message_body,
            from_="+14235893521",
            to=phone_number,
        )
        
        # Redirect with download url as a query parameter
        return redirect(url_for('form', download=download_url))

    # GET request
    download_url = request.args.get('download')
    return render_template('index.html', download_url=download_url)


@app.route('/admin')
@requires_auth
def admin():

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    users = c.fetchall()
    conn.close()
    return render_template('admin.html', users=users)

@app.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join('static', 'output_ids', filename)
    return send_file(file_path, as_attachment=True)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
