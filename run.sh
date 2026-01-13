#!/bin/bash
echo "Starting Toolshed App..."
echo "Installing dependencies..."
pip install -r requirements.txt --break-system-packages --quiet

echo ""
echo "Starting server..."
echo "Access the application at:"
echo "  Local:   http://localhost:5000"
echo "  Network: http://$(hostname -I | awk '{print $1}'):5000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python app.py
