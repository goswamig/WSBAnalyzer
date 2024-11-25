import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const StockSentimentDashboard = ({ data = [], summary = {} }) => {
  // Early return if no data
  if (!data || data.length === 0) {
    return (
      <div className="p-4 text-center">
        <p className="text-gray-600">No data available to display</p>
      </div>
    );
  }

  // Safely prepare data for pie chart
  const pieData = data.map(item => ({
    name: item.ticker || 'Unknown',
    value: item.avg_confidence || 0,
    displayValue: ((item.avg_confidence || 0) * 100).toFixed(0) + '%',
    sentiment: (item.dominant_sentiment || '').toLowerCase(),
    confidence: item.avg_confidence || 0,
    reasoning: item.reasoning_summary || '',
    mentions: item.mention_count || 0
  }));

  const COLORS = {
    bullish: '#22c55e',
    bearish: '#ef4444',
    neutral: '#9ca3af'
  };

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length > 0) {
      const data = payload[0].payload;
      return (
        <div className="bg-white p-4 border rounded shadow">
          <p className="font-bold">{data.name}</p>
          <p className="text-sm capitalize">Sentiment: {data.sentiment}</p>
          <p className="text-sm">Confidence: {(data.confidence * 100).toFixed(1)}%</p>
          <p className="text-sm">Mentions: {data.mentions}</p>
          {data.reasoning && (
            <p className="text-sm text-gray-600 mt-2">{data.reasoning}</p>
          )}
        </div>
      );
    }
    return null;
  };

  const renderCustomLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, name, displayValue }) => {
    const RADIAN = Math.PI / 180;
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);

    return (
      <g>
        <text 
          x={x} 
          y={y-8} 
          fill="white" 
          textAnchor="middle" 
          dominantBaseline="central"
          className="text-xs font-bold"
        >
          {name}
        </text>
        <text 
          x={x} 
          y={y+8} 
          fill="white" 
          textAnchor="middle" 
          dominantBaseline="central"
          className="text-xs"
        >
          {displayValue}
        </text>
      </g>
    );
  };

  // Calculate sentiment distribution
  const sentimentCounts = data.reduce((acc, item) => {
    const sentiment = (item.dominant_sentiment || '').toLowerCase();
    acc[sentiment] = (acc[sentiment] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="w-full">
          <CardHeader>
            <CardTitle>Stock Sentiment & Confidence Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-96">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={130}
                    labelLine={false}
                    label={renderCustomLabel}
                  >
                    {pieData.map((entry, index) => (
                      <Cell 
                        key={`cell-${index}`} 
                        fill={COLORS[entry.sentiment] || COLORS.neutral}
                        stroke="#fff"
                        strokeWidth={2}
                      />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip />} />
                  <Legend 
                    formatter={(value, entry) => {
                      const { sentiment } = entry.payload;
                      return `${value} (${sentiment || 'unknown'})`;
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card className="w-full">
          <CardHeader>
            <CardTitle>Confidence Score & Mentions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-96">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={data}
                  margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="ticker" />
                  <YAxis 
                    yAxisId="confidence"
                    domain={[0, 1]} 
                    tickFormatter={(value) => `${(value * 100).toFixed(0)}%`}
                  />
                  <YAxis 
                    yAxisId="mentions"
                    orientation="right"
                    domain={[0, 'auto']}
                  />
                  <Tooltip 
                    formatter={(value, name) => {
                      if (name === "avg_confidence") return `${(value * 100).toFixed(1)}%`;
                      return value;
                    }}
                    labelFormatter={(label) => `Ticker: ${label}`}
                  />
                  <Bar yAxisId="confidence" dataKey="avg_confidence" name="Confidence Score">
                    {data.map((entry, index) => (
                      <Cell 
                        key={index} 
                        fill={COLORS[(entry.dominant_sentiment || '').toLowerCase()] || COLORS.neutral} 
                      />
                    ))}
                  </Bar>
                  <Bar yAxisId="mentions" dataKey="mention_count" name="Mentions" fill="#6366f1" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {data.map((stock) => (
          <Card key={stock.ticker || Math.random()} className="w-full">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>{stock.ticker || 'Unknown'}</span>
                <span
                  className={`px-2 py-1 rounded text-sm ${
                    (stock.dominant_sentiment || '').toLowerCase() === 'bullish'
                      ? 'bg-green-100 text-green-800'
                      : (stock.dominant_sentiment || '').toLowerCase() === 'bearish'
                      ? 'bg-red-100 text-red-800'
                      : 'bg-gray-100 text-gray-800'
                  }`}
                >
                  {stock.dominant_sentiment || 'Unknown'}
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-600">Confidence:</span>
                  <span className="font-medium">
                    {((stock.avg_confidence || 0) * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Mentions:</span>
                  <span className="font-medium">{stock.mention_count || 0}</span>
                </div>
                <div className="text-sm text-gray-600">
                  {stock.reasoning_summary || 'No reasoning available'}
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
};

export default StockSentimentDashboard;