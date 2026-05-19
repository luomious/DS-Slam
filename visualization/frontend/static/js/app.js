import { SlamWebSocket } from './websocket.js';
import { ThreeRenderer } from './renderer.js';

class SlamVisualizer {
    constructor() {
        this._setStatus('Initializing...');
        
        try {
            this.renderer3D = new ThreeRenderer('scene-content');
            if (!this.renderer3D.enabled) {
                this._setStatus('ERROR: ThreeRenderer failed');
                return;
            }
        } catch(e) {
            this._setStatus('ERROR: ThreeRenderer: ' + e.message);
            throw e;
        }

        this.ws = null;
        this.frameCount = 0;
        this.keyframeCount = 0;
        this.mapPointCount = 0;
        this.lastFrameTime = performance.now();
        this.fps = 0;
        this.frameInterval = 1000;
        this.lastRenderTime = 0;
        this.minRenderInterval = 33;
        this.pendingFrame = null;
        this.pendingMapPoints = null;
        this.canvasSizes = {};
        this.rgbImg = new Image();
        this.yoloImg = new Image();
        this._wsConnected = false;
        this._dataLoaded = { trajectory: false, mapPoints: false, pointcloud: false };
        this._initTime = performance.now();

        this._setStatus('Connecting WebSocket...');
        this.initWebSocket();
        this._setStatus('Loading static data...');
        this.loadStaticData();
        this.startFPSCounter();
        this.startRenderLoop();
        
        this._setStatus('Ready');
    }

    _setStatus(msg) {
        const el = document.getElementById('init-status');
        if (el) el.textContent = msg;
    }

    initWebSocket() {
        const wsUrl = 'ws://' + location.host + '/ws/slam';
        this.ws = new SlamWebSocket(wsUrl, (data) => this.handleMessage(data));
        this.ws.connect();
    }

    startFPSCounter() {
        setInterval(() => {
            const now = performance.now();
            const elapsed = now - this.lastFrameTime;
            if (elapsed > 0) {
                this.fps = Math.round(this.frameCount * 1000 / elapsed);
            }
            const fpsEl = document.getElementById('fps-value');
            if (fpsEl) fpsEl.textContent = this.fps;
            this.frameCount = 0;
            this.lastFrameTime = now;
        }, this.frameInterval);
    }

    startRenderLoop() {
        const loop = () => {
            if (this.pendingFrame) {
                this._renderFrame(this.pendingFrame);
                this.pendingFrame = null;
            }
            if (this.pendingMapPoints) {
                this._renderMapPoints(this.pendingMapPoints);
                this.pendingMapPoints = null;
            }
            requestAnimationFrame(loop);
        };
        requestAnimationFrame(loop);
    }

    async loadStaticData() {
        // Load trajectory
        try {
            const resp = await fetch('/api/trajectory');
            if (resp.ok) {
                const data = await resp.json();
                const poseCount = data.poses ? data.poses.length : 0;
                this._setStatus('Trajectory: ' + poseCount + ' poses');
                if (poseCount > 0 && this.renderer3D && this.renderer3D.enabled) {
                    this.renderer3D.addTrajectory(data.poses);
                    this.keyframeCount = poseCount;
                    this.updateUI();
                    this.hidePlaceholder('scene-content');
                    this._dataLoaded.trajectory = true;
                }
            } else {
                this._setStatus('Trajectory: HTTP ' + resp.status);
            }
        } catch (e) {
            this._setStatus('Trajectory FAILED: ' + e.message);
        }

        // Load map points
        try {
            const resp = await fetch('/api/map_points');
            if (resp.ok) {
                const data = await resp.json();
                if (data.coords && data.coords.length >= 3 && data.point_count > 0 && this.renderer3D && this.renderer3D.enabled) {
                    this.renderer3D.updateMapPoints(data.coords);
                    this.hidePlaceholder('scene-content');
                    this.mapPointCount = data.point_count;
                    this.updateUI();
                    this._dataLoaded.mapPoints = true;
                }
            }
        } catch (e) { /* ignore */ }

        // Load point cloud (optional)
        try {
            const resp = await fetch('/api/pointcloud');
            if (resp.ok) {
                const meta = await resp.json();
                if (meta.vertex_count > 0) {
                    const points = await this.fetchPLYPoints();
                    if (points.length > 0 && this.renderer3D && this.renderer3D.enabled) {
                        this.renderer3D.addPointCloud(points);
                        this.hidePlaceholder('scene-content');
                        this._dataLoaded.pointcloud = true;
                    }
                }
            }
        } catch (e) { /* ignore */ }

        // Load grid map (optional)
        try {
            const resp = await fetch('/api/gridmap');
            if (resp.ok) {
                const blob = await resp.blob();
                if (blob.size > 0) {
                    const url = URL.createObjectURL(blob);
                    const canvas = document.getElementById('grid-canvas');
                    const container = document.querySelector('.grid-panel .image-container');
                    if (canvas && container) {
                        const ctx = canvas.getContext('2d');
                        const img = new Image();
                        img.onload = () => {
                            const dims = this._getCanvasDims(canvas, container);
                            canvas.width = dims.w;
                            canvas.height = dims.h;
                            ctx.imageSmoothingEnabled = false;
                            ctx.drawImage(img, 0, 0, dims.w, dims.h);
                            this.hidePlaceholder('grid-panel');
                        };
                        img.src = url;
                    }
                }
            }
        } catch (e) { /* ignore */ }

        this._updateProgressBar();
    }

    _updateProgressBar() {
        const bar = document.getElementById('progress-bar');
        const text = document.getElementById('progress-text');
        if (!bar || !text) return;

        const wsOk = this._wsConnected;
        const trajOk = this._dataLoaded.trajectory;
        const ptsOk = this._dataLoaded.mapPoints;
        const liveOk = this.frameCount > 0;

        let steps = 0;
        let total = 4;
        if (wsOk) steps++;
        if (trajOk) steps++;
        if (ptsOk) steps++;
        if (liveOk) steps++;

        const pct = Math.round(steps / total * 100);
        bar.style.width = pct + '%';
        bar.style.backgroundColor = pct >= 100 ? '#3fb950' : pct >= 50 ? '#d29922' : '#f85149';
        
        const labels = [];
        if (wsOk) labels.push('WS'); else labels.push('WS...');
        if (trajOk) labels.push('Traj'); else labels.push('Traj...');
        if (ptsOk) labels.push('Pts'); else labels.push('Pts...');
        if (liveOk) labels.push('Live'); else labels.push('Live...');
        text.textContent = labels.join(' | ') + ' ' + pct + '%';
    }

    async fetchPLYPoints() {
        try {
            const resp = await fetch('/api/plypoints');
            if (!resp.ok) return [];
            return await resp.json();
        } catch (e) { return []; }
    }

    _getCanvasDims(canvas, container) {
        const key = container.className || container.id || 'default';
        if (!this.canvasSizes[key] || Date.now() - this.canvasSizes[key].lastUpdate > 5000) {
            this.canvasSizes[key] = { w: container.clientWidth, h: container.clientHeight, lastUpdate: Date.now() };
        }
        return this.canvasSizes[key];
    }

    hidePlaceholder(panelId) {
        const panel = document.getElementById(panelId) || document.querySelector('.' + panelId);
        if (panel) {
            const ph = panel.querySelector('.placeholder');
            if (ph) ph.classList.add('hidden');
        }
    }

    handleMessage(data) {
        if (data.type === 'pong') return;
        if (data.type === 'frame_update') {
            this.pendingFrame = data;
        } else if (data.type === 'map_points_update') {
            this.pendingMapPoints = data;
        }
    }

    _renderFrame(data) {
        this.frameCount++;
        if (data.frame_number !== undefined) this.frameCount = data.frame_number;
        if (data.keyframe_count !== undefined) this.keyframeCount = data.keyframe_count;
        if (data.map_points !== undefined) this.mapPointCount = data.map_points;
        this.updateUI();

        if (data.pose && this.renderer3D && this.renderer3D.enabled) {
            this.renderer3D.updateCameraPose(data.pose);
            this.hidePlaceholder('scene-content');
        }

        if (data.image_base64) {
            this._drawImage(this.rgbImg, 'rgb-canvas', 'rgb-panel',
                data.image_base64, 'jpeg', data.features, (img) => {
                    this.hidePlaceholder('rgb-panel');
                    const infoEl = document.getElementById('rgb-info');
                    if (infoEl) infoEl.textContent = img.width + 'x' + img.height;
                    const featEl = document.getElementById('feature-count');
                    if (featEl) featEl.textContent = data.features ? data.features.length + ' features' : '0 features';
                });
        }

        if (data.mask_base64) {
            this._drawImage(this.yoloImg, 'yolo-canvas', 'yolo-panel',
                data.mask_base64, 'png', null, (img) => {
                    this.hidePlaceholder('yolo-panel');
                });
        }

        this._updateProgressBar();
    }

    _renderMapPoints(data) {
        if (data.map_points_coords && this.renderer3D && this.renderer3D.enabled) {
            this.renderer3D.updateMapPoints(data.map_points_coords);
            this.hidePlaceholder('scene-content');
            const infoEl = document.getElementById('pointcloud-info');
            if (infoEl && data.map_points_count) {
                infoEl.textContent = data.map_points_count.toLocaleString() + ' points';
            }
        }
    }

    _drawImage(imgEl, canvasId, panelClass, base64, format, features, onDrawn) {
        const canvas = document.getElementById(canvasId);
        const container = document.querySelector('.' + panelClass + ' .image-container');
        if (!canvas || !container) return;

        const ctx = canvas.getContext('2d');
        const dims = this._getCanvasDims(canvas, container);

        if (canvas.width !== dims.w || canvas.height !== dims.h) {
            canvas.width = dims.w;
            canvas.height = dims.h;
        }

        imgEl.onload = () => {
            const scale = Math.min(dims.w / imgEl.width, dims.h / imgEl.height);
            const tw = Math.floor(imgEl.width * scale);
            const th = Math.floor(imgEl.height * scale);
            ctx.clearRect(0, 0, dims.w, dims.h);
            const ox = Math.floor((dims.w - tw) / 2);
            const oy = Math.floor((dims.h - th) / 2);
            ctx.drawImage(imgEl, ox, oy, tw, th);

            if (features && features.length > 0) {
                ctx.fillStyle = '#58a6ff';
                for (const f of features) {
                    ctx.beginPath();
                    ctx.arc(ox + f.x * scale, oy + f.y * scale, 2, 0, Math.PI * 2);
                    ctx.fill();
                }
            }
            if (onDrawn) onDrawn(imgEl);
        };
        imgEl.src = 'data:image/' + format + ';base64,' + base64;
    }

    updateUI() {
        const fnEl = document.getElementById('frame-num');
        if (fnEl) fnEl.textContent = this.frameCount;
        const kfEl = document.getElementById('kf-num');
        if (kfEl) kfEl.textContent = this.keyframeCount;
        const mpEl = document.getElementById('map-pts');
        if (mpEl) mpEl.textContent = this.mapPointCount.toLocaleString();

        const statusEl = document.getElementById('slam-status');
        if (statusEl) {
            if (this.frameCount > 0) {
                statusEl.innerHTML = '<span class="status-dot"></span><span>TRACKING</span>';
                statusEl.className = 'status-badge tracking';
            } else if (this.keyframeCount > 0) {
                statusEl.innerHTML = '<span class="status-dot"></span><span>STATIC</span>';
                statusEl.className = 'status-badge online';
            }
        }
    }
}

window.addEventListener('load', () => {
    try {
        window.visualizer = new SlamVisualizer();
    } catch(e) {
        var errDiv = document.createElement('div');
        errDiv.style.cssText = 'color:red;padding:20px;font-family:monospace;position:fixed;top:0;left:0;right:0;background:black;z-index:99999;font-size:14px';
        errDiv.textContent = 'DS-SLAM Init Error: ' + (e.stack || e.message);
        document.body.appendChild(errDiv);
    }
});

window.addEventListener('resize', () => {
    if (window.visualizer) {
        window.visualizer.canvasSizes = {};
        if (window.visualizer.renderer3D) {
            window.visualizer.renderer3D.resize();
        }
    }
});
