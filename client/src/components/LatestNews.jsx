import React from "react";
import ReactCountryFlag from "react-country-flag";

const statusLabel = {
  fresh: { label: "[F]", color: "text-orange-600" },
  new: { label: "[N]", color: "text-blue-600" },
  old: { label: "[O]", color: "text-gray-400" },
};

const sentimentStyle = {
  "Muito Positivo": "bg-green-100 text-green-700",
  "Positivo": "bg-lime-100 text-lime-700",
  Neutro: "bg-gray-100 text-gray-700",
  Negativo: "bg-amber-100 text-amber-700",
  "Muito Negativo": "bg-red-100 text-red-700",
};

function formatRelativeTime(iso) {
  if (!iso) return "";
  const dt = new Date(iso);
  const diffMs = Date.now() - dt.getTime();
  const minutes = Math.round(diffMs / 60000);
  if (minutes < 1) return "now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  return `${days}d ago`;
}

const Badge = ({ children, className = "" }) => (
  <span className={`px-1 py-0.3 rounded text-xs font-semibold ${className}`}>
    {children}
  </span>
);

const LatestNews = ({ topics, maxItems = 16 }) => {
  const allNews = topics
    .flatMap(({ topic, region, news }) =>
      (news || []).map((item) => ({ ...item, topic, region }))
    )
    .filter(n => n.published)
    // FILTRO: apenas FRESH/NEW e sentimento não neutro
    .filter(n => (n.status === 'fresh' || n.status === 'new') && n.sentiment && n.sentiment !== 'Neutro')
    .sort((a, b) => new Date(b.published) - new Date(a.published))
    .slice(0, maxItems);

  if (!allNews.length) return null;

  return (
    <div className="px-6 py-4">
      <div className="text-lg font-bold mb-4">
        Últimas {maxItems} notícias de todos os tópicos (F/N, não neutras)
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {allNews.map((item, i) => {
          const status = statusLabel[item.status] || statusLabel.old;
          const rel = formatRelativeTime(item.published);
          const fullDate = new Date(item.published).toLocaleString();
          const sentiCls =
            (item.sentiment && sentimentStyle[item.sentiment]) || "bg-gray-100";

          return (
            <div
              key={item.link || i}
              className="bg-white rounded-lg shadow-sm border p-3 flex flex-col gap-1"
            >
              <div className="flex items-center gap-2">
                <span className="text-xl" title={item.region || "GLOBAL"}>
                  {item.region && item.region !== "GLOBAL" ? (
                    <ReactCountryFlag
                      countryCode={item.region}
                      svg
                      style={{ width: "1.25em", height: "1.25em" }}
                      title={item.region}
                    />
                  ) : (
                    <span role="img" aria-label="Global">🌍</span>
                  )}
                </span>
                <span className={`font-bold ${status.color}`}>
                  {status.label}
                </span>
                <a
                  href={item.link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-medium hover:underline flex-1 truncate"
                  title={item.title}
                >
                  {item.title}
                </a>
              </div>

              <div className="flex flex-wrap gap-2 pl-7">
                {item.sentiment && (
                  <Badge className={sentiCls}>{item.sentiment}</Badge>
                )}
                {item.topic && (
                  <Badge className="bg-sky-100 text-sky-700">{item.topic}</Badge>
                )}
                {item.source && (
                  <Badge className="bg-indigo-100 text-indigo-700">{item.source}</Badge>
                )}
                <Badge
                  className="bg-gray-100 text-gray-700"
                  title={fullDate}
                  aria-label={fullDate}
                >
                  {rel || fullDate}
                </Badge>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default LatestNews;
