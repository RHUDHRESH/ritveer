#!/usr/bin/env python3
"""
AI Thinking Engine - Real-time reasoning and thought visualization
Streams AI reasoning process, shows what the model is thinking about
"""

import asyncio
import json
import requests
from datetime import datetime
from typing import Dict, List, Optional, AsyncGenerator
import time

class ThinkingPhase:
    """Represents a phase of AI thinking"""
    def __init__(self, phase_name: str, description: str):
        self.phase_name = phase_name
        self.description = description
        self.start_time = time.time()
        self.thoughts = []
        self.status = "in_progress"

    def add_thought(self, thought: str, confidence: float = 0.5):
        """Add a thought to this phase"""
        self.thoughts.append({
            "thought": thought,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat()
        })

    def complete(self):
        """Mark phase as complete"""
        self.status = "completed"
        self.duration = time.time() - self.start_time

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "phase_name": self.phase_name,
            "description": self.description,
            "thoughts": self.thoughts,
            "status": self.status,
            "duration": getattr(self, 'duration', None)
        }


class AIThinkingEngine:
    """Manages AI thinking process and reasoning visualization"""

    def __init__(self):
        self.ollama_url = "http://localhost:11434"
        self.current_session = None
        self.thinking_history = []

    def create_session(self, task_description: str) -> Dict:
        """Create a new thinking session"""
        session = {
            "id": f"session_{int(time.time() * 1000)}",
            "task": task_description,
            "start_time": datetime.now().isoformat(),
            "phases": [],
            "current_phase": 0,
            "status": "thinking",
            "overall_progress": 0
        }
        self.current_session = session
        return session

    async def stream_ai_reasoning(
        self,
        prompt: str,
        model: str = "llama3.1:latest"
    ) -> AsyncGenerator[Dict, None]:
        """
        Stream AI reasoning with structured thinking phases.
        Yields intermediate thoughts and reasoning steps.
        """

        # Define thinking phases for various tasks
        phases = [
            ThinkingPhase(
                "Understanding",
                "Analyzing the problem and breaking it down"
            ),
            ThinkingPhase(
                "Research & Context",
                "Gathering relevant information and context"
            ),
            ThinkingPhase(
                "Analysis",
                "Deep analysis of the problem space"
            ),
            ThinkingPhase(
                "Synthesis",
                "Combining insights and forming conclusions"
            ),
            ThinkingPhase(
                "Verification",
                "Double-checking reasoning and validating results"
            )
        ]

        session = self.create_session(prompt)

        for phase in phases:
            session["phases"].append(phase.to_dict())
            session["current_phase"] += 1
            session["overall_progress"] = int((session["current_phase"] / len(phases)) * 100)

            # Yield phase start
            yield {
                "type": "phase_start",
                "phase": phase.to_dict(),
                "session": session,
                "timestamp": datetime.now().isoformat()
            }

            # Stream thoughts during this phase
            async for thought in self._generate_phase_thoughts(prompt, phase, model):
                phase.add_thought(thought["text"], thought.get("confidence", 0.7))
                session["phases"][-1]["thoughts"] = phase.thoughts

                yield {
                    "type": "thought",
                    "phase": phase.phase_name,
                    "thought": thought["text"],
                    "confidence": thought.get("confidence", 0.7),
                    "session": session,
                    "timestamp": datetime.now().isoformat()
                }

            # Phase complete
            phase.complete()
            yield {
                "type": "phase_complete",
                "phase": phase.to_dict(),
                "session": session,
                "timestamp": datetime.now().isoformat()
            }

        # Final result
        session["status"] = "complete"
        yield {
            "type": "session_complete",
            "session": session,
            "timestamp": datetime.now().isoformat()
        }

    async def _generate_phase_thoughts(
        self,
        prompt: str,
        phase: ThinkingPhase,
        model: str
    ) -> AsyncGenerator[Dict, None]:
        """Generate thoughts for a specific phase"""

        phase_prompts = {
            "Understanding": f"""
            You are analyzing this task: "{prompt}"

            In the UNDERSTANDING phase, break down what's being asked:
            1. What is the core problem?
            2. What key elements are involved?
            3. What's the objective?

            Provide 2-3 clear, concise insights. Format as JSON:
            {{"thoughts": ["thought1", "thought2", "thought3"]}}
            """,

            "Research & Context": f"""
            For this task: "{prompt}"

            In the RESEARCH phase, consider:
            1. What background knowledge is relevant?
            2. What similar problems exist?
            3. What patterns apply here?

            Provide 2-3 contextual insights. Format as JSON:
            {{"thoughts": ["thought1", "thought2", "thought3"]}}
            """,

            "Analysis": f"""
            For this task: "{prompt}"

            In the ANALYSIS phase, dig deeper:
            1. What are the constraints?
            2. What are the opportunities?
            3. What's the logical structure?

            Provide 2-3 analytical insights. Format as JSON:
            {{"thoughts": ["thought1", "thought2", "thought3"]}}
            """,

            "Synthesis": f"""
            For this task: "{prompt}"

            In the SYNTHESIS phase, combine insights:
            1. How do these elements work together?
            2. What's the integrated perspective?
            3. What emerges from this combination?

            Provide 2-3 synthesized insights. Format as JSON:
            {{"thoughts": ["thought1", "thought2", "thought3"]}}
            """,

            "Verification": f"""
            For this task: "{prompt}"

            In the VERIFICATION phase, validate:
            1. Does this reasoning hold up?
            2. Are there gaps or inconsistencies?
            3. What's the confidence level?

            Provide 2-3 verification insights. Format as JSON:
            {{"thoughts": ["thought1", "thought2", "thought3"]}}
            """
        }

        phase_prompt = phase_prompts.get(phase.phase_name, phase_prompts["Understanding"])

        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": model,
                    "prompt": phase_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.8,
                        "top_p": 0.9,
                        "max_tokens": 500
                    }
                },
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                response_text = data.get("response", "")

                # Try to parse JSON thoughts
                try:
                    if "{" in response_text and "}" in response_text:
                        start = response_text.find("{")
                        end = response_text.rfind("}") + 1
                        json_str = response_text[start:end]
                        parsed = json.loads(json_str)
                        thoughts = parsed.get("thoughts", [response_text])
                    else:
                        thoughts = [response_text]
                except:
                    thoughts = [response_text]

                # Yield each thought with confidence
                for i, thought in enumerate(thoughts):
                    confidence = 0.9 - (i * 0.1)  # Decrease confidence for each thought
                    yield {
                        "text": thought.strip(),
                        "confidence": max(0.3, confidence)
                    }
                    await asyncio.sleep(0.1)  # Small delay for visual effect

            else:
                yield {
                    "text": f"Error querying model: HTTP {response.status_code}",
                    "confidence": 0.5
                }

        except Exception as e:
            yield {
                "text": f"Error: {str(e)}",
                "confidence": 0.3
            }

    async def analyze_with_thinking(
        self,
        description: str,
        location: str = "",
        model: str = "llama3.1:latest"
    ) -> Dict:
        """
        Perform analysis while streaming thinking process.
        Collects all thoughts and returns complete analysis.
        """

        prompt = f"""
        Analyze this artisan description and provide insights:

        Description: "{description}"
        Location: "{location}"

        Provide analysis in JSON format:
        {{
            "artisan_type": "type",
            "specialization": "specialty",
            "skill_level": "level",
            "business_potential": "potential",
            "recommended_actions": ["action1", "action2"],
            "target_market": "market",
            "estimated_monthly_income": "income",
            "growth_opportunities": ["opportunity1"]
        }}
        """

        session = self.create_session(f"Analyzing artisan work: {description}")
        all_thoughts = []

        # Stream the reasoning process
        async for event in self.stream_ai_reasoning(prompt, model):
            if event["type"] == "thought":
                all_thoughts.append(event["thought"])

        # Get final analysis
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "max_tokens": 1000
                    }
                },
                timeout=30
            )

            if response.status_code == 200:
                response_text = response.json().get("response", "")
                analysis = self._parse_analysis(response_text)
                analysis["thinking_process"] = all_thoughts
                return analysis
        except Exception as e:
            print(f"Analysis error: {e}")

        return {
            "error": "Analysis failed",
            "thinking_process": all_thoughts
        }

    def _parse_analysis(self, response_text: str) -> Dict:
        """Parse AI response to extract analysis"""
        try:
            if "{" in response_text and "}" in response_text:
                start = response_text.find("{")
                end = response_text.rfind("}") + 1
                json_str = response_text[start:end]
                return json.loads(json_str)
        except:
            pass

        return {
            "artisan_type": "unknown",
            "specialization": "general",
            "skill_level": "intermediate",
            "business_potential": "medium",
            "recommended_actions": ["expand_skills"],
            "target_market": "local",
            "estimated_monthly_income": "₹15,000-25,000",
            "growth_opportunities": ["online_sales"]
        }

    def get_thinking_history(self) -> List[Dict]:
        """Get history of thinking sessions"""
        return self.thinking_history


# Create global instance
ai_thinking = AIThinkingEngine()


def create_thinking_routes(app):
    """Add AI thinking routes to Flask app"""
    from flask import jsonify, request, Response
    import threading

    @app.route('/api/analyze-with-thinking', methods=['GET', 'POST'])
    def analyze_with_thinking_endpoint():
        """Analyze with real-time thinking stream"""

        if request.method == 'GET':
            description = request.args.get('description', '')
            location = request.args.get('location', '')
        else:
            data = request.get_json()
            description = data.get('description', '')
            location = data.get('location', '')

        if not description or len(description) < 10:
            return jsonify({
                'success': False,
                'error': 'Please describe your work in detail'
            }), 400

        def generate():
            """Generator for streaming response"""
            try:
                # Send initial session info
                session = ai_thinking.create_session(f"Analyzing: {description}")
                yield f"data: {json.dumps({'type': 'session_start', 'session': session})}\n\n"

                # Define phases to generate thoughts for
                phases_data = [
                    {
                        "name": "Understanding",
                        "description": "Analyzing the problem and breaking it down",
                        "prompt": f"""Analyze this artisan description and identify key aspects:

Description: "{description}"
Location: "{location}"

What is the core understanding here? List 3 key insights about this artisan work.
Provide ONLY raw thoughts, one per line, no JSON formatting."""
                    },
                    {
                        "name": "Research & Context",
                        "description": "Gathering relevant information and context",
                        "prompt": f"""For an artisan working with: "{description}"

What relevant market context and background knowledge applies? List 3 contextual insights.
Provide ONLY raw thoughts, one per line, no JSON formatting."""
                    },
                    {
                        "name": "Analysis",
                        "description": "Deep analysis of the problem space",
                        "prompt": f"""Given this artisan work: "{description}"

What constraints, opportunities and logical structures exist? List 3 analytical insights.
Provide ONLY raw thoughts, one per line, no JSON formatting."""
                    },
                    {
                        "name": "Synthesis",
                        "description": "Combining insights and forming conclusions",
                        "prompt": f"""For an artisan with: "{description}"

How do elements work together? What integrated perspective emerges? List 3 synthesis insights.
Provide ONLY raw thoughts, one per line, no JSON formatting."""
                    },
                    {
                        "name": "Verification",
                        "description": "Double-checking reasoning and validating results",
                        "prompt": f"""For the artisan described as: "{description}"

Does the reasoning hold? Any gaps or inconsistencies? List 3 verification points.
Provide ONLY raw thoughts, one per line, no JSON formatting."""
                    }
                ]

                # Process each phase
                for phase_info in phases_data:
                    phase_name = phase_info["name"]

                    # Send phase start
                    phase_data = {
                        "phase_name": phase_name,
                        "description": phase_info["description"],
                        "thoughts": [],
                        "status": "in_progress"
                    }
                    yield f"data: {json.dumps({'type': 'phase_start', 'phase': phase_data})}\n\n"

                    # Query Ollama for thoughts
                    try:
                        response = requests.post(
                            f"{ai_thinking.ollama_url}/api/generate",
                            json={
                                "model": "llama3.1:latest",
                                "prompt": phase_info["prompt"],
                                "stream": False,
                                "options": {
                                    "temperature": 0.8,
                                    "top_p": 0.9,
                                    "max_tokens": 300
                                }
                            },
                            timeout=30
                        )

                        if response.status_code == 200:
                            response_text = response.json().get("response", "")
                            # Split by lines and filter empty ones
                            thoughts = [t.strip() for t in response_text.split('\n') if t.strip()]

                            # Yield individual thoughts
                            for i, thought in enumerate(thoughts[:4]):  # Limit to 4 thoughts per phase
                                confidence = 0.95 - (i * 0.15)
                                yield f"data: {json.dumps({
                                    'type': 'thought',
                                    'phase': phase_name,
                                    'thought': thought,
                                    'confidence': max(0.5, confidence)
                                })}\n\n"

                        else:
                            yield f"data: {json.dumps({
                                'type': 'thought',
                                'phase': phase_name,
                                'thought': f'(Ollama error: HTTP {response.status_code})',
                                'confidence': 0.4
                            })}\n\n"

                    except Exception as e:
                        yield f"data: {json.dumps({
                            'type': 'thought',
                            'phase': phase_name,
                            'thought': f'(Connection error: {str(e)[:50]})',
                            'confidence': 0.3
                        })}\n\n"

                    # Send phase complete
                    yield f"data: {json.dumps({
                        'type': 'phase_complete',
                        'phase': phase_name
                    })}\n\n"

                # Send session complete
                yield f"data: {json.dumps({
                    'type': 'session_complete',
                    'message': 'Analysis thinking complete'
                })}\n\n"

            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        return Response(
            generate(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'
            }
        )

    @app.route('/api/thinking-status', methods=['GET'])
    def thinking_status():
        """Get current thinking session status"""
        if ai_thinking.current_session:
            return jsonify({
                'success': True,
                'session': ai_thinking.current_session
            })
        return jsonify({
            'success': False,
            'message': 'No active thinking session'
        }), 404

    @app.route('/api/thinking-history', methods=['GET'])
    def thinking_history():
        """Get history of thinking sessions"""
        return jsonify({
            'success': True,
            'history': ai_thinking.get_thinking_history()
        })
