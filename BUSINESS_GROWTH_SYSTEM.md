# Artisan Business Growth System

## Overview

A complete, no-nonsense business intelligence system that helps artisans grow their craft businesses by researching equipment, finding markets, locating venues, and creating actionable growth plans.

## How It Works

You give context about who you are, what you do, and where you operate. The system automatically:

1. **Analyzes your needs** - Makes intelligent assumptions about equipment/materials you'll need based on your craft
2. **Researches suppliers** - Finds equipment sellers with pricing and contact information
3. **Identifies e-commerce opportunities** - Shows which marketplaces are best for your craft with revenue potential
4. **Finds selling venues** - Discovers galleries, shops, and events where you can sell or consign
5. **Plans trips** - Creates logistics for visiting suppliers, venues, or events
6. **Generates business plans** - Creates concrete, actionable growth strategies

## System Architecture

### Core Modules

**business_intelligence.py**
- `BusinessContext` - Stores artisan/business information
- `EquipmentResearcher` - Research and find equipment with prices
- `MarketplaceOpportunityFinder` - Find e-commerce sales channels
- `EventVenueFinder` - Find craft fairs, galleries, markets
- `TripPlanner` - Plan trips and logistics
- `BusinessPlanGenerator` - Generate growth plans and timelines
- `BusinessIntelligenceSystem` - Master orchestrator

**research_engine.py**
- `GoogleMapsResearcher` - Find local businesses and locations
- `SupplierResearcher` - Research equipment suppliers and pricing
- `MarketplaceResearcher` - Deep dive into e-commerce platforms
- `EventVenueResearcher` - Research events and venues
- `WebContentAnalyzer` - Analyze web content and search
- `ComprehensiveResearchEngine` - Combine all research tools

**business_cli.py**
- `ArtisanBusinessGrowthCLI` - Interactive command-line interface
- Guides through information gathering
- Runs research and analysis
- Generates comprehensive business reports

## Using the System

### Start the CLI

```bash
cd artisan_agents
python business_cli.py
```

### Interactive Questions

The system asks you about:

**Personal Information**
- Name
- Age
- Years of experience with craft

**Craft Information**
- Type of craft (pottery, carpentry, etc.)
- What you create
- Special techniques/unique products

**Location**
- City, state, country
- Current workspace setup

**Business**
- Current monthly income
- Target monthly income
- Current and target customer numbers

### What You Get

1. **Equipment & Materials Analysis**
   - Automatic list of everything you need based on your craft
   - Assumptions about workspace requirements

2. **Marketplace Research**
   - Top e-commerce platforms for your craft
   - Fee structure for each platform
   - Monthly revenue potential estimates
   - Links to sign up

3. **Local Venue Discovery**
   - Nearby galleries and gift shops
   - Contact information
   - Maps and directions

4. **Supplier Research**
   - Online retailers (Amazon, Flipkart, Alibaba)
   - Local suppliers
   - Price estimates
   - Contact information

5. **Event & Fair Finder**
   - Upcoming craft fairs
   - Art markets
   - Holiday bazaars
   - Application information

6. **Business Growth Plan**
   - 4-phase comprehensive strategy
   - Timeline for each phase
   - Specific objectives
   - Success metrics

7. **Action Plan**
   - Week-by-week tasks
   - Priority-ordered action items
   - Marketplace setup guides
   - Venue scouting logistics

8. **Trip Planning**
   - Route optimization for venue visits
   - Material sourcing trips
   - Event attendance planning
   - Time and cost estimates

## Example Usage

### Input Example: Potter in Delhi

```
Name: Priya Sharma
Age: 32
Experience: 8 years
Craft: Pottery
Description: Hand-thrown ceramic vases and decorative pieces
Specialties: Glazing, wheel throwing, traditional designs
Location: Delhi, Delhi, India
Workspace: Medium (15x15 feet)
Current Income: ₹20,000/month
Target Income: ₹75,000/month
Current Customers: 15
```

### System Output

**Equipment Needed:**
- Clay (pottery clay)
- Kiln/furnace for firing
- Pottery wheel
- Glazes and pigments
- Workspace 20x20 feet (upgrade from current)
- Drying racks
- Brushes and tools

**E-commerce Opportunities:**
- Etsy: 6.5% fees, global audience, estimated ₹30,000-120,000/month
- Amazon Handmade: 15% commission, large audience, estimated ₹15,000-75,000/month
- Flipkart: 8-20% commission, Indian market, estimated ₹10,000-50,000/month
- Shopify: $29/month, branded store, estimated ₹50,000-200,000/month

**Local Venues:**
- Anokhi Gallery, New Delhi - Gallery consignment (25% commission)
- Crafts Council Shop, Delhi - Direct retail (30% commission)
- Dilli Haat - Weekly craft market booth available
- Weekly farmer's markets in residential areas

**Action Plan - Week 1:**
1. Research pottery clay suppliers (cost: ₹2,000-5,000/bag)
2. Get quotes for kiln upgrade (cost: ₹50,000-200,000)
3. Scout 5 galleries in person
4. Prepare product samples for consignment

**Action Plan - Week 2-3:**
1. Set up Etsy seller account
2. Take product photography
3. Write compelling product descriptions
4. Create 15+ listings with pricing

**Action Plan - Week 4:**
1. Visit Anokhi Gallery with samples
2. Negotiate consignment terms
3. Make first online sale
4. Monitor seller ratings and feedback

**6-Month Projection:**
- Month 1: Equipment acquired, online presence established
- Month 2: First consignment placements, initial online sales
- Month 3: 50+ customers across all channels
- Month 4: ₹45,000/month revenue
- Month 5: ₹60,000/month revenue
- Month 6: Target ₹75,000/month achieved

## Key Features

### No Configuration Required
- Works out of the box
- Mock data for development
- Real searches and research available with API keys

### Intelligent Assumptions
- Based on craft type, automatically identifies likely needs
- Suggests appropriate marketplaces
- Recommends suitable venues and events

### Comprehensive Research
- E-commerce: Etsy, Amazon, Flipkart, Shopify, Instagram, custom stores
- Suppliers: Online retailers, local shops, wholesale distributors
- Venues: Galleries, gift shops, craft fairs, markets, farmer's markets
- Events: Seasonal fairs, holiday bazaars, art shows
- Pricing: Estimates and comparison across sources

### Actionable Plans
- Week-by-week tasks
- Priority-ordered action items
- Clear timelines
- Success metrics and milestones

### Trip Planning
- Route optimization
- Time estimates
- Material checklists
- Contact information

## File Structure

```
artisan_agents/
├── business_intelligence.py     # Core system logic
├── research_engine.py            # Web research tools
├── business_cli.py              # Interactive CLI
├── app.py                       # Flask web backend (optional)
└── index.html                   # Web dashboard (optional)
```

## Example Output

The system generates a comprehensive text report saved as:
```
business_plan_Priya_Sharma_20251027_093015.txt
```

This report includes:
- Executive summary
- Situation analysis
- Equipment needs with sourcing
- E-commerce opportunities
- Venue opportunities
- 30-day action plan
- 6-month milestones
- Resource links
- Next steps

## How to Run

### Command Line (Interactive)
```bash
cd artisan_agents
python business_cli.py
```

### Programmatic Usage
```python
from business_cli import ArtisanBusinessGrowthCLI

cli = ArtisanBusinessGrowthCLI()
cli.run_interactive_session()
```

### Individual Modules
```python
from business_intelligence import BusinessContext, BusinessPlanGenerator
from research_engine import ComprehensiveResearchEngine

# Create context
context = BusinessContext()
context.add_personal_info("Name", 30, 5)
context.add_craft_info("pottery", "Description", ["specialty"])
context.add_location_info("City", "State", "Country")

# Generate plan
plan_gen = BusinessPlanGenerator(context)
plan = plan_gen.generate_growth_plan()

# Research opportunities
engine = ComprehensiveResearchEngine()
research = engine.research_complete_business_setup("pottery", "City")
```

## What This Solves

**Before**: Artisans struggle with:
- What equipment do I actually need?
- Where can I sell my products?
- How do I price things?
- Which marketplace should I use?
- How do I find customers locally?
- How do I reach bigger markets?

**After**: Complete roadmap with:
- Identified equipment needs and suppliers
- Multiple e-commerce platforms with revenue estimates
- Local venues and events with contact information
- Concrete action steps and timeline
- 6-month business growth plan
- Pricing and commission information

## No Fuss

This system doesn't:
- Generate fancy dashboards
- Require expensive APIs
- Need data cleaning
- Require extensive configuration
- Have mock features

It:
- Asks relevant questions
- Makes intelligent assumptions
- Researches real opportunities
- Generates actionable plans
- Saves comprehensive reports
- Provides real next steps

## Future Enhancements

Optional additions:
- Real Google Maps API integration
- Real e-commerce platform APIs
- Database for storing plans
- Multi-user support
- Mobile app version
- Real-time marketplace pricing
- Automated supplier notifications
- Customer management system

## Support

Run the system and follow the prompts. All output is saved to text files for future reference.

No fuss. Just actionable business growth.
