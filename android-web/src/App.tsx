import { useRef, useState } from "react";
import { CreateMLCEngine } from "@mlc-ai/web-llm";
import "./App.css";

const MODEL = "Qwen2.5-0.5B-Instruct-q4f16_1-MLC";

type Message = { role: "user" | "assistant"; content: string };

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [status, setStatus] = useState("Модель не загружена");
  const [progress, setProgress] = useState(0);
  const [ready, setReady] = useState(false);
  const [busy, setBusy] = useState(false);
  const engine = useRef<any>(null);

  async function loadModel() {
    if (engine.current || busy) return;
    setBusy(true);
    setStatus("Подготовка локальной модели…");
    try {
      engine.current = await CreateMLCEngine(MODEL, {
        initProgressCallback: (report) => {
          setStatus(report.text || "Загрузка модели…");
          setProgress(Math.round((report.progress || 0) * 100));
        },
      });
      setReady(true);
      setStatus("AI работает на устройстве");
    } catch (error) {
      setStatus("Не удалось загрузить модель. Проверь поддержку WebGPU и память.");
      console.error(error);
    } finally {
      setBusy(false);
    }
  }

  async function sendMessage() {
    const text = input.trim();
    if (!text || busy) return;

    const next: Message[] = [...messages, { role: "user", content: text }];
    setMessages([...next, { role: "assistant", content: "" }]);
    setInput("");
    setBusy(true);

    try {
      if (!engine.current) {
        engine.current = await CreateMLCEngine(MODEL, {
          initProgressCallback: (report) => {
            setStatus(report.text || "Загрузка модели…");
            setProgress(Math.round((report.progress || 0) * 100));
          },
        });
        setReady(true);
      }

      setStatus("Генерирую ответ локально…");
      const stream = await engine.current.chat.completions.create({
        messages: [
          { role: "system", content: "Ты AI HUB — полезный русскоязычный помощник. Отвечай ясно, дружелюбно и по делу." },
          ...next,
        ],
        stream: true,
        temperature: 0.7,
        max_tokens: 700,
      });

      let answer = "";
      for await (const chunk of stream) {
        answer += chunk.choices?.[0]?.delta?.content || "";
        setMessages([...next, { role: "assistant", content: answer }]);
      }
      setStatus("AI работает на устройстве");
    } catch (error) {
      console.error(error);
      setMessages([...next, {
        role: "assistant",
        content: "Не удалось запустить модель. Открой приложение в актуальном Chrome с поддержкой WebGPU и попробуй снова.",
      }]);
      setStatus("Ошибка запуска модели");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="app">
      <header className="topbar">
        <div className="brand-icon">✳</div>
        <div className="brand">
          <h1>AI HUB</h1>
          <span>Личный локальный ИИ</span>
        </div>
        <div className={`indicator ${ready ? "online" : ""}`} />
      </header>

      <section className="model-card">
        <div className="model-title">
          <div>
            <span className="eyebrow">ЛОКАЛЬНАЯ МОДЕЛЬ</span>
            <h2>Qwen 2.5 · 0.5B</h2>
          </div>
          <span className="chip">{ready ? "ГОТОВА" : "WEBGPU"}</span>
        </div>
        <p className="status">{status}</p>
        {!ready && (
          <div className="progress-track">
            <div className="progress-fill" style={{ width: `${progress}%` }} />
          </div>
        )}
        {!ready && (
          <button className="load-button" onClick={loadModel} disabled={busy}>
            {busy ? `Подготовка… ${progress}%` : "↓  Загрузить модель"}
          </button>
        )}
        <p className="privacy">🔒 Сообщения обрабатываются на устройстве после загрузки модели.</p>
      </section>

      <section className="chat">
        {messages.length === 0 ? (
          <div className="welcome">
            <div className="welcome-symbol">✳</div>
            <h2>Привет! Я AI HUB.</h2>
            <p>Твой ИИ-помощник, который может работать прямо на телефоне.</p>
            <button className="suggestion" onClick={() => setInput("Привет! Расскажи, что ты умеешь.")}>
              Что ты умеешь? <span>↗</span>
            </button>
            <button className="suggestion" onClick={() => setInput("Помоги мне составить план на сегодня.")}>
              Составь план на день <span>↗</span>
            </button>
          </div>
        ) : (
          <div className="messages">
            {messages.map((message, i) => (
              <div className={`message ${message.role}`} key={i}>
                <div className="message-label">{message.role === "user" ? "ТЫ" : "AI HUB"}</div>
                <div className="message-content">
                  {message.content || (busy && message.role === "assistant" ? "Думаю…" : "")}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <form className="composer" onSubmit={(e) => { e.preventDefault(); void sendMessage(); }}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void sendMessage();
            }
          }}
          placeholder="Напиши сообщение…"
          rows={1}
          aria-label="Сообщение"
        />
        <button className="send-button" type="submit" disabled={!input.trim() || busy} aria-label="Отправить">↑</button>
      </form>
      <footer>AI HUB MOBILE <span>·</span> PRIVATE BY DESIGN</footer>
    </main>
  );
}
