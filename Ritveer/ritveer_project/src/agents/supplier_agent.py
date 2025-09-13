from typing import Any, Dict, List
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from src.graph.state import RitveerState
from config.settings import settings
from src.graph.workflow import reasoning_llm
from src.tools.scraper_tools import scrape_supplier_website
from src.tools.twilio_tools import make_call

# Define the JSON schema for the supplier selection
SUPPLIER_SELECTION_SCHEMA = {
    "type": "object",
    "properties": {
        "suppliers_to_call": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name of the supplier."},
                    "phone_number": {"type": "string", "description": "Phone number of the supplier."},
                    "reason": {"type": "string", "description": "Reason for selecting this supplier."},
                },
                "required": ["name", "phone_number", "reason"],
            },
            "description": "List of suppliers to call based on scraped data and policy.",
        }
    },
    "required": ["suppliers_to_call"],
}

# Craft a system prompt for the reasoning LLM to select suppliers
supplier_selection_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a procurement specialist. Your task is to analyze the provided artisan clusters "
            "and scraped supplier data to decide which suppliers to call for a quote. "
            "Consider the item, quantity, and budget from the normalized request. "
            "Prioritize suppliers that are geographically close (from artisan clusters) and offer competitive prices. "
            "Output your decision in a strict JSON schema:\n"
            f"{SUPPLIER_SELECTION_SCHEMA}\n"
            "Ensure your output is a valid JSON object that conforms to the schema."
        ),
        ("human", "Normalized Request: {normalized_request}\nArtisan Clusters: {artisan_clusters}\nScraped Data: {scraped_data}"),
    ]
)

# Create the chain for supplier selection
supplier_selection_chain = supplier_selection_prompt | reasoning_llm | JsonOutputParser()


def supplier_agent_node(state: RitveerState) -> Dict[str, Any]:
    """
    The supplier agent node scrapes websites, uses LLM to select suppliers to call,
    makes calls, and updates supplier_quotes in the state.
    """
    print("---SUPPLIER AGENT: Processing supplier information---")
    normalized_request = state.get("normalized_request", {})
    artisan_clusters = state.get("artisan_clusters", [])

    item = normalized_request.get("item")

    if not item:
        print("SUPPLIER AGENT: No item found in normalized_request. Skipping supplier agent.")
        return {"supplier_quotes": []}

    # Step 1: Scrape websites for prices (placeholder for actual scraping logic)
    # For demonstration, let's assume we have a list of dummy supplier URLs
    supplier_urls = [
        "http://example.com/supplierA",
        "http://example.com/supplierB",
        "http://example.com/supplierC",
    ]

    scraped_data = []
    for url in supplier_urls:
        scraped_data.extend(scrape_supplier_website(url, item))

    # Step 2: Use reasoning LLM to decide which suppliers to call
    suppliers_to_call_decision = supplier_selection_chain.invoke(
        {
            "normalized_request": normalized_request,
            "artisan_clusters": artisan_clusters,
            "scraped_data": scraped_data,
        }
    )

    suppliers_to_call = suppliers_to_call_decision.get("suppliers_to_call", [])

    # Step 3: Use Twilio voice tool to place calls and record responses (placeholder)
    # For demonstration, we'll simulate call responses
    supplier_quotes = []
    for supplier in suppliers_to_call:
        print(f"SUPPLIER AGENT: Calling {supplier['name']} at {supplier['phone_number']}")
        # In a real scenario, make_call would trigger an actual call and
        # you'd have a mechanism to record and process the response.
        # For now, we'll simulate a quote.

        # Dummy TwiML URL - replace with actual TwiML for recording
        dummy_twiml_url = "http://demo.twilio.com/docs/voice.xml"
        call_result = make_call(supplier["phone_number"], dummy_twiml_url)

        # Simulate a quote based on scraped data or a random value
        simulated_quote = {
            "supplier_name": supplier['name'],
            "item": item,
            "price": f"{len(supplier['name']) * 100}", # Dummy price
            "currency": "INR",
            "call_sid": call_result.get("sid"),
            "call_status": call_result.get("status"),
            "notes": "Simulated quote from voice call."
        }
        supplier_quotes.append(simulated_quote)

    # Step 4: Update the supplier_quotes field in the state
    return {"supplier_quotes": supplier_quotes}
