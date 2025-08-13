import React from 'react';

const Header = ({ lastUpdate }) => {
  return (
    <>
      <div className="bg-slate-800 text-white px-6 py-5 text-xl font-bold sticky top-0 z-20">
        News Tracker
      </div>
      {lastUpdate && (
        <div className="px-10 py-4 text-lg text-darkgray-600">
          Última atualização: {lastUpdate}
        </div>
      )}
    </>
  );
};

export default Header;
