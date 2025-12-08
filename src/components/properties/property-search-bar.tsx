'use client';

import { useState, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { propertyApi } from '@/lib/api';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Search, X } from 'lucide-react';
import debounce from 'lodash/debounce';

interface PropertySearchBarProps {
  onSearch: (query: string) => void;
}

export function PropertySearchBar({ onSearch }: PropertySearchBarProps) {
  const [query, setQuery] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);

  const { data: suggestions } = useQuery({
    queryKey: ['autocomplete', query],
    queryFn: () => propertyApi.autocomplete(query),
    enabled: query.length >= 3,
  });

  const debouncedSearch = useCallback(
    debounce((value: string) => {
      if (value.length >= 3) {
        setShowSuggestions(true);
      }
    }, 300),
    []
  );

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setQuery(value);
    debouncedSearch(value);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setShowSuggestions(false);
    onSearch(query);
  };

  const handleSelect = (address: string) => {
    setQuery(address);
    setShowSuggestions(false);
    onSearch(address);
  };

  const handleClear = () => {
    setQuery('');
    setShowSuggestions(false);
    onSearch('');
  };

  return (
    <form onSubmit={handleSubmit} className="relative">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          type="text"
          placeholder="Search by address, parcel ID, or owner name..."
          value={query}
          onChange={handleChange}
          onFocus={() => query.length >= 3 && setShowSuggestions(true)}
          className="pl-10 pr-10"
        />
        {query && (
          <button
            type="button"
            onClick={handleClear}
            className="absolute right-3 top-1/2 -translate-y-1/2"
          >
            <X className="h-4 w-4 text-muted-foreground hover:text-foreground" />
          </button>
        )}
      </div>

      {/* Autocomplete Suggestions */}
      {showSuggestions && suggestions && suggestions.length > 0 && (
        <div className="absolute z-50 w-full mt-1 bg-white rounded-md border shadow-lg max-h-60 overflow-auto">
          {suggestions.map((suggestion, index) => (
            <button
              key={index}
              type="button"
              onClick={() => handleSelect(suggestion.address)}
              className="w-full px-4 py-2 text-left text-sm hover:bg-gray-100 focus:bg-gray-100"
            >
              <span className="font-medium">{suggestion.address}</span>
              {suggestion.city && (
                <span className="text-muted-foreground ml-2">
                  {suggestion.city}
                </span>
              )}
            </button>
          ))}
        </div>
      )}
    </form>
  );
}
