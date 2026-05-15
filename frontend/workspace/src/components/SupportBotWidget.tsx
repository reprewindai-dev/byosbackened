import { useRef, useState } from "react";
import { MessageSquare, Send, X } from "lucide-react";
import { cn } from "@/lib/cn";
import { supportService } from "@/lib/services/support.service";

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
};

export function SupportBotWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const sessionRef = useRef<string | null>(null);

  async function send() {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    setError(null);
    const userMsg: Message = { id: crypto.randomUUID(), role: "user", content: text, created_at: new Date().toISOString() };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);
    try {
      const res = await supportService.chat({
        message: text,
        conversation_id: sessionRef.current ?? undefined,
      });
      if (res.data.conversation_id) {
        sessionRef.current = res.data.conversation_id;
      }
      const botMsg: Message = {
        id: res.data.conversation_id || crypto.randomUUID(),
        role: "assistant",
        content: res.data.response,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, botMsg]);
    } catch {
      setError("Support bot unavailable. Try again in a moment or use support@veklom.com.");
    } finally {
      setLoading(false);
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
    }
  }

  return (
    <div className="fixed bottom-6 right-6 z-50">
      {open && (
        <div className="mb-3 flex w-80 flex-col overflow-hidden rounded-xl border border-rule bg-ink-2 shadow-2xl">
          <div className="flex items-center justify-between border-b border-rule bg-ink-1 px-4 py-3">
            <div className="flex items-center gap-2">
              <MessageSquare className="h-4 w-4 text-brass" />
              <span className="text-sm font-semibold text-bone">Veklom Support</span>
            </div>
            <button type="button" onClick={() => setOpen(false)} aria-label="Close support chat" className="text-muted hover:text-bone">
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="flex max-h-72 flex-col gap-2 overflow-y-auto p-3">
            {messages.length === 0 && (
              <div className="py-4 text-center text-xs text-muted">Ask anything about Veklom features, pricing, integrations.</div>
            )}
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={cn(
                  "max-w-[90%] rounded-lg px-3 py-2 text-xs leading-5",
                  msg.role === "user"
                    ? "ml-auto bg-brass/20 text-bone"
                    : "bg-white/[0.04] text-bone-2",
                )}
              >
                {msg.content}
              </div>
            ))}
            {loading && (
              <div className="flex gap-1 self-start">
                {[0, 1, 2].map((i) => (
                  <span key={i} className="h-1.5 w-1.5 animate-bounce rounded-full bg-brass" style={{ animationDelay: `${i * 0.15}s` }} />
                ))}
              </div>
            )}
            {error && <div className="text-xs text-crimson">{error}</div>}
            <div ref={bottomRef} />
          </div>

          <div className="flex items-center gap-2 border-t border-rule px-3 py-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  void send();
                }
              }}
              placeholder="Type a message..."
              className="flex-1 bg-transparent text-xs text-bone outline-none placeholder:text-muted"
              disabled={loading}
            />
            <button
              type="button"
              onClick={() => void send()}
              disabled={!input.trim() || loading}
              aria-label="Send message"
              className="text-muted hover:text-brass disabled:opacity-40"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label={open ? "Close support chat" : "Open support chat"}
        className="flex h-12 w-12 items-center justify-center rounded-full bg-brass shadow-lg hover:bg-brass/90 transition-all"
      >
        {open ? <X className="h-5 w-5 text-ink-1" /> : <MessageSquare className="h-5 w-5 text-ink-1" />}
      </button>
    </div>
  );
}
