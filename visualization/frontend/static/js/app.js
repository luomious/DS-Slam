import { SlamWebSocket } from './websocket.js';
import { ThreeRenderer } from './renderer.js';

class SlamVisualizer {
    constructor() {
        this.renderer3D = new ThreeRenderer('scene-content');
        this.ws = null;
        this.frameCount = 0;
        this.keyframeCount = 0;
        this.mapPointCount = 0;
        this.lastFrameTime = performance.now();
        this.fps = 0;
        this.frameInterval = 1000;

        this.initWebSocket();
        this.loadStaticData();
        this.startFPSCounter();
    }

    initWebSocket() {
        const wsUrl = `ws://${location.host}/ws/slam`;
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
            document.getElementById('fps-value').textContent = this.fps;
            this.frameCount = 0;
            this.lastFrameTime = now;
        }, this.frameInterval);
    }

    async loadStaticData() {
        setTimeout(() => {
            this.loadTrajectory().catch(console.warn);
            this.loadPointCloud().catch(console.warn);
            this.loadGridMap().catch(console.warn);
        }, 500);
    }

    async loadTrajectory() {
        try {
            const resp = await fetch('/api/trajectory');
            if (resp.ok) {
                const data = await resp.json();
                if (data.poses && data.poses.length > 0) {
                    this.renderer3D.addTrajectory(data.poses);
                    this.keyframeCount = data.poses.length;
                    this.updateUI();
                    this.hidePlaceholder('scene-content');
                }
            }
        } catch (e) {
            console.warn('Trajectory load failed:', e);
        }
    }

    async loadPointCloud() {
        try {
            const resp = await fetch('/api/pointcloud');
            if (resp.ok) {
                const meta = await resp.json();
                this.mapPointCount = meta.vertex_count || 0;
                this.updateUI();
                document.getElementById('pointcloud-info').textContent = 
                    `${(meta.vertex_count / 10000).toFixed(1)}万点`;

                if (meta.vertex_count > 0) {
                    const points = await this.fetchPLYPoints();
                    if (points.length > 0) {
                        this.renderer3D.addPointCloud(points);
                        this.hidePlaceholder('scene-content');
                    }
                }
            }
        } catch (e) {
            console.warn('Point cloud load failed:', e);
        }
    }

    async fetchPLYPoints() {
        try {
            const resp = await fetch('/api/plypoints');
            if (!resp.ok) return [];
            return await resp.json();
        } catch (e) {
            return [];
        }
    }

    async loadGridMap() {
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
                            const maxWidth = container.clientWidth;
                            const maxHeight = container.clientHeight;
                            
                            const scale = Math.min(maxWidth / img.width, maxHeight / img.height);
                            const targetWidth = Math.floor(img.width * scale);
                            const targetHeight = Math.floor(img.height * scale);
                            
                            canvas.width = targetWidth;
                            canvas.height = targetHeight;
                            
                            ctx.imageSmoothingEnabled = false;
                            ctx.drawImage(img, 0, 0, targetWidth, targetHeight);
                            
                            this.hidePlaceholder('grid-panel');
                            document.getElementById('grid-size').textContent = 
                                `${img.width}×${img.height}`;
                        };
                        
                        img.src = url;
                    }
                }
            }
        } catch (e) {
            console.warn('Grid map load failed:', e);
        }
    }

    hidePlaceholder(panelId) {
        const panel = document.getElementById(panelId) || document.querySelector(`.${panelId}`);
        if (panel) {
            const placeholder = panel.querySelector('.placeholder');
            if (placeholder) {
                placeholder.classList.add('hidden');
            }
        }
    }

    handleMessage(data) {
        if (data.type === 'pong') return;

        if (data.type === 'frame_update') {
            this.updateFrame(data);
        }
    }

    updateFrame(data) {
        this.frameCount++;

        if (data.frame_number !== undefined) {
            this.frameCount = data.frame_number;
        }
        if (data.keyframe_count !== undefined) {
            this.keyframeCount = data.keyframe_count;
        }
        if (data.map_points !== undefined) {
            this.mapPointCount = data.map_points;
        }

        this.updateUI();

        if (data.image_base64) {
            this.drawRGBCanvas(data.image_base64, data.features);
        }

        if (data.mask_base64) {
            this.drawYOLOCanvas(data.mask_base64, data.dynamic_coverage);
        }
    }

    drawRGBCanvas(base64, features) {
        const canvas = document.getElementById('rgb-canvas');
        const container = document.querySelector('.rgb-panel .image-container');
        
        if (!canvas || !container) return;

        const ctx = canvas.getContext('2d');
        const img = new Image();
        
        img.onload = () => {
            const maxWidth = container.clientWidth;
            const maxHeight = container.clientHeight;
            
            const scale = Math.min(maxWidth / img.width, maxHeight / img.height);
            const targetWidth = Math.floor(img.width * scale);
            const targetHeight = Math.floor(img.height * scale);

            canvas.width = targetWidth;
            canvas.height = targetHeight;
            
            ctx.drawImage(img, 0, 0, targetWidth, targetHeight);

            if (features && features.length > 0) {
                ctx.fillStyle = '#58a6ff';
                const featureScale = scale;
                for (const f of features) {
                    ctx.beginPath();
                    ctx.arc(f.x * featureScale, f.y * featureScale, 3, 0, Math.PI * 2);
                    ctx.fill();
                }
            }

            this.hidePlaceholder('rgb-panel');
            document.getElementById('rgb-info').textContent = `${img.width}×${img.height}`;
            document.getElementById('feature-count').textContent = features ? `${features.length} features` : '0 features';
        };
        
        img.src = `data:image/jpeg;base64,${base64}`;
    }

    drawYOLOCanvas(base64, coverage) {
        const canvas = document.getElementById('yolo-canvas');
        const container = document.querySelector('.yolo-panel .image-container');
        
        if (!canvas || !container) return;

        const ctx = canvas.getContext('2d');
        const img = new Image();
        
        img.onload = () => {
            const maxWidth = container.clientWidth;
            const maxHeight = container.clientHeight;
            
            const scale = Math.min(maxWidth / img.width, maxHeight / img.height);
            const targetWidth = Math.floor(img.width * scale);
            const targetHeight = Math.floor(img.height * scale);

            canvas.width = targetWidth;
            canvas.height = targetHeight;
            
            ctx.drawImage(img, 0, 0, targetWidth, targetHeight);

            ctx.fillStyle = 'rgba(248, 81, 73, 0.3)';
            ctx.fillRect(0, 0, targetWidth, targetHeight);

            this.hidePlaceholder('yolo-panel');
            document.getElementById('yolo-class').textContent = 'Class: person';
            document.getElementById('yolo-coverage').textContent = `Coverage: ${coverage || 0}%`;
        };
        
        img.src = `data:image/png;base64,${base64}`;
    }

    updateUI() {
        document.getElementById('frame-num').textContent = this.frameCount;
        document.getElementById('kf-num').textContent = this.keyframeCount;
        document.getElementById('map-pts').textContent = this.mapPointCount.toLocaleString();

        const statusEl = document.getElementById('slam-status');
        if (this.frameCount > 0) {
            statusEl.textContent = 'TRACKING';
            statusEl.className = 'status-badge tracking';
        } else if (this.keyframeCount > 0) {
            statusEl.textContent = 'STATIC';
            statusEl.className = 'status-badge online';
        } else {
            statusEl.textContent = 'INIT';
            statusEl.className = 'status-badge';
        }
    }
}

window.addEventListener('load', () => {
    console.log('[DS-SLAM] Initializing visualizer...');
    window.visualizer = new SlamVisualizer();
    console.log('[DS-SLAM] Visualizer initialized');
});

window.addEventListener('resize', () => {
    if (window.visualizer && window.visualizer.renderer3D) {
        window.visualizer.renderer3D.resize();
    }
});