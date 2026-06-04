// DS-SLAM Visualizer - Non-module loader with dynamic Three.js import
// This file is loaded as a regular script, not ES module, to avoid importmap failures

(function() {
    'use strict';
    
    const PROGRESS_BAR = document.getElementById('progress-bar');
    const PROGRESS_TEXT = document.getElementById('progress-text');
    const INIT_STATUS = document.getElementById('init-status');
    
    function setProgress(pct, text) {
        if (PROGRESS_BAR) {
            PROGRESS_BAR.style.width = pct + '%';
            PROGRESS_BAR.style.backgroundColor = pct >= 100 ? '#3fb950' : pct >= 50 ? '#d29922' : '#f85149';
        }
        if (PROGRESS_TEXT) PROGRESS_TEXT.textContent = text;
    }
    
    function setStatus(msg) {
        if (INIT_STATUS) INIT_STATUS.textContent = msg;
    }
    
    // ===== WebSocket =====
    class SlamWS {
        constructor(url) {
            this.url = url;
            this.ws = null;
            this.onMessage = null;
            this.connected = false;
            this._pingInterval = null;
            this._pongTimeout = null;
            this._reconnectTimeout = null;
            this._reconnectAttempts = 0;
        }
        
        connect() {
            // Cleanup previous connection
            this._cleanup();
            
            try {
                this.ws = new WebSocket(this.url);
            } catch(e) {
                console.error('[WS] Constructor failed:', e);
                this._scheduleReconnect();
                return;
            }
            this.ws.onopen = () => {
                this.connected = true;
                this._reconnectAttempts = 0;
                this._updateIndicator(true);
                setProgress(25, 'WS | Traj... | Pts... | Live... 25%');
                setStatus('WebSocket connected');
                console.log('[WS] Connected');
                // Start ping every 15 seconds
                this._pingInterval = setInterval(() => {
                    if (this.connected && this.ws.readyState === WebSocket.OPEN) {
                        this.ws.send(JSON.stringify({type:'ping'}));
                        // Set pong timeout (5 seconds)
                        this._pongTimeout = setTimeout(() => {
                            console.warn('[WS] Pong timeout, reconnecting...');
                            this.ws.close();
                        }, 5000);
                    }
                }, 15000);
            };
            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    // Handle server ping/pong
                    if (data.type === 'server_ping') {
                        this.ws.send(JSON.stringify({type:'pong'}));
                        return;
                    }
                    if (data.type === 'pong') {
                        // Clear pong timeout
                        if (this._pongTimeout) {
                            clearTimeout(this._pongTimeout);
                            this._pongTimeout = null;
                        }
                        return;
                    }
                    if (data.type === 'keepalive') {
                        return;
                    }
                    if (this.onMessage) this.onMessage(data);
                } catch(e) {}
            };
            this.ws.onclose = (event) => {
                console.log('[WS] Closed:', event.code, event.reason);
                this.connected = false;
                this._updateIndicator(false);
                this._cleanup();
                this._scheduleReconnect();
            };
            this.ws.onerror = (event) => {
                console.error('[WS] Error:', event);
                this.ws.close();
            };
        }
        
        _cleanup() {
            if (this._pingInterval) {
                clearInterval(this._pingInterval);
                this._pingInterval = null;
            }
            if (this._pongTimeout) {
                clearTimeout(this._pongTimeout);
                this._pongTimeout = null;
            }
            if (this._reconnectTimeout) {
                clearTimeout(this._reconnectTimeout);
                this._reconnectTimeout = null;
            }
        }
        
        _scheduleReconnect() {
            if (this._reconnectTimeout) return;
            // Exponential backoff: 1s, 2s, 4s, 8s, max 10s
            const delay = Math.min(1000 * Math.pow(2, this._reconnectAttempts), 10000);
            this._reconnectAttempts++;
            console.log(`[WS] Reconnecting in ${delay}ms (attempt ${this._reconnectAttempts})`);
            this._reconnectTimeout = setTimeout(() => {
                this._reconnectTimeout = null;
                this.connect();
            }, delay);
        }
        
        _updateIndicator(connected) {
            const dot = document.getElementById('ws-dot');
            const text = document.getElementById('ws-text');
            if (dot) dot.className = 'ws-dot ' + (connected ? 'connected' : '');
            if (text) text.textContent = connected ? 'Connected' : 'Disconnected';
        }
    }
    
    // ===== State =====
    let frameCount = 0, keyframeCount = 0, mapPointCount = 0;
    let lastFrameTime = performance.now(), fps = 0;
    let pendingFrame = null, pendingMapPoints = null;
    let threeRenderer = null;
    let ws = null;
    let rgbImg = new Image();
    let yoloImg = new Image();
    let canvasSizes = {};
    let dataLoaded = { trajectory: false, mapPoints: false, live: false };
    
    // ===== Init =====
    setStatus('Starting...');
    setProgress(0, 'WS... | Traj... | Pts... | Live... 0%');
    
    // 1. Connect WebSocket
    ws = new SlamWS('ws://' + location.host + '/ws/slam');
    ws.onMessage = handleMessage;
    ws.connect();
    
    // 2. Try to load Three.js dynamically
    setStatus('Loading Three.js...');
    
    async function initThreeJS() {
        // Check if dynamic import is supported (needs script[type=module] or importmap)
        if (typeof window !== 'undefined' && !window.importShim && !document.querySelector('script[type="importmap"]')) {
            console.warn('[ThreeJS] No importmap found, trying anyway...');
        }
        for (let attempt = 1; attempt <= 3; attempt++) {
            try {
                console.log('[ThreeJS] Import attempt', attempt + '/3');
                const THREE = await import('three');
                console.log('[ThreeJS] THREE loaded:', typeof THREE);
                const { OrbitControls } = await import('three/addons/controls/OrbitControls.js');
                console.log('[ThreeJS] OrbitControls loaded:', typeof OrbitControls);
                
                // Check scene-content exists
                const sceneEl = document.getElementById('scene-content');
                if (!sceneEl) {
                    console.error('[ThreeJS] #scene-content not found!');
                    return false;
                }
                console.log('[ThreeJS] #scene-content found:', sceneEl.clientWidth + 'x' + sceneEl.clientHeight);
                
                threeRenderer = new ThreeRendererInline(THREE, OrbitControls, 'scene-content');
                if (!threeRenderer.enabled) {
                    console.error('[ThreeJS] Renderer not enabled after init');
                    continue;
                }
                console.log('[ThreeJS] OK, enabled=true');
                setStatus('Three.js loaded');
                return true;
            } catch(e) {
                console.error('[DS-LAM] Three.js import failed (attempt ' + attempt + '):', e.message || e);
                if (attempt < 3) await new Promise(r => setTimeout(r, 500 * attempt));
            }
        }
        console.error('[ThreeJS] FAILED after 3 attempts - 3D panel will be disabled');
        setStatus('3D disabled (Three.js unavailable)');
        return false;
    }    
    // ===== Three.js Renderer (inline, uses passed THREE/OrbitControls) =====
    class ThreeRendererInline {
        constructor(THREE, OrbitControls, containerId) {
            this.THREE = THREE;
            this.container = document.getElementById(containerId);
            if (!this.container) { this.enabled = false; return; }
            
            const w = this.container.clientWidth || 400;
            const h = this.container.clientHeight || 300;
            
            this.scene = new THREE.Scene();
            this.scene.background = new THREE.Color(0x0d1117);
            
            this.camera = new THREE.PerspectiveCamera(60, w/h, 0.01, 100);
            this.camera.position.set(1, 1, 1);
            
            this.renderer = new THREE.WebGLRenderer({ antialias: true });
            this.renderer.setSize(w, h);
            this.renderer.setPixelRatio(window.devicePixelRatio);
            this.renderer.domElement.style.position = 'absolute';
            this.renderer.domElement.style.top = '0';
            this.renderer.domElement.style.left = '0';
            this.renderer.domElement.style.width = '100%';
            this.renderer.domElement.style.height = '100%';
            this.renderer.domElement.style.zIndex = '0';
            this.container.appendChild(this.renderer.domElement);
            
            this.controls = new OrbitControls(this.camera, this.renderer.domElement);
            this.controls.enableDamping = true;
            this.controls.dampingFactor = 0.05;
            
            // Grid
            this.gridHelper = new THREE.GridHelper(10, 20, 0x30363d, 0x21262d);
            this.gridHelper.visible = false;
            this.scene.add(this.gridHelper);
            
            // Axes
            this.axesHelper = new THREE.AxesHelper(0.3);
            this.axesHelper.visible = false;
            this.scene.add(this.axesHelper);
            
            // Lights
            this.scene.add(new THREE.AmbientLight(0xffffff, 0.6));
            const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
            dirLight.position.set(5, 10, 7);
            this.scene.add(dirLight);
            
            // Trajectory line (yellow)
            const trajGeo = new THREE.BufferGeometry();
            const maxPts = 5000;
            this.trajPositions = new Float32Array(maxPts * 3);
            this.trajGeo = trajGeo.setAttribute('position', new THREE.BufferAttribute(this.trajPositions, 3));
            trajGeo.setDrawRange(0, 0);
            const trajMat = new THREE.LineBasicMaterial({ color: 0x00e5ff, linewidth: 2 });
            this.trajLine = new THREE.Line(trajGeo, trajMat);
            this.trajLine.visible = false;
            this.scene.add(this.trajLine);
            this.trajCount = 0;
            
            // Sparse map points (from ORB features)
            const ptGeo = new THREE.BufferGeometry();
            const maxMapPts = 20000;
            this.mapPositions = new Float32Array(maxMapPts * 3);
            this.mapColors = new Float32Array(maxMapPts * 3);
            ptGeo.setAttribute('position', new THREE.BufferAttribute(this.mapPositions, 3));
            ptGeo.setAttribute('color', new THREE.BufferAttribute(this.mapColors, 3));
            ptGeo.setDrawRange(0, 0);
            const ptMat = new THREE.PointsMaterial({ size: 0.03, vertexColors: true, sizeAttenuation: true });
            this.mapPoints = new THREE.Points(ptGeo, ptMat);
            this.scene.add(this.mapPoints);
            this.mapPtCount = 0;
            
            // Dense point cloud (from depth reconstruction)
            const denseGeo = new THREE.BufferGeometry();
            const maxDensePts = 100000;
            this.densePositions = new Float32Array(maxDensePts * 3);
            this.denseColors = new Float32Array(maxDensePts * 3);
            denseGeo.setAttribute('position', new THREE.BufferAttribute(this.densePositions, 3));
            denseGeo.setAttribute('color', new THREE.BufferAttribute(this.denseColors, 3));
            denseGeo.setDrawRange(0, 0);
            const denseMat = new THREE.PointsMaterial({ size: 0.04, vertexColors: true, sizeAttenuation: true, transparent: true, opacity: 0.88 });
            this.densePoints = new THREE.Points(denseGeo, denseMat);
            this.scene.add(this.densePoints);
            this.densePtCount = 0;
            
            // Camera marker
            const camGeo = new THREE.ConeGeometry(0.02, 0.06, 4);
            const camMat = new THREE.MeshBasicMaterial({ color: 0x00ff88 });
            this.cameraMarker = new THREE.Mesh(camGeo, camMat);
            this.scene.add(this.cameraMarker);
            
            this.enabled = true;
            
            // Auto-scale grid
            this._autoScaleGrid();
            
            // Animation loop
            const animate = () => {
                requestAnimationFrame(animate);
                this.controls.update();
                this.renderer.render(this.scene, this.camera);
            };
            animate();
        }
        
        _autoScaleGrid() {
            if (this.trajCount > 2) {
                let minX=Infinity, maxX=-Infinity, minY=Infinity, maxY=-Infinity, minZ=Infinity, maxZ=-Infinity;
                for (let i = 0; i < this.trajCount; i++) {
                    const x = this.trajPositions[i*3], y = this.trajPositions[i*3+1], z = this.trajPositions[i*3+2];
                    if (x < minX) minX = x; if (x > maxX) maxX = x;
                    if (y < minY) minY = y; if (y > maxY) maxY = y;
                    if (z < minZ) minZ = z; if (z > maxZ) maxZ = z;
                }
                const range = Math.max(maxX-minX, maxY-minY, maxZ-minZ, 0.5);
                const cx = (minX+maxX)/2, cy = (minY+maxY)/2, cz = (minZ+maxZ)/2;
                this.camera.position.set(cx + range*0.8, cy + range*1.2, cz + range*0.8);
                this.controls.target.set(cx, cy, cz);
            }
        }
        
        addTrajectory(poses) {
            if (!this.enabled) return;
            const THREE = this.THREE;
            for (const p of poses) {
                const tx = p.tx !== undefined ? p.tx : (p.position ? p.position[0] : 0);
                const ty = p.ty !== undefined ? p.ty : (p.position ? p.position[1] : 0);
                const tz = p.tz !== undefined ? p.tz : (p.position ? p.position[2] : 0);
                if (this.trajCount < this.trajPositions.length / 3) {
                    // Backend uses OpenCV camera coordinates: X-right, Y-down, Z-forward
                    // Three.js uses Y-up coordinate system: X-right, Y-up, Z-backward
                    // Convert: (x,y,z)_OpenCV -> (x,-y,-z)_Three.js
                    this.trajPositions[this.trajCount*3] = tx;      // x -> x
                    this.trajPositions[this.trajCount*3+1] = -ty;   // y -> -y (down -> up)
                    this.trajPositions[this.trajCount*3+2] = -tz;   // z -> -z (forward -> backward)
                    this.trajCount++;
                }
            }
            this.trajLine.geometry.setDrawRange(0, this.trajCount);
            this.trajLine.geometry.attributes.position.needsUpdate = true;
            this._autoScaleGrid();
            
            // Update camera marker to last trajectory point
            if (this.trajCount > 0 && this.cameraMarker) {
                const lastIdx = this.trajCount - 1;
                const cx = this.trajPositions[lastIdx*3];
                const cy = this.trajPositions[lastIdx*3+1];
                const cz = this.trajPositions[lastIdx*3+2];
                this.cameraMarker.position.set(cx, cy, cz);
                this.cameraMarker.lookAt(cx + 0.01, cy, cz);
            }
            
            // Hide placeholder
            const ph = this.container.querySelector('.placeholder');
            if (ph) ph.classList.add('hidden');
        }
        
        updateMapPoints(coords) {
            if (!this.enabled) return;
            const n = Math.floor(coords.length / 3);
            const maxN = Math.min(n, this.mapPositions.length / 3);
            for (let i = 0; i < maxN; i++) {
                // Backend uses OpenCV camera coordinates: X-right, Y-down, Z-forward
                // Three.js uses Y-up coordinate system: X-right, Y-up, Z-backward
                // Convert: (x,y,z)_OpenCV -> (x,-y,-z)_Three.js
                this.mapPositions[i*3] = coords[i*3];      // x -> x
                this.mapPositions[i*3+1] = -coords[i*3+1]; // y -> -y (down -> up)
                this.mapPositions[i*3+2] = -coords[i*3+2]; // z -> -z (forward -> backward)
                // Color: height-based (use -y as height in Three.js)
                const h = -coords[i*3+1]; // -Y is up in Three.js
                this.mapColors[i*3] = 0.3 + 0.7 * Math.max(0, Math.min(1, h/2));
                this.mapColors[i*3+1] = 0.8;
                this.mapColors[i*3+2] = 0.3 + 0.7 * Math.max(0, Math.min(1, 1-h/2));
            }
            this.mapPtCount = maxN;
            this.mapPoints.geometry.setDrawRange(0, maxN);
            this.mapPoints.geometry.attributes.position.needsUpdate = true;
            this.mapPoints.geometry.attributes.color.needsUpdate = true;
        }
        
        updateDensePoints(coords, colors) {
            if (!this.enabled) return;
            const n = Math.floor(coords.length / 3);
            const maxN = Math.min(n, this.densePositions.length / 3);
            const hasColors = colors && colors.length >= n;
            for (let i = 0; i < maxN; i++) {
                // Backend uses OpenCV camera coordinates: X-right, Y-down, Z-forward
                // Three.js uses Y-up coordinate system: X-right, Y-up, Z-backward
                // Convert: (x,y,z)_OpenCV -> (x,-y,-z)_Three.js
                this.densePositions[i*3] = coords[i*3];      // x -> x
                this.densePositions[i*3+1] = -coords[i*3+1]; // y -> -y (down -> up)
                this.densePositions[i*3+2] = -coords[i*3+2]; // z -> -z (forward -> backward)
                // Color: use RGB from dataset if available, fallback to height colormap
                if (hasColors) {
                    this.denseColors[i*3] = colors[i*3];
                    this.denseColors[i*3+1] = colors[i*3+1];
                    this.denseColors[i*3+2] = colors[i*3+2];
                } else {
                    const h = -coords[i*3+1]; // -Y is up in Three.js
                    const t = Math.max(0, Math.min(1, (h + 0.5) / 2.5));
                    this.denseColors[i*3] = 0.2 + 0.8 * t;
                    this.denseColors[i*3+1] = 0.3 + 0.5 * (1 - Math.abs(t - 0.5) * 2);
                    this.denseColors[i*3+2] = 0.2 + 0.8 * (1 - t);
                }
            }
            this.densePtCount = maxN;
            this.densePoints.geometry.setDrawRange(0, maxN);
            this.densePoints.geometry.attributes.position.needsUpdate = true;
            this.densePoints.geometry.attributes.color.needsUpdate = true;
            
            // Hide placeholder if points rendered & show scene controls
            if (maxN > 100) {
                const ph = this.container.querySelector('.placeholder');
                if (ph) ph.classList.add('hidden');
            }
        }
        
        updateCameraPose(pose) {
            if (!this.enabled) return;
            const THREE = this.THREE;
            let tx, ty, tz;
            if (pose.tx !== undefined) {
                tx = pose.tx; ty = pose.ty; tz = pose.tz;
            } else if (pose.position) {
                tx = pose.position[0]; ty = pose.position[1]; tz = pose.position[2];
            } else if (Array.isArray(pose)) {
                // 4x4 matrix
                tx = pose[3]; ty = pose[7]; tz = pose[11];
            } else return;
            
            // Backend uses OpenCV camera coordinates: X-right, Y-down, Z-forward
            // Three.js uses Y-up coordinate system: X-right, Y-up, Z-backward
            // Convert: (x,y,z)_OpenCV -> (x,-y,-z)_Three.js
            this.cameraMarker.position.set(tx, -ty, -tz); // x, -y, -z
            this.cameraMarker.lookAt(tx + 0.01, -ty, -tz);
            
            // Smooth follow
            this.controls.target.lerp(this.cameraMarker.position, 0.05);
        }
        
        resize() {
            if (!this.enabled || !this.container) return;
            const w = this.container.clientWidth || 400;
            const h = this.container.clientHeight || 300;
            this.camera.aspect = w/h;
            this.camera.updateProjectionMatrix();
            this.renderer.setSize(w, h);
        }
        
        clearTrajectory() {
            this.trajCount = 0;
            this.trajPositions.fill(0);
            this.trajLine.geometry.setDrawRange(0, 0);
            this.trajLine.geometry.attributes.position.needsUpdate = true;
            this.trajLine.visible = false;
        }
        
        clearMapPoints() {
            this.mapPtCount = 0;
            this.mapPositions.fill(0);
            this.mapColors.fill(0);
            this.mapPoints.geometry.setDrawRange(0, 0);
            this.mapPoints.geometry.attributes.position.needsUpdate = true;
            this.mapPoints.geometry.attributes.color.needsUpdate = true;
        }
        
        clearDensePoints() {
            this.densePtCount = 0;
            this.densePositions.fill(0);
            this.denseColors.fill(0);
            this.densePoints.geometry.setDrawRange(0, 0);
            this.densePoints.geometry.attributes.position.needsUpdate = true;
            this.densePoints.geometry.attributes.color.needsUpdate = true;
        }
    }
    
    // ===== Handle messages =====
    function handleMessage(data) {
        if (data.type === 'pong') return;
        if (data.type === 'frame_update') {
            pendingFrame = data;
        } else if (data.type === 'map_points_update') {
            pendingMapPoints = data;
        } else if (data.type === 'dense_points_update') {
            const n = data.coords ? Math.floor(data.coords.length / 3) : 0;
            console.log('[PointCloud] Received dense_points_update:', n, 'points, has_colors:', !!data.colors);
            if (data.coords && threeRenderer && threeRenderer.enabled) {
                threeRenderer.updateDensePoints(data.coords, data.colors);
                const infoEl = document.getElementById('pointcloud-info');
                if (infoEl && data.point_count) {
                    infoEl.textContent = data.point_count.toLocaleString() + ' dense points';
                }
            }
        } else if (data.type === 'trajectory_update') {
            const n = data.poses ? data.poses.length : 0;
            console.log('[Trajectory] Received trajectory_update:', n, 'poses');
            if (threeRenderer && threeRenderer.enabled) {
                threeRenderer.clearTrajectory();
                if (n > 0) {
                    threeRenderer.addTrajectory(data.poses);
                    keyframeCount = n;
                    dataLoaded.trajectory = true;
                    updateProgress();
                }
            }
            setStatus('Trajectory: ' + n + ' poses');
        } else if (data.type === 'scene_reset') {
            console.log('[Scene] Received scene_reset, clearing all data');
            if (threeRenderer && threeRenderer.enabled) {
                threeRenderer.clearTrajectory();
                threeRenderer.clearMapPoints();
                threeRenderer.clearDensePoints();
            }
            dataLoaded.trajectory = false;
            dataLoaded.mapPoints = false;
            keyframeCount = 0;
            mapPointCount = 0;
            updateProgress();
            setStatus('Scene cleared');
        } else if (data.type === 'gridmap_update' && data.image_base64) {
            const canvas = document.getElementById('grid-canvas');
            if (canvas) {
                const ctx = canvas.getContext('2d');
                const container = canvas.parentElement;
                const w = container.clientWidth || 320;
                const h = container.clientHeight || 240;
                canvas.width = w;
                canvas.height = h;
                const img = new Image();
                img.onload = () => {
                    ctx.clearRect(0, 0, w, h);
                    const scale = Math.min(w/img.width, h/img.height);
                    const tw = Math.floor(img.width*scale), th = Math.floor(img.height*scale);
                    const ox = Math.floor((w-tw)/2), oy = Math.floor((h-th)/2);
                    ctx.drawImage(img, ox, oy, tw, th);
                    const ph = container.querySelector('.placeholder');
                    if (ph) ph.classList.add('hidden');
                };
                img.src = 'data:image/png;base64,' + data.image_base64;
            }
        }
    }
    
    // ===== Render loop =====
    function renderLoop() {
        if (pendingFrame) {
            renderFrame(pendingFrame);
            pendingFrame = null;
        }
        if (pendingMapPoints) {
            renderMapPoints(pendingMapPoints);
            pendingMapPoints = null;
        }
        requestAnimationFrame(renderLoop);
    }
    requestAnimationFrame(renderLoop);
    
    function renderFrame(data) {
        frameCount++;
        if (data.frame_number !== undefined) frameCount = data.frame_number;
        if (data.keyframe_count !== undefined) keyframeCount = data.keyframe_count;
        if (data.map_points !== undefined) mapPointCount = data.map_points;
        updateUI();
        
        if (data.pose && threeRenderer && threeRenderer.enabled) {
            threeRenderer.updateCameraPose(data.pose);
        }
        
        if (data.image_base64) {
            drawImage(rgbImg, 'rgb-canvas', 'rgb-panel', data.image_base64, 'jpeg', data.features);
        }
        if (data.mask_base64) {
            drawImage(yoloImg, 'yolo-canvas', 'yolo-panel', data.mask_base64, 'png', null);
        } else if (data.image_base64) {
            // No mask → show original image on YOLO panel
            drawImage(yoloImg, 'yolo-canvas', 'yolo-panel', data.image_base64, 'jpeg', null);
        }
        
        if (!dataLoaded.live) {
            dataLoaded.live = true;
            updateProgress();
        }
    }
    
    function renderMapPoints(data) {
        if (data.map_points_coords && threeRenderer && threeRenderer.enabled) {
            threeRenderer.updateMapPoints(data.map_points_coords);
            const infoEl = document.getElementById('pointcloud-info');
            if (infoEl && data.map_points_count) {
                infoEl.textContent = data.map_points_count.toLocaleString() + ' points';
            }
        }
    }
    
    function drawImage(imgEl, canvasId, panelClass, base64, format, features) {
        const canvas = document.getElementById(canvasId);
        const container = document.querySelector('.' + panelClass + ' .image-container');
        if (!canvas || !container) return;
        const ctx = canvas.getContext('2d');
        const w = container.clientWidth || 320;
        const h = container.clientHeight || 240;
        if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
        imgEl.onload = () => {
            const scale = Math.min(w/imgEl.width, h/imgEl.height);
            const tw = Math.floor(imgEl.width*scale), th = Math.floor(imgEl.height*scale);
            ctx.clearRect(0,0,w,h);
            const ox = Math.floor((w-tw)/2), oy = Math.floor((h-th)/2);
            ctx.drawImage(imgEl, ox, oy, tw, th);
            if (features && features.length > 0) {
                ctx.fillStyle = '#58a6ff';
                for (const f of features) { ctx.beginPath(); ctx.arc(ox+f.x*scale, oy+f.y*scale, 2, 0, Math.PI*2); ctx.fill(); }
            }
            // Hide placeholder
            const panel = document.getElementById(panelClass) || document.querySelector('.' + panelClass);
            if (panel) { const ph = panel.querySelector('.placeholder'); if (ph) ph.classList.add('hidden'); }
            if (panelClass === 'rgb-panel') {
                const infoEl = document.getElementById('rgb-info');
                if (infoEl) infoEl.textContent = imgEl.width + 'x' + imgEl.height;
                const featEl = document.getElementById('feature-count');
                if (featEl) featEl.textContent = (features ? features.length : 0) + ' features';
            }
        };
        imgEl.src = 'data:image/' + format + ';base64,' + base64;
    }
    
    function updateUI() {
        const fnEl = document.getElementById('frame-num'); if (fnEl) fnEl.textContent = frameCount;
        const kfEl = document.getElementById('kf-num'); if (kfEl) kfEl.textContent = keyframeCount;
        const mpEl = document.getElementById('map-pts'); if (mpEl) mpEl.textContent = mapPointCount.toLocaleString();
        const statusEl = document.getElementById('slam-status');
        if (statusEl && frameCount > 0) {
            statusEl.innerHTML = '<span class="status-dot"></span><span>TRACKING</span>';
            statusEl.className = 'status-badge tracking';
        }
    }
    
    function updateProgress() {
        let steps = 0, total = 4;
        const wsOk = ws && ws.connected;
        const trajOk = dataLoaded.trajectory;
        const ptsOk = dataLoaded.mapPoints;
        const liveOk = dataLoaded.live;
        if (wsOk) steps++; if (trajOk) steps++; if (ptsOk) steps++; if (liveOk) steps++;
        const pct = Math.round(steps/total*100);
        const labels = [];
        labels.push(wsOk ? 'WS' : 'WS...');
        labels.push(trajOk ? 'Traj' : 'Traj...');
        labels.push(ptsOk ? 'Pts' : 'Pts...');
        labels.push(liveOk ? 'Live' : 'Live...');
        setProgress(pct, labels.join(' | ') + ' ' + pct + '%');
    }
    
    // FPS counter
    setInterval(() => {
        const now = performance.now();
        const elapsed = now - lastFrameTime;
        if (elapsed > 0) fps = Math.round(frameCount * 1000 / elapsed);
        const fpsEl = document.getElementById('fps-value');
        if (fpsEl) fpsEl.textContent = fps;
        frameCount = 0;
        lastFrameTime = now;
    }, 1000);
    
    // ===== Load static data =====
    async function loadStaticData() {
        // [FIX C] Fetch last frame for RGB/YOLO panels when SLAM not running
        try {
            console.log('[InitFrame] Fetching /api/latest_frame ...');
            const lfr = await fetch('/api/latest_frame');
            if (lfr.ok) {
                const lfd = await lfr.json();
                if (lfd.frame) {
                    console.log('[InitFrame] Got frame:', JSON.stringify(lfd.frame).substring(0, 100));
                    pendingFrame = lfd.frame;
                    // Will be picked up by renderLoop
                }
            } else {
                console.warn('[InitFrame] HTTP', lfr.status);
            }
        } catch(ef) { console.warn('[InitFrame] failed:', ef.message); }

        // Wait for Three.js to load
        let threeOk = false;
        try {
            threeOk = await initThreeJS();
        } catch(e) {
            console.error('[InitData] initThreeJS threw:', e);
        }
        setStatus(threeOk ? 'Three.js ready, loading data...' : 'No 3D, loading 2D...');
        
        // Trajectory
        try {
            const resp = await fetch('/api/trajectory');
            if (resp.ok) {
                const data = await resp.json();
                const n = data.poses ? data.poses.length : 0;
                setStatus('Trajectory: ' + n + ' poses');
                if (n > 0 && threeRenderer && threeRenderer.enabled) {
                    threeRenderer.addTrajectory(data.poses);
                    keyframeCount = n;
                    dataLoaded.trajectory = true;
                    updateProgress();
                }
            }
        } catch(e) { setStatus('Trajectory failed: ' + e.message); }
        
        // Map points
        try {
            const resp = await fetch('/api/map_points');
            if (resp.ok) {
                const data = await resp.json();
                if (data.coords && data.point_count > 0 && threeRenderer && threeRenderer.enabled) {
                    threeRenderer.updateMapPoints(data.coords);
                    mapPointCount = data.point_count;
                }
            }
        } catch(e) { console.warn('[MapPoints] load failed:', e); }
        
        // Dense point cloud
        try {
            console.log('[DensePoints] Fetching...');
            const resp = await fetch('/api/dense_points');
            console.log('[DensePoints] Response:', resp.status, resp.ok);
            if (resp.ok) {
                const data = await resp.json();
                console.log('[DensePoints] Data:', data.point_count, 'pts, threeRenderer=', !!threeRenderer, 'enabled=', threeRenderer?.enabled);
                if (data.coords && data.point_count > 0 && threeRenderer && threeRenderer.enabled) {
                    threeRenderer.updateDensePoints(data.coords, data.colors);
                    threeRenderer._autoScaleGrid();
                    console.log('[DensePoints] UPDATED', data.point_count, 'points, camera adjusted');
                    dataLoaded.mapPoints = true;
                    updateProgress();
                }
            }
        } catch(e) { console.warn('[DensePoints] load failed:', e); }
        
        // Grid map (2D occupancy grid from map points) - [FIXED v2]
        try {
            const resp = await fetch('/api/gridmap');
            if (resp.ok) {
                const ct = resp.headers.get('content-type') || '';
                const gridImg = new Image();
                gridImg.onerror = function(e) { console.error('[GridMap] Image ERROR', e); };
                // [FIX] Hide placeholder immediately
                const gpnl2 = document.querySelector('.grid-panel');
                if (gpnl2) { const gph2 = gpnl2.querySelector('.placeholder'); if (gph2) gph2.style.display = 'none'; }
                gridImg.onload = function() {
            var gc = document.getElementById('grid-canvas');
            if (gc) {
                // Force minimum canvas size
                if (gc.width < 10 || gc.height < 10) {
                    gc.width = Math.max(gc.parentElement.clientWidth || 320, 320);
                    gc.height = Math.max(gc.parentElement.clientHeight || 240, 240);
                    console.log('[Gridmap] Forced canvas size:', gc.width, 'x', gc.height);
                }
            }
                    console.log("[GridMap] loaded:", this.width, "x", this.height);
                    var canvas = document.getElementById("grid-canvas");
                    var container = document.querySelector(".grid-panel .image-container");
                    if (container) { container.style.display = "block"; container.style.minHeight = "200px"; }
                    var w = Math.max(container ? container.clientWidth : 0, 320);
                    var h = Math.max(container ? container.clientHeight : 0, 240);
                        console.log("[GridMap] canvas:", w, "x", h);
                        canvas.width = w; canvas.height = h;
                        const ctx = canvas.getContext('2d');
                        const scale = Math.min(w/gridImg.width, h/gridImg.height);
                        const tw = Math.floor(gridImg.width*scale), th = Math.floor(gridImg.height*scale);
                        ctx.clearRect(0,0,w,h);
                        const ox = Math.floor((w-tw)/2), oy = Math.floor((h-th)/2);
                        ctx.drawImage(gridImg, ox, oy, tw, th);
                        // Hide placeholder
                        const panel = document.querySelector('.grid-panel');
                        if (panel) { const ph = panel.querySelector('.placeholder'); if (ph) ph.classList.add('hidden'); }
                        const sizeEl = document.getElementById('grid-size');
                        if (sizeEl) sizeEl.textContent = gridImg.width + 'x' + gridImg.height;
                };
                console.log('[GridMap] Content-Type:', ct);
                if (ct.includes('application/json') || ct === '') {
                    const data = await resp.json();
                    console.log('[GridMap] JSON data keys:', Object.keys(data));
                    if (data.image_base64) {
                        console.log('[GridMap] Setting src from base64, len=', data.image_base64.length);
                        gridImg.src = 'data:image/png;base64,' + data.image_base64;
                    } else {
                        console.warn('[GridMap] No image_base64 in data');
                    }
                } else if (ct.includes('image/')) {
                    console.log('[GridMap] Getting blob...');
                    const blob = await resp.blob();
                    gridImg.src = URL.createObjectURL(blob);
                } else {
                    console.warn('[GridMap] Unknown content-type, trying JSON...');
                    try {
                        const data = await resp.json();
                        if (data.image_base64) gridImg.src = 'data:image/png;base64,' + data.image_base64;
                    } catch(e2) {
                        const blob = await resp.blob();
                        gridImg.src = URL.createObjectURL(blob);
                    }
                }
            }
        } catch(e) { console.warn('[GridMap] load failed:', e); }
        // [FIX] Ensure placeholder is hidden even before image loads
            const gpnl = document.querySelector('.grid-panel');
            if (gpnl) { const gph = gpnl.querySelector('.placeholder'); if (gph) gph.style.display = 'none'; }
        
        updateUI();
        setStatus('Ready');
    }
    
    loadStaticData();
    
    // Resize handler
    window.addEventListener('resize', () => {
        canvasSizes = {};
        if (threeRenderer) threeRenderer.resize();
    });
    

    // ===== Dataset Selector & Controls =====
    async function loadDatasets() {
        try {
            const resp = await fetch('/api/datasets');
            if (resp.ok) {
                const data = await resp.json();
                const sel = document.getElementById('dataset-select');
                if (!sel) return;
                sel.innerHTML = '';
                // Add camera option first
                const camOpt = document.createElement('option');
                camOpt.value = '__live_camera__';
                camOpt.textContent = '📷 实时摄像头';
                sel.appendChild(camOpt);
                for (const ds of data.datasets) {
                    const opt = document.createElement('option');
                    opt.value = ds.name;
                    opt.textContent = ds.name + (ds.ready ? ' ✓' : ' ✗');
                    opt.disabled = !ds.ready;
                    sel.appendChild(opt);
                }
                if (data.datasets.length === 0) {
                    // Camera option already added above
                } else {
                    // Default: select camera mode
                    sel.value = '__live_camera__';
                    console.log('[Dataset] Default mode: live camera');
                    sel.dispatchEvent(new Event('change'));
                }
            }
        } catch(e) { console.warn('[Datasets] load failed:', e); }
    }
    loadDatasets();
    
    // Dataset selection handler
    const datasetSelect = document.getElementById('dataset-select');
    if (datasetSelect) {
        datasetSelect.addEventListener('change', async function() {
            const selectedDataset = this.value;
            if (!selectedDataset) return;
            
            console.log('[Dataset] Switching to:', selectedDataset);
            const btn = document.getElementById('btn-load-test');
            if (btn) {
                btn.textContent = 'Loading...';
                btn.disabled = true;
            }
            
            // ====== Camera mode ======
            if (selectedDataset === '__live_camera__') {
                try {
                    // Stop any dataset playback first
                    await fetch('/api/playback/stop', {method: 'POST'});
                    const resp = await fetch('/api/camera/start', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({camera_index: 0, fps: 10})
                    });
                    const data = await resp.json();
                    console.log('[Camera] Started:', data);
                    if (btn) { btn.textContent = 'Camera Live'; btn.disabled = false; }
                    // Clear 3D scene for camera mode
                    if (threeRenderer && threeRenderer.enabled) {
                        threeRenderer.clearTrajectory();
                        threeRenderer.clearDensePoints();
                    }
                } catch(e) {
                    console.error('[Camera] Failed to start:', e);
                    if (btn) { btn.textContent = 'Camera Error'; setTimeout(() => { btn.textContent = 'Test Frame'; btn.disabled = false; }, 2000); }
                }
                return;
            }
            
            // ====== Dataset mode ======
            try {
                // Stop camera if running
                await fetch('/api/camera/stop', {method: 'POST'});
                const resp = await fetch('/api/select_dataset', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({dataset: selectedDataset, auto_playback: true, fps: 10})
                });
                
                if (resp.ok) {
                    const data = await resp.json();
                    console.log('[Dataset] Switched successfully:', data);
                    
                    // Also fetch 3D data via HTTP to ensure scene updates even if WS is not connected
                    console.log('[Dataset] Fetching 3D data via HTTP...');
                    
                    // Fetch trajectory
                    try {
                        const trajResp = await fetch('/api/trajectory');
                        if (trajResp.ok) {
                            const trajData = await trajResp.json();
                            console.log('[Dataset] Trajectory loaded:', trajData.poses ? trajData.poses.length : 0, 'poses');
                            if (threeRenderer && threeRenderer.enabled && trajData.poses && trajData.poses.length > 0) {
                                threeRenderer.clearTrajectory();
                                threeRenderer.addTrajectory(trajData.poses);
                                keyframeCount = trajData.poses.length;
                                dataLoaded.trajectory = true;
                                updateProgress();
                            }
                        }
                    } catch(e) { console.warn('[Dataset] Failed to fetch trajectory:', e); }
                    
                    // Fetch dense points
                    try {
                        const denseResp = await fetch('/api/dense_points');
                        if (denseResp.ok) {
                            const denseData = await denseResp.json();
                            const n = denseData.coords ? Math.floor(denseData.coords.length / 3) : 0;
                            console.log('[Dataset] Dense points loaded:', n, 'points');
                            if (threeRenderer && threeRenderer.enabled && denseData.coords && n > 0) {
                                threeRenderer.clearDensePoints();
                                threeRenderer.updateDensePoints(denseData.coords, denseData.colors);
                                const infoEl = document.getElementById('pointcloud-info');
                                if (infoEl) {
                                    infoEl.textContent = n.toLocaleString() + ' dense points';
                                }
                            } else if (threeRenderer && threeRenderer.enabled) {
                                threeRenderer.clearDensePoints();
                                const infoEl = document.getElementById('pointcloud-info');
                                if (infoEl) {
                                    infoEl.textContent = 'No dense points';
                                }
                            }
                        }
                    } catch(e) { console.warn('[Dataset] Failed to fetch dense points:', e); }
                    
                    // Fetch gridmap
                    try {
                        const gridResp = await fetch('/api/gridmap');
                        if (gridResp.ok) {
                            const gridData = await gridResp.json();
                            if (gridData.image_base64) {
                                console.log('[Dataset] Gridmap loaded');
                                const canvas = document.getElementById('grid-canvas');
                                if (canvas) {
                                    const ctx = canvas.getContext('2d');
                                    const container = canvas.parentElement;
                                    const w = container.clientWidth || 320;
                                    const h = container.clientHeight || 240;
                                    canvas.width = w;
                                    canvas.height = h;
                                    const img = new Image();
                                    img.onload = () => {
                                        ctx.clearRect(0, 0, w, h);
                                        const scale = Math.min(w/img.width, h/img.height);
                                        const tw = Math.floor(img.width*scale), th = Math.floor(img.height*scale);
                                        const ox = Math.floor((w-tw)/2), oy = Math.floor((h-th)/2);
                                        ctx.drawImage(img, ox, oy, tw, th);
                                    };
                                    img.src = 'data:image/png;base64,' + gridData.image_base64;
                                }
                            }
                        }
                    } catch(e) { console.warn('[Dataset] Failed to fetch gridmap:', e); }
                    
                    if (btn) {
                        btn.textContent = 'Test Frame';
                        btn.disabled = false;
                    }
                    // Reload test frame with new dataset
                    loadTestFrame();
                } else {
                    console.error('[Dataset] Switch failed:', resp.status);
                    if (btn) {
                        btn.textContent = 'Error!';
                        setTimeout(() => { btn.textContent = 'Test Frame'; btn.disabled = false; }, 2000);
                    }
                }
            } catch(e) {
                console.error('[Dataset] Switch error:', e);
                if (btn) {
                    btn.textContent = 'Error!';
                    setTimeout(() => { btn.textContent = 'Test Frame'; btn.disabled = false; }, 2000);
                }
            }
        });
    }
    
    window.loadTestFrame = async function loadTestFrame() {
        try {
            const btn = document.getElementById('btn-load-test');
            btn.textContent = 'Loading...';
            btn.disabled = true;
            const resp = await fetch('/api/push_test_frame', {method: 'POST'});
            const data = await resp.json();
            console.log('[TestFrame]', data);
            btn.textContent = 'Test Frame';
            btn.disabled = false;
            if (data.has_mask) {
                // Trigger renderLoop to pick up the new frame via snapshot
                const lfr = await fetch('/api/latest_frame');
                if (lfr.ok) {
                    const lfd = await lfr.json();
                    if (lfd.frame) pendingFrame = lfd.frame;
                }
            }
        } catch(e) {
            console.error('[TestFrame] failed:', e);
            const btn = document.getElementById('btn-load-test');
            btn.textContent = 'Error!';
            setTimeout(() => { btn.textContent = 'Test Frame'; btn.disabled = false; }, 2000);
        }
    }
    
    window.resetView = function resetView() {
        if (threeRenderer && threeRenderer.enabled) {
            threeRenderer._autoScaleGrid();
            console.log('[ResetView] Camera reset to fit data');
        }
    }
    
    window.skipPlaybackGenerate = async function skipPlaybackGenerate() {
        try {
            const btn = document.getElementById('btn-skip-playback');
            btn.textContent = '⏳ Generating...';
            btn.disabled = true;
            
            console.log('[SkipPlayback] Starting direct result generation...');
            
            // Stop any ongoing playback
            const stopResp = await fetch('/api/stop_playback', {method: 'POST'});
            console.log('[SkipPlayback] Stopped playback:', await stopResp.json());
            
            // Get current dataset
            const sel = document.getElementById('dataset-select');
            const currentDataset = sel ? sel.value : '';
            if (!currentDataset) {
                alert('Please select a dataset first!');
                btn.textContent = '⚡ Skip Playback';
                btn.disabled = false;
                return;
            }
            
            // Switch dataset without auto_playback to load all 3D data
            console.log('[SkipPlayback] Loading 3D data for:', currentDataset);
            const resp = await fetch('/api/select_dataset', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({dataset: currentDataset, auto_playback: false})
            });
            
            if (resp.ok) {
                const data = await resp.json();
                console.log('[SkipPlayback] Dataset loaded:', data);
                
                // Fetch trajectory
                const trajResp = await fetch('/api/trajectory');
                if (trajResp.ok) {
                    const trajData = await trajResp.json();
                    console.log('[SkipPlayback] Trajectory loaded:', trajData.poses ? trajData.poses.length : 0, 'poses');
                    if (threeRenderer && threeRenderer.enabled && trajData.poses && trajData.poses.length > 0) {
                        threeRenderer.clearTrajectory();
                        threeRenderer.addTrajectory(trajData.poses);
                        keyframeCount = trajData.poses.length;
                        dataLoaded.trajectory = true;
                    }
                }
                
                // Fetch dense points
                const denseResp = await fetch('/api/dense_points');
                if (denseResp.ok) {
                    const denseData = await denseResp.json();
                    const n = denseData.coords ? Math.floor(denseData.coords.length / 3) : 0;
                    console.log('[SkipPlayback] Dense points loaded:', n, 'points');
                    if (threeRenderer && threeRenderer.enabled && denseData.coords && n > 0) {
                        threeRenderer.updateDensePoints(denseData.coords, denseData.colors);
                        const infoEl = document.getElementById('pointcloud-info');
                        if (infoEl) {
                            infoEl.textContent = n.toLocaleString() + ' dense points';
                        }
                    }
                }
                
                // Fetch gridmap
                const gridResp = await fetch('/api/gridmap');
                if (gridResp.ok) {
                    const gridData = await gridResp.json();
                    if (gridData.image_base64) {
                        console.log('[SkipPlayback] Gridmap loaded');
                        const canvas = document.getElementById('grid-canvas');
                        if (canvas) {
                            const ctx = canvas.getContext('2d');
                            const container = canvas.parentElement;
                            const w = container.clientWidth || 320;
                            const h = container.clientHeight || 240;
                            canvas.width = w;
                            canvas.height = h;
                            const img = new Image();
                            img.onload = () => {
                                ctx.clearRect(0, 0, w, h);
                                const scale = Math.min(w/img.width, h/img.height);
                                const tw = Math.floor(img.width*scale), th = Math.floor(img.height*scale);
                                const ox = Math.floor((w-tw)/2), oy = Math.floor((h-th)/2);
                                ctx.drawImage(img, ox, oy, tw, th);
                            };
                            img.src = 'data:image/png;base64,' + gridData.image_base64;
                        }
                    }
                }
                
                // Load a test frame for RGB/YOLO panels
                const frameResp = await fetch('/api/push_test_frame', {method: 'POST'});
                if (frameResp.ok) {
                    const lfr = await fetch('/api/latest_frame');
                    if (lfr.ok) {
                        const lfd = await lfr.json();
                        if (lfd.frame) pendingFrame = lfd.frame;
                    }
                }
                
                console.log('[SkipPlayback] Result generation complete!');
                btn.textContent = '✅ Done!';
                setTimeout(() => { btn.textContent = '⚡ Skip Playback'; btn.disabled = false; }, 2000);
            } else {
                console.error('[SkipPlayback] Failed to load dataset');
                btn.textContent = ' Error!';
                setTimeout(() => { btn.textContent = '⚡ Skip Playback'; btn.disabled = false; }, 2000);
            }
        } catch(e) {
            console.error('[SkipPlayback] Error:', e);
            const btn = document.getElementById('btn-skip-playback');
            btn.textContent = '❌ Error!';
            setTimeout(() => { btn.textContent = ' Skip Playback'; btn.disabled = false; }, 2000);
        }
    }

    // ===== Scene Overlay Controls (inspired by 3D-point-cloud-visualizer) =====
    window.setScenePtSize = function(val) {
        // Slider 0.5-80 -> size 0.005-0.8 world units
        const size = val / 100;
        if (threeRenderer && threeRenderer.enabled) {
            if (threeRenderer.densePoints) {
                threeRenderer.densePoints.material.size = size;
                threeRenderer.densePoints.material.needsUpdate = true;
            }
            if (threeRenderer.mapPoints) {
                threeRenderer.mapPoints.material.size = size * 1.5;
                threeRenderer.mapPoints.material.needsUpdate = true;
            }
        }
        const el = document.getElementById('scene-pt-size-val');
        if (el) el.textContent = size.toFixed(3);
    };

    window.setSceneOpacity = function(val) {
        const opacity = parseFloat(val);
        if (threeRenderer && threeRenderer.enabled) {
            if (threeRenderer.densePoints) {
                threeRenderer.densePoints.material.opacity = opacity;
                threeRenderer.densePoints.material.transparent = opacity < 1;
                threeRenderer.densePoints.material.needsUpdate = true;
            }
            if (threeRenderer.mapPoints) {
                threeRenderer.mapPoints.material.opacity = opacity;
                threeRenderer.mapPoints.material.transparent = opacity < 1;
                threeRenderer.mapPoints.material.needsUpdate = true;
            }
        }
        const el = document.getElementById('scene-opacity-val');
        if (el) el.textContent = opacity.toFixed(2);
    };

    window.setSceneSizeAttenuation = function(enabled) {
        if (threeRenderer && threeRenderer.enabled) {
            if (threeRenderer.densePoints) {
                threeRenderer.densePoints.material.sizeAttenuation = enabled;
                threeRenderer.densePoints.material.needsUpdate = true;
            }
            if (threeRenderer.mapPoints) {
                threeRenderer.mapPoints.material.sizeAttenuation = enabled;
                threeRenderer.mapPoints.material.needsUpdate = true;
            }
        }
    };

    window.setSceneBg = function(theme) {
        if (threeRenderer && threeRenderer.enabled) {
            if (theme === 'dark') {
                threeRenderer.scene.background = new threeRenderer.THREE.Color(0x0d1117);
            } else {
                threeRenderer.scene.background = new threeRenderer.THREE.Color(0xf0f2f5);
            }
        }
    };

    // Scene interaction mode: 'nav' = orbit/pan, 'pick' = click to pick point
    let _sceneInteractionMode = 'nav';
    let _sceneRaycaster = null;
    let _sceneMouse = null;
    let _scenePickedMarker = null;

    window.setSceneMode = function(mode) {
        _sceneInteractionMode = mode;
        const navBtn = document.getElementById('mode-nav-btn');
        const pickBtn = document.getElementById('mode-pick-btn');
        const pickingPanel = document.getElementById('picking-info');
        const cont = threeRenderer ? threeRenderer.container : null;

        if (mode === 'pick') {
            if (navBtn) { navBtn.style.background = '#30363d'; navBtn.style.color = '#c9d1d9'; }
            if (pickBtn) { pickBtn.style.background = '#1f6feb'; pickBtn.style.color = '#fff'; }
            // Init raycaster if needed
            if (!_sceneRaycaster && threeRenderer && threeRenderer.THREE) {
                const THREE = threeRenderer.THREE;
                _sceneRaycaster = new THREE.Raycaster();
                _sceneMouse = new THREE.Vector2();
                _scenePickedMarker = new THREE.Points(
                    new THREE.BufferGeometry().setAttribute('position', new THREE.BufferAttribute(new Float32Array([0,0,0]), 3)),
                    new THREE.PointsMaterial({ color: 0xff4444, size: 0.05 })
                );
                threeRenderer.scene.add(_scenePickedMarker);
            }
            if (cont && !cont._scenePickListener) {
                cont._scenePickListener = true;
                cont.addEventListener('click', _onSceneClick);
            }
        } else {
            if (navBtn) { navBtn.style.background = '#1f6feb'; navBtn.style.color = '#fff'; }
            if (pickBtn) { pickBtn.style.background = '#30363d'; pickBtn.style.color = '#c9d1d9'; }
            if (pickingPanel) pickingPanel.style.display = 'none';
        }
    };

    function _onSceneClick(event) {
        if (_sceneInteractionMode !== 'pick' || !threeRenderer || !threeRenderer.enabled) return;
        const rect = threeRenderer.renderer.domElement.getBoundingClientRect();
        _sceneMouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        _sceneMouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
        _sceneRaycaster.setFromCamera(_sceneMouse, threeRenderer.camera);

        const objects = [];
        if (threeRenderer.densePoints && threeRenderer.densePtCount > 0) objects.push(threeRenderer.densePoints);
        if (threeRenderer.mapPoints && threeRenderer.mapPtCount > 0) objects.push(threeRenderer.mapPoints);

        _sceneRaycaster.params.Points.threshold = 0.1;
        const intersects = _sceneRaycaster.intersectObjects(objects, true);

        const pickingPanel = document.getElementById('picking-info');
        const pickingData = document.getElementById('picking-data');
        if (intersects.length > 0) {
            const i = intersects[0];
            const localPos = i.point;
            if (pickingPanel && pickingData) {
                let colorInfo = 'N/A';
                if (i.object.geometry && i.object.geometry.attributes.color) {
                    const c = i.object.geometry.attributes.color;
                    if (i.index !== undefined) {
                        const r = Math.floor(c.getX(i.index) * 255);
                        const g = Math.floor(c.getY(i.index) * 255);
                        const b = Math.floor(c.getZ(i.index) * 255);
                        colorInfo = 'RGB(' + r + ',' + g + ',' + b + ')';
                    }
                }
                pickingData.innerHTML =
                    'XYZ: ' + localPos.x.toFixed(3) + ', ' + localPos.y.toFixed(3) + ', ' + localPos.z.toFixed(3) + '<br>' +
                    'Color: ' + colorInfo;
                pickingPanel.style.display = 'block';
            }
            if (_scenePickedMarker) {
                _scenePickedMarker.position.copy(localPos);
            }
        } else {
            if (pickingPanel) pickingPanel.style.display = 'none';
        }
    }

    // Grid toggle
    window.setSceneGrid = function(visible) {
        if (threeRenderer && threeRenderer.enabled) {
            if (threeRenderer.gridHelper) threeRenderer.gridHelper.visible = visible;
            if (threeRenderer.axesHelper) threeRenderer.axesHelper.visible = visible;
        }
    };

    // Trajectory toggle
    window.setSceneTrajectory = function(visible) {
        if (threeRenderer && threeRenderer.enabled) {
            if (threeRenderer.trajLine) threeRenderer.trajLine.visible = visible;
        }
    };

    // Scene controls toggle via panel header button
    window.toggleSceneControls = function() {
        const ctrl = document.getElementById('scene-controls');
        if (ctrl) {
            ctrl.style.display = ctrl.style.display === 'none' ? 'block' : 'none';
        }
    };

})();
