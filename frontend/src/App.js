// frontend/src/App.js

// NOTE: Ensure your local React setup (src/index.js) imports 'index.css'
// If your local build is fixed, we keep this import:
import './index.css'; 
import React, { useState, useCallback, useMemo } from 'react';

// --- Component 1: DetailItem (Reusable UI for profile details) ---
const DetailItem = ({ label, value, className = 'text-gray-800' }) => (
  <p className="flex flex-col sm:flex-row sm:justify-between">
    <strong className="text-gray-700 w-24">{label}:</strong>
    <span className={`flex-1 ${className}`}>{value}</span>
  </p>
);

// --- Component 2: ResultCard (Individual Match) ---
const ResultCard = ({ match }) => {
  const [showFullDetails, setShowFullDetails] = useState(false);
  return (
    <div className="bg-white p-6 mb-6 rounded-2xl shadow-xl border border-gray-100 transition duration-300 hover:shadow-2xl">

      {/* Founder Name & Role */}
      <h3 className="text-2xl font-bold text-gray-900 flex flex-wrap items-center mb-1">
        {match.founder_name}
        <span className="ml-4 px-3 py-1 text-sm font-semibold text-white bg-blue-600 rounded-full shadow-md">
          {match.role}
        </span>
      </h3>

      {/* Company & Location (Sub-Title) */}
      <p className="text-lg text-gray-500 mb-4">
        <strong className="font-semibold text-gray-700">{match.company}</strong> in {match.location}
      </p>

      {/* Match Explanation (Provenance) */}
      <div className="bg-yellow-50 border-l-4 border-yellow-400 p-3 mb-4 text-sm text-gray-700 italic">
        <p><strong className="text-yellow-700">Matched On:</strong> {match.match_explanation}</p>
      </div>

      {/* Core Details (Idea & About) */}
      <div className="space-y-4 mb-4">
        <p className="text-gray-700 leading-relaxed">
          <strong className="text-gray-900">Idea:</strong> {match.full_details.idea}
        </p>
        <p className="text-gray-700 leading-relaxed">
          <strong className="text-gray-900">About:</strong> {match.full_details.about}
        </p>
      </div>

      {/* Full Details Expander */}
      <button
        onClick={() => setShowFullDetails(!showFullDetails)}
        className="text-blue-600 hover:text-blue-800 font-semibold text-sm mt-3 flex items-center"
      >
        {showFullDetails ? 'Hide Full Details' : 'Show Full Details'}
        {/* Add a simple chevron icon here for flair */}
      </button>

      {showFullDetails && (
        <div className="mt-4 pt-4 border-t border-gray-100 space-y-2">
          {/* Re-use your DetailItem component here with enhanced classes */}
          <DetailItem label="Keywords" value={match.full_details.keywords} />
          <DetailItem label="Stage" value={match.full_details.stage} className="font-medium text-purple-600" />

          <a
            href={match.full_details.linked_in}
            target="_blank"
            rel="noopener noreferrer"
            className="text-green-600 hover:text-green-700 font-semibold text-sm mt-3 block"
          >
            View LinkedIn Profile →
          </a>

          {/* Notes (if available) - use an Alert style */}
          {match.full_details.notes && (
            <div className="bg-red-50 border-l-4 border-red-400 p-3 mt-4 text-sm text-gray-700">
              <strong className="text-red-700">Notes:</strong> {match.full_details.notes}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// --- Component 3: Main App ---
const App = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [hasSearched, setHasSearched] = useState(false);

  // Function to handle the API search
  const handleSearch = useCallback(async (e) => {
    e.preventDefault();
    setHasSearched(true);
    if (!query.trim()) {
      setError("Please enter a search query.");
      setResults([]);
      return;
    }

    setIsLoading(true);
    setError(null);
    setResults([]);

    try {
      // NOTE: This call must point to your running FastAPI backend!
      const response = await fetch('http://127.0.0.1:8000/api/v1/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP error! Status: ${response.status}. Response: ${errorText.substring(0, 100)}...`);
      }

      const data = await response.json();
      setResults(data.matches || []);
    } catch (err) {
      console.error("API Search Error:", err);
      // Inform the user about the likely cause (FastAPI not running)
      setError(`Failed to connect to backend API or process response. Ensure the FastAPI server is running at http://127.0.0.1:8000. Error: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  }, [query]);

  // Status message logic
  const StatusMessage = useMemo(() => {
    if (error) {
      return (
        <p className="p-4 bg-red-100 text-red-700 rounded-lg font-medium shadow-md transition duration-300">
          <span className="font-bold">Error:</span> {error}
        </p>
      );
    }

    if (isLoading) {
      return (
        <div className="flex items-center justify-center p-4">
          {/* Tailwind-based Spinner SVG */}
          <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span className="text-lg text-gray-600">Searching the founder database...</span>
        </div>
      );
    }

    if (hasSearched && results.length === 0) {
      return (
        <p className="p-4 bg-yellow-100 text-yellow-700 rounded-lg font-medium shadow-md">
          No matches found for **"{query}"**.
        </p>
      );
    }

    if (!hasSearched) {
      return (
        <p className="p-4 bg-blue-50 text-blue-600 rounded-lg font-medium shadow-md">
          Type your query above to start searching the database of founders!
        </p>
      );
    }

    return null;
  }, [error, isLoading, hasSearched, results.length, query]);

  return (
    <div className="min-h-screen bg-gray-50 flex justify-center py-10">
      <div className="w-full max-w-5xl mx-auto p-4 md:p-10">
        <h1 className="text-4xl font-bold text-blue-800 mb-8 border-b-2 border-blue-100 pb-2">
          RAG Startup Matchmaker 🚀
        </h1>
        <header className="mb-6 text-center">
          <p className="text-gray-500 mt-2">Find the perfect founder match using natural language search.</p>
        </header>

        <form onSubmit={handleSearch} className="flex flex-col md:flex-row gap-4 mb-4">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g., 'A software engineer interested in health tech startups in New York'"
            disabled={isLoading}
            className="flex-grow p-4 border-2 border-gray-300 rounded-xl focus:outline-none focus:ring-4 focus:ring-blue-100 focus:border-blue-500 transition duration-200 text-gray-700 text-lg"
          />
          <button
            type="submit"
            disabled={isLoading}
            className="w-full md:w-auto px-6 py-3 font-bold text-white bg-blue-600 rounded-lg shadow-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition duration-150 transform hover:scale-[1.01]"
          >
            {isLoading ? (
              <span className="flex items-center w-full justify-center">
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" viewBox="0 0 24 24">...</svg>Searching...
              </span>
            ) : 'Find Matches'}

          </button>
        </form>

        <div className="min-h-[20px] mb-4">
          {StatusMessage}
        </div>

        {/* Results Display */}
        {results.length > 0 && (
          <div className="results-container mt-4">
            <h2 className="text-2xl font-bold text-gray-800 mb-4 border-b pb-2">
              Top {results.length} Match{results.length !== 1 ? 'es' : ''} Found:
            </h2>
            {results.map((match) => (
              <ResultCard key={match.id} match={match} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;