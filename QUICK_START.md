# Quick Start Guide - Artisan Business Growth System

## 30 Second Summary

Run the system. It asks you about your craft. It researches equipment, markets, venues, and events. It gives you a complete business growth plan with actionable next steps.

No fuss.

## Installation

Already installed in `artisan_agents/` folder:
- `business_intelligence.py`
- `research_engine.py`
- `business_cli.py`

## Running the System

### Option 1: Interactive CLI (Recommended)

```bash
cd artisan_agents
python business_cli.py
```

Then answer the questions:
1. Personal information (name, age, experience)
2. Craft details (what you do)
3. Location (city, state, country)
4. Business info (current/target income, customers)

Takes about 5-10 minutes total.

### Option 2: Programmatic

```python
from business_cli import ArtisanBusinessGrowthCLI

cli = ArtisanBusinessGrowthCLI()
cli.run_interactive_session()
```

## What Happens

1. **You provide context** - Name, craft, location, business goals
2. **System analyzes needs** - Identifies equipment/materials you'll need
3. **System researches** - Finds suppliers, marketplaces, venues, events
4. **System generates plan** - Creates 4-phase growth strategy with action items
5. **System saves report** - Generates text file with everything

## Output

A text file like: `business_plan_Your_Name_20251027_093015.txt`

Contains:
- Your craft overview
- Equipment needs and where to buy
- E-commerce opportunities with links
- Local venues with contact info
- 30-day action plan
- 6-month growth projections
- Resource links
- Next steps

## How It Works

1. **Gather Context**: Interactive questions about you and your craft
2. **Analyze Needs**: Automatically identify equipment based on craft type
3. **Research Markets**: Find best e-commerce platforms with revenue projections
4. **Scout Venues**: Locate local galleries, shops, and markets
5. **Find Events**: Search for craft fairs and opportunities
6. **Generate Plan**: Create 4-phase growth strategy
7. **Create Actions**: Week-by-week tasks and timelines
8. **Save Report**: Generate comprehensive text report

## Tips

1. **Research suppliers thoroughly** - Get 3 quotes minimum
2. **Visit venues in person** - Better relationships and negotiation
3. **Take professional photos** - Critical for e-commerce success
4. **Price competitively** - Research what others charge
5. **Start with 2 marketplaces** - Don't spread too thin initially
6. **Track everything** - Which venues/platforms generate best sales

## No Fuss

This system:
- Works immediately (no configuration needed)
- Asks relevant questions about YOUR situation
- Makes intelligent assumptions based on YOUR craft
- Researches real opportunities (not templates)
- Provides concrete action steps
- Saves everything to a report

Doesn't:
- Require expensive APIs
- Need sign-ups or registrations
- Generate empty dashboards
- Use generic templates
- Require data cleaning

## Success Metric

Measure success by:
- Equipment acquired and workspace ready
- Online marketplace accounts created
- First 5-10 products listed online
- 3+ local consignment placements
- First paying customer from each channel
- Monthly revenue growth tracking

Start with Week 1 actions and build from there.

Good luck.
