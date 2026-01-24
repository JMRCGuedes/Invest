// Fetch and display portfolio summary
async function loadSummary() {
    try {
        const response = await fetch('/api/summary');
        const data = await response.json();
        
        document.getElementById('available-cash').textContent = formatCurrency(data.available_cash);
        document.getElementById('total-invested').textContent = formatCurrency(data.total_invested);
        document.getElementById('portfolio-value').textContent = formatCurrency(data.portfolio_value);
        
        const profit = data.total_profit;
        const profitElement = document.getElementById('total-profit');
        const percentageElement = document.getElementById('profit-percentage');
        
        profitElement.textContent = formatCurrency(profit);
        profitElement.className = 'card-value ' + (profit >= 0 ? 'positive' : 'negative');
        
        const profitPercent = (profit / 10000) * 100;
        percentageElement.textContent = (profit >= 0 ? '+' : '') + profitPercent.toFixed(2) + '%';
        percentageElement.className = 'card-percentage ' + (profit >= 0 ? 'positive' : 'negative');
        
    } catch (error) {
        console.error('Error loading summary:', error);
    }
}

// Load allocation chart (CSS-based)
async function loadAllocationChart() {
    try {
        const response = await fetch('/api/portfolio');
        const data = await response.json();
        
        const container = document.getElementById('allocation-chart');
        
        if (data.length === 0) {
            container.innerHTML = '<div class="loading">No holdings available</div>';
            return;
        }
        
        // Calculate total value
        const total = data.reduce((sum, item) => sum + item.current_value, 0);
        
        // Sort by value descending
        data.sort((a, b) => b.current_value - a.current_value);
        
        // Create bar chart
        container.innerHTML = data.map(item => {
            const percentage = (item.current_value / total * 100).toFixed(1);
            return `
                <div class="chart-row">
                    <div class="chart-label">
                        <span class="chart-asset">${item.asset}</span>
                        <span class="chart-value">${formatCurrency(item.current_value)}</span>
                    </div>
                    <div class="chart-bar-container">
                        <div class="chart-bar" style="width: ${percentage}%">
                            <span class="chart-percentage">${percentage}%</span>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
        
    } catch (error) {
        console.error('Error loading allocation chart:', error);
    }
}

// Load holdings as simple list
async function loadHoldings() {
    try {
        const response = await fetch('/api/portfolio');
        const data = await response.json();
        
        const container = document.getElementById('holdings-list');
        
        if (data.length === 0) {
            container.innerHTML = '<div class="loading">No holdings in portfolio</div>';
            return;
        }
        
        container.innerHTML = data.map(item => `
            <div class="holding-item">
                <div class="holding-header">
                    <span class="holding-asset">${item.asset}</span>
                    <span class="type-badge type-${item.type.toLowerCase()}">${item.type}</span>
                </div>
                <div class="holding-details">
                    <div class="holding-stat">
                        <span class="stat-label">Quantity</span>
                        <span class="stat-value">${item.quantity}</span>
                    </div>
                    <div class="holding-stat">
                        <span class="stat-label">Current Price</span>
                        <span class="stat-value">${formatCurrency(item.current_price)}</span>
                    </div>
                    <div class="holding-stat">
                        <span class="stat-label">Value</span>
                        <span class="stat-value">${formatCurrency(item.current_value)}</span>
                    </div>
                    <div class="holding-stat">
                        <span class="stat-label">Profit/Loss</span>
                        <span class="stat-value ${item.profit >= 0 ? 'positive' : 'negative'}">${formatCurrency(item.profit)} (${item.return_pct.toFixed(2)}%)</span>
                    </div>
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Error loading holdings:', error);
    }
}

// Utility function to format currency
function formatCurrency(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(value);
}

// Load assets for performance chart
async function loadPerformanceAssets() {
    try {
        const response = await fetch('/api/assets');
        const assets = await response.json();
        
        const select = document.getElementById('performance-asset-select');
        
        if (assets.length === 0) {
            select.innerHTML = '<option value="">No assets available</option>';
            return;
        }
        
        select.innerHTML = '<option value="">Select an asset...</option>' + 
            assets.map(asset => `<option value="${asset}">${asset}</option>`).join('');
        
        // Load first asset by default
        if (assets.length > 0) {
            select.value = assets[0];
            loadPerformanceChart(assets[0]);
        }
        
        // Add change listener
        select.addEventListener('change', (e) => {
            if (e.target.value) {
                loadPerformanceChart(e.target.value);
            }
        });
        
    } catch (error) {
        console.error('Error loading performance assets:', error);
    }
}

// Load performance chart for specific asset
async function loadPerformanceChart(asset) {
    try {
        const response = await fetch(`/api/asset-performance/${asset}`);
        const data = await response.json();
        
        const container = document.getElementById('performance-chart');
        
        if (data.length === 0) {
            container.innerHTML = '<div class="loading">No trading history for this asset</div>';
            return;
        }
        
        // Find min and max for scaling
        const profits = data.map(d => d.cumulative_profit);
        const minProfit = Math.min(...profits, 0);
        const maxProfit = Math.max(...profits, 0);
        const range = maxProfit - minProfit || 1;
        
        // Create timeline visualization
        let html = '<div class="performance-summary">';
        const finalProfit = data[data.length - 1].cumulative_profit;
        const profitClass = finalProfit >= 0 ? 'positive' : 'negative';
        html += `<div class="performance-total ${profitClass}">Total P/L: ${formatCurrency(finalProfit)}</div>`;
        html += '</div>';
        
        html += '<div class="performance-timeline">';
        
        data.forEach((point, index) => {
            const profit = point.cumulative_profit;
            const height = Math.abs((profit - minProfit) / range * 100);
            const isPositive = profit >= 0;
            const decisionClass = point.decision === 'BUY' ? 'buy-marker' : 
                                   point.decision === 'SELL' ? 'sell-marker' : 'hold-marker';
            
            html += `
                <div class="timeline-point" data-index="${index}">
                    <div class="point-marker ${decisionClass}" title="${point.decision} at ${formatCurrency(point.price)}">
                        ${point.decision === 'BUY' ? '▲' : point.decision === 'SELL' ? '▼' : '●'}
                    </div>
                    <div class="point-bar ${isPositive ? 'profit-bar' : 'loss-bar'}" style="height: ${height}%"></div>
                    <div class="point-info">
                        <div class="point-date">${point.date}</div>
                        <div class="point-profit ${isPositive ? 'positive' : 'negative'}">${formatCurrency(profit)}</div>
                        <div class="point-price">${formatCurrency(point.price)}</div>
                    </div>
                </div>
            `;
        });
        
        html += '</div>';
        
        container.innerHTML = html;
        
    } catch (error) {
        console.error('Error loading performance chart:', error);
    }
}

// Initialize dashboard ONCE
(function() {
    let initialized = false;
    
    function init() {
        if (initialized) return;
        initialized = true;
        
        loadSummary();
        loadAllocationChart();
        loadPerformanceAssets();
        loadHoldings();
    }
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
