import React from 'react';

const statusLabel = {
  fresh: { label: '[F]', color: 'text-orange-600' },
  new:   { label: '[N]', color: 'text-blue-600' },
  old:   { label: '[O]', color: 'text-gray-400' }
};

const NewsItem = ({ item }) => {
  if (!item) return null;
  const labelObj = statusLabel[item.status] || statusLabel.old;

  return (
    <li
      className={item.status === "old" ? "opacity-70" : ""}
      style={{ display: 'flex', alignItems: 'center' }}
    >
      <span className={`font-bold mr-1 ${labelObj.color}`}>
        {labelObj.label}
      </span>
      <a
        href={item.link}
        target="_blank"
        rel="noopener noreferrer"
        className="hover:underline text-gray-900 flex-1"
      >
        {item.title}
      </a>
    </li>
  );
};

export default NewsItem;
