"""Turn a browser data-URL (a pasted / attached screenshot) into an Anthropic
image content block, with validation. Pure — imports nothing from the app.

Used by the Command Deck's Huyang chat and the ticket-draft flow so an operator
can hand Huyang a screenshot to read instead of pasting text.
"""
import base64
import binascii

# Claude accepts png / jpeg / gif / webp. The Messages API caps a single image at
# ~5MB; we hold decoded bytes a little under that to leave request headroom.
_ALLOWED = {'image/png', 'image/jpeg', 'image/gif', 'image/webp'}
_MAX_BYTES = 4 * 1024 * 1024  # 4 MB decoded


def image_block_from_data_url(data_url):
    """Return (block, error). `block` is an Anthropic image content-block dict, or
    None on error with a short error code. Accepts 'data:image/png;base64,....'."""
    if not data_url or not isinstance(data_url, str):
        return None, 'no_image'
    if not data_url.startswith('data:') or ',' not in data_url:
        return None, 'bad_image'

    header, b64 = data_url.split(',', 1)
    meta = header[len('data:'):]            # e.g. 'image/png;base64'
    if ';base64' not in meta:
        return None, 'bad_image'
    media_type = meta.split(';', 1)[0].strip().lower()
    if media_type not in _ALLOWED:
        return None, 'unsupported_type'

    b64 = b64.strip()
    try:
        raw = base64.b64decode(b64, validate=True)
    except (binascii.Error, ValueError):
        return None, 'bad_image'
    if not raw:
        return None, 'empty_image'
    if len(raw) > _MAX_BYTES:
        return None, 'too_large'

    return {
        'type': 'image',
        'source': {'type': 'base64', 'media_type': media_type, 'data': b64},
    }, None
