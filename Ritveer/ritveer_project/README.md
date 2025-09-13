# Ritveer Project

This project is a LangChain and Ollama-based system for orchestrating a series of agents to handle a variety of tasks.

## Directory Structure

```
ritveer_project/
├── .env                  # Stores all secrets and API keys (DO NOT commit to Git)
├── .gitignore            # Standard file to ignore temp files, .env, etc.
├── docker-compose.yml    # Defines and runs your entire infrastructure (Ollama, Redis, etc.)
├── Dockerfile            # To containerize the main Python application
├── requirements.txt      # Lists all Python package dependencies
├── README.md             # Project documentation
│
├── config/
│   ├── settings.py       # Loads configurations from .env and YAML files
│   └── policy.yml        # Your business rules (e.g., 3-strike rule, ledger limits)
│
├── notebooks/
│   ├── 01_test_intake_agent.ipynb  # Jupyter notebooks for testing and development
│   └── 02_data_clustering_poc.ipynb
│
├── src/
│   ├── __init__.py
│   ├── main.py           # Entry point: Starts the API server or message consumer
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── intake_agent.py
│   │   ├── cluster_agent.py
│   │   ├── supplier_agent.py
│   │   └── ... (one file per agent)
│   │
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── state.py      # Defines the `RitveerState` TypedDict
│   │   └── workflow.py   # Where you build and compile the LangGraph
│   │
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── postgis_tools.py
│   │   ├── twilio_tools.py
│   │   ├── razorpay_tools.py
│   │   └── ... (wrappers for every external API)
│   │
│   └── utils/
│       ├── __init__.py
│       └── logging_config.py # Centralized logging setup
│
└── tests/
    ├── __init__.py
    ├── test_agents.py        # Unit tests for individual agents
    └── test_tools.py         # Unit tests for your API tool wrappers

frontend/
├── ... (React frontend)
```

## Getting Started

### Backend

1.  **Install Docker and Docker Compose.**
2.  **Create a `.env` file** in the root directory and add your API keys and secrets.
3.  **Run `docker-compose up -d`** to start the services.
4.  **The API will be available at `http://localhost:8000`**.

### Frontend

1.  **Navigate to the `frontend` directory.**
2.  **Run `npm install`** to install the dependencies.
3.  **Run `npm run dev`** to start the development server.
4.  **The frontend will be available at `http://localhost:5173`**.

## Project Overview

*   **`.env`**: Stores all secrets and API keys. This file is ignored by Git.
*   **`.gitignore`**: Standard file to ignore temp files, `.env`, etc.
*   **`docker-compose.yml`**: Defines and runs your entire infrastructure (Ollama, Redis, etc.).
*   **`Dockerfile`**: To containerize the main Python application.
*   **`requirements.txt`**: Lists all Python package dependencies.
*   **`README.md`**: Project documentation.
*   **`config/`**: Contains configuration files.
    *   **`settings.py`**: Loads configurations from `.env` and YAML files.
    *   **`policy.yml`**: Your business rules (e.g., 3-strike rule, ledger limits).
*   **`notebooks/`**: Jupyter notebooks for testing and development.
*   **`src/`**: Contains the source code.
    *   **`main.py`**: Entry point: Starts the API server or message consumer.
    *   **`agents/`**: Contains the agents.
    *   **`graph/`**: Contains the LangGraph workflow.
    *   **`tools/`**: Contains the tools for the agents.
    *   **`utils/`**: Contains utility functions.
*   **`tests/`**: Contains the tests.
*   **`frontend/`**: Contains the React frontend.

## Project Initialization Checklist

[x] Project Initialization

[x] Initialize a git repository and create the full project scaffolding (directories: config, src, tests, etc.).

[x] Create the .gitignore file.

[x] Set up a Python virtual environment (venv or conda).

[x] Create the requirements.txt file with initial packages: langchain, langgraph, fastapi, uvicorn, python-dotenv, redis, psycopg2-binary, pyyaml.

[x] Create the .env.example file listing all needed secrets (Twilio, Razorpay, Shiprocket, Google Cloud, etc.).

## Containerized Services (docker-compose.yml)

[x] Define the ollama service.

[x] Define the redis service (for caching and the Pub/Sub fallback).

[x] Define the postgres service with the PostGIS extension enabled.

[x] Define the main app service, building from the Dockerfile.

## Application Container (Dockerfile)

[x] Write a Dockerfile for the main Python application. It should install dependencies from requirements.txt and run the main.py file.

## Initial Configuration (config/)

[x] Write config/settings.py to load all environment variables from .env.

[x] Create the initial config/policy.yml with placeholder values.

## Update requirements.txt for Settings Management

[x] Add pydantic-settings to requirements.txt.

[x] Run pip install to install the new package.

## Refactor Settings with Pydantic

[x] Refactor config/settings.py to use pydantic-settings.

## Update Configuration Files

[x] Create the config/policy.yml file with the specified content.

[x] Create the config/settings.py file with the specified content.

## Phase 1, Step 1: LangGraph Foundation (src/graph/)

[x] Define the Shared State (src/graph/state.py)

## Set Up the LangGraph Orchestrator (src/graph/)

[x] Define the Master State: In src/graph/state.py, define the RitveerState TypedDict. Map out all the fields it will hold throughout the workflow (e.g., raw_message: str, normalized_request: dict, artisan_clusters: list, supplier_quotes: list, final_order: dict, shipping_label_url: str, etc.).

[x] Initialize the Workflow: In src/graph/workflow.py, create the instance of StateGraph, passing your RitveerState as the schema.

[x] Instantiate LLM Clients: In workflow.py, import your settings object. Create two global instances of ChatOllama: one configured for the fast model (gemma3:1b) and one for the reasoning model (gemma3:4b).

## Build Agent 1: The IntakeAgent (The Entry Point)

[x] Tooling (API Wrapper): Create the src/tools/twilio_tools.py file. Define a function that is responsible for parsing the incoming webhook data from Twilio to extract the sender's phone number and message body.

[x] API Endpoint: In src/main.py, create a FastAPI POST endpoint (e.g., /hooks/whatsapp). This endpoint will use the Twilio tool and then trigger the LangGraph workflow, passing the raw message as the initial input.

[x] Agent Logic: In src/agents/intake_agent.py, create the intake_agent_node function.

[x] LLM Prompting: Inside the agent node, craft a system prompt for the fast LLM (gemma3:1b). The prompt must instruct it to act as an order-intake specialist, read the user's message, and extract key entities (item, quantity, budget, location, etc.) into a strict JSON schema.

[x] State Update: The agent must take the JSON output from the LLM and update the normalized_request field in the RitveerState.

## Build Agent 2: The ClusterAgent (Geospatial Logic)

[x] Database Schema: Design the artisans table in your PostGIS database. Ensure it has columns for name, craft_type, and a location column of type GEOMETRY or GEOGRAPHY.

[x] Tooling (Database Wrapper): In a new src/tools/postgis_tools.py, define a function find_artisan_clusters. This function must connect to the database, take a location from the state, and execute an ST_ClusterKMeans query to find and return groups of nearby artisans.

[x] Agent Logic: Create the cluster_agent_node in src/agents/cluster_agent.py. It should read the location from the normalized_request in the state, call the find_artisan_clusters tool, and write the results into the artisan_clusters field in the state.

## Build Agent 3: The SupplierAgent (External Communication)

[x] Tooling (Web & Voice): Create src/tools/scraper_tools.py. Define functions for scraping supplier websites. In twilio_tools.py, add functions for making automated voice calls and sending SMS messages using Twilio's APIs.

[x] Agent Logic: Create the supplier_agent_node. This agent will be a multi-step node. First, it scrapes websites for prices. Then, it uses the reasoning LLM (gemma3:4b) to decide which suppliers to call. Finally, it uses the Twilio voice tool to place calls, record responses, and updates the supplier_quotes field in the state.

## Build Agent 4: The CommitAgent (Business Rule Logic)

[x] Tooling (Payments): Create src/tools/razorpay_tools.py with a function create_payment_order that interacts with the Razorpay API.

[x] Agent Logic: Create the commit_agent_node. This agent must read the pooling rules from settings.POLICY_CONFIG. It will perform the calculation (Δcost and SLA risk) based on the supplier_quotes. If the rules are met, it will call the Razorpay tool to generate a pooled payment link and update the state.

## Build Agent 6: The OpsAgent (Logistics)

[x] Tooling (Shipping): Create src/tools/shipping_tools.py. Define functions to wrap the Shiprocket and India Post APIs for creating shipments and generating shipping labels.

[x] Agent Logic: Create the ops_agent_node. It will read the order details from the state, call the appropriate shipping tool, and save the shipping_label_url and tracking ID back to the state.

## Build Agent 7: The CashAgent (Financial Reconciliation)

[x] Tooling (Ledger): Add functions to postgis_tools.py (or a new db_tools.py) for interacting with a financial ledger table in the database.

[x] Agent Logic: Create the cash_agent_node. After a payment confirmation (via a Razorpay webhook), this agent will record the transaction in the ledger table. It must check the transaction amount against the max_unapproved_delta_inr from settings.POLICY_CONFIG.

## Build Agent 8: The LearnAgent (Continuous Improvement)

[x] Tooling (Data Warehousing): This agent will re-use the database tools.

[x] Agent Logic: Create the learn_agent_node. This agent runs at the end of a successful flow. It will read delivery times and any quality flags from the state, then update the reliability scores for the involved suppliers in the database.

## Assemble and Compile the Final Graph

[x] Import All Nodes: In src/graph/workflow.py, import all eight agent node functions.

[x] Add Nodes to Graph: Call workflow.add_node() for each of the eight agents, giving each a unique name.

[x] Define Edges: Call workflow.add_edge() to connect the nodes in the correct sequence: Intake -> Cluster -> Supplier, and so on.

[x] Set Entry and End Points: Define the IntakeAgent as the entry point and connect the LearnAgent to the special END node.

[x] Compile the Graph: Call workflow.compile() to create the final, runnable LangGraph application.
