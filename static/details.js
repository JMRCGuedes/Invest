// Fetch and display portfolio holdings
async function loadPortfolio() {
    try {
        const response = await fetch('/api/portfolio');
        const data = await response.json();
        
        const tbody = document.getElementById('portfolio-body');
        
        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" class="loading">No holdings in portfolio</td></tr>';
            return;
        }
        
        tbody.innerHTML = data.map(item => `
            <tr>
                <td><strong>${item.asset}</strong></td>
                <td><span class="type-badge type-${item.type.toLowerCase()}">${item.type}</span></td>
                <td>${item.quantity}</td>
                <td>${formatCurrency(item.average_price)}</td>
                <td>${formatCurrency(item.current_price)}</td>
                <td>${formatCurrency(item.invested_value)}</td>
                <td>${formatCurrency(item.current_value)}</td>
                <td class="${item.profit >= 0 ? 'positive' : 'negative'}">${formatCurrency(item.profit)}</td>
                <td class="${item.return_pct >= 0 ? 'positive' : 'negative'}">${item.return_pct.toFixed(2)}%</td>
            </tr>
        `).join('');
        
    } catch (error) {
        console.error('Error loading portfolio:', error);
        document.getElementById('portfolio-body').innerHTML = 
            '<tr><td colspan="9" class="loading">Error loading portfolio data</td></tr>';
    }
}

// Fetch and display trading signals
async function loadSignals() {
    try {
        const response = await fetch('/api/signals');
        const data = await response.json();
        
        const tbody = document.getElementById('signals-body');
        
        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="loading">No signals available</td></tr>';
            return;
        }
        
        tbody.innerHTML = data.map(item => `
            <tr>
                <td>${item.date}</td>
                <td><strong>${item.asset}</strong></td>
                <td><span class="type-badge type-${item.asset_type.toLowerCase()}">${item.asset_type}</span></td>
                <td><span class="decision-badge decision-${item.decision.toLowerCase()}">${item.decision}</span></td>
                <td>${item.confidence}</td>
                <td>${formatCurrency(item.price)}</td>
            </tr>
        `).join('');
        
    } catch (error) {
        console.error('Error loading signals:', error);
        document.getElementById('signals-body').innerHTML = 
            '<tr><td colspan="6" class="loading">Error loading signals data</td></tr>';
    }
}

// Fetch and display trade history
async function loadTradeHistory() {
    try {
        const response = await fetch('/api/trade-history');
        const data = await response.json();
        
        const tbody = document.getElementById('history-body');
        
        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="loading">No trade history available</td></tr>';
            return;
        }
        
        // Reverse to show most recent first
        const reversed = data.reverse();
        
        tbody.innerHTML = reversed.map(item => `
            <tr>
                <td>${item.date}</td>
                <td><strong>${item.asset}</strong></td>
                <td><span class="type-badge type-${item.asset_type.toLowerCase()}">${item.asset_type}</span></td>
                <td><span class="decision-badge decision-${item.decision.toLowerCase()}">${item.decision}</span></td>
                <td>${item.confidence}</td>
                <td>${formatCurrency(item.price)}</td>
            </tr>
        `).join('');
        
    } catch (error) {
        console.error('Error loading trade history:', error);
        document.getElementById('history-body').innerHTML = 
            '<tr><td colspan="6" class="loading">Error loading trade history</td></tr>';
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

// Initialize details page
document.addEventListener('DOMContentLoaded', function() {
    loadPortfolio();
    loadSignals();
    loadTradeHistory();
});
