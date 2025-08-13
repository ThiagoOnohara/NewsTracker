import TopicItem from './TopicItem';

const TopicList = ({ topics, onRemove, removing }) => {
  return (
    <div className="px-6 flex flex-wrap gap-3 mb-4">
      {topics.map(({ topic, region, news }) => {
        const freshCount = news.filter(n => n.status === "fresh").length;
        return (
          <TopicItem
            key={topic}
            topic={topic}
            region={region}
            freshCount={freshCount}
            onRemove={onRemove}
            removing={removing}
          />
        );
      })}
    </div>
  );
};

export default TopicList;
