#!/usr/bin/env python3
"""
ArtisanHub Simple Flask Web Application
Working version with mock backend integration
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime
import json

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    """Serve the main frontend"""
    return send_from_directory('.', 'index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files"""
    return send_from_directory('static', filename)

@app.route('/api/agents', methods=['POST'])
def handle_agent_request():
    """Handle agent requests from frontend"""
    try:
        data = request.get_json()
        print(f"📥 Received request: {data}")
        
        # Mock response for demo
        response = {
            "success": True,
            "request_id": f"REQ-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "status": "intake_processing",
            "message": "Request received and being processed",
            "data": data
        }
        
        print(f"✅ Response generated: {response}")
        return jsonify(response)
        
    except Exception as e:
        print(f"❌ Error processing request: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to process request"
        }), 500

@app.route('/api/orders/<order_id>', methods=['GET'])
def get_order_status(order_id):
    """Get order status by ID"""
    try:
        # Mock response
        response = {
            "order_id": order_id,
            "status": "in_delivery",
            "created_at": datetime.now().isoformat(),
            "estimated_delivery": "2024-10-28T18:00:00Z"
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/suppliers', methods=['POST'])
def get_suppliers():
    """Get supplier recommendations"""
    try:
        data = request.get_json()
        
        # Mock supplier data for demo
        suppliers = [
            {
                "id": f"SUP-{datetime.now().strftime('%Y%m%d%H%M%S')}-1",
                "name": "Chennai Metal Works",
                "location": data.get('location', 'Chennai'),
                "price": round(100 + (data.get('quantity', 1) * 50), 2),
                "delivery_days": 2,
                "rating": 4.5,
                "confidence": 0.85,
                "material": data.get('material', 'Materials')
            },
            {
                "id": f"SUP-{datetime.now().strftime('%Y%m%d%H%M%S')}-2",
                "name": "Mumbai Steel Suppliers",
                "location": data.get('location', 'Mumbai'),
                "price": round(120 + (data.get('quantity', 1) * 55), 2),
                "delivery_days": 3,
                "rating": 4.2,
                "confidence": 0.78,
                "material": data.get('material', 'Materials')
            },
            {
                "id": f"SUP-{datetime.now().strftime('%Y%m%d%H%M%S')}-3",
                "name": "Delhi Industrial Materials",
                "location": data.get('location', 'Delhi'),
                "price": round(90 + (data.get('quantity', 1) * 45), 2),
                "delivery_days": 4,
                "rating": 4.0,
                "confidence": 0.72,
                "material": data.get('material', 'Materials')
            }
        ]
        
        return jsonify({
            "success": True,
            "suppliers": suppliers
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/analytics', methods=['GET'])
def get_analytics():
    """Get platform analytics data"""
    try:
        # Mock analytics data
        analytics = {
            "total_orders": 156,
            "active_suppliers": 42,
            "avg_delivery_time": "18h",
            "success_rate": "94%",
            "order_trends": {
                "labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                "data": [12, 19, 15, 25, 22, 30, 28]
            },
            "material_categories": {
                "labels": ["Metals", "Wood", "Plastics", "Textiles", "Others"],
                "data": [35, 25, 20, 15, 5]
            }
        }
        
        return jsonify({
            "success": True,
            "analytics": analytics
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "backend_available": True
    })

if __name__ == '__main__':
    print("🚀 Starting ArtisanHub Web Application...")
    print("📱 Frontend: http://localhost:5000")
    print("🔧 API Base: http://localhost:5000/api")
    print("❤️  Health Check: http://localhost:5000/api/health")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
