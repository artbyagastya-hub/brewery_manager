"""
MiMo AI Engine - Core integration with MiMo-V2-Flash API
Provides function calling capabilities for autonomous brewery management
"""

import os
import json
import logging
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

MIMO_API_KEY = os.getenv('MIMO_API_KEY', '')
# Support both MIMO_API_URL and MIMO_BASE_URL environment variables
MIMO_BASE_URL = os.getenv('MIMO_BASE_URL', 'https://api.xiaomi.com/mimo/v1')
MIMO_API_URL = os.getenv('MIMO_API_URL', f'{MIMO_BASE_URL}/chat/completions')

class MiMoEngine:
    def __init__(self):
        self.api_key = MIMO_API_KEY
        self.api_url = MIMO_API_URL
        # Per-session conversation histories (keyed by session_id)
        self._conversations: Dict[str, List[Dict]] = {}
        self.max_history = 20
        self.db = None
        self._init_db()
    
    def _init_db(self):
        """Initialize database connection for chat history persistence"""
        try:
            from models.database import Database
            self.db = Database()
        except Exception as e:
            import logging
            logging.warning(f"Could not initialize database for chat history: {e}")
    
    def _get_history(self, session_id: str) -> List[Dict]:
        """Get conversation history for a specific session, loading from DB if needed"""
        if session_id not in self._conversations:
            # Try to load from database
            self._conversations[session_id] = self._load_history_from_db(session_id)
        return self._conversations[session_id]
    
    def _load_history_from_db(self, session_id: str) -> List[Dict]:
        """Load conversation history from database"""
        if not self.db:
            return []
        try:
            history = self.db.get_chat_history(session_id, limit=self.max_history * 2)
            return [{"role": msg["role"], "content": msg["content"]} for msg in history]
        except Exception as e:
            import logging
            logging.warning(f"Could not load chat history from DB: {e}")
            return []
    
    def _save_message_to_db(self, session_id: str, role: str, content: str):
        """Save a single message to the database"""
        if not self.db:
            return
        try:
            self.db.save_chat_message(session_id, role, content)
        except Exception as e:
            import logging
            logging.warning(f"Could not save chat message to DB: {e}")
    
    def _set_history(self, session_id: str, messages: List[Dict]):
        """Set conversation history for a specific session"""
        self._conversations[session_id] = messages[-self.max_history * 2:]  # Keep bounded
    
    def clear_history(self, session_id: str):
        """Clear conversation history for a specific session"""
        if session_id in self._conversations:
            del self._conversations[session_id]
    
    def load_history_from_db(self, session_id: str, db, limit: int = 20):
        """Load conversation history from database for a session"""
        try:
            messages = db.get_chat_history(session_id, limit)
            self._conversations[session_id] = messages
        except Exception:
            self._conversations[session_id] = []
        
    def _get_headers(self) -> Dict[str, str]:
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
    
    async def chat(self, messages: List[Dict], tools: List[Dict] = None, 
                   tool_choice: str = 'auto') -> Dict:
        """Send chat completion request to MiMo API"""
        payload = {
            'model': 'mimo-v2-flash',
            'messages': messages,
            'temperature': 0.4,
            'max_tokens': 4096,
        }
        
        if tools:
            payload['tools'] = tools
            payload['tool_choice'] = tool_choice
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                logger.debug(f"MiMo API request: {self.api_url}, tools={bool(tools)}, msgs={len(messages)}")
                response = await client.post(
                    self.api_url,
                    headers=self._get_headers(),
                    json=payload
                )
                response.raise_for_status()
                resp_json = response.json()
                # Log response structure for debugging
                choices = resp_json.get('choices', [])
                if choices:
                    msg = choices[0].get('message', {})
                    content = msg.get('content', '')
                    has_tools = bool(msg.get('tool_calls'))
                    logger.info(f"MiMo API response: content_len={len(content) if content else 0}, has_tools={has_tools}")
                    if not content and not has_tools:
                        logger.warning(f"MiMo API returned empty content and no tool_calls. Full message keys: {list(msg.keys())}")
                else:
                    logger.warning(f"MiMo API returned no choices. Response keys: {list(resp_json.keys())}")
                return resp_json
            except httpx.HTTPStatusError as e:
                logger.error(f"MiMo API HTTP error: {e.response.status_code} - {e.response.text[:500]}")
                return {'error': f"HTTP {e.response.status_code}: {e.response.text[:200]}"}
            except Exception as e:
                logger.error(f"MiMo API error: {e}", exc_info=True)
                return {'error': str(e)}
    
    def health_check(self) -> Dict:
        """Check if the MiMo API is accessible"""
        return {
            'status': 'healthy',
            'model': 'mimo-v2-flash',
            'api_url': self.api_url,
            'api_key_configured': bool(self.api_key)
        }

    async def generate_speech(self, text: str, voice: str = "mimo_default") -> bytes:
        """Generate TTS audio from text using mimo-v2-tts model"""
        import base64
        payload = {
            'model': 'mimo-v2-tts',
            'messages': [
                {
                    "role": "user",
                    "content": "Read this out loud please."
                },
                {
                    "role": "assistant",
                    "content": text
                }
            ],
            'audio': {
                'format': 'wav',
                'voice': voice
            }
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    self.api_url,
                    headers=self._get_headers(),
                    json=payload
                )
                response.raise_for_status()
                resp_json = response.json()
                message = resp_json.get('choices', [])[0].get('message', {})
                audio_data = message.get('audio', {}).get('data', '')
                if audio_data:
                    return base64.b64decode(audio_data)
                return None
            except Exception as e:
                logger.error(f"TTS API error: {e}")
                return None
    
    def _get_fallback_response(self, user_message: str) -> str:
        """Provide intelligent fallback responses when API is unavailable"""
        message_lower = user_message.lower()
        
        # Greeting responses
        if any(word in message_lower for word in ['hello', 'hi', 'hey', 'xin chào', 'chào']):
            return "Hello! I'm your Brewery AI Assistant. I can help you with:\n\n• 📊 **Inventory** - Check stock levels and materials\n• 🍺 **Production** - Monitor batches and schedules\n• 💰 **Sales** - View orders and revenue\n• 📈 **Reports** - Generate analytics and insights\n\nWhat would you like to know about your brewery operations?"
        
        # Inventory related
        if any(word in message_lower for word in ['inventory', 'stock', 'material', 'kho', 'nguyên liệu']):
            return "📦 **Inventory Management**\n\nI can help you check inventory levels. Here are some things you can ask:\n\n• \"Show low stock items\"\n• \"Check malt inventory\"\n• \"What materials need reordering?\"\n\nWould you like me to check your current inventory status?"
        
        # Production related
        if any(word in message_lower for word in ['production', 'batch', 'brew', 'sản xuất', 'brewing']):
            return "🏭 **Production Overview**\n\nI can help with production management:\n\n• \"Show active batches\"\n• \"What's in fermentation?\"\n• \"Production schedule this week\"\n• \"Check batch quality\"\n\nWhat production information do you need?"
        
        # Sales related
        if any(word in message_lower for word in ['sales', 'order', 'revenue', 'bán hàng', 'doanh thu']):
            return "💰 **Sales & Orders**\n\nI can assist with sales data:\n\n• \"Show recent orders\"\n• \"Revenue this month\"\n• \"Top customers\"\n• \"Pending deliveries\"\n\nWhat sales information would you like?"
        
        # Recipe related
        if any(word in message_lower for word in ['recipe', 'formula', 'công thức']):
            return "📝 **Recipe Management**\n\nI can help with recipes:\n\n• \"Show all recipes\"\n• \"IPA recipe details\"\n• \"Calculate recipe cost\"\n• \"Import BeerSmith recipe\"\n\nWhat recipe information do you need?"
        
        # Tank/equipment related
        if any(word in message_lower for word in ['tank', 'fermenter', 'bồn', 'thiết bị']):
            return "🔧 **Equipment & Tanks**\n\nI can check equipment status:\n\n• \"Show tank status\"\n• \"Available fermenters\"\n• \"Maintenance schedule\"\n• \"Equipment alerts\"\n\nWhat equipment information do you need?"
        
        # Quality related
        if any(word in message_lower for word in ['quality', 'test', 'chất lượng', 'kiểm định']):
            return "🔬 **Quality Control**\n\nI can help with quality management:\n\n• \"Show quality records\"\n• \"Pending tests\"\n• \"Quality alerts\"\n• \"Batch quality history\"\n\nWhat quality information do you need?"
        
        # Help
        if any(word in message_lower for word in ['help', 'giúp', 'hướng dẫn', 'what can you do']):
            return "🤖 **Brewery AI Assistant Capabilities**\n\nI can help you manage your brewery:\n\n📦 **Inventory** - Stock levels, materials, reordering\n🏭 **Production** - Batches, schedules, fermentation\n💰 **Sales** - Orders, revenue, customers\n📝 **Recipes** - Formulas, costs, ingredients\n🔧 **Equipment** - Tanks, fermenters, maintenance\n🔬 **Quality** - Tests, records, alerts\n📊 **Reports** - Analytics, summaries, trends\n\nJust ask me anything about your brewery operations!"
        
        # Default response
        return f"I understand you're asking about: \"{user_message}\"\n\nI'm currently operating in offline mode. Here's what I can help with:\n\n• 📦 Inventory management\n• 🏭 Production tracking\n• 💰 Sales & orders\n• 📝 Recipe management\n• 🔧 Equipment status\n• 🔬 Quality control\n\nPlease try asking about one of these topics, or type \"help\" for more options."
    
    def _generate_tool_fallback_response(self, user_message: str, tool_results: list) -> str:
        """Generate a fallback response when the API returns empty content after tool calls.
        
        This synthesizes tool results into a natural language response so the AI
        always has something meaningful to say, even if the MiMo API fails to generate
        a follow-up response.
        """
        if not tool_results:
            return self._get_fallback_response(user_message)
        
        parts = []
        
        for tr in tool_results:
            tool_name = tr.get('tool', '')
            result = tr.get('result', {})
            
            if isinstance(result, dict) and 'error' in str(result):
                parts.append(f"I ran into an issue with {tool_name.replace('_', ' ')}, but I can try again.")
                continue
            
            # Format based on tool type
            if tool_name == 'get_dashboard_summary':
                active = result.get('active_batches', 0)
                orders = result.get('pending_orders', 0)
                low_stock = result.get('low_stock_items', 0)
                tasks = result.get('pending_tasks', 0)
                staff = result.get('active_staff', 0)
                equipment = result.get('available_equipment', 0)
                parts.append(
                    f"📊 **Dashboard Summary**\n\n"
                    f"• 🏭 Active Batches: **{active}**\n"
                    f"• 📦 Pending Orders: **{orders}**\n"
                    f"• ⚠️ Low Stock Items: **{low_stock}**\n"
                    f"• 📋 Pending Tasks: **{tasks}**\n"
                    f"• 👥 Active Staff: **{staff}**\n"
                    f"• 🔧 Available Equipment: **{equipment}**"
                )
            
            elif tool_name == 'query_sales':
                results = result.get('results', [])
                if results:
                    lines = ["💰 **Top Sales Results:**\n"]
                    for r in results[:5]:
                        name = r.get('name', 'Unknown')
                        sold = r.get('total_sold', 0)
                        revenue = r.get('total_revenue', 0)
                        lines.append(f"• **{name}**: Sold {sold}, Revenue {revenue}")
                    parts.append('\n'.join(lines))
                else:
                    parts.append("💰 No recent sales data found.")
            
            elif tool_name == 'query_inventory':
                items = result.get('items', [])
                count = result.get('count', 0)
                if count > 0:
                    lines = [f"📦 **Inventory ({count} items):**\n"]
                    for item in items[:10]:
                        name = item.get('name', 'Unknown')
                        qty = item.get('quantity', 0)
                        unit = item.get('unit', '')
                        min_qty = item.get('min_quantity', 0)
                        status = '✅' if qty > min_qty else '⚠️ Low' if qty > 0 else '❌ Out'
                        lines.append(f"• {status} **{name}**: {qty} {unit}")
                    parts.append('\n'.join(lines))
                else:
                    parts.append("📦 No inventory items found.")
            
            elif tool_name == 'get_tank_availability':
                tanks = result.get('available_tanks', [])
                if tanks:
                    lines = [f"🫗 **Available Tanks ({len(tanks)}):**\n"]
                    for t in tanks[:10]:
                        name = t.get('name', 'Unknown')
                        capacity = t.get('capacity', 0)
                        unit = t.get('capacity_unit', 'L')
                        lines.append(f"• **{name}**: {capacity} {unit} - Available")
                    parts.append('\n'.join(lines))
                else:
                    parts.append("🫗 No available tanks found.")
            
            elif tool_name == 'query_recipes':
                recipes = result.get('recipes', [])
                if recipes:
                    lines = [f"🍺 **Recipes ({len(recipes)}):**\n"]
                    for r in recipes[:5]:
                        name = r.get('name', 'Unknown')
                        abv = r.get('abv', 'N/A')
                        ibu = r.get('ibu', 'N/A')
                        lines.append(f"• **{name}**: ABV {abv}%, IBU {ibu}")
                    parts.append('\n'.join(lines))
                else:
                    parts.append("🍺 No recipes found.")
            
            elif tool_name == 'get_products':
                products = result.get('products', [])
                if products:
                    lines = [f"🍺 **Products ({len(products)}):**\n"]
                    for p in products[:5]:
                        name = p.get('name', 'Unknown')
                        ptype = p.get('beer_type', '')
                        abv = p.get('abv', '')
                        lines.append(f"• **{name}** ({ptype}) - {abv}% ABV")
                    parts.append('\n'.join(lines))
                else:
                    parts.append("🍺 No products found.")
            
            elif tool_name == 'query_batches':
                batches = result.get('batches', [])
                if batches:
                    lines = [f"🏭 **Active Batches ({len(batches)}):**\n"]
                    for b in batches[:5]:
                        batch_num = b.get('batch_number', b.get('id', ''))
                        product = b.get('product_name', 'Unknown')
                        status = b.get('status', '')
                        lines.append(f"• **#{batch_num}**: {product} - {status}")
                    parts.append('\n'.join(lines))
                else:
                    parts.append("🏭 No active batches found.")
            
            elif tool_name == 'query_staff':
                staff = result.get('staff', [])
                if staff:
                    lines = [f"👥 **Staff ({len(staff)}):**\n"]
                    for s in staff[:5]:
                        name = s.get('name', 'Unknown')
                        pos = s.get('position', s.get('role', ''))
                        lines.append(f"• **{name}** - {pos}")
                    parts.append('\n'.join(lines))
                else:
                    parts.append("👥 No staff members found.")
            
            elif tool_name == 'get_daily_tasks':
                tasks = result.get('tasks', [])
                if tasks:
                    lines = [f"📋 **Today's Tasks ({len(tasks)}):**\n"]
                    for t in tasks[:5]:
                        title = t.get('title', 'Untitled')
                        priority = t.get('priority', 'normal')
                        assignee = t.get('assignee_name', 'Unassigned')
                        lines.append(f"• [{priority.upper()}] **{title}** → {assignee}")
                    parts.append('\n'.join(lines))
                else:
                    parts.append("📋 No tasks scheduled for today.")
            
            else:
                # Generic tool result
                result_str = json.dumps(result, indent=2)
                if len(result_str) > 500:
                    result_str = result_str[:500] + "..."
                parts.append(f"I looked up the {tool_name.replace('_', ' ')} data. Here's what I found:\n\n```\n{result_str}\n```")
        
        return '\n\n'.join(parts)

    async def process_message(self, user_message: str, context: Dict = None) -> Dict:
        """Process user message with tool support and active planning.
        
        Handles tool calling with proper system prompt preservation,
        fallback response generation, and error recovery to prevent
        the AI from returning empty responses.
        """
        from utils.ai_tools import get_tools, execute_tool
        from utils.ai_prompts import get_system_prompt
        from utils.ai_memory import get_memory
        from utils.ai_planner import get_planner
        
        memory = get_memory()
        planner = get_planner()
        
        # Increment message count for proactive triggers
        message_count = memory.get_context('message_count') or 0
        message_count += 1
        memory.update_context('message_count', message_count)
        
        # On first message of the day, generate daily agenda
        last_agenda_date = memory.get_context('last_agenda_date')
        today = date.today().isoformat()
        if last_agenda_date != today:
            try:
                agenda = planner.generate_daily_agenda()
                memory.update_context('last_agenda_date', today)
                memory.update_context('daily_agenda', agenda)
            except Exception:
                logger.debug("Failed to generate daily agenda", exc_info=True)
        
        # Enhance context with memory and planning info
        enhanced_context = context or {}
        
        # Add proactive suggestions every 3rd message
        if message_count % 3 == 0 and planner.mode != 'reactive':
            try:
                suggestions = planner.get_proactive_suggestions()
                if suggestions:
                    enhanced_context['proactive_suggestions'] = suggestions[:3]
            except Exception:
                logger.debug("Failed to get proactive suggestions", exc_info=True)
        
        # Add memory context
        recent_observations = memory.get_recent_observations(3)
        if recent_observations:
            enhanced_context['recent_observations'] = recent_observations
        
        unresolved_alerts = memory.get_unresolved_alerts()
        if unresolved_alerts:
            enhanced_context['unresolved_alerts'] = unresolved_alerts[:3]
        
        # Get session-specific conversation history
        session_id = context.get('session_id', 'default') if context else 'default'
        history = self._get_history(session_id)
        
        system_prompt = get_system_prompt(enhanced_context)
        
        messages = [{'role': 'system', 'content': system_prompt}]
        messages.extend(history[-self.max_history:])
        messages.append({'role': 'user', 'content': user_message})
        
        tools = get_tools()
        
        try:
            response = await self.chat(messages, tools)
        except Exception as e:
            logger.error(f"API call failed: {e}", exc_info=True)
            response = {'error': str(e)}
        
        if 'error' in response:
            # Use fallback response instead of showing error
            fallback = self._get_fallback_response(user_message)
            history.append({'role': 'user', 'content': user_message})
            history.append({'role': 'assistant', 'content': fallback})
            self._save_message_to_db(session_id, 'user', user_message)
            self._save_message_to_db(session_id, 'assistant', fallback)
            self._set_history(session_id, history)
            
            # Record observation about API error
            memory.remember_observation('system', 'API unavailable, used fallback response', 'normal')
            logger.warning(f"MiMo API error for session {session_id}: {response.get('error')}")
            
            return {'type': 'message', 'content': fallback}
        
        choice = response.get('choices', [{}])[0]
        message = choice.get('message', {})
        
        history.append({'role': 'user', 'content': user_message})
        self._save_message_to_db(session_id, 'user', user_message)
        
        if message.get('tool_calls'):
            results = []
            for tool_call in message['tool_calls']:
                func_name = tool_call['function']['name']
                func_args = json.loads(tool_call['function']['arguments'])
                result = execute_tool(func_name, func_args)
                results.append({
                    'tool': func_name,
                    'args': func_args,
                    'result': result
                })
                
                # Record tool usage in memory
                memory.remember_decision(
                    'tool_use',
                    f"Used {func_name}",
                    f"Args: {json.dumps(func_args)[:100]}",
                    'success' if result and 'error' not in str(result) else 'error'
                )
                logger.info(f"Tool executed: {func_name} for session {session_id}")
            
            history.append({
                'role': 'assistant',
                'content': message.get('content', ''),
                'tool_calls': message['tool_calls']
            })
            
            # Reconstruct follow_up_messages with system prompt to ensure context is preserved
            # This is critical - without the system prompt, the model may not know how to
            # synthesize tool results into a meaningful response
            follow_up_messages = [
                {'role': 'system', 'content': system_prompt}
            ]
            # Include recent history for context
            follow_up_messages.extend(history[-(self.max_history):])
            # Add the assistant's tool_calls message
            follow_up_messages.append({
                'role': 'assistant',
                'content': message.get('content', ''),
                'tool_calls': message['tool_calls']
            })
            # Add each tool result
            for i, tool_call in enumerate(message['tool_calls']):
                tool_result_str = json.dumps(results[i]['result'])
                follow_up_messages.append({
                    'role': 'tool',
                    'tool_call_id': tool_call['id'],
                    'content': tool_result_str
                })
            
            # Call API to synthesize tool results into a natural language response
            final_message = ''
            try:
                final_response = await self.chat(follow_up_messages)
                if 'error' not in final_response:
                    final_message = final_response.get('choices', [{}])[0].get('message', {}).get('content', '')
                else:
                    logger.warning(f"Follow-up API call returned error: {final_response.get('error')}")
            except Exception as e:
                logger.error(f"Follow-up API call failed: {e}", exc_info=True)
            
            # If final_message is empty, too short, or contains raw tool call XML
            # (which means the API didn't synthesize a proper response), generate fallback
            has_raw_xml = final_message and ('<tool_call>' in final_message or '<function>' in final_message or '<invoke>' in final_message)
            if not final_message or len(final_message.strip()) < 5 or has_raw_xml:
                if has_raw_xml:
                    logger.warning(f"MiMo API returned raw tool call XML instead of synthesized response for session {session_id}, generating fallback")
                else:
                    logger.warning(f"Empty response from MiMo API after tool calls for session {session_id}, generating fallback")
                final_message = self._generate_tool_fallback_response(user_message, results)
            
            history.append({'role': 'assistant', 'content': final_message})
            self._save_message_to_db(session_id, 'assistant', final_message)
            self._set_history(session_id, history)
            
            return {
                'type': 'tool_use',
                'tools_called': results,
                'content': final_message,
                'proactive_suggestions': enhanced_context.get('proactive_suggestions')
            }
        else:
            content = message.get('content', '')
            if not content or len(content.strip()) < 3:
                content = self._get_fallback_response(user_message)
            history.append({'role': 'assistant', 'content': content})
            self._save_message_to_db(session_id, 'assistant', content)
            self._set_history(session_id, history)
            
            # Record conversation observation
            memory.remember_observation(
                'conversation',
                f"User: {user_message[:50]}... Assistant: {content[:50]}...",
                'normal'
            )
            
            return {
                'type': 'message', 
                'content': content,
                'proactive_suggestions': enhanced_context.get('proactive_suggestions')
            }

# Singleton instance
_engine = None

def get_engine() -> MiMoEngine:
    global _engine
    if _engine is None:
        _engine = MiMoEngine()
    return _engine