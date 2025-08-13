import React from 'react';
import ReactCountryFlag from "react-country-flag";
import NewsItem from './NewsItem';

const sentimentConfig = [
  { key: "Muito Positivo", emoji: "🤩", color: "green" },
  { key: "Positivo",       emoji: "🙂", color: "lime" },
  // Neutro continua listado no cabeçalho de badges, mas a lista abaixo filtra
  { key: "Neutro",         emoji: "😐", color: "gray" },
  { key: "Negativo",       emoji: "🙁", color: "amber" },
  { key: "Muito Negativo", emoji: "😡", color: "red" },
];

const NewsGrid = ({ topics, setSummaryLoading, showSummary, onOpenHistory }) => (
  <div className="flex flex-wrap gap-6 px-6">
    {topics.map(({ topic, region, news }) => {
      // FILTRO visual padrão
      const filtered = (news || []).filter(
        n => (n.status === 'fresh' || n.status === 'new') && n.sentiment && n.sentiment !== 'Neutro'
      );

      // Contadores pelos mesmos critérios (apenas não neutros)
      const counts = filtered.reduce((acc, item) => {
        acc[item.sentiment] = (acc[item.sentiment] || 0) + 1;
        return acc;
      }, {});

      return (
        <div key={topic} className="relative w-80">
          {/* Título do tópico com bandeira */}
          <div className="absolute -top-3 left-4 bg-black text-white text-sm font-semibold px-3 py-1 rounded-t-lg rounded-b-none z-10 flex items-center space-x-2">
            <span>{topic}</span>
            <span>
              {region && region !== "GLOBAL" ? (
                <ReactCountryFlag
                  countryCode={region}
                  svg
                  style={{ width: "1.5em", height: "1.5em" }}
                  title={region}
                />
              ) : (
                <span role="img" aria-label="Global" style={{ fontSize: "1.5em" }}>
                  🌍
                </span>
              )}
            </span>
          </div>

          <div className="mt-2 flex flex-col bg-white rounded-lg shadow-sm border p-4 h-[360px]">
            {/* Badges agregados (não neutros) */}
            <div className="flex justify-center mb-2 space-x-1">
              {sentimentConfig.map(({ key, emoji, color }) => (
                <div
                  key={key}
                  className={`flex flex-col items-center bg-${color}-100 text-${color}-800 rounded px-1 py-0.5`}
                  title={`${key}: ${counts[key] || 0}`}
                >
                  <span className="text-sm">{emoji}</span>
                  <span className="text-xs font-bold">{counts[key] || 0}</span>
                </div>
              ))}
            </div>

            {/* Lista rolável com filtro aplicado */}
            <ul className="flex-1 overflow-y-auto space-y-2">
              {filtered.map((item, i) => (
                <NewsItem
                  key={item.link || i}
                  item={item}
                  setSummaryLoading={setSummaryLoading}
                  showSummary={showSummary}
                />
              ))}
              {!filtered.length && (
                <li className="text-xs text-gray-500">Sem F/N não neutras neste tópico.</li>
              )}
            </ul>

            {/* Ação: abrir histórico completo do tópico */}
            <button
              type="button"
              onClick={() => onOpenHistory(topic)}
              className="mt-3 text-xs bg-slate-100 hover:bg-slate-200 text-slate-800 border border-slate-300 rounded px-2 py-1"
            >
              Ver histórico
            </button>
          </div>
        </div>
      );
    })}
  </div>
);

export default NewsGrid;
