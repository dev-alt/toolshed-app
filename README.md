# Toolshed App 🔧

A distinctive industrial-styled web application for managing your workshop tools, consumables, and materials. Built with Flask and SQLite.

## Features

### Current Features
- **Tools Inventory**: Track all your power tools and hand tools with photos, brands, models, and locations
- **Consumables Tracking**: Monitor drill bits, saw blades, sanding discs, and other consumables with low-stock alerts
- **Search & Filter**: Quickly find tools by name, brand, category
- **Photo Upload**: Visual inventory with image support
- **Purchase Links**: Direct links to Bunnings, manuals, and datasheets
- **Mobile Friendly**: Responsive design for checking inventory while shopping
- **Industrial Aesthetic**: Distinctive dark theme with workshop-inspired design

### Coming Soon
- Materials inventory (wood, aluminum, resin, filament)
- NZ retailer integration (Bunnings, Mitre10 price scraping)
- Project planning and "what do I need" checker
- QR code labels for quick lookup
- Maintenance reminders
- Battery compatibility matrix
- Usage statistics

## Setup

### Requirements
- Python 3.8+
- pip

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt --break-system-packages
```

2. Run the application:
```bash
python app.py
```

3. Open your browser and navigate to:
```
http://localhost:5000
```

For network access (check inventory from your phone while shopping):
```
http://YOUR_COMPUTER_IP:5000
```

## Usage

### Adding Your First Tool

1. Click "Add Tool" button on dashboard
2. Fill in the details:
   - **Name**: Tool name (e.g., "Orbital Sander")
   - **Brand/Model**: Ryobi, Ozito, etc.
   - **Category**: Power Tool, Hand Tool, etc.
   - **Purchase Info**: Date and price for tracking value
   - **Location**: Where it's stored in your workshop
   - **Links**: Bunnings product page, manual PDF
3. Upload a photo
4. Add notes about specifications or maintenance

### Tracking Consumables

1. Go to "Consumables" section
2. Add items like:
   - "125mm Sanding Discs - 80 Grit"
   - "HSS Drill Bit Set"
   - "Jigsaw Blades - Wood"
3. Set minimum stock levels for alerts
4. Link to purchase URLs for easy reordering

### Finding Accessories

On any tool detail page:
- Click "Find Accessories" to search Bunnings for compatible items
- Or add your own purchase links

## Database

The application uses SQLite (`tools.db`) which will be created automatically on first run.

**Database location**: Same directory as `app.py`

### Backup
To backup your data:
```bash
cp tools.db tools.db.backup
```

## File Structure

```
toolshed-app/
├── app.py                  # Flask application
├── requirements.txt        # Python dependencies
├── tools.db               # SQLite database (created on first run)
├── static/
│   ├── css/
│   │   └── style.css      # Industrial-themed styles
│   └── uploads/           # Tool photos
└── templates/             # HTML templates
    ├── base.html
    ├── index.html
    ├── tools.html
    ├── tool_detail.html
    ├── add_tool.html
    ├── edit_tool.html
    ├── consumables.html
    ├── add_consumable.html
    └── materials.html
```

## Mobile Access

To access from your phone while shopping at Bunnings:

1. Find your computer's IP address:
   - **Linux/Mac**: `hostname -I` or `ip addr show`
   - **Windows**: `ipconfig`

2. Make sure your phone and computer are on the same WiFi network

3. Open browser on phone: `http://YOUR_COMPUTER_IP:5000`

4. Bookmark it for quick access!

## Customization

### Adding More Categories

Edit the category dropdowns in:
- `templates/add_tool.html`
- `templates/edit_tool.html`
- `templates/add_consumable.html`

### Changing Colors

Edit CSS variables in `static/css/style.css`:
```css
:root {
    --accent-orange: #ff6b35;  /* Your preferred accent color */
    --bg-primary: #0a0e12;     /* Background color */
    /* ... more variables */
}
```

## Future Enhancements

### Planned Features
- **Bunnings Scraper**: Auto-find accessories and track prices
- **Project Planner**: "I want to build X, what do I need?"
- **Material Calculator**: Track lumber, extrusions, resin usage
- **QR Code Labels**: Print labels, scan to view tool info
- **Maintenance Log**: Track when you last serviced tools
- **Cost Tracking**: Project costs including consumables
- **Shopping List Generator**: Auto-generate list based on low stock

### Technical Improvements
- Add user authentication for multi-user access
- Export/import data as JSON or CSV
- API for integration with other tools
- Better mobile app experience (PWA)

## Tips

- Take consistent photos for clean inventory look
- Use descriptive locations ("Workshop Drawer 3, Left Side")
- Set realistic minimum stock levels for consumables
- Add purchase links when you buy something new
- Keep notes about specifications you frequently need

## Troubleshooting

**Images not uploading?**
- Check file size (max 16MB)
- Ensure `static/uploads/` directory exists and is writable

**Can't access from phone?**
- Check firewall settings
- Ensure both devices on same network
- Try using computer's IP instead of hostname

**Database errors?**
- Delete `tools.db` to start fresh (you'll lose data)
- Check write permissions in application directory

## License

Free to use and modify for personal use.

## Feedback

Built for makers, by makers. Enjoy your organized workshop! 🛠️
