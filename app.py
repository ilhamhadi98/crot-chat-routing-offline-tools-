from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from litellm import completion, model_list, token_counter, completion_cost
import psutil
import requests
import os
import json
import time
import sqlite3
from datetime import datetime

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
    with get_db() as conn:
        prov = conn.execute("SELECT * FROM providers WHERE name = ?", (name,)).fetchone()
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
            # Fetch models using Google API directly
            r = requests.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={prov['api_key']}", timeout=5)
            if r.status_code == 200:
                status = "online"
                found_models = [m["name"].replace("models/", "") for m in r.json().get("models", []) if "generateContent" in m.get("supportedGenerationMethods", [])]
        elif name == "openai":
            r = requests.get("https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {prov['api_key']}"}, timeout=5)
            if r.status_code == 200:
                status = "online"
                found_models = [m["id"] for m in r.json().get("data", []) if "gpt" in m["id"]]
        else:
            # Fallback check
            status = "online"
            found_models = ["default-model"]

    except Exception as e:
        print(f"Connection check failed for {name}: {str(e)}")
        status = "offline"

    with get_db() as conn:
        conn.execute("UPDATE providers SET status = ?, available_models = ?, last_checked = CURRENT_TIMESTAMP WHERE name = ?", 
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
    model = data.get("model")
    message = data.get("message", "")
    session_name = data.get("session_name", "Default Session")
    history = data.get("history", [])

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

    messages = []
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
            if provider_name == "gemini":
                target_model = f"gemini/{model}"
            elif provider_name == "ollama":
                target_model = f"ollama/{model}"
            else:
                target_model = model # for openai and others
            
            response = completion(
                model=target_model, messages=messages, api_key=api_key if api_key != 'local' else None, stream=True
            )

            for chunk in response:
                content = chunk['choices'][0]['delta'].get('content', '')
                if content:
                    full_reply += content
                    yield f"data: {json.dumps({'text': content})}\n\n"

            end_time = time.time()
            process_time = round(end_time - start_time, 2)
            
            # Precise token counting
            try:
                prompt_tokens = token_counter(model=target_model, messages=messages)
                completion_tokens = token_counter(model=target_model, text=full_reply)
                tokens = prompt_tokens + completion_tokens
            except:
                # Fallback to rough estimation if token_counter fails
                tokens = len(full_reply.split()) + len(message.split()) + 50
            
            # Precise cost calculation
            try:
                cost = completion_cost(model=target_model, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
            except:
                # Fallback to default cost for local/unsupported models
                cost = (tokens / 1000) * 0.00015
            
            with get_db() as conn:
                conn.execute("INSERT OR IGNORE INTO sessions (name) VALUES (?)", (session_name,))
                conn.execute("UPDATE sessions SET total_tokens = total_tokens + ?, total_cost = total_cost + ? WHERE name = ?", (tokens, cost, session_name))
                conn.execute("UPDATE providers SET total_usage_cost = total_usage_cost + ? WHERE name = ?", (cost, provider_name))
                conn.execute("INSERT INTO messages (session_name, role, content, provider, model, tokens, cost, process_time) VALUES (?,?,?,?,?,?,?,?)",
                             (session_name, "user", message, provider_name, model, 0, 0, 0))
                conn.execute("INSERT INTO messages (session_name, role, content, provider, model, tokens, cost, process_time) VALUES (?,?,?,?,?,?,?,?)",
                             (session_name, "assistant", full_reply, provider_name, model, tokens, cost, process_time))
                conn.execute("INSERT INTO rag_kb (content, session_name) VALUES (?,?)", (full_reply, session_name))
                conn.commit()

            yield f"data: {json.dumps({'done': True, 'tokens': tokens, 'cost': round(cost, 6), 'process_time': process_time, 'model': model, 'provider': provider_name})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(generate(), mimetype='text/event-stream')

if __name__ == "__main__":
    app.run(debug=True, port=5000)
