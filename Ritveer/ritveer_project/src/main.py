from fastapi import FastAPI, Request
from src.graph.workflow import app as ritveer_app
from src.tools.twilio_tools import parse_twilio_webhook

app = FastAPI()

@app.post("/invoke")
async def invoke(request: dict):
    inputs = {"initial_query": request.get("message")}
    return ritveer_app.invoke(inputs)

@app.post("/hooks/whatsapp")
async def twilio_whatsapp_webhook(request: Request):
    form_data = await request.form()
    parsed_data = parse_twilio_webhook(form_data)
    
    # Assuming the LangGraph workflow expects 'initial_query' in its state
    inputs = {"initial_query": parsed_data["message_body"], "raw_message": parsed_data["message_body"]}
    
    # You might want to store sender_phone_number in the state as well
    # For now, just passing the message body
    
    result = ritveer_app.invoke(inputs)
    return {"status": "success", "message": "Webhook received and workflow triggered."}


@app.get("/")
async def root():
    return {"message": "Welcome to the Ritveer API"}