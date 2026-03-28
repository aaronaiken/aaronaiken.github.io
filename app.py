from flask import Flask, request, render_template, make_response, redirect, url_for
import datetime
import os
import subprocess
import functools
import pytz
import requests
import emoji
import glob

app = Flask(__name__)

# --- Configuration & Secrets ---
app.secret_key = os.environ.get('FLASK_SECRET_KEY')
PASSWORD = os.environ.get('FLASK_PASSWORD')

def is_authenticated():
    return request.cookies.get('auth_token') == 'authenticated_user'

def get_git_status():
    try:
        subprocess.run(["git", "fetch"], check=True, capture_output=True)
        status = subprocess.check_output(["git", "status", "-uno"], encoding='utf-8')
        if "Your branch is up to date" in status:
            return "online"
        elif "Your branch is ahead of" in status:
            return "syncing"
        else:
            return "offline"
    except Exception:
        return "offline"

def post_to_omg_lol(status_text):
    api_key = os.environ.get('OMG_LOL_API_KEY')
    address = os.environ.get('OMG_LOL_ADDRESS')
    if not api_key or not address: return
    url = f"https://api.omg.lol/address/{address}/statuses"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    status_text = status_text.strip()
    emojis_found = emoji.emoji_list(status_text)
    payload = {}

    # Logic to handle Omg.lol "icon" emoji vs content
    if emojis_found and emojis_found[0]['match_start'] == 0:
        extracted_emoji = emojis_found[0]['emoji']
        payload["emoji"] = extracted_emoji
        payload["content"] = status_text[len(extracted_emoji):].strip()
    else:
        payload["content"] = status_text

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to post to Omg.lol: {e}")

def perform_git_operations(filename, commit_message):
    subprocess.run(["git", "pull", "origin", "main"], check=True)
    subprocess.run(["git", "add", filename], check=True)
    subprocess.run(["git", "commit", "-m", commit_message], check=True)
    subprocess.run(["git", "push", "origin", "main"], check=True)

def extract_tags(text):
    tags = []
    valid_tags = ["movie", "book", "music", "idea", "tech", "coffee"]
    for tag in valid_tags:
        if f"#{tag}" in text.lower():
            tags.append(tag)
    return tags

def generate_front_matter(title, date_str, layout, author, source, content):
    fm = f"---\ntitle: {title}\ndate: {date_str}\nlayout: {layout}\nauthor: {author}\nsource: {source}\n"
    tags = extract_tags(content)
    if tags: fm += f"tags: {tags}\n"
    fm += f"---\n{content}\n"
    return fm

# --- Routes ---

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('password') == PASSWORD:
            resp = make_response(redirect(url_for('publish_status')))
            resp.set_cookie('auth_token', 'authenticated_user', max_age=60*60*24*30, httponly=True, samesite='Lax')
            return resp
        return "Invalid Password", 401
    return render_template('login.html')

@app.route("/logout")
def logout():
    resp = make_response(redirect(url_for('login')))
    resp.set_cookie('auth_token', '', expires=0)
    return resp

@app.route("/publish", methods=['GET', 'POST'])
def publish_status():
    if not is_authenticated(): return redirect(url_for('login'))

    if request.method == 'POST':
        status_text = request.form['status']
        utc_now = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
        eastern = pytz.timezone('America/New_York')
        now_eastern = utc_now.astimezone(eastern)
        date_str = now_eastern.strftime("%Y-%m-%d %H:%M:%S %z")
        filename = now_eastern.strftime("_status_updates/%Y-%m-%d-%H%M%S-status-web.markdown")

        fm = generate_front_matter("Status Update", date_str, "status_update", "aaron", "web", status_text)
        os.makedirs("_status_updates", exist_ok=True)
        with open(filename, "w") as f: f.write(fm)

        perform_git_operations(filename, "Add status update via web form")
        post_to_omg_lol(status_text)
        return render_template('success.html')
    else:
        git_status = get_git_status()
        history = []
        files = sorted(glob.glob("_status_updates/*.markdown"), reverse=True)[:3]
        for f in files:
            with open(f, 'r') as cf:
                history.append(cf.read().split("---")[-1].strip())
        return render_template('publish_form.html', history=history, git_status=git_status)

@app.route('/sw.js')
def service_worker(): return app.send_static_file('sw.js')

if __name__ == "__main__":
    app.run(debug=True)