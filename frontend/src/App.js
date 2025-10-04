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
        <div className="bg-white p-6 mb-4 rounded-xl shadow-lg border border-gray-100 transition duration-300 hover:shadow-xl">
            <div className="match-summary">
                <h3 className="text-xl font-extrabold text-blue-800 flex flex-wrap items-center mb-2">
                    {match.founder_name} 
                    <span className="ml-3 mt-1 md:mt-0 px-3 py-1 text-xs font-semibold text-white bg-blue-500 rounded-full shadow-md">
                        {match.role}
                    </span>
                </h3>
                <p className="text-md text-gray-600 mb-3">
                    <strong className="font-semibold text-gray-800">{match.company}</strong> in {match.location}
                </p>
                
                <p className="text-sm italic text-gray-700 p-3 bg-blue-50 rounded-lg border-l-4 border-blue-400 my-3">
                    <span className="font-bold text-blue-600">💡 Match Explanation:</span> {match.match_explanation}
                </p>
                
                <p className="text-xs text-gray-500 mt-2 pt-2 border-t border-gray-100">
                    Matched on: 
                    <span className="font-medium text-purple-600 ml-1">
                        {match.provenance.matched_on_fields}
                    </span> | ID: {match.id.substring(0, 8)}...
                </p>

                <button 
                    onClick={() => setShowFullDetails(!showFullDetails)} 
                    className="mt-4 w-full py-2 text-sm font-semibold text-blue-700 bg-blue-100 rounded-lg hover:bg-blue-200 transition duration-150"
                >
                    {showFullDetails ? "Hide Full Profile ▲" : "Show Full Profile ▼"}
                </button>
            </div>

            {/* Show More Details */}
            {showFullDetails && (
                <div className="full-details mt-4 pt-4 border-t border-gray-200 space-y-2 text-sm">
                    <DetailItem label="Stage" value={match.full_details.stage} />
                    <DetailItem label="Idea" value={match.full_details.idea} />
                    <DetailItem label="Bio" value={match.full_details.about} />
                    <DetailItem label="Keywords" value={match.full_details.keywords} />
                    <p className="flex justify-between">
                        <strong className="text-gray-700">LinkedIn:</strong> 
                        <a href={match.full_details.linked_in} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">
                            View Profile
                        </a>
                    </p>
                    {match.full_details.notes && <DetailItem label="Notes" value={match.full_details.notes} className="text-red-500 italic" />}
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
        <div className="min-h-screen bg-gray-50 p-4 sm:p-8 font-sans">
            <div className="max-w-4xl mx-auto">
                <header className="text-center py-6 mb-8 border-b-4 border-blue-500 rounded-b-xl bg-white shadow-xl">
                    <h1 className="text-4xl font-extrabold text-gray-900 tracking-tight">
                        RAG Founder Matchmaker 🚀
                    </h1>
                    <p className="text-gray-500 mt-2">Find the perfect founder match using natural language search.</p>
                </header>
                
                <form onSubmit={handleSearch} className="search-form bg-white p-6 rounded-xl shadow-lg mb-8 flex flex-col md:flex-row space-y-4 md:space-y-0 md:space-x-4">
                    <input
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="E.g., Find me a seed-stage founder with expertise in cleantech and robotics."
                        disabled={isLoading}
                        className="flex-grow p-3 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-150 text-gray-700"
                    />
                    <button 
                        type="submit" 
                        disabled={isLoading}
                        className="w-full md:w-auto px-6 py-3 font-bold text-white bg-blue-600 rounded-lg shadow-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition duration-150 transform hover:scale-[1.01]"
                    >
                        {isLoading ? 'Searching...' : 'Find Matches'}
                    </button>
                </form>

                <div className="min-h-[100px] mb-8">
                    {StatusMessage}
                </div>
                
                {/* Results Display */}
                {results.length > 0 && (
                    <div className="results-container mt-6">
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
