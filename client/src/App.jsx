import React, { useState, useEffect, useRef } from 'react';
import Header from './components/Header';
import TopicList from './components/TopicList';
import NewsGrid from './components/NewsGrid';
import LatestNews from './components/LatestNews';
import SentimentTrends from './components/SentimentTrends';
import ReactFlagsSelect from 'react-flags-select';
import TopicHistory from './components/TopicHistory';

const App = () => {
  const [topics, setTopics] = useState([]);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [intervalMinutes, setIntervalMinutes] = useState(1);
  const [removing, setRemoving] = useState(null);
  const [newTopic, setNewTopic] = useState('');
  const [selectedRegion, setSelectedRegion] = useState('US');
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryData, setSummaryData] = useState(null);

  const [addingTopic, setAddingTopic] = useState(false);
  const [historyTopic, setHistoryTopic] = useState(null); // NOVO

  const timerRef = useRef(null);
  const firstUpdateRef = useRef(true);
  const sessionStartMsRef = useRef(null);

  const fetchLast = async () => {
    try {
      const res = await fetch('http://localhost:8000/last-update');
      const j = await res.json();
      if (j.status === 'success') {
        setLastUpdate(new Date(j.last_update * 1000).toLocaleString());
      } else {
        console.warn('Resposta inesperada de /last-update');
      }
    } catch (err) {
      console.error('Erro ao buscar /last-update:', err);
    }
  };

  const pollTopics = async () => {
    if (!sessionStartMsRef.current) {
      const res = await fetch('http://localhost:8000/last-update');
      const j = await res.json();
      sessionStartMsRef.current = j.last_update * 1000;
    }
    const resT = await fetch('http://localhost:8000/topics');
    const names = (await resT.json()).data;
    const perTopic = await Promise.all(
      names.map(async (topic) => {
        const r = await fetch(`http://localhost:8000/news/${encodeURIComponent(topic)}/all`);
        const dt = await r.json();
        const newsList = dt.data || [];
        const region = newsList.length > 0 ? newsList[0].region : 'GLOBAL';
        return { topic, region, news: newsList };
      })
    );
    setTopics(perTopic);
  };

  const loadAll = async () => {
    setRefreshing(true);
    try {
      await fetch('http://localhost:8000/force-update', { method: 'POST' });
      await pollTopics();
      await fetchLast();
    } finally {
      setRefreshing(false);
    }
  };

  const handleAddTopic = async () => {
    const trimmed = newTopic.trim();
    if (!trimmed) return;
    setAddingTopic(true);
    try {
      await fetch(
        `http://localhost:8000/add-topic?topic=${encodeURIComponent(trimmed)}&region=${encodeURIComponent(selectedRegion)}`,
        { method: 'POST' }
      );
      setNewTopic('');
      await pollTopics();
      await fetchLast();
    } finally {
      setAddingTopic(false);
    }
  };

  useEffect(() => {
    pollTopics();
    fetchLast();
    timerRef.current = setInterval(pollTopics, intervalMinutes * 60000);
    return () => clearInterval(timerRef.current);
  }, []);

  useEffect(() => {
    if (!firstUpdateRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = setInterval(pollTopics, intervalMinutes * 60000);
    }
    firstUpdateRef.current = false;
    return () => clearInterval(timerRef.current);
  }, [intervalMinutes]);

  const handleRemove = async (topic) => {
    if (!window.confirm(`Remover tópico "${topic}"?`)) return;
    setRemoving(topic);
    await fetch(`http://localhost:8000/remove-topic?topic=${encodeURIComponent(topic)}`, { method: 'DELETE' });
    setRemoving(null);
    await pollTopics();
  };

  // Banner de resumo (mantido)
  const showSummary = (summaryResult) => {
    setSummaryLoading(false);
    setSummaryData(summaryResult);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };
  const handleCloseSummary = () => setSummaryData(null);

  // Abrir histórico sob demanda
  const handleOpenHistory = (topic) => setHistoryTopic(topic);
  const handleCloseHistory = () => setHistoryTopic(null);

  return (
    <div className="relative">
      <Header lastUpdate={lastUpdate} />

      {refreshing && (
        <div className="fixed top-3 left-1/2 -translate-x-1/2 z-30 flex items-center gap-2 bg-blue-50 border border-blue-200 px-4 py-1 rounded shadow">
          <span className="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin"></span>
          <span className="text-blue-900 font-medium text-sm">Atualizando notícias...</span>
        </div>
      )}

      {/* CONTROLE DE INTERVALO E ATUALIZAÇÃO */}
      <div className="px-6 mb-4">
        <label className="flex items-center gap-2">
          <input
            type="number"
            min="1"
            value={intervalMinutes}
            onChange={(e) => setIntervalMinutes(Math.max(1, Number(e.target.value)))}
            className="border px-2 py-1 text-sm w-20 rounded"
          />
          <span className="text-sm">intervalo (minutes)</span>
        </label>

        <button
          onClick={loadAll}
          disabled={refreshing}
          className="mt-2 bg-blue-500 hover:bg-blue-600 text-white text-sm px-3 py-1 rounded flex items-center gap-2 disabled:opacity-50"
        >
          {refreshing && (
            <span className="inline-block w-4 h-4 border-2 border-white border-t-blue-300 rounded-full animate-spin"></span>
          )}
          {refreshing ? "Atualizando..." : "Atualizar"}
        </button>
      </div>

      {/* ADICIONAR NOVO TÓPICO */}
      <div className="px-6 mb-4 flex items-center gap-4">
        <ReactFlagsSelect
          selected={selectedRegion}
          onSelect={(code) => setSelectedRegion(code)}
          countries={['US', 'BR', 'DE', 'CN', 'JP']}
          placeholder="Selecione região"
          className="flag-select"
        />

        <input
          type="text"
          placeholder="Novo tópico"
          value={newTopic}
          onChange={(e) => setNewTopic(e.target.value)}
          className="border px-2 py-1 text-sm rounded w-64"
        />
        <button
          type="button"
          onClick={handleAddTopic}
          disabled={addingTopic || refreshing}
          className="bg-green-500 hover:bg-green-600 text-white text-sm px-3 py-1 rounded flex items-center gap-2 disabled:opacity-50"
        >
          {addingTopic && (
            <span className="inline-block w-4 h-4 border-2 border-white border-t-green-300 rounded-full animate-spin"></span>
          )}
          {addingTopic ? "Adicionando..." : "Adicionar"}
        </button>
      </div>

      <LatestNews topics={topics}/>
      <SentimentTrends topics={topics} />
      <TopicList topics={topics} onRemove={handleRemove} removing={removing} />
      <NewsGrid
        topics={topics}
        sessionStartMs={sessionStartMsRef.current || 0}
        setSummaryLoading={setSummaryLoading}
        showSummary={showSummary}
        onOpenHistory={handleOpenHistory}
      />

      {/* Modal de histórico sob demanda */}
      {historyTopic && (
        <TopicHistory topic={historyTopic} onClose={handleCloseHistory} />
      )}
    </div>
  );
};

export default App;
