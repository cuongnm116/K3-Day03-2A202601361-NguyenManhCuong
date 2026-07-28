# Lab 3: Chatbot vs ReAct Agent (Industry Edition)

Welcome to Phase 3 of the Agentic AI course! This lab focuses on moving from a simple LLM Chatbot to a sophisticated **ReAct Agent** with industry-standard monitoring.

## 🚀 Getting Started

### 1. Setup Environment
Copy the `.env.example` to `.env` and fill in your API keys:
```bash
cp .env.example .env
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Directory Structure
- `src/tools/`: Extension point for your custom tools.

## 🏠 Running with Local Models (CPU)

If you don't want to use OpenAI or Gemini, you can run open-source models (like Phi-3) directly on your CPU using `llama-cpp-python`.

### 1. Download the Model
Download the **Phi-3-mini-4k-instruct-q4.gguf** (approx 2.2GB) from Hugging Face:
- [Phi-3-mini-4k-instruct-GGUF](https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf)
- Direct Download: [phi-3-mini-4k-instruct-q4.gguf](https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf)

### 2. Place Model in Project
Create a `models/` folder in the root and move the downloaded `.gguf` file there.

### 3. Update `.env`
Change your `DEFAULT_PROVIDER` and set the path:
```env
DEFAULT_PROVIDER=local
LOCAL_MODEL_PATH=./models/Phi-3-mini-4k-instruct-q4.gguf
```

## 🎯 Lab Objectives

1.  **Baseline Chatbot**: Observe the limitations of a standard LLM when faced with multi-step reasoning.
2.  **ReAct Loop**: Implement the `Thought-Action-Observation` cycle in `src/agent/agent.py`.
3.  **Provider Switching**: Swap between OpenAI and Gemini seamlessly using the `LLMProvider` interface.
4.  **Failure Analysis**: Use the structured logs in `logs/` to identify why the agent fails (hallucinations, parsing errors).
5.  **Grading & Bonus**: Follow the [SCORING.md](file:///Users/tindt/personal/ai-thuc-chien/day03-lab-agent/SCORING.md) to maximize your points and explore bonus metrics.

## 🛠️ How to Use This Baseline
The code is designed as a **Production Prototype**. It includes:
- **Telemetry**: Every action is logged in JSON format for later analysis.
- **Robust Provider Pattern**: Easily extendable to any LLM API.
- **Clean Skeletons**: Focus on the logic that matters—the agent's reasoning process.

## 🖥️ Run the Local UI

The repository includes a dependency-free browser UI. It runs the existing
Chatbot baseline or ReAct Agent V2 with deterministic local tools, so no API key
is required.

```powershell
.\.venv\Scripts\Activate.ps1
python scripts/run_ui.py
```

Open:

```text
http://127.0.0.1:8000
```

Use the mode switch to compare Chatbot, Agent V1, and Agent V2 behavior. The result panel
shows the final answer, LLM step count, tool count, tool path, and complete
Thought–Action–Observation trace. Press `Ctrl+C` in the terminal to stop the
server.

The provider switch offers:

- **Demo local:** deterministic and free; no API key required.
- **Gemini live:** reads `GEMINI_API_KEY` and the model from `GEMINI_MODEL` or
  `DEFAULT_MODEL` in `.env`.
- **OpenAI live:** reads `OPENAI_API_KEY` and the model from `OPENAI_MODEL` or
  `DEFAULT_MODEL` in `.env`.

Example:

```env
DEFAULT_PROVIDER=gemini
DEFAULT_MODEL=gemini-2.5-flash
GEMINI_API_KEY=your_new_key
```

---

*Happy Coding! Let's build agents that actually work.*
