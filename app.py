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


app = Flask(__name__)
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
                 designation TEXT NOT NULL,
                 phone TEXT NOT NULL,
                 email TEXT NOT NULL,
                 address TEXT NOT NULL,
                image_path TEXT
                 )''')
    conn.commit()
    conn.close()

init_db()

@app.route('/download_excel')
def download_excel():
    conn = sqlite3.connect('database.db')
    df = pd.read_sql_query("SELECT name, designation, phone, email, address FROM users", conn)
    conn.close()
    
    file_path = "static/exports/user_data.xlsx"
    df.to_excel(file_path, index=False)

    return send_file(file_path, as_attachment=True)






def create_id(name, designation, phone_number, email, address, photo):
    image = Image.open("id_template.png")
    d= ImageDraw.Draw(image)
    
    def add_text(text,text_pos,font_size):
        font_path = os.path.join("fonts", "Arial.ttf")
        font = ImageFont.truetype(font_path,font_size)
        d.text(text_pos,text,font=font,fill="black")

    add_text(name,(158,535),45)
    add_text(designation,(265,585),30)
    add_text(phone_number,(90,700),30)
    add_text(email,(90,782),30)
    add_text(address,(90,882),30)
    
    
    passport_image = Image.open(photo).convert("RGBA")
    passport_image = passport_image.resize((350, 350))  # optional
    
    image.paste(passport_image, (130, 150), passport_image)
    filename = f"{name}_{int(time.time())}.png"
    output_path = os.path.join("static","output_ids", filename)
    image.save(output_path)
    return output_path
    
    
    
    

@app.route('/', methods=['GET', 'POST'])
def form():
    download_url = None  # Define it at the start

    if request.method == 'POST':
        name = request.form['name']
        designation = request.form['designation']
        phone = request.form['phone']
        email = request.form['email']
        address = request.form['address']
        cropped_image_data = request.form['cropped_image']

    # Decode and save cropped image
        if ',' in cropped_image_data:
            header, encoded = cropped_image_data.split(",", 1)
        else:
            flash('Invalid image data received.', 'danger')
            return redirect(url_for('form'))
        binary_data = base64.b64decode(encoded)
        image = Image.open(BytesIO(binary_data))
    
    # Save image to static folder
        filename = secure_filename(f"{name.replace(' ', '_')}_photo.png")
        image_path = os.path.join('static/ids', filename)
        image.save(image_path)

        
        # Save to DB
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT INTO users (name, designation, phone, email, address, image_path) VALUES (?, ?, ?, ?, ?, ?)",
                  (name, designation, phone, email, address, image_path))
        conn.commit()
        conn.close()

        # Generate ID and get file path
        file_path = create_id(name, designation, phone, email, address, image_path)
        download_url = '/' + file_path  # Flask uses static/ prefix by default

        flash('Form submitted successfully! Your ID has been created.', 'success')
        
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
