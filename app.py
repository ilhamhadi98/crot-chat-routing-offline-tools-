from flask import Flask, request, jsonify, render_template, Response
from litellm import completion
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
                tokens INTEGER DEFAULT 0,
                cost REAL DEFAULT 0,
                process_time REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Tabel RAG (Virtual Table untuk Pencarian Cepat)
        conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS rag_kb USING fts5(content, session_name)")

init_db()

@app.route("/")
def index():
    return render_template("index.html")

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
        
        # Ambil total statistik dari DB
        with get_db() as conn:
            row = conn.execute("SELECT SUM(total_tokens) as t, SUM(total_cost) as c FROM sessions").fetchone()
            global_tokens = row['t'] or 0
            global_cost = row['c'] or 0

        return jsonify({
            "cpu": cpu, "ram": ram, "gpu": gpu_usage,
            "global_tokens": global_tokens, "global_cost": global_cost
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/models/<provider>")
def get_models(provider):
    if provider == "ollama":
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code == 200:
                return jsonify([m["name"] for m in response.json().get("models", [])])
        except: pass
    elif provider == "openai":
        return jsonify(["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"])
    elif provider == "gemini":
        return jsonify(["gemini-1.5-pro", "gemini-1.5-flash"])
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
        return jsonify([dict(r) for r in rows])

@app.route("/chat", methods=["POST"])
def chat():
    start_time = time.time()
    data = request.json
    model = data.get("model")
    provider = data.get("provider")
    api_key = data.get("api_key")
    message = data.get("message", "")
    session_name = data.get("session_name", "Default Session")
    history = data.get("history", [])

    # Simple RAG menggunakan FTS5 SQLite
    past_context = ""
    try:
        with get_db() as conn:
            # Mencari teks yang mirip di database
            search_query = message.replace("'", "")
            results = conn.execute("SELECT content FROM rag_kb WHERE content MATCH ? LIMIT 2", (f"{search_query}*",)).fetchall()
            if results:
                past_context = "\n---\n".join([r['content'] for r in results])
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
            response = completion(
                model=f"{provider}/{model}" if provider not in ["openai", "ollama"] else (f"ollama/{model}" if provider == "ollama" else model),
                messages=messages, api_key=api_key if api_key else None, stream=True
            )

            for chunk in response:
                content = chunk['choices'][0]['delta'].get('content', '')
                if content:
                    full_reply += content
                    yield f"data: {json.dumps({'text': content})}\n\n"

            end_time = time.time()
            process_time = round(end_time - start_time, 2)
            tokens = len(full_reply.split()) + len(message.split()) + 50
            cost = (tokens / 1000) * 0.00015
            
            # SIMPAN KE SQLITE
            with get_db() as conn:
                # Update/Insert Sesi
                conn.execute("INSERT OR IGNORE INTO sessions (name) VALUES (?)", (session_name,))
                conn.execute("UPDATE sessions SET total_tokens = total_tokens + ?, total_cost = total_cost + ? WHERE name = ?", (tokens, cost, session_name))
                # Simpan Pesan AI
                conn.execute("INSERT INTO messages (session_name, role, content, tokens, cost, process_time) VALUES (?,?,?,?,?,?)",
                             (session_name, "user", message, 0, 0, 0))
                conn.execute("INSERT INTO messages (session_name, role, content, tokens, cost, process_time) VALUES (?,?,?,?,?,?)",
                             (session_name, "assistant", full_reply, tokens, cost, process_time))
                # Indeks ke RAG
                conn.execute("INSERT INTO rag_kb (content, session_name) VALUES (?,?)", (full_reply, session_name))
                conn.commit()

            yield f"data: {json.dumps({'done': True, 'tokens': tokens, 'cost': round(cost, 6), 'process_time': process_time})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(generate(), mimetype='text/event-stream')

if __name__ == "__main__":
    app.run(debug=True, port=5000)
