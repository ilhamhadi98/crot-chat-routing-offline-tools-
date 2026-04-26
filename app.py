from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from litellm import completion, model_list, token_counter, completion_cost
import psutil
import requests
import os
import json
import time
import sqlite3
import subprocess
import platform
from datetime import datetime

# --- TOOLS DEFINITION ---
def run_shell_command(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        return {"stdout": result.stdout, "stderr": result.stderr, "exit_code": result.returncode}
    except Exception as e:
        return {"error": str(e)}

def read_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return {"content": f.read()}
    except Exception as e:
        return {"error": str(e)}

def list_directory(path="."):
    try:
        return {"items": os.listdir(path)}
    except Exception as e:
        return {"error": str(e)}

def search_memory(query):
    """Search through all past chat messages across all sessions."""
    try:
        with get_db() as conn:
            # Clean query for FTS5
            search_query = query.replace("'", "").replace('"', "")
            results = conn.execute(
                "SELECT content, session_name FROM rag_kb WHERE content MATCH ? LIMIT 5", 
                (f"{search_query}*",)
            ).fetchall()
            if not results:
                return {"message": "No relevant memories found for that query."}
            return {"memories": [dict(r) for r in results]}
    except Exception as e:
        return {"error": str(e)}


# Metadata for LiteLLM
tools_schema = [
    {
        "type": "function",
        "function": {
            "name": "run_shell_command",
            "description": "Execute a shell command on the local system and return the output.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The command to run, e.g., 'dir' or 'python --version'"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the content of a local file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file to read"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List files and folders in a directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the directory, default is current directory"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_memory",
            "description": "Search through all previous conversations and memories across all sessions to find relevant context from the past.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search term or topic to look for in past conversations"}
                },
                "required": ["query"]
            }
        }
    }
]

# Map names to actual functions
available_functions = {
    "run_shell_command": run_shell_command,
    "read_file": read_file,
    "list_directory": list_directory
}


# Coba import GPUtil untuk GPU
try:
    import GPUtil
except ImportError:
    GPUtil = None

app = Flask(__name__)
CORS(app) # Enable CORS for all routes

# Konfigurasi Database
DB_PATH = "crot_engine.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        # Tabel Sesi
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                total_tokens INTEGER DEFAULT 0,
                total_cost REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Tabel Pesan
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_name TEXT,
                role TEXT,
                content TEXT,
                provider TEXT,
                model TEXT,
                tokens INTEGER DEFAULT 0,
                cost REAL DEFAULT 0,
                process_time REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Tabel Provider
        conn.execute("""
            CREATE TABLE IF NOT EXISTS providers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                api_key TEXT,
                status TEXT DEFAULT 'unknown',
                last_checked TIMESTAMP,
                total_usage_cost REAL DEFAULT 0.0,
                available_models TEXT DEFAULT '[]'
            )
        """)
        # Migrasi Kolom (Jika DB sudah ada tapi kolom belum ada)
        try:
            conn.execute("ALTER TABLE providers ADD COLUMN available_models TEXT DEFAULT '[]'")
        except: pass # Kolom sudah ada
        
        try:
            conn.execute("ALTER TABLE messages ADD COLUMN provider TEXT")
            conn.execute("ALTER TABLE messages ADD COLUMN model TEXT")
        except: pass

        # Tabel RAG
        conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS rag_kb USING fts5(content, session_name)")
        
        # Ollama Default
        conn.execute("INSERT OR IGNORE INTO providers (name, api_key, status) VALUES (?,?,?)", ('ollama', 'local', 'online'))

init_db()

@app.route("/")
def index():
    return jsonify({"status": "online", "message": "CROT Backend is running"})

@app.route("/system_stats")
def system_stats():
    try:
        cpu = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory().percent
        gpu_usage = 0
        if GPUtil:
            try:
                gpus = GPUtil.getGPUs()
                if gpus: gpu_usage = round(gpus[0].load * 100, 1)
            except: pass
        
        with get_db() as conn:
            row = conn.execute("SELECT SUM(total_tokens) as t, SUM(total_cost) as c FROM sessions").fetchone()
            global_tokens = row['t'] or 0
            global_cost = row['c'] or 0
            prov_rows = conn.execute("SELECT name, status, total_usage_cost FROM providers").fetchall()
            provider_stats = [dict(r) for r in prov_rows]

        return jsonify({
            "cpu": cpu, "ram": ram, "gpu": gpu_usage,
            "global_tokens": global_tokens, "global_cost": global_cost,
            "provider_stats": provider_stats
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/providers", methods=["GET", "POST", "DELETE"])
def manage_providers():
    if request.method == "GET":
        with get_db() as conn:
            rows = conn.execute("SELECT * FROM providers").fetchall()
            return jsonify([dict(r) for r in rows])
    if request.method == "POST":
        data = request.json
        name = data.get("name").lower()
        key = data.get("api_key")
        with get_db() as conn:
            conn.execute("INSERT OR REPLACE INTO providers (name, api_key) VALUES (?, ?)", (name, key))
            conn.commit()
        return jsonify({"status": "saved"})
    if request.method == "DELETE":
        name = request.args.get("name")
        if name == "ollama": return jsonify({"error": "Cannot delete default provider"}), 400
        with get_db() as conn:
            conn.execute("DELETE FROM providers WHERE name = ?", (name,))
            conn.commit()
        return jsonify({"status": "deleted"})

@app.route("/check_connection/<name>", methods=["GET"])
def check_connection(name):
    name = name.lower() # Case-insensitive check
    with get_db() as conn:
        prov = conn.execute("SELECT * FROM providers WHERE LOWER(name) = ?", (name,)).fetchone()
    if not prov: return jsonify({"status": "error"}), 404
    
    status = "offline"
    found_models = []
    try:
        if name == "ollama":
            r = requests.get("http://localhost:11434/api/tags", timeout=3)
            if r.status_code == 200:
                status = "online"
                found_models = [m["name"] for m in r.json().get("models", [])]
        elif name == "gemini":
            r = requests.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={prov['api_key']}", timeout=5)
            if r.status_code == 200:
                status = "online"
                found_models = [m["name"].replace("models/", "") for m in r.json().get("models", []) if "generateContent" in m.get("supportedGenerationMethods", [])]
        elif name == "openai":
            r = requests.get("https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {prov['api_key']}"}, timeout=5)
            if r.status_code == 200:
                status = "online"
                found_models = [m["id"] for m in r.json().get("data", []) if "gpt" in m["id"]]
        elif name == "openrouter":
            # OpenRouter model list is public, but we can send key if available
            headers = {}
            if prov['api_key'] and prov['api_key'] != 'local':
                headers["Authorization"] = f"Bearer {prov['api_key']}"
            r = requests.get("https://openrouter.ai/api/v1/models", headers=headers, timeout=10)
            if r.status_code == 200:
                status = "online"
                all_models = r.json().get("data", [])
                found_models = []
                for m in all_models:
                    m_id = m.get("id")
                    pricing = m.get("pricing", {})
                    # Check if model is free (pricing is "0" as string from API)
                    if pricing.get("prompt") == "0" and pricing.get("completion") == "0":
                        found_models.append(f"{m_id} (FREE)")
                    else:
                        found_models.append(m_id)
        else:
            status = "online"
            found_models = ["default-model"]

    except Exception as e:
        print(f"Connection check failed for {name}: {str(e)}")
        status = "offline"

    with get_db() as conn:
        conn.execute("UPDATE providers SET status = ?, available_models = ?, last_checked = CURRENT_TIMESTAMP WHERE LOWER(name) = ?", 
                     (status, json.dumps(found_models), name))
        conn.commit()
    return jsonify({"status": status, "models": found_models})

@app.route("/models/<provider>")
def get_models(provider):
    with get_db() as conn:
        row = conn.execute("SELECT available_models FROM providers WHERE name = ?", (provider.lower(),)).fetchone()
        if row:
            return jsonify(json.loads(row['available_models']))
    return jsonify([])

@app.route("/sessions", methods=["GET"])
def list_sessions():
    with get_db() as conn:
        rows = conn.execute("SELECT name, total_tokens, total_cost FROM sessions ORDER BY created_at DESC").fetchall()
        return jsonify([dict(r) for r in rows])

@app.route("/load_session/<name>", methods=["GET"])
def load_session(name):
    with get_db() as conn:
        rows = conn.execute("SELECT role, content FROM messages WHERE session_name = ? ORDER BY created_at ASC", (name,)).fetchall()
        # Also get images for user messages, if they exist
        final_rows = []
        for r in rows:
            row_dict = dict(r)
            if row_dict['role'] == 'user':
                # This is a simplification; image data isn't stored in the DB yet
                # In a real app, you'd fetch image URLs or base64 strings associated with the message
                pass 
            final_rows.append(row_dict)
        return jsonify(final_rows)

@app.route("/session/<path:session_name>", methods=["DELETE"])
def delete_session(session_name):
    try:
        with get_db() as conn:
            # Delete from all relevant tables
            conn.execute("DELETE FROM messages WHERE session_name = ?", (session_name,))
            conn.execute("DELETE FROM rag_kb WHERE session_name = ?", (session_name,))
            conn.execute("DELETE FROM sessions WHERE name = ?", (session_name,))
            conn.commit()
        return jsonify({"status": "deleted", "session_name": session_name})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/chat", methods=["POST"])
def chat():
    start_time = time.time()
    data = request.json
    provider_name = data.get("provider").lower()
    model = data.get("model", "").replace(" (FREE)", "")
    message = data.get("message", "")
    session_name = data.get("session_name", "Default Session")
    history = data.get("history", [])

    # Detect OS
    current_os = platform.system()

    with get_db() as conn:
        prov = conn.execute("SELECT api_key FROM providers WHERE name = ?", (provider_name,)).fetchone()
    api_key = prov['api_key'] if prov else None

    # Simple RAG
    past_context = ""
    try:
        with get_db() as conn:
            search_query = message.replace("'", "")
            results = conn.execute("SELECT content FROM rag_kb WHERE content MATCH ? LIMIT 2", (f"{search_query}*",)).fetchall()
            if results: past_context = "\n---\n".join([r['content'] for r in results])
    except: pass

    # Base System Prompt
    system_instruction = f"You are a powerful AI assistant with access to local system tools. " \
                         f"You are currently running on **{current_os}**. " \
                         f"Use appropriate commands for this OS (e.g., use 'dir' instead of 'ls' on Windows, or 'ipconfig' instead of 'ifconfig'). " \
                         f"If a task requires local information or action, use the provided tools automatically."
    
    messages = [{"role": "system", "content": system_instruction}]
    if past_context:
        messages.append({"role": "system", "content": f"Past context found: {past_context}"})
    
    for h in history:
        messages.append({"role": h["role"], "content": h["content"]})
    
    user_content = [{"type": "text", "text": message}]
    for img in data.get("images", []):
        user_content.append({"type": "image_url", "image_url": {"url": img}})
    messages.append({"role": "user", "content": user_content})

    def generate():
        full_reply = ""
        try:
            # LiteLLM routing
            if provider_name == "gemini": target_model = f"gemini/{model}"
            elif provider_name == "ollama": target_model = f"ollama/{model}"
            elif provider_name == "openrouter": target_model = f"openrouter/{model}"
            else: target_model = model

            # --- FIRST CALL: Check if tools are needed ---
            response = completion(
                model=target_model, 
                messages=messages, 
                api_key=api_key if api_key != 'local' else None,
                tools=tools_schema,
                tool_choice="auto"
            )

            response_message = response.choices[0].message
            tool_calls = getattr(response_message, 'tool_calls', None)
            content = getattr(response_message, 'content', "") or ""

            # Robustness: Some models (like Qwen via Ollama) might put JSON tool calls in 'content'
            if not tool_calls and "{" in content and "arguments" in content:
                try:
                    # Very simple heuristic to catch raw JSON tool calls in text
                    potential_json = content[content.find("{"):content.rfind("}")+1]
                    call_data = json.loads(potential_json)
                    if "name" in call_data:
                        # Convert raw text tool call into a formal tool call object
                        class MockToolCall:
                            def __init__(self, d):
                                self.id = f"call_{int(time.time())}"
                                self.type = "function"
                                class MockFunc:
                                    def __init__(self, name, args):
                                        self.name = name
                                        self.arguments = json.dumps(args)
                                self.function = MockFunc(d['name'], d.get('arguments', {}))
                            def model_dump(self):
                                return {"id": self.id, "type": "function", "function": {"name": self.function.name, "arguments": self.function.arguments}}
                        
                        tool_calls = [MockToolCall(call_data)]
                except: pass

            if tool_calls:
                # Add AI's request to history
                if hasattr(response_message, 'model_dump'):
                    messages.append(response_message.model_dump())
                else:
                    messages.append({"role": "assistant", "content": content, "tool_calls": [t.model_dump() for t in tool_calls]})
                
                # Execute tools
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    tool_msg = f"\n> 🛠️ Using tool: **{function_name}**...\n"
                    yield f"data: {json.dumps({'text': tool_msg})}\n\n"
                    
                    if function_name in available_functions:
                        function_to_call = available_functions[function_name]
                        function_response = function_to_call(**function_args)
                    else:
                        function_response = {"error": f"Tool {function_name} not found"}
                    
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(function_response),
                    })
                
                # Force the model to summarize
                messages.append({"role": "user", "content": "Great, now summarize the findings for the user based on that tool output."})

                # --- SECOND CALL: Get final answer with tool data ---
                response = completion(
                    model=target_model, 
                    messages=messages, 
                    api_key=api_key if api_key != 'local' else None,
                    stream=True
                )
            else:
                # If no tools, just stream the first response (re-call with stream=True)
                response = completion(
                    model=target_model, 
                    messages=messages, 
                    api_key=api_key if api_key != 'local' else None,
                    tools=tools_schema,
                    stream=True
                )

            for chunk in response:
                content = chunk['choices'][0]['delta'].get('content', '')
                if content:
                    full_reply += content
                    yield f"data: {json.dumps({'text': content})}\n\n"

            # (Logging logic remains the same)
            end_time = time.time()
            process_time = round(end_time - start_time, 2)
            try:
                prompt_tokens = token_counter(model=target_model, messages=messages)
                completion_tokens = token_counter(model=target_model, text=full_reply)
                tokens = prompt_tokens + completion_tokens
            except: tokens = len(full_reply.split()) + len(message.split()) + 50
            
            try: cost = completion_cost(model=target_model, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
            except: cost = (tokens / 1000) * 0.00015
            
            with get_db() as conn:
                conn.execute("INSERT OR IGNORE INTO sessions (name) VALUES (?)", (session_name,))
                conn.execute("UPDATE sessions SET total_tokens = total_tokens + ?, total_cost = total_cost + ? WHERE name = ?", (tokens, cost, session_name))
                conn.execute("UPDATE providers SET total_usage_cost = total_usage_cost + ? WHERE name = ?", (cost, provider_name))
                conn.execute("INSERT INTO messages (session_name, role, content, provider, model, tokens, cost, process_time) VALUES (?,?,?,?,?,?,?,?)",
                             (session_name, "user", message, provider_name, model, 0, 0, 0))
                conn.execute("INSERT INTO messages (session_name, role, content, provider, model, tokens, cost, process_time) VALUES (?,?,?,?,?,?,?,?)",
                             (session_name, "assistant", full_reply, provider_name, model, tokens, cost, process_time))
                # Store both user and assistant content in RAG for long-term memory
                conn.execute("INSERT INTO rag_kb (content, session_name) VALUES (?,?)", (f"User said: {message}", session_name))
                conn.execute("INSERT INTO rag_kb (content, session_name) VALUES (?,?)", (f"Assistant replied: {full_reply}", session_name))
                conn.commit()

            yield f"data: {json.dumps({'done': True, 'tokens': tokens, 'cost': round(cost, 6), 'process_time': process_time, 'model': model, 'provider': provider_name})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(generate(), mimetype='text/event-stream')


if __name__ == "__main__":
    app.run(debug=True, port=5000)
