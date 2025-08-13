// src/components/SentimentTrends.jsx
import React, { useMemo, useState } from "react";
import ReactCountryFlag from "react-country-flag";
import {
  ComposedChart,
  Area,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
  ReferenceLine,
} from "recharts";

/** Converte rótulos em escore numérico */
const SENTIMENT_SCORE = {
  "Muito Negativo": -2,
  "Negativo": -1,
  "Neutro": 0,
  "Positivo": 1,
  "Muito Positivo": 2,
};

// Janelas: 12h, 6h, 2h
const WINDOWS = [
  { label: "2h",  ms:  2 * 60 * 60 * 1000, bin:  5 * 60 * 1000 }, // 5  min
  { label: "6h",  ms:  6 * 60 * 60 * 1000, bin: 15 * 60 * 1000 }, // 15 min
  { label: "12h", ms: 12 * 60 * 60 * 1000, bin: 30 * 60 * 1000 }, // 30 min
];

function binTimestamp(timestamp, binMilliseconds) {
  return Math.floor(timestamp / binMilliseconds) * binMilliseconds;
}

// suavização simples por janela deslizante de tamanho k
function smoothArray(array, k = 2, key = "sentiment") {
  if (k <= 1 || array.length <= 2) return array;
  const output = array.map((row) => ({ ...row }));
  for (let i = 0; i < array.length; i++) {
    let sum = 0;
    let count = 0;
    for (let j = i - k; j <= i + k; j++) {
      if (j >= 0 && j < array.length && typeof array[j][key] === "number") {
        sum += array[j][key];
        count += 1;
      }
    }
    output[i][key] = count ? sum / count : array[i][key];
  }
  return output;
}

function colorForTopic(topic) {
  let hash = 0;
  for (let i = 0; i < topic.length; i++) {
    hash = (hash * 31 + topic.charCodeAt(i)) >>> 0;
  }
  const hue = hash % 360;
  return `hsl(${hue}, 65%, 45%)`;
}

function formatTimeLabel(timestamp) {
  return new Date(timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

/**
 * props.topics: [{ topic, region, news: [{ published, sentiment, ... }] }]
 */
export default function SentimentTrends({ topics }) {
  // default agora é 12h (index 0)
  const [winIdx, setWinIdx] = useState(0);
  const [topN, setTopN] = useState(8);
  const [doSmooth, setDoSmooth] = useState(true);

  const cards = useMemo(() => {
    const now = Date.now();
    const currentWindow = WINDOWS[winIdx];
    const windowMilliseconds = currentWindow.ms;
    const binMilliseconds = currentWindow.bin;
    const start = now - windowMilliseconds;

    // constrói bins globais alinhados ao período
    const bins = [];
    for (let t = binTimestamp(start, binMilliseconds); t <= now; t += binMilliseconds) {
      bins.push(t);
    }

    // agrega por tópico somente dentro da janela [start, now]
    const perTopic = topics.map(({ topic, region, news = [] }) => {
      const binMap = new Map(); // binTimestamp -> { sum, count }
      for (const n of news) {
        if (!n || !n.published || !n.sentiment) continue;
        const timestamp = Date.parse(n.published);
        if (Number.isNaN(timestamp) || timestamp < start || timestamp > now) continue;

        const bTime = binTimestamp(timestamp, binMilliseconds);
        const sentimentValue = SENTIMENT_SCORE[n.sentiment];
        if (typeof sentimentValue !== "number") continue;

        if (!binMap.has(bTime)) {
          binMap.set(bTime, { sum: 0, count: 0 });
        }
        const binData = binMap.get(bTime);
        binData.sum += sentimentValue;
        binData.count += 1;
      }

      const data = bins.map((bTime) => {
        const binData = binMap.get(bTime);
        const volume = binData ? binData.count : 0;
        const sentiment = binData ? binData.sum / binData.count : null;
        return {
          ts: bTime,
          time: formatTimeLabel(bTime),
          volume,
          sentiment,
        };
      });

      // preenche lacunas de sentimento para manter a área contínua
      const filled = data.map((row, index, arr) => {
        if (row.sentiment !== null) return row;
        let left = index - 1;
        while (left >= 0 && arr[left].sentiment === null) left--;
        let right = index + 1;
        while (right < arr.length && arr[right].sentiment === null) right++;
        let sValue = 0;
        if (left >= 0 && right < arr.length) {
          sValue = (arr[left].sentiment + arr[right].sentiment) / 2;
        } else if (left >= 0) {
          sValue = arr[left].sentiment;
        } else if (right < arr.length) {
          sValue = arr[right].sentiment;
        } else {
          sValue = 0;
        }
        return { ...row, sentiment: sValue };
      });

      const finalData = doSmooth ? smoothArray(filled, 2, "sentiment") : filled;
      const totalVol = finalData.reduce((acc, cur) => acc + (cur.volume || 0), 0);

      return {
        topic,
        region: region || "GLOBAL",
        color: colorForTopic(topic),
        totalVol,
        data: finalData,
      };
    });

    // Top N por VOLUME dentro da janela selecionada
    perTopic.sort((a, b) => b.totalVol - a.totalVol);
    return perTopic.slice(0, topN);
  }, [topics, winIdx, topN, doSmooth]);

  return (
    <div className="px-6 py-4">
      <div className="flex items-center justify-between mb-3">
        <div className="text-lg font-bold">Sentiment Trends</div>
        <div className="flex items-center gap-3">
          <label className="text-sm">Janela:</label>
          <select
            className="border px-2 py-1 rounded text-sm"
            value={winIdx}
            onChange={(event) => setWinIdx(Number(event.target.value))}
          >
            {WINDOWS.map((w, index) => (
              <option key={w.label} value={index}>
                {w.label}
              </option>
            ))}
          </select>

          <label className="text-sm">Top N:</label>
          <input
            type="number"
            min="3"
            max="24"
            className="border px-2 py-1 rounded text-sm w-20"
            value={topN}
            onChange={(event) => {
              const parsed = Number(event.target.value);
              const clamped = Math.max(3, Math.min(24, Number.isFinite(parsed) ? parsed : 8));
              setTopN(clamped);
            }}
          />

          <label className="text-sm flex items-center gap-1">
            <input
              type="checkbox"
              checked={doSmooth}
              onChange={(event) => setDoSmooth(event.target.checked)}
            />
            Suavizar
          </label>
        </div>
      </div>

      {/* Grid: 4 colunas em xl (ex.: top 8 => 4 x 2) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {cards.map((card) => {
          const regionCode = (card.region || "GLOBAL").toUpperCase();
          const isGlobal = regionCode === "GLOBAL";

          return (
            <div key={`${card.topic}-${regionCode}`} className="bg-white rounded-lg border shadow-sm p-2">
              {/* Cabeçalho com região + título */}
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2 min-w-0">
                  {/* Bandeira ou globo */}
                  <span title={regionCode} className="shrink-0">
                    {isGlobal ? (
                      <span role="img" aria-label="Global" style={{ fontSize: "1.1rem" }}>
                        🌍
                      </span>
                    ) : (
                      <ReactCountryFlag
                        countryCode={regionCode}
                        svg
                        style={{ width: "1.1rem", height: "1.1rem" }}
                        title={regionCode}
                      />
                    )}
                  </span>
                  {/* Região + Tópico */}
                  <div className="font-semibold truncate">
                    <span className="text-gray-500 mr-1">{regionCode} —</span>
                    <span className="text-gray-900">{card.topic}</span>
                  </div>
                </div>
                <div className="text-xs text-gray-500">vol {card.totalVol}</div>
              </div>

              {/* Gráfico */}
              <div style={{ width: "100%", height: 220 }}>
                <ResponsiveContainer>
                  <ComposedChart data={card.data} margin={{ top: 8, right: 24, bottom: 8, left: 0 }}>
                    <CartesianGrid stroke="#f1f5f9" />
                    <XAxis dataKey="time" tick={{ fontSize: 11 }} />
                    {/* Y esquerdo: sentimento [-2..2] */}
                    <YAxis yAxisId="left" domain={[-2, 2]} tick={{ fontSize: 11 }} />
                    {/* Y direito: volume */}
                    <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} />
                    <Tooltip
                      formatter={(value, name) => {
                        if (name === "sentiment") {
                          const numeric = typeof value === "number" ? value : Number(value);
                          const fixed = Number.isFinite(numeric) ? numeric.toFixed(2) : value;
                          return [fixed, "Sentimento"];
                        }
                        return [value, "Volume"];
                      }}
                      labelFormatter={(label, payload) => {
                        if (payload && payload.length > 0 && payload[0].payload && payload[0].payload.ts) {
                          return new Date(payload[0].payload.ts).toLocaleString();
                        }
                        return label;
                      }}
                    />
                    <Legend verticalAlign="top" height={24} wrapperStyle={{ fontSize: 11 }} />

                    {/* Linha de referência no zero (neutro) */}
                    <ReferenceLine y={0} yAxisId="left" stroke="#9ca3af" strokeDasharray="3 3" />

                    {/* Barras: volume */}
                    <Bar
                      yAxisId="right"
                      dataKey="volume"
                      name="Volume"
                      fill="rgba(148,163,184,0.6)"
                      radius={[2, 2, 0, 0]}
                    />

                    {/* Área de sentimento (preenchida) */}
                    <Area
                      yAxisId="left"
                      type="monotone"
                      dataKey="sentiment"
                      name="Sentimento"
                      stroke={card.color}
                      fill={card.color}
                      fillOpacity={0.25}
                      strokeWidth={2}
                      dot={false}
                      isAnimationActive={false}
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
