"""Bunny.net storage helpers — image optimization + uploads to status/projects/after-dark zones."""
import os
import logging
import requests as req_lib
from PIL import Image


logger = logging.getLogger(__name__)


# Storage zone constants — read from env at import time, mirror what app.py does.
BUNNY_STORAGE_ZONE = os.environ.get('BUNNY_STORAGE_ZONE')
BUNNY_API_KEY      = os.environ.get('BUNNY_API_KEY')
BUNNY_CDN_URL      = os.environ.get('BUNNY_CDN_URL', '').rstrip('/')

BUNNY_STATUS_STORAGE_ZONE = os.environ.get('BUNNY_STATUS_STORAGE_ZONE')
BUNNY_STATUS_API_KEY      = os.environ.get('BUNNY_STATUS_API_KEY')
BUNNY_STATUS_CDN_URL      = os.environ.get('BUNNY_STATUS_CDN_URL', '').rstrip('/')

BUNNY_AD_STORAGE_ZONE = os.environ.get('BUNNY_AFTER_DARK_STORAGE_ZONE', '')
BUNNY_AD_API_KEY      = os.environ.get('BUNNY_AFTER_DARK_API_KEY', '')
BUNNY_AD_CDN_URL      = os.environ.get('BUNNY_AFTER_DARK_CDN_URL', '').rstrip('/')

ALLOWED_FILE_EXTENSIONS = {
	'jpg', 'jpeg', 'png', 'gif', 'webp',
	'pdf', 'txt', 'md',
	'doc', 'docx', 'xls', 'xlsx',
	'zip', 'mp4', 'mov'
}


def list_bunny_ad_folder(subfolder):
	"""
	List files in a Bunny After Dark storage zone subfolder.
	subfolder: 'videos', 'music', or 'ani'
	Returns list of dicts: {name, url, ext}
	Returns [] on any error.
	"""
	if not BUNNY_AD_STORAGE_ZONE or not BUNNY_AD_API_KEY or not BUNNY_AD_CDN_URL:
		return []
	list_url = f"https://ny.storage.bunnycdn.com/{BUNNY_AD_STORAGE_ZONE}/{subfolder}/"
	try:
		resp = req_lib.get(
			list_url,
			headers={'AccessKey': BUNNY_AD_API_KEY, 'Accept': 'application/json'},
			timeout=10
		)
		if resp.status_code != 200:
			return []
		items = resp.json()
		result = []
		for item in items:
			if item.get('IsDirectory'):
				continue
			name = item.get('ObjectName', '')
			ext = name.rsplit('.', 1)[-1].lower() if '.' in name else ''
			result.append({
				'name': name,
				'url': f"{BUNNY_AD_CDN_URL}/{subfolder}/{name}",
				'ext': ext,
			})
		return result
	except Exception as e:
		logger.error(f"Bunny AD list error ({subfolder}): {e}")
		return []


def optimize_image(input_path, max_width=1200):
	with Image.open(input_path) as img:
		if img.mode in ("RGBA", "P"):
			img = img.convert("RGB")
		w_percent = (max_width / float(img.size[0]))
		if w_percent < 1.0:
			h_size = int((float(img.size[1]) * float(w_percent)))
			img = img.resize((max_width, h_size), Image.Resampling.LANCZOS)
		img.save(input_path, "JPEG", optimize=True, quality=85)


def upload_status_image_to_bunny(image_bytes, filename):
	"""Upload a processed status image to Bunny storage zone. Returns CDN URL."""
	upload_url = f"https://ny.storage.bunnycdn.com/{BUNNY_STATUS_STORAGE_ZONE}/status/{filename}"
	response = req_lib.put(
		upload_url,
		data=image_bytes,
		headers={
			'AccessKey': BUNNY_STATUS_API_KEY,
			'Content-Type': 'image/jpeg',
		},
		timeout=60
	)
	if response.status_code != 201:
		raise Exception(f"Bunny status upload failed: {response.status_code} {response.text}")
	return f"{BUNNY_STATUS_CDN_URL}/status/{filename}"


def _allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_FILE_EXTENSIONS


def _upload_to_bunny(file_obj, filename, content_type):
	"""Upload a file to Bunny.net storage. Returns CDN URL or raises."""
	upload_url = f"https://ny.storage.bunnycdn.com/{BUNNY_STORAGE_ZONE}/{filename}"
	response = req_lib.put(
		upload_url,
		data=file_obj,
		headers={
			'AccessKey': BUNNY_API_KEY,
			'Content-Type': content_type,
		},
		timeout=60
	)
	if response.status_code != 201:
		raise Exception(f"Bunny upload failed: {response.status_code} {response.text}")
	return f"{BUNNY_CDN_URL}/{filename}"
