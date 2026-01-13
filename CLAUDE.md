# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Toolshed App is a Flask-based web application for tracking workshop tools, consumables, and materials. Uses SQLite for data persistence with an industrial-themed responsive UI for desktop and mobile access.

## Development Commands

### Running the Application

Start the server (automatically installs dependencies):
```bash
./run.sh
```

Or manually:
```bash
pip install -r requirements.txt --break-system-packages
python app.py
```

The application runs on `http://0.0.0.0:5000` by default and is accessible from other devices on the same network.

### Database Operations

The SQLite database (`tools.db`) is automatically initialized on first run.

View schema:
```bash
sqlite3 tools.db ".schema"
```

Query data:
```bash
sqlite3 tools.db "SELECT * FROM tools;"
sqlite3 tools.db "SELECT * FROM consumables WHERE quantity <= min_quantity;"
```

Backup database:
```bash
cp tools.db tools.db.backup
```

Reset database (WARNING: deletes all data):
```bash
rm tools.db && python app.py
```

## Architecture

### Application Structure

- **app.py**: Single-file Flask application containing all routes, database logic, and initialization
- **templates/**: Jinja2 HTML templates with base template inheritance pattern
- **static/css/**: Industrial-themed CSS with CSS variables for customization
- **static/uploads/**: User-uploaded tool/consumable images (created automatically)
- **tools.db**: SQLite database with three main tables

### Data Model

**Three main entities:**

1. **tools** - Power tools and hand tools
   - Core fields: name, category, brand, model, condition, location
   - Purchase tracking: purchase_date, purchase_price
   - References: bunnings_url, manual_url
   - Media: image_path

2. **consumables** - Drill bits, saw blades, sanding discs, etc.
   - Inventory: quantity, unit, min_quantity (for low-stock alerts)
   - Relationships: compatible_with (free text linking to tools)
   - Ordering: purchase_url

3. **materials** - Raw materials (planned feature, minimal implementation)
   - Stock tracking: quantity, unit, material_type

### Key Patterns

**Database access:**
- Uses `get_db()` helper for connection management
- `sqlite3.Row` factory for dict-like row access
- Direct SQL queries (no ORM) with parameterized queries for safety
- Connection opened/closed within each route handler

**File uploads:**
- Werkzeug's `secure_filename()` for sanitization
- Timestamped filenames to prevent collisions: `YYYYMMDD_HHMMSS_originalname.ext`
- File extension validation via `allowed_file()` helper
- 16MB max upload size
- Allowed formats: png, jpg, jpeg, gif, webp

**Template inheritance:**
- `base.html` provides layout structure and navigation
- Individual templates extend base and override content blocks
- Flask's `render_template()` for rendering with context

### Route Structure

- `/` - Dashboard with counts, low-stock alerts, recent tools
- `/tools` - Tool listing with search and category filtering
- `/tool/<id>` - Tool detail with compatible consumables
- `/tool/add`, `/tool/<id>/edit`, `/tool/<id>/delete` - Tool CRUD
- `/consumables` - Consumable listing
- `/consumable/add` - Add consumable (edit/delete not yet implemented)
- `/materials` - Materials listing (minimal implementation)
- `/search/bunnings` - Placeholder for future Bunnings integration

## Development Notes

### Mobile Access Pattern

The application is designed for "shop while at the hardware store" use case:
- Server binds to `0.0.0.0` to accept connections from local network
- Responsive CSS for phone screens
- Search and filter features for quick lookup while shopping

### Future Integration Points

Several features are planned but not implemented:
- Bunnings/Mitre10 price scraping (route exists: `/search/bunnings`)
- Edit/delete for consumables and materials
- QR code label generation
- Maintenance reminder system
- Battery compatibility matrix
- Project planning tools

### Image Handling

Images are stored in `static/uploads/` and referenced in the database as relative paths (`uploads/filename.ext`). Templates use Flask's `url_for('static', filename=...)` for proper URL generation.

### Customization

Categories are hardcoded in template dropdowns:
- Tool categories: Power Tools, Hand Tools, Measuring Tools, Outdoor, Other
- Consumable categories: Drill Bits, Saw Blades, Sanding, Fasteners, Adhesives, Other

To add categories, edit the `<select>` elements in:
- `templates/add_tool.html`
- `templates/edit_tool.html`
- `templates/add_consumable.html`

CSS theming uses CSS variables in `static/css/style.css` (`:root` selector).

## Common Development Tasks

When adding features, follow these patterns:

**Adding a new field to a table:**
1. Add column to table schema in `init_db()` (note: existing DBs won't auto-migrate)
2. Update relevant INSERT/UPDATE queries in route handlers
3. Add form field to add/edit templates
4. Update display templates to show the new field

**Adding a new page:**
1. Create route handler in `app.py`
2. Create template in `templates/`
3. Add navigation link in `templates/base.html` if needed

**Low-stock alerts:**
Consumables with `quantity <= min_quantity` are shown on the dashboard. The query is in the `index()` route.
