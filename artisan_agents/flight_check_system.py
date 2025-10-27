#!/usr/bin/env python3
"""
Flight Check System - System Operations Monitor
Monitors Ollama AI agents, Flask app health, database connections, and all system operations
"""

from flask import Flask, jsonify, request
from datetime import datetime, timedelta
import json
import requests
import time
import threading
import psutil
import socket
from typing import Dict, List, Optional
import sqlite3
import os

class FlightCheckSystem:
    """Comprehensive system health monitoring for ArtisanHub"""

    def __init__(self):
        self.ollama_url = "http://localhost:11434"
        self.flask_url = "http://localhost:5000"
        self.db_path = "flight_checks.db"
        self.checks_interval = 60  # Check every 60 seconds
        self.health_history = []
        self.alerts = []
        self.status_thresholds = {
            'cpu_usage': 80,
            'memory_usage': 85,
            'disk_usage': 90,
            'response_time': 5000  # milliseconds
        }
        self._init_database()
        self._start_monitoring()

    def _init_database(self):
        """Initialize SQLite database for storing check history"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Flight checks history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS flight_checks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    system_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    details TEXT NOT NULL,
                    response_time INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # System alerts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    alert_level TEXT NOT NULL,
                    component TEXT NOT NULL,
                    message TEXT NOT NULL,
                    value REAL,
                    threshold REAL,
                    resolved INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # System metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    cpu_usage REAL,
                    memory_usage REAL,
                    disk_usage REAL,
                    ollama_status TEXT,
                    flask_status TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[FlightCheck][ERROR] Database init failed: {e}")

    def _start_monitoring(self):
        """Start background monitoring thread"""
        monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        monitor_thread.start()

    def _monitoring_loop(self):
        """Background monitoring loop"""
        while True:
            try:
                self.perform_flight_check()
                time.sleep(self.checks_interval)
            except Exception as e:
                print(f"[FlightCheck][ERROR] Monitoring loop error: {e}")
                time.sleep(5)

    def perform_flight_check(self) -> Dict:
        """Perform comprehensive flight check of all systems"""
        timestamp = datetime.now().isoformat()

        checks = {
            'timestamp': timestamp,
            'overall_status': 'GREEN',
            'systems': {}
        }

        # Check Ollama AI System
        ollama_check = self._check_ollama()
        checks['systems']['ollama'] = ollama_check
        if ollama_check['status'] != 'HEALTHY':
            checks['overall_status'] = 'RED' if ollama_check['status'] == 'CRITICAL' else 'YELLOW'

        # Check Flask Application
        flask_check = self._check_flask()
        checks['systems']['flask'] = flask_check
        if flask_check['status'] != 'HEALTHY':
            checks['overall_status'] = 'RED' if flask_check['status'] == 'CRITICAL' else 'YELLOW'

        # Check System Resources
        resource_check = self._check_system_resources()
        checks['systems']['resources'] = resource_check
        if resource_check['status'] != 'HEALTHY':
            checks['overall_status'] = 'RED' if resource_check['status'] == 'CRITICAL' else 'YELLOW'

        # Check Database
        db_check = self._check_database()
        checks['systems']['database'] = db_check
        if db_check['status'] != 'HEALTHY':
            checks['overall_status'] = 'RED' if db_check['status'] == 'CRITICAL' else 'YELLOW'

        # Check Network
        network_check = self._check_network()
        checks['systems']['network'] = network_check
        if network_check['status'] != 'HEALTHY':
            checks['overall_status'] = 'RED' if network_check['status'] == 'CRITICAL' else 'YELLOW'

        # Store in history
        self._store_check(checks)
        self.health_history.append(checks)

        # Keep only last 100 checks in memory
        if len(self.health_history) > 100:
            self.health_history = self.health_history[-100:]

        return checks

    def _check_ollama(self) -> Dict:
        """Check Ollama AI service health"""
        try:
            start_time = time.time()
            response = requests.get(
                f"{self.ollama_url}/api/tags",
                timeout=5
            )
            response_time = int((time.time() - start_time) * 1000)

            if response.status_code == 200:
                data = response.json()
                models = data.get('models', [])
                return {
                    'status': 'HEALTHY',
                    'service': 'Ollama AI Engine',
                    'models_available': len(models),
                    'models': [m.get('name') for m in models],
                    'response_time_ms': response_time,
                    'message': f'{len(models)} models ready'
                }
            else:
                return {
                    'status': 'DEGRADED',
                    'service': 'Ollama AI Engine',
                    'error': f'HTTP {response.status_code}',
                    'response_time_ms': response_time
                }
        except requests.Timeout:
            return {
                'status': 'CRITICAL',
                'service': 'Ollama AI Engine',
                'error': 'Service timeout',
                'message': 'Ollama service not responding'
            }
        except Exception as e:
            return {
                'status': 'CRITICAL',
                'service': 'Ollama AI Engine',
                'error': str(e),
                'message': 'Unable to connect to Ollama'
            }

    def _check_flask(self) -> Dict:
        """Check Flask application health"""
        try:
            start_time = time.time()
            response = requests.get(
                f"{self.flask_url}/api/health",
                timeout=5
            )
            response_time = int((time.time() - start_time) * 1000)

            if response.status_code == 200:
                data = response.json()
                return {
                    'status': 'HEALTHY',
                    'service': 'Flask Web App',
                    'port': 5000,
                    'response_time_ms': response_time,
                    'details': data,
                    'message': 'Application running normally'
                }
            else:
                return {
                    'status': 'DEGRADED',
                    'service': 'Flask Web App',
                    'port': 5000,
                    'error': f'HTTP {response.status_code}',
                    'response_time_ms': response_time
                }
        except requests.Timeout:
            return {
                'status': 'CRITICAL',
                'service': 'Flask Web App',
                'port': 5000,
                'error': 'Service timeout',
                'message': 'Flask application not responding'
            }
        except Exception as e:
            return {
                'status': 'CRITICAL',
                'service': 'Flask Web App',
                'port': 5000,
                'error': str(e),
                'message': 'Unable to connect to Flask app'
            }

    def _check_system_resources(self) -> Dict:
        """Check system resource utilization"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            status = 'HEALTHY'
            issues = []

            if cpu_percent > self.status_thresholds['cpu_usage']:
                status = 'DEGRADED'
                issues.append(f"High CPU usage: {cpu_percent}%")

            if memory.percent > self.status_thresholds['memory_usage']:
                status = 'DEGRADED'
                issues.append(f"High memory usage: {memory.percent}%")

            if disk.percent > self.status_thresholds['disk_usage']:
                status = 'CRITICAL'
                issues.append(f"Critical disk usage: {disk.percent}%")

            return {
                'status': status,
                'service': 'System Resources',
                'cpu': {
                    'percent': cpu_percent,
                    'threshold': self.status_thresholds['cpu_usage']
                },
                'memory': {
                    'percent': memory.percent,
                    'used_gb': round(memory.used / (1024**3), 2),
                    'total_gb': round(memory.total / (1024**3), 2),
                    'threshold': self.status_thresholds['memory_usage']
                },
                'disk': {
                    'percent': disk.percent,
                    'used_gb': round(disk.used / (1024**3), 2),
                    'total_gb': round(disk.total / (1024**3), 2),
                    'free_gb': round(disk.free / (1024**3), 2),
                    'threshold': self.status_thresholds['disk_usage']
                },
                'issues': issues if issues else ['None']
            }
        except Exception as e:
            return {
                'status': 'UNKNOWN',
                'service': 'System Resources',
                'error': str(e)
            }

    def _check_database(self) -> Dict:
        """Check database connectivity and status"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Check table counts
            cursor.execute("SELECT COUNT(*) FROM flight_checks")
            checks_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM system_alerts")
            alerts_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM system_metrics")
            metrics_count = cursor.fetchone()[0]

            conn.close()

            return {
                'status': 'HEALTHY',
                'service': 'SQLite Database',
                'database': self.db_path,
                'tables': {
                    'flight_checks': checks_count,
                    'system_alerts': alerts_count,
                    'system_metrics': metrics_count
                },
                'message': 'Database operational'
            }
        except Exception as e:
            return {
                'status': 'CRITICAL',
                'service': 'SQLite Database',
                'error': str(e),
                'message': 'Database connection failed'
            }

    def _check_network(self) -> Dict:
        """Check network connectivity"""
        try:
            # Check internet connectivity
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            internet = 'ONLINE'
        except:
            internet = 'OFFLINE'

        try:
            # Check localhost connectivity
            socket.create_connection(("127.0.0.1", 5000), timeout=2)
            localhost = 'ONLINE'
        except:
            localhost = 'OFFLINE'

        status = 'HEALTHY' if localhost == 'ONLINE' else 'DEGRADED'

        return {
            'status': status,
            'service': 'Network',
            'localhost': localhost,
            'internet': internet,
            'message': f'Local network: {localhost}, Internet: {internet}'
        }

    def _store_check(self, check_data: Dict):
        """Store check results in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            timestamp = check_data['timestamp']
            details = json.dumps(check_data['systems'])

            cursor.execute('''
                INSERT INTO flight_checks (timestamp, system_name, status, details, response_time)
                VALUES (?, ?, ?, ?, ?)
            ''', (timestamp, 'SYSTEM', check_data['overall_status'], details, 0))

            # Also store metrics
            systems = check_data['systems']
            cpu = systems.get('resources', {}).get('cpu', {}).get('percent', 0)
            memory = systems.get('resources', {}).get('memory', {}).get('percent', 0)
            disk = systems.get('resources', {}).get('disk', {}).get('percent', 0)
            ollama_status = systems.get('ollama', {}).get('status', 'UNKNOWN')
            flask_status = systems.get('flask', {}).get('status', 'UNKNOWN')

            cursor.execute('''
                INSERT INTO system_metrics (timestamp, cpu_usage, memory_usage, disk_usage, ollama_status, flask_status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (timestamp, cpu, memory, disk, ollama_status, flask_status))

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[FlightCheck][ERROR] Failed to store check: {e}")

    def get_latest_check(self) -> Optional[Dict]:
        """Get the latest flight check"""
        if self.health_history:
            return self.health_history[-1]
        return None

    def get_check_history(self, limit: int = 50) -> List[Dict]:
        """Get check history"""
        return self.health_history[-limit:]

    def get_system_status_summary(self) -> Dict:
        """Get overall system status summary"""
        latest_check = self.get_latest_check()
        if not latest_check:
            return {'status': 'UNKNOWN', 'message': 'No checks performed yet'}

        systems = latest_check['systems']
        summary = {
            'timestamp': latest_check['timestamp'],
            'overall_status': latest_check['overall_status'],
            'systems_healthy': sum(1 for s in systems.values() if s.get('status') == 'HEALTHY'),
            'systems_degraded': sum(1 for s in systems.values() if s.get('status') == 'DEGRADED'),
            'systems_critical': sum(1 for s in systems.values() if s.get('status') == 'CRITICAL'),
            'total_systems': len(systems),
            'system_statuses': {
                name: {
                    'status': data.get('status'),
                    'service': data.get('service')
                }
                for name, data in systems.items()
            }
        }
        return summary


# Initialize flight check system
flight_check = FlightCheckSystem()


def create_flight_check_routes(app: Flask):
    """Add flight check routes to Flask app"""

    @app.route('/api/flight-check', methods=['GET'])
    def get_flight_check():
        """Get latest flight check"""
        check = flight_check.get_latest_check()
        if check:
            return jsonify({
                'success': True,
                'data': check
            })
        else:
            return jsonify({
                'success': False,
                'message': 'No flight checks performed yet'
            }), 404

    @app.route('/api/flight-check-history', methods=['GET'])
    def get_flight_check_history():
        """Get flight check history"""
        limit = request.args.get('limit', 50, type=int)
        history = flight_check.get_check_history(limit)
        return jsonify({
            'success': True,
            'total': len(history),
            'data': history
        })

    @app.route('/api/system-status', methods=['GET'])
    def get_system_status():
        """Get system status summary"""
        summary = flight_check.get_system_status_summary()
        return jsonify({
            'success': True,
            'data': summary
        })

    @app.route('/api/perform-flight-check', methods=['POST'])
    def perform_flight_check():
        """Manually trigger a flight check"""
        check = flight_check.perform_flight_check()
        return jsonify({
            'success': True,
            'data': check
        })

    @app.route('/api/flight-check-status', methods=['GET'])
    def flight_check_status():
        """Get continuous flight check status (for monitoring dashboard)"""
        check = flight_check.get_latest_check()
        if not check:
            return jsonify({'status': 'INITIALIZING'}), 202

        return jsonify({
            'status': check['overall_status'],
            'timestamp': check['timestamp'],
            'systems': check['systems']
        })
