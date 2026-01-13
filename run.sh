#!/bin/bash
echo "Starting Toolshed App..."
echo "Installing dependencies..."
pip3 install -r requirements.txt --quiet 2>/dev/null || pip3 install -r requirements.txt

echo ""
echo "Starting server..."
echo "Access the application at:"
echo "  Local:   http://localhost:5000"
echo "  Network: http://$(hostname -I | awk '{print $1}'):5000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python3 app.py
