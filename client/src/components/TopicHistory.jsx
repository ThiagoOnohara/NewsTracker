import React, { useEffect, useMemo, useState } from "react";
import NewsItem from "./NewsItem";

const STATUS_OPTIONS = [
  { value: "all", label: "Todos" },
  { value: "fresh", label: "Fresh [F]" },
  { value: "new", label: "New [N]" },
  { value: "old", label: "Old [O]" },
];

export default function TopicHistory({ topic, onClose }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [includeNeutral, setIncludeNeutral] = useState(false);
  const [status, setStatus] = useState("all");

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        setLoading(true);
        const r = await fetch(`http://localhost:8000/news/${encodeURIComponent(topic)}/all`);
        const j = await r.json();
        if (!active) return;
        const data = (j && j.data) || [];
        setItems(data);
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => { active = false; };
  }, [topic]);

  const filtered = useMemo(() => {
    return items
      .filter(n => (status === "all" ? true : n.status === status))
      .filter(n => includeNeutral ? true : (n.sentiment && n.sentiment !== "Neutro"))
      .sort((a, b) => new Date(b.published || 0) - new Date(a.published || 0));
  }, [items, includeNeutral, status]);

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-3xl bg-white rounded-lg shadow-lg border p-4 max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between mb-2">
          <div className="font-semibold">Histórico — {topic}</div>
          <button
            onClick={onClose}
            className="text-sm text-slate-600 hover:text-slate-900"
          >
            Fechar
          </button>
        </div>

        <div className="flex items-center gap-4 mb-3">
          <label className="text-sm flex items-center gap-2">
            Status:
            <select
              value={status}
              onChange={e => setStatus(e.target.value)}
              className="border rounded px-2 py-1 text-sm"
            >
              {STATUS_OPTIONS.map(o => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </label>
          <label className="text-sm flex items-center gap-1">
            <input
              type="checkbox"
              checked={includeNeutral}
              onChange={e => setIncludeNeutral(e.target.checked)}
            />
            Incluir Neutro
          </label>
          <div className="text-xs text-slate-500">
            {loading ? "Carregando..." : `${filtered.length} itens`}
          </div>
        </div>

        <ul className="flex-1 overflow-y-auto space-y-2">
          {loading ? (
            <li className="text-sm text-slate-500">Buscando do backend…</li>
          ) : filtered.length ? (
            filtered.map((item, i) => <NewsItem key={item.link || i} item={item} />)
          ) : (
            <li className="text-sm text-slate-500">Nenhum item no filtro atual.</li>
          )}
        </ul>
      </div>
    </div>
  );
}
