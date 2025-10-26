#!/usr/bin/env python3
"""
ArtisanHub Flight Check System
Comprehensive testing of all components: Ollama, AI Engine, Web Scraper, APIs
"""

import requests
import json
import time
import sys
import subprocess
from datetime import datetime

class FlightCheckSystem:
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.results = {}
        self.total_checks = 0
        self.passed_checks = 0
    
    def log_result(self, test_name: str, status: bool, message: str = "", details: dict = None):
        """Log test result with timestamp"""
        self.total_checks += 1
        if status:
            self.passed_checks += 1
            icon = "✅"
        else:
            icon = "❌"
        
        self.results[test_name] = {
            "status": "PASS" if status else "FAIL",
            "message": message,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"{icon} {test_name}: {message}")
        if details:
            for key, value in details.items():
                print(f"   • {key}: {value}")
    
    def test_ollama_connection(self):
        """Test if Ollama is running and accessible"""
        try:
            # Test Ollama API
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [model.get("name", "unknown") for model in models]
                self.log_result(
                    "Ollama Connection",
                    True,
                    f"Found {len(models)} models",
                    {"models": model_names, "status_code": response.status_code}
                )
                return True
            else:
                self.log_result(
                    "Ollama Connection",
                    False,
                    f"HTTP {response.status_code}",
                    {"status_code": response.status_code}
                )
                return False
        except requests.exceptions.ConnectionError:
            self.log_result(
                "Ollama Connection",
                False,
                "Connection refused - Ollama not running",
                {"error": "Connection refused"}
            )
            return False
        except Exception as e:
            self.log_result(
                "Ollama Connection",
                False,
                f"Error: {str(e)}",
                {"error": str(e)}
            )
            return False
    
    def test_flask_server(self):
        """Test if Flask server is running"""
        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.log_result(
                    "Flask Server",
                    True,
                    "Server responding correctly",
                    {"status": data.get("status"), "components": data.keys()}
                )
                return True
            else:
                self.log_result(
                    "Flask Server",
                    False,
                    f"HTTP {response.status_code}",
                    {"status_code": response.status_code}
                )
                return False
        except Exception as e:
            self.log_result(
                "Flask Server",
                False,
                f"Connection error: {str(e)}",
                {"error": str(e)}
            )
            return False
    
    def test_ai_analysis_endpoint(self):
        """Test AI artisan analysis endpoint"""
        try:
            test_description = "I build custom furniture from reclaimed wood, specializing in dining tables and bookshelves."
            payload = {"description": test_description}
            
            response = requests.post(
                f"{self.base_url}/api/artisan-analysis",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    analysis = data.get("analysis", {})
                    self.log_result(
                        "AI Analysis Endpoint",
                        True,
                        "Artisan analysis working",
                        {
                            "artisan_type": analysis.get("artisan_type"),
                            "confidence": analysis.get("confidence"),
                            "suppliers_found": len(data.get("suppliers", []))
                        }
                    )
                    return True
                else:
                    self.log_result(
                        "AI Analysis Endpoint",
                        False,
                        f"API returned failure: {data.get('error', 'Unknown error')}"
                    )
                    return False
            else:
                self.log_result(
                    "AI Analysis Endpoint",
                    False,
                    f"HTTP {response.status_code}",
                    {"status_code": response.status_code}
                )
                return False
        except Exception as e:
            self.log_result(
                "AI Analysis Endpoint",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
            return False
    
    def test_intelligent_sourcing_endpoint(self):
        """Test intelligent sourcing endpoint"""
        try:
            payload = {
                "artisan_type": "carpenter",
                "specific_needs": ["wood", "saw", "drill"]
            }
            
            response = requests.post(
                f"{self.base_url}/api/intelligent-sourcing",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    recommendations = data.get("recommendations", {})
                    self.log_result(
                        "Intelligent Sourcing Endpoint",
                        True,
                        "Supplier recommendations working",
                        {
                            "immediate_needs": len(recommendations.get("immediate_needs", [])),
                            "budget_allocation": recommendations.get("budget_allocation", {}),
                            "suppliers_ranked": len(recommendations.get("suppliers_ranked", []))
                        }
                    )
                    return True
                else:
                    self.log_result(
                        "Intelligent Sourcing Endpoint",
                        False,
                        f"API returned failure: {data.get('error', 'Unknown error')}"
                    )
                    return False
            else:
                self.log_result(
                    "Intelligent Sourcing Endpoint",
                    False,
                    f"HTTP {response.status_code}",
                    {"status_code": response.status_code}
                )
                return False
        except Exception as e:
            self.log_result(
                "Intelligent Sourcing Endpoint",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
            return False
    
    def test_static_files(self):
        """Test if static files are served correctly"""
        try:
            response = requests.get(f"{self.base_url}/", timeout=5)
            if response.status_code == 200:
                content_length = len(response.content)
                self.log_result(
                    "Static File Serving",
                    True,
                    "Frontend loading correctly",
                    {"content_length": content_length, "content_type": response.headers.get("content-type")}
                )
                return True
            else:
                self.log_result(
                    "Static File Serving",
                    False,
                    f"HTTP {response.status_code}",
                    {"status_code": response.status_code}
                )
                return False
        except Exception as e:
            self.log_result(
                "Static File Serving",
                False,
                f"Error loading frontend: {str(e)}",
                {"error": str(e)}
            )
            return False
    
    def test_artisan_intelligence_engine(self):
        """Test the artisan intelligence engine directly"""
        try:
            # Import and test the intelligence engine
            sys.path.append('artisan_agents')
            from intelligent_app import ArtisanIntelligenceEngine
            
            engine = ArtisanIntelligenceEngine()
            
            # Test with known artisan types
            test_cases = [
                ("I work with wood and build furniture", "carpenter"),
                ("I weld metal and create sculptures", "metal_worker"),
                ("I make pottery on a wheel", "potter"),
                ("I create jewelry with gems", "jeweler"),
                ("I sew clothes and fabrics", "textile_artist")
            ]
            
            passed_tests = 0
            for description, expected_type in test_cases:
                result = engine.analyze_artisan_description(description)
                if result.get("artisan_type") == expected_type and result.get("confidence", 0) > 50:
                    passed_tests += 1
            
            success_rate = (passed_tests / len(test_cases)) * 100
            self.log_result(
                "Artisan Intelligence Engine",
                success_rate >= 80,
                f"{passed_tests}/{len(test_cases)} tests passed ({success_rate:.0f}%)",
                {"success_rate": success_rate, "passed_tests": passed_tests}
            )
            return success_rate >= 80
        except Exception as e:
            self.log_result(
                "Artisan Intelligence Engine",
                False,
                f"Engine error: {str(e)}",
                {"error": str(e)}
            )
            return False
    
    def test_web_scraper_intelligence(self):
        """Test the web scraper intelligence"""
        try:
            sys.path.append('artisan_agents')
            from intelligent_app import WebScraperIntelligence
            
            scraper = WebScraperIntelligence()
            
            # Test supplier finding
            test_needs = ["wood", "tools", "safety equipment"]
            suppliers = scraper.find_suppliers_for_needs(test_needs)
            
            if suppliers and len(suppliers) > 0:
                self.log_result(
                    "Web Scraper Intelligence",
                    True,
                    f"Found {len(suppliers)} suppliers",
                    {"suppliers": [s.get("name") for s in suppliers[:3]]}
                )
                return True
            else:
                self.log_result(
                    "Web Scraper Intelligence",
                    False,
                    "No suppliers found",
                    {"suppliers_count": 0}
                )
                return False
        except Exception as e:
            self.log_result(
                "Web Scraper Intelligence",
                False,
                f"Scraper error: {str(e)}",
                {"error": str(e)}
            )
            return False
    
    def test_database_connection(self):
        """Test database connection if exists"""
        try:
            import sqlite3
            import os
            
            db_path = "artisan_agents/agents.db"
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                conn.close()
                
                self.log_result(
                    "Database Connection",
                    True,
                    f"Database accessible with {len(tables)} tables",
                    {"tables": [t[0] for t in tables]}
                )
                return True
            else:
                self.log_result(
                    "Database Connection",
                    True,
                    "Database not found (expected for demo)",
                    {"database_path": db_path}
                )
                return True
        except Exception as e:
            self.log_result(
                "Database Connection",
                False,
                f"Database error: {str(e)}",
                {"error": str(e)}
            )
            return False
    
    def run_all_checks(self):
        """Run comprehensive flight check"""
        print("🚀 Starting ArtisanHub Flight Check")
        print("=" * 50)
        print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 50)
        
        # Run all tests
        checks = [
            self.test_flask_server,
            self.test_static_files,
            self.test_ai_analysis_endpoint,
            self.test_intelligent_sourcing_endpoint,
            self.test_artisan_intelligence_engine,
            self.test_web_scraper_intelligence,
            self.test_database_connection,
            self.test_ollama_connection
        ]
        
        for check in checks:
            try:
                check()
                print()  # Add spacing
            except Exception as e:
                self.log_result(
                    f"Test Error: {check.__name__}",
                    False,
                    f"Test failed with exception: {str(e)}"
                )
                print()
        
        # Generate summary
        self.print_summary()
    
    def print_summary(self):
        """Print comprehensive summary"""
        print("=" * 50)
        print("📊 FLIGHT CHECK SUMMARY")
        print("=" * 50)
        
        success_rate = (self.passed_checks / self.total_checks) * 100
        
        print(f"📈 Overall Success Rate: {success_rate:.1f}%")
        print(f"✅ Passed: {self.passed_checks}/{self.total_checks}")
        print(f"❌ Failed: {self.total_checks - self.passed_checks}/{self.total_checks}")
        print()
        
        print("📋 Detailed Results:")
        for test_name, result in self.results.items():
            status_icon = "✅" if result["status"] == "PASS" else "❌"
            print(f"  {status_icon} {test_name}: {result['status']}")
        
        print()
        if success_rate >= 80:
            print("🎉 FLIGHT CHECK PASSED - System is operational!")
        elif success_rate >= 60:
            print("⚠️  FLIGHT CHECK PARTIAL - Some components need attention")
        else:
            print("🚨 FLIGHT CHECK FAILED - System needs immediate attention")
        
        print("=" * 50)
        print(f"⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Export results to file
        self.export_results()
    
    def export_results(self):
        """Export results to JSON file"""
        try:
            report = {
                "flight_check_summary": {
                    "total_checks": self.total_checks,
                    "passed_checks": self.passed_checks,
                    "success_rate": round((self.passed_checks / self.total_checks) * 100, 1),
                    "timestamp": datetime.now().isoformat()
                },
                "detailed_results": self.results
            }
            
            with open("flight_check_report.json", "w") as f:
                json.dump(report, f, indent=2)
            
            print(f"📄 Report exported to: flight_check_report.json")
        except Exception as e:
            print(f"❌ Failed to export report: {str(e)}")

if __name__ == "__main__":
    flight_check = FlightCheckSystem()
    flight_check.run_all_checks()
