def get_chat_html():
    """Returns the HTML chat interface"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Sales Agent</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px; }
            .container { width: 100%; max-width: 700px; background: white; border-radius: 12px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); overflow: hidden; display: flex; flex-direction: column; height: 80vh; }
            .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; }
            .header h1 { font-size: 24px; }
            .messages { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 15px; }
            .message { padding: 12px 16px; border-radius: 8px; max-width: 85%; word-wrap: break-word; }
            .user-message { background: #667eea; color: white; align-self: flex-end; }
            .agent-message { background: #f0f0f0; color: #333; align-self: flex-start; }
            .input-area { padding: 20px; border-top: 1px solid #eee; display: flex; gap: 10px; }
            input { flex: 1; padding: 12px; border: 1px solid #ddd; border-radius: 8px; font-size: 16px; }
            button { padding: 12px 24px; background: #667eea; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 16px; font-weight: 500; }
            button:hover { background: #764ba2; }
            .loading { color: #999; font-style: italic; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🛍️ Sales Agent</h1>
                <p>Ask me about our products!</p>
            </div>
            <div class="messages" id="messages"></div>
            <div class="input-area">
                <input type="text" id="question" placeholder="Ask about products..." />
                <button onclick="sendMessage()">Send</button>
            </div>
        </div>
        <script>
            async function sendMessage() {
                const input = document.getElementById('question');
                const question = input.value.trim();
                if (!question) return;
                
                const messagesDiv = document.getElementById('messages');
                
                // Add user message
                const userMsg = document.createElement('div');
                userMsg.className = 'message user-message';
                userMsg.textContent = question;
                messagesDiv.appendChild(userMsg);
                
                // Add loading indicator
                const loadingMsg = document.createElement('div');
                loadingMsg.className = 'message agent-message loading';
                loadingMsg.textContent = 'Thinking...';
                messagesDiv.appendChild(loadingMsg);
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
                
                input.value = '';
                
                try {
                    const response = await fetch('/?question=' + encodeURIComponent(question));
                    const data = await response.json();
                    
                    // Remove loading message
                    messagesDiv.removeChild(loadingMsg);
                    
                    // Add agent response
                    const agentMsg = document.createElement('div');
                    agentMsg.className = 'message agent-message';
                    agentMsg.textContent = data.response;
                    messagesDiv.appendChild(agentMsg);
                    messagesDiv.scrollTop = messagesDiv.scrollHeight;
                } catch (error) {
                    messagesDiv.removeChild(loadingMsg);
                    const errorMsg = document.createElement('div');
                    errorMsg.className = 'message agent-message';
                    errorMsg.textContent = 'Error: ' + error.message;
                    messagesDiv.appendChild(errorMsg);
                }
            }
            
            document.getElementById('question').addEventListener('keypress', (e) => {
                if (e.key === 'Enter') sendMessage();
            });
        </script>
    </body>
    </html>
    '''
