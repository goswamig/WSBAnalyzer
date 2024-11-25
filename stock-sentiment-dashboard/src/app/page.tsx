'use client';

import { useEffect, useState } from 'react';
import StockSentimentDashboard from '@/components/StockSentimentDashboard';

interface StockData {
  ticker: string;
  dominant_sentiment: string;
  avg_confidence: number;
  mention_count: number;
  reasoning_summary: string;
}

interface SummaryData {
  high_confidence_calls: StockData[];
  total_tickers_analyzed?: number;
  sentiment_distribution?: Record<string, number>;
  most_mentioned_tickers?: Record<string, number>;
}

export default function Home() {
  const [data, setData] = useState<StockData[]>([]);
  const [summary, setSummary] = useState<SummaryData>({ high_confidence_calls: [] });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        setError(null);

        // Replace with your actual API endpoint
        const response = await fetch('http://localhost:5000/api/sentiment');
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        
        // Assuming your API returns { data: StockData[], summary: SummaryData }
        setData(result.data || []);
        setSummary(result.summary || { high_confidence_calls: [] });
      } catch (err) {
        console.error('Error fetching data:', err);
        setError(err instanceof Error ? err.message : 'An error occurred while fetching data');
        
        // Load sample data in development for testing
        if (process.env.NODE_ENV === 'development') {
          const sampleData = [
            {
              ticker: "AAPL",
              dominant_sentiment: "bullish",
              avg_confidence: 0.85,
              mention_count: 10,
              reasoning_summary: "Strong earnings and product pipeline"
            },
            {
              ticker: "TSLA",
              dominant_sentiment: "bearish",
              avg_confidence: 0.78,
              mention_count: 8,
              reasoning_summary: "Market competition concerns"
            },
            {
              ticker: "NVDA",
              dominant_sentiment: "bullish",
              avg_confidence: 0.92,
              mention_count: 15,
              reasoning_summary: "AI dominance and strong growth"
            }
          ];

          const sampleSummary = {
            high_confidence_calls: sampleData,
            total_tickers_analyzed: 3,
            sentiment_distribution: {
              bullish: 2,
              bearish: 1
            },
            most_mentioned_tickers: {
              "NVDA": 15,
              "AAPL": 10,
              "TSLA": 8
            }
          };

          setData(sampleData);
          setSummary(sampleSummary);
        }
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, []);

  return (
    <main className="container mx-auto p-4">
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 rounded-lg p-4 mb-4">
          Error: {error}
        </div>
      )}

      <StockSentimentDashboard 
        data={data} 
        summary={summary}
        isLoading={isLoading}
      />
    </main>
  );
}