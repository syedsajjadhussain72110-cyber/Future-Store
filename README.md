# Future Store

**Flask and MongoDB e-commerce application with content-based recommendations and a catalog-aware, rule-based shopping assistant.**

An existing academic team project for the **Data Science Foundations (DSF) e-Project at Aptech Computer Education**. This repository preserves the original services, blueprints, templates, and frontend design, with publication cleanup and reproducible setup. It is a local academic prototype.

![Original recommendation interface](docs/screenshots/recommendations.png)

## Features

- Product catalog, text search, category/price/rating filters, and sorting.
- Registration, hashed passwords, login/logout, and customer sessions.
- Shopping cart with quantity updates and removal.
- Demo checkout, order history, and customer dashboard.
- Product reviews with duplicate-review checks.
- Admin dashboard, product creation/soft deletion, and order status management.
- Content-based product recommendations.
- Catalog-aware shopping assistant and preset store-policy answers.
- Contact form and example help, returns, and legal pages.

**Checkout records demo orders; no card or wallet payments are processed.** Some shipping/address/payment controls are interface examples and are not persisted by the current backend.

## Tech stack

Python 3.10+ · Flask · MongoDB/PyMongo · Werkzeug · Jinja2 · HTML · CSS · JavaScript · python-dotenv

Frontend resources include Font Awesome, Swiper, and Google Fonts. Recommendations are deterministic catalog rules. The assistant does not use an LLM or external AI API.

## Project structure

```text
app.py                      Flask factory and development entry point
app_db.py                   Shared MongoDB client, indexes, integer IDs
config.py                   Environment settings
seed_db.py                  Demonstration catalog loader
blueprints/                 auth, store, cart, orders, dashboard, admin, pages, ai
services/                   Authentication, catalog, cart, orders, recommendations, assistant
templates/                  Feature-specific Jinja templates and shared layout
static/css/style.css        Original dark store design
static/js/script.js         Carousel, chat widget, interface interactions
static/products.json        91-item demonstration catalog
static/images/placeholder.svg
docs/screenshots/           Original project evidence
tests/                      Isolated application/service checks
init_db.py                  Historical SQLite schema utility
migrate_sqlite_to_mongo.py  Optional private-data migration utility
update_dead_links.py        Image-reference cleanup
MIGRATION_NOTES.md          Sanitized original implementation notes
.env.example                Non-secret settings template
requirements.txt            Application dependencies
requirements-dev.txt        Test dependencies
```

Local databases, credentials, private report files, student IDs, caches, and virtual environments are excluded.

## Installation

```bash
git clone https://github.com/syedsajjadhussain72110-cyber/Future-Store.git
cd Future-Store
python -m venv .venv
```

Activate the environment:

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

```bash
# macOS / Linux
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env`:

```powershell
# Windows PowerShell
Copy-Item .env.example .env
```

```bash
# macOS / Linux
cp .env.example .env
```

Generate a secret locally and paste its output into `SECRET_KEY` in your private `.env`:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Startup rejects a missing secret or the example placeholder. Never commit `.env`, credentials, or database exports.

## MongoDB setup

Install and start [MongoDB Community Server](https://www.mongodb.com/try/download/community), or configure your own authenticated instance. Default local settings:

```dotenv
MONGO_URI=mongodb://localhost:27017
MONGO_DB=future_store
FLASK_ENV=development
```

Check the server:

```bash
mongosh --eval "db.runCommand({ ping: 1 })"
```

Load the bundled catalog into a **new, empty demonstration database**:

```bash
python seed_db.py
```

Seeding refuses a database containing existing products, categories, users, carts, orders, or reviews. Select a new `MONGO_DB` to preserve existing data. No default administrator or shared password is supplied.

Register your own local account, then promote it in `mongosh`:

```javascript
use future_store
db.users.updateOne(
  { email: "your-local-account@example.com" },
  { $set: { role: "admin" } }
)
```

Alternatively, set both `SEED_ADMIN_EMAIL` and a locally chosen `SEED_ADMIN_PASSWORD` of at least 12 characters before seeding. Sign out and back in after a role change because roles are stored in sessions.

The historical SQLite migration utility is optional and not part of quick start. It clears destination collections before copying your private SQLite data. Use it only against an isolated database you intend to replace. The original `database.db` is intentionally absent.

## Running

```bash
python app.py
```

Open `http://127.0.0.1:5000` locally; this is a development URL, not a public demo. Main routes include `/`, `/product/<id>`, `/auth/register`, `/auth/login`, `/cart/`, `/cart/checkout`, `/orders/`, `/dashboard/`, `/admin/`, and `/ai/chat` (POST JSON).

`FLASK_ENV=production` disables debug mode. Public hosting also requires a production WSGI server and the hardening below.

## Recommendation system

`services/recommendation_service.py` selects other active products in the current product's category. It ranks them by **absolute price difference first, then rating**. When too few are available, globally top-rated active products fill remaining slots. The current product and duplicate recommendations are excluded.

This is deterministic content-based logic; it has no trained model, embeddings, collaborative filtering, or browsing-history personalization.

## Shopping assistant

`services/ai_service.py` matches greetings, policy intents, category synonyms, and budget phrases such as “under $100.” It queries MongoDB and returns up to four product cards. When no category matches, significant words are searched across names, descriptions, and brands. Category-based responses may be broad suggestions rather than an exact product match.

`/ai/chat` serves the frontend widget. A short session history supports display across pages; matching uses the latest message rather than multi-turn reasoning. This is a **rule-based shopping assistant**, not an autonomous LLM agent.

## Screenshots and assets

The screenshot is original evidence from the supplied academic report. Account dashboards, credentials, student identifiers, signatures, private records, and the full report are not published. It depicts the original interface, not a hosted-demo claim.

The catalog references external images, mainly Unsplash; no external photo collection is bundled. Unsplash imagery remains subject to the [Unsplash License](https://unsplash.com/license). Product names and brands belong to their owners and do not imply affiliation. Expired Amazon image references use a local placeholder. Libraries/fonts retain their respective licenses.

## Academic team attribution

The original DSF report lists:

- Syed Sajjad Hussain
- Muhammad Raza Khan
- Ali (listed with this name in the report)
- Abdul Hameed
- Hamdan Ahmad Siddiqui
- Abdul Momin
- Hassan Ahmed

Published on Syed Sajjad Hussain's portfolio account as an **academic team project**. Individual component ownership is not asserted. Student identifiers and signatures are omitted. No new software license has been assigned to the team's work.

## Validation

Publication review on **10 October 2026**: **20 automated checks passed**, Python compilation passed, and `pip check` found no broken requirements. Checks cover public page rendering, filters, registration/login, hashing, cart/checkout/order history, reviews, admin access/product management, recommendations, assistant responses, clean catalog seeding, refusal to seed existing data, and session-key validation.

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m compileall -q .
python -m pip check
```

Tests use **mongomock** and Flask's test client. They do not verify real MongoDB network/authentication behavior, browser interactions, external images, concurrency, or production deployment. A live MongoDB integration test was not run. Two existing `datetime.utcnow()` deprecation warnings remain.

Tested: Flask 3.1.3, PyMongo 4.18.3, Werkzeug 3.1.9, python-dotenv 1.2.4, pytest 9.1.1, mongomock 4.3.0.

## Limitations and future improvements

- Add CSRF protection, rate limiting, stronger validation, and safe redirect checks before public hosting.
- Add payment integration, stock reservation/decrement, and atomic checkout transactions.
- Persist and validate shipping/address/payment details.
- Replace state-changing GET routes with protected POST/DELETE operations.
- Improve category/brand matching and align all preset policies with implemented behavior.
- Add real MongoDB/browser tests, dependency locking, accessibility checks, and deployment configuration.
- Replace naive UTC timestamps with timezone-aware values.

These are future improvements, not current features or production-readiness claims.
