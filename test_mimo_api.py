"""Diagnostic script to test MiMo API response format"""
import os
import asyncio
import httpx
import json
from dotenv import load_dotenv

load_dotenv()

MIMO_API_KEY = os.getenv('MIMO_API_KEY', '')
MIMO_BASE_URL = os.getenv('MIMO_BASE_URL', 'https://api.xiaomimimo.com/v1')
MIMO_API_URL = f'{MIMO_BASE_URL}/chat/completions'

async def test_api():
    headers = {
        'Authorization': f'Bearer {MIMO_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    # Test 1: Simple message without tools
    payload1 = {
        'model': 'mimo-v2-flash',
        'messages': [
            {'role': 'system', 'content': 'You are a helpful brewery AI assistant.'},
            {'role': 'user', 'content': 'hi'}
        ],
        'temperature': 0.1,
        'max_tokens': 100,
    }
    
    print("=" * 60)
    print("TEST 1: Simple 'hi' message (no tools)")
    print(f"URL: {MIMO_API_URL}")
    print(f"API Key configured: {bool(MIMO_API_KEY)}")
    print(f"API Key prefix: {MIMO_API_KEY[:20]}...")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(MIMO_API_URL, headers=headers, json=payload1)
            print(f"\nStatus Code: {resp.status_code}")
            print(f"Response Headers: {dict(resp.headers)}")
            data = resp.json()
            print(f"\nFull Response JSON:")
            print(json.dumps(data, indent=2))
            
            # Check content
            choices = data.get('choices', [])
            if choices:
                msg = choices[0].get('message', {})
                content = msg.get('content', '')
                print(f"\n--- Analysis ---")
                print(f"Message keys: {list(msg.keys())}")
                print(f"Content: '{content}'")
                print(f"Content length: {len(content) if content else 0}")
                print(f"Has tool_calls: {bool(msg.get('tool_calls'))}")
                print(f"Finish reason: {choices[0].get('finish_reason')}")
            else:
                print(f"\n--- No choices in response ---")
                print(f"Response keys: {list(data.keys())}")
        except httpx.HTTPStatusError as e:
            print(f"\nHTTP Error: {e.response.status_code}")
            print(f"Response body: {e.response.text[:1000]}")
        except Exception as e:
            print(f"\nError: {type(e).__name__}: {e}")

asyncio.run(test_api())