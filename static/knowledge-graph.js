// Knowledge Graph 3D Visualization
// InnerVerse - CS Joseph's MBTI Knowledge Graph

let graphData = { nodes: [], edges: [] };
let fullGraphData = { nodes: [], edges: [] };
let graphStats = {};
let graph3D = null;
let selectedNode = null;

// Filter states
let frequencyThreshold = 3;
let categoryFilter = 'all';
let searchTerm = '';

// Color schemes
function getCategoryColor(category) {
    const colors = {
        foundational: '#7C3AED',    // Purple
        intermediate: '#A78BFA',     // Light purple
        advanced: '#EC4899',         // Pink
        uncategorized: '#6B7280'     // Gray
    };
    return colors[category] || colors.uncategorized;
}

function getRelationshipColor(type) {
    const colors = {
        requires_understanding: '#7C3AED',
        leads_to: '#10B981',
        contrasts_with: '#EF4444',
        builds_on: '#3B82F6',
        enables: '#F59E0B',
        manifests_as: '#8B5CF6',
        part_of: '#6366F1',
        related_to: '#6B7280'
    };
    return colors[type] || colors.related_to;
}

// Load graph data from API
async function loadGraphData() {
    console.log('🔄 Starting graph data load...');
    
    try {
        console.log('📡 Fetching from /api/knowledge-graph...');
        const response = await fetch('/api/knowledge-graph');
        const data = await response.json();
        console.log('✅ Data received:', data.nodes.length, 'nodes,', data.edges.length, 'edges');
        
        // Transform to 3D force graph format
        fullGraphData = {
            nodes: data.nodes.map(node => ({
                id: node.id,
                label: node.label,
                type: node.type,
                category: node.category,
                definition: node.definition || 'No definition available',
                frequency: node.frequency || 1,
                val: Math.max(5, (node.frequency || 1) * 2), // Node size based on frequency
                color: getCategoryColor(node.category),
                sourceDocuments: node.source_documents || []
            })),
            edges: data.edges.map(edge => ({
                source: edge.source,
                target: edge.target,
                label: edge.relationship_type,
                strength: edge.strength || 1,
                color: getRelationshipColor(edge.relationship_type),
                evidence: edge.evidence_samples || []
            }))
        };
        
        graphStats = data.metadata || {};
        console.log('📊 Graph stats:', graphStats);
        
        // Update stats display
        document.getElementById('document-count').textContent = graphStats.total_documents_processed || 0;
        
        // Apply initial filters
        console.log('🔍 Applying filters...');
        updateFilteredGraph();
        
        // Hide loading indicator
        document.getElementById('loading-indicator').style.display = 'none';
        
        // Initialize 3D graph
        console.log('🎨 Initializing 3D graph...');
        initGraph3D();
        
    } catch (error) {
        console.error('❌ Failed to load graph:', error);
        document.getElementById('loading-indicator').innerHTML = `
            <div style="color: #EF4444;">
                <p>❌ Failed to load knowledge graph</p>
                <p style="font-size: 14px; color: #94A3B8;">${error.message}</p>
                <p style="font-size: 12px; color: #94A3B8; margin-top: 10px;">Check console for details</p>
            </div>
        `;
    }
}

// Update filtered graph data
function updateFilteredGraph() {
    // Filter nodes by frequency threshold
    let nodes = fullGraphData.nodes.filter(node =>
        node.frequency >= frequencyThreshold
    );
    
    // Apply category filter
    if (categoryFilter !== 'all') {
        nodes = nodes.filter(node => node.category === categoryFilter);
    }
    
    // Apply search filter
    if (searchTerm) {
        const search = searchTerm.toLowerCase();
        nodes = nodes.filter(node =>
            node.label.toLowerCase().includes(search) ||
            node.definition.toLowerCase().includes(search)
        );
    }
    
    // Only include edges where both nodes are visible
    const nodeIds = new Set(nodes.map(n => n.id));
    const edges = fullGraphData.edges.filter(edge =>
        nodeIds.has(edge.source) && nodeIds.has(edge.target)
    );
    
    graphData = { nodes, edges };
    
    // Update stats
    document.getElementById('concept-count').textContent = nodes.length;
    document.getElementById('connection-count').textContent = edges.length;
    
    // Update graph if initialized
    if (graph3D) {
        graph3D.graphData(graphData);
    }
}

// Initialize 3D Force Graph
function initGraph3D() {
    const container = document.getElementById('graph-container');
    
    console.log('🌐 Initializing Knowledge Graph...');
    console.log('Container:', container);
    console.log('Container size:', container.offsetWidth, 'x', container.offsetHeight);
    console.log('Graph data:', graphData.nodes.length, 'nodes,', graphData.edges.length, 'edges');
    
    try {
        graph3D = ForceGraph3D()
            (container)
            .graphData(graphData)
            .nodeLabel('label')
            .nodeColor('color')
            .nodeVal('val')
            .linkLabel('label')
            .linkColor('color')
            .linkWidth(link => link.strength * 0.5)
            .linkDirectionalParticles(2)
            .linkDirectionalParticleWidth(1.5)
            .backgroundColor('#0F172A')
            .width(container.offsetWidth)
            .height(container.offsetHeight)
            .onNodeClick(handleNodeClick)
            .onNodeHover(handleNodeHover)
            .onNodeDragEnd(node => {
                node.fx = node.x;
                node.fy = node.y;
                node.fz = node.z;
            });
        
        // Add node labels
        graph3D.nodeThreeObject(node => {
            const sprite = new SpriteText(node.label);
            sprite.material.depthWrite = false;
            sprite.color = node.color;
            sprite.textHeight = 4;
            return sprite;
        });
        
        console.log('✅ Knowledge Graph initialized successfully!');
        
        // Handle window resize
        window.addEventListener('resize', () => {
            if (graph3D) {
                graph3D
                    .width(container.offsetWidth)
                    .height(container.offsetHeight);
            }
        });
        
    } catch (error) {
        console.error('❌ Failed to initialize 3D graph:', error);
        
        // Show fallback message for browsers without WebGL
        container.innerHTML = `
            <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: #F8FAFC; text-align: center; padding: 40px;">
                <div style="font-size: 60px; margin-bottom: 20px;">🌐</div>
                <h2 style="color: #7C3AED; margin-bottom: 10px;">WebGL Not Available</h2>
                <p style="color: #94A3B8; max-width: 500px; margin-bottom: 20px;">
                    Your browser or environment doesn't support WebGL, which is required for the 3D visualization.
                </p>
                <p style="color: #CBD5E1; max-width: 500px;">
                    <strong>Graph Data Loaded:</strong><br>
                    ${graphData.nodes.length} concepts, ${graphData.edges.length} connections
                </p>
                <p style="color: #94A3B8; font-size: 14px; margin-top: 20px;">
                    Try using Chrome, Firefox, or Safari on a device with GPU support.
                </p>
            </div>
        `;
    }
}

// Handle node click
function handleNodeClick(node) {
    if (!node) return;
    
    selectedNode = node;
    
    // Find connected nodes
    const connections = graphData.edges
        .filter(edge =>
            edge.source.id === node.id || edge.target.id === node.id
        )
        .map(edge => {
            const isSource = edge.source.id === node.id;
            const neighbor = isSource ? edge.target : edge.source;
            return {
                label: neighbor.label,
                relationship: edge.label,
                direction: isSource ? '→' : '←'
            };
        });
    
    // Update panel
    document.getElementById('node-label').textContent = node.label;
    document.getElementById('node-definition').textContent = node.definition;
    
    // Update badges
    document.getElementById('node-meta').innerHTML = `
        <span class="badge">${node.type}</span>
        <span class="badge">${node.category}</span>
        <span class="badge">Frequency: ${node.frequency}</span>
    `;
    
    // Update connections
    document.getElementById('connections-header').textContent = 
        `Connected Concepts (${connections.length})`;
    
    const connectionsList = document.getElementById('connections-list');
    if (connections.length === 0) {
        connectionsList.innerHTML = '<li style="color: #6B7280;">No connections</li>';
    } else {
        connectionsList.innerHTML = connections
            .slice(0, 15) // Show max 15
            .map(conn => `
                <li>${conn.direction} ${conn.relationship}: <strong>${conn.label}</strong></li>
            `)
            .join('');
        
        if (connections.length > 15) {
            connectionsList.innerHTML += `
                <li style="color: #7C3AED; font-style: italic;">
                    + ${connections.length - 15} more connections
                </li>
            `;
        }
    }
    
    // Update sources
    const docCount = node.sourceDocuments?.length || 0;
    document.getElementById('sources-header').textContent = 
        `Appears in ${docCount} ${docCount === 1 ? 'document' : 'documents'}`;
    
    // Show panel
    document.getElementById('node-details-panel').style.display = 'block';
    
    // Center camera on node
    const distance = 150;
    const distRatio = 1 + distance / Math.hypot(node.x, node.y, node.z);
    
    graph3D.cameraPosition(
        { x: node.x * distRatio, y: node.y * distRatio, z: node.z * distRatio },
        node,
        1000
    );
}

// Handle node hover
function handleNodeHover(node) {
    container.style.cursor = node ? 'pointer' : 'default';
}

// View source documents
function viewSourceDocs() {
    if (!selectedNode || !selectedNode.sourceDocuments || selectedNode.sourceDocuments.length === 0) {
        alert('No source documents available for this concept.');
        return;
    }
    
    // Navigate to Content Atlas filtered by these documents
    const docIds = selectedNode.sourceDocuments.join(',');
    window.location.href = `/content-atlas?documents=${docIds}`;
}

// Set up event listeners (called from init function)
function setupEventListeners() {
    console.log('⚡ Setting up event listeners...');
    
    // Frequency slider
    const frequencySlider = document.getElementById('frequency-slider');
    const thresholdDisplay = document.getElementById('threshold-display');
    
    frequencySlider.addEventListener('input', (e) => {
        frequencyThreshold = parseInt(e.target.value);
        thresholdDisplay.textContent = `≥ ${frequencyThreshold}`;
        updateFilteredGraph();
    });
    
    // Category filter
    const categorySelect = document.getElementById('category-filter');
    categorySelect.addEventListener('change', (e) => {
        categoryFilter = e.target.value;
        updateFilteredGraph();
    });
    
    // Search input with debounce
    const searchInput = document.getElementById('search-input');
    let searchTimeout;
    searchInput.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            searchTerm = e.target.value;
            updateFilteredGraph();
        }, 300);
    });
    
    // Reset filters
    document.getElementById('reset-filters-btn').addEventListener('click', () => {
        frequencyThreshold = 3;
        categoryFilter = 'all';
        searchTerm = '';
        
        frequencySlider.value = 3;
        thresholdDisplay.textContent = '≥ 3';
        categorySelect.value = 'all';
        searchInput.value = '';
        
        updateFilteredGraph();
    });
    
    // Center graph
    document.getElementById('center-graph-btn').addEventListener('click', () => {
        if (graph3D) {
            graph3D.zoomToFit(1000);
        }
    });
    
    // Close panel
    document.getElementById('close-panel-btn').addEventListener('click', () => {
        document.getElementById('node-details-panel').style.display = 'none';
        selectedNode = null;
    });
    
    // View sources button
    document.getElementById('view-sources-btn').addEventListener('click', viewSourceDocs);
    
    // Dismiss instructions
    document.getElementById('dismiss-instructions').addEventListener('click', () => {
        document.getElementById('instructions').style.display = 'none';
        localStorage.setItem('kg-instructions-dismissed', 'true');
    });
    
    // Check if instructions were dismissed
    if (localStorage.getItem('kg-instructions-dismissed') === 'true') {
        document.getElementById('instructions').style.display = 'none';
    }
    
    console.log('✅ Event listeners setup complete');
}

// SpriteText class for 3D labels (simplified version)
class SpriteText extends THREE.Sprite {
    constructor(text = '', textHeight = 10, color = '#ffffff') {
        super(new THREE.SpriteMaterial());
        this._text = `${text}`;
        this._textHeight = textHeight;
        this._color = color;
        
        this._fontFace = 'Arial';
        this._fontSize = 90;
        this._fontWeight = 'normal';
        
        this._canvas = document.createElement('canvas');
        this._texture = new THREE.Texture(this._canvas);
        this.material.map = this._texture;
        
        this._genCanvas();
    }
    
    get text() { return this._text; }
    set text(text) {
        this._text = text;
        this._genCanvas();
    }
    
    get textHeight() { return this._textHeight; }
    set textHeight(textHeight) {
        this._textHeight = textHeight;
        this._genCanvas();
    }
    
    get color() { return this._color; }
    set color(color) {
        this._color = color;
        this._genCanvas();
    }
    
    _genCanvas() {
        const canvas = this._canvas;
        const ctx = canvas.getContext('2d');
        
        const font = `${this._fontWeight} ${this._fontSize}px ${this._fontFace}`;
        ctx.font = font;
        
        const textWidth = ctx.measureText(this._text).width;
        canvas.width = textWidth;
        canvas.height = this._fontSize;
        
        ctx.font = font;
        ctx.fillStyle = this._color;
        ctx.textBaseline = 'bottom';
        ctx.fillText(this._text, 0, canvas.height);
        
        this._texture.needsUpdate = true;
        
        const yScale = this._textHeight * 0.1;
        const xScale = yScale * textWidth / this._fontSize;
        this.scale.set(xScale, yScale, 1);
    }
    
    dispose() {
        this._texture.dispose();
        this.material.dispose();
    }
}

// Mobile: Make legend collapsible on small screens
function initMobileLegend() {
    if (window.innerWidth <= 768) {
        const legendEl = document.getElementById('legend');
        const legendHeader = legendEl.querySelector('.legend-header');
        
        if (legendHeader && legendEl) {
            // Start collapsed on mobile to save space
            legendEl.classList.add('collapsed');
            
            legendHeader.addEventListener('click', () => {
                legendEl.classList.toggle('collapsed');
            });
            
            console.log('📱 Mobile legend collapsibility enabled');
        }
    }
}

// Check if libraries are loaded
function checkLibraries() {
    console.log('🔍 Checking libraries...');
    console.log('ForceGraph3D available?', typeof ForceGraph3D !== 'undefined');
    console.log('THREE available?', typeof THREE !== 'undefined');
    
    if (typeof ForceGraph3D === 'undefined') {
        console.error('❌ ForceGraph3D library not loaded!');
        document.getElementById('loading-indicator').innerHTML = `
            <div style="color: #EF4444; padding: 20px; text-align: center;">
                <p style="font-size: 18px; margin-bottom: 10px;">❌ 3D Graph Library Failed to Load</p>
                <p style="font-size: 14px; color: #94A3B8;">The 3D visualization library couldn't load from the CDN.</p>
                <p style="font-size: 14px; color: #94A3B8; margin-top: 10px;">This might be due to network issues or ad blockers.</p>
                <button onclick="location.reload()" style="margin-top: 20px; padding: 10px 20px; background: #7C3AED; color: white; border: none; border-radius: 8px; cursor: pointer;">
                    Retry
                </button>
            </div>
        `;
        return false;
    }
    
    if (typeof THREE === 'undefined') {
        console.error('❌ THREE.js library not loaded!');
        return false;
    }
    
    console.log('✅ All libraries loaded');
    return true;
}

// Initialize everything
function init() {
    console.log('🚀 Knowledge Graph page initializing...');
    
    // Check libraries first
    if (!checkLibraries()) {
        console.error('❌ Libraries not available, cannot initialize graph');
        return;
    }
    
    // Set up event listeners
    setupEventListeners();
    
    // Initialize mobile features
    initMobileLegend();
    
    // Load graph data
    console.log('📊 Loading graph data...');
    loadGraphData();
}

// Initialize on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    // DOM already loaded
    init();
}

// Re-initialize mobile features on window resize
let resizeTimer;
window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
        initMobileLegend();
    }, 250);
});
