/* Plantorix - Chart.js wrappers. Every chart is created once and then updated in place. */
const Charts = (() => {
  const C = { main: "#0e5a6e", light: "#7fb8bf", dark: "#0b3c55", amber: "#b8741c",
              grid: "#e6ebee", axis: "#55646e" };
  const charts = {};

  // Draws a vertical line at the selected frame on line charts.
  const frameCursor = {
    id: "frameCursor",
    afterDatasetsDraw(chart) {
      const idx = chart.options.plugins.frameCursor && chart.options.plugins.frameCursor.index;
      if (idx == null || !chart.scales.x) return;
      const x = chart.scales.x.getPixelForValue(idx), a = chart.chartArea, ctx = chart.ctx;
      ctx.save(); ctx.strokeStyle = "#26323a"; ctx.lineWidth = 1.5; ctx.setLineDash([4, 3]);
      ctx.beginPath(); ctx.moveTo(x, a.top); ctx.lineTo(x, a.bottom); ctx.stroke(); ctx.restore();
    }
  };

  function baseOptions(xTitle, yTitle) {
    return {
      responsive: true, maintainAspectRatio: false, animation: false,
      interaction: { mode: "index", intersect: false },
      plugins: { legend: { display: false }, frameCursor: { index: null } },
      scales: {
        x: { title: { display: !!xTitle, text: xTitle, color: C.axis }, grid: { display: false },
             ticks: { color: C.axis, maxTicksLimit: 8, maxRotation: 0 } },
        y: { title: { display: !!yTitle, text: yTitle, color: C.axis }, grid: { color: C.grid },
             ticks: { color: C.axis }, beginAtZero: true }
      }
    };
  }

  function make(id, config) {
    if (charts[id]) charts[id].destroy();
    charts[id] = new Chart(document.getElementById(id), config);
    return charts[id];
  }

  function lineDataset(label, data, color, dashed) {
    return { label, data, borderColor: color, backgroundColor: color, borderWidth: 2,
             pointRadius: data.length < 30 ? 3 : 0, pointHoverRadius: 4, tension: 0,
             borderDash: dashed ? [6, 4] : [] };
  }

  function drawFrameBars(frame) {
    const labels = frame.values.map((_, i) => "S" + i);
    const above = new Set(frame.above_average_sensors);
    const colors = frame.values.map((_, i) => above.has(i) ? C.dark : C.light);
    if (!charts.chBars) {
      const o = baseOptions("Sensor (CSV index)", "Recorded sensor value");
      o.plugins.tooltip = { callbacks: { label: c => "Recorded value: " + c.parsed.y } };
      o.scales.x.ticks.maxTicksLimit = 16;
      make("chBars", { type: "bar", data: { labels, datasets: [{ data: frame.values, backgroundColor: colors,
        borderRadius: 3 }] }, options: o });
    } else {
      const c = charts.chBars;
      c.data.labels = labels; c.data.datasets[0].data = frame.values;
      c.data.datasets[0].backgroundColor = colors; c.update("none");
    }
  }

  function drawTotal(ts) {
    const o = baseOptions("Frame", "Sum of 32 sensors");
    o.plugins.tooltip = { callbacks: { title: i => "Frame " + i[0].label } };
    make("chTotal", { type: "line", data: { labels: ts.frames,
      datasets: [lineDataset("Calculated sum", ts.calculated_sum, C.main)] },
      options: o, plugins: [frameCursor] });
  }

  function drawCompare(ts) {
    const o = baseOptions("Frame", "Recorded sensor value (sum)");
    o.plugins.legend = { display: true, position: "bottom", labels: { color: C.axis, usePointStyle: true, pointStyle: "line", boxWidth: 28 } };
    o.plugins.tooltip = { callbacks: { title: i => "Frame " + i[0].label } };
    const sets = [lineDataset("Calculated sum of 32 sensors", ts.calculated_sum, C.main)];
    if (ts.sump) sets.push(lineDataset("sumP column (dashed)", ts.sump, C.amber, true));
    make("chCompare", { type: "line", data: { labels: ts.frames, datasets: sets },
      options: o, plugins: [frameCursor] });
  }

  function drawSensor(ts, sensor) {
    const o = baseOptions("Frame", "Recorded sensor value");
    o.plugins.tooltip = { callbacks: { title: i => "Frame " + i[0].label } };
    make("chSensor", { type: "line", data: { labels: ts.frames,
      datasets: [lineDataset("Sensor " + sensor, ts.sensor_series, C.main)] },
      options: o, plugins: [frameCursor] });
  }

  function setCursor(frameIndex) {
    ["chTotal", "chCompare", "chSensor"].forEach(id => {
      const c = charts[id];
      if (c) { c.options.plugins.frameCursor.index = frameIndex; c.update("none"); }
    });
  }

  function destroyAll() {
    Object.keys(charts).forEach(k => { charts[k].destroy(); delete charts[k]; });
  }

  return { drawFrameBars, drawTotal, drawCompare, drawSensor, setCursor, destroyAll };
})();
