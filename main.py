import anthropic
import requests
import json
import os
from flask import Flask, request, jsonify

# Try to import vector_search, but don't fail if missing
try:
    from vector_search import search_products_by_vector
    VECTOR_SEARCH_ERROR = None
except Exception as e:
    print(f"Error importing vector_search: {e}")
    VECTOR_SEARCH_ERROR = str(e)
    search_products_by_vector = None

app = Flask(__name__)


# Configuration
SHEET_API_URL = "https://script.google.com/macros/s/AKfycbx4QRKcj_ikDiBVI4TtxXsg_72BGQn28HpRjOahYfeAW34CyyZ9zvcSP9_jQzsb3OIyBg/exec"
SHEET_TOKEN = "pRjOahYfeAW34CyyZ9zvcSP9"

def get_client():
    return anthropic.Anthropic()

# Define the RAG-enhanced tools
tools = [
    {
        "name": "search_products",
        "description": "Search for relevant products using semantic vector search.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What products is the customer looking for?"
                },
                "num_results": {
                    "type": "integer",
                    "description": "How many product recommendations to return (default: 5)",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_current_inventory",
        "description": "Get current product availability and pricing from the product database.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_name": {
                    "type": "string",
                    "description": "Name of the product to check"
                }
            },
            "required": ["product_name"]
        }
    }
]

def search_products_tool(query, num_results=5):
    """Search products using vector search"""
    if search_products_by_vector is None:
        # Return dummy data if vector_search not available
        print("[DUMMY DATA] vector_search not available, using mock results")
        return {
            "status": "success", 
            "results": [
                {"name": "Ceramic Guard Ultra", "price": 89.0, "match": 0.8},
                {"name": "Engine Cleaner MV40", "price": 34.50, "match": 0.7}
            ],
            "note": "[DUMMY DATA]"
        }
    
    try:
        results = search_products_by_vector(query, num_results)
        return {"status": "success", "results": results, "note": "[REAL DATA]"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def get_inventory_tool(product_name):
    """Get inventory from Google Sheets"""
    try:
        response = requests.get(
            SHEET_API_URL,
            params={"product_name": product_name, "token": SHEET_TOKEN}
        )
        data = response.json()
        return {"status": "success", "inventory": data}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def process_tool_call(tool_name, tool_input, logs):
    """Process tool calls from Claude"""
    if tool_name == "search_products":
        logs.append(f"🔧 Calling search_products with query: '{tool_input.get('query')}'")
        result = search_products_tool(
            tool_input.get("query"),
            tool_input.get("num_results", 5)
        )
        data_type = result.get("note", "unknown")
        logs.append(f"✓ Got {len(result.get('results', []))} results {data_type}")
        return result
    elif tool_name == "get_current_inventory":
        logs.append(f"🔧 Calling get_current_inventory for: '{tool_input.get('product_name')}'")
        result = get_inventory_tool(tool_input.get("product_name"))
        logs.append(f"✓ Inventory check complete")
        return result
    else:
        logs.append(f"❌ Unknown tool: {tool_name}")
        return {"status": "error", "message": f"Unknown tool: {tool_name}"}

def sales_agent(user_message):
    """Run the sales agent with Claude, returns (response, logs)"""
    client = get_client()
    logs = []
    
    logs.append("🟢 Agent started")
    if search_products_by_vector is None:
        logs.append(f"⚠️  Using DUMMY PRODUCT DATA")
        if VECTOR_SEARCH_ERROR:
            logs.append(f"   Error: {VECTOR_SEARCH_ERROR}")
    else:
        logs.append("✅ Using REAL VECTOR SEARCH")
    logs.append(f"📝 Question: {user_message}")
   
    # Load system prompt
    system_prompt = load_system_prompt()
    
    messages = [
        {"role": "user", "content": user_message}
    ]
    
    # Agentic loop
    loop_count = 0
    while True:
        loop_count += 1
        logs.append(f"")
        logs.append(f"🔄 Loop {loop_count}: Calling Claude...")
        
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1024,
            system=system_prompt,
            tools=tools,
            messages=messages
        )
        
        logs.append(f"⬅️ Response type: {response.stop_reason}")
        
        # Check if we're done
        if response.stop_reason == "end_turn":
            logs.append(f"✅ Agent finished")
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text, logs
            return "No response generated", logs
        
        # Process tool calls
        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_result = process_tool_call(block.name, block.input, logs)
                    
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(tool_result)
                    })
            
            messages.append({"role": "user", "content": tool_results})
        else:
            logs.append(f"⚠️ Unexpected stop reason: {response.stop_reason}")
            break
        
        if loop_count > 10:
            logs.append("❌ Max loops reached")
            break
    
    return "Agent loop ended unexpectedly", logs

def load_system_prompt():
    """Load system prompt from file or return default"""
    try:
        with open("system_prompt_rag.txt", "r") as f:
            return f.read()
    except:
        return """You are a friendly and knowledgeable sales agent for an automotive product company. 
Your goal is to help customers find the right products for their needs and recommend suitable items.

When a customer asks about products:
1. Use the search_products tool to find relevant items
2. Check inventory with get_current_inventory if needed
3. Provide friendly recommendations with product details and prices
4. Suggest complementary products when appropriate

Be helpful, professional, and focus on genuinely matching customer needs."""

# Routes
@app.route('/', methods=['GET'])
def home():
    """Root endpoint - returns HTML interface with logging pane"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Sales Agent</title>
        <style>
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background: #f5f5f5;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
            }
            h1 { 
                color: #333;
                margin-bottom: 20px;
            }
            .main-content {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
            }
            .chat-section, .logs-section {
                background: white;
                border-radius: 8px;
                padding: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .logs-section {
                grid-column: 1 / -1;
            }
            .input-group {
                display: flex;
                gap: 10px;
                margin-bottom: 20px;
            }
            input[type="text"] {
                flex: 1;
                padding: 12px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 14px;
            }
            input[type="text"]:focus {
                outline: none;
                border-color: #0066cc;
                box-shadow: 0 0 4px rgba(0,102,204,0.2);
            }
            button {
                padding: 12px 24px;
                background: #0066cc;
                color: white;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
                font-weight: 500;
            }
            button:hover {
                background: #0052a3;
            }
            button:disabled {
                background: #999;
                cursor: not-allowed;
            }
            #response {
                background: #f9f9f9;
                padding: 15px;
                border-radius: 4px;
                border-left: 4px solid #0066cc;
                line-height: 1.6;
                color: #333;
                min-height: 100px;
            }
            #logs {
                background: #f0f0f0;
                padding: 15px;
                border-radius: 4px;
                font-family: 'Courier New', monospace;
                font-size: 12px;
                line-height: 1.6;
                color: #333;
                max-height: 300px;
                overflow-y: auto;
                border: 1px solid #ddd;
            }
            .log-entry {
                margin: 4px 0;
                white-space: pre-wrap;
                word-break: break-word;
            }
            .loading {
                color: #0066cc;
                font-style: italic;
            }
            .error {
                color: #d32f2f;
                font-weight: bold;
            }
            h2 {
                font-size: 16px;
                margin-top: 0;
                color: #333;
                border-bottom: 2px solid #0066cc;
                padding-bottom: 10px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 Sales Agent</h1>
            
            <div class="main-content">
                <div class="chat-section">
                    <h2>Chat</h2>
                    <div class="input-group">
                        <input type="text" id="question" placeholder="Ask about products..." />
                        <button onclick="askAgent()" id="askBtn">Ask</button>
                    </div>
                    <div id="response"></div>
                </div>
                
                <div class="chat-section">
                    <h2>Response</h2>
                    <div id="responseText" style="min-height: 150px;"></div>
                </div>
                
                <div class="logs-section">
                    <h2>Debug Logs</h2>
                    <div id="logs"></div>
                </div>
            </div>
        </div>
        
        <script>
            function addLog(message) {
                const logsDiv = document.getElementById('logs');
                const entry = document.createElement('div');
                entry.className = 'log-entry';
                entry.textContent = message;
                logsDiv.appendChild(entry);
                logsDiv.scrollTop = logsDiv.scrollHeight;
            }
            
            function clearLogs() {
                document.getElementById('logs').innerHTML = '';
            }
            
            function askAgent() {
                const q = document.getElementById('question').value;
                if (!q) return;
                
                clearLogs();
                addLog('Sending request...');
                document.getElementById('response').innerHTML = '';
                document.getElementById('responseText').innerHTML = '';
                document.getElementById('askBtn').disabled = true;
                
                fetch('/ask?question=' + encodeURIComponent(q))
                    .then(r => r.json())
                    .then(data => {
                        // Display response
                        document.getElementById('responseText').innerHTML = '<p>' + escapeHtml(data.response) + '</p>';
                        
                        // Display logs
                        clearLogs();
                        data.logs.forEach(log => addLog(log));
                        
                        addLog('✅ Done');
                    })
                    .catch(err => {
                        clearLogs();
                        addLog('❌ Error: ' + err.message);
                        document.getElementById('response').innerHTML = '<p style="color: red;">Error: ' + err.message + '</p>';
                    })
                    .finally(() => {
                        document.getElementById('askBtn').disabled = false;
                    });
            }
            
            function escapeHtml(text) {
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }
            
            document.getElementById('question').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') askAgent();
            });
        </script>
    </body>
    </html>
    '''

@app.route('/ask', methods=['GET'])
def ask():
    """API endpoint for asking the agent"""
    question = request.args.get('question', '')
    if not question:
        return jsonify({"error": "No question provided", "logs": []}), 400
    
    try:
        response, logs = sales_agent(question)
        return jsonify({"response": response, "logs": logs})
    except Exception as e:
        return jsonify({"error": str(e), "logs": [f"❌ Exception: {str(e)}"]}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200

# Main entry point
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
