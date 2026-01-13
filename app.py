from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3
import os
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

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
            material_type TEXT,
            quantity REAL,
            unit TEXT,
            location TEXT,
            notes TEXT,
            image_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    """Main dashboard"""
    conn = get_db()
    
    # Get counts
    tool_count = conn.execute('SELECT COUNT(*) as count FROM tools').fetchone()['count']
    consumable_count = conn.execute('SELECT COUNT(*) as count FROM consumables').fetchone()['count']
    material_count = conn.execute('SELECT COUNT(*) as count FROM materials').fetchone()['count']
    
    # Get low stock consumables
    low_stock = conn.execute('''
        SELECT * FROM consumables 
        WHERE quantity <= min_quantity 
        ORDER BY quantity ASC 
        LIMIT 5
    ''').fetchall()
    
    # Get recent tools
    recent_tools = conn.execute('''
        SELECT * FROM tools 
        ORDER BY created_at DESC 
        LIMIT 6
    ''').fetchall()
    
    conn.close()
    
    return render_template('index.html', 
                         tool_count=tool_count,
                         consumable_count=consumable_count,
                         material_count=material_count,
                         low_stock=low_stock,
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
    
    return render_template('tool_detail.html', tool=tool, compatible=compatible)

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

@app.route('/materials')
def materials():
    """List all materials"""
    conn = get_db()
    materials = conn.execute('SELECT * FROM materials ORDER BY name').fetchall()
    conn.close()
    
    return render_template('materials.html', materials=materials)

@app.route('/search/bunnings')
def search_bunnings():
    """Search Bunnings for accessories - placeholder for future implementation"""
    tool_name = request.args.get('tool', '')
    # This would integrate with web scraping in the future
    return jsonify({'message': 'Bunnings search coming soon', 'tool': tool_name})

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
