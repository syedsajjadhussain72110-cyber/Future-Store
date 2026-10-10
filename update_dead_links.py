"""
Future Store — Replace dead Amazon image links with the placeholder image.

WHAT THIS FIXES
----------------
The `products` collection has a batch of documents whose `image` field
points at Amazon (either a full "https://m.media-amazon.com/..." /
"https://images-na.ssl-images-amazon.com/..." URL, or a bare filename
left over from a broken import, e.g. "71aX+kAJizL._AC_SL1500_.jpg").
Those Amazon links are confirmed dead/expired — Amazon itself returns
"Not Found" for them — so there's nothing to repair them *to*. This
script replaces every one of them with the local placeholder image path
(/static/images/placeholder.svg) directly in MongoDB.

Note: app.py's `product_image` Jinja helper (services/image_utils.
normalize_image) already does this same substitution at render time, so
your site is not broken even without running this script — every page
already falls back to the placeholder for these products. Run this
script if you'd rather have that reflected in the database itself
(useful for things like a JSON export, or another service, that reads
`image` straight out of MongoDB without going through normalize_image()).

MATCHING RULES
---------------
A product's `image` value is treated as a dead Amazon link, and replaced
with the placeholder, if it meets ANY of:
  1. Contains "amazon.com"   (case-insensitive)   — e.g. m.media-amazon.com
  2. Contains "images-na"    (case-insensitive)   — e.g. images-na.ssl-images-amazon.com
  3. Is a bare filename (no http/https scheme, no leading "/", no "/" at
     all) — these only ever came from the same broken Amazon import and
     have no live host to point at either, so they're dead too even
     though the string itself doesn't literally say "amazon.com".

This script is read-before-write and idempotent: documents that are
already the placeholder (or any other non-Amazon value) are left alone,
so re-running it after everything's fixed is a safe no-op.

Usage:
    python update_dead_links.py             # uses MONGO_URI / MONGO_DB from config.py
    python update_dead_links.py --dry-run   # show what would change, write nothing
"""
import argparse

from pymongo import MongoClient

from config import Config
from services.image_utils import DEAD_IMAGE_HOST_MARKERS, DEFAULT_PLACEHOLDER


def is_dead_amazon_link(value) -> bool:
    """True for full Amazon URLs (dead) and bare leftover filenames (also dead)."""
    if not value:
        return False
    value = str(value).strip()
    if not value:
        return False

    lowered = value.lower()
    if any(marker in lowered for marker in DEAD_IMAGE_HOST_MARKERS):
        return True

    # Bare filename: no scheme, no leading slash, no "/" anywhere.
    if not value.startswith(("http://", "https://", "/")) and "/" not in value:
        return True

    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print what would be changed without writing to MongoDB.",
    )
    args = parser.parse_args()

    client = MongoClient(Config.MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[Config.MONGO_DB]

    all_products = list(db.products.find({}))
    to_fix = [p for p in all_products if is_dead_amazon_link(p.get("image"))]

    if not to_fix:
        print(f"Checked {len(all_products)} products — no dead Amazon links found. Nothing to do.")
        return

    print(f"Checked {len(all_products)} products — {len(to_fix)} have a dead Amazon image link:\n")

    for p in to_fix:
        old_value = p.get("image")
        name = p.get("name", "(unnamed)")
        print(f"  #{p['_id']:<5} {name:<45} {old_value!r} -> {DEFAULT_PLACEHOLDER!r}")

        if not args.dry_run:
            db.products.update_one({"_id": p["_id"]}, {"$set": {"image": DEFAULT_PLACEHOLDER}})

    if args.dry_run:
        print(f"\nDry run only — no changes written. Re-run without --dry-run to apply.")
    else:
        print(f"\nUpdated {len(to_fix)} product(s) in MongoDB — image now set to the placeholder.")


if __name__ == "__main__":
    main()
