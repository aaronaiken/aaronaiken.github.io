from flask import Flask, request, render_template
import datetime
import os
import subprocess

app = Flask(__name__)

@app.route("/sms", methods=['POST'])
def sms_reply():
    sms_text = request.form['Body']
    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d %H:%M:%S %z")
    filename = now.strftime("_status_updates/%Y-%m-%d-%H%M%S-status-sms.markdown")

    front_matter = f"""---
title: Status Update
date: {date_str}
layout: status_update
author: aaron
source: sms ($0.0079)
---
{sms_text}
"""

    os.makedirs("_status_updates", exist_ok=True)
    with open(filename, "w") as f:
        f.write(front_matter)

    subprocess.run(["git", "add", filename], check=True)
    subprocess.run(["git", "commit", "-m", "Add status update via SMS"], check=True)
    subprocess.run(["git", "push", "origin", "main"], check=True)

    return "OK", 200

@app.route("/publish", methods=['GET', 'POST'])
def publish_status():
    if request.method == 'POST':
        status_text = request.form['status']
        now = datetime.datetime.now()
        date_str = now.strftime("%Y-%m-%d %H:%M:%S %z")
        filename = now.strftime("_status_updates/%Y-%m-%d-%H%M%S-status-web.markdown")

        front_matter = f"""---
title: Status Update
date: {date_str}
layout: status_update
author: aaron
source: web
---
{status_text}
"""

        os.makedirs("_status_updates", exist_ok=True)
        with open(filename, "w") as f:
            f.write(front_matter)

        subprocess.run(["git", "add", filename], check=True)
        subprocess.run(["git", "commit", "-m", "Add status update via web form"], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)

        return "Status update published via web!", 200
    else:
        return render_template('publish_form.html')

if __name__ == "__main__":
    app.run(debug=True)