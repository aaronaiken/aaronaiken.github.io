from flask import Flask, request
import datetime
import os
import subprocess
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

@app.route("/sms", methods=['POST'])
def sms_reply():
    sms_text = request.form['Body']
    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d %H:%M:%S %z")
    filename = now.strftime("_status_updates/%Y-%m-%d-%H%M%S-status.markdown")

    front_matter = f"""---
title: Status Update
date: {date_str}
layout: status_update
author: aaron
---
{sms_text}
"""

    os.makedirs("_status_updates", exist_ok=True)
    with open(filename, "w") as f:
        f.write(front_matter)

    subprocess.run(["git", "add", filename], check=True)
    subprocess.run(["git", "commit", "-m", "Add status update via SMS"], check=True)
    subprocess.run(["git", "push", "origin", "main"], check=True)

    resp = MessagingResponse()
    resp.message("Status update published!")
    return str(resp)

if __name__ == "__main__":
    app.run(debug=True)