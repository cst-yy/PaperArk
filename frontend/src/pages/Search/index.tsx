import { useState } from "react";
import { Search as SearchIcon, FileText } from "lucide-react";
import { Link } from "react-router-dom";
import { search as searchApi } from "@/features/search/api";
import type { SearchResult } from "@/features/search/types";
import { debounce } from "@/utils";

export default function Search() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);

  const debouncedSearch = debounce(async (q: string) => {
    if (q.length < 2) {
      setResults([]);
      return;
    }
    setLoading(true);
    try {
      const response = await searchApi(q);
      setResults(response.results);
    } catch (err) {
      console.error("Search failed:", err);
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, 300);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setQuery(e.target.value);
    debouncedSearch(e.target.value);
  };

  return (
    <div className="mx-auto max-w-3xl p-6">
      {/* Search bar */}
      <div className="relative mb-6">
        <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
        <input
          type="text"
          placeholder="搜索论文标题、摘要和 PDF 正文…"
          value={query}
          onChange={handleChange}
          className="input pl-10 py-3 text-base"
          autoFocus
        />
      </div>

      {/* Results */}
      {loading ? (
        <div className="py-10 text-center text-sm text-gray-400">Searching...</div>
      ) : results.length > 0 ? (
        <div className="space-y-3">
          <p className="text-xs text-gray-500">{results.length} results</p>
          {results.map((result, idx) => (
            <Link
              key={idx}
              to={`/reader/${result.paper_id}`}
              className="card block hover:shadow-md transition-shadow"
            >
              <div className="flex items-start gap-3">
                <FileText className="mt-0.5 h-4 w-4 shrink-0 text-gray-400" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900">
                    {result.title}
                  </p>
                  <p className="mt-1 text-xs text-gray-600 line-clamp-2">
                    {result.snippet}
                  </p>
                  {result.page_number && (
                    <p className="mt-1 text-[10px] text-gray-400">
                      Page {result.page_number}
                    </p>
                  )}
                </div>
              </div>
            </Link>
          ))}
        </div>
      ) : query.length >= 2 ? (
        <div className="py-10 text-center text-sm text-gray-400">
          No results found for "{query}"
        </div>
      ) : (
        <div className="py-10 text-center text-sm text-gray-400">
          Type at least 2 characters to search
        </div>
      )}
    </div>
  );
}
