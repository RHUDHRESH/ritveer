# 🏗️ System Architecture - AI Thinking System

## High-Level Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     USER BROWSER                                 │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  pro_dashboard_enhanced.html                             │   │
│  │  ────────────────────────────────────────────────────   │   │
│  │  • Input form (description, location)                   │   │
│  │  • Real-time thinking display                           │   │
│  │  • Analysis results section                             │   │
│  └──────────────────────────────────────────────────────────┘   │
│           ▲                                        ▲              │
│           │                                        │              │
│           │ EventSource Stream                     │ Analysis API │
│           │ (text/event-stream)                    │              │
└───────────┼────────────────────────────────────────┼──────────────┘
            │                                        │
            │                                        │
┌───────────▼────────────────────────────────────────▼──────────────┐
│                      FLASK APPLICATION (localhost:5000)            │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  /api/analyze-with-thinking (GET)                          │  │
│  │  ───────────────────────────────────────────────────────   │  │
│  │  • Receives: description + location                        │  │
│  │  • Streams: 5 thinking phases                              │  │
│  │  • Format: Server-Sent Events (SSE)                        │  │
│  │  • Returns: Phases + Thoughts + Confidence                 │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                           ▲                                        │
│                           │                                        │
│  ┌─────────────────────────┴──────────────────────────────────┐  │
│  │  ai_thinking_engine.py                                     │  │
│  │  ──────────────────────────────────────────────────────   │  │
│  │  • ThinkingPhase class                                     │  │
│  │  • AIThinkingEngine class                                  │  │
│  │  • create_thinking_routes(app)                             │  │
│  │                                                             │  │
│  │  For each of 5 phases:                                     │  │
│  │  1. Generate phase-specific prompt                         │  │
│  │  2. Query Ollama AI model                                  │  │
│  │  3. Parse response into thoughts                           │  │
│  │  4. Stream each thought with confidence                    │  │
│  │  5. Mark phase as complete                                 │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                           ▲                                        │
│                           │                                        │
│  ┌─────────────────────────┴──────────────────────────────────┐  │
│  │  /api/analyze-artisan (POST)                               │  │
│  │  ──────────────────────────────────────────────────────   │  │
│  │  • Gets called after thinking is complete                  │  │
│  │  • Returns actual analysis results                         │  │
│  │  • Includes: artisan_type, skill_level, income, etc       │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                           ▲
                           │
                Ollama API (localhost:11434)
                           │
┌─────────────────────────▼────────────────────────────────────────┐
│                   OLLAMA AI ENGINE                                │
│  ─────────────────────────────────────────────────────────────  │
│  • Model: llama3.1:latest                                        │
│  • Temperature: 0.8 (creative but consistent)                    │
│  • Max tokens: 300 per phase                                     │
│  • Timeout: 30 seconds                                           │
│                                                                   │
│  Processes 5 phases of prompts:                                  │
│  1. Understanding - "What's the core problem?"                   │
│  2. Research - "What context applies?"                           │
│  3. Analysis - "What are constraints & opportunities?"           │
│  4. Synthesis - "How do elements work together?"                 │
│  5. Verification - "Does reasoning hold?"                        │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow: Step by Step

```
1. USER SUBMITS ANALYSIS
   ├─ Description: "I'm a potter with 15 years experience"
   ├─ Location: "Delhi"
   └─ Browser: addEventListener on EventSource

2. BROWSER -> FLASK
   GET /api/analyze-with-thinking?description=...&location=...

3. FLASK -> STREAMING RESPONSE
   Yields SSE formatted events:

   data: {"type": "session_start", "session": {...}}

   data: {"type": "phase_start", "phase": {...}}

   data: {"type": "thought", "phase": "Understanding",
          "thought": "Master potter...", "confidence": 0.95}

   data: {"type": "thought", "phase": "Understanding",
          "thought": "Traditional techniques...", "confidence": 0.80}

   data: {"type": "phase_complete", "phase": "Understanding"}

   ... (repeats for all 5 phases)

   data: {"type": "session_complete", "message": "Complete"}

4. BROWSER RECEIVES EVENTS
   Each event triggers JavaScript handler:
   - phase_start: Create phase card, show description
   - thought: Add thought item, animate in
   - phase_complete: Mark phase as done, dim color
   - session_complete: Close connection, enable analysis

5. AFTER THINKING COMPLETE
   Browser calls: POST /api/analyze-artisan
   Gets final analysis JSON with:
   - artisan_type
   - skill_level
   - business_potential
   - estimated_monthly_income
   - recommended_actions

6. DISPLAY RESULTS
   Populate results grid with:
   - Cards showing each result
   - Opportunities/recommendations
   - Call to action buttons
```

## Thinking Phase Details

### Phase 1: Understanding (3-5 seconds)
```
Prompt: "What is the core understanding here? List 3 key insights"
Response:
  - Master potter with 15 years experience
  - Hand-thrown pottery specialization
  - Traditional wheel throwing techniques

Thoughts Generated: 3-4 thoughts with 95%, 80%, 75% confidence
```

### Phase 2: Research & Context (3-5 seconds)
```
Prompt: "What relevant market context applies? List 3 contextual insights"
Response:
  - Pottery market shows strong demand
  - Craft fairs are primary sales channel
  - Online presence critical for growth

Thoughts Generated: 3-4 thoughts with decreasing confidence
```

### Phase 3: Analysis (3-5 seconds)
```
Prompt: "What constraints and opportunities exist? List 3 analytical insights"
Response:
  - Limited production capacity
  - Premium positioning available
  - Direct-to-consumer potential

Thoughts Generated: 3-4 thoughts
```

### Phase 4: Synthesis (3-5 seconds)
```
Prompt: "How do elements work together? List 3 synthesis insights"
Response:
  - Combine quality + storytelling
  - Leverage traditional + modern appeal
  - Multi-channel sales strategy

Thoughts Generated: 3-4 thoughts
```

### Phase 5: Verification (3-5 seconds)
```
Prompt: "Does reasoning hold? List 3 verification points"
Response:
  - Strategy aligns with market trends
  - Leverages existing strengths
  - Addresses growth limitations

Thoughts Generated: 3-4 thoughts
```

## Technical Stack

### Frontend
```
HTML5
├─ Canvas-ready for future visualizations
└─ EventSource API (native browser)

CSS3
├─ Gradients and animations
├─ Responsive grid layout
└─ Modern design with Glassmorphism

JavaScript (ES6+)
├─ EventSource for streaming
├─ Fetch API for analysis
├─ Dynamic DOM manipulation
└─ Real-time UI updates
```

### Backend
```
Python 3.8+
├─ Flask (web framework)
├─ Requests (HTTP client)
└─ JSON (data serialization)

flask_cors (CORS support)
psutil (system monitoring)
sqlite3 (database)
```

### External Services
```
Ollama (localhost:11434)
├─ llama3.1:latest model
├─ 30 second timeout
└─ Non-blocking async
```

## Event-Driven Architecture

```
Browser                           Flask                        Ollama
  │                                │                             │
  ├──── GET /api/analyze-with ────>│                             │
  │                                │                             │
  │<──── 200 OK (SSE Stream) ──────┤                             │
  │                                │                             │
  │<─ "data: phase_start" ─────────┤                             │
  │  (Understanding)               │                             │
  │                                ├─ POST /api/generate ─────>│
  │                                │ (Understanding phase)       │
  │                                │                      (wait...|
  │                                │ <──── response ─────────────┤
  │                                │ Parse into thoughts        │
  │<─ "data: thought" ─────────────┤                             │
  │  [95%] Master potter...        │                             │
  │                                │                             │
  │<─ "data: thought" ─────────────┤                             │
  │  [80%] Ceramic specialization  │                             │
  │                                │                             │
  │<─ "data: phase_complete" ──────┤                             │
  │                                │                             │
  │  (repeat for 4 more phases)    │                             │
  │                                │                             │
  │<─ "data: session_complete" ────┤                             │
  │                                │                             │
  ├──── POST /api/analyze-artisan->│                             │
  │                                ├─ POST /api/generate ─────>│
  │                                │ (Analysis)                  │
  │                                │                     (wait...)
  │<── {"artisan_type": ...} ──────┤ <───────── response ────────┤
  │                                │                             │
  Display Results                  │                             │
```

## Files & Responsibilities

```
Project Root/
├── real_intelligent_app.py          (Main Flask app)
│   ├─ Imports thinking routes
│   ├─ Imports flight check routes
│   ├─ Defines RealArtisanIntelligence class
│   └─ Starts server on :5000
│
├── ai_thinking_engine.py            (AI Thinking System)
│   ├─ ThinkingPhase class
│   ├─ AIThinkingEngine class
│   ├─ create_thinking_routes(app)
│   └─ /api/analyze-with-thinking endpoint
│
├── flight_check_system.py           (System Monitoring)
│   ├─ FlightCheckSystem class
│   ├─ create_flight_check_routes(app)
│   └─ /api/flight-check endpoints
│
├── pro_dashboard_enhanced.html      (Main UI with thinking)
│   ├─ Input form
│   ├─ Real-time thinking display
│   ├─ Results section
│   └─ EventSource listener
│
├── flight_check_dashboard.html      (System monitoring UI)
│   ├─ Status indicators
│   ├─ Resource graphs
│   └─ History table
│
└── flight_checks.db                 (SQLite database)
    ├─ flight_checks table
    ├─ system_alerts table
    └─ system_metrics table
```

## Response Headers for Streaming

```
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
X-Accel-Buffering: no
Transfer-Encoding: chunked
Connection: keep-alive
```

These headers ensure:
- Browser doesn't cache the stream
- Proxy doesn't buffer events
- Connection stays open
- Events stream in real-time

## Performance Characteristics

```
Phase 1:    3-5 seconds  (Understanding)
Phase 2:    3-5 seconds  (Research)
Phase 3:    3-5 seconds  (Analysis)
Phase 4:    3-5 seconds  (Synthesis)
Phase 5:    3-5 seconds  (Verification)
─────────────────────────────────────
Total:     15-25 seconds (depending on Ollama speed)

Per Phase:
- Ollama call: 2-4 seconds
- Response parsing: <100ms
- Streaming: <500ms per thought
- Browser rendering: <50ms per thought
```

## Scalability Notes

### Current Design (Single User)
- One request per user
- Ollama blocks per request
- Memory: ~100MB per analysis
- CPU: 1-2 cores during analysis

### For Multiple Users
Consider:
- Ollama queue system
- Request rate limiting
- Connection pooling
- WebSocket instead of SSE
- Caching responses
- Load balancing

---

**Architecture designed for clarity and extensibility!**

Make AI thinking visible and understandable! 🧠✨
