from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
import sqlite3
import os
from datetime import datetime
from werkzeug.utils import secure_filename
import requests
from bs4 import BeautifulSoup
import re
import json
from urllib.parse import urlencode
import qrcode
from io import BytesIO
import base64

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# QR code configuration
app.config['QR_FOLDER'] = 'static/qr_codes'
os.makedirs(app.config['QR_FOLDER'], exist_ok=True)

def get_db():
    """Get database connection"""
    conn = sqlite3.connect('tools.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database with tables"""
    conn = get_db()
    c = conn.cursor()
    
    # Tools table
    c.execute('''
        CREATE TABLE IF NOT EXISTS tools (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            brand TEXT,
            model TEXT,
            purchase_date TEXT,
            purchase_price REAL,
            condition TEXT,
            location TEXT,
            notes TEXT,
            image_path TEXT,
            bunnings_url TEXT,
            manual_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Consumables table
    c.execute('''
        CREATE TABLE IF NOT EXISTS consumables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            quantity INTEGER DEFAULT 0,
            unit TEXT,
            min_quantity INTEGER,
            location TEXT,
            compatible_with TEXT,
            notes TEXT,
            image_path TEXT,
            purchase_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Materials table
    c.execute('''
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            material_type TEXT,
            quantity REAL DEFAULT 0,
            unit TEXT,
            min_quantity REAL,
            dimensions_length REAL,
            dimensions_width REAL,
            dimensions_thickness REAL,
            dimension_unit TEXT,
            grade TEXT,
            finish TEXT,
            color TEXT,
            purchase_price REAL,
            cost_per_unit REAL,
            supplier TEXT,
            purchase_date TEXT,
            purchase_url TEXT,
            location TEXT,
            notes TEXT,
            image_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Fasteners table (screws, bolts, nuts, washers, etc.)
    c.execute('''
        CREATE TABLE IF NOT EXISTS fasteners (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            size TEXT NOT NULL,
            length TEXT,
            material TEXT,
            head_type TEXT,
            thread_type TEXT,
            quantity INTEGER DEFAULT 0,
            min_quantity INTEGER,
            location TEXT,
            notes TEXT,
            image_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Favorites table
    c.execute('''
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_type TEXT NOT NULL,
            item_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(item_type, item_id)
        )
    ''')

    conn.commit()
    conn.close()

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def generate_qr_code(item_type, item_id):
    """
    Generate QR code for an item.
    Returns base64 encoded image data.
    """
    # Create URL that will be encoded in QR code
    qr_data = f"{request.host_url}scan/{item_type}/{item_id}"

    # Create QR code instance
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)

    # Create image
    img = qr.make_image(fill_color="black", back_color="white")

    # Save to BytesIO buffer
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    # Convert to base64 for embedding in HTML
    img_base64 = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/png;base64,{img_base64}"

def scrape_bunnings_search(query):
    """
    Search Bunnings NZ for products.
    Note: Bunnings uses client-side rendering, so we return a search URL
    and mock data for demonstration. For production, consider:
    1. Using Playwright/Selenium for JS rendering
    2. Using official Bunnings API if available
    3. Manual entry with URL parser
    """
    try:
        search_url = f"https://www.bunnings.co.nz/search/products?q={requests.utils.quote(query)}"

        # For now, return the search URL and suggest opening it
        # In a production app, you'd either:
        # - Use Playwright to render JS
        # - Use an official API
        # - Parse a pasted product URL

        # Try basic scraping as fallback but expect it might not work
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-NZ,en;q=0.9',
        }

        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()

        # Try to extract from script tags with product data
        soup = BeautifulSoup(response.content, 'html.parser')
        products = []

        # Try to find JSON data in script tags
        script_tags = soup.find_all('script', type='application/ld+json')
        for script in script_tags:
            try:
                data = json.loads(script.string)
                if data.get('@type') == 'Product' or data.get('@type') == 'ItemList':
                    # Handle product list schema
                    if 'itemListElement' in data:
                        for item in data['itemListElement'][:10]:
                            product_data = item.get('item', {})
                            products.append({
                                'name': product_data.get('name', ''),
                                'brand': product_data.get('brand', {}).get('name'),
                                'price': product_data.get('offers', {}).get('price'),
                                'url': product_data.get('url', search_url),
                                'image_url': product_data.get('image'),
                                'source': 'Bunnings NZ'
                            })
            except:
                continue

        if products:
            return {'success': True, 'products': products, 'search_url': search_url}

        # If no products found, return helpful message with search URL
        return {
            'success': True,
            'products': [],
            'search_url': search_url,
            'message': f'Unable to scrape Bunnings automatically. <a href="{search_url}" target="_blank" style="color: var(--primary); text-decoration: underline;">Click here to open Bunnings search</a> and manually enter product details.'
        }

    except requests.RequestException as e:
        search_url = f"https://www.bunnings.co.nz/search/products?q={requests.utils.quote(query)}"
        return {
            'success': True,
            'products': [],
            'search_url': search_url,
            'message': f'Could not fetch from Bunnings. <a href="{search_url}" target="_blank" style="color: var(--primary); text-decoration: underline;">Click here to search manually</a>.'
        }
    except Exception as e:
        search_url = f"https://www.bunnings.co.nz/search/products?q={requests.utils.quote(query)}"
        return {
            'success': True,
            'products': [],
            'search_url': search_url,
            'message': f'Error: {str(e)}. <a href="{search_url}" target="_blank" style="color: var(--primary); text-decoration: underline;">Open Bunnings search manually</a>.'
        }

@app.route('/')
def index():
    """Main dashboard"""
    conn = get_db()

    # Get counts
    tool_count = conn.execute('SELECT COUNT(*) as count FROM tools').fetchone()['count']
    consumable_count = conn.execute('SELECT COUNT(*) as count FROM consumables').fetchone()['count']
    fastener_count = conn.execute('SELECT COUNT(*) as count FROM fasteners').fetchone()['count']
    material_count = conn.execute('SELECT COUNT(*) as count FROM materials').fetchone()['count']

    # Get low stock consumables
    low_stock_consumables = conn.execute('''
        SELECT * FROM consumables
        WHERE quantity <= min_quantity
        ORDER BY quantity ASC
        LIMIT 5
    ''').fetchall()

    # Get low stock fasteners
    low_stock_fasteners = conn.execute('''
        SELECT * FROM fasteners
        WHERE min_quantity IS NOT NULL AND quantity <= min_quantity
        ORDER BY quantity ASC
        LIMIT 5
    ''').fetchall()

    # Get recent tools
    recent_tools = conn.execute('''
        SELECT * FROM tools
        ORDER BY created_at DESC
        LIMIT 6
    ''').fetchall()

    # Get favorite count
    favorite_count = conn.execute('SELECT COUNT(*) as count FROM favorites').fetchone()['count']

    conn.close()

    return render_template('index.html',
                         tool_count=tool_count,
                         consumable_count=consumable_count,
                         fastener_count=fastener_count,
                         material_count=material_count,
                         favorite_count=favorite_count,
                         low_stock_consumables=low_stock_consumables,
                         low_stock_fasteners=low_stock_fasteners,
                         recent_tools=recent_tools)

@app.route('/tools')
def tools():
    """List all tools"""
    conn = get_db()
    category = request.args.get('category', '')
    search = request.args.get('search', '')
    
    query = 'SELECT * FROM tools WHERE 1=1'
    params = []
    
    if category:
        query += ' AND category = ?'
        params.append(category)
    
    if search:
        query += ' AND (name LIKE ? OR brand LIKE ? OR model LIKE ?)'
        search_term = f'%{search}%'
        params.extend([search_term, search_term, search_term])
    
    query += ' ORDER BY name'
    
    tools = conn.execute(query, params).fetchall()
    categories = conn.execute('SELECT DISTINCT category FROM tools ORDER BY category').fetchall()
    
    conn.close()
    
    return render_template('tools.html', tools=tools, categories=categories, 
                         current_category=category, search=search)

@app.route('/tool/<int:tool_id>')
def tool_detail(tool_id):
    """View single tool details"""
    conn = get_db()
    tool = conn.execute('SELECT * FROM tools WHERE id = ?', (tool_id,)).fetchone()

    # Get compatible consumables
    compatible = []
    if tool:
        compatible = conn.execute('''
            SELECT * FROM consumables
            WHERE compatible_with LIKE ?
        ''', (f'%{tool["name"]}%',)).fetchall()

    conn.close()

    if not tool:
        return "Tool not found", 404

    # Generate QR code
    qr_code = generate_qr_code('tool', tool_id)

    return render_template('tool_detail.html', tool=tool, compatible=compatible, qr_code=qr_code)

@app.route('/tool/add', methods=['GET', 'POST'])
def add_tool():
    """Add new tool"""
    if request.method == 'POST':
        conn = get_db()
        c = conn.cursor()
        
        # Handle file upload
        image_path = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_path = f"uploads/{filename}"
        
        c.execute('''
            INSERT INTO tools (name, category, brand, model, purchase_date, 
                             purchase_price, condition, location, notes, image_path,
                             bunnings_url, manual_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            request.form.get('name'),
            request.form.get('category'),
            request.form.get('brand'),
            request.form.get('model'),
            request.form.get('purchase_date'),
            request.form.get('purchase_price'),
            request.form.get('condition', 'Good'),
            request.form.get('location'),
            request.form.get('notes'),
            image_path,
            request.form.get('bunnings_url'),
            request.form.get('manual_url')
        ))
        
        conn.commit()
        conn.close()
        
        return redirect(url_for('tools'))
    
    return render_template('add_tool.html')

@app.route('/tool/<int:tool_id>/edit', methods=['GET', 'POST'])
def edit_tool(tool_id):
    """Edit existing tool"""
    conn = get_db()
    
    if request.method == 'POST':
        c = conn.cursor()
        
        # Get current tool for image handling
        tool = conn.execute('SELECT * FROM tools WHERE id = ?', (tool_id,)).fetchone()
        image_path = tool['image_path']
        
        # Handle file upload
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_path = f"uploads/{filename}"
        
        c.execute('''
            UPDATE tools 
            SET name=?, category=?, brand=?, model=?, purchase_date=?, 
                purchase_price=?, condition=?, location=?, notes=?, image_path=?,
                bunnings_url=?, manual_url=?
            WHERE id=?
        ''', (
            request.form.get('name'),
            request.form.get('category'),
            request.form.get('brand'),
            request.form.get('model'),
            request.form.get('purchase_date'),
            request.form.get('purchase_price'),
            request.form.get('condition'),
            request.form.get('location'),
            request.form.get('notes'),
            image_path,
            request.form.get('bunnings_url'),
            request.form.get('manual_url'),
            tool_id
        ))
        
        conn.commit()
        conn.close()
        
        return redirect(url_for('tool_detail', tool_id=tool_id))
    
    tool = conn.execute('SELECT * FROM tools WHERE id = ?', (tool_id,)).fetchone()
    conn.close()
    
    if not tool:
        return "Tool not found", 404
    
    return render_template('edit_tool.html', tool=tool)

@app.route('/tool/<int:tool_id>/delete', methods=['POST'])
def delete_tool(tool_id):
    """Delete a tool"""
    conn = get_db()
    conn.execute('DELETE FROM tools WHERE id = ?', (tool_id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for('tools'))

@app.route('/consumables')
def consumables():
    """List all consumables"""
    conn = get_db()
    consumables = conn.execute('SELECT * FROM consumables ORDER BY name').fetchall()
    conn.close()
    
    return render_template('consumables.html', consumables=consumables)

@app.route('/consumable/add', methods=['GET', 'POST'])
def add_consumable():
    """Add new consumable"""
    if request.method == 'POST':
        conn = get_db()
        c = conn.cursor()
        
        # Handle file upload
        image_path = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_path = f"uploads/{filename}"
        
        c.execute('''
            INSERT INTO consumables (name, category, quantity, unit, min_quantity,
                                   location, compatible_with, notes, image_path, purchase_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            request.form.get('name'),
            request.form.get('category'),
            request.form.get('quantity', 0),
            request.form.get('unit'),
            request.form.get('min_quantity', 0),
            request.form.get('location'),
            request.form.get('compatible_with'),
            request.form.get('notes'),
            image_path,
            request.form.get('purchase_url')
        ))
        
        conn.commit()
        conn.close()
        
        return redirect(url_for('consumables'))
    
    return render_template('add_consumable.html')

@app.route('/consumable/<int:consumable_id>/edit', methods=['GET', 'POST'])
def edit_consumable(consumable_id):
    """Edit a consumable"""
    conn = get_db()

    if request.method == 'POST':
        c = conn.cursor()

        # Handle file upload
        image_path = request.form.get('current_image')
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_path = f"uploads/{filename}"

        c.execute('''
            UPDATE consumables
            SET name = ?, category = ?, quantity = ?, unit = ?, min_quantity = ?,
                location = ?, compatible_with = ?, notes = ?, image_path = ?, purchase_url = ?
            WHERE id = ?
        ''', (
            request.form.get('name'),
            request.form.get('category'),
            request.form.get('quantity', 0),
            request.form.get('unit'),
            request.form.get('min_quantity', 0),
            request.form.get('location'),
            request.form.get('compatible_with'),
            request.form.get('notes'),
            image_path,
            request.form.get('purchase_url'),
            consumable_id
        ))

        conn.commit()
        conn.close()

        return redirect(url_for('consumables'))

    consumable = conn.execute('SELECT * FROM consumables WHERE id = ?', (consumable_id,)).fetchone()
    conn.close()

    if not consumable:
        return redirect(url_for('consumables'))

    return render_template('edit_consumable.html', consumable=consumable)

@app.route('/consumable/<int:consumable_id>/delete', methods=['POST'])
def delete_consumable(consumable_id):
    """Delete a consumable"""
    conn = get_db()
    conn.execute('DELETE FROM consumables WHERE id = ?', (consumable_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('consumables'))

@app.route('/materials')
def materials():
    """List all materials"""
    conn = get_db()
    materials = conn.execute('SELECT * FROM materials ORDER BY category, name').fetchall()

    # Get low stock materials
    low_stock = conn.execute('''
        SELECT * FROM materials
        WHERE min_quantity IS NOT NULL AND quantity <= min_quantity
        ORDER BY category, name
    ''').fetchall()

    conn.close()

    return render_template('materials.html', materials=materials, low_stock=low_stock)

@app.route('/material/add', methods=['GET', 'POST'])
def add_material():
    """Add new material"""
    if request.method == 'POST':
        conn = get_db()
        c = conn.cursor()

        # Handle file upload
        image_path = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_path = f"uploads/{filename}"

        c.execute('''
            INSERT INTO materials (name, category, material_type, quantity, unit, min_quantity,
                                 dimensions_length, dimensions_width, dimensions_thickness, dimension_unit,
                                 grade, finish, color, purchase_price, cost_per_unit, supplier,
                                 purchase_date, purchase_url, location, notes, image_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            request.form.get('name'),
            request.form.get('category'),
            request.form.get('material_type'),
            request.form.get('quantity', 0),
            request.form.get('unit'),
            request.form.get('min_quantity') or None,
            request.form.get('dimensions_length') or None,
            request.form.get('dimensions_width') or None,
            request.form.get('dimensions_thickness') or None,
            request.form.get('dimension_unit'),
            request.form.get('grade'),
            request.form.get('finish'),
            request.form.get('color'),
            request.form.get('purchase_price') or None,
            request.form.get('cost_per_unit') or None,
            request.form.get('supplier'),
            request.form.get('purchase_date'),
            request.form.get('purchase_url'),
            request.form.get('location'),
            request.form.get('notes'),
            image_path
        ))

        conn.commit()
        conn.close()

        return redirect(url_for('materials'))

    return render_template('add_material.html')

@app.route('/material/<int:material_id>/edit', methods=['GET', 'POST'])
def edit_material(material_id):
    """Edit a material"""
    conn = get_db()

    if request.method == 'POST':
        c = conn.cursor()

        # Handle file upload
        image_path = request.form.get('current_image')
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_path = f"uploads/{filename}"

        c.execute('''
            UPDATE materials
            SET name = ?, category = ?, material_type = ?, quantity = ?, unit = ?, min_quantity = ?,
                dimensions_length = ?, dimensions_width = ?, dimensions_thickness = ?, dimension_unit = ?,
                grade = ?, finish = ?, color = ?, purchase_price = ?, cost_per_unit = ?, supplier = ?,
                purchase_date = ?, purchase_url = ?, location = ?, notes = ?, image_path = ?
            WHERE id = ?
        ''', (
            request.form.get('name'),
            request.form.get('category'),
            request.form.get('material_type'),
            request.form.get('quantity', 0),
            request.form.get('unit'),
            request.form.get('min_quantity') or None,
            request.form.get('dimensions_length') or None,
            request.form.get('dimensions_width') or None,
            request.form.get('dimensions_thickness') or None,
            request.form.get('dimension_unit'),
            request.form.get('grade'),
            request.form.get('finish'),
            request.form.get('color'),
            request.form.get('purchase_price') or None,
            request.form.get('cost_per_unit') or None,
            request.form.get('supplier'),
            request.form.get('purchase_date'),
            request.form.get('purchase_url'),
            request.form.get('location'),
            request.form.get('notes'),
            image_path,
            material_id
        ))

        conn.commit()
        conn.close()

        return redirect(url_for('materials'))

    material = conn.execute('SELECT * FROM materials WHERE id = ?', (material_id,)).fetchone()
    conn.close()

    if not material:
        return redirect(url_for('materials'))

    return render_template('edit_material.html', material=material)

@app.route('/material/<int:material_id>/delete', methods=['POST'])
def delete_material(material_id):
    """Delete a material"""
    conn = get_db()
    conn.execute('DELETE FROM materials WHERE id = ?', (material_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('materials'))

@app.route('/fasteners')
def fasteners():
    """List all fasteners with search and filter"""
    conn = get_db()

    # Get search parameters
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    location = request.args.get('location', '')

    # Build query
    query = 'SELECT * FROM fasteners WHERE 1=1'
    params = []

    if search:
        query += ' AND (category LIKE ? OR size LIKE ? OR material LIKE ? OR head_type LIKE ? OR location LIKE ?)'
        search_param = f'%{search}%'
        params.extend([search_param] * 5)

    if category:
        query += ' AND category = ?'
        params.append(category)

    if location:
        query += ' AND location LIKE ?'
        params.append(f'%{location}%')

    query += ' ORDER BY category, size, length'

    fasteners = conn.execute(query, params).fetchall()

    # Get unique categories and locations for filters
    categories = conn.execute('SELECT DISTINCT category FROM fasteners WHERE category IS NOT NULL AND category != "" ORDER BY category').fetchall()
    locations = conn.execute('SELECT DISTINCT location FROM fasteners WHERE location IS NOT NULL AND location != "" ORDER BY location').fetchall()

    # Get low stock items (quantity <= min_quantity)
    low_stock = conn.execute('''
        SELECT * FROM fasteners
        WHERE min_quantity IS NOT NULL AND quantity <= min_quantity
        ORDER BY category, size
    ''').fetchall()

    conn.close()

    return render_template('fasteners.html',
                         fasteners=fasteners,
                         categories=categories,
                         locations=locations,
                         low_stock=low_stock,
                         search=search,
                         current_category=category,
                         current_location=location)

@app.route('/fastener/add', methods=['GET', 'POST'])
def add_fastener():
    """Add a new fastener"""
    if request.method == 'POST':
        conn = get_db()
        c = conn.cursor()

        # Handle file upload
        image_path = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_path = f"uploads/{filename}"

        c.execute('''
            INSERT INTO fasteners (category, size, length, material, head_type, thread_type,
                                 quantity, min_quantity, location, notes, image_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            request.form.get('category'),
            request.form.get('size'),
            request.form.get('length'),
            request.form.get('material'),
            request.form.get('head_type'),
            request.form.get('thread_type'),
            request.form.get('quantity', 0),
            request.form.get('min_quantity', 0),
            request.form.get('location'),
            request.form.get('notes'),
            image_path
        ))

        conn.commit()
        conn.close()

        return redirect(url_for('fasteners'))

    return render_template('add_fastener.html')

@app.route('/fastener/wizard')
def fastener_wizard():
    """Interactive wizard for adding fasteners"""
    return render_template('fastener_wizard.html')

@app.route('/fastener/batch-add', methods=['POST'])
def batch_add_fasteners():
    """Add multiple fasteners at once from wizard"""
    conn = get_db()
    c = conn.cursor()

    # Get form data
    data = request.get_json()
    fasteners = data.get('fasteners', [])

    added_count = 0
    for fastener in fasteners:
        try:
            c.execute('''
                INSERT INTO fasteners (category, size, length, material, head_type, thread_type,
                                     quantity, min_quantity, location, notes, image_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                fastener.get('category'),
                fastener.get('size'),
                fastener.get('length'),
                fastener.get('material'),
                fastener.get('head_type'),
                fastener.get('thread_type'),
                fastener.get('quantity', 0),
                fastener.get('min_quantity', 0),
                fastener.get('location'),
                fastener.get('notes'),
                None  # image_path - not supported in batch mode
            ))
            added_count += 1
        except Exception as e:
            print(f"Error adding fastener: {e}")
            continue

    conn.commit()
    conn.close()

    return jsonify({'success': True, 'count': added_count})

@app.route('/fastener/<int:fastener_id>/edit', methods=['GET', 'POST'])
def edit_fastener(fastener_id):
    """Edit a fastener"""
    conn = get_db()

    if request.method == 'POST':
        c = conn.cursor()

        # Handle file upload
        image_path = request.form.get('current_image')
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_path = f"uploads/{filename}"

        c.execute('''
            UPDATE fasteners
            SET category = ?, size = ?, length = ?, material = ?, head_type = ?, thread_type = ?,
                quantity = ?, min_quantity = ?, location = ?, notes = ?, image_path = ?
            WHERE id = ?
        ''', (
            request.form.get('category'),
            request.form.get('size'),
            request.form.get('length'),
            request.form.get('material'),
            request.form.get('head_type'),
            request.form.get('thread_type'),
            request.form.get('quantity', 0),
            request.form.get('min_quantity', 0),
            request.form.get('location'),
            request.form.get('notes'),
            image_path,
            fastener_id
        ))

        conn.commit()
        conn.close()

        return redirect(url_for('fasteners'))

    fastener = conn.execute('SELECT * FROM fasteners WHERE id = ?', (fastener_id,)).fetchone()
    conn.close()

    if not fastener:
        return redirect(url_for('fasteners'))

    return render_template('edit_fastener.html', fastener=fastener)

@app.route('/fastener/<int:fastener_id>/delete', methods=['POST'])
def delete_fastener(fastener_id):
    """Delete a fastener"""
    conn = get_db()
    conn.execute('DELETE FROM fasteners WHERE id = ?', (fastener_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('fasteners'))

@app.route('/fastener/<int:fastener_id>/duplicate')
def duplicate_fastener(fastener_id):
    """Duplicate a fastener (pre-fill form with existing data)"""
    conn = get_db()
    fastener = conn.execute('SELECT * FROM fasteners WHERE id = ?', (fastener_id,)).fetchone()
    conn.close()

    if not fastener:
        return redirect(url_for('fasteners'))

    return render_template('add_fastener.html', fastener=fastener, is_duplicate=True)

@app.route('/api/autocomplete/brands')
def autocomplete_brands():
    """Get list of unique brands from database for autocomplete"""
    conn = get_db()
    brands = conn.execute('''
        SELECT DISTINCT brand FROM tools
        WHERE brand IS NOT NULL AND brand != ''
        ORDER BY brand
    ''').fetchall()
    conn.close()
    return jsonify([row['brand'] for row in brands])

@app.route('/api/autocomplete/models')
def autocomplete_models():
    """Get list of unique models from database for autocomplete, optionally filtered by brand"""
    brand = request.args.get('brand', '')
    conn = get_db()
    if brand:
        models = conn.execute('''
            SELECT DISTINCT model FROM tools
            WHERE brand = ? AND model IS NOT NULL AND model != ''
            ORDER BY model
        ''', (brand,)).fetchall()
    else:
        models = conn.execute('''
            SELECT DISTINCT model FROM tools
            WHERE model IS NOT NULL AND model != ''
            ORDER BY model
        ''').fetchall()
    conn.close()
    return jsonify([row['model'] for row in models])

@app.route('/search/bunnings')
def search_bunnings():
    """Search Bunnings for products"""
    query = request.args.get('q', '')
    if not query:
        return jsonify({'success': False, 'error': 'No search query provided', 'products': []})

    results = scrape_bunnings_search(query)
    return jsonify(results)

# QR Code Routes

@app.route('/scan/<item_type>/<int:item_id>')
def scan_redirect(item_type, item_id):
    """Redirect scanned QR code to appropriate item page"""
    if item_type == 'tool':
        return redirect(url_for('tool_detail', tool_id=item_id))
    elif item_type == 'consumable':
        return redirect(url_for('consumable_detail', consumable_id=item_id))
    elif item_type == 'material':
        return redirect(url_for('material_detail', material_id=item_id))
    elif item_type == 'fastener':
        return redirect(url_for('fastener_detail', fastener_id=item_id))
    else:
        return redirect(url_for('index'))

@app.route('/scanner')
def scanner():
    """QR code scanner page"""
    return render_template('scanner.html')

@app.route('/labels')
def labels():
    """Printable labels page"""
    conn = get_db()

    # Get selected items from query params
    tool_ids = request.args.getlist('tools[]')
    consumable_ids = request.args.getlist('consumables[]')
    material_ids = request.args.getlist('materials[]')
    fastener_ids = request.args.getlist('fasteners[]')

    items = []

    # Fetch tools
    for tool_id in tool_ids:
        tool = conn.execute('SELECT * FROM tools WHERE id = ?', (tool_id,)).fetchone()
        if tool:
            items.append({
                'type': 'tool',
                'id': tool['id'],
                'name': tool['name'],
                'brand': tool['brand'],
                'category': tool['category'],
                'location': tool['location'],
                'qr_code': generate_qr_code('tool', tool['id'])
            })

    # Fetch consumables
    for consumable_id in consumable_ids:
        consumable = conn.execute('SELECT * FROM consumables WHERE id = ?', (consumable_id,)).fetchone()
        if consumable:
            items.append({
                'type': 'consumable',
                'id': consumable['id'],
                'name': consumable['name'],
                'category': consumable['category'],
                'location': consumable['location'],
                'qr_code': generate_qr_code('consumable', consumable['id'])
            })

    # Fetch materials
    for material_id in material_ids:
        material = conn.execute('SELECT * FROM materials WHERE id = ?', (material_id,)).fetchone()
        if material:
            items.append({
                'type': 'material',
                'id': material['id'],
                'name': material['name'],
                'category': material['category'],
                'location': material['location'],
                'qr_code': generate_qr_code('material', material['id'])
            })

    # Fetch fasteners
    for fastener_id in fastener_ids:
        fastener = conn.execute('SELECT * FROM fasteners WHERE id = ?', (fastener_id,)).fetchone()
        if fastener:
            items.append({
                'type': 'fastener',
                'id': fastener['id'],
                'name': f"{fastener['fastener_type']} - {fastener['head_type']}",
                'category': fastener['fastener_type'],
                'location': fastener['location'],
                'qr_code': generate_qr_code('fastener', fastener['id'])
            })

    conn.close()

    return render_template('labels.html', items=items)

@app.route('/consumable/<int:consumable_id>')
def consumable_detail(consumable_id):
    """Consumable detail page"""
    conn = get_db()
    consumable = conn.execute('SELECT * FROM consumables WHERE id = ?', (consumable_id,)).fetchone()
    conn.close()

    if not consumable:
        return redirect(url_for('consumables'))

    qr_code = generate_qr_code('consumable', consumable_id)
    return render_template('consumable_detail.html', consumable=consumable, qr_code=qr_code)

@app.route('/material/<int:material_id>')
def material_detail(material_id):
    """Material detail page"""
    conn = get_db()
    material = conn.execute('SELECT * FROM materials WHERE id = ?', (material_id,)).fetchone()
    conn.close()

    if not material:
        return redirect(url_for('materials'))

    qr_code = generate_qr_code('material', material_id)
    return render_template('material_detail.html', material=material, qr_code=qr_code)

@app.route('/fastener/<int:fastener_id>')
def fastener_detail(fastener_id):
    """Fastener detail page"""
    conn = get_db()
    fastener = conn.execute('SELECT * FROM fasteners WHERE id = ?', (fastener_id,)).fetchone()
    conn.close()

    if not fastener:
        return redirect(url_for('fasteners'))

    qr_code = generate_qr_code('fastener', fastener_id)
    return render_template('fastener_detail.html', fastener=fastener, qr_code=qr_code)

# Favorites Routes

@app.route('/api/favorite/toggle', methods=['POST'])
def toggle_favorite():
    """Toggle favorite status for an item"""
    data = request.get_json()
    item_type = data.get('item_type')
    item_id = data.get('item_id')

    if not item_type or not item_id:
        return jsonify({'success': False, 'error': 'Missing parameters'}), 400

    conn = get_db()

    # Check if already favorited
    existing = conn.execute(
        'SELECT id FROM favorites WHERE item_type = ? AND item_id = ?',
        (item_type, item_id)
    ).fetchone()

    if existing:
        # Remove favorite
        conn.execute('DELETE FROM favorites WHERE item_type = ? AND item_id = ?', (item_type, item_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'favorited': False})
    else:
        # Add favorite
        conn.execute(
            'INSERT INTO favorites (item_type, item_id) VALUES (?, ?)',
            (item_type, item_id)
        )
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'favorited': True})

@app.route('/api/favorites/check', methods=['POST'])
def check_favorites():
    """Check favorite status for multiple items"""
    data = request.get_json()
    items = data.get('items', [])

    if not items:
        return jsonify({'favorites': []})

    conn = get_db()
    favorites = []

    for item in items:
        existing = conn.execute(
            'SELECT id FROM favorites WHERE item_type = ? AND item_id = ?',
            (item['type'], item['id'])
        ).fetchone()

        if existing:
            favorites.append({'type': item['type'], 'id': item['id']})

    conn.close()
    return jsonify({'favorites': favorites})

@app.route('/favorites')
def favorites_page():
    """View all favorited items"""
    conn = get_db()

    # Get all favorites with item details
    favorites = conn.execute('''
        SELECT item_type, item_id, created_at
        FROM favorites
        ORDER BY created_at DESC
    ''').fetchall()

    items = []

    for fav in favorites:
        item_type = fav['item_type']
        item_id = fav['item_id']

        if item_type == 'tool':
            tool = conn.execute('SELECT * FROM tools WHERE id = ?', (item_id,)).fetchone()
            if tool:
                items.append({
                    'type': 'tool',
                    'id': tool['id'],
                    'name': tool['name'],
                    'brand': tool['brand'],
                    'model': tool['model'],
                    'category': tool['category'],
                    'location': tool['location'],
                    'image_path': tool['image_path']
                })
        elif item_type == 'consumable':
            consumable = conn.execute('SELECT * FROM consumables WHERE id = ?', (item_id,)).fetchone()
            if consumable:
                items.append({
                    'type': 'consumable',
                    'id': consumable['id'],
                    'name': consumable['name'],
                    'category': consumable['category'],
                    'quantity': consumable['quantity'],
                    'unit': consumable['unit'],
                    'location': consumable['location'],
                    'image_path': consumable['image_path']
                })
        elif item_type == 'material':
            material = conn.execute('SELECT * FROM materials WHERE id = ?', (item_id,)).fetchone()
            if material:
                items.append({
                    'type': 'material',
                    'id': material['id'],
                    'name': material['name'],
                    'category': material['category'],
                    'quantity': material['quantity'],
                    'unit': material['unit'],
                    'location': material['location'],
                    'image_path': material['image_path']
                })
        elif item_type == 'fastener':
            fastener = conn.execute('SELECT * FROM fasteners WHERE id = ?', (item_id,)).fetchone()
            if fastener:
                items.append({
                    'type': 'fastener',
                    'id': fastener['id'],
                    'name': f"{fastener['fastener_type']} - {fastener['diameter']}mm",
                    'category': fastener['fastener_type'],
                    'quantity': fastener['quantity'],
                    'location': fastener['location'],
                    'image_path': fastener['image_path']
                })

    conn.close()
    return render_template('favorites.html', items=items)

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
