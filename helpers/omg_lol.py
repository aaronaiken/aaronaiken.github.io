"""omg.lol status mirror — POSTs status text (with leading-emoji extraction) to the omg.lol API."""
import os
import emoji
import requests


def post_to_omg_lol(text):
	api, addr = os.environ.get('OMG_LOL_API_KEY'), os.environ.get('OMG_LOL_ADDRESS')
	if not api or not addr:
		return
	url = f"https://api.omg.lol/address/{addr}/statuses"
	text = text.strip()
	found = emoji.emoji_list(text)
	payload = {"content": text}
	if found and found[0]['match_start'] == 0:
		payload["emoji"] = found[0]['emoji']
		payload["content"] = text[len(found[0]['emoji']):].strip()
	requests.post(url, json=payload, headers={"Authorization": f"Bearer {api}"})
