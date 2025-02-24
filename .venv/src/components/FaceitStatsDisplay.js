import React from 'react';

const FaceitStatsDisplay = ({ matchData }) => {
  const { map, score, players, finishedAt } = matchData;

  return (
    <div className="w-full max-w-4xl bg-gray-900 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-gray-800 bg-gray-800">
        <div className="flex justify-between items-center text-gray-100">
          <div className="flex items-center gap-4">
            <span className="text-xl font-bold">{map}</span>
            <span className="px-3 py-1 bg-gray-700 rounded">{score}</span>
          </div>
          <span className="text-sm text-gray-400">{finishedAt}</span>
        </div>
      </div>

      {/* Table */}
      <div className="p-4">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-gray-100">
            <thead>
              <tr className="bg-gray-800">
                <th className="px-4 py-3 text-left font-medium">Player</th>
                <th className="px-2 py-3 text-center font-medium">K</th>
                <th className="px-2 py-3 text-center font-medium">D</th>
                <th className="px-2 py-3 text-center font-medium">A</th>
                <th className="px-2 py-3 text-center font-medium">K/D</th>
                <th className="px-2 py-3 text-center font-medium">ADR</th>
                <th className="px-2 py-3 text-center font-medium">MKs</th>
                <th className="px-2 py-3 text-center font-medium">UTIL</th>
                <th className="px-2 py-3 text-center font-medium">ELO</th>
                <th className="px-2 py-3 text-center font-medium">Δ</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {players.map((player, index) => (
                <tr 
                  key={player.name}
                  className={index % 2 === 0 ? 'bg-gray-900' : 'bg-gray-800/50'}
                >
                  <td className="px-4 py-3 font-medium">{player.name}</td>
                  <td className="px-2 py-3 text-center">{player.kills}</td>
                  <td className="px-2 py-3 text-center">{player.deaths}</td>
                  <td className="px-2 py-3 text-center">{player.assists}</td>
                  <td className="px-2 py-3 text-center">{player.kd.toFixed(2)}</td>
                  <td className="px-2 py-3 text-center font-medium text-blue-400">
                    {player.adr.toFixed(1)}
                  </td>
                  <td className="px-2 py-3 text-center">{player.multiKills}</td>
                  <td className="px-2 py-3 text-center">{player.utilityDmg}</td>
                  <td className="px-2 py-3 text-center">{player.elo || '-'}</td>
                  <td className={`px-2 py-3 text-center ${player.eloChange >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {player.eloChange ? (player.eloChange >= 0 ? `+${player.eloChange}` : player.eloChange) : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Legend */}
        <div className="mt-4 text-xs text-gray-400 space-y-1">
          <p>MKs = Multi Kills (Double + Triple + Quadro + Penta)</p>
          <p>UTIL = Utility Damage</p>
        </div>
      </div>
    </div>
  );
};

export default FaceitStatsDisplay;