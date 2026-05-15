import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

export class ThreeRenderer {
    constructor(containerId) {
        this.container = document.getElementById(containerId) || document.querySelector(`.${containerId}`);
        
        if (!this.container) {
            console.error(`[ThreeRenderer] Container not found: ${containerId}`);
            this.enabled = false;
            return;
        }
        
        this.enabled = true;
        this.scene = new THREE.Scene();
        this.camera = new THREE.PerspectiveCamera(60, 1, 0.01, 200);
        this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.renderer.setClearColor(0x0f172a, 1);
        this.container.appendChild(this.renderer.domElement);

        this.orbit = new OrbitControls(this.camera, this.renderer.domElement);
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

        this.trajectoryGroup = new THREE.Group();
        this.scene.add(this.trajectoryGroup);

        this.pointCloudGroup = new THREE.Group();
        this.scene.add(this.pointCloudGroup);
    }

    addTrajectory(poses) {
        if (!this.enabled) return;
        this.trajectoryGroup.clear();

        if (!poses || poses.length === 0) return;

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
        this.trajectoryGroup.add(line);

        const startMarker = new THREE.Mesh(
            new THREE.SphereGeometry(0.05),
            new THREE.MeshBasicMaterial({ color: 0x22c55e })
        );
        startMarker.position.set(poses[0].tx, poses[0].ty, poses[0].tz);
        this.trajectoryGroup.add(startMarker);

        const endMarker = new THREE.Mesh(
            new THREE.SphereGeometry(0.05),
            new THREE.MeshBasicMaterial({ color: 0xef4444 })
        );
        const last = poses[poses.length - 1];
        endMarker.position.set(last.tx, last.ty, last.tz);
        this.trajectoryGroup.add(endMarker);

        this.centerCameraOnTrajectory(poses);
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

        const size = Math.max(maxX - minX, maxY - minY, maxZ - minZ);
        const distance = size * 2;

        this.orbit.target.set(centerX, centerY, centerZ);
        this.camera.position.set(
            centerX + distance * 0.5,
            centerY + distance * 0.3,
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

    resize() {
        if (!this.enabled) return;
        const width = this.container.clientWidth;
        const height = this.container.clientHeight;
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