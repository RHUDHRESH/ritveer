# KARIGAR Quick Start Guide

Get the multi-agent platform running in 5 minutes.

## Prerequisites

- Python 3.8+
- pip (Python package manager)

## 🚀 5-Minute Setup

### Step 1: Install Dependencies (1 minute)

```bash
cd karigar
pip install -r requirements.txt
```

### Step 2: Setup Environment (1 minute)

```bash
cp .env.template .env
```

Edit `.env` and add your API keys:
```env
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4
DATABASE_URL=sqlite:///./karigar.db
```

### Step 3: Initialize Database (1 minute)

```bash
python -c "from src.karigar.schemas.models import init_db; init_db()"
```

### Step 4: Start the API (1 minute)

```bash
python -m uvicorn src.karigar.api.main:app --reload
```

Output:
```
Uvicorn running on http://127.0.0.1:8000
```

### Step 5: Visit API Documentation (1 minute)

Open in browser: `http://localhost:8000/docs`

## ✅ Test It Out

### Test 1: Health Check

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "ok",
  "services": {
    "api": "running",
    "database": "connected",
    "tools": 15,
    "workflows": 4
  }
}
```

### Test 2: Onboard an Artisan

```bash
curl -X POST http://localhost:8000/api/artisan/onboard \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Priya Sharma",
    "craft_type": "pottery",
    "location": "Jaipur",
    "experience_years": 8,
    "has_portfolio": true,
    "has_website": false,
    "has_social_media": true
  }'
```

Response includes:
- Artisan profile created
- Market analysis completed
- Suppliers identified
- Business recommendations

### Test 3: View Available Tools

```bash
curl http://localhost:8000/api/tools
```

Response:
```json
{
  "tools": [
    {
      "name": "supplier_search",
      "description": "Search for suppliers...",
      "required_parameters": ["material_name", "location", "quantity"]
    },
    ...
  ],
  "total": 15
}
```

### Test 4: View Available Workflows

```bash
curl http://localhost:8000/api/workflows
```

Response:
```json
{
  "workflows": [
    {
      "type": "artisan_onboarding",
      "agents": ["IntakeAgent", "SupplierAgent"],
      "description": "Onboard new artisan..."
    },
    ...
  ]
}
```

## 🎯 What's Running

### 4 AI Agents
1. **IntakeAgent** - Onboards artisans, validates profiles
2. **SupplierAgent** - Finds suppliers, negotiates quotes
3. **CommitAgent** - Manages orders, tracks production
4. **SalesAgent** - Drives sales, manages customers

### 15 Tools
- 3 Supplier tools
- 3 Payment tools
- 3 Document tools
- 4 Research tools

### 4 Workflows
1. **Artisan Onboarding** - Complete 30-second setup
2. **Order Fulfillment** - Full order management
3. **Sales Activation** - Launch sales channels
4. **Complete Journey** - All agents working together

## 📊 System Architecture

```
┌─────────────────────────────────────────────┐
│          FastAPI Backend (Port 8000)        │
├─────────────────────────────────────────────┤
│                                             │
│  Workflow Orchestrator                      │
│  ├─ IntakeAgent    → Market Research       │
│  ├─ SupplierAgent  → Find Suppliers        │
│  ├─ CommitAgent    → Manage Orders         │
│  └─ SalesAgent     → Drive Sales           │
│                                             │
│  Tool Registry (15 Tools)                   │
│  ├─ Supplier Tools (search, quotes, valid) │
│  ├─ Payment Tools (links, status, refund)  │
│  ├─ Document Tools (PDF, QR, reports)      │
│  └─ Research Tools (scrape, market, trends)│
│                                             │
│  Database                                   │
│  └─ SQLite (artisans, orders, suppliers)   │
│                                             │
└─────────────────────────────────────────────┘
```

## 🔌 API Endpoints Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | System health check |
| `/api/artisan/onboard` | POST | Onboard new artisan |
| `/api/order/create` | POST | Create customer order |
| `/api/supplier/search` | POST | Find suppliers |
| `/api/workflows` | GET | List workflow types |
| `/api/workflows/{id}` | GET | Get workflow status |
| `/api/tools` | GET | List available tools |
| `/api/tools/{name}/execute` | POST | Execute a tool |

## 🛠️ Common Tasks

### Get Artisan Workflows

```bash
curl http://localhost:8000/api/artisan/artisan_abc123/workflows
```

### Execute a Tool Directly

```bash
curl -X POST http://localhost:8000/api/tools/supplier_search/execute \
  -H "Content-Type: application/json" \
  -d '{
    "material_name": "clay",
    "location": "Jaipur",
    "quantity": 50
  }'
```

### Create an Order

```bash
curl -X POST "http://localhost:8000/api/order/create?artisan_id=artisan_abc123" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "John Doe",
    "customer_email": "john@example.com",
    "customer_phone": "+91-9999-999999",
    "description": "Custom pottery vase",
    "quantity": 5,
    "timeline_days": 21,
    "estimated_cost": 25000
  }'
```

## 📈 Understanding Workflows

### Artisan Onboarding Workflow (30 seconds)

1. **IntakeAgent receives artisan data**
   - Validates profile
   - Assesses skill level
   - Scores business readiness

2. **IntakeAgent executes market research**
   - Analyzes market for craft type
   - Identifies competitors
   - Detects trends
   - Creates business profile

3. **SupplierAgent activates**
   - Searches for material suppliers
   - Gets quotes from top suppliers
   - Validates supplier credibility
   - Prepares procurement strategy

4. **Result**
   - Complete artisan profile created
   - Market analysis stored
   - Suppliers identified and validated

## 🐛 Troubleshooting

### Port 8000 already in use

```bash
# Use different port
python -m uvicorn src.karigar.api.main:app --port 8001
```

### Database errors

```bash
# Reset database
rm karigar.db
python -c "from src.karigar.schemas.models import init_db; init_db()"
```

### Module not found errors

```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt
```

### API keys missing

Add to `.env`:
```env
OPENAI_API_KEY=sk-your-key-here
DATABASE_URL=sqlite:///./karigar.db
```

## 📚 Next Steps

1. **Read the full documentation:** `README.md`
2. **Explore the codebase:** Check agent implementations
3. **Create custom tools:** Add tools specific to your needs
4. **Build frontend:** Create React UI for visualization
5. **Deploy to production:** Use Gunicorn/Uvicorn servers

## 💡 Pro Tips

1. **Use FastAPI Swagger UI:** Visit `/docs` for interactive API testing
2. **Check logs:** API logs show all agent thinking and tool execution
3. **Test tools individually:** Use `/api/tools/{name}/execute` to debug
4. **Monitor workflows:** Use `/api/workflows/{id}` to track progress
5. **Integration:** KARIGAR API can be called from any language/framework

## 🎉 You're Ready!

The multi-agent platform is now running. Start by:

1. Opening `http://localhost:8000/docs`
2. Testing the Swagger UI
3. Running sample requests
4. Creating real artisan profiles
5. Observing agent workflows in action

---

**Questions?** Check the full README.md or review agent implementations in `src/karigar/agents/`
