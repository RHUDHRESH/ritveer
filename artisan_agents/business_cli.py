#!/usr/bin/env python3
"""
Artisan Business Growth CLI
Main entry point - interactive system to help artisans grow their businesses
"""

import sys
from typing import Dict, Optional
import json
from datetime import datetime
from business_intelligence import BusinessIntelligenceSystem, BusinessContext, BusinessPlanGenerator
from research_engine import ComprehensiveResearchEngine, SupplierResearcher, MarketplaceResearcher
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ArtisanBusinessGrowthCLI:
    """Interactive CLI for artisan business growth"""

    def __init__(self):
        self.context = None
        self.research_engine = ComprehensiveResearchEngine()
        self.full_research = None
        self.plan_generator = None

    def print_header(self, title: str):
        """Print formatted header"""
        print("\n" + "="*80)
        print(f"  {title}")
        print("="*80 + "\n")

    def print_section(self, title: str):
        """Print formatted section"""
        print(f"\n{title}")
        print("-" * len(title))

    def get_context(self):
        """Interactive session to gather artisan context"""
        self.print_header("ARTISAN BUSINESS GROWTH SYSTEM")

        print("""
This system helps you grow your artisan craft business by:
1. Understanding your craft and business
2. Researching equipment, materials, and suppliers
3. Finding e-commerce opportunities
4. Locating venues and events
5. Creating a concrete growth plan

Let's start by learning about you and your craft.\n""")

        # Initialize context
        self.context = BusinessContext()

        # Personal Info
        print("--- PERSONAL INFORMATION ---")
        name = input("What's your name? > ").strip()
        try:
            age = int(input("How old are you? > "))
        except ValueError:
            age = 0

        try:
            experience = int(input("How many years of experience with your craft? > "))
        except ValueError:
            experience = 0

        self.context.add_personal_info(name, age, experience)

        # Craft Info
        print("\n--- CRAFT INFORMATION ---")
        craft = input("What's your craft/trade? (pottery, carpentry, weaving, jeweler, etc) > ").strip()
        description = input("Describe what you create: > ").strip()
        specialties_input = input("Any special techniques or unique products? (comma-separated, or press Enter to skip) > ").strip()
        specialties = [s.strip() for s in specialties_input.split(',')] if specialties_input else []

        self.context.add_craft_info(craft, description, specialties)

        # Location
        print("\n--- LOCATION INFORMATION ---")
        city = input("What city are you in? > ").strip()
        state = input("State/Province? > ").strip()
        country = input("Country? > ").strip()
        workspace = input("Current workspace setup? (small/medium/large/none) > ").strip()

        self.context.add_location_info(city, state, country, workspace)

        # Business
        print("\n--- BUSINESS INFORMATION ---")
        try:
            current = float(input("Current monthly income? (enter 0 if just starting) > ") or 0)
        except ValueError:
            current = 0

        try:
            target = float(input("Target monthly income? > ") or 0)
        except ValueError:
            target = 0

        try:
            customers = int(input("Current customer base? (number or estimate, enter 0 if none) > ") or 0)
        except ValueError:
            customers = 0

        try:
            target_cust = int(input("Target number of customers? > ") or 0)
        except ValueError:
            target_cust = 0

        self.context.add_business_info(current, target, customers)

        return self.context

    def display_needs_analysis(self):
        """Show what the artisan needs based on craft"""
        self.print_section("EQUIPMENT & MATERIALS ANALYSIS")

        needs = self.context.get_needs_assumptions()

        print(f"""
Based on your craft ({self.context.data['craft'].get('type')}),
you'll likely need the following:

""")

        for i, need in enumerate(needs, 1):
            print(f"  {i}. {need}")

        print("""
Next, we'll research pricing and suppliers for these items.""")

    def run_comprehensive_research(self):
        """Research all aspects of the business"""
        self.print_section("COMPREHENSIVE BUSINESS RESEARCH")

        context = self.context.get_context()
        craft = context['craft'].get('type')
        city = context['location'].get('city')
        state = context['location'].get('state')
        location_str = f"{city}, {state}"

        print(f"""
Researching opportunities for {craft} artisan in {location_str}...

This will take a moment...\n""")

        # Run comprehensive research
        self.full_research = self.research_engine.research_complete_business_setup(craft, location_str)

        # Display marketplace opportunities
        self.print_section("E-COMMERCE MARKETPLACE OPPORTUNITIES")

        marketplace_researcher = MarketplaceResearcher()
        platforms = marketplace_researcher.get_best_platforms(craft)

        print(f"\nTop {len(platforms)} platforms for selling {craft}:\n")

        for i, platform in enumerate(platforms, 1):
            print(f"{i}. {platform['name']}")
            print(f"   Best for: {platform['best_for']}")
            print(f"   Fees: {platform['fees']}")

            # Get revenue potential
            potential = marketplace_researcher.estimate_revenue_potential(craft, platform['name'])
            print(f"   Potential Monthly Revenue: {potential['monthly_revenue_potential']}")
            print(f"   Average Order Value: {potential['average_order_value']}")
            print(f"   Sign up: {platform['sign_up']}\n")

        # Display venues
        self.print_section("LOCAL SELLING VENUES")

        venues = self.research_engine.venues.find_galleries_and_shops(location_str)

        if venues:
            print(f"\nFound {len(venues)} potential venues for consignment:\n")
            for i, venue in enumerate(venues[:5], 1):  # Show top 5
                print(f"{i}. {venue['name']}")
                print(f"   Address: {venue['address']}")
                print(f"   Phone: {venue['phone']}")
                print(f"   Map: {venue['url']}")
                print(f"   Next: Call or visit to discuss consignment\n")
        else:
            print(f"\nSearch for galleries and shops in {location_str} on Google Maps")

        # Display equipment suppliers
        self.print_section("EQUIPMENT & MATERIAL SUPPLIERS")

        needs = self.context.get_needs_assumptions()[:3]  # Top 3 needs

        print(f"\nResearching suppliers for key materials...\n")

        for need in needs:
            print(f"For {need}:")
            supplier_info = self.research_engine.suppliers.find_suppliers_for_item(need, location_str)

            print(f"  Online: {supplier_info['best_option']['reason']}")
            print(f"  Action: {supplier_info['best_option']['action']}\n")

        # Events
        self.print_section("UPCOMING EVENTS & CRAFT FAIRS")

        events = self.research_engine.venues.find_craft_fairs(location_str)

        if events:
            print(f"\nSearching for craft fairs and markets in {location_str}...")
            print(f"Check local event calendars and Google for:\n")
            print(f"  - Craft fairs")
            print(f"  - Art markets")
            print(f"  - Seasonal bazaars")
            print(f"  - Holiday pop-ups\n")

    def generate_business_plan(self):
        """Generate comprehensive business growth plan"""
        self.print_section("GENERATING YOUR BUSINESS GROWTH PLAN")

        self.plan_generator = BusinessPlanGenerator(self.context)
        plan = self.plan_generator.generate_growth_plan()

        print(f"\nYour {len(plan['phases'])}-Phase Growth Strategy:\n")

        for phase in plan['phases']:
            print(f"\nPHASE {phase['phase']}: {phase['name'].upper()}")
            print(f"Duration: {phase['duration']}")
            print("Objectives:")
            for obj in phase['objectives']:
                print(f"  - {obj}")

    def generate_action_plan(self):
        """Generate detailed action items"""
        self.print_section("YOUR ACTION PLAN")

        actions = self.plan_generator.generate_action_plan()

        print("\nPriority Actions for This Week:\n")

        for action in actions:
            print(f"PRIORITY {action['priority']}: {action['action'].upper()}")
            print(f"Description: {action['description']}")
            print(f"Timeline: {action['timeline']}\n")

        # Add marketplace actions
        marketplace_researcher = MarketplaceResearcher()
        craft = self.context.data['craft'].get('type')
        platforms = marketplace_researcher.get_best_platforms(craft)

        if platforms:
            print("\nONLINE MARKETPLACE SETUP:\n")
            for i, platform in enumerate(platforms[:2], 1):
                guide = marketplace_researcher.get_marketplace_setup_guide(platform['name'].lower().replace(' ', '_'))
                if guide['guide'].get('steps'):
                    print(f"\n{i}. {platform['name'].upper()} SETUP")
                    print(f"   Time Required: {guide['guide'].get('time')}")
                    print(f"   Cost: {guide['guide'].get('cost')}")
                    print("   Steps:")
                    for step in guide['guide'].get('steps', [])[:3]:  # First 3 steps
                        print(f"     - {step}")
                    print(f"   Full Guide: {guide['url']}")

    def generate_trip_plan(self):
        """Generate trip planning for venue visits"""
        self.print_section("TRIP PLANNING - VENUE SCOUTING")

        location = self.context.data['location']
        city = location.get('city')
        state = location.get('state')

        venues = self.research_engine.venues.find_galleries_and_shops(f"{city}, {state}")

        if not venues:
            print(f"""
To scout selling venues in {city}:

1. Open Google Maps
2. Search for "art gallery" or "gift shop" in your area
3. Make a list of promising locations
4. Plan your route to visit 3-5 on the same day
5. Bring product samples and business cards

Key Questions to Ask:
  - Do you accept consignment?
  - What's your commission rate? (typically 25-50%)
  - What types of products sell best?
  - How often do you want new items?
  - What's your customer demographic?
""")
        else:
            print(f"""
Venue Scouting Trip Plan for {city}:

Venues to Visit:
""")
            for i, venue in enumerate(venues[:5], 1):
                print(f"\n{i}. {venue['name']}")
                print(f"   Address: {venue['address']}")
                print(f"   Phone: {venue['phone']}")

            print(f"""
Trip Planning:
  - Visit 3-5 venues on the same day
  - Call ahead if possible
  - Bring: Product samples, business cards, photos, price list
  - Ask about consignment terms and commission rates
  - Get business card or contact info from manager
  - Follow up with email proposal
""")

    def generate_final_report(self):
        """Generate comprehensive final report"""
        self.print_header("YOUR ARTISAN BUSINESS GROWTH REPORT")

        context = self.context.get_context()
        craft = context['craft'].get('type')
        location = f"{context['location'].get('city')}, {context['location'].get('state')}"

        report = f"""
═══════════════════════════════════════════════════════════════════════════════
                    ARTISAN BUSINESS GROWTH PLAN
═══════════════════════════════════════════════════════════════════════════════

Name: {context['personal'].get('name', 'N/A')}
Craft: {craft.title()}
Location: {location}
Experience: {context['personal'].get('experience_years', 0)} years
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

─────────────────────────────────────────────────────────────────────────────

SITUATION ANALYSIS

Current Status:
  - Monthly Income: ${context['business'].get('current_income', 0):,.0f}
  - Current Customers: {context['business'].get('current_customers', 0)}
  - Workspace: {context['location'].get('current_workspace', 'Not specified')}

Business Goals:
  - Target Monthly Income: ${context['business'].get('target_income', 0):,.0f}
  - Target Customers: 50+ (build from current base)

─────────────────────────────────────────────────────────────────────────────

EQUIPMENT NEEDS

Based on your craft ({craft}), acquire:
"""
        needs = self.context.get_needs_assumptions()
        for i, need in enumerate(needs, 1):
            report += f"\n  {i}. {need}"

        report += f"""

Action: Research each item's price on Amazon, Flipkart, and local suppliers.
        Get 3 quotes minimum before purchasing.

─────────────────────────────────────────────────────────────────────────────

REVENUE OPPORTUNITIES

E-Commerce Platforms:
"""

        marketplace_researcher = MarketplaceResearcher()
        platforms = marketplace_researcher.get_best_platforms(craft)

        for platform in platforms[:3]:
            potential = marketplace_researcher.estimate_revenue_potential(craft, platform['name'])
            report += f"""

  {platform['name']}
  ├─ Audience: {platform['best_for']}
  ├─ Fees: {platform['fees']}
  ├─ Potential: {potential['monthly_revenue_potential']}
  └─ Sign up: {platform['sign_up']}"""

        report += f"""

Local Venues:
  - Galleries: Search "art gallery" in Google Maps for {context['location'].get('city')}
  - Gift shops: Check local boutiques for consignment opportunities
  - Markets: Look for weekly craft fairs and farmer's markets
  - Events: Seasonal bazaars and holiday pop-ups

─────────────────────────────────────────────────────────────────────────────

ACTION PLAN - NEXT 30 DAYS

Week 1: Foundation
  ☐ Research and source key equipment
  ☐ Get price quotes from 3+ suppliers
  ☐ Scout 5 local selling venues
  ☐ Prepare product samples

Week 2: Online Setup
  ☐ Create accounts on 2 marketplaces
  ☐ Take product photos
  ☐ Write product descriptions
  ☐ Create 10+ listings

Week 3: Venue Outreach
  ☐ Visit scouted venues in person
  ☐ Pitch consignment to gallery owners
  ☐ Negotiate terms and commission rates
  ☐ Drop off samples if accepted

Week 4: Launch & Monitor
  ☐ Make first online sales
  ☐ Deliver initial consignment stock
  ☐ Gather customer feedback
  ☐ Refine products and listings

─────────────────────────────────────────────────────────────────────────────

SUCCESS METRICS

Target: {context['business'].get('target_income', 0):,.0f}/month within 6 months

Milestones:
  Month 1: Establish online presence (5+ sales)
  Month 2: Add consignment venues (3+ locations)
  Month 3: Reach 20 customers
  Month 4: 500/month revenue
  Month 5: 1000+/month revenue
  Month 6: Target income achieved

─────────────────────────────────────────────────────────────────────────────

RESOURCES & LINKS

Research:
  - Google Maps: maps.google.com
  - Product Research: amazon.com, flipkart.com, alibaba.com
  - Event Calendar: Search "[city] craft fair 2024"

Marketplace Sign-up:
  - Etsy: etsy.com/sell
  - Amazon Handmade: amazon.com/handmade
  - Flipkart: seller.flipkart.com

Supplier Contact:
  - Search "[item] supplier [city]" on Google
  - Use Google Maps to find local business
  - Check business website for contact info

─────────────────────────────────────────────────────────────────────────────

NEXT STEP

No fuss. Start with your Week 1 action items:

1. Open a spreadsheet and list all equipment you need
2. Search for suppliers on Amazon, Flipkart, and Google
3. Write down phone numbers and emails
4. Get price quotes
5. Scout venues on Google Maps

This is your business. This plan is your roadmap. Execute it.

═══════════════════════════════════════════════════════════════════════════════
Generated by Artisan Business Growth System
No BS, just actionable steps to grow your craft business.
═══════════════════════════════════════════════════════════════════════════════
"""
        print(report)

        # Save report
        filename = f"business_plan_{context['personal'].get('name', 'artisan').replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"\n\nReport saved to: {filename}")

        return report

    def run_interactive_session(self):
        """Run complete interactive session"""
        try:
            # Step 1: Gather context
            self.get_context()

            # Step 2: Analyze needs
            self.display_needs_analysis()

            # Step 3: Run research
            input("\n\nPress Enter to begin comprehensive research...")
            self.run_comprehensive_research()

            # Step 4: Generate plans
            input("\n\nPress Enter to generate your business growth plan...")
            self.generate_business_plan()

            # Step 5: Action plan
            input("\n\nPress Enter to see your detailed action plan...")
            self.generate_action_plan()

            # Step 6: Trip planning
            input("\n\nPress Enter to see venue scouting trip plan...")
            self.generate_trip_plan()

            # Step 7: Final report
            input("\n\nPress Enter to generate your final business report...")
            self.generate_final_report()

            self.print_header("SESSION COMPLETE")
            print("""
Your business growth plan is ready!

Next steps:
1. Review the generated report
2. Start with Week 1 actions
3. Execute ruthlessly
4. Track your progress
5. Adjust as needed

Good luck growing your craft business!
""")

        except KeyboardInterrupt:
            print("\n\nSession ended by user.")
            sys.exit(0)
        except Exception as e:
            logger.error(f"Error during session: {e}", exc_info=True)
            raise


def main():
    """Main entry point"""
    cli = ArtisanBusinessGrowthCLI()
    cli.run_interactive_session()


if __name__ == '__main__':
    main()
