import anthropic
import requests
import json
import os
from flask import Flask, request, jsonify
from interface import get_chat_html

app = Flask(__name__)

# Configuration
SHEET_API_URL = "https://script.google.com/macros/s/AKfycbx4QRKcj_ikDiBVI4TtxXsg_72BGQn28HpRjOahYfeAW34CyyZ9zvcSP9_jQzsb3OIyBg/exec"
SHEET_TOKEN = "pRjOahYfeAW34CyyZ9zvcSP9"

# Initialize Anthropic client lazily (not at startup)
def get_client():
    return anthropic.Anthropic()

# Define the product sheet tool
tools = [
    {
        "name": "get_product_data",
        "description": "Retrieve product information from the product database. Use this to answer questions about products, availability, pricing, features, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What product information are you looking for?"
                }
            },
            "required": ["query"]
        }
    }
]

SYSTEM_PROMPT = """You are a knowledgeable and friendly sales agent. Your job is to help customers find the right products and suggest upgrades or complementary products when appropriate.

Guidelines:
- Be helpful and genuine, not pushy
- Answer questions honestly about products
- When appropriate, suggest upgrades or complementary products that add real value
- You can offer discounts or special promotions if they seem hesitant (e.g., "I can offer 10% off if you buy today")
- Always prioritize customer satisfaction over making a sale
- If a product isn't available or doesn't exist, be honest about it

Tone: Professional but conversational, knowledgeable, enthusiastic about products."""

def fetch_product_data(query):
    """Fetch product data from the Google Sheet API"""
    try:
        response = requests.get(
            SHEET_API_URL,
            params={"token": SHEET_TOKEN},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        return data
    except Exception as e:
        return {"error": f"Failed to fetch product data: {str(e)}"}

def run_sales_agent(user_message):
    """Run the sales agent with Claude"""
    
    client = get_client()
    messages = [{"role": "user", "content": user_message}]
    
    # Call Claude with tool use
    response = client.messages.create(
        model="claude-opus-4-5-20251101",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        tools=tools,
        messages=messages
    )
    
    # Process response and handle tool use
    while response.stop_reason == "tool_use":
        tool_use_block = next(
            (block for block in response.content if block.type == "tool_use"),
            None
        )
        
        if not tool_use_block:
            break
        
        messages.append({"role": "assistant", "content": response.content})
        
        # Execute the tool
        if tool_use_block.name == "get_product_data":
            query = tool_use_block.input.get("query", "")
            product_data = fetch_product_data(query)
            tool_result = json.dumps(product_data)
        else:
            tool_result = json.dumps({"error": "Unknown tool"})
        
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_block.id,
                    "content": tool_result
                }
            ]
        })
        
        # Get Claude's next response
        response = client.messages.create(
            model="claude-opus-4-5-20251101",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages
        )
    
    # Extract final text response
    final_response = next(
        (block.text for block in response.content if hasattr(block, "text")),
        "I couldn't generate a response."
    )
    
    return final_response

@app.route('/', methods=['GET', 'POST', 'OPTIONS'])
def sales_agent():
    """Sales agent endpoint and UI"""
    
    # Enable CORS
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST',
            'Access-Control-Allow-Headers': 'Content-Type',
        }
        return ('', 204, headers)
    
    # If GET request with no question parameter, serve HTML UI
    if request.method == 'GET' and not request.args.get('question'):
        return get_chat_html()
    
    try:
        # Get question from request
        if request.method == 'POST':
            request_json = request.get_json()
            question = request_json.get('question') if request_json else None
        else:
            question = request.args.get('question')
        
        if not question:
            return jsonify({"error": "No question provided"}), 400
        
        # Run the agent
        response = run_sales_agent(question)
        
        return jsonify({
            "question": question,
            "response": response
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
