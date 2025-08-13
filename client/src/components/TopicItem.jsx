import React from 'react';
import ReactCountryFlag from "react-country-flag";

const TopicItem = ({ topic, region, freshCount, onRemove, removing }) => (
  <div className="relative bg-gray-100 border border-gray-300 rounded-md px-3 py-2 flex items-center gap-2 text-base min-w-[200px]">
    <button
      onClick={() => onRemove(topic)}
      disabled={removing === topic}
      className={`text-red-500 hover:text-red-700 text-xs ${removing === topic ? 'opacity-50 cursor-not-allowed' : ''}`}
    >
      ❌
    </button>
    <span className="font-medium truncate">{topic}</span>
    <span className="ml-2">
      {region && region !== "GLOBAL" ? (
        <ReactCountryFlag
          countryCode={region}
          svg
          style={{ width: "1.5em", height: "1.5em" }}
          title={region}
        />
      ) : (
        <span role="img" aria-label="Global" style={{ fontSize: "1.5em" }}>🌍</span>
      )}
    </span>
    {freshCount > 0 && (
      <span className="absolute top-0 right-0 bg-orange-600 text-white text-[12px] px-2 py-1 rounded-full">
        {freshCount}
      </span>
    )}
  </div>
);

export default TopicItem;
