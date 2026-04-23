from flask import Flask, request, jsonify, render_template
from litellm import completion
import psutil
import requests
import os

# Coba import GPUtil untuk GPU
try:
    import GPUtil
except ImportError:
    GPUtil = None

app = Flask(__name__)

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
                if gpus:
                    gpu_usage = round(gpus[0].load * 100, 1)
            except:
                pass
        return jsonify({"cpu": cpu, "ram": ram, "gpu": gpu_usage})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/models/<provider>")
def get_models(provider):
    if provider == "ollama":
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code == 200:
                models = [m["name"] for m in response.json().get("models", [])]
                return jsonify(models)
            return jsonify([])
        except:
            return jsonify([])
    elif provider == "openai":
        return jsonify(["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"])
    elif provider == "gemini":
        return jsonify(["gemini-1.5-pro", "gemini-1.5-flash", "gemini-pro"])
    return jsonify([])

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    model = data.get("model")
    provider = data.get("provider")
    api_key = data.get("api_key")
    message = data.get("message")
    image_data = data.get("image")
    history = data.get("history", [])

    # Susun pesan untuk LiteLLM
    messages = []
    # Masukkan history
    for h in history:
        messages.append({"role": h["role"], "content": h["content"]})

    # Masukkan pesan baru (Multimodal)
    content = [{"type": "text", "text": message}]
    if image_data:
        content.append({"type": "image_url", "image_url": {"url": image_data}})
    
    messages.append({"role": "user", "content": content})

    try:
        # Panggil LiteLLM
        response = completion(
            model=f"{provider}/{model}" if provider not in ["openai", "ollama"] else (f"ollama/{model}" if provider == "ollama" else model),
            messages=messages,
            api_key=api_key if api_key else None
        )

        reply = response["choices"][0]["message"]["content"]
        usage = response.get("usage", {})
        
        return jsonify({
            "reply": reply,
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "estimated_cost": round(usage.get("total_cost", 0) if usage.get("total_cost") else (usage.get("total_tokens", 0)/1000)*0.00015, 6)
        })

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Jalankan pada port 5000
    app.run(debug=True, port=5000)
