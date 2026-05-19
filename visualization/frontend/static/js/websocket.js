export class SlamWebSocket {
    constructor(url, onMessage) {
        this.url = url;
        this.onMessage = onMessage;
        this.ws = null;
        this.reconnectInterval = 3000;
        this.connected = false;
        this._onConnect = null;
        this._onDisconnect = null;
    }

    connect() {
        try {
            this.ws = new WebSocket(this.url);
        } catch(e) {
            console.error('[WS] Constructor failed:', e);
            return;
        }

        this.ws.onopen = () => {
            this.connected = true;
            this.onStatusChange(true);
            // Notify visualizer
            if (window.visualizer) {
                window.visualizer._wsConnected = true;
                window.visualizer._updateProgressBar();
            }
            console.log('[WS] Connected to', this.url);
        };

        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.onMessage(data);
            } catch (e) {
                console.warn('[WS] Parse error:', e);
            }
        };

        this.ws.onclose = () => {
            this.connected = false;
            this.onStatusChange(false);
            if (window.visualizer) {
                window.visualizer._wsConnected = false;
                window.visualizer._updateProgressBar();
            }
            console.log('[WS] Disconnected, reconnecting in', this.reconnectInterval, 'ms');
            setTimeout(() => this.connect(), this.reconnectInterval);
        };

        this.ws.onerror = (error) => {
            console.error('[WS] Error:', error);
            this.ws.close();
        };

        this.startPing();
    }

    startPing() {
        setInterval(() => {
            if (this.connected && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({ type: 'ping' }));
            }
        }, 30000);
    }

    onStatusChange(connected) {
        const indicator = document.getElementById('ws-indicator');
        const dot = document.getElementById('ws-dot');
        const text = document.getElementById('ws-text');
        
        if (indicator) {
            indicator.className = 'ws-indicator ' + (connected ? 'connected' : '');
        }
        if (dot) {
            dot.className = 'ws-dot ' + (connected ? 'connected' : '');
        }
        if (text) {
            text.textContent = connected ? 'Connected' : 'Disconnected';
        }
    }

    send(data) {
        if (this.connected && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        }
    }
}
