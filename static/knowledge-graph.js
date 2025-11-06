// Knowledge Graph 3D Visualization - Simplified & Reliable
// InnerVerse - CS Joseph's MBTI Knowledge Graph

// Simpler initialization that works more reliably
async function initializeGraph() {
  console.log('🚀 Initializing Knowledge Graph...');
  
  try {
    console.log('📡 Fetching data...');
    const response = await fetch('/api/knowledge-graph');
    const data = await response.json();
    
    console.log(`✅ Loaded ${data.nodes.length} nodes, ${data.edges.length} edges`);
    
    // Filter data
    const minFreq = 3;
    const nodes = data.nodes.filter(n => (n.frequency || 1) >= minFreq);
    const nodeIds = new Set(nodes.map(n => n.id));
    const links = data.edges.filter(e => 
      nodeIds.has(e.source) && nodeIds.has(e.target)
    );
    
    console.log(`🔍 Filtered to ${nodes.length} nodes, ${links.length} links`);
    
    // Color scheme
    const categoryColors = {
      foundational: '#7C3AED',
      intermediate: '#A78BFA',
      advanced: '#EC4899',
      uncategorized: '#6B7280'
    };
    
    // Format for ForceGraph
    const graphData = {
      nodes: nodes.map(n => ({
        id: n.id,
        name: n.label,
        val: (n.frequency || 1) * 2,
        color: categoryColors[n.category] || categoryColors.uncategorized,
        category: n.category,
        definition: n.definition || 'No definition available',
        frequency: n.frequency || 1
      })),
      links: links.map(e => ({
        source: e.source,
        target: e.target,
        relationship: e.relationship_type
      }))
    };
    
    // Update stats
    document.getElementById('concept-count').textContent = nodes.length;
    document.getElementById('connection-count').textContent = links.length;
    document.getElementById('document-count').textContent = data.metadata?.total_documents_processed || 0;
    
    // Initialize graph with minimal config
    console.log('🎨 Creating 3D graph...');
    const elem = document.getElementById('graph-container');
    
    if (!elem) {
      throw new Error('Graph container not found');
    }
    
    const Graph = ForceGraph3D()
      (elem)
      .graphData(graphData)
      .nodeLabel(node => `${node.name} (${node.frequency}x)`)
      .nodeAutoColorBy('color')
      .nodeVal('val')
      .backgroundColor('#0F172A')
      .linkColor(() => '#475569')
      .linkOpacity(0.3)
      .width(elem.clientWidth || 1200)
      .height(elem.clientHeight || 600)
      .onNodeClick(node => {
        showNodeDetails(node);
      })
      .onNodeHover(node => {
        elem.style.cursor = node ? 'pointer' : 'default';
      });
      
    console.log('✅ Graph initialized successfully!');
    
    // Hide loading indicator
    const loadingEl = document.getElementById('loading-indicator');
    if (loadingEl) {
      loadingEl.style.display = 'none';
    }
    
    // Store graph reference
    window.graph3D = Graph;
    
  } catch (error) {
    console.error('❌ Graph initialization failed:', error);
    const elem = document.getElementById('graph-container');
    if (elem) {
      elem.innerHTML = `
        <div style="color: white; padding: 50px; text-align: center;">
          <p style="font-size: 20px; margin-bottom: 10px;">❌ Failed to Load Graph</p>
          <p style="font-size: 14px; color: #94A3B8;">${error.message}</p>
          <button onclick="location.reload()" style="margin-top: 20px; padding: 10px 20px; background: #7C3AED; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 14px;">
            Retry
          </button>
        </div>
      `;
    }
  }
}

// Show node details in sidebar panel
function showNodeDetails(node) {
  const panel = document.getElementById('node-details-panel');
  if (!panel) return;
  
  document.getElementById('node-name').textContent = node.name;
  document.getElementById('node-category').textContent = node.category || 'uncategorized';
  document.getElementById('node-frequency').textContent = node.frequency || 1;
  document.getElementById('node-definition').textContent = node.definition || 'No definition available';
  
  panel.style.display = 'block';
}

// Event listeners
document.addEventListener('DOMContentLoaded', () => {
  console.log('📄 DOM loaded, setting up controls...');
  
  // Close panel button
  const closeBtn = document.getElementById('close-panel-btn');
  if (closeBtn) {
    closeBtn.addEventListener('click', () => {
      document.getElementById('node-details-panel').style.display = 'none';
    });
  }
  
  // Center graph button
  const centerBtn = document.getElementById('center-graph-btn');
  if (centerBtn) {
    centerBtn.addEventListener('click', () => {
      if (window.graph3D) {
        window.graph3D.zoomToFit(400);
      }
    });
  }
  
  // Dismiss instructions
  const dismissBtn = document.getElementById('dismiss-instructions');
  if (dismissBtn) {
    dismissBtn.addEventListener('click', () => {
      document.getElementById('instructions').style.display = 'none';
      localStorage.setItem('kg-instructions-dismissed', 'true');
    });
  }
  
  // Auto-hide instructions if previously dismissed
  if (localStorage.getItem('kg-instructions-dismissed') === 'true') {
    const instructions = document.getElementById('instructions');
    if (instructions) {
      instructions.style.display = 'none';
    }
  }
  
  console.log('✅ Controls ready');
});

// Run when page loads
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeGraph);
} else {
  initializeGraph();
}
