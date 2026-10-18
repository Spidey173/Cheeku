/**
 * CHEEKU NEURAL OPERATING SYSTEM // CORE RUNTIME ENGINE
 * Focused Organic Fluid Consciousness & Middle Music Waves
 * Three.js • WebGL Shaders • UnrealBloom • Real-time Web Audio FFT • Mature VisionOS Transcription
 */

class CheekuOS {
    constructor() {
        this.state = 'BOOTING';
        this.canvas = document.getElementById('webgl-canvas');
        this.transcriptBar = document.getElementById('transcript-bar');
        this.transcriptText = document.getElementById('live-transcript-text');
        this.actionHud = document.getElementById('action-hud');
        this.speechFloater = document.getElementById('holo-speech-floater');
        this.audioPlayer = document.getElementById('tts-audio-player');
        this.coreTrigger = document.getElementById('core-trigger');

        // Frontend Chat & Command Dock Elements
        this.chatDock = document.getElementById('hud-chat-dock');
        this.chatForm = document.getElementById('chat-form');
        this.chatInput = document.getElementById('chat-input');
        this.micDockBtn = document.getElementById('mic-dock-btn');
        this.sendDockBtn = document.getElementById('send-dock-btn');
        this.eqBars = document.querySelectorAll('#eq-bars .eq-bar');
        this.lastAssistantReply = '';
        this.currentAudioSource = null;
        this.speechFallbackTimer = null;
        this.audioPlayed = false;
        this.activeUtterance = null;

        // Audio & FFT Analysis
        this.audioCtx = null;
        this.micAnalyser = null;
        this.ttsAnalyser = null;
        this.fftData = new Uint8Array(128);
        this.audioLevel = 0.0;
        this.isAudioSetup = false;

        // Mouse & Gravitational Physics
        this.mouse = { x: 0, y: 0, targetX: 0, targetY: 0, normX: 0, normY: 0, down: false };
        this.cursorEl = document.getElementById('energy-cursor');

        // Speech Recognition
        this.recognition = null;
        this.isListening = false;
        this.speechActive = false;
        this.continuousMode = false; // Siri/Alexa/ChatGPT mode: single-turn by default
        this.transcriptTimer = null;
        this.silenceTimer = null; // Ultra-fast silence endpointing timer
        this.listenWindowTimer = null; // 5-second listen window timer
        this.latestSpokenText = '';

        // WebSocket
        this.ws = null;
        this.reconnectTimer = null;

        // Three.js Core Objects
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.composer = null;
        this.clock = new THREE.Clock();

        // 3D Visual Entities (Focused on Middle Fluid Core + Music Waves)
        this.coreGroup = null;
        this.plasmaSphere = null;
        this.plasmaMaterial = null;
        this.musicWaveRibbons = []; // Fluid 3D acoustic music waves in middle
        this.shockwaves = [];
        this.particles = null;
        this.particleGeo = null;
        this.nebulaMesh = null;

        // State & Camera Choreography
        this.targetCameraZ = 4.8;
        this.currentCameraZ = 10.0; // Boot sequence zoom target

        this.init();
    }

    async init() {
        this.initThree();
        this.initPostProcessing();
        this.createEnvironment();
        this.createFluidCore();
        this.createMiddleMusicWaves();
        this.createStarfield();
        this.initCursor();
        this.initEvents();
        this.initSpeechRecognition();
        this.connectWebSocket();
        
        // Start Render Loop
        this.animate();

        // Run Clean Boot Sequence
        this.runBootSequence();
    }

    /* ==========================================================================
       THREE.JS SCENE & POST-PROCESSING
       ========================================================================== */
    initThree() {
        this.scene = new THREE.Scene();
        this.scene.fog = new THREE.FogExp2(0x02040a, 0.045);

        const aspect = window.innerWidth / window.innerHeight;
        this.camera = new THREE.PerspectiveCamera(52, aspect, 0.1, 1000);
        this.camera.position.set(0, 0, this.currentCameraZ);

        this.renderer = new THREE.WebGLRenderer({
            canvas: this.canvas,
            antialias: true,
            alpha: true,
            powerPreference: 'high-performance'
        });
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
        this.renderer.toneMappingExposure = 1.35;

        // Soothing, Eye-Friendly Lighting (Zero Harsh Glare)
        const ambientLight = new THREE.AmbientLight(0x0a101f, 1.4);
        this.scene.add(ambientLight);

        const pointCyan = new THREE.PointLight(0x38bdf8, 1.2, 20);
        pointCyan.position.set(0, 0, 2.5);
        this.scene.add(pointCyan);

        const pointPurple = new THREE.PointLight(0x818cf8, 0.9, 18);
        pointPurple.position.set(0, -1.5, -1.5);
        this.scene.add(pointPurple);
    }

    initPostProcessing() {
        // Disabled harsh UnrealBloomPass to eliminate eye strain and blinding neon glow
        this.composer = null;
    }

    /* ==========================================================================
       THE LIVING FLUID PLASMA CORE (MIDDLE ENTITY)
       ========================================================================== */
    createFluidCore() {
        this.coreGroup = new THREE.Group();
        this.scene.add(this.coreGroup);

        // Procedural GLSL Simplex Noise Shader for organic liquid deformation
        const vertexShader = `
            uniform float uTime;
            uniform float uAudio;
            uniform float uDisplacement;
            varying vec3 vNormal;
            varying vec3 vPosition;
            varying float vNoise;

            vec4 permute(vec4 x){return mod(((x*34.0)+1.0)*x, 289.0);}
            vec4 taylorInvSqrt(vec4 r){return 1.79284291400159 - 0.85373472095314 * r;}
            float snoise(vec3 v){
                const vec2 C = vec2(1.0/6.0, 1.0/3.0);
                const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);
                vec3 i  = floor(v + dot(v, C.yyy));
                vec3 x0 = v - i + dot(i, C.xxx);
                vec3 g = step(x0.yzx, x0.xyz);
                vec3 l = 1.0 - g;
                vec3 i1 = min(g.xyz, l.zxy);
                vec3 i2 = max(g.xyz, l.zxy);
                vec3 x1 = x0 - i1 + 1.0 * C.xxx;
                vec3 x2 = x0 - i2 + 2.0 * C.xxx;
                vec3 x3 = x0 - 1.0 + 3.0 * C.xxx;
                i = mod(i, 289.0);
                vec4 p = permute(permute(permute(
                            i.z + vec4(0.0, i1.z, i2.z, 1.0))
                        + i.y + vec4(0.0, i1.y, i2.y, 1.0))
                        + i.x + vec4(0.0, i1.x, i2.x, 1.0));
                float n_ = 0.142857142857;
                vec3 ns = n_ * D.wyz - D.xzx;
                vec4 j = p - 49.0 * floor(p * ns.z * ns.z);
                vec4 x_ = floor(j * ns.z);
                vec4 y_ = floor(j - 7.0 * x_);
                vec4 x = x_ *ns.x + ns.yyyy;
                vec4 y = y_ *ns.x + ns.yyyy;
                vec4 h = 1.0 - abs(x) - abs(y);
                vec4 b0 = vec4(x.xy, y.xy);
                vec4 b1 = vec4(x.zw, y.zw);
                vec4 s0 = floor(b0)*2.0 + 1.0;
                vec4 s1 = floor(b1)*2.0 + 1.0;
                vec4 sh = -step(h, vec4(0.0));
                vec4 a0 = b0.xzyw + s0.xzyw*sh.xxyy;
                vec4 a1 = b1.xzyw + s1.xzyw*sh.zzww;
                vec3 p0 = vec3(a0.xy, h.x);
                vec3 p1 = vec3(a0.zw, h.y);
                vec3 p2 = vec3(a1.xy, h.z);
                vec3 p3 = vec3(a1.zw, h.w);
                vec4 norm = taylorInvSqrt(vec4(dot(p0,p0), dot(p1,p1), dot(p2, p2), dot(p3,p3)));
                p0 *= norm.x; p1 *= norm.y; p2 *= norm.z; p3 *= norm.w;
                vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
                m = m * m;
                return 42.0 * dot(m*m, vec4(dot(p0,x0), dot(p1,x1), dot(p2,x2), dot(p3,x3)));
            }

            void main() {
                vNormal = normal;
                vPosition = position;
                // Double harmonic turbulence
                float n1 = snoise(position * 2.1 + vec3(uTime * 0.75));
                float n2 = snoise(position * 4.2 - vec3(uTime * 1.1)) * 0.4;
                float noise = n1 + n2;
                vNoise = noise;
                
                // Voice amplitude drives liquid wave displacement
                float audioAmp = 0.14 + (uAudio * 0.45);
                float amp = audioAmp * uDisplacement;
                vec3 newPosition = position + normal * (noise * amp);
                gl_Position = projectionMatrix * modelViewMatrix * vec4(newPosition, 1.0);
            }
        `;

        const fragmentShader = `
            uniform float uTime;
            uniform float uAudio;
            uniform vec3 uColorA;
            uniform vec3 uColorB;
            varying vec3 vNormal;
            varying vec3 vPosition;
            varying float vNoise;

            void main() {
                vec3 normal = normalize(vNormal);
                // Soft, gentle matte rim (no blinding white specular)
                float fresnel = pow(1.0 - abs(dot(normal, vec3(0.0, 0.0, 1.0))), 2.0);
                vec3 baseColor = mix(uColorA, uColorB, vNoise * 0.45 + 0.55);
                vec3 softGlow = uColorA * (fresnel * 0.45 + uAudio * 0.4);
                vec3 finalColor = baseColor + softGlow;
                gl_FragColor = vec4(finalColor, 0.92);
            }
        `;

        this.plasmaMaterial = new THREE.ShaderMaterial({
            vertexShader,
            fragmentShader,
            uniforms: {
                uTime: { value: 0 },
                uAudio: { value: 0 },
                uDisplacement: { value: 1.0 },
                uColorA: { value: new THREE.Color(0x0ea5e9) }, // Calm sky azure
                uColorB: { value: new THREE.Color(0x6366f1) }  // Soft calming indigo
            },
            transparent: true,
            blending: THREE.NormalBlending
        });

        const sphereGeo = new THREE.SphereGeometry(0.92, 72, 72);
        this.plasmaSphere = new THREE.Mesh(sphereGeo, this.plasmaMaterial);
        this.coreGroup.add(this.plasmaSphere);
    }

    /* ==========================================================================
       CLEAN ACOUSTIC MUSIC WAVE (HORIZONTAL SOUND RIBBON - ZERO CIRCLE RINGS)
       ========================================================================== */
    createMiddleMusicWaves() {
        // Single clean horizontal acoustic soundwave ribbon beneath the core (Zero circle rings)
        this.wavePoints = 96;
        const positions = new Float32Array(this.wavePoints * 3);
        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

        const material = new THREE.LineBasicMaterial({
            color: 0x38bdf8,
            transparent: true,
            opacity: 0.65,
            linewidth: 2
        });

        this.acousticWaveLine = new THREE.Line(geometry, material);
        this.acousticWaveLine.position.set(0, -1.35, 0);
        this.coreGroup.add(this.acousticWaveLine);
    }

    /* ==========================================================================
       DEEP SPACE STARFIELD
       ========================================================================== */
    createStarfield() {
        const particleCount = 2800;
        const positions = new Float32Array(particleCount * 3);
        const colors = new Float32Array(particleCount * 3);
        const velocities = [];

        const colorCyan = new THREE.Color(0x00f3ff);
        const colorTeal = new THREE.Color(0x00ffd5);
        const colorPurple = new THREE.Color(0xb026ff);
        const colorWhite = new THREE.Color(0xffffff);

        for (let i = 0; i < particleCount; i++) {
            const r = 2.2 + Math.random() * 24.0;
            const theta = Math.random() * Math.PI * 2;
            const phi = Math.acos(2.0 * Math.random() - 1.0);

            positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
            positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
            positions[i * 3 + 2] = r * Math.cos(phi);

            const randColor = Math.random();
            let c = colorCyan;
            if (randColor < 0.35) c = colorCyan;
            else if (randColor < 0.65) c = colorTeal;
            else if (randColor < 0.85) c = colorPurple;
            else c = colorWhite;

            colors[i * 3] = c.r;
            colors[i * 3 + 1] = c.g;
            colors[i * 3 + 2] = c.b;

            velocities.push({
                x: (Math.random() - 0.5) * 0.005,
                y: (Math.random() - 0.5) * 0.005,
                z: (Math.random() - 0.5) * 0.005
            });
        }

        this.particleGeo = new THREE.BufferGeometry();
        this.particleGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        this.particleGeo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
        this.particleVelocities = velocities;

        const sprite = this.createParticleSprite();

        const particleMat = new THREE.PointsMaterial({
            size: 0.15,
            map: sprite,
            vertexColors: true,
            transparent: true,
            opacity: 0.8,
            blending: THREE.AdditiveBlending,
            depthWrite: false
        });

        this.particles = new THREE.Points(this.particleGeo, particleMat);
        this.scene.add(this.particles);
    }

    createParticleSprite() {
        const canvas = document.createElement('canvas');
        canvas.width = 64;
        canvas.height = 64;
        const ctx = canvas.getContext('2d');
        const grad = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
        grad.addColorStop(0, 'rgba(255, 255, 255, 1)');
        grad.addColorStop(0.25, 'rgba(0, 243, 255, 0.8)');
        grad.addColorStop(0.6, 'rgba(176, 38, 255, 0.25)');
        grad.addColorStop(1, 'rgba(0, 0, 0, 0)');
        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, 64, 64);

        const texture = new THREE.Texture(canvas);
        texture.needsUpdate = true;
        return texture;
    }

    createEnvironment() {
        const bgGeo = new THREE.SphereGeometry(45, 32, 32);
        const bgMat = new THREE.MeshBasicMaterial({
            color: 0x020511,
            side: THREE.BackSide
        });
        this.nebulaMesh = new THREE.Mesh(bgGeo, bgMat);
        this.scene.add(this.nebulaMesh);
    }

    /* ==========================================================================
       BOOT SEQUENCE
       ========================================================================== */
    runBootSequence() {
        const overlay = document.getElementById('boot-overlay');
        const spark = document.getElementById('boot-spark');
        const shockwave = document.getElementById('boot-shockwave');
        const status = document.getElementById('boot-status');
        const barFill = document.getElementById('boot-bar-fill');

        if (typeof gsap !== 'undefined') {
            const tl = gsap.timeline({
                onComplete: () => {
                    overlay.classList.add('boot-done');
                    this.setState('READY', 'Cheeku Neural OS Ready');
                }
            });

            tl.to(spark, { scale: 3.5, duration: 0.5, ease: 'power2.out' })
              .to(barFill, { width: '40%', duration: 0.4, ease: 'linear' }, '<')
              .call(() => { if (status) status.innerText = 'QUANTUM CORE SYNTHESIS'; })
              .to(spark, { scale: 10, opacity: 0.2, duration: 0.4, ease: 'power4.out' })
              .to(shockwave, {
                  width: '180vw',
                  height: '180vw',
                  opacity: 0.8,
                  duration: 0.8,
                  ease: 'power3.out'
              }, '<')
              .to(shockwave, { opacity: 0, duration: 0.3 }, '-=0.2')
              .to(barFill, { width: '100%', duration: 0.5 })
              .to(this, {
                  currentCameraZ: 4.8,
                  duration: 1.4,
                  ease: 'expo.out'
              }, '-=0.4')
              .call(() => { if (status) status.innerText = 'ONLINE // READY'; })
              .to(overlay, { opacity: 0, duration: 0.6, ease: 'power2.inOut' });

        } else {
            setTimeout(() => {
                overlay.classList.add('boot-done');
                this.currentCameraZ = 4.8;
                this.setState('READY', 'Ready');
            }, 1000);
        }
    }

    /* ==========================================================================
       INTERACTIVE ENERGY CURSOR & ACOUSTIC RIPPLES
       ========================================================================== */
    initCursor() {
        window.addEventListener('mousemove', (e) => {
            this.mouse.targetX = e.clientX;
            this.mouse.targetY = e.clientY;
            this.mouse.normX = (e.clientX / window.innerWidth) * 2 - 1;
            this.mouse.normY = -(e.clientY / window.innerHeight) * 2 + 1;
        });

        window.addEventListener('mousedown', () => {
            this.mouse.down = true;
            this.emitAcousticRipple();
        });

        window.addEventListener('mouseup', () => {
            this.mouse.down = false;
        });
    }

    emitAcousticRipple() {
        // Organic liquid ripple on the fluid blob (Zero circle rings)
        if (this.plasmaMaterial) {
            this.plasmaMaterial.uniforms.uDisplacement.value = 1.5;
            setTimeout(() => {
                if (this.plasmaMaterial) {
                    this.plasmaMaterial.uniforms.uDisplacement.value = this.state === 'LISTENING' ? 1.3 : 1.0;
                }
            }, 250);
        }
    }

    /* ==========================================================================
       WEB AUDIO API & MICROPHONE FREQUENCY ANALYSIS
       ========================================================================== */
    setupAudioContext() {
        if (!this.audioCtx) {
            try {
                const AudioCtxClass = window.AudioContext || window.webkitAudioContext;
                if (AudioCtxClass) {
                    this.audioCtx = new AudioCtxClass();
                }
            } catch (e) {
                console.warn('AudioContext creation notice:', e);
            }
        }
        if (this.audioCtx) {
            if (this.audioCtx.state === 'suspended') {
                this.audioCtx.resume().catch(() => {});
            }
            if (!this.ttsAnalyser) {
                try {
                    this.ttsAnalyser = this.audioCtx.createAnalyser();
                    this.ttsAnalyser.fftSize = 256;
                    this.ttsAnalyser.smoothingTimeConstant = 0.8;
                } catch(e) {}
            }
        }
        if (window.speechSynthesis) {
            window.speechSynthesis.resume();
        }
        this.isAudioSetup = true;

        // Non-blocking microphone stream analysis for 3D fluid core ripples
        if (!this.micAnalyser && navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            navigator.mediaDevices.getUserMedia({ audio: true }).then((stream) => {
                if (this.audioCtx) {
                    const micSource = this.audioCtx.createMediaStreamSource(stream);
                    this.micAnalyser = this.audioCtx.createAnalyser();
                    this.micAnalyser.fftSize = 256;
                    this.micAnalyser.smoothingTimeConstant = 0.75;
                    micSource.connect(this.micAnalyser);
                }
            }).catch(() => {
                // Mic denied or not needed for voice output
            });
        }
    }

    unlockAudio() {
        this.setupAudioContext();
        if (this.audioCtx && this.audioCtx.state === 'suspended') {
            this.audioCtx.resume().catch(() => {});
        }
        if (window.speechSynthesis) {
            window.speechSynthesis.resume();
        }
    }

    getLiveAudioLevel() {
        if (this.ttsAnalyser && this.state === 'SPEAKING') {
            this.ttsAnalyser.getByteFrequencyData(this.fftData);
            let sum = 0;
            for (let i = 0; i < 32; i++) {
                sum += this.fftData[i];
            }
            const level = (sum / 32) / 255.0;
            if (level > 0.04) return Math.min(1.0, level * 1.8);
        }
        if (this.state === 'SPEAKING') {
            // Procedural dynamic voice modulation for visual core & music waves fallback
            const t = Date.now() * 0.012;
            return 0.35 + 0.3 * Math.abs(Math.sin(t)) * (0.8 + 0.2 * Math.sin(t * 0.33));
        }
        if (this.micAnalyser && this.isListening) {
            this.micAnalyser.getByteFrequencyData(this.fftData);
            let sum = 0;
            for (let i = 0; i < 32; i++) {
                sum += this.fftData[i];
            }
            return (sum / 32) / 255.0;
        }
        return 0;
    }

    /* ==========================================================================
       SPEECH RECOGNITION & REFINED LIVE TRANSCRIPTION (VISIONOS AESTHETIC)
       ========================================================================== */
    initSpeechRecognition() {
        const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRec) {
            console.warn('Web Speech Recognition not supported in this browser.');
            return;
        }

        this.recognition = new SpeechRec();
        this.recognition.continuous = false; // Capture one utterance per interaction like Siri/Alexa
        this.recognition.interimResults = true;
        this.recognition.lang = 'en-US';

        this.recognition.onstart = () => {
            // Guard: Never start mic if assistant is speaking or processing
            if (this.state === 'SPEAKING' || this.state === 'THINKING' || this.state === 'CALLING_TOOL' || this.state === 'GENERATING') {
                this.stopListening();
                return;
            }
            this.isListening = true;
            this.latestSpokenText = '';
            clearTimeout(this.silenceTimer);
            this.setState('LISTENING', 'Listening...');
            this.showLiveTranscript('Listening...');
            this.updateTriggerHint('LISTENING...');
            this.updateMicButtonState(true);
        };

        this.recognition.onresult = (event) => {
            // Guard: completely drop events if not in LISTENING state
            if (this.state !== 'LISTENING') {
                return;
            }

            let interimTranscript = '';
            let finalTranscript = '';

            for (let i = event.resultIndex; i < event.results.length; ++i) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    finalTranscript += transcript;
                } else {
                    interimTranscript += transcript;
                }
            }

            const activePhrase = (finalTranscript || interimTranscript).trim();
            if (activePhrase) {
                this.latestSpokenText = activePhrase;
                this.showLiveTranscript(activePhrase);
                if (Math.random() < 0.3) {
                    this.emitAcousticRipple();
                }

                // Low-Latency VAD: Eliminate Chrome's 2.5s silence delay.
                // 700ms pause after speaking immediately dispatches user turn.
                clearTimeout(this.silenceTimer);
                this.silenceTimer = setTimeout(() => {
                    if (this.state === 'LISTENING' && this.latestSpokenText && this.latestSpokenText.length > 1) {
                        const clean = this.latestSpokenText;
                        this.latestSpokenText = '';
                        clearTimeout(this.silenceTimer);
                        clearTimeout(this.listenWindowTimer);
                        this.stopListening();
                        this.sendUserSpeech(clean);
                    }
                }, 700);
            }

            if (finalTranscript.trim()) {
                clearTimeout(this.silenceTimer);
                clearTimeout(this.listenWindowTimer);
                const clean = finalTranscript.trim();
                this.latestSpokenText = '';
                this.stopListening();
                this.sendUserSpeech(clean);
            }
        };

        this.recognition.onerror = (event) => {
            console.warn('Speech event error:', event.error);
            if (event.error !== 'no-speech') {
                this.stopListening();
                this.setState('READY', 'Ready');
            }
        };

        this.recognition.onend = () => {
            this.isListening = false;
            this.updateMicButtonState(false);
            if (this.state === 'LISTENING') {
                if (this.speechActive) {
                    try { this.recognition.start(); } catch(e){}
                } else {
                    this.setState('READY', 'Ready');
                    this.updateTriggerHint('TAP TO SPEAK');
                }
            }
        };
    }

    startListening() {
        if (this.state === 'SPEAKING' || this.state === 'THINKING' || this.state === 'CALLING_TOOL' || this.state === 'GENERATING') {
            console.log('[Cheeku] Microphone disabled while assistant is busy.');
            return;
        }
        this.setupAudioContext();
        if (!this.recognition) return;
        this.speechActive = true;
        this.updateMicButtonState(true);
        try {
            this.recognition.start();
        } catch (e) {}
    }

    stopListening() {
        this.speechActive = false;
        this.isListening = false;
        clearTimeout(this.silenceTimer);
        clearTimeout(this.listenWindowTimer);
        this.latestSpokenText = '';
        if (this.recognition) {
            try {
                this.recognition.abort(); // Immediately releases audio hardware
            } catch (e) {
                try { this.recognition.stop(); } catch(e2) {}
            }
        }
        this.updateMicButtonState(false);
        if (this.state !== 'SPEAKING' && this.state !== 'THINKING') {
            this.updateTriggerHint('TAP TO SPEAK');
        }
    }

    updateMicButtonState(active) {
        if (this.micDockBtn) {
            if (active) {
                this.micDockBtn.classList.add('active');
            } else {
                this.micDockBtn.classList.remove('active');
            }
        }
    }

    toggleSpeech() {
        if (this.isListening || this.speechActive) {
            this.stopListening();
            this.setState('READY', 'Ready');
            this.hideLiveTranscript();
        } else {
            if (this.state === 'SPEAKING') {
                this.stopCurrentAudio();
            }
            this.startListening();
        }
    }

    showLiveTranscript(text) {
        if (!this.transcriptBar || !this.transcriptText) return;
        this.transcriptText.innerText = `"${text}"`;
        this.transcriptBar.classList.remove('hidden');

        clearTimeout(this.transcriptTimer);
        this.transcriptTimer = setTimeout(() => {
            if (!this.isListening) {
                this.hideLiveTranscript();
            }
        }, 5000);
    }

    hideLiveTranscript() {
        if (this.transcriptBar) {
            this.transcriptBar.classList.add('hidden');
        }
    }

    /* ==========================================================================
       HOLOGRAPHIC ACTION HUD & RESPONSE FLOATER
       ========================================================================== */
    showActionHUD(data) {
        if (!this.actionHud) return;
        const iconEl = document.getElementById('action-icon');
        const typeEl = document.getElementById('action-type');
        const titleEl = document.getElementById('action-title');
        const detailEl = document.getElementById('action-detail');
        const progressEl = document.getElementById('action-progress');
        const statusEl = document.getElementById('action-status-tag');

        const title = data.title || 'SYSTEM DIRECTIVE';
        const detail = data.detail || '';
        const status = data.status || 'ACTIVE';

        if (title.toLowerCase().includes('youtube')) iconEl.innerText = '🎵';
        else if (title.toLowerCase().includes('telemetry') || title.toLowerCase().includes('vital')) iconEl.innerText = '⚡';
        else if (title.toLowerCase().includes('search')) iconEl.innerText = '🌐';
        else iconEl.innerText = '⚙️';

        if (typeEl) typeEl.innerText = 'DIRECTIVE ENGAGED';
        if (titleEl) titleEl.innerText = title.toUpperCase();
        if (detailEl) detailEl.innerText = detail ? `"${detail}"` : 'Processing request...';
        if (statusEl) statusEl.innerText = status.toUpperCase();

        this.actionHud.classList.remove('hidden');

        if (progressEl) {
            progressEl.style.width = '20%';
            setTimeout(() => { progressEl.style.width = '75%'; }, 300);
            setTimeout(() => { progressEl.style.width = '100%'; }, 900);
        }

        clearTimeout(this.actionTimer);
        this.actionTimer = setTimeout(() => {
            this.actionHud.classList.add('hidden');
        }, 4500);
    }

    showSpeechFloater(text) {
        if (!this.speechFloater) return;
        const textEl = document.getElementById('holo-response-text');
        if (textEl) textEl.innerText = text;

        this.speechFloater.classList.remove('hidden');

        clearTimeout(this.floaterTimer);
        this.floaterTimer = setTimeout(() => {
            if (this.state !== 'SPEAKING') {
                this.speechFloater.classList.add('hidden');
            }
        }, 8000);
    }

    /* ==========================================================================
       STATE MACHINE & VISUAL LANGUAGES
       ========================================================================== */
    setState(newState, detail = '') {
        this.state = newState;
        document.body.className = `state-${newState.toLowerCase()}`;

        // HARD ENFORCEMENT: Never allow microphone capture while assistant is busy or speaking
        if (newState === 'SPEAKING' || newState === 'THINKING' || newState === 'CALLING_TOOL' || newState === 'GENERATING') {
            this.stopListening();
        }

        const stateText = document.getElementById('state-text');
        if (stateText) stateText.innerText = newState;

        switch (newState) {
            case 'IDLE':
            case 'READY':
                this.targetCameraZ = 4.8;
                if (this.plasmaMaterial) {
                    this.plasmaMaterial.uniforms.uColorA.value.set(0x00f3ff);
                    this.plasmaMaterial.uniforms.uColorB.value.set(0xb026ff);
                }
                break;

            case 'LISTENING':
                this.targetCameraZ = 4.2; // Smooth camera focus
                if (this.plasmaMaterial) {
                    this.plasmaMaterial.uniforms.uColorA.value.set(0x00ffd5); // Bright electric teal
                    this.plasmaMaterial.uniforms.uColorB.value.set(0x00f3ff);
                }
                this.emitAcousticRipple(0x00ffd5);
                break;

            case 'THINKING':
                this.targetCameraZ = 5.2;
                if (this.plasmaMaterial) {
                    this.plasmaMaterial.uniforms.uColorA.value.set(0xb026ff); // Hyper violet
                    this.plasmaMaterial.uniforms.uColorB.value.set(0xff007f);
                }
                break;

            case 'SPEAKING':
                this.targetCameraZ = 4.5;
                if (this.plasmaMaterial) {
                    this.plasmaMaterial.uniforms.uColorA.value.set(0x00f3ff);
                    this.plasmaMaterial.uniforms.uColorB.value.set(0xffd000); // Warm gold speech glow
                }
                break;
        }
    }

    updateTriggerHint(text) {
        const hint = document.getElementById('trigger-hint');
        if (hint) hint.innerText = text;
    }

    /* ==========================================================================
       WEBSOCKET BRIDGE
       ========================================================================== */
    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('Cheeku Neural WebSocket Connected.');
        };

        this.ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                this.handleWSMessage(msg);
            } catch (e) {
                console.error('Error parsing WebSocket payload:', e);
            }
        };

        this.ws.onclose = () => {
            console.warn('WebSocket closed. Reconnecting in 2s...');
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = setTimeout(() => this.connectWebSocket(), 2000);
        };

        this.ws.onerror = (err) => {
            console.error('WebSocket error:', err);
        };
    }

    handleWSMessage(msg) {
        switch (msg.type) {
            case 'state_change':
                if (msg.payload && msg.payload.interrupted) {
                    this.stopCurrentAudio();
                }
                this.setState(msg.payload.state, msg.payload.details);
                break;

            case 'chat':
                if (msg.payload.role === 'assistant') {
                    this.lastAssistantReply = msg.payload.content;
                    this.showSpeechFloater(msg.payload.content);
                }
                break;

            case 'audio_failed':
                console.warn('Neural TTS synthesis failed. Invoking emergency speech fallback.');
                if (msg.payload && msg.payload.text) {
                    this.speakWithWebSpeech(msg.payload.text);
                }
                break;

            case 'tool_call':
                this.showActionHUD({
                    title: msg.payload.args?.title || msg.payload.tool,
                    detail: msg.payload.args?.detail || JSON.stringify(msg.payload.args?.args || {}),
                    status: 'ACTIVE'
                });
                break;

            case 'tool_result':
                let resData = {};
                try {
                    resData = typeof msg.payload.result === 'string' ? JSON.parse(msg.payload.result) : msg.payload.result;
                } catch(e) {
                    resData = { output: msg.payload.result };
                }
                this.showActionHUD({
                    title: resData.title || msg.payload.tool,
                    detail: resData.output || resData.detail || 'Directive complete',
                    status: 'COMPLETED'
                });
                break;

            case 'audio_chunk':
                if (msg.payload && msg.payload.audio_base64) {
                    const mime = msg.payload.mime_type || 'audio/wav';
                    this.playAudioData(msg.payload.audio_base64, mime);
                }
                break;

            case 'telemetry':
                this.updateTelemetry(msg.payload);
                break;
        }
    }

    stopCurrentAudio() {
        if (this.currentAudioSource) {
            try {
                this.currentAudioSource.onended = null;
                this.currentAudioSource.stop();
                this.currentAudioSource.disconnect();
            } catch (e) {}
            this.currentAudioSource = null;
        }
        if (window.speechSynthesis) {
            try {
                window.speechSynthesis.cancel();
            } catch (e) {}
        }
        clearTimeout(this.speechFallbackTimer);
        this.audioPlayed = false;
    }

    sendUserSpeech(text) {
        if (!text || !this.ws || this.ws.readyState !== WebSocket.OPEN) return;
        this.stopCurrentAudio();
        this.unlockAudio();
        this.ws.send(JSON.stringify({
            type: 'transcript',
            payload: { text: text }
        }));
    }

    sendUserChat(text) {
        if (!text || !text.trim()) return;
        const clean = text.trim();
        this.stopCurrentAudio();
        this.unlockAudio();
        this.showLiveTranscript(clean);
        this.setState('THINKING', 'Consulting neural brain...');

        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'chat',
                payload: { text: clean }
            }));
        } else {
            console.warn('WebSocket not connected. Unable to send command.');
        }
    }

    async playAudioData(b64, mime = 'audio/wav') {
        if (!b64) return false;
        this.stopListening(); // HARD STOP: Prevent microphone conflict during playback
        this.unlockAudio();

        // HARD SILENCE: Cancel any browser speech synthesis to ensure only neural TTS plays
        if (window.speechSynthesis) {
            try { window.speechSynthesis.cancel(); } catch (e) {}
        }

        try {
            if (!this.audioCtx) {
                const AudioCtxClass = window.AudioContext || window.webkitAudioContext;
                if (AudioCtxClass) this.audioCtx = new AudioCtxClass();
            }

            if (this.audioCtx && this.audioCtx.state === 'suspended') {
                await this.audioCtx.resume();
            }

            // Convert Base64 string to Uint8Array buffer
            const binaryString = window.atob(b64);
            const len = binaryString.length;
            const bytes = new Uint8Array(len);
            for (let i = 0; i < len; i++) {
                bytes[i] = binaryString.charCodeAt(i);
            }

            // Decode raw audio bytes with Web Audio API (slice copy avoids detached buffer issues)
            const audioBuffer = await this.audioCtx.decodeAudioData(bytes.buffer.slice(0));

            // Stop any currently playing audio node
            if (this.currentAudioSource) {
                try {
                    this.currentAudioSource.onended = null;
                    this.currentAudioSource.stop();
                } catch (e) {}
                this.currentAudioSource = null;
            }

            const source = this.audioCtx.createBufferSource();
            source.buffer = audioBuffer;

            // Route audio: Source -> Visualizer Analyser -> Speakers
            if (this.ttsAnalyser) {
                source.connect(this.ttsAnalyser);
                this.ttsAnalyser.connect(this.audioCtx.destination);
            } else {
                source.connect(this.audioCtx.destination);
            }

            this.currentAudioSource = source;
            this.audioPlayed = true;
            clearTimeout(this.speechFallbackTimer);

            this.setState('SPEAKING', 'Cheeku is speaking...');
            if (this.lastAssistantReply) {
                this.showSpeechFloater(this.lastAssistantReply);
            }

            source.onended = () => {
                if (this.currentAudioSource === source) {
                    this.currentAudioSource = null;
                }
                this.setState('READY', 'Ready');
                if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                    this.ws.send(JSON.stringify({ type: 'state_change', payload: { state: 'READY' } }));
                }
                // Only restart listening if continuous mode is enabled
                if (this.continuousMode) {
                    this.startListening();
                }
            };

            source.start(0);
            return true;

        } catch (err) {
            console.warn('Web Audio API playback notice, invoking Web Speech fallback:', err);
            if (this.lastAssistantReply) {
                this.speakWithWebSpeech(this.lastAssistantReply);
            }
            return false;
        }
    }

    speakWithWebSpeech(text) {
        if (!('speechSynthesis' in window) || !text) {
            this.setState('READY', 'Ready');
            return;
        }
        this.stopListening(); // HARD STOP: Stop microphone during speech synthesis

        try {
            this.unlockAudio();

            let clean = text.replace(/[🌸💖✨🎶💕😊🥰*#`_~><[\]]/g, '').trim();
            if (!clean) return;

            // Clear any lingering queue
            window.speechSynthesis.cancel();
            window.speechSynthesis.resume();

            const utterance = new SpeechSynthesisUtterance(clean);
            utterance.rate = 1.0;
            utterance.pitch = 1.15;
            utterance.volume = 1.0;

            // CRITICAL FOR CHROME/SAFARI: Store utterance globally to prevent V8 garbage collection mid-speech
            window.__activeUtterance = utterance;
            this.activeUtterance = utterance;

            const voices = window.speechSynthesis.getVoices();
            if (voices && voices.length > 0) {
                const preferred = voices.find(v => 
                    v.name.includes('Samantha') || 
                    v.name.includes('Victoria') || 
                    v.name.includes('Karen') || 
                    v.name.includes('Tessa') ||
                    (v.lang && v.lang.startsWith('en') && v.name.toLowerCase().includes('female'))
                );
                if (preferred) utterance.voice = preferred;
            }

            utterance.onstart = () => {
                this.audioPlayed = true;
                clearTimeout(this.speechFallbackTimer);
                this.setState('SPEAKING', 'Cheeku is speaking...');
                if (this.lastAssistantReply) {
                    this.showSpeechFloater(this.lastAssistantReply);
                }
            };

            utterance.onend = () => {
                window.__activeUtterance = null;
                this.activeUtterance = null;
                this.setState('READY', 'Ready');
                if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                    this.ws.send(JSON.stringify({ type: 'state_change', payload: { state: 'READY' } }));
                }
                if (this.continuousMode) {
                    this.startListening();
                }
            };

            utterance.onerror = (err) => {
                console.warn('SpeechSynthesis error event:', err);
                window.__activeUtterance = null;
                this.activeUtterance = null;
                this.setState('READY', 'Ready');
            };

            // Small 40ms timeout ensures Chrome completes previous cancel() cleanup before speak()
            setTimeout(() => {
                window.speechSynthesis.resume();
                window.speechSynthesis.speak(utterance);
            }, 40);

        } catch (err) {
            console.warn('Client-side speech synthesis exception:', err);
            this.setState('READY', 'Ready');
        }
    }

    updateTelemetry(data) {
        const cpu = document.getElementById('tel-cpu');
        const ram = document.getElementById('tel-ram');
        const status = document.getElementById('tel-status');

        if (cpu && data.cpu_percent !== undefined) cpu.innerText = `${data.cpu_percent.toFixed(0)}%`;
        if (ram && data.ram_used_gb !== undefined) ram.innerText = `${data.ram_used_gb.toFixed(1)} GB`;
        if (status && data.status) status.innerText = data.status.toUpperCase();
    }

    /* ==========================================================================
       USER EVENT LISTENERS
       ========================================================================== */
    initEvents() {
        window.addEventListener('resize', () => {
            const w = window.innerWidth;
            const h = window.innerHeight;
            this.camera.aspect = w / h;
            this.camera.updateProjectionMatrix();
            this.renderer.setSize(w, h);
            if (this.composer) this.composer.setSize(w, h);
        });

        if (this.coreTrigger) {
            this.coreTrigger.addEventListener('click', (e) => {
                e.stopPropagation();
                this.unlockAudio();
                this.toggleSpeech();
            });
        }

        // Chat Form Submission
        if (this.chatForm) {
            this.chatForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.unlockAudio();
                if (this.chatInput) {
                    const text = this.chatInput.value.trim();
                    if (text) {
                        this.sendUserChat(text);
                        this.chatInput.value = '';
                    }
                }
            });
        }

        // Dock Mic Button
        if (this.micDockBtn) {
            this.micDockBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.unlockAudio();
                this.toggleSpeech();
            });
        }

        // Voice Test Button
        const voiceTestBtn = document.getElementById('voice-test-btn');
        if (voiceTestBtn) {
            voiceTestBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.unlockAudio();
                const testMsg = "Hello! Cheeku neural voice is active and crystal clear!";
                this.lastAssistantReply = testMsg;
                this.showSpeechFloater(testMsg);
                this.speakWithWebSpeech(testMsg);
            });
        }

        // Preload and cache browser voices
        if ('speechSynthesis' in window) {
            window.speechSynthesis.onvoiceschanged = () => {
                window.speechSynthesis.getVoices();
            };
        }

        // Global User Interaction Unlock for Audio Context & Speech Synthesis
        const globalUnlock = () => {
            this.unlockAudio();
        };
        ['click', 'touchstart', 'keydown', 'mousedown', 'pointerdown'].forEach(ev => {
            window.addEventListener(ev, globalUnlock, { passive: true });
        });

        // Spacebar Hotkey to toggle Mic (when not typing in chat input)
        window.addEventListener('keydown', (e) => {
            if (e.code === 'Space' && !e.repeat) {
                const targetTag = (e.target && e.target.tagName) ? e.target.tagName.toLowerCase() : '';
                if (targetTag !== 'input' && targetTag !== 'textarea') {
                    e.preventDefault();
                    this.toggleSpeech();
                }
            }
        });

        // Cmd + C (or Ctrl + C) Hotkey: Activates listening with a 5-second automatic listen window
        window.addEventListener('keydown', (e) => {
            const isCmdC = (e.metaKey || e.ctrlKey) && (e.key.toLowerCase() === 'c' || e.code === 'KeyC');
            if (isCmdC) {
                const selectedText = window.getSelection() ? window.getSelection().toString() : '';
                const targetTag = (e.target && e.target.tagName) ? e.target.tagName.toLowerCase() : '';
                const isTyping = (targetTag === 'input' || targetTag === 'textarea') && selectedText.length > 0;

                // Do not intercept if user has highlighted text to copy
                if (!isTyping && !selectedText) {
                    e.preventDefault();
                    this.unlockAudio();
                    if (this.state === 'SPEAKING') {
                        this.stopCurrentAudio();
                    }
                    this.startListening();
                    this.showLiveTranscript('Listening (Cmd+C)...');

                    // 5-second listen window: if no speech is heard within 5s, turns off automatically
                    clearTimeout(this.listenWindowTimer);
                    this.listenWindowTimer = setTimeout(() => {
                        if (this.state === 'LISTENING' && !this.latestSpokenText) {
                            this.stopListening();
                            this.setState('READY', 'Ready');
                            this.updateTriggerHint('TAP TO SPEAK');
                        }
                    }, 5000);
                }
            }
        });
    }

    /* ==========================================================================
       RENDER LOOP: PROCEDURAL MOTION & MIDDLE MUSIC WAVES
       ========================================================================== */
    animate() {
        requestAnimationFrame(() => this.animate());

        const delta = this.clock.getDelta();
        const elapsedTime = this.clock.getElapsedTime();

        // 1. Audio Level Sync
        const currentAudioLevel = this.getLiveAudioLevel();
        this.audioLevel = THREE.MathUtils.lerp(this.audioLevel, currentAudioLevel, 0.3);

        // 2. Camera Organic Cinematic Motion
        this.currentCameraZ = THREE.MathUtils.lerp(this.currentCameraZ, this.targetCameraZ, 0.04);
        
        const breathY = Math.sin(elapsedTime * 0.8) * 0.1;
        const breathX = Math.cos(elapsedTime * 0.5) * 0.07;

        const targetCamX = breathX + this.mouse.normX * 0.45;
        const targetCamY = breathY + this.mouse.normY * 0.3;

        this.camera.position.x = THREE.MathUtils.lerp(this.camera.position.x, targetCamX, 0.05);
        this.camera.position.y = THREE.MathUtils.lerp(this.camera.position.y, targetCamY, 0.05);
        this.camera.position.z = this.currentCameraZ;
        this.camera.lookAt(0, 0, 0);

        // 3. Update Middle Fluid Plasma Blob
        if (this.plasmaMaterial) {
            this.plasmaMaterial.uniforms.uTime.value = elapsedTime;
            this.plasmaMaterial.uniforms.uAudio.value = this.audioLevel;
            const stateDisplacement = this.state === 'THINKING' ? 1.6 : (this.state === 'LISTENING' ? 1.35 : 1.0);
            this.plasmaMaterial.uniforms.uDisplacement.value = stateDisplacement;
        }

        // Pulse scale with live music & speech
        const coreScale = 1.0 + (this.audioLevel * 0.42) + Math.sin(elapsedTime * 1.5) * 0.025;
        this.plasmaSphere.scale.set(coreScale, coreScale, coreScale);

        // 4. Update Clean Acoustic Waveform Line (Zero Circle Rings)
        if (this.acousticWaveLine) {
            const posAttr = this.acousticWaveLine.geometry.attributes.position;
            const positions = posAttr.array;
            const total = this.wavePoints || 96;

            for (let i = 0; i < total; i++) {
                const norm = (i / (total - 1)) * 2.0 - 1.0; // from -1.0 to +1.0
                const x = norm * 1.8; // span width beneath the fluid core

                // Gaussian bell curve envelope for elegant tapering
                const envelope = Math.exp(-norm * norm * 3.2);

                // Sample audio FFT frequency
                const fftIdx = Math.floor(Math.abs(norm) * 28);
                let freq = (this.fftData[fftIdx] / 255.0);
                if (this.audioLevel < 0.02) {
                    freq = 0.04 + Math.sin(elapsedTime * 2.0 + norm * 3.5) * 0.03;
                }

                // Gentle vertical wave undulating with sound
                const waveHeight = Math.sin(norm * 10.0 - elapsedTime * 4.0) * (0.04 + this.audioLevel * 0.38) * freq * envelope;
                const y = waveHeight;
                const z = 0;

                positions[i * 3] = x;
                positions[i * 3 + 1] = y;
                positions[i * 3 + 2] = z;
            }
            posAttr.needsUpdate = true;
        }

        // 6. Particle Field Motion & Subtle Gravitational Drift
        if (this.particles && this.particleGeo) {
            const posAttr = this.particleGeo.attributes.position;
            const positions = posAttr.array;
            const pCount = this.particleVelocities.length;
            const mouseWorldX = this.mouse.normX * 5.5;
            const mouseWorldY = this.mouse.normY * 3.5;

            for (let i = 0; i < pCount; i++) {
                let px = positions[i * 3];
                let py = positions[i * 3 + 1];
                let pz = positions[i * 3 + 2];
                const vel = this.particleVelocities[i];

                px += vel.x;
                py += vel.y;
                pz += vel.z;

                // Mouse gravitational attraction
                const dx = mouseWorldX - px;
                const dy = mouseWorldY - py;
                const distSq = dx * dx + dy * dy;
                if (distSq < 14.0 && distSq > 0.1) {
                    const force = 0.0025 / Math.sqrt(distSq);
                    px += dx * force;
                    py += dy * force;
                }

                // Wrap-around
                if (Math.abs(px) > 18) vel.x *= -1;
                if (Math.abs(py) > 18) vel.y *= -1;
                if (Math.abs(pz) > 18) vel.z *= -1;

                positions[i * 3] = px;
                positions[i * 3 + 1] = py;
                positions[i * 3 + 2] = pz;
            }
            posAttr.needsUpdate = true;
        }

        // 6. Update Bottom HUD EQ Bars
        if (this.eqBars && this.eqBars.length > 0) {
            const isSpeakingOrListening = this.state === 'SPEAKING' || this.state === 'LISTENING';
            this.eqBars.forEach((bar, idx) => {
                let h = 4;
                if (isSpeakingOrListening) {
                    const freqSample = this.fftData[idx * 5] || 0;
                    h = Math.max(4, (freqSample / 255) * 20 + this.audioLevel * 14);
                } else {
                    h = 4 + Math.sin(elapsedTime * 3 + idx) * 2;
                }
                bar.style.height = `${Math.min(24, Math.round(h))}px`;
            });
        }

        // 7. Render
        if (this.composer) {
            this.composer.render();
        } else {
            this.renderer.render(this.scene, this.camera);
        }
    }
}

// Instantiate and Boot Cheeku OS on DOM Ready
window.addEventListener('DOMContentLoaded', () => {
    window.cheeku = new CheekuOS();
});
