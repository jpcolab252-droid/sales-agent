import anthropic
import requests
import json
import os
from flask import Flask, request, jsonify
from interface import get_chat_html
from vector_search import search_products_by_vector

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
        "description": "Search for relevant products using semantic vector search. Use this to find products matching customer needs, preferences, or questions. Returns the most relevant products with match scores.",
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

