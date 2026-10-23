/**
 * CHEEKU NEURAL OPERATING SYSTEM // VERCEL LIVE DEMO ENGINE
 * Three.js 3D WebGL Simplex Shader • Real-Time Voice STT/TTS • Autonomous Neural Brain
 */

class CheekuDemo {
    constructor() {
        this.state = 'BOOTING';
        this.canvas = document.getElementById('webgl-canvas');
        this.transcriptBar = document.getElementById('transcript-bar');
        this.transcriptText = document.getElementById('live-transcript-text');
        this.actionHud = document.getElementById('action-hud');
        this.actionIcon = document.getElementById('action-icon');
        this.actionType = document.getElementById('action-type');
        this.actionTitle = document.getElementById('action-title');
        this.actionDetail = document.getElementById('action-detail');
        this.actionProgress = document.getElementById('action-progress');
        this.actionEmbed = document.getElementById('action-embed-container');
        this.actionCloseBtn = document.getElementById('action-close-btn');

        this.speechFloater = document.getElementById('holo-speech-floater');
        this.holoResponseText = document.getElementById('holo-response-text');
        this.coreTrigger = document.getElementById('core-trigger');

        // Command Dock & Inputs
        this.chatForm = document.getElementById('chat-form');
        this.chatInput = document.getElementById('chat-input');
        this.micDockBtn = document.getElementById('mic-dock-btn');
        this.sendDockBtn = document.getElementById('send-dock-btn');
        this.voiceTestBtn = document.getElementById('voice-test-btn');
        this.stateText = document.getElementById('state-text');
        this.eqBars = document.querySelectorAll('#eq-bars .eq-bar');

        // Settings Modal
        this.settingsBtn = document.getElementById('settings-btn');
        this.settingsModal = document.getElementById('settings-modal');
        this.settingsBackdrop = document.getElementById('settings-backdrop');
        this.settingsCloseBtn = document.getElementById('settings-close-btn');
        this.settingsSaveBtn = document.getElementById('settings-save-btn');
        this.groqKeyInput = document.getElementById('groq-api-key');
        this.voiceSelect = document.getElementById('voice-select');
        this.sfxToggle = document.getElementById('sfx-toggle');

        // Audio & Speech
        this.audioCtx = null;
        this.recognition = null;
        this.isListening = false;
        this.isSpeaking = false;
        this.silenceTimer = null;
        this.selectedVoice = null;
        this.sfxEnabled = true;

        // Mouse Parallax Physics
        this.mouse = { x: 0, y: 0, targetX: 0, targetY: 0 };

        // Three.js Core Objects
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.composer = null;
        this.clock = new THREE.Clock();
        this.coreGroup = null;
        this.plasmaSphere = null;
        this.plasmaMaterial = null;
        this.acousticWaveLine = null;
        this.particles = null;
        this.audioLevel = 0.0;

        // Conversation History
        this.history = [];
        this.notes = JSON.parse(localStorage.getItem('cheeku_demo_notes') || '[]');
        this.groqApiKey = localStorage.getItem('cheeku_groq_api_key') || '';

        this.init();
    }

    async init() {
        this.initThree();
        this.initPostProcessing();
        this.createFluidCore();
        this.createMiddleMusicWaves();
        this.createStarfield();
        this.initAudioContext();
        this.initSpeechRecognition();
        this.initSpeechSynthesis();
        this.initEvents();
        this.animate();
        this.runBootSequence();
    }

    /* ==========================================================================
       THREE.JS SCENE SETUP & SHADERS
       ========================================================================== */
    initThree() {
        this.scene = new THREE.Scene();
        this.scene.fog = new THREE.FogExp2(0x02040a, 0.045);

        const aspect = window.innerWidth / window.innerHeight;
        this.camera = new THREE.PerspectiveCamera(52, aspect, 0.1, 1000);
        this.camera.position.set(0, 0, 4.8);

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

        // Ambient Lights
        const ambLight = new THREE.AmbientLight(0x0f172a, 1.2);
        this.scene.add(ambLight);

        const dirLight = new THREE.DirectionalLight(0x38bdf8, 2.0);
        dirLight.position.set(5, 8, 5);
        this.scene.add(dirLight);

        const purpleLight = new THREE.PointLight(0x818cf8, 3.0, 50);
        purpleLight.position.set(-6, -4, 2);
        this.scene.add(purpleLight);
    }

    initPostProcessing() {
        if (!THREE.EffectComposer || !THREE.UnrealBloomPass) return;
        const renderPass = new THREE.RenderPass(this.scene, this.camera);
        this.bloomPass = new THREE.UnrealBloomPass(
            new THREE.Vector2(window.innerWidth, window.innerHeight),
            1.25,  // strength
            0.55,  // radius
            0.22   // threshold
        );

        this.composer = new THREE.EffectComposer(this.renderer);
        this.composer.addPass(renderPass);
        this.composer.addPass(this.bloomPass);
    }

    createFluidCore() {
        this.coreGroup = new THREE.Group();
        this.scene.add(this.coreGroup);

        // Procedural GLSL Simplex Noise Shader for liquid deformation
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
                float n1 = snoise(position * 2.2 + vec3(uTime * 0.75));
                float n2 = snoise(position * 4.4 - vec3(uTime * 1.1)) * 0.4;
                float noise = n1 + n2;
                vNoise = noise;
                
                float audioAmp = 0.12 + (uAudio * 0.45);
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
                float fresnel = pow(1.0 - abs(dot(normal, vec3(0.0, 0.0, 1.0))), 2.0);
                vec3 baseColor = mix(uColorA, uColorB, vNoise * 0.45 + 0.55);
                vec3 softGlow = uColorA * (fresnel * 0.45 + uAudio * 0.4);
                vec3 finalColor = baseColor + softGlow;
                gl_FragColor = vec4(finalColor, 0.94);
            }
        `;

        this.plasmaMaterial = new THREE.ShaderMaterial({
            vertexShader,
            fragmentShader,
            uniforms: {
                uTime: { value: 0 },
                uAudio: { value: 0 },
                uDisplacement: { value: 1.0 },
                uColorA: { value: new THREE.Color(0x38bdf8) }, // Azure cyan
                uColorB: { value: new THREE.Color(0x818cf8) }  // Soft indigo
            },
            transparent: true,
            blending: THREE.NormalBlending
        });

        const sphereGeo = new THREE.SphereGeometry(0.92, 72, 72);
        this.plasmaSphere = new THREE.Mesh(sphereGeo, this.plasmaMaterial);
        this.coreGroup.add(this.plasmaSphere);
    }

    createMiddleMusicWaves() {
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

    createStarfield() {
        const particleCount = 2400;
        const positions = new Float32Array(particleCount * 3);
        const colors = new Float32Array(particleCount * 3);

        const colorCyan = new THREE.Color(0x38bdf8);
        const colorPurple = new THREE.Color(0x818cf8);
        const colorWhite = new THREE.Color(0xffffff);

        for (let i = 0; i < particleCount; i++) {
            const r = 2.2 + Math.random() * 22.0;
            const theta = Math.random() * Math.PI * 2;
            const phi = Math.acos(2.0 * Math.random() - 1.0);

            positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
            positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
            positions[i * 3 + 2] = r * Math.cos(phi);

            const mixed = Math.random() < 0.5 ? colorCyan : (Math.random() < 0.8 ? colorPurple : colorWhite);
            colors[i * 3] = mixed.r;
            colors[i * 3 + 1] = mixed.g;
            colors[i * 3 + 2] = mixed.b;
        }

        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

        const material = new THREE.PointsMaterial({
            size: 0.035,
            vertexColors: true,
            transparent: true,
            opacity: 0.75,
            blending: THREE.AdditiveBlending
        });

        this.particles = new THREE.Points(geometry, material);
        this.scene.add(this.particles);
    }

    /* ==========================================================================
       BOOT SEQUENCE CHOREOGRAPHY
       ========================================================================== */
    runBootSequence() {
        const overlay = document.getElementById('boot-overlay');
        const fill = document.getElementById('boot-bar-fill');
        const status = document.getElementById('boot-status');

        if (fill) fill.style.width = '45%';
        setTimeout(() => {
            if (status) status.innerText = 'SYNAPSE ONLINE // READY';
            if (fill) fill.style.width = '100%';
            this.playChime('ready');
        }, 600);

        setTimeout(() => {
            if (overlay) overlay.classList.add('boot-done');
            this.setState('READY', 'Cheeku Neural Core Online 💖');
        }, 1100);
    }

    /* ==========================================================================
       SYNTHESIZED WEB AUDIO SOUND CHIMES
       ========================================================================== */
    initAudioContext() {
        try {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (AudioContext) {
                this.audioCtx = new AudioContext();
            }
        } catch (e) {
            console.warn('Web Audio not supported:', e);
        }
    }

    playChime(type) {
        if (!this.sfxEnabled || !this.audioCtx) return;
        if (this.audioCtx.state === 'suspended') {
            this.audioCtx.resume();
        }

        const now = this.audioCtx.currentTime;
        const osc = this.audioCtx.createOscillator();
        const gain = this.audioCtx.createGain();
        osc.connect(gain);
        gain.connect(this.audioCtx.destination);

        if (type === 'activate') {
            // Rising sci-fi blip
            osc.type = 'sine';
            osc.frequency.setValueAtTime(440, now);
            osc.frequency.exponentialRampToValueAtTime(880, now + 0.15);
            gain.gain.setValueAtTime(0.08, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.18);
            osc.start(now);
            osc.stop(now + 0.18);
        } else if (type === 'deactivate') {
            // Falling soft blip
            osc.type = 'sine';
            osc.frequency.setValueAtTime(740, now);
            osc.frequency.exponentialRampToValueAtTime(360, now + 0.12);
            gain.gain.setValueAtTime(0.06, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.14);
            osc.start(now);
            osc.stop(now + 0.14);
        } else if (type === 'action') {
            // High-tech affirmative dual chord
            osc.type = 'triangle';
            osc.frequency.setValueAtTime(523.25, now); // C5
            osc.frequency.setValueAtTime(659.25, now + 0.08); // E5
            osc.frequency.setValueAtTime(783.99, now + 0.16); // G5
            gain.gain.setValueAtTime(0.06, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
            osc.start(now);
            osc.stop(now + 0.35);
        } else if (type === 'ready') {
            // Soft boot chime
            osc.type = 'sine';
            osc.frequency.setValueAtTime(330, now);
            osc.frequency.exponentialRampToValueAtTime(660, now + 0.3);
            gain.gain.setValueAtTime(0.07, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.45);
            osc.start(now);
            osc.stop(now + 0.45);
        }
    }

    /* ==========================================================================
       SPEECH RECOGNITION (STT)
       ========================================================================== */
    initSpeechRecognition() {
        const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRec) {
            console.warn('Web Speech Recognition not supported in this browser.');
            return;
        }

        this.recognition = new SpeechRec();
        this.recognition.continuous = false;
        this.recognition.interimResults = true;
        this.recognition.lang = 'en-US';

        this.recognition.onstart = () => {
            this.isListening = true;
            this.setState('LISTENING', 'Listening...');
            this.showTranscript('Listening to your voice...');
            this.playChime('activate');
        };

        this.recognition.onresult = (event) => {
            let interim = '';
            let finalTranscript = '';

            for (let i = event.resultIndex; i < event.results.length; ++i) {
                if (event.results[i].isFinal) {
                    finalTranscript += event.results[i][0].transcript;
                } else {
                    interim += event.results[i][0].transcript;
                }
            }

            const current = finalTranscript || interim;
            if (current) {
                this.showTranscript(current);
                this.audioLevel = 0.5 + Math.random() * 0.4;
            }

            if (finalTranscript) {
                this.processUserInput(finalTranscript.trim());
            }
        };

        this.recognition.onerror = (event) => {
            console.warn('Speech recognition notice:', event.error);
            if (event.error === 'not-allowed') {
                this.showTranscript('⚠️ Microphone access blocked. Please type below.');
            }
            this.stopListening();
        };

        this.recognition.onend = () => {
            this.isListening = false;
            if (this.state === 'LISTENING') {
                this.setState('READY', 'Ready');
                this.hideTranscript();
            }
        };
    }

    toggleListening() {
        if (!this.recognition) {
            alert('Voice input is not supported in this browser. Please type your message into the dock.');
            return;
        }

        if (this.isListening) {
            this.stopListening();
        } else {
            this.startListening();
        }
    }

    startListening() {
        if (this.isSpeaking) {
            window.speechSynthesis.cancel();
            this.isSpeaking = false;
        }
        try {
            this.recognition.start();
        } catch (e) {
            // Already started
        }
    }

    stopListening() {
        if (this.recognition && this.isListening) {
            try {
                this.recognition.stop();
            } catch (e) {}
            this.playChime('deactivate');
        }
        this.isListening = false;
        this.hideTranscript();
    }

    showTranscript(text) {
        if (this.transcriptBar && this.transcriptText) {
            this.transcriptText.innerText = text;
            this.transcriptBar.classList.remove('hidden');
        }
    }

    hideTranscript() {
        if (this.transcriptBar) {
            setTimeout(() => {
                this.transcriptBar.classList.add('hidden');
            }, 1200);
        }
    }

    /* ==========================================================================
       SPEECH SYNTHESIS (TTS)
       ========================================================================== */
    initSpeechSynthesis() {
        if (!window.speechSynthesis) return;

        const populateVoices = () => {
            const voices = window.speechSynthesis.getVoices();
            if (!this.voiceSelect) return;
            this.voiceSelect.innerHTML = '';

            voices.forEach((v, idx) => {
                const opt = document.createElement('option');
                opt.value = v.name;
                opt.textContent = `${v.name} (${v.lang})`;
                if (v.lang.startsWith('en') && (v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('Samantha') || v.name.includes('Ava'))) {
                    opt.selected = true;
                    this.selectedVoice = v;
                }
                this.voiceSelect.appendChild(opt);
            });

            if (!this.selectedVoice && voices.length > 0) {
                this.selectedVoice = voices[0];
            }
        };

        populateVoices();
        if (window.speechSynthesis.onvoiceschanged !== undefined) {
            window.speechSynthesis.onvoiceschanged = populateVoices;
        }
    }

    speak(text) {
        if (!window.speechSynthesis) return;
        window.speechSynthesis.cancel();

        const utterance = new SpeechSynthesisUtterance(text);
        if (this.selectedVoice) {
            utterance.voice = this.selectedVoice;
        }
        utterance.rate = 1.02;
        utterance.pitch = 1.05;

        utterance.onstart = () => {
            this.isSpeaking = true;
            this.setState('SPEAKING', 'Speaking...');
            this.startSpeakingAnimation();
        };

        utterance.onend = () => {
            this.isSpeaking = false;
            this.audioLevel = 0.0;
            this.setState('READY', 'Ready');
        };

        utterance.onerror = () => {
            this.isSpeaking = false;
            this.audioLevel = 0.0;
            this.setState('READY', 'Ready');
        };

        window.speechSynthesis.speak(utterance);
    }

    startSpeakingAnimation() {
        if (!this.isSpeaking) return;
        // Modulate audioLevel to animate the 3D core & EQ bars
        this.audioLevel = 0.35 + Math.sin(Date.now() * 0.015) * 0.3 + Math.random() * 0.25;

        if (this.eqBars) {
            this.eqBars.forEach((bar, i) => {
                const h = 4 + Math.random() * 12;
                bar.style.height = `${h}px`;
            });
        }

        requestAnimationFrame(() => {
            if (this.isSpeaking) this.startSpeakingAnimation();
            else {
                if (this.eqBars) this.eqBars.forEach(b => b.style.height = '3px');
            }
        });
    }

    /* ==========================================================================
       AUTONOMOUS NEURAL BRAIN (BUILT-IN ENGINE + OPTIONAL LIVE GROQ)
       ========================================================================== */
    async processUserInput(rawText) {
        if (!rawText || !rawText.trim()) return;
        const text = rawText.trim();
        this.stopListening();
        this.setState('THINKING', 'Consulting Cheeku Brain...');

        // If user has provided a Groq API key in Settings, use live Groq Cloud
        if (this.groqApiKey) {
            try {
                await this.callGroqApi(text);
                return;
            } catch (err) {
                console.warn('Groq live API call failed, falling back to built-in brain:', err);
            }
        }

        // Fast, high-fidelity built-in neural reasoning
        setTimeout(() => {
            this.executeBuiltinBrain(text);
        }, 450);
    }

    async callGroqApi(userText) {
        this.history.push({ role: 'user', content: userText });
        const systemPrompt = `You are Cheeku, an advanced, charming, and hyper-capable AI voice assistant. Keep responses concise, warm, witty, and spoken-friendly (2-3 sentences max).`;

        const response = await fetch('https://api.groq.com/openai/v1/chat/completions', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.groqApiKey}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                model: 'llama-3.3-70b-versatile',
                messages: [
                    { role: 'system', content: systemPrompt },
                    ...this.history.slice(-6)
                ],
                max_tokens: 150,
                temperature: 0.7
            })
        });

        if (!response.ok) {
            throw new Error(`Groq API returned ${response.status}`);
        }

        const data = await response.json();
        const reply = data.choices?.[0]?.message?.content || "I processed that, but had trouble articulating it.";
        this.history.push({ role: 'assistant', content: reply });
        this.showSpeechFloater(reply);
        this.speak(reply);
    }

    executeBuiltinBrain(text) {
        const query = text.toLowerCase();
        let reply = '';

        // 1. YouTube & Music Tool Directive
        if (query.includes('play') || query.includes('music') || query.includes('song') || query.includes('synthwave') || query.includes('lofi')) {
            const track = query.replace(/play|music|song|on youtube/gi, '').trim() || 'Synthwave Cyber Chill Beats';
            this.showActionHud('🎵', 'SYSTEM DIRECTIVE', 'STREAMING AUDIO TRACK', `"${track}"`, () => {
                window.open(`https://www.youtube.com/results?search_query=${encodeURIComponent(track)}`, '_blank');
            });
            reply = `Playing ${track} for you now. Turn up the volume!`;
        }
        // 2. System Hardware Vitals Directive
        else if (query.includes('vital') || query.includes('system') || query.includes('cpu') || query.includes('ram') || query.includes('spec')) {
            const cpu = Math.floor(10 + Math.random() * 25);
            const ram = (2.8 + Math.random() * 0.8).toFixed(1);
            this.showActionHud('📊', 'HARDWARE TELEMETRY', 'CORE DIAGNOSTICS COMPLETED', `CPU Load: ${cpu}% | RAM: ${ram} GB / 16.0 GB | FPS: 60 | Status: Nominal`);
            reply = `System vitals are running nominal. CPU utilization is sitting at ${cpu} percent and memory allocation is ${ram} gigabytes.`;
        }
        // 3. Notes & Memory Directive
        else if (query.includes('note') || query.includes('remember') || query.includes('save')) {
            const noteContent = text.replace(/save note|remember to|take a note|add note|remember that|note/gi, '').trim() || 'Important task saved to Cheeku memory';
            this.notes.push({ text: noteContent, date: new Date().toLocaleTimeString() });
            localStorage.setItem('cheeku_demo_notes', JSON.stringify(this.notes));
            this.showActionHud('📝', 'MEMORY WRITE', 'QUICK NOTE COMMITTED', `"${noteContent}"`);
            reply = `Noted! I've committed "${noteContent}" to permanent neural memory.`;
        }
        // 4. Identity & Introduction
        else if (query.includes('who are you') || query.includes('what are you') || query.includes('about yourself') || query.includes('your name')) {
            reply = "I'm Cheeku, your event-driven neural voice OS assistant. I feature an asynchronous FSM, Three.js WebGL fluid shaders, and instant tool calling.";
        }
        // 5. Capabilities
        else if (query.includes('what can you do') || query.includes('capabilities') || query.includes('help') || query.includes('tools')) {
            reply = "I can stream YouTube music, inspect hardware vitals, write memory notes, answer queries, and chat with real-time voice speech!";
        }
        // 6. Joke
        else if (query.includes('joke') || query.includes('funny') || query.includes('laugh')) {
            const jokes = [
                "Why do programmers prefer dark mode? Because light attracts bugs!",
                "There are 10 types of people in the world: those who understand binary, and those who don't.",
                "Why did the neural network cross the road? To optimize its loss function on the other side!",
                "A SQL query walks into a bar, walks up to two tables and asks: 'Can I join you?'"
            ];
            reply = jokes[Math.floor(Math.random() * jokes.length)];
        }
        // 7. General Friendly Conversational Responses
        else if (query.includes('hello') || query.includes('hi') || query.includes('hey')) {
            reply = "Greetings! All neural synapses are operating at peak efficiency. What directive shall we run?";
        }
        else if (query.includes('thank')) {
            reply = "You're very welcome! Always at your service.";
        }
        else {
            reply = `Acknowledged: "${text}". I have logged the directive and am ready for your next request!`;
        }

        this.showSpeechFloater(reply);
        this.speak(reply);
    }

    /* ==========================================================================
       HOLOGRAPHIC ACTION HUD & FLOATER
       ========================================================================== */
    showActionHud(icon, type, title, detail, onClickAction) {
        this.playChime('action');
        if (this.actionIcon) this.actionIcon.innerText = icon;
        if (this.actionType) this.actionType.innerText = type;
        if (this.actionTitle) this.actionTitle.innerText = title;
        if (this.actionDetail) this.actionDetail.innerText = detail;

        if (this.actionProgress) {
            this.actionProgress.style.width = '0%';
            setTimeout(() => { this.actionProgress.style.width = '100%'; }, 50);
        }

        if (this.actionHud) {
            this.actionHud.classList.remove('hidden');
        }

        if (onClickAction) {
            this.actionCard = document.querySelector('.action-card');
            if (this.actionCard) {
                this.actionCard.style.cursor = 'pointer';
                this.actionCard.onclick = () => {
                    onClickAction();
                    this.actionCard.onclick = null;
                    this.actionCard.style.cursor = 'default';
                };
            }
        }
    }

    hideActionHud() {
        if (this.actionHud) {
            this.actionHud.classList.add('hidden');
        }
    }

    showSpeechFloater(text) {
        if (this.holoResponseText) {
            this.holoResponseText.innerText = text;
        }
        if (this.speechFloater) {
            this.speechFloater.classList.remove('hidden');
        }
    }

    hideSpeechFloater() {
        if (this.speechFloater) {
            this.speechFloater.classList.add('hidden');
        }
    }

    /* ==========================================================================
       STATE MACHINE MANAGEMENT
       ========================================================================== */
    setState(state, details) {
        this.state = state;
        document.body.className = `state-${state.toLowerCase()}`;
        if (this.stateText) {
            this.stateText.innerText = state;
        }

        // Adjust 3D Core Color & Displacement based on FSM State
        if (this.plasmaMaterial) {
            const uColorA = this.plasmaMaterial.uniforms.uColorA.value;
            const uColorB = this.plasmaMaterial.uniforms.uColorB.value;

            if (state === 'LISTENING') {
                uColorA.setHex(0x2dd4bf); // Teal
                uColorB.setHex(0x0284c7);
            } else if (state === 'THINKING') {
                uColorA.setHex(0x818cf8); // Indigo/Purple
                uColorB.setHex(0xc084fc);
            } else if (state === 'SPEAKING') {
                uColorA.setHex(0x38bdf8); // Sky Cyan
                uColorB.setHex(0xf43f5e); // Rose Accent
            } else {
                uColorA.setHex(0x38bdf8); // Calm Azure
                uColorB.setHex(0x818cf8);
            }
        }
    }

    /* ==========================================================================
       USER INTERACTION EVENTS
       ========================================================================== */
    initEvents() {
        // Spacebar to talk
        window.addEventListener('keydown', (e) => {
            if (e.code === 'Space' && document.activeElement !== this.chatInput) {
                e.preventDefault();
                this.toggleListening();
            }
        });

        // Click 3D Core to talk
        if (this.coreTrigger) {
            this.coreTrigger.addEventListener('click', () => {
                this.toggleListening();
            });
        }

        // Mic Button
        if (this.micDockBtn) {
            this.micDockBtn.addEventListener('click', () => {
                this.toggleListening();
            });
        }

        // Chat Form Submit
        if (this.chatForm) {
            this.chatForm.addEventListener('submit', (e) => {
                e.preventDefault();
                const text = this.chatInput.value;
                if (text && text.trim()) {
                    this.chatInput.value = '';
                    this.processUserInput(text);
                }
            });
        }

        // Action HUD Dismiss
        if (this.actionCloseBtn) {
            this.actionCloseBtn.addEventListener('click', () => {
                this.hideActionHud();
            });
        }

        // Test Voice Button
        if (this.voiceTestBtn) {
            this.voiceTestBtn.addEventListener('click', () => {
                this.playChime('action');
                this.speak("Cheeku neural voice engine is operating smoothly.");
            });
        }

        // Prompt Chips Click
        const chips = document.querySelectorAll('.prompt-chip');
        chips.forEach(chip => {
            chip.addEventListener('click', () => {
                const query = chip.getAttribute('data-query');
                if (query) {
                    this.processUserInput(query);
                }
            });
        });

        // Settings Modal Events
        if (this.settingsBtn) {
            this.settingsBtn.addEventListener('click', () => {
                if (this.groqKeyInput) this.groqKeyInput.value = this.groqApiKey;
                if (this.sfxToggle) this.sfxToggle.checked = this.sfxEnabled;
                this.settingsModal.classList.remove('hidden');
            });
        }

        const closeSettings = () => {
            this.settingsModal.classList.add('hidden');
        };

        if (this.settingsCloseBtn) this.settingsCloseBtn.addEventListener('click', closeSettings);
        if (this.settingsBackdrop) this.settingsBackdrop.addEventListener('click', closeSettings);

        if (this.settingsSaveBtn) {
            this.settingsSaveBtn.addEventListener('click', () => {
                if (this.groqKeyInput) {
                    this.groqApiKey = this.groqKeyInput.value.trim();
                    localStorage.setItem('cheeku_groq_api_key', this.groqApiKey);
                }
                if (this.sfxToggle) {
                    this.sfxEnabled = this.sfxToggle.checked;
                }
                if (this.voiceSelect && window.speechSynthesis) {
                    const voices = window.speechSynthesis.getVoices();
                    this.selectedVoice = voices.find(v => v.name === this.voiceSelect.value) || this.selectedVoice;
                }
                closeSettings();
                this.playChime('action');
            });
        }

        // Mouse Move for Parallax
        window.addEventListener('mousemove', (e) => {
            this.mouse.targetX = (e.clientX / window.innerWidth - 0.5) * 2;
            this.mouse.targetY = -(e.clientY / window.innerHeight - 0.5) * 2;
        });

        // Resize Listener
        window.addEventListener('resize', () => {
            if (!this.camera || !this.renderer) return;
            this.camera.aspect = window.innerWidth / window.innerHeight;
            this.camera.updateProjectionMatrix();
            this.renderer.setSize(window.innerWidth, window.innerHeight);
            if (this.composer) {
                this.composer.setSize(window.innerWidth, window.innerHeight);
            }
        });
    }

    /* ==========================================================================
       ANIMATION RENDER LOOP
       ========================================================================== */
    animate() {
        requestAnimationFrame(() => this.animate());

        const delta = this.clock.getDelta();
        const elapsedTime = this.clock.getElapsedTime();

        // Smooth Mouse Parallax
        this.mouse.x += (this.mouse.targetX - this.mouse.x) * 0.05;
        this.mouse.y += (this.mouse.targetY - this.mouse.y) * 0.05;

        // Animate Fluid Core Shaders
        if (this.plasmaMaterial) {
            this.plasmaMaterial.uniforms.uTime.value = elapsedTime;
            this.plasmaMaterial.uniforms.uAudio.value = this.audioLevel;
        }

        // Rotate Core & Starfield gently
        if (this.coreGroup) {
            this.coreGroup.rotation.y = elapsedTime * 0.18 + (this.mouse.x * 0.3);
            this.coreGroup.rotation.x = this.mouse.y * 0.2;
        }

        if (this.particles) {
            this.particles.rotation.y = elapsedTime * 0.02;
            this.particles.rotation.x = elapsedTime * 0.01;
        }

        // Animate Acoustic Wave Ribbon
        if (this.acousticWaveLine) {
            const positions = this.acousticWaveLine.geometry.attributes.position.array;
            for (let i = 0; i < this.wavePoints; i++) {
                const x = (i / (this.wavePoints - 1) - 0.5) * 3.6;
                const waveAmp = 0.06 + (this.audioLevel * 0.35);
                const y = Math.sin(x * 4.5 + elapsedTime * 3.5) * waveAmp;
                positions[i * 3] = x;
                positions[i * 3 + 1] = y;
                positions[i * 3 + 2] = 0;
            }
            this.acousticWaveLine.geometry.attributes.position.needsUpdate = true;
        }

        // Render with Bloom or Fallback
        if (this.composer) {
            this.composer.render();
        } else if (this.renderer && this.scene && this.camera) {
            this.renderer.render(this.scene, this.camera);
        }
    }
}

// Instantiate on DOM Loaded
document.addEventListener('DOMContentLoaded', () => {
    window.cheekuDemo = new CheekuDemo();
});
