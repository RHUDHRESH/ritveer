# KARIGAR System Architecture

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                      Client Layer                                │
│                  (Browser / External API)                        │
└─────────────────────────────┬──────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                   FastAPI Backend (Port 8000)                    │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              REST API Endpoints                            │ │
│  │  POST /api/artisan/onboard                                 │ │
│  │  POST /api/order/create                                    │ │
│  │  GET  /api/workflows                                       │ │
│  │  POST /api/tools/{name}/execute                            │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────┬──────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│              Workflow Orchestrator                               │
│  Coordinates agent workflows and state flow                      │
└─────────────────────────────┬──────────────────────────────────┘
                              │
                ┌─────────────┼─────────────┐
                ▼             ▼             ▼
           ┌────────┐    ┌────────┐    ┌────────┐
           │ Agent  │    │ Agent  │    │ Agent  │
           │ Chain  │    │ Chain  │    │ Chain  │
           └────────┘    └────────┘    └────────┘
                │             │             │
                └─────────────┼─────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                      Tool Registry (15 Tools)                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Supplier Tools │ Payment Tools │ Document Tools │Research│   │
│  │ • Search       │ • Links       │ • PDF Gen      │• Market│   │
│  │ • Quotes       │ • Status      │ • QR Codes     │• Scrape│   │
│  │ • Validate     │ • Refund      │ • Reports      │• Trends│   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────┬──────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                      SQLite Database                             │
│  Artisans │ Orders │ Suppliers │ Ledger │ Inventory │ Stores    │
└──────────────────────────────────────────────────────────────────┘
```

## Agent Workflow Architecture

### Artisan Onboarding Workflow

```
┌────────────────────────────────────────────────────────────────┐
│  START: Artisan wants to join platform                         │
└────────────────────┬───────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────────┐
│  IntakeAgent.think()                                            │
│  • Validate profile (name, craft, location, experience)        │
│  • Assess skill level (1-8 years → beginner/expert)            │
│  • Score business readiness (portfolio, website, social)       │
└────────────────────┬───────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────────┐
│  IntakeAgent.act()                                              │
│  • Market research for craft type                              │
│  • Competitor analysis                                         │
│  • Trend detection                                             │
│  • Create business profile                                     │
└────────────────────┬───────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────────┐
│  IntakeAgent.observe()                                          │
│  • Store artisan assessment in memory                          │
│  • Remember market research                                    │
│  • Prepare state for SupplierAgent                            │
└────────────────────┬───────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────────┐
│  SupplierAgent.think()                                          │
│  • Analyze material needs                                      │
│  • Determine sourcing strategy                                 │
│  • Prioritize cost vs speed vs quality                        │
└────────────────────┬───────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────────┐
│  SupplierAgent.act()                                            │
│  • Search for suppliers (material, location, quantity)         │
│  • Generate quotes from top suppliers                          │
│  • Validate supplier credibility                               │
│  • Compare quotes and select best                              │
└────────────────────┬───────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────────┐
│  SupplierAgent.observe()                                        │
│  • Store supplier information                                  │
│  • Remember best quotes                                        │
│  • Update state for next agent                                │
└────────────────────┬───────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────────┐
│  RESULT: Complete artisan profile with:                        │
│  • Market analysis                                             │
│  • Supplier quotes                                             │
│  • Business recommendations                                    │
│  • Revenue projections                                         │
└────────────────────────────────────────────────────────────────┘
```

## Agent State Flow

```
Initial State
    │ {artisan_data: {...}}
    ▼
IntakeAgent
    │ Enriches state with:
    │ • artisan_profile
    │ • market_analysis
    │ • competitive_position
    ▼
SupplierAgent
    │ Enriches state with:
    │ • suppliers_identified
    │ • supplier_results
    │ • best_quote
    ▼
CommitAgent
    │ Enriches state with:
    │ • order_committed
    │ • production_timeline
    │ • quality_checklist
    ▼
SalesAgent
    │ Enriches state with:
    │ • sales_setup_complete
    │ • product_listings
    │ • customer_segments
    ▼
Final State (Complete Profile)
```

## Tool Execution Flow

```
Agent.act() calls tool
    │
    ▼
Tool Registry
    │
    ▼
Tool.execute(params)
    ├─ Validate parameters ✓
    ├─ Execute logic
    ├─ Handle errors
    └─ Return ToolResult
    │
    ▼
Agent.observe()
    ├─ Process result
    ├─ Update memory
    └─ Enrich state
    │
    ▼
Result returned to workflow
```

## Database Schema Relationships

```
┌──────────────────┐
│    Artisan       │
├──────────────────┤
│ id (PK)          │
│ name             │
│ craft_type       │
│ location         │
│ skill_level      │
└────────┬─────────┘
         │ 1:N
         ├──────────────┬──────────────┬──────────────┐
         │              │              │              │
         ▼              ▼              ▼              ▼
    ┌─────────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐
    │ Materials   │ │  Orders  │ │ Suppliers│ │ MicroStore │
    ├─────────────┤ ├──────────┤ ├──────────┤ ├────────────┤
    │ material_id │ │ order_id │ │ quote_id │ │ store_id   │
    │ artisan_id  │ │ artisan_ │ │ artisan_ │ │ artisan_id │
    │ name        │ │ id       │ │ id       │ │ store_name │
    │ quantity    │ │ customer │ │ supplier │ │ products   │
    └─────────────┘ │ details  │ │ details  │ └────────────┘
                    │ timeline │ │ quotes   │
                    └──────┬───┘ └──────────┘
                           │ 1:N
                           ▼
                    ┌──────────────┐
                    │   Ledger     │
                    ├──────────────┤
                    │ entry_id     │
                    │ artisan_id   │
                    │ order_id     │
                    │ amount       │
                    │ type         │
                    └──────────────┘
```

## Workflow State Management

```
AgentState
├── agent_id: str
├── agent_role: AgentRole
├── session_id: str
├── artisan_id: str
├── context: Dict          # Workflow-specific data
│   ├── artisan_data
│   ├── artisan_profile
│   ├── market_analysis
│   ├── suppliers_identified
│   ├── order_data
│   └── ...
├── history: List          # All actions taken
│   └── [{"agent": "...", "action": {...}, "timestamp": "..."}]
├── decisions: List        # All decisions made
│   └── [{"agent": "...", "decision": {...}, "timestamp": "..."}]
├── started_at: datetime
└── updated_at: datetime
```

## Agent Memory Hierarchy

```
Agent Memory
├── Short-term (Current Workflow)
│   └── Decisions and actions in current session
├── Medium-term (Session Memory)
│   ├── Artisan profiles
│   ├── Supplier information
│   └── Quote history
└── Long-term (Persistent Memory - ChromaDB)
    ├── Market patterns
    ├── Supplier ratings
    ├── Customer preferences
    └── Learned rules
```

## API Request-Response Flow

```
HTTP Request
    │
    ▼
FastAPI Endpoint
    │
    ├─ Parse and validate request
    │
    ▼
Workflow Orchestrator
    │
    ├─ Create initial state
    │
    ▼
Execute Agent Sequence
    │
    ├─ Agent 1 (think → act → observe)
    ├─ Agent 2 (think → act → observe)
    ├─ Agent 3 (think → act → observe)
    │
    ▼
Collect Results
    │
    ├─ Final state
    ├─ Execution history
    ├─ Decisions made
    │
    ▼
HTTP Response (JSON)
    │
    {
      "status": "success",
      "workflow": {...},
      "results": {...}
    }
```

## Tool Integration Points

```
Each Agent has access to:

IntakeAgent
├── market_research
├── competitor_analysis
└── trend_detection

SupplierAgent
├── supplier_search
├── quote_generator
└── supplier_validation

CommitAgent
├── pdf_generator
├── qrcode_generator
└── report_generator

SalesAgent
├── web_scraper
├── payment_link_generator
└── commission_calculator
```

## Scalability Architecture

### Horizontal Scaling

```
Load Balancer
    │
    ├─ API Server 1
    ├─ API Server 2
    └─ API Server 3

All connected to:
    ├─ Shared Database (PostgreSQL)
    ├─ Shared Cache (Redis)
    └─ Shared Vector Store (ChromaDB)
```

### Vertical Scaling

```
Single Server Optimization:
├── Async/await throughout
├── Connection pooling
├── Caching strategies
├── Batch processing
└── Resource limits
```

## Error Handling Flow

```
Tool or Agent fails
    │
    ▼
Catch exception
    │
    ├─ Log error
    ├─ Return ToolResult with success=False
    │
    ▼
Agent observes failure
    │
    ├─ Decide retry vs skip
    ├─ Fall back to default data
    ├─ Update memory
    │
    ▼
Workflow continues with mitigation
    │
    ▼
Final result includes both successes and failures
```

## Security Architecture

```
API Layer
├── CORS enabled for configured origins
├── Request validation with Pydantic
└── Error messages sanitized

Database Layer
├── SQLAlchemy ORM prevents SQL injection
├── Parameterized queries
└── Encrypted sensitive data (future)

Agent Layer
├── Tool execution sandboxed
├── External API calls authenticated
└── Rate limiting (future)
```

## Performance Characteristics

### Agent Execution Time
- IntakeAgent: 10-20 seconds (includes API calls)
- SupplierAgent: 10-15 seconds (includes searches)
- CommitAgent: 5-10 seconds (local processing)
- SalesAgent: 8-12 seconds (includes research)

### Total Workflow Time
- Onboarding: 30-45 seconds
- Order Fulfillment: 45-60 seconds
- Sales Activation: 60-90 seconds
- Complete Journey: 3-5 minutes

### Bottlenecks
1. External API calls (Ollama, market research APIs)
2. Tool execution (web scraping takes time)
3. Database operations (minimal impact with caching)

---

## Summary

KARIGAR uses a modular architecture with:
- **Agents** that think and act independently
- **Tools** that agents can use
- **Workflows** that orchestrate agent sequences
- **Database** that persists all data
- **API** that exposes workflows to clients

This architecture allows for easy extension with new agents, tools, and workflows while maintaining clear separation of concerns.
