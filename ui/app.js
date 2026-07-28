const form = document.querySelector("#chat-form");
const message = document.querySelector("#message");
const modeButtons = [...document.querySelectorAll(".mode")];
const providerButtons = [...document.querySelectorAll(".provider")];
const emptyState = document.querySelector("#empty-state");
const resultContent = document.querySelector("#result-content");
const runButton = document.querySelector(".run-button");
let activeMode = "agent_v2";
let activeProvider = "demo";

const examples = {
  iphone:
    "Tôi muốn mua 2 iPhone dùng mã WINNER và giao 0.8 kg tới Hà Nội. Tổng bao nhiêu?",
  macbook: "Tôi có thể mua 1 MacBook và giao tới Sài Gòn không?",
  policy: "Chính sách đổi trả là gì?",
};

modeButtons.forEach((button) => {
  button.addEventListener("click", () => {
    activeMode = button.dataset.mode;
    modeButtons.forEach((item) => item.classList.toggle("active", item === button));
  });
});

providerButtons.forEach((button) => {
  button.addEventListener("click", () => {
    setProvider(button.dataset.provider);
  });
});

function setProvider(provider) {
  activeProvider = provider;
  providerButtons.forEach((item) =>
    item.classList.toggle("active", item.dataset.provider === provider),
  );
}

async function loadConfig() {
  try {
    const response = await fetch("/api/config");
    if (!response.ok) return;
    const config = await response.json();
    setProvider(config.default_provider);

    const geminiButton = document.querySelector('[data-provider="gemini"]');
    const geminiHint = geminiButton.querySelector("small");
    geminiHint.textContent = config.gemini_configured
      ? config.gemini_model
      : "Thiếu GEMINI_API_KEY";

    const openaiButton = document.querySelector('[data-provider="openai"]');
    const openaiHint = openaiButton.querySelector("small");
    openaiHint.textContent = config.openai_configured
      ? config.openai_model
      : "Thiếu OPENAI_API_KEY";
  } catch {
    setProvider("demo");
  }
}

loadConfig();

document.querySelectorAll("[data-example]").forEach((button) => {
  button.addEventListener("click", () => {
    message.value = examples[button.dataset.example];
    message.focus();
  });
});

document.querySelector("#clear-button").addEventListener("click", () => {
  resultContent.classList.add("hidden");
  emptyState.classList.remove("hidden");
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = message.value.trim();
  if (!text) {
    message.focus();
    return;
  }

  runButton.disabled = true;
  runButton.querySelector("span:first-child").textContent = "Đang chạy…";

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        mode: activeMode,
        provider: activeProvider,
        message: text,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Không thể chạy hệ thống");
    renderResult(data);
  } catch (error) {
    renderResult({
      mode: activeMode,
      provider: activeProvider,
      model: "unknown",
      answer: `Lỗi: ${error.message}`,
      llm_calls: 0,
      tool_calls: 0,
      tool_path: [],
      trace: [],
    });
  } finally {
    runButton.disabled = false;
    runButton.querySelector("span:first-child").textContent = "Chạy hệ thống";
  }
});

function renderResult(data) {
  emptyState.classList.add("hidden");
  resultContent.classList.remove("hidden");
  document.querySelector("#llm-calls").textContent = data.llm_calls;
  document.querySelector("#tool-calls").textContent = data.tool_calls;
  document.querySelector("#result-mode").textContent =
    data.mode === "agent_v1"
      ? "Agent V1"
      : data.mode === "agent_v2"
        ? "Agent V2"
        : "Chatbot";
  document.querySelector("#provider-used").textContent =
    data.provider === "gemini"
      ? `Gemini live · ${data.model}`
      : data.provider === "openai"
        ? `OpenAI live · ${data.model}`
        : `Demo local · ${data.model}`;
  document.querySelector("#answer").textContent = data.answer;
  document.querySelector("#tool-path").textContent =
    data.tool_path.length > 0 ? data.tool_path.join(" → ") : "No tools";

  const trace = document.querySelector("#trace");
  trace.replaceChildren();
  if (data.trace.length === 0) {
    const item = document.createElement("li");
    item.dataset.index = "1";
    item.textContent = "Baseline: một LLM call, không có tool trace.";
    trace.append(item);
    return;
  }

  data.trace.forEach((entry, index) => {
    const item = document.createElement("li");
    item.dataset.index = String(index + 1);
    item.textContent = entry;
    if (entry.startsWith("Action:")) item.classList.add("action");
    trace.append(item);
  });
}
