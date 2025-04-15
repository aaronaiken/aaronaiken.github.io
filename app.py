from flask import Flask, request, render_template, Response
import datetime
import os
import subprocess
import functools
import pytz
wraps = functools.wraps

app = Flask(__name__)

# --- Configuration for Basic Auth ---
USERNAME = 'purring'  # Replace with your desired username
PASSWORD = '67i4uc_Rvq@yXjeNF_Z.'  # Replace with a strong password

def check_auth(username, password):
    """Checks if username/password combination is valid."""
    return username == USERNAME and password == PASSWORD

def authenticate():
    """Sends a 401 response that enables basic auth."""
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials.', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

def perform_git_operations(filename, commit_message):
    subprocess.run(["git", "pull", "origin", "main"], check=True)  # Pull first
    subprocess.run(["git", "add", filename], check=True)
    subprocess.run(["git", "commit", "-m", commit_message], check=True)
    subprocess.run(["git", "push", "origin", "main"], check=True)

def extract_tags(text):
    tags = []
    if "#movie" in text.lower():
        tags.append("movie")
    if "#book" in text.lower():
        tags.append("book")
    # Add more tag checks as needed
    return tags

def generate_front_matter(title, date_str, layout, author, source, content):
    front_matter = f"""---
title: {title}
date: {date_str}
layout: {layout}
author: {author}
source: {source}
"""
    tags = extract_tags(content)
    if tags:
        front_matter += f"tags: {tags}\n"
    front_matter += f"""---
{content}
"""
    print(front_matter)
    return front_matter

@app.route("/sms", methods=['POST'])
def sms_reply():
    sms_text = request.form['Body']
    utc_now = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
    eastern = pytz.timezone('America/New_York')
    now_eastern = utc_now.astimezone(eastern)
    date_str = now_eastern.strftime("%Y-%m-%d %H:%M:%S %z")
    filename = now_eastern.strftime("_status_updates/%Y-%m-%d-%H%M%S-status-sms.markdown")
    # now = datetime.datetime.now()
    # date_str = now.strftime("%Y-%m-%d %H:%M:%S %z")
    # filename = now.strftime("_status_updates/%Y-%m-%d-%H%M%S-status-sms.markdown")

    front_matter = generate_front_matter(
        title="Status Update",
        date_str=date_str,
        layout="status_update",
        author="aaron",
        source="sms ($0.0079)",
        content=sms_text
    )

    os.makedirs("_status_updates", exist_ok=True)
    with open(filename, "w") as f:
        f.write(front_matter)

    perform_git_operations(filename, "Add status update via SMS")
    return "OK", 200

@app.route("/publish", methods=['GET', 'POST'])
@requires_auth
def publish_status():
    if request.method == 'POST':
        status_text = request.form['status']
        utc_now = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
        eastern = pytz.timezone('America/New_York')
        now_eastern = utc_now.astimezone(eastern)
        date_str = now_eastern.strftime("%Y-%m-%d %H:%M:%S %z")
        print(f"Generated date string: {date_str}")
        filename = now_eastern.strftime("_status_updates/%Y-%m-%d-%H%M%S-status-web.markdown")
        # now = datetime.datetime.now()
        # date_str = now.strftime("%Y-%m-%d %H:%M:%S %z")
        # filename = now.strftime("_status_updates/%Y-%m-%d-%H%M%S-status-web.markdown")
        front_matter = generate_front_matter(
            title="Status Update",
            date_str=date_str,
            layout="status_update",
            author="aaron",
            source="web",
            content=status_text
        )
        os.makedirs("_status_updates", exist_ok=True)
        with open(filename, "w") as f:
            f.write(front_matter)
        perform_git_operations(filename, "Add status update via web form")
        return "Status update published via web!", 200
    else:
        return render_template('publish_form.html')
if __name__ == "__main__":
    app.run(debug=True)