// Global chart instances
let assetAllocationChart = null;
let tradingActivityChart = null;

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
        
        const profitPercent = (profit / 10000) * 100; // INITIAL_CAPITAL = 10000
        percentageElement.textContent = (profit >= 0 ? '+' : '') + profitPercent.toFixed(2) + '%';
        percentageElement.className = 'card-percentage ' + (profit >= 0 ? 'positive' : 'negative');
        
    } catch (error) {
        console.error('Error loading summary:', error);
    }
}

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

// Load asset allocation chart
async function loadAssetAllocationChart() {
    try {
        const response = await fetch('/api/asset-allocation');
        const data = await response.json();
        
        if (data.length === 0) return;
        
        const ctx = document.getElementById('assetAllocationChart');
        
        // Destroy existing chart if it exists
        if (assetAllocationChart) {
            assetAllocationChart.destroy();
        }
        
        const labels = data.map(item => item.asset);
        const values = data.map(item => item.current_value);
        
        assetAllocationChart = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: [
                        '#667eea', '#764ba2', '#f093fb', '#4facfe',
                        '#43e97b', '#fa709a', '#fee140', '#30cfd0',
                        '#a8edea', '#fed6e3', '#c471f5', '#12c2e9'
                    ],
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            generateLabels: function(chart) {
                                const data = chart.data;
                                return data.labels.map((label, i) => ({
                                    text: `${label}: ${formatCurrency(data.datasets[0].data[i])}`,
                                    fillStyle: data.datasets[0].backgroundColor[i],
                                    hidden: false,
                                    index: i
                                }));
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.parsed || 0;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((value / total) * 100).toFixed(1);
                                return `${label}: ${formatCurrency(value)} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
        
    } catch (error) {
        console.error('Error loading asset allocation chart:', error);
    }
}

// Load trading activity chart
async function loadTradingActivityChart() {
    try {
        const response = await fetch('/api/performance-history');
        const data = await response.json();
        
        if (data.length === 0) return;
        
        const ctx = document.getElementById('tradingActivityChart');
        
        // Destroy existing chart if it exists
        if (tradingActivityChart) {
            tradingActivityChart.destroy();
        }
        
        const labels = data.map(item => item.date);
        const buys = data.map(item => item.buys);
        const sells = data.map(item => item.sells);
        
        tradingActivityChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Buy Signals',
                        data: buys,
                        backgroundColor: '#10b981',
                        borderColor: '#059669',
                        borderWidth: 1
                    },
                    {
                        label: 'Sell Signals',
                        data: sells,
                        backgroundColor: '#ef4444',
                        borderColor: '#dc2626',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        stacked: false,
                        grid: {
                            display: false
                        }
                    },
                    y: {
                        stacked: false,
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                }
            }
        });
        
    } catch (error) {
        console.error('Error loading trading activity chart:', error);
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

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    loadSummary();
    loadPortfolio();
    loadSignals();
    loadTradeHistory();
    loadAssetAllocationChart();
    loadTradingActivityChart();
    
    // Optional: Refresh data every 5 minutes (300000ms)
    // Uncomment the lines below if you want auto-refresh
    /*
    setInterval(() => {
        loadSummary();
        loadPortfolio();
        loadSignals();
        loadTradeHistory();
        loadAssetAllocationChart();
        loadTradingActivityChart();
    }, 300000);
    */
});
