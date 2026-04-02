#!/usr/bin/env python
"""
Mock Ollama Server for testing BYOS Backend
Simulates Ollama API responses when Ollama is not installed
"""
import json
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

class MockOllamaHandler(BaseHTTPRequestHandler):
    """Mock Ollama API handler"""
    
    def do_GET(self):
        """Handle GET requests"""
        if self.path == "/api/tags":
            self.send_json_response({
                "models": [
                    {
                        "name": "llama3.2:1b",
                        "model": "llama3.2:1b",
                        "modified_at": "2026-02-26T05:00:00Z",
                        "size": 1234567890,
                        "digest": "mock-digest-123"
                    }
                ]
            })
        else:
            self.send_error(404, "Not Found")
    
    def do_POST(self):
        """Handle POST requests"""
        if self.path == "/api/generate":
            self.handle_generate()
        else:
            self.send_error(404, "Not Found")
    
    def handle_generate(self):
        """Handle generate request"""
        try:
            # Read request body
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body)
            
            prompt = data.get("prompt", "")
            model = data.get("model", "llama3.2:1b")
            stream = data.get("stream", False)
            
            # Generate mock response
            response_text = self.generate_mock_response(prompt, model)
            
            if stream:
                # Streaming response (simplified)
                self.send_streaming_response(response_text)
            else:
                # Non-streaming response
                self.send_json_response({
                    "model": model,
                    "created_at": time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                    "response": response_text,
                    "done": True,
                    "total_duration": 500000000,
                    "load_duration": 100000000,
                    "prompt_eval_count": len(prompt.split()),
                    "prompt_eval_duration": 200000000,
                    "eval_count": len(response_text.split()),
                    "eval_duration": 200000000
                })
                
        except Exception as e:
            self.send_error(500, f"Internal Server Error: {str(e)}")
    
    def generate_mock_response(self, prompt: str, model: str) -> str:
        """Generate mock response based on prompt"""
        prompt_lower = prompt.lower()
        
        if "marketing" in prompt_lower or "saas" in prompt_lower:
            return """The best marketing strategy for a SaaS company involves a multi-channel approach:

1. Content Marketing - Create valuable blog posts, whitepapers, and case studies
2. SEO Optimization - Target high-intent keywords and optimize landing pages
3. Paid Advertising - Use Google Ads and LinkedIn for targeted campaigns
4. Email Marketing - Build nurture sequences for lead conversion
5. Social Media - Focus on LinkedIn and Twitter for B2B engagement
6. Product-Led Growth - Offer free trials and freemium plans
7. Customer Success - Leverage existing customers for referrals

The key is to measure everything and optimize based on data-driven insights."""
        
        elif "game" in prompt_lower or "battle" in prompt_lower or "arena" in prompt_lower:
            return """Game Concept: "Nexus Arena" - A futuristic multiplayer battle arena

Core Features:
- 5v5 team-based combat with unique character classes
- Dynamic environmental hazards that change mid-match
- Ability combination system for strategic depth
- Real-time physics-based destruction
- Seasonal content updates with new maps and characters

Gameplay Mechanics:
- Fast-paced 15-minute matches
- Objective-based gameplay (capture points, escort missions)
- Progressive character customization
- Skill-based matchmaking system
- Spectator mode with live commentary

Monetization:
- Battle pass system with cosmetic rewards
- Character unlock system through gameplay
- Premium skins and emotes
- Tournament entry fees with prize pools

This combines the best elements of MOBAs and hero shooters with innovative mechanics."""
        
        elif "machine learning" in prompt_lower or "ai" in prompt_lower:
            return """Machine learning is a subset of artificial intelligence that enables computers to learn and improve from experience without being explicitly programmed.

Key Concepts:
1. **Training Data** - ML models learn patterns from large datasets
2. **Algorithms** - Mathematical procedures that find patterns in data
3. **Models** - The output of training, capable of making predictions
4. **Features** - Individual measurable properties of the data

Types of Machine Learning:
- **Supervised Learning** - Learning from labeled data (classification, regression)
- **Unsupervised Learning** - Finding patterns in unlabeled data (clustering)
- **Reinforcement Learning** - Learning through trial and error with rewards

Real-World Applications:
- Email spam filtering
- Recommendation systems (Netflix, Amazon)
- Image recognition
- Natural language processing
- Self-driving cars
- Medical diagnosis

The process involves feeding data to algorithms, which then create models that can make predictions or decisions based on new, unseen data."""
        
        else:
            return f"""This is a mock response from the {model} model for the prompt: "{prompt[:100]}..."

The system is working correctly and generating responses. This is a simulated response since we're running a mock Ollama server for testing purposes.

Key points:
- The API endpoint is functioning properly
- Request parsing is working
- Response generation is successful
- JSON formatting is correct

The actual Ollama would provide more sophisticated responses based on the trained model's knowledge and capabilities."""
    
    def send_json_response(self, data, status_code=200):
        """Send JSON response"""
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def send_streaming_response(self, response_text):
        """Send streaming response (simplified)"""
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        
        # Send response in chunks
        words = response_text.split()
        for i, word in enumerate(words):
            chunk_data = {
                "model": "llama3.2:1b",
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "response": word + " ",
                "done": False
            }
            self.wfile.write((json.dumps(chunk_data) + "\n").encode())
            time.sleep(0.05)  # Simulate streaming delay
        
        # Final chunk
        final_chunk = {
            "model": "llama3.2:1b",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "response": "",
            "done": True,
            "total_duration": 500000000,
            "load_duration": 100000000,
            "prompt_eval_count": 10,
            "prompt_eval_duration": 200000000,
            "eval_count": len(words),
            "eval_duration": 200000000
        }
        self.wfile.write((json.dumps(final_chunk) + "\n").encode())
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    
    def log_message(self, format, *args):
        """Suppress logging"""
        pass

def start_mock_ollama():
    """Start mock Ollama server"""
    server = HTTPServer(('127.0.0.1', 11434), MockOllamaHandler)
    print("🤖 Mock Ollama Server Started")
    print("📍 URL: http://127.0.0.1:11434")
    print("📋 Available models: llama3.2:1b")
    print("🔄 Ready to handle requests...")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Mock Ollama Server Stopped")
        server.server_close()

if __name__ == "__main__":
    start_mock_ollama()
