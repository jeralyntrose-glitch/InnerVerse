/**
 * InnerVerse Smart Hybrid Search
 * Handles exact queries (seasons, lessons) + semantic search
 */

class SmartSearch {
    constructor() {
        this.searchInput = document.getElementById('global-search');
        this.searchResults = document.getElementById('search-results');
        this.searchClear = document.getElementById('search-clear');
        this.debounceTimer = null;
        this.currentResults = [];
        
        this.init();
    }
    
    init() {
        // Search input event
        this.searchInput.addEventListener('input', (e) => {
            const query = e.target.value.trim();
            
            // Show/hide clear button
            this.searchClear.style.display = query ? 'block' : 'none';
            
            // Debounce search
            clearTimeout(this.debounceTimer);
            this.debounceTimer = setTimeout(() => {
                this.performSearch(query);
            }, 300);
        });
        
        // Clear button
        this.searchClear.addEventListener('click', () => {
            this.searchInput.value = '';
            this.searchClear.style.display = 'none';
            this.hideResults();
            this.searchInput.focus();
        });
        
        // Keyboard shortcuts
        this.searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.hideResults();
                this.searchInput.blur();
            }
        });
        
        // Click outside to close
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.search-container')) {
                this.hideResults();
            }
        });
    }
    
    async performSearch(query) {
        if (!query) {
            this.hideResults();
            return;
        }
        
        try {
            // Call backend search API
            const response = await fetch('/api/search', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({query})
            });
            
            if (!response.ok) {
                throw new Error('Search failed');
            }
            
            const results = await response.json();
            this.currentResults = results;
            this.displayResults(results, query);
            
        } catch (error) {
            console.error('Search error:', error);
            this.showError();
        }
    }
    
    displayResults(results, query) {
        if (!results || results.length === 0) {
            this.showNoResults(query);
            return;
        }
        
        // Group results by type
        const grouped = this.groupResults(results);
        
        let html = '';
        
        // Seasons
        if (grouped.seasons && grouped.seasons.length > 0) {
            html += this.renderGroup('Seasons', grouped.seasons);
        }
        
        // Lessons
        if (grouped.lessons && grouped.lessons.length > 0) {
            html += this.renderGroup('Lessons', grouped.lessons.slice(0, 5));
        }
        
        // Show "View All" if more results
        if (results.length > 5) {
            html += `
                <a href="/search?q=${encodeURIComponent(query)}" class="search-view-all">
                    👁️ View all ${results.length} results →
                </a>
            `;
        }
        
        this.searchResults.querySelector('.search-results-content').innerHTML = html;
        this.showResults();
    }
    
    groupResults(results) {
        const grouped = {
            seasons: [],
            lessons: []
        };
        
        results.forEach(result => {
            if (result.type === 'season') {
                grouped.seasons.push(result);
            } else {
                grouped.lessons.push(result);
            }
        });
        
        return grouped;
    }
    
    renderGroup(title, items) {
        let html = `<div class="search-result-group">`;
        html += `<div class="search-group-header">${title}</div>`;
        
        items.forEach(item => {
            const thumbnail = item.youtube_id 
                ? `https://img.youtube.com/vi/${item.youtube_id}/mqdefault.jpg`
                : '/static/images/placeholder.jpg';
            
            const url = item.type === 'season' 
                ? `/season/${item.season_id}`
                : `/lesson/${item.lesson_id}`;
            
            html += `
                <a href="${url}" class="search-result-item">
                    <img src="${thumbnail}" alt="${item.title}" class="search-result-thumbnail">
                    <div class="search-result-info">
                        <div class="search-result-title">${this.highlightQuery(item.title)}</div>
                        <div class="search-result-meta">${item.meta}</div>
                    </div>
                </a>
            `;
        });
        
        html += `</div>`;
        return html;
    }
    
    highlightQuery(text) {
        // TODO: Highlight search terms in results
        return text;
    }
    
    showNoResults(query) {
        this.searchResults.querySelector('.search-results-content').innerHTML = `
            <div class="search-no-results">
                <div class="search-no-results-icon">🔍</div>
                <p>No results found for "<strong>${query}</strong>"</p>
                <p style="font-size: 0.9em; margin-top: 10px;">
                    Try searching for a season number, lesson title, or topic
                </p>
            </div>
        `;
        this.showResults();
    }
    
    showError() {
        this.searchResults.querySelector('.search-results-content').innerHTML = `
            <div class="search-no-results">
                <div class="search-no-results-icon">⚠️</div>
                <p>Search temporarily unavailable</p>
            </div>
        `;
        this.showResults();
    }
    
    showResults() {
        this.searchResults.style.display = 'block';
    }
    
    hideResults() {
        this.searchResults.style.display = 'none';
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    new SmartSearch();
});
