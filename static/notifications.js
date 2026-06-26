function formatCurrency(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency', currency: 'USD',
        minimumFractionDigits: 2, maximumFractionDigits: 2
    }).format(value);
}

async function loadNotifications() {
    try {
        const [notifRes, signalRes] = await Promise.all([
            fetch('/api/notifications'),
            fetch('/api/signals'),
        ]);
        const actions = await notifRes.json();
        const signals = await signalRes.json();

        // ── Signal summary counts ──────────────────────
        const summaryEl = document.getElementById('signal-summary');
        if (signals.length === 0) {
            summaryEl.innerHTML = '<div class="loading">No signal data available.</div>';
        } else {
            const n_buy  = signals.filter(s => s.decision === 'BUY').length;
            const n_sell = signals.filter(s => s.decision === 'SELL').length;
            const n_hold = signals.filter(s => s.decision === 'HOLD').length;
            const runDate = signals[0]?.date?.split(' ')[0] ?? '';
            summaryEl.innerHTML = `
                <div class="signal-summary-meta">Run: ${runDate}</div>
                <div class="signal-summary-counts">
                    <div class="signal-count-card buy-card">
                        <div class="sc-number">${n_buy}</div>
                        <div class="sc-label">BUY</div>
                    </div>
                    <div class="signal-count-card hold-card">
                        <div class="sc-number">${n_hold}</div>
                        <div class="sc-label">HOLD</div>
                    </div>
                    <div class="signal-count-card sell-card">
                        <div class="sc-number">${n_sell}</div>
                        <div class="sc-label">SELL</div>
                    </div>
                </div>
            `;
        }

        // ── Actions list ───────────────────────────────
        const listEl = document.getElementById('notifications-list');
        if (actions.length === 0) {
            listEl.innerHTML = '<div class="notif-empty">No BUY or SELL actions in the last bot run — all positions held.</div>';
            return;
        }

        listEl.innerHTML = actions.map(item => {
            const isBuy = item.type === 'BUY';
            return `
                <div class="notif-item notif-${item.type.toLowerCase()}">
                    <div class="notif-icon">${isBuy ? '🟢' : '🔴'}</div>
                    <div class="notif-body">
                        <span class="notif-action">${item.type}</span>
                        <strong>${item.asset}</strong>
                        <span class="notif-meta">@ ${formatCurrency(item.price)} · confidence ${item.confidence}</span>
                    </div>
                    <div class="notif-date">${item.date}</div>
                </div>
            `;
        }).join('');

    } catch (error) {
        console.error('Error loading notifications:', error);
    }
}

document.addEventListener('DOMContentLoaded', loadNotifications);
