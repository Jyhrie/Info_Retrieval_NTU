import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Search, TrendingUp, TrendingDown, LineChart, MessageSquare, Hash, Database, Tag, AlertCircle } from 'lucide-react';
import { ApiClient, QueryResponse } from './services/api';

interface Comment {
  text: string;
  sentiment: string;
}

interface Keyword {
  keyword: string;
  count: number;
}

const FILTER_OPTIONS_SUBREDDIT = [
  'tigerbrokers_official',
  'webull',
  'TigerBrokers',
  'singaporefi',
  'ibkr',
  'moomoo_official',
  'Etoro',
  'RobinHood',
  'plus500',
  'Fidelity',
  'thinkorswim',
  'InteractiveBrokers',
  'TradeStation',
  'CharlesSchwab',
  'vanguard',
  'merrilledge',
  'etrade',
  'tdameritrade',
  'Trading212',
  'RevolutTrading',
  'FreetradeApp',
  'Wealthsimple'
];

function App() {
  const [query, setQuery] = useState('');
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [selectedSubreddits, setSelectedSubreddits] = useState<string[]>([]);
  const [queryError, setQueryError] = useState('');
  const [sentiment, setSentiment] = useState<'positive' | 'negative' | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [comments, setComments] = useState<Comment[]>([]);
  const [subreddits, setSubreddits] = useState<string[]>([]);
  const [recordCount, setRecordCount] = useState<number>(0);
  const [keywords, setKeywords] = useState<Keyword[]>([]);
  const [apiError, setApiError] = useState<string | null>(null);

  const toggleSubreddit = (subreddit: string) => {
    setSelectedSubreddits(prev => {
      if (prev.includes(subreddit)) {
        return prev.filter(s => s !== subreddit);
      } else {
        return [...prev, subreddit];
      }
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!query.trim()) {
      setQueryError('Please enter a valid query');
      return;
    }
    setQueryError('');
    setApiError(null);
    setIsLoading(true);

    try {
      // Prepare the payload according to your requirements
      const payload = {
        query: query,
        subreddit: selectedSubreddits,
        date: selectedDate
      };

      console.log('Sending payload:', payload);
      const response = await ApiClient.getQueryResponse(payload);

      console.log('getQueryResponse response:', response);

      setSentiment(response.sentiment);
      setComments(response.comments);
      setSubreddits(response.subreddits);
      setRecordCount(response.recordCount);
      setKeywords(response.keywords);
    } catch (error) {
      console.error('Error fetching query response:', error);
      setApiError('Failed to fetch data. Please try again later.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 text-white">
      <div className="container mx-auto px-4 py-8">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between mb-12"
        >
          <div className="flex items-center gap-2">
            <LineChart className="w-8 h-8 text-blue-400" />
            <h1 className="text-2xl font-bold">Trading Platform Sentiment Analyzer</h1>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-gray-800 rounded-xl p-8 shadow-2xl mb-8"
        >
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Query Input */}
            <div className="relative">
              <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Enter Query"
                className="w-full pl-12 pr-4 py-3 bg-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
              />
              {queryError && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex items-center gap-2 mt-2 text-red-400"
                >
                  <AlertCircle className="w-4 h-4" />
                  <span className="text-sm">{queryError}</span>
                </motion.div>
              )}
            </div>

            {/* Date Filter */}
            <div className="relative">
              <label className="block text-sm font-medium text-gray-300 mb-2">Date Filter</label>
              <input
                type="date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="w-full px-4 py-3 bg-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all text-white"
              />
            </div>

            {/* Subreddit Filter Buttons */}
            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-300 mb-2">Select Subreddits</label>
              <div className="flex flex-wrap gap-2">
                {FILTER_OPTIONS_SUBREDDIT.map((subreddit) => (
                  <motion.button
                    key={subreddit}
                    type="button"
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => toggleSubreddit(subreddit)}
                    className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                      selectedSubreddits.includes(subreddit)
                        ? 'bg-blue-500 text-white'
                        : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    }`}
                  >
                    r/{subreddit}
                  </motion.button>
                ))}
              </div>
            </div>

            {/* Submit Button */}
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              type="submit"
              className="w-full bg-blue-500 text-white px-6 py-3 rounded-lg hover:bg-blue-600 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={isLoading}
            >
              {isLoading ? 'Analyzing...' : 'Analyze'}
            </motion.button>

            {apiError && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center gap-2 mt-2 text-red-400"
              >
                <AlertCircle className="w-4 h-4" />
                <span className="text-sm">{apiError}</span>
              </motion.div>
            )}
          </form>

          {isLoading ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex justify-center items-center py-12"
            >
              <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
            </motion.div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mt-8">
              {/* Sentiment Section */}
              {sentiment && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="text-center"
                >
                  <motion.div
                    className={`inline-flex items-center justify-center p-8 rounded-full ${
                      sentiment === 'positive' ? 'bg-green-500/20' : 'bg-red-500/20'
                    }`}
                  >
                    {sentiment === 'positive' ? (
                      <TrendingUp className="w-24 h-24 text-green-500" />
                    ) : (
                      <TrendingDown className="w-24 h-24 text-red-500" />
                    )}
                  </motion.div>
                  <motion.h2
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`text-3xl font-bold mt-4 ${
                      sentiment === 'positive' ? 'text-green-500' : 'text-red-500'
                    }`}
                  >
                    {sentiment.toUpperCase()}
                  </motion.h2>
                  <motion.p
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="text-gray-400 mt-2"
                  >
                    Platform sentiment analysis for {query}
                  </motion.p>
                </motion.div>
              )}

              {/* Record Count Widget */}
              {recordCount > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="bg-gray-700/50 rounded-xl p-6"
                >
                  <div className="flex items-center gap-2 mb-4">
                    <Database className="w-5 h-5 text-emerald-400" />
                    <h3 className="text-xl font-semibold">Relevant Records</h3>
                  </div>
                  <div className="text-center">
                    <motion.span
                      initial={{ scale: 0.5, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      className="text-5xl font-bold text-emerald-400"
                    >
                      {recordCount.toLocaleString()}
                    </motion.span>
                    <p className="text-gray-400 mt-2">Total records analyzed</p>
                  </div>
                </motion.div>
              )}

              {/* Keywords Widget */}
              {keywords.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="bg-gray-700/50 rounded-xl p-6"
                >
                  <div className="flex items-center gap-2 mb-4">
                    <Tag className="w-5 h-5 text-yellow-400" />
                    <h3 className="text-xl font-semibold">Top Keywords</h3>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {keywords.map((keyword, index) => (
                      <motion.div
                        key={index}
                        initial={{ opacity: 0, scale: 0.8 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: index * 0.1 }}
                        className="bg-gray-800/50 px-3 py-1 rounded-full"
                      >
                        <span className="text-gray-300">{keyword.keyword}</span>
                        <span className="ml-2 text-yellow-400">{keyword.count}</span>
                      </motion.div>
                    ))}
                  </div>
                </motion.div>
              )}

              {/* Comments Section */}
              {comments.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="bg-gray-700/50 rounded-xl p-6"
                >
                  <div className="flex items-center gap-2 mb-4">
                    <MessageSquare className="w-5 h-5 text-blue-400" />
                    <h3 className="text-xl font-semibold">Trading Platform Comments</h3>
                    <span className="ml-auto bg-blue-500/20 text-blue-400 px-2 py-1 rounded-full text-sm">
                      {comments.length} comments
                    </span>
                  </div>
                  <div className="space-y-4 max-h-80 overflow-y-auto custom-scrollbar">
                    {comments.map((comment, index) => (
                      <motion.div
                        key={index}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.1 }}
                        className="bg-gray-800/50 rounded-lg p-4"
                      >
                        <p className="text-gray-300">{comment.text}</p>
                        <span className="text-sm text-blue-400 mt-2 inline-block">
                          {comment.sentiment}
                        </span>
                      </motion.div>
                    ))}
                  </div>
                </motion.div>
              )}

              {/* Subreddits Section */}
              {subreddits.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="bg-gray-700/50 rounded-xl p-6"
                >
                  <div className="flex items-center gap-2 mb-4">
                    <Hash className="w-5 h-5 text-purple-400" />
                    <h3 className="text-xl font-semibold">Related Subreddits</h3>
                    <span className="ml-auto bg-purple-500/20 text-purple-400 px-2 py-1 rounded-full text-sm">
                      {subreddits.length} subreddits
                    </span>
                  </div>
                  <div className="space-y-4 max-h-80 overflow-y-auto custom-scrollbar">
                    {subreddits.map((subreddit, index) => (
                      <motion.div
                        key={index}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.1 }}
                        className="bg-gray-800/50 rounded-lg p-4"
                      >
                        <p className="text-gray-300">{subreddit}</p>
                      </motion.div>
                    ))}
                  </div>
                </motion.div>
              )}
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
}

export default App;