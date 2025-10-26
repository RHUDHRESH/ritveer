
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from .agents_system import AgentSystem, Agent, Tool, AgentState, ToolState

app = FastAPI()

app.mount("/static", StaticFiles(directory="artisan_agents/static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse('artisan_agents/static/index.html')
agents_system = AgentSystem()

@app.post("/agents", response_model=AgentState)
def create_agent(agent_state: AgentState):
    # This is a placeholder. In a real application, you would create a concrete Agent instance.
    # For now, we'll just use the state to demonstrate the API.
    agent = object() # Replace with actual agent creation
    agent.name = agent_state.name
    agent.state = agent_state
    try:
        agents_system.add_agent(agent)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return agent.state

@app.delete("/agents/{agent_name}")
def delete_agent(agent_name: str):
    try:
        agents_system.remove_agent(agent_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"message": f"Agent {agent_name} deleted successfully."}

@app.get("/agents/{agent_name}", response_model=AgentState)
def get_agent(agent_name: str):
    agent = agents_system.get_agent(agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_name} not found.")
    return agent.state

@app.post("/tools", response_model=ToolState)
def create_tool(tool_state: ToolState):
    # This is a placeholder. In a real application, you would create a concrete Tool instance.
    tool = object() # Replace with actual tool creation
    tool.name = tool_state.name
    tool.state = tool_state
    try:
        agents_system.add_tool(tool)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return tool.state

@app.delete("/tools/{tool_name}")
def delete_tool(tool_name: str):
    try:
        agents_system.remove_tool(tool_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"message": f"Tool {tool_name} deleted successfully."}

@app.get("/tools/{tool_name}", response_model=ToolState)
def get_tool(tool_name: str):
    tool = agents_system.get_tool(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found.")
    return tool.state
