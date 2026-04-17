from flask import Flask, request, render_template, make_response, redirect, url_for, jsonify
from werkzeug.utils import secure_filename # Correct way to get this
from PIL import Image # Correct way to get Image
from datetime import datetime
import os, subprocess, pytz, requests, emoji, glob, json, time

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY')
PASSWORD = os.environ.get('FLASK_PASSWORD')

# Point this to your local clone of the GitHub Pages repo on PythonAnywhere
UPLOAD_FOLDER = '/home/aaronaiken/status_update/assets/img/status/'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Path to tasks.json inside the Jekyll repo clone
TASKS_FILE = 'assets/data/tasks.json'

def is_authenticated():
    return request.cookies.get('auth_token') == 'authenticated_user'

def get_git_status():
    """Checks if local repo is in sync with origin/main."""
    try:
        # 1. Try to fetch. If this fails, we are 'offline'.
        # We use a timeout so it doesn't hang the web app.
        subprocess.run(["git", "fetch"], check=True, capture_output=True, timeout=5)

        # 2. Check the status
        status = subprocess.check_output(["git", "status", "-sb"], encoding='utf-8')

        # 'sb' gives a short branch status like: ## main...origin/main
        if "ahead" in status:
            return "syncing" # Yellow: Local changes not yet pushed
        elif "behind" in status:
            return "offline" # Red: Needs a pull
        else:
            return "online"  # Green: All systems go
    except Exception as e:
        print(f"Git Status Error: {e}")
        return False

def get_active_tags():
    pa_tz = pytz.timezone('America/New_York')
    now = datetime.now(pa_tz)

    print(f"DEBUG: Local PA Time is {now.strftime('%H:%M:%S')}")

    tags = ["ALL"]
    hour = now.hour

    tags.append(now.strftime("%A").upper()) # Adds 'THURSDAY', 'FRIDAY', etc.

    # Ensure 24-hour coverage
    if 5 <= hour < 12:
        tags.append("AM")

    # PM should be active from Noon until Midnight
    if 12 <= hour < 24:
        tags.append("PM")

    # EVE overlaps for the late-night vibe
    if hour >= 17 or hour < 5:
        tags.append("EVE")

    # Day Type
    day_type = "WEEKEND" if now.weekday() >= 5 else "WEEKDAY"
    tags.append(day_type)

    # Special Dates
    date_str = now.strftime("%m/%d")
    if date_str == "12/25": tags.append("CHRISTMAS")
    if date_str == "03/11": tags.append("BIRTHDAY")
    if date_str == "04/05": tags.append("EASTER")

    return tags

def get_valid_comms():
    active_tags = get_active_tags()
    valid_comms = []

    try:
        with open('static/comms.txt', 'r') as f:
            for line in f:
                clean_line = line.strip()
                if not clean_line:
                    continue

                # --- FIX: These blocks must be INSIDE the for loop ---
                if "|" not in clean_line:
                    valid_comms.append(clean_line)
                    continue

                parts = clean_line.split("|")
                message = parts[-1].strip()
                required_tags = [p.strip().upper() for p in parts[:-1] if p.strip()]

                if all(tag in active_tags for tag in required_tags):
                    # SPECIFICITY WEIGHTING:
                    # If it matches specific tags (like PM), add it 10 times
                    # so it shows up way more often than 'ALL' lines.
                    weight = 10 ** len(required_tags)
                    for _ in range(weight):
                        valid_comms.append(message)
                # ----------------------------------------------------

    except FileNotFoundError:
        return ["Secure line cut."]

    return valid_comms if valid_comms else ["Scanning..."]

def post_to_omg_lol(text):
    api, addr = os.environ.get('OMG_LOL_API_KEY'), os.environ.get('OMG_LOL_ADDRESS')
    if not api or not addr: return
    url = f"https://api.omg.lol/address/{addr}/statuses"
    text = text.strip()
    found = emoji.emoji_list(text)
    payload = {"content": text}
    if found and found[0]['match_start'] == 0:
        payload["emoji"] = found[0]['emoji']
        payload["content"] = text[len(found[0]['emoji']):].strip()
    requests.post(url, json=payload, headers={"Authorization": f"Bearer {api}"})

def perform_git_ops(filename):
    # Stash any uncommitted changes so the pull never fails on a dirty tree
    stash = subprocess.run(
        ["git", "stash"], capture_output=True, encoding='utf-8'
    )
    stashed = "No local changes" not in stash.stdout

    subprocess.run(["git", "pull", "--rebase", "origin", "main"], check=True)

    # Restore stashed changes on top of the fresh pull
    if stashed:
        subprocess.run(["git", "stash", "pop"], check=True)

    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "commit", "-m", "update from cockpit"], check=True)
    subprocess.run(["git", "push", "origin", "main"], check=True)

def optimize_image(input_path, max_width=1200):
    with Image.open(input_path) as img:
        # Convert to RGB if it's a PNG/WebP with transparency to ensure JPEG compatibility
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        # Calculate aspect ratio
        w_percent = (max_width / float(img.size[0]))
        if w_percent < 1.0: # Only downscale, never upscale
            h_size = int((float(img.size[1]) * float(w_percent)))
            img = img.resize((max_width, h_size), Image.Resampling.LANCZOS)

        # Save with optimization and 85% quality (sweet spot for web)
        img.save(input_path, "JPEG", optimize=True, quality=85)

# ---- TASKS HELPERS ----

def load_tasks():
    """Read tasks.json from the Jekyll repo. Returns dict with 'tasks' list."""
    try:
        with open(TASKS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"tasks": []}

def save_tasks(data):
    """Write tasks.json back to the Jekyll repo."""
    os.makedirs(os.path.dirname(TASKS_FILE), exist_ok=True)
    with open(TASKS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def post_task_status(title):
    """Fire a status update + omg.lol post announcing a new task."""
    now = datetime.now(pytz.timezone('America/New_York'))
    fn = now.strftime("_status_updates/%Y-%m-%d-%H%M%S.markdown")
    text = f"📋 New task logged: {title} → [aaronaiken.me/tools/tasks/](https://aaronaiken.me/tools/tasks/)"
    fm = (
        f"---\ntitle: Status\ndate: {now.strftime('%Y-%m-%d %H:%M:%S %z')}\n"
        f"layout: status_update\nauthor: aaron\nsource: web\n---\n"
    )
    os.makedirs("_status_updates", exist_ok=True)
    with open(fn, "w") as f:
        f.write(fm + text + "\n")
    return fn, text


# ---- EXISTING ROUTES — untouched ----

@app.route("/publish", methods=['GET', 'POST'])
def publish_status():
    if not is_authenticated(): return redirect(url_for('login'))

    if request.method == 'POST':
        txt = request.form['status']
        image_file = request.files.get('image')  # Grab the payload

        now = datetime.now(pytz.timezone('America/New_York'))
        fn = now.strftime("_status_updates/%Y-%m-%d-%H%M%S.markdown")

        # 1. Process Image Payload (if exists)
        image_markdown = ""
        has_image = False

        if image_file and image_file.filename != '':
            has_image = True

            # Ensure your assets directory exists
            img_dir = "assets/img/status"
            os.makedirs(img_dir, exist_ok=True)

            # Secure filename and add timestamp to prevent overwrites
            img_name = secure_filename(image_file.filename)
            img_path_fs = os.path.join(img_dir, f"{now.strftime('%Y%m%d%H%M%S')}-{img_name}")

            # Save the actual file to your local Jekyll repo clone
            image_file.save(img_path_fs)

            # ADD THIS LINE: Run the optimization/resize
            optimize_image(img_path_fs)

            # Prepare the Markdown string (relative to your site root)
            image_markdown = f"\n\n![Status Image](/{img_path_fs})"

        # 2. Build Front Matter
        tags = [t for t in ["movie", "book", "music", "idea", "coffee"] if f"#{t}" in txt.lower()]
        fm = f"---\ntitle: Status\ndate: {now.strftime('%Y-%m-%d %H:%M:%S %z')}\nlayout: status_update\n"
        fm += "author: aaron\n"
        fm += "source: web\n"
        if tags: fm += f"tags: {tags}\n"

        # 3. Assemble Full Markdown Content
        full_markdown = f"{fm}---\n{txt}{image_markdown}\n"

        # 4. Save and Push
        os.makedirs("_status_updates", exist_ok=True)
        with open(fn, "w") as f:
            f.write(full_markdown)

        # This will now push both the .markdown file AND the new image in assets/
        perform_git_ops(fn)

        # 5. The OMG.lol Fork
        # Only post to OMG if there is NO image (since OMG won't host the binary)
        if not has_image:
            post_to_omg_lol(txt)

        return render_template('success.html')

    # GET request remains the same
    files = sorted(glob.glob("_status_updates/*.markdown"), reverse=True)[:3]
    history = [open(f).read().split("---")[-1].strip() for f in files]
    # Pass the whole list to the template
    comms_list = get_valid_comms()
    tasks_data = load_tasks()
    return render_template(
        'publish_form.html',
        history=history,
        git_status=get_git_status(),
        comms_list=comms_list,
        tasks=tasks_data.get('tasks', [])
    )

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST' and request.form.get('password') == PASSWORD:
        r = make_response(redirect(url_for('publish_status')))
        r.set_cookie('auth_token', 'authenticated_user', max_age=2592000, httponly=True, samesite='Lax')
        return r
    return render_template('login.html')

@app.route("/logout")
def logout():
    r = make_response(redirect(url_for('login')))
    r.set_cookie('auth_token', '', expires=0); return r


# ---- TASKS ROUTES ----

@app.route("/tasks/add", methods=['POST'])
def tasks_add():
    """Add a new task. Writes JSON, fires a status update, git pushes."""
    if not is_authenticated():
        return jsonify({"error": "unauthorized"}), 401

    title = request.form.get('title', '').strip()
    if not title:
        return jsonify({"error": "title required"}), 400

    data = load_tasks()
    task = {
        "id": str(int(time.time())),
        "title": title,
        "status": "open",
        "created": datetime.now(pytz.timezone('America/New_York')).isoformat(),
        "completed": None
    }
    data['tasks'].insert(0, task)  # newest first
    save_tasks(data)

    # Fire the status update announcing the new task
    fn, status_text = post_task_status(title)

    # Single git push — picks up both tasks.json and the new status update
    perform_git_ops(fn)

    # Mirror to omg.lol
    post_to_omg_lol(status_text)

    return jsonify({"ok": True, "task": task})


@app.route("/tasks/complete", methods=['POST'])
def tasks_complete():
    """Mark a task complete. Returns the task title for the optional log prompt."""
    if not is_authenticated():
        return jsonify({"error": "unauthorized"}), 401

    task_id = request.form.get('id', '').strip()
    if not task_id:
        return jsonify({"error": "id required"}), 400

    data = load_tasks()
    target = next((t for t in data['tasks'] if t['id'] == task_id), None)
    if not target:
        return jsonify({"error": "task not found"}), 404

    target['status'] = 'complete'
    target['completed'] = datetime.now(pytz.timezone('America/New_York')).isoformat()
    save_tasks(data)

    # Push the updated tasks.json — no status update here, that's the user's choice
    perform_git_ops(TASKS_FILE)

    return jsonify({"ok": True, "task": target})


@app.route("/tasks/delete", methods=['POST'])
def tasks_delete():
    """Hard delete a task. No status update — just housekeeping."""
    if not is_authenticated():
        return jsonify({"error": "unauthorized"}), 401

    task_id = request.form.get('id', '').strip()
    if not task_id:
        return jsonify({"error": "id required"}), 400

    data = load_tasks()
    before = len(data['tasks'])
    data['tasks'] = [t for t in data['tasks'] if t['id'] != task_id]
    if len(data['tasks']) == before:
        return jsonify({"error": "task not found"}), 404

    save_tasks(data)
    perform_git_ops(TASKS_FILE)

    return jsonify({"ok": True})


if __name__ == "__main__": app.run(debug=True)