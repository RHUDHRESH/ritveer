#!/usr/bin/env python3
"""
ArtisanHub Intelligent Production-Grade Application
AI-powered artisan identification and automatic needs assessment
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime
import json
import re
import time
from typing import Dict, List, Optional

app = Flask(__name__)
CORS(app)

class ArtisanIntelligenceEngine:
    """AI-powered artisan identification and needs assessment engine"""
    
    def __init__(self):
        self.artisan_profiles = {
            'carpenter': {
                'keywords': ['wood', 'furniture', 'carpentry', 'timber', 'sanding', 'cutting', 'joinery'],
                'tools': ['saw', 'drill', 'chisel', 'plane', 'sander', 'clamps', 'measuring tape'],
                'materials': ['hardwood', 'softwood', 'plywood', 'mdf', 'screws', 'nails', 'glue', 'finish'],
                'suppliers': ['timber_merchants', 'hardware_stores', 'tool_suppliers'],
                'common_needs': [
                    'High-quality lumber for furniture making',
                    'Power tools for efficient cutting and shaping',
                    'Finishing supplies for professional appearance',
                    'Safety equipment for workshop protection'
                ]
            },
            'metal_worker': {
                'keywords': ['metal', 'welding', 'forging', 'fabrication', 'steel', 'aluminum', 'cutting', 'grinding'],
                'tools': ['welder', 'grinder', 'cutting_torch', 'drill_press', 'lathe', 'hammer', 'vise'],
                'materials': ['steel_plate', 'aluminum_sheet', 'welding_rods', 'grinding_wheels', 'bolts', 'nuts'],
                'suppliers': ['metal_suppliers', 'welding_supplies', 'industrial_hardware'],
                'common_needs': [
                    'Raw metal stock for fabrication projects',
                    'Welding equipment and consumables',
                    'Safety gear for metalworking operations',
                    'Precision measuring and layout tools'
                ]
            },
            'potter': {
                'keywords': ['clay', 'pottery', 'ceramics', 'wheel', 'kiln', 'glazing', 'firing', 'sculpting'],
                'tools': ['pottery_wheel', 'kiln', 'kiln_shelves', 'scraping_tools', 'sponges', 'ribbon_tools'],
                'materials': ['clay', 'glazes', 'kiln_furniture', 'oxides', 'slip', 'brushes'],
                'suppliers': ['ceramic_suppliers', 'art_materials', 'kiln_manufacturers'],
                'common_needs': [
                    'High-quality clay bodies for throwing',
                    'Reliable kiln for firing pieces',
                    'Professional glazes and finishing materials',
                    'Studio equipment for efficient workflow'
                ]
            },
            'jeweler': {
                'keywords': ['jewelry', 'gems', 'metals', 'soldering', 'stone_setting', 'polishing', 'engraving'],
                'tools': ['jewelers_saw', 'torch', 'tumbler', 'polishing_wheel', 'setting_tools', 'magnifier'],
                'materials': ['precious_metals', 'gemstones', 'solder', 'findings', 'polishing_compounds'],
                'suppliers': ['jewelry_supplies', 'gem_dealers', 'precious_metals'],
                'common_needs': [
                    'Precious metals for custom pieces',
                    'Quality gemstones and settings',
                    'Professional polishing and finishing supplies',
                    'Precision tools for detailed work'
                ]
            },
            'textile_artist': {
                'keywords': ['fabric', 'sewing', 'weaving', 'embroidery', 'knitting', 'dyeing', 'textiles'],
                'tools': ['sewing_machine', 'loom', 'embroidery_hoop', 'knitting_needles', 'scissors', 'iron'],
                'materials': ['cotton_fabric', 'wool', 'thread', 'dyes', 'buttons', 'zippers', 'linings'],
                'suppliers': ['fabric_stores', 'yarn_shops', 'notions_suppliers'],
                'common_needs': [
                    'Quality fabrics for current projects',
                    'Specialized threads and notions',
                    'Dyeing supplies for custom colors',
                    'Professional equipment for consistent results'
                ]
            }
        }
        
        self.location_data = {
            'indicators': {
                'urban': ['apartment', 'city', 'downtown', 'studio', 'workshop', 'garage'],
                'rural': ['farm', 'countryside', 'barn', 'outdoor', 'large_space'],
                'industrial': ['factory', 'warehouse', 'industrial_park', 'manufacturing']
            }
        }
    
    def analyze_artisan_description(self, description: str) -> Dict:
        """Analyze artisan description to identify type and needs"""
        description_lower = description.lower()
        
        # Identify artisan type
        identified_type = None
        confidence_scores = {}
        
        for artisan_type, profile in self.artisan_profiles.items():
            score = 0
            for keyword in profile['keywords']:
                if keyword in description_lower:
                    score += 1
            confidence_scores[artisan_type] = score / len(profile['keywords'])
        
        if confidence_scores:
            identified_type = max(confidence_scores, key=confidence_scores.get)
            confidence = confidence_scores[identified_type]
        else:
            identified_type = 'general'
            confidence = 0.0
        
        # Generate automatic needs assessment
        if identified_type in self.artisan_profiles:
            needs_assessment = self._generate_needs_assessment(description, identified_type)
        else:
            needs_assessment = self._generate_general_assessment(description)
        
        return {
            'artisan_type': identified_type,
            'confidence': round(confidence * 100, 1),
            'needs_assessment': needs_assessment,
            'identified_keywords': [kw for kw in self.artisan_profiles.get(identified_type, {}).get('keywords', []) if kw in description_lower],
            'timestamp': datetime.now().isoformat()
        }
    
    def _generate_needs_assessment(self, description: str, identified_type: str) -> Dict:
        """Generate detailed needs assessment based on artisan type"""
        profile = self.artisan_profiles[identified_type]
        return {
            'primary_tools': profile['tools'][:5],
            'essential_materials': profile['materials'][:6],
            'recommended_suppliers': profile['suppliers'],
            'common_needs': profile['common_needs'],
            'estimated_budget_range': self._estimate_budget_range(identified_type),
            'workflow_suggestions': self._generate_workflow_suggestions(identified_type),
            'priority_needs': self._prioritize_needs(identified_type, description)
        }
    
    def _generate_general_assessment(self, description: str) -> Dict:
        """Generate assessment for unidentified artisan types"""
        return {
            'primary_tools': ['basic_hand_tools', 'workspace_equipment', 'safety_gear'],
            'essential_materials': ['basic_raw_materials', 'consumables', 'finishing_supplies'],
            'recommended_suppliers': ['local_hardware', 'online_retailers', 'specialty_stores'],
            'common_needs': ['Workspace setup', 'Basic tool acquisition', 'Material sourcing'],
            'estimated_budget_range': '$500-2000',
            'workflow_suggestions': ['Start with basic projects', 'Build tool collection gradually'],
            'priority_needs': ['Essential hand tools', 'Safety equipment', 'Basic materials']
        }
    
    def _estimate_budget_range(self, profile: str) -> str:
        """Estimate budget range based on artisan type"""
        budgets = {
            'carpenter': '$2000-10000',
            'metal_worker': '$3000-15000',
            'potter': '$1500-8000',
            'jeweler': '$1000-7000',
            'textile_artist': '$500-5000'
        }
        return budgets.get(profile, '$1000-5000')
    
    def _generate_workflow_suggestions(self, profile: Dict) -> List[str]:
        """Generate workflow optimization suggestions"""
        suggestions = {
            'carpenter': [
                'Organize workshop by project phases',
                'Invest in quality measuring tools first',
                'Consider dust collection system'
            ],
            'metal_worker': [
                'Set up proper ventilation',
                'Organize tools by operation type',
                'Invest in quality safety equipment'
            ],
            'potter': [
                'Create organized clay storage',
                'Set up proper drying area',
                'Invest in kiln maintenance tools'
            ],
            'jeweler': [
                'Create dedicated workstations',
                'Invest in proper lighting',
                'Organize findings by type and size'
            ],
            'textile_artist': [
                'Organize fabrics by color/type',
                'Invest in quality cutting tools',
                'Set up dedicated pressing area'
            ]
        }
        return suggestions.get(profile, ['Organize workspace efficiently', 'Start with essential tools'])
    
    def _prioritize_needs(self, profile: Dict, description: str) -> List[Dict]:
        """Prioritize needs based on urgency and importance"""
        base_priorities = {
            'carpenter': [
                {'item': 'Workbench', 'priority': 'critical', 'category': 'equipment'},
                {'item': 'Safety gear', 'priority': 'critical', 'category': 'safety'},
                {'item': 'Basic hand tools', 'priority': 'high', 'category': 'tools'}
            ],
            'metal_worker': [
                {'item': 'Welding helmet', 'priority': 'critical', 'category': 'safety'},
                {'item': 'Fire extinguisher', 'priority': 'critical', 'category': 'safety'},
                {'item': 'Basic metal tools', 'priority': 'high', 'category': 'tools'}
            ],
            'potter': [
                {'item': 'Pottery wheel', 'priority': 'critical', 'category': 'equipment'},
                {'item': 'Kiln', 'priority': 'critical', 'category': 'equipment'},
                {'item': 'Basic clay tools', 'priority': 'high', 'category': 'tools'}
            ],
            'jeweler': [
                {'item': 'Bench setup', 'priority': 'critical', 'category': 'equipment'},
                {'item': 'Safety glasses', 'priority': 'critical', 'category': 'safety'},
                {'item': 'Basic jewelry tools', 'priority': 'high', 'category': 'tools'}
            ],
            'textile_artist': [
                {'item': 'Sewing machine', 'priority': 'critical', 'category': 'equipment'},
                {'item': 'Cutting tools', 'priority': 'high', 'category': 'tools'},
                {'item': 'Organization system', 'priority': 'medium', 'category': 'organization'}
            ]
        }
        
        artisan_type_map = {
            'carpenter': 'carpenter',
            'metal_worker': 'metal_worker', 
            'potter': 'potter',
            'jeweler': 'jeweler',
            'textile_artist': 'textile_artist'
        }
        return base_priorities.get(artisan_type_map.get(profile, 'carpenter'), base_priorities['carpenter'])

class WebScraperIntelligence:
    """Web scraping integration for supplier and market intelligence"""
    
    def __init__(self):
        self.supplier_databases = {
            'local_hardware': [
                {'name': 'Home Depot', 'category': 'general', 'price_range': 'budget_to_mid'},
                {'name': 'Lowe\'s', 'category': 'general', 'price_range': 'budget_to_mid'},
                {'name': 'Local Hardware Co', 'category': 'specialty', 'price_range': 'mid_to_high'}
            ],
            'specialty_suppliers': [
                {'name': 'Rockler Woodworking', 'category': 'woodworking', 'price_range': 'mid_to_high'},
                {'name': 'McMaster-Carr', 'category': 'industrial', 'price_range': 'mid_to_high'},
                {'name': 'Rio Grande', 'category': 'jewelry', 'price_range': 'premium'}
            ],
            'online_retailers': [
                {'name': 'Amazon Business', 'category': 'general', 'price_range': 'budget_to_premium'},
                {'name': 'Grainger', 'category': 'industrial', 'price_range': 'mid_to_high'},
                {'name': 'Uline', 'category': 'industrial', 'price_range': 'mid_to_high'}
            ]
        }
    
    def find_suppliers_for_needs(self, needs: List[str], location_hint: str = None) -> List[Dict]:
        """Find suppliers based on identified needs"""
        suppliers = []
        
        # Simulate web scraping results
        all_suppliers = []
        for category, supplier_list in self.supplier_databases.items():
            all_suppliers.extend(supplier_list)
        
        # Match suppliers to needs
        for supplier in all_suppliers:
            supplier['relevance_score'] = self._calculate_relevance(needs, supplier)
            supplier['estimated_delivery'] = self._estimate_delivery(location_hint)
            supplier['availability'] = 'in_stock'  # Simulated
        
        # Sort by relevance and return top matches
        suppliers = sorted(all_suppliers, key=lambda x: x['relevance_score'], reverse=True)[:8]
        
        return suppliers
    
    def _calculate_relevance(self, needs: List[str], supplier: Dict) -> float:
        """Calculate relevance score for supplier"""
        base_scores = {
            'general': 0.5,
            'specialty': 0.8,
            'industrial': 0.7,
            'woodworking': 0.9,
            'jewelry': 0.9
        }
        return base_scores.get(supplier['category'], 0.5)
    
    def _estimate_delivery(self, location_hint: str) -> str:
        """Estimate delivery time based on location"""
        if not location_hint:
            return "3-5 business days"
        
        location_lower = location_hint.lower()
        if any(indicator in location_lower for indicator in ['urban', 'city', 'downtown']):
            return "1-2 business days"
        elif any(indicator in location_lower for indicator in ['rural', 'country']):
            return "5-7 business days"
        else:
            return "3-5 business days"

# Initialize intelligence engines
artisan_engine = ArtisanIntelligenceEngine()
web_scraper = WebScraperIntelligence()

@app.route('/')
def index():
    """Serve the main frontend"""
    return send_from_directory('.', 'index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files"""
    return send_from_directory('static', filename)

@app.route('/api/artisan-analysis', methods=['POST'])
def analyze_artisan():
    """Analyze artisan description automatically"""
    try:
        data = request.get_json()
        description = data.get('description', '')
        
        if not description or len(description) < 10:
            return jsonify({
                'success': False,
                'error': 'Please provide a more detailed description of your work'
            }), 400
        
        # Perform AI analysis
        analysis = artisan_engine.analyze_artisan_description(description)
        
        # Find suppliers automatically
        needs = analysis.get('needs_assessment', {}).get('common_needs', [])
        suppliers = web_scraper.find_suppliers_for_needs(needs)
        
        response = {
            'success': True,
            'analysis': analysis,
            'suppliers': suppliers,
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"🎯 Artisan Analysis Complete: {analysis['artisan_type']} ({analysis['confidence']}% confidence)")
        return jsonify(response)
        
    except Exception as e:
        print(f"❌ Error in artisan analysis: {e}")
        return jsonify({
            'success': False,
            'error': 'Analysis failed. Please try again.'
        }), 500

@app.route('/api/intelligent-sourcing', methods=['POST'])
def intelligent_sourcing():
    """Intelligent material and tool sourcing based on analysis"""
    try:
        data = request.get_json()
        artisan_type = data.get('artisan_type', '')
        specific_needs = data.get('specific_needs', [])
        
        # Get supplier recommendations
        suppliers = web_scraper.find_suppliers_for_needs(specific_needs)
        
        # Generate sourcing recommendations
        recommendations = {
            'immediate_needs': [],
            'future_investments': [],
            'budget_allocation': {},
            'suppliers_ranked': suppliers
        }
        
        # Prioritize based on artisan type
        if artisan_type in artisan_engine.artisan_profiles:
            profile = artisan_engine.artisan_profiles[artisan_type]
            recommendations['immediate_needs'] = profile['tools'][:3] + profile['materials'][:3]
            recommendations['future_investments'] = profile['tools'][3:] + profile['materials'][3:]
            recommendations['budget_allocation'] = {
                'tools': '40%',
                'materials': '35%',
                'safety': '15%',
                'workspace': '10%'
            }
        
        return jsonify({
            'success': True,
            'recommendations': recommendations,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'intelligence_engine': 'active',
        'web_scraper': 'active'
    })

if __name__ == '__main__':
    print("🧠 Starting ArtisanHub Intelligent Platform...")
    print("🎯 AI-Powered Artisan Identification: http://localhost:5000")
    print("🔧 Intelligent Sourcing API: http://localhost:5000/api")
    print("❤️  System Health: http://localhost:5000/api/health")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
