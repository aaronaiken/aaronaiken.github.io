from flask import Flask, request, render_template, make_response, redirect, url_for
import datetime, os, subprocess, pytz, requests, emoji, glob

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY')
PASSWORD = os.environ.get('FLASK_PASSWORD')

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
        return "offline"

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
    subprocess.run(["git", "pull", "--rebase", "origin", "main"], check=True)
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "commit", "-m", "update from cockpit"], check=True)
    subprocess.run(["git", "push", "origin", "main"], check=True)

@app.route("/publish", methods=['GET', 'POST'])
def publish_status():
    if not is_authenticated(): return redirect(url_for('login'))
    if request.method == 'POST':
        txt = request.form['status']
        now = datetime.datetime.now(pytz.timezone('America/New_York'))
        fn = now.strftime("_status_updates/%Y-%m-%d-%H%M%S.markdown")
        tags = [t for t in ["movie", "book", "music", "idea", "coffee"] if f"#{t}" in txt.lower()]
        fm = f"---\ntitle: Status\ndate: {now.strftime('%Y-%m-%d %H:%M:%S %z')}\nlayout: status_update\n"
        if tags: fm += f"tags: {tags}\n"
        fm += f"---\n{txt}\n"
        os.makedirs("_status_updates", exist_ok=True)
        with open(fn, "w") as f: f.write(fm)
        perform_git_ops(fn)
        post_to_omg_lol(txt)
        return render_template('success.html')

    files = sorted(glob.glob("_status_updates/*.markdown"), reverse=True)[:3]
    history = [open(f).read().split("---")[-1].strip() for f in files]
    return render_template('publish_form.html', history=history, git_status=get_git_status())

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

if __name__ == "__main__": app.run(debug=True)