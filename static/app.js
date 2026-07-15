(() => {
  const pttButton = document.getElementById("pttButton");
  const pttHint = document.getElementById("pttHint");
  const heardText = document.getElementById("heardText");
  const replyText = document.getElementById("replyText");
  const logList = document.getElementById("logList");
  const unitList = document.getElementById("unitList");
  const logCount = document.getElementById("logCount");
  const connectionPill = document.getElementById("connectionPill");
  const versionTag = document.getElementById("versionTag");
  const textForm = document.getElementById("textForm");
  const textInput = document.getElementById("textInput");
  const muteButton = document.getElementById("muteButton");
  const resetButton = document.getElementById("resetButton");
  const meterBar = document.getElementById("meterBar");

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  let recognition = null;
  let listening = false;
  let muted = false;
  let finalTranscript = "";
  let interimTranscript = "";
  let submitting = false;
  let meterTimer = null;

  function setConnection(state, label) {
    connectionPill.className = `status-pill ${state}`;
    connectionPill.textContent = label;
  }

  function speak(text) {
    if (muted || !window.speechSynthesis || !text) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.02;
    utterance.pitch = 0.95;
    window.speechSynthesis.speak(utterance);
  }

  function formatTime(iso) {
    try {
      return new Date(iso).toLocaleTimeString();
    } catch {
      return "";
    }
  }

  function renderLog(entries) {
    if (!entries.length) {
      logList.innerHTML = '<p class="empty">No traffic logged yet.</p>';
      logCount.textContent = "0 entries";
      return;
    }
    logCount.textContent = `${entries.length} entr${entries.length === 1 ? "y" : "ies"}`;
    logList.innerHTML = entries
      .map(
        (entry) => `
      <article class="log-item">
        <div class="meta">
          <span>${formatTime(entry.timestamp)} · ${escapeHtml(entry.unit_id || "Unknown vessel")}</span>
          <span class="badge ${entry.priority}">${entry.priority}</span>
        </div>
        <p><strong>RX:</strong> ${escapeHtml(entry.transcript)}</p>
        <p><strong>TX:</strong> ${escapeHtml(entry.response)}</p>
      </article>`
      )
      .join("");
  }

  function renderUnits(units) {
    if (!units.length) {
      unitList.innerHTML = '<p class="empty">No vessels heard yet.</p>';
      return;
    }
    unitList.innerHTML = units
      .map(
        (unit) => `
      <article class="unit-card">
        <div class="meta">
          <strong>${escapeHtml(unit.unit_id)}</strong>
          <span>${escapeHtml(unit.status)}</span>
        </div>
        <p>${escapeHtml(unit.last_location || "No location")}</p>
        <p class="meta">Last heard ${formatTime(unit.last_heard)}</p>
      </article>`
      )
      .join("");
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  async function refreshBoard() {
    const [logRes, unitRes, healthRes] = await Promise.all([
      fetch("/api/log"),
      fetch("/api/units"),
      fetch("/api/health"),
    ]);
    const logData = await logRes.json();
    const unitData = await unitRes.json();
    const healthData = await healthRes.json();
    if (healthData.version && versionTag) {
      versionTag.textContent = `v${healthData.version}`;
    }
    renderLog(logData.entries || []);
    renderUnits(unitData.units || []);
  }

  async function submitTranscript(transcript) {
    const cleaned = (transcript || "").trim();
    if (!cleaned || submitting) return;
    submitting = true;
    heardText.textContent = cleaned;
    replyText.textContent = "Processing…";
    try {
      const response = await fetch("/api/dispatch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ transcript: cleaned, channel: "VHF Ch 16" }),
      });
      if (!response.ok) {
        throw new Error(`Dispatch failed (${response.status})`);
      }
      const data = await response.json();
      applyDispatchEvent(data);
    } catch (error) {
      replyText.textContent = error.message || "Dispatch failed";
    } finally {
      submitting = false;
    }
  }

  function applyDispatchEvent(data) {
    if (!data || !data.reply) return;
    const reply = data.reply;
    heardText.textContent = reply.transcript;
    replyText.textContent = reply.response;
    speak(reply.spoken_response || reply.response);
    if (Array.isArray(data.units)) {
      renderUnits(data.units);
    }
    refreshBoard();
  }

  function startMeter() {
    stopMeter();
    meterTimer = setInterval(() => {
      const width = 18 + Math.floor(Math.random() * 70);
      meterBar.style.width = `${width}%`;
    }, 120);
  }

  function stopMeter() {
    if (meterTimer) {
      clearInterval(meterTimer);
      meterTimer = null;
    }
    meterBar.style.width = "8%";
  }

  function setupRecognition() {
    if (!SpeechRecognition) {
      pttHint.textContent = "Speech API unavailable — use text fallback";
      pttButton.disabled = true;
      return;
    }
    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    recognition.onresult = (event) => {
      interimTranscript = "";
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const result = event.results[i];
        if (result.isFinal) {
          finalTranscript += `${result[0].transcript} `;
        } else {
          interimTranscript += result[0].transcript;
        }
      }
      heardText.textContent = `${finalTranscript}${interimTranscript}`.trim() || "Listening…";
    };

    recognition.onerror = (event) => {
      if (event.error === "not-allowed") {
        pttHint.textContent = "Microphone blocked — allow mic access";
      } else if (event.error !== "aborted") {
        pttHint.textContent = `Mic error: ${event.error}`;
      }
    };

    recognition.onend = () => {
      if (listening) {
        try {
          recognition.start();
        } catch {
          // Ignore restart races.
        }
      }
    };
  }

  async function startListening() {
    if (!recognition || listening) return;
    finalTranscript = "";
    interimTranscript = "";
    listening = true;
    pttButton.classList.add("hot");
    pttButton.setAttribute("aria-pressed", "true");
    pttHint.textContent = "Listening… release to dispatch";
    heardText.textContent = "Listening…";
    startMeter();
    try {
      recognition.start();
    } catch {
      // Already started.
    }
  }

  async function stopListening() {
    if (!listening) return;
    listening = false;
    pttButton.classList.remove("hot");
    pttButton.setAttribute("aria-pressed", "false");
    pttHint.textContent = "Release to send";
    stopMeter();
    try {
      recognition.stop();
    } catch {
      // Ignore.
    }
    const transcript = `${finalTranscript}${interimTranscript}`.trim();
    finalTranscript = "";
    interimTranscript = "";
    if (transcript) {
      await submitTranscript(transcript);
    } else {
      heardText.textContent = "No speech captured";
    }
  }

  function connectSocket() {
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const socket = new WebSocket(`${protocol}://${window.location.host}/ws`);

    socket.addEventListener("open", () => setConnection("online", "Online"));
    socket.addEventListener("close", () => {
      setConnection("offline", "Reconnecting…");
      setTimeout(connectSocket, 1500);
    });
    socket.addEventListener("message", (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "dispatch_event") {
          applyDispatchEvent(data);
        } else if (data.type === "reset") {
          heardText.textContent = "Waiting for traffic…";
          replyText.textContent = "—";
          refreshBoard();
        }
      } catch {
        // Ignore malformed payloads.
      }
    });

    setInterval(() => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send("ping");
      }
    }, 25000);
  }

  pttButton.addEventListener("mousedown", (event) => {
    event.preventDefault();
    startListening();
  });
  pttButton.addEventListener("mouseup", (event) => {
    event.preventDefault();
    stopListening();
  });
  pttButton.addEventListener("mouseleave", () => {
    if (listening) stopListening();
  });
  pttButton.addEventListener("touchstart", (event) => {
    event.preventDefault();
    startListening();
  });
  pttButton.addEventListener("touchend", (event) => {
    event.preventDefault();
    stopListening();
  });
  pttButton.addEventListener("keydown", (event) => {
    if ((event.code === "Space" || event.key === " ") && !listening) {
      event.preventDefault();
      startListening();
    }
  });
  pttButton.addEventListener("keyup", (event) => {
    if (event.code === "Space" || event.key === " ") {
      event.preventDefault();
      stopListening();
    }
  });

  textForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const value = textInput.value.trim();
    if (!value) return;
    textInput.value = "";
    await submitTranscript(value);
  });

  muteButton.addEventListener("click", () => {
    muted = !muted;
    muteButton.textContent = muted ? "Unmute voice" : "Mute voice";
    if (muted && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
  });

  resetButton.addEventListener("click", async () => {
    await fetch("/api/reset", { method: "DELETE" });
    heardText.textContent = "Waiting for traffic…";
    replyText.textContent = "—";
    await refreshBoard();
  });

  setupRecognition();
  connectSocket();
  refreshBoard().catch(() => setConnection("offline", "API unavailable"));
})();
