import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

export class ThreeRenderer {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            this.container = document.querySelector(`.${containerId}`);
        }
        
        if (!this.container) {
            console.error('[ThreeRenderer] Container not found:', containerId);
            this.enabled = false;
            return;
        }
        
        this.enabled = true;
        this.scene = new THREE.Scene();
        this.camera = new THREE.PerspectiveCamera(60, 1, 0.01, 200);
        this.renderer = new THREE.WebGLRenderer({ antialias: false, alpha: true, powerPreference: 'high-performance' });
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this.renderer.setClearColor(0x0f172a, 1);
        
        // CRITICAL: canvas must be positioned to fill container
        const canvas = this.renderer.domElement;
        canvas.style.position = 'absolute';
        canvas.style.top = '0';
        canvas.style.left = '0';
        canvas.style.width = '100%';
        canvas.style.height = '100%';
        canvas.style.zIndex = '0';  // Below placeholder
        
        this.container.appendChild(canvas);

        this.orbit = new OrbitControls(this.camera, canvas);
        this.orbit.enableDamping = true;
        this.orbit.dampingFactor = 0.1;
        this.orbit.rotateSpeed = 0.8;

        this.camera.position.set(0, 2, 4);
        this.camera.lookAt(0, 0, 0);

        this.setupScene();
        this.resize();
        this.animate();
    }

    setupScene() {
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
        this.scene.add(ambientLight);

        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
        directionalLight.position.set(5, 10, 7);
        this.scene.add(directionalLight);

        const axesHelper = new THREE.AxesHelper(1);
        this.scene.add(axesHelper);

        const gridHelper = new THREE.GridHelper(10, 20, 0x1e293b, 0x1e293b);
        gridHelper.position.y = -0.01;
        this.scene.add(gridHelper);
        this.gridHelper = gridHelper;

        this.trajectoryGroup = new THREE.Group();
        this.scene.add(this.trajectoryGroup);

        this.pointCloudGroup = new THREE.Group();
        this.scene.add(this.pointCloudGroup);

        // Real-time pose tracking
        this.liveTrajectoryPoints = [];
        this.maxLivePoints = 2000;
        
        // Pre-allocate trajectory line geometry
        this.liveTrajectoryPositions = new Float32Array(this.maxLivePoints * 3);
        this.liveTrajectoryGeometry = new THREE.BufferGeometry();
        this.liveTrajectoryGeometry.setAttribute('position', 
            new THREE.BufferAttribute(this.liveTrajectoryPositions, 3));
        this.liveTrajectoryGeometry.setDrawRange(0, 0);
        
        const liveMaterial = new THREE.LineBasicMaterial({
            color: 0xfbbf24,
            linewidth: 2,
            transparent: true,
            opacity: 0.9
        });
        this.liveTrajectoryLine = new THREE.Line(this.liveTrajectoryGeometry, liveMaterial);
        this.trajectoryGroup.add(this.liveTrajectoryLine);
        
        this.cameraMarker = null;
        
        // Reusable objects to reduce GC
        this._tempVec3 = new THREE.Vector3();
        this._tempQuat = new THREE.Quaternion();
    }

    updateCameraPose(pose) {
        if (!this.enabled || !pose) return;

        const tx = pose.tx || 0;
        const ty = pose.ty || 0;
        const tz = pose.tz || 0;

        // Add point to trajectory
        const idx = this.liveTrajectoryPoints.length;
        if (idx >= this.maxLivePoints) {
            this.liveTrajectoryPoints.shift();
            this.liveTrajectoryPositions.copyWithin(0, 3, this.maxLivePoints * 3);
            this.liveTrajectoryPoints.push(1);
        }
        
        const pointIdx = Math.min(idx, this.maxLivePoints - 1);
        this.liveTrajectoryPositions[pointIdx * 3] = tx;
        this.liveTrajectoryPositions[pointIdx * 3 + 1] = ty;
        this.liveTrajectoryPositions[pointIdx * 3 + 2] = tz;
        
        if (idx < this.maxLivePoints) {
            this.liveTrajectoryPoints.push(1);
        }

        const drawCount = Math.min(this.liveTrajectoryPoints.length, this.maxLivePoints);
        this.liveTrajectoryGeometry.setDrawRange(0, drawCount);
        this.liveTrajectoryGeometry.attributes.position.needsUpdate = true;

        this.updateCameraMarker(tx, ty, tz, pose);

        // Auto-follow: smoothly move orbit target
        this._tempVec3.set(tx, ty, tz);
        this.orbit.target.lerp(this._tempVec3, 0.05);
    }

    updateCameraMarker(tx, ty, tz, pose) {
        if (!this.cameraMarker) {
            const markerGroup = new THREE.Group();

            const bodyGeo = new THREE.BoxGeometry(0.08, 0.06, 0.04);
            const bodyMat = new THREE.MeshBasicMaterial({ color: 0xfbbf24, transparent: true, opacity: 0.8 });
            markerGroup.add(new THREE.Mesh(bodyGeo, bodyMat));

            const coneGeo = new THREE.ConeGeometry(0.02, 0.06, 4);
            const coneMat = new THREE.MeshBasicMaterial({ color: 0xef4444 });
            const cone = new THREE.Mesh(coneGeo, coneMat);
            cone.rotation.x = Math.PI / 2;
            cone.position.z = -0.05;
            markerGroup.add(cone);

            this.cameraMarker = markerGroup;
            this.scene.add(this.cameraMarker);
        }

        this.cameraMarker.position.set(tx, ty, tz);

        if (pose.qw !== undefined) {
            this._tempQuat.set(pose.qx, pose.qy, pose.qz, pose.qw);
            this.cameraMarker.quaternion.copy(this._tempQuat);
        }
    }

    addTrajectory(poses) {
        if (!this.enabled) return;
        if (!poses || poses.length === 0) return;

        const staticGroup = new THREE.Group();
        staticGroup.name = 'staticTrajectory';

        const positions = new Float32Array(poses.length * 3);
        for (let i = 0; i < poses.length; i++) {
            positions[i * 3] = poses[i].tx;
            positions[i * 3 + 1] = poses[i].ty;
            positions[i * 3 + 2] = poses[i].tz;
        }

        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

        const material = new THREE.LineBasicMaterial({
            color: 0x38bdf8,
            linewidth: 2,
            transparent: true,
            opacity: 0.8
        });

        const line = new THREE.Line(geometry, material);
        staticGroup.add(line);

        const startMarker = new THREE.Mesh(
            new THREE.SphereGeometry(0.05),
            new THREE.MeshBasicMaterial({ color: 0x22c55e })
        );
        startMarker.position.set(poses[0].tx, poses[0].ty, poses[0].tz);
        staticGroup.add(startMarker);

        const endMarker = new THREE.Mesh(
            new THREE.SphereGeometry(0.05),
            new THREE.MeshBasicMaterial({ color: 0xef4444 })
        );
        const last = poses[poses.length - 1];
        endMarker.position.set(last.tx, last.ty, last.tz);
        staticGroup.add(endMarker);

        this.trajectoryGroup.add(staticGroup);

        if (this.liveTrajectoryPoints.length <= 1) {
            this.centerCameraOnTrajectory(poses);
        }
    }

    centerCameraOnTrajectory(poses) {
        let minX = Infinity, maxX = -Infinity;
        let minY = Infinity, maxY = -Infinity;
        let minZ = Infinity, maxZ = -Infinity;

        for (const pose of poses) {
            minX = Math.min(minX, pose.tx);
            maxX = Math.max(maxX, pose.tx);
            minY = Math.min(minY, pose.ty);
            maxY = Math.max(maxY, pose.ty);
            minZ = Math.min(minZ, pose.tz);
            maxZ = Math.max(maxZ, pose.tz);
        }

        const centerX = (minX + maxX) / 2;
        const centerY = (minY + maxY) / 2;
        const centerZ = (minZ + maxZ) / 2;

        const size = Math.max(maxX - minX, maxY - minY, maxZ - minZ, 0.5);
        const distance = size * 3;

        this.orbit.target.set(centerX, centerY, centerZ);
        this.camera.position.set(
            centerX + distance * 0.5,
            centerY + distance * 0.7,
            centerZ + distance * 0.5
        );
        this.orbit.update();
    }

    addPointCloud(points) {
        if (!this.enabled) return;
        this.pointCloudGroup.clear();

        if (!points || points.length === 0) return;

        const geometry = new THREE.BufferGeometry();
        const positions = new Float32Array(points.length * 3);
        const colors = new Float32Array(points.length * 3);

        for (let i = 0; i < points.length; i++) {
            positions[i * 3] = points[i].x;
            positions[i * 3 + 1] = points[i].y;
            positions[i * 3 + 2] = points[i].z;
            colors[i * 3] = points[i].r / 255;
            colors[i * 3 + 1] = points[i].g / 255;
            colors[i * 3 + 2] = points[i].b / 255;
        }

        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

        const material = new THREE.PointsMaterial({
            size: 0.02,
            vertexColors: true,
            transparent: true,
            opacity: 0.8
        });

        const pointCloud = new THREE.Points(geometry, material);
        this.pointCloudGroup.add(pointCloud);
    }

    updateMapPoints(coords) {
        if (!this.enabled || !coords || coords.length < 3) return;
        
        const pointCount = Math.floor(coords.length / 3);
        
        // Update or create live point cloud
        if (!this.livePointCloud) {
            const geometry = new THREE.BufferGeometry();
            const maxPoints = 5000;
            const positions = new Float32Array(maxPoints * 3);
            const colors = new Float32Array(maxPoints * 3);
            
            geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
            geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
            geometry.setDrawRange(0, 0);
            
            const material = new THREE.PointsMaterial({
                size: 0.02,
                vertexColors: true,
                transparent: true,
                opacity: 0.7,
                sizeAttenuation: true
            });
            
            this.livePointCloud = new THREE.Points(geometry, material);
            this.livePointCloudGeometry = geometry;
            this.livePointCloudMaxPoints = maxPoints;
            this.pointCloudGroup.add(this.livePointCloud);
        }
        
        // Update positions
        const posAttr = this.livePointCloudGeometry.attributes.position;
        const colAttr = this.livePointCloudGeometry.attributes.color;
        const drawCount = Math.min(pointCount, this.livePointCloudMaxPoints);
        
        for (let i = 0; i < drawCount; i++) {
            posAttr.array[i * 3] = coords[i * 3];
            posAttr.array[i * 3 + 1] = coords[i * 3 + 2];  // Z up -> Y up swap
            posAttr.array[i * 3 + 2] = -coords[i * 3 + 1];  // Y -> -Z
            
            // Color: height-based gradient (blue low -> green mid -> red high)
            const y = coords[i * 3 + 2]; // original Z
            const t = Math.max(0, Math.min(1, (y + 0.5) / 1.0));
            if (t < 0.5) {
                colAttr.array[i * 3] = 0.2;
                colAttr.array[i * 3 + 1] = 0.4 + t * 1.2;
                colAttr.array[i * 3 + 2] = 1.0 - t * 1.6;
            } else {
                colAttr.array[i * 3] = (t - 0.5) * 2;
                colAttr.array[i * 3 + 1] = 1.0 - (t - 0.5) * 1.2;
                colAttr.array[i * 3 + 2] = 0.2;
            }
        }
        
        posAttr.needsUpdate = true;
        colAttr.needsUpdate = true;
        this.livePointCloudGeometry.setDrawRange(0, drawCount);
        
        // Auto-scale grid to match data extent
        this._autoScaleGrid(coords);
    }
    
    _autoScaleGrid(coords) {
        if (!this.gridHelper) return;
        let maxExtent = 0;
        for (let i = 0; i < coords.length; i += 3) {
            const ext = Math.max(Math.abs(coords[i]), Math.abs(coords[i + 2]));
            if (ext > maxExtent) maxExtent = ext;
        }
        const gridSize = Math.max(2, Math.ceil(maxExtent * 2.5));
        // Only update if significantly different
        if (Math.abs(this._lastGridSize - gridSize) > 1) {
            this.scene.remove(this.gridHelper);
            this.gridHelper = new THREE.GridHelper(gridSize, gridSize, 0x1e293b, 0x1e293b);
            this.gridHelper.position.y = -0.01;
            this.scene.add(this.gridHelper);
            this._lastGridSize = gridSize;
        }
    }

    resize() {
        if (!this.enabled || !this.container) return;
        const width = this.container.clientWidth;
        const height = this.container.clientHeight;
        if (width === 0 || height === 0) {
            // Container not yet laid out, retry after a short delay
            setTimeout(() => this.resize(), 100);
            return;
        }
        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height);
    }

    animate() {
        if (!this.enabled) return;
        requestAnimationFrame(() => this.animate());
        this.orbit.update();
        this.renderer.render(this.scene, this.camera);
    }
}
