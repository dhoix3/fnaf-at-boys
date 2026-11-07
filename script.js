/* =========================================
   FIVE NIGHTS AT THE BOYS' — FNaF 1 Style
   Game Logic (Vanilla JS)
   ========================================= */

(function() {
    'use strict';

    // ------------------------------------------------------------------
    // Audio System (Web Audio API synthesized)
    // ------------------------------------------------------------------
    const AudioSys = (() => {
        let ctx = null;
        const ensureCtx = () => {
            if (!ctx) {
                const Ctx = window.AudioContext || window.webkitAudioContext;
                ctx = new Ctx();
            }
            return ctx;
        };

        const playTone = (freq, type, duration, vol = 0.1, when = 0) => {
            const c = ensureCtx();
            const t = c.currentTime + when;
            const o = c.createOscillator();
            const g = c.createGain();
            o.type = type;
            o.frequency.setValueAtTime(freq, t);
            g.gain.setValueAtTime(vol, t);
            g.gain.exponentialRampToValueAtTime(0.001, t + duration);
            o.connect(g);
            g.connect(c.destination);
            o.start(t);
            o.stop(t + duration);
        };

        const playNoise = (duration, vol = 0.05) => {
            const c = ensureCtx();
            const bufferSize = c.sampleRate * duration;
            const buffer = c.createBuffer(1, bufferSize, c.sampleRate);
            const data = buffer.getChannelData(0);
            for (let i = 0; i < bufferSize; i++) data[i] = Math.random() * 2 - 1;
            const source = c.createBufferSource();
            source.buffer = buffer;
            const g = c.createGain();
            g.gain.setValueAtTime(vol, c.currentTime);
            source.connect(g);
            g.connect(c.destination);
            source.start();
            source.stop(c.currentTime + duration);
        };

        const playDoor = () => {
            // Heavy metallic clang
            playTone(80, 'sawtooth', 0.2, 0.3);
            setTimeout(() => playTone(120, 'square', 0.15, 0.2), 50);
            setTimeout(() => playNoise(0.3, 0.2), 100);
        };

        const playLight = () => playTone(900, 'square', 0.08, 0.1);

        const playJumpscare = () => {
            playNoise(2, 0.4);
            for (let i = 0; i < 12; i++) {
                setTimeout(() => playTone(50 + i * 30, 'sawtooth', 0.3, 0.4), i * 80);
            }
        };

        const playPowerOut = () => {
            playTone(60, 'sawtooth', 3, 0.25);
            setTimeout(() => playTone(45, 'sawtooth', 3, 0.25), 1500);
            setTimeout(() => playTone(55, 'sawtooth', 3, 0.25), 3000);
        };

        const playFoxySteps = () => {
            playTone(100, 'square', 0.1, 0.2);
            setTimeout(() => playTone(80, 'square', 0.1, 0.25), 200);
            setTimeout(() => playTone(60, 'square', 0.15, 0.3), 400);
        };

        return { playDoor, playLight, playJumpscare, playPowerOut, playFoxySteps, playNoise, ensureCtx };
    })();

    // ------------------------------------------------------------------
    // Image Helper with Fallback
    // ------------------------------------------------------------------
    const setupImageFallback = (imgEl, fallbackText) => {
        imgEl.onerror = () => {
            imgEl.style.display = 'none';
            const wrap = imgEl.parentElement;
            if (wrap) {
                const fb = document.createElement('div');
                fb.className = 'fallback-img';
                fb.textContent = fallbackText;
                wrap.appendChild(fb);
            }
        };
    };

    // ------------------------------------------------------------------
    // Game State
    // ------------------------------------------------------------------
    const state = {
        running: false,
        started: false,
        timeHour: 12,
        timeMinute: 0,
        timeSecond: 0,
        power: 100,
        powerOut: false,
        cameraOpen: false,
        currentCam: '1A',

        doors: { left: false, right: false },
        lights: { left: false, right: false },

        freddy: '1A',
        bonnie: '1A',
        chica: '4A',
        foxy: '1C',

        foxyLastCheck: Date.now(),
        foxyRunning: false,
        foxyRunDeadline: null,

        bonnieAtLeftDoorSince: null,
        chicaAtRightDoorSince: null,
        freddyAtLeftDoorSince: null,

        goldenActive: false,
        goldenShowTime: null,
        goldenDeadline: null,

        tickId: null,
        powerId: null,
        aiId: null,
        goldenId: null,

        eyeBlinkTimer: null,
    };

    // ------------------------------------------------------------------
    // DOM Refs
    // ------------------------------------------------------------------
    const $ = (id) => document.getElementById(id);
    const els = {
        office: $('office'),
        powerFill: $('power-fill'),
        powerText: $('power-text'),
        timeDisplay: $('time-display'),
        doorLeft: $('door-left'),
        doorRight: $('door-right'),
        lightLeft: $('light-left'),
        lightRight: $('light-right'),
        cameraBtn: $('camera-btn'),
        cameraView: $('camera-view'),
        charLeft: $('char-left'),
        charRight: $('char-right'),
        charLeftImg: $('char-left-img'),
        charRightImg: $('char-right-img'),
        eyesLeft: $('eyes-left'),
        eyesRight: $('eyes-right'),
        goldenFreddy: $('golden-freddy'),
        gfImg: $('gf-img'),
        powerOut: $('power-out'),
        jumpscare: $('jumpscare'),
        jsImg: $('js-img'),
        jsFallback: $('js-fallback'),
        jsText: $('js-text'),
        gameOver: $('game-over'),
        winScreen: $('win-screen'),
        goTitle: $('go-title'),
        goSub: $('go-sub'),
        feedCam: $('feed-cam'),
        startBtn: $('start-btn'),
        audioUnlock: $('audio-unlock'),
    };

    // ------------------------------------------------------------------
    // Initialization
    // ------------------------------------------------------------------
    function init() {
        ['char-left-img', 'char-right-img', 'gf-img',
         'cam-img-1A','cam-img-1B','cam-img-2A','cam-img-4A','cam-img-1C'].forEach(id => {
            const el = $(id);
            if (el) {
                const fallback = id.includes('char-left') ? 'PHOTO 2' :
                                 id.includes('char-right') ? 'PHOTO 3' :
                                 id === 'gf-img' ? 'PHOTO 5' :
                                 id.includes('1A') ? 'PHOTO 1' :
                                 id.includes('1B') ? 'PHOTO 1' :
                                 id.includes('2A') ? 'PHOTO 2' :
                                 id.includes('4A') ? 'PHOTO 3' : 'PHOTO 4';
                setupImageFallback(el, fallback);
            }
        });

        setupImageFallback(els.jsImg, 'PHOTO X');

        els.doorLeft.addEventListener('click', () => toggleDoor('left'));
        els.doorRight.addEventListener('click', () => toggleDoor('right'));
        els.lightLeft.addEventListener('click', () => toggleLight('left'));
        els.lightRight.addEventListener('click', () => toggleLight('right'));
        els.cameraBtn.addEventListener('click', toggleCamera);

        document.querySelectorAll('.cam-room-btn').forEach(btn => {
            btn.addEventListener('click', () => selectCam(btn.dataset.cam));
        });

        $('go-restart').addEventListener('click', restartGame);
        $('win-restart').addEventListener('click', restartGame);

        els.startBtn.addEventListener('click', () => {
            els.audioUnlock.classList.add('hidden');
            AudioSys.ensureCtx();
            startGame();
        });

        updateUI();
        startEyeBlink();
    }

    function startEyeBlink() {
        els.eyeBlinkTimer = setInterval(() => {
            if (!state.running || state.powerOut) return;
            [els.eyesLeft, els.eyesRight].forEach(eyeContainer => {
                const eyes = eyeContainer.querySelectorAll('.eye');
                eyes.forEach(eye => {
                    eye.classList.add('blink');
                    setTimeout(() => eye.classList.remove('blink'), 150);
                });
            });
        }, 3000);
    }

    // ------------------------------------------------------------------
    // Game Start / Restart
    // ------------------------------------------------------------------
    function startGame() {
        state.running = true;
        state.started = true;
        state.timeHour = 12;
        state.timeMinute = 0;
        state.timeSecond = 0;
        state.power = 100;
        state.powerOut = false;
        state.cameraOpen = false;
        state.currentCam = '1A';
        state.doors = { left: false, right: false };
        state.lights = { left: false, right: false };
        state.freddy = '1A';
        state.bonnie = '1A';
        state.chica = '4A';
        state.foxy = '1C';
        state.foxyLastCheck = Date.now();
        state.foxyRunning = false;
        state.foxyRunDeadline = null;
        state.bonnieAtLeftDoorSince = null;
        state.chicaAtRightDoorSince = null;
        state.freddyAtLeftDoorSince = null;
        state.goldenActive = false;
        state.goldenShowTime = null;
        state.goldenDeadline = null;

        els.cameraView.classList.add('hidden');
        els.gameOver.classList.add('hidden');
        els.winScreen.classList.add('hidden');
        els.jumpscare.classList.add('hidden');
        els.powerOut.classList.remove('visible');
        els.office.classList.remove('hidden');

        hideAllChars();
        updateUI();
        updateCameraFeed();

        clearInterval(state.tickId);
        clearInterval(state.powerId);
        clearInterval(state.aiId);
        clearInterval(state.goldenId);

        let tickCount = 0;
        state.tickId = setInterval(() => {
            if (!state.running || state.powerOut) return;
            tickCount++;
            state.timeSecond += 0.1;
            if (state.timeSecond >= 60) {
                state.timeSecond = 0;
                state.timeMinute = 0;
                state.timeHour++;
                if (state.timeHour > 6) {
                    winGame();
                    return;
                }
            }
            updateUI();
        }, 100);

        state.powerId = setInterval(() => {
            if (!state.running || state.powerOut) return;
            let drainPerSec = 1 / 9.6;
            if (state.doors.left) drainPerSec += 1;
            if (state.doors.right) drainPerSec += 1;
            if (state.lights.left) drainPerSec += 1;
            if (state.lights.right) drainPerSec += 1;
            state.power -= drainPerSec * 0.1;
            if (state.power <= 0) {
                state.power = 0;
                triggerPowerOut();
            }
            updateUI();
        }, 100);

        state.aiId = setInterval(() => {
            if (!state.running || state.powerOut) return;
            runAI();
        }, 2000);

        state.goldenId = setInterval(() => {
            if (!state.running || state.powerOut || state.cameraOpen) return;
            if (Math.random() < 0.01) {
                spawnGoldenFreddy();
            }
        }, 5000);
    }

    function restartGame() {
        els.gameOver.classList.add('hidden');
        els.winScreen.classList.add('hidden');
        startGame();
    }

    function winGame() {
        state.running = false;
        clearInterval(state.tickId);
        clearInterval(state.powerId);
        clearInterval(state.aiId);
        clearInterval(state.goldenId);
        els.winScreen.classList.remove('hidden');
    }

    function triggerPowerOut() {
        state.powerOut = true;
        state.running = false;
        state.doors = { left: false, right: false };
        state.lights = { left: false, right: false };
        clearInterval(state.tickId);
        clearInterval(state.powerId);
        clearInterval(state.aiId);
        clearInterval(state.goldenId);
        AudioSys.playPowerOut();
        hideAllChars();
        els.powerOut.classList.add('visible');
        updateUI();

        setTimeout(() => {
            triggerJumpscare('freddy', 'FREDDY GETS YOU');
        }, 5000);
    }

    // ------------------------------------------------------------------
    // UI Toggles
    // ------------------------------------------------------------------
    function toggleDoor(side) {
        if (!state.running || state.powerOut || state.cameraOpen) return;
        state.doors[side] = !state.doors[side];
        AudioSys.playDoor();
        updateUI();
    }

    function toggleLight(side) {
        if (!state.running || state.powerOut || state.cameraOpen) return;
        state.lights[side] = !state.lights[side];
        AudioSys.playLight();
        updateUI();
    }

    function toggleCamera() {
        if (!state.running || state.powerOut) return;
        state.cameraOpen = !state.cameraOpen;
        if (state.cameraOpen) {
            els.cameraView.classList.remove('hidden');
            els.cameraBtn.classList.add('active');
            if (state.currentCam === '1C' && state.foxy === '1C') {
                state.foxyLastCheck = Date.now();
                state.foxyRunning = false;
                state.foxyRunDeadline = null;
            }
            if (state.goldenActive && state.goldenDeadline) {
                const now = Date.now();
                if (now - state.goldenShowTime <= 2000) {
                    dismissGoldenFreddy();
                } else {
                    triggerGoldenGlitch();
                }
            }
        } else {
            els.cameraView.classList.add('hidden');
            els.cameraBtn.classList.remove('active');
        }
        updateUI();
    }

    function selectCam(cam) {
        if (!state.running || state.powerOut) return;
        state.currentCam = cam;
        if (cam === '1C' && state.foxy === '1C') {
            state.foxyLastCheck = Date.now();
            state.foxyRunning = false;
            state.foxyRunDeadline = null;
        }
        updateCameraFeed();
        updateUI();
    }

    // ------------------------------------------------------------------
    // UI Update
    // ------------------------------------------------------------------
    function updateUI() {
        const pct = Math.max(0, Math.floor(state.power));
        els.powerText.textContent = pct + '%';
        els.powerFill.style.width = pct + '%';
        if (pct <= 30) {
            els.powerFill.classList.add('low');
        } else {
            els.powerFill.classList.remove('low');
        }

        const hour = state.timeHour === 12 ? 12 : state.timeHour;
        const min = Math.floor(state.timeMinute).toString().padStart(2, '0');
        els.timeDisplay.textContent = `${hour}:${min} AM`;

        setBtnActive(els.doorLeft, state.doors.left);
        setBtnActive(els.doorRight, state.doors.right);
        setBtnActive(els.lightLeft, state.lights.left);
        setBtnActive(els.lightRight, state.lights.right);
        setBtnActive(els.cameraBtn, state.cameraOpen);

        updateDoorways();
    }

    function setBtnActive(btn, active) {
        if (active) btn.classList.add('active');
        else btn.classList.remove('active');
    }

    function updateDoorways() {
        if (state.bonnie === 'LDoor') {
            showChar('left', 'bonnie');
        } else if (state.freddy === 'LDoor') {
            showChar('left', 'freddy');
        } else {
            hideChar('left');
        }

        if (state.chica === 'RDoor') {
            showChar('right', 'chica');
        } else {
            hideChar('right');
        }
    }

    function showChar(side, enemy) {
        const charDiv = side === 'left' ? els.charLeft : els.charRight;
        const imgEl = side === 'left' ? els.charLeftImg : els.charRightImg;
        const eyesDiv = side === 'left' ? els.eyesLeft : els.eyesRight;
        const fallbackText = enemy === 'bonnie' ? 'PHOTO 2' :
                             enemy === 'chica' ? 'PHOTO 3' : 'PHOTO 1';
        imgEl.textContent = fallbackText;

        // Apply dark filter if light is off
        const lightOn = side === 'left' ? state.lights.left : state.lights.right;
        if (!lightOn) {
            imgEl.classList.add('dark');
            createEyes(eyesDiv, true);
        } else {
            imgEl.classList.remove('dark');
            createEyes(eyesDiv, false);
        }

        charDiv.classList.remove('hidden');
        charDiv.classList.add('visible');
    }

    function createEyes(container, glowing) {
        container.innerHTML = '';
        const eye1 = document.createElement('div');
        const eye2 = document.createElement('div');
        eye1.className = 'eye';
        eye2.className = 'eye';
        if (!glowing) {
            eye1.style.opacity = '0.2';
            eye2.style.opacity = '0.2';
            eye1.style.boxShadow = 'none';
            eye2.style.boxShadow = 'none';
        }
        container.appendChild(eye1);
        container.appendChild(eye2);
    }

    function hideChar(side) {
        const charDiv = side === 'left' ? els.charLeft : els.charRight;
        charDiv.classList.remove('visible');
        setTimeout(() => charDiv.classList.add('hidden'), 400);
    }

    function hideAllChars() {
        hideChar('left');
        hideChar('right');
    }

    // ------------------------------------------------------------------
    // Camera Feed
    // ------------------------------------------------------------------
    function updateCameraFeed() {
        document.querySelectorAll('.cam-enemy').forEach(el => el.classList.remove('visible'));
        els.feedCam.textContent = state.currentCam;

        const roomMap = {
            '1A': state.freddy === '1A' ? 'cam-enemy-1A' :
                  state.bonnie === '1A' ? 'cam-enemy-1A' : null,
            '1B': state.freddy === '1B' ? 'cam-enemy-1B' : null,
            '2A': state.bonnie === '2A' ? 'cam-enemy-2A' : null,
            '4A': state.chica === '4A' ? 'cam-enemy-4A' : null,
            '1C': state.foxy === '1C' ? 'cam-enemy-1C' : null,
        };
        const target = roomMap[state.currentCam];
        if (target) {
            const el = $(target);
            if (el) el.classList.add('visible');
        }

        document.querySelectorAll('.cam-room-btn').forEach(btn => {
            if (btn.dataset.cam === state.currentCam) btn.classList.add('active');
            else btn.classList.remove('active');
        });
    }

    // ------------------------------------------------------------------
    // AI Movement Logic
    // ------------------------------------------------------------------
    function runAI() {
        // Freddy: Moves ONLY when camera is open OR closed (never when watching him on cam)
        if (state.freddy !== 'LDoor' && state.freddy !== 'office') {
            const roll = Math.random();
            // Freddy freezes if player is watching his current cam
            const watchingFreddy = state.cameraOpen && state.currentCam === state.freddy;
            if (!watchingFreddy) {
                if (state.freddy === '1A' && roll < 0.25) {
                    state.freddy = '1B';
                } else if (state.freddy === '1B' && roll < 0.25) {
                    state.freddy = Math.random() < 0.5 ? '2A' : '4A';
                } else if ((state.freddy === '2A' || state.freddy === '4A') && roll < 0.2) {
                    state.freddy = 'LDoor';
                    state.freddyAtLeftDoorSince = Date.now();
                }
            }
        }

        // Bonnie
        if (state.bonnie !== 'LDoor') {
            const roll = Math.random();
            if (state.bonnie === '1A' && roll < 0.35) {
                state.bonnie = '2A';
            } else if (state.bonnie === '2A' && roll < 0.35) {
                state.bonnie = 'LDoor';
                state.bonnieAtLeftDoorSince = Date.now();
            }
        }

        // Chica
        if (state.chica !== 'RDoor') {
            const roll = Math.random();
            if (state.chica === '4A' && roll < 0.35) {
                state.chica = 'RDoor';
                state.chicaAtRightDoorSince = Date.now();
            }
        }

        // Foxy
        if (state.foxy === '1C' && !state.foxyRunning && !state.foxyRunDeadline) {
            const sinceCheck = Date.now() - state.foxyLastCheck;
            if (sinceCheck >= 15000) {
                state.foxyRunning = true;
                state.foxyRunDeadline = Date.now() + 1500; // 1.5 seconds to react
                AudioSys.playFoxySteps();
            }
        }

        updateCameraFeed();
        updateDoorways();
        checkDoorThreats();
    }

    function checkDoorThreats() {
        const now = Date.now();

        // Bonnie at left door: door open for 3-5s -> jumpscare
        if (state.bonnie === 'LDoor' && !state.doors.left) {
            if (!state.bonnieAtLeftDoorSince) state.bonnieAtLeftDoorSince = now;
            const threatTime = 3000 + Math.random() * 2000; // 3-5 seconds
            if (now - state.bonnieAtLeftDoorSince >= threatTime) {
                triggerJumpscare('bonnie', 'BONNIE GETS YOU');
            }
        } else {
            state.bonnieAtLeftDoorSince = null;
        }

        // Chica at right door: door open for 3-5s -> jumpscare
        if (state.chica === 'RDoor' && !state.doors.right) {
            if (!state.chicaAtRightDoorSince) state.chicaAtRightDoorSince = now;
            const threatTime = 3000 + Math.random() * 2000;
            if (now - state.chicaAtRightDoorSince >= threatTime) {
                triggerJumpscare('chica', 'CHICA GETS YOU');
            }
        } else {
            state.chicaAtRightDoorSince = null;
        }

        // Freddy at left door: door open for 5s -> jumpscare
        if (state.freddy === 'LDoor' && !state.doors.left) {
            if (!state.freddyAtLeftDoorSince) state.freddyAtLeftDoorSince = now;
            if (now - state.freddyAtLeftDoorSince >= 5000) {
                triggerJumpscare('freddy', 'FREDDY GETS YOU');
            }
        } else if (state.freddy !== 'LDoor') {
            state.freddyAtLeftDoorSince = null;
        }

        // Foxy running: 1.5 seconds to close left door
        if (state.foxyRunning && state.foxyRunDeadline) {
            if (state.doors.left) {
                state.foxy = '1C';
                state.foxyRunning = false;
                state.foxyRunDeadline = null;
                state.foxyLastCheck = Date.now();
                state.power -= 5;
                if (state.power < 0) state.power = 0;
                updateUI();
            } else if (now >= state.foxyRunDeadline) {
                state.foxyRunning = false;
                state.foxyRunDeadline = null;
                triggerJumpscare('foxy', 'FOXY GETS YOU');
            }
        }
    }

    // ------------------------------------------------------------------
    // Golden Freddy (Enemy 5 - Secret)
    // ------------------------------------------------------------------
    function spawnGoldenFreddy() {
        state.goldenActive = true;
        state.goldenShowTime = Date.now();
        state.goldenDeadline = state.goldenShowTime + 2000;
        els.goldenFreddy.classList.add('visible');
    }

    function dismissGoldenFreddy() {
        state.goldenActive = false;
        state.goldenShowTime = null;
        state.goldenDeadline = null;
        els.goldenFreddy.classList.remove('visible');
    }

    function triggerGoldenGlitch() {
        state.goldenActive = false;
        state.goldenShowTime = null;
        state.goldenDeadline = null;
        els.goldenFreddy.classList.remove('visible');

        const glitch = document.createElement('div');
        glitch.className = 'glitch-overlay';
        document.body.appendChild(glitch);

        setTimeout(() => {
            document.body.removeChild(glitch);
            triggerJumpscare('golden', 'GOLDEN FREDDY GETS YOU');
        }, 1500);
    }

    // ------------------------------------------------------------------
    // Jumpscare
    // ------------------------------------------------------------------
    function triggerJumpscare(enemy, text) {
        state.running = false;
        clearInterval(state.tickId);
        clearInterval(state.powerId);
        clearInterval(state.aiId);
        clearInterval(state.goldenId);

        const imgMap = {
            freddy: 'assets/photo1.jpg',
            bonnie: 'assets/photo2.jpg',
            chica: 'assets/photo3.jpg',
            foxy: 'assets/photo4.jpg',
            golden: 'assets/photo5.jpg',
        };
        const fbMap = {
            freddy: 'PHOTO 1',
            bonnie: 'PHOTO 2',
            chica: 'PHOTO 3',
            foxy: 'PHOTO 4',
            golden: 'PHOTO 5',
        };

        els.jsImg.src = imgMap[enemy] || '';
        els.jsImg.alt = text;
        els.jsImg.style.display = 'none';
        els.jsFallback.classList.add('hidden');
        els.jsFallback.textContent = fbMap[enemy] || 'PHOTO X';
        els.jsText.textContent = text;

        // Phase 1: Black screen for 0.5 seconds
        els.jumpscare.classList.remove('hidden');
        els.jumpscare.classList.add('active');
        document.getElementById('js-phase-1').style.display = 'block';
        document.getElementById('js-phase-2').style.display = 'none';

        // Red flash overlay
        const flash = document.createElement('div');
        flash.className = 'red-flash';
        document.body.appendChild(flash);

        // Phase 2: Show jumpscare after 0.5s black screen
        setTimeout(() => {
            document.getElementById('js-phase-1').style.display = 'none';
            document.getElementById('js-phase-2').style.display = 'flex';
            if (els.jsImg.complete && els.jsImg.naturalWidth > 0) {
                els.jsImg.style.display = 'block';
            } else {
                els.jsFallback.classList.remove('hidden');
            }
            AudioSys.playJumpscare();
        }, 500);

        setTimeout(() => {
            document.body.removeChild(flash);
            els.jumpscare.classList.remove('active');
            setTimeout(() => {
                els.jumpscare.classList.add('hidden');
                els.gameOver.classList.remove('hidden');
                els.goTitle.textContent = 'GAME OVER';
                els.goSub.textContent = text;
            }, 300);
        }, 2500);
    }

    // ------------------------------------------------------------------
    // Boot
    // ------------------------------------------------------------------
    init();

})();
