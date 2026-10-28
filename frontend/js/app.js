/* Plantorix - dashboard logic. All numbers shown come from API responses. */
(() => {
    const $ = id => document.getElementById(id);
    const HEALTH_EVERY_MS = 10000;
    const PLAY_EVERY_MS = 120;

    const state = {
        datasets: [], byParticipant: new Map(),
        participant: null, take: null, side: null, id: null,
        summary: null, series: null, validation: null,
        frame: 0, frameData: null, sensor: 0, sensorCache: {},
        playing: false, timer: null, busy: false, frameToken: 0, loadToken: 0,
    };

    /* ---------- API health (really checked, repeated automatically) ---------- */
    async function checkHealth() {
        const pill = $("apiStatus"), text = $("apiStatusText");
        try {
            const h = await Api.get("/api/health", 5000);
            if (h.status === "ok") {
                pill.className = "status-pill ok";
                text.textContent = "API connected · " + h.recordings_found + " recordings";
            } else {
                pill.className = "status-pill warn";
                text.textContent = "API running, no recordings found";
            }
        } catch (err) {
            pill.className = "status-pill bad";
            text.textContent = "API offline";
        }
    }

    /* ---------- Banners and status ---------- */
    function showError(msg) { $("errorText").textContent = msg; $("errorBanner").classList.remove("hidden"); }
    function hideError() { $("errorBanner").classList.add("hidden"); }
    function setOverlay(html) {
        const o = $("heatOverlay");
        if (html) { o.innerHTML = html; o.classList.remove("hidden"); } else o.classList.add("hidden");
    }
    function setDatasetStatus(kind, main, sub) {
        const card = $("cardStatus");
        card.classList.toggle("good", kind === "good"); card.classList.toggle("bad", kind === "bad");
        $("vStatus").textContent = main; $("sStatus").textContent = sub || " ";
    }
    function setControls(enabled) {
        ["prevBtn", "nextBtn", "playBtn", "slider", "exportBtn"].forEach(id => { $(id).disabled = !enabled; });
    }
    function fmt(n) { return Number(n).toLocaleString("en-US", { maximumFractionDigits: 2 }); }

    /* ---------- Recording selection ---------- */
    function indexDatasets(list) {
        state.byParticipant = new Map();
        list.forEach(r => {
            if (!state.byParticipant.has(r.participant)) state.byParticipant.set(r.participant, new Map());
            const takes = state.byParticipant.get(r.participant);
            if (!takes.has(r.take)) takes.set(r.take, {});
            takes.get(r.take)[r.side] = r;
        });
    }
    function fillSelect(sel, values, current) {
        sel.innerHTML = "";
        values.forEach(v => { const o = document.createElement("option"); o.value = o.textContent = v; sel.appendChild(o); });
        if (current && values.includes(current)) sel.value = current;
        sel.disabled = values.length === 0;
    }
    function refreshSideButtons() {
        const entry = state.byParticipant.get(state.participant).get(state.take);
        ["L", "R"].forEach(s => {
            const b = $(s === "L" ? "sideL" : "sideR");
            b.disabled = !entry[s];
            b.setAttribute("aria-pressed", String(state.side === s));
        });
    }
    function chooseTake(take, preferredSide) {
        state.take = take;
        const entry = state.byParticipant.get(state.participant).get(take);
        state.side = entry[preferredSide] ? preferredSide : (entry.L ? "L" : "R");
        refreshSideButtons();
        loadRecording(entry[state.side].dataset_id);
    }

    async function loadDatasets() {
        setOverlay('<span><span class="spinner"></span>Finding recordings...</span>');
        try {
            const data = await Api.get("/api/datasets");
            if (!data.count) {
                setDatasetStatus("bad", "No recordings", "dataset folder is empty");
                $("recMeta").textContent = "No pressure recordings were found.";
                setOverlay("<span><b>No recordings found.</b><br>Check the dataset folder: python -m backend.config</span>");
                return;
            }
            state.datasets = data.recordings;
            indexDatasets(state.datasets);
            const participants = [...state.byParticipant.keys()];
            state.participant = participants[0];
            fillSelect($("selParticipant"), participants, state.participant);
            fillSelect($("selTake"), [...state.byParticipant.get(state.participant).keys()]);
            chooseTake($("selTake").value, "L");
        } catch (err) {
            setDatasetStatus("bad", "Unavailable", "API error");
            $("recMeta").textContent = "Recordings could not be loaded.";
            setOverlay("<span><b>No data to show.</b><br>The API could not be reached.</span>");
            showError(err.message);
        }
    }

    /* ---------- Loading one recording ---------- */
    async function loadRecording(id) {
        const token = ++state.loadToken;
        stopPlay(); hideError(); setControls(false);
        state.id = id; state.sensorCache = {};
        setDatasetStatus("", "Loading...", id);
        setOverlay('<span><span class="spinner"></span>Loading recording...</span>');
        try {
            const [summary, series, validation] = await Promise.all([
                Api.get("/api/datasets/" + id + "/summary"),
                Api.get("/api/datasets/" + id + "/timeseries"),
                Api.get("/api/datasets/" + id + "/validation"),
            ]);
            if (token !== state.loadToken) return;      // a newer selection took over
            Object.assign(state, { summary, series, validation, frame: 0 });
            renderRecording();
            await showFrame(0);
            await loadSensorSeries(state.sensor);
            setOverlay(null); setControls(true);
        } catch (err) {
            if (token !== state.loadToken) return;
            Charts.destroyAll(); Heatmap.clear();
            setDatasetStatus("bad", "Failed to load", id);
            setOverlay("<span><b>This recording could not be loaded.</b><br>" + escapeHtml(err.message) + "</span>");
            showError(err.message);
        }
    }

    function escapeHtml(s) { return String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }

    function renderRecording() {
        const s = state.summary, v = state.validation;
        setDatasetStatus("good", "Loaded", s.participant + " · take " + s.take + " · " + (s.side === "L" ? "left" : "right"));
        $("recMeta").innerHTML = "Participant " + escapeHtml(s.participant) + " &middot; file <b>" + escapeHtml(s.filename) + "</b>";
        $("vSensors").textContent = s.sensor_count;
        $("vFrames").textContent = s.frame_count;
        $("legMin").textContent = s.value_min; $("legMax").textContent = s.value_max;
        $("legendBar").style.background = Heatmap.gradientCss();
        $("layoutNote").classList.toggle("hidden", s.sensor_layout_verified);
        const slider = $("slider"); slider.max = s.frame_count - 1; slider.value = 0;

        const issue = $("issueBanner");
        if (s.known_issue) { issue.textContent = "Dataset note for this take: " + s.known_issue; issue.classList.remove("hidden"); }
        else issue.classList.add("hidden");

        // Data quality panel
        $("dqDims").textContent = v.rows + " rows × " + v.columns + " columns";
        $("dqSensors").textContent = v.sensor_channels;
        $("dqMissing").textContent = v.missing_values;
        $("dqRange").textContent = s.value_min + " to " + s.value_max;
        $("dqFile").textContent = s.filename;
        const sp = v.sump_check, el = $("dqSump");
        if (!sp.available) { el.textContent = "sumP column not available"; el.className = "v"; }
        else if (sp.matches_exactly) { el.textContent = "Yes, all " + v.rows + " frames"; el.className = "v ok-text"; }
        else { el.textContent = "No: " + sp.frames_with_difference + " frame(s) differ (max " + sp.max_abs_difference + ")"; el.className = "v"; }
        $("dqWarnings").innerHTML = v.warnings.length
            ? v.warnings.map(w => "<li>" + escapeHtml(w) + "</li>").join("") : "";
        $("dqCols").innerHTML = v.available_columns.map(c => "<li>" + escapeHtml(c) + "</li>").join("");

        // Charts that depend only on the whole recording
        Charts.drawTotal(state.series);
        Charts.drawCompare(state.series);
        $("cmpNote").textContent = sp.available
            ? (sp.matches_exactly ? "The two lines coincide: the 32-sensor sum equals sumP in every frame."
                : "Largest difference: " + sp.max_abs_difference + " (recorded sensor value units).")
            : "sumP is not available for this recording.";
    }

    /* ---------- One frame ---------- */
    async function showFrame(i) {
        const token = ++state.frameToken;
        const f = await Api.get("/api/datasets/" + state.id + "/frame/" + i);
        if (token !== state.frameToken) return;
        state.frame = i; state.frameData = f;
        const above = new Set(f.above_average_sensors);
        Heatmap.update(f.values, state.summary.value_min, state.summary.value_max, above, state.sensor);

        $("vFrame").textContent = i; $("vMax").textContent = f.max; $("vMean").textContent = fmt(f.mean);
        $("sMax").textContent = "sensor S" + f.max_sensor_index;
        $("slider").value = i; $("sliderLabel").textContent = i + " / " + (f.frame_count - 1);
        $("aMean").textContent = fmt(f.mean);
        $("aMax").textContent = f.max + " (S" + f.max_sensor_index + ")";
        $("aMin").textContent = f.min + " (S" + f.min_sensor_index + ")";
        $("aTotal").textContent = fmt(f.total);
        $("aAbove").textContent = above.size + " of 32";
        $("chips").innerHTML = f.above_average_sensors
            .map(s => '<button class="chip" data-s="' + s + '">S' + s + " · " + f.values[s] + "</button>").join("");
        $("frameTable").innerHTML = f.values.map((v, s) => "<tr><td>S" + s + "</td><td>" + v + "</td></tr>").join("");
        Charts.drawFrameBars(f);
        Charts.setCursor(i);
        showDetail(state.sensor, true);
        renderOrthotic();
    }

    function showDetail(sensor, selected) {
        const f = state.frameData; if (!f) return;
        const v = f.values[sensor], above = f.above_average_sensors.includes(sensor);
        $("detail").innerHTML = "<b>Sensor " + sensor + "</b> (CSV column PressureSensor " + sensor + ")" +
            (selected ? " &middot; selected" : "") + "<br>Recorded value: <b class='num'>" + v + "</b>" +
            " &middot; frame " + f.frame_index + " &middot; " + (above ? "above" : "at or below") + " this frame's average (" + fmt(f.mean) + ")";
    }

    async function loadSensorSeries(sensor) {
        state.sensor = sensor; $("selSensor").value = String(sensor);
        if (state.frameData) {
            Heatmap.update(state.frameData.values, state.summary.value_min, state.summary.value_max,
                new Set(state.frameData.above_average_sensors), sensor);
            showDetail(sensor, true);
        }
        try {
            if (!state.sensorCache[sensor]) {
                state.sensorCache[sensor] = await Api.get("/api/datasets/" + state.id + "/timeseries?sensor=" + sensor);
            }
            Charts.drawSensor(state.sensorCache[sensor], sensor);
            Charts.setCursor(state.frame);
        } catch (err) { showError(err.message); }
    }

    /* ---------- Orthotic design prototype ---------- */
    function renderOrthotic() {
        const f = state.frameData, verified = state.summary.sensor_layout_verified;
        const steps = [
            ["done", "✓", "Review the pressure analysis", "Frame " + f.frame_index + " of " + (f.frame_count - 1) + " in " + state.summary.dataset_id + " is loaded; the numbers above come from the recording."],
            ["done", "✓", "Identify relatively high readings", f.above_average_sensors.length + " sensors read above this frame's average (mean " + fmt(f.mean) + "). This is a relative comparison, not a clinical threshold."],
            [verified ? "done" : "blocked", verified ? "✓" : "!", "Verify physical sensor locations", verified ? "Sensor mapping verified." : "Not verified. CSV sensor indices have not been matched to positions on the foot."],
            ["blocked", "–", "Propose regional offloading", "Not available. It needs verified sensor positions and validated clinical criteria, so no region, depth or material is suggested."],
        ];
        $("orthSteps").innerHTML = steps.map(s =>
            '<li><span class="mark ' + s[0] + '">' + s[1] + "</span><span><b>" + s[2] + "</b><br><span class='small muted'>" + escapeHtml(s[3]) + "</span></span></li>").join("");
    }

    function exportSummary() {
        const f = state.frameData; if (!f) return;
        const out = {
            notice: "Research and educational prototype output. Not clinically validated, not a diagnosis, not manufacturing-ready.",
            source: { dataset_id: f.dataset_id, frame_index: f.frame_index, value_label: f.value_label, unit_note: "raw sensor counts, not kPa" },
            frame_statistics: { mean: f.mean, max: f.max, min: f.min, total: f.total },
            relative_high_readings: {
                definition: "Sensors with a recorded value above the mean of the 32 sensors in this frame. Relative comparison only.",
                sensors: f.above_average_sensors.map(s => ({
                    csv_sensor_index: s, recorded_value: f.values[s],
                    fraction_of_frame_max: Math.round(f.values[s] / f.max * 1000) / 1000
                })),
            },
            sensor_layout_verified: f.sensor_layout_verified,
            regional_offloading: "not proposed: sensor positions are not verified",
            offloading_depth_mm: null, material: null,
            generated_in_browser_at: new Date().toISOString(),
        };
        const blob = new Blob([JSON.stringify(out, null, 2)], { type: "application/json" });
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = "plantorix_" + f.dataset_id + "_frame" + f.frame_index + ".json";
        document.body.appendChild(a); a.click(); a.remove();
        setTimeout(() => URL.revokeObjectURL(a.href), 1000);
    }

    /* ---------- Playback ---------- */
    function stopPlay() {
        state.playing = false; clearInterval(state.timer); state.timer = null;
        $("playBtn").textContent = "Play";
    }
    function startPlay() {
        state.playing = true; $("playBtn").textContent = "Pause";
        const last = state.summary.frame_count - 1;
        if (state.frame >= last) state.frame = -1;
        state.timer = setInterval(async () => {
            if (state.busy) return;
            const next = state.frame + 1;
            if (next > last) { stopPlay(); return; }
            state.busy = true;
            try { await showFrame(next); } catch (err) { stopPlay(); showError(err.message); }
            state.busy = false;
        }, PLAY_EVERY_MS);
    }
    async function goTo(i) {
        const last = state.summary.frame_count - 1;
        i = Math.max(0, Math.min(last, i));
        try { await showFrame(i); } catch (err) { showError(err.message); }
    }

    /* ---------- Wiring ---------- */
    function init() {
        const sel = $("selSensor");
        for (let i = 0; i < 32; i++) { const o = document.createElement("option"); o.value = i; o.textContent = "S" + i; sel.appendChild(o); }
        Heatmap.build($("heatgrid"), 32, {
            onHover: i => showDetail(i, i === state.sensor),
            onLeave: () => showDetail(state.sensor, true),
            onSelect: i => loadSensorSeries(i),
        });
        Heatmap.clear();

        $("selParticipant").addEventListener("change", e => {
            state.participant = e.target.value;
            const takes = [...state.byParticipant.get(state.participant).keys()];
            fillSelect($("selTake"), takes);
            chooseTake(takes[0], state.side || "L");
        });
        $("selTake").addEventListener("change", e => chooseTake(e.target.value, state.side || "L"));
        ["L", "R"].forEach(s => $(s === "L" ? "sideL" : "sideR").addEventListener("click", () => {
            state.side = s; refreshSideButtons();
            loadRecording(state.byParticipant.get(state.participant).get(state.take)[s].dataset_id);
        }));
        $("slider").addEventListener("input", e => { stopPlay(); goTo(Number(e.target.value)); });
        $("prevBtn").addEventListener("click", () => { stopPlay(); goTo(state.frame - 1); });
        $("nextBtn").addEventListener("click", () => { stopPlay(); goTo(state.frame + 1); });
        $("playBtn").addEventListener("click", () => state.playing ? stopPlay() : startPlay());
        $("chips").addEventListener("click", e => { const b = e.target.closest(".chip"); if (b) loadSensorSeries(Number(b.dataset.s)); });
        $("selSensor").addEventListener("change", e => loadSensorSeries(Number(e.target.value)));
        $("exportBtn").addEventListener("click", exportSummary);
        $("retryBtn").addEventListener("click", () => {
            hideError();
            if (state.id) loadRecording(state.id); else loadDatasets();
        });

        checkHealth(); setInterval(checkHealth, HEALTH_EVERY_MS);
        loadDatasets();
    }
    document.addEventListener("DOMContentLoaded", init);
})();