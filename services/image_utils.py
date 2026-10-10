"""
Future Store — Product Image URL Normalization
Single source of truth for turning a product document's raw `image` field
into something safe to drop straight into an <img src="..."> or a JSON
API response.

WHY THIS EXISTS
----------------
The `products` collection has data from two different sources:
  1. The original Unsplash-seeded catalog (full https:// URLs, still live).
  2. A later bulk import of Amazon product data. Some of those rows kept
     only a bare image filename (e.g. "71aX+kAJizL._AC_SL1500_.jpg") with
     no host, and others kept a full "https://m.media-amazon.com/..." or
     "https://images-na.ssl-images-amazon.com/..." URL — but it turns out
     EVERY Amazon-sourced image link, bare or full, is now dead/expired
     (confirmed by hand: the full URLs 404 directly in the browser too).
     There's no live Amazon CDN to reconstruct or fall back to, so any
     Amazon-origin value — in whatever shape it's stored — is treated as
     unrecoverable and mapped straight to the local placeholder image.

normalize_image() is the one place that resolves any of those shapes
into a real, fetchable URL (or the placeholder). It's a plain function
(no Flask app/request context required) so it can be:
  - registered as the `product_image` Jinja global in app.py,
  - reused by services/ai_service.py when building the AI chat widget's
    JSON product cards,
  - reused by services/product_service.py when admin-created products
    are inserted,
  - reused by update_dead_links.py, the one-off data migration script
    that cleans the same dead Amazon links up in MongoDB itself.
"""

# Substrings that identify a known-dead Amazon image host. Checked
# case-insensitively against the whole value, so it catches both
# "m.media-amazon.com" and "images-na.ssl-images-amazon.com" links.
DEAD_IMAGE_HOST_MARKERS = ("amazon.com", "images-na")

DEFAULT_PLACEHOLDER = "/static/images/placeholder.svg"


def normalize_image(image_value, placeholder: str = DEFAULT_PLACEHOLDER) -> str:
    """
    Return a safe, fetchable <img src> value for a stored product image.

    - None / "" / missing                  -> placeholder
    - contains a known-dead Amazon host     -> placeholder (confirmed 404,
      marker ("amazon.com" / "images-na")      don't even attempt the request)
    - already "http://..." / "https://..." -> returned unchanged
    - already "/static/..."                -> returned unchanged
    - "static/..." (no leading slash)      -> leading slash added
    - bare filename, e.g.
      "71aX+kAJizL._AC_SL1500_.jpg"        -> placeholder. (These were
                                               previously reconstructed
                                               into a full Amazon CDN URL,
                                               but that host is confirmed
                                               dead, so there's nothing
                                               live to reconstruct to.)
    - anything else unrecognized           -> placeholder, rather than risk
                                               rendering another broken
                                               relative-path 404
    """
    if not image_value:
        return placeholder

    value = str(image_value).strip()
    if not value:
        return placeholder

    lowered = value.lower()
    if any(marker in lowered for marker in DEAD_IMAGE_HOST_MARKERS):
        return placeholder

    if value.startswith(("http://", "https://")):
        return value

    if value.startswith("/static/"):
        return value

    if value.startswith("static/"):
        return f"/{value}"

    # Bare filename, no scheme, no slash — these only ever originated
    # from the now-dead Amazon import, so there's no live host to
    # reconstruct. Fall back to the placeholder.
    return placeholder
