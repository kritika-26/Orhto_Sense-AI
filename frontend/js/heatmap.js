/* Plantorix - sensor views.
   Matrix view : 32 cells ordered by CSV index (no anatomical meaning).
   Diagram view: sensors placed as on the dataset's numbering diagram. That placement is
                 supported by tests on the recordings but NOT confirmed by the dataset authors.
   No foot outline is drawn in either view. */
const Heatmap = (() => {
  // One-hue colour scale, light to dark teal-blue.
  const STOPS = ["#eaf4f3", "#a6d3d0", "#4aa0a8", "#1d6a8a", "#0b3c55"];
  const SVGNS = "http://www.w3.org/2000/svg";
  let cells = [];
  let sensors = [];   // diagram view: [{g, circle, text}] indexed by CSV sensor index

  function hexToRgb(h) { return [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16)); }
  function colorAt(t) {
    t = Math.max(0, Math.min(1, t));
    const seg = t * (STOPS.length - 1), i = Math.min(Math.floor(seg), STOPS.length - 2), f = seg - i;
    const a = hexToRgb(STOPS[i]), b = hexToRgb(STOPS[i + 1]);
    return a.map((v, k) => Math.round(v + (b[k] - v) * f));
  }
  function textColor(rgb) {
    const lum = (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) / 255;
    return lum > 0.6 ? "#16262d" : "#ffffff";
  }
  function gradientCss() { return "linear-gradient(90deg," + STOPS.join(",") + ")"; }

  function bind(el, i, handlers) {
    el.addEventListener("mouseenter", () => handlers.onHover(i));
    el.addEventListener("focus", () => handlers.onHover(i));
    el.addEventListener("mouseleave", () => handlers.onLeave());
    el.addEventListener("blur", () => handlers.onLeave());
    el.addEventListener("click", () => handlers.onSelect(i));
  }

  function build(container, count, handlers) {
    container.innerHTML = "";
    cells = [];
    for (let i = 0; i < count; i++) {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "cell";
      b.innerHTML = '<span class="i">S' + i + '</span><span class="val">-</span>';
      bind(b, i, handlers);
      container.appendChild(b);
      cells.push(b);
    }
  }

  function buildDiagram(svg, layout, handlers) {
    svg.innerHTML = "";
    svg.setAttribute("viewBox", "0 0 " + layout.width + " " + layout.height);
    sensors = [];
    layout.sensors.forEach(s => {
      const g = document.createElementNS(SVGNS, "g");
      g.setAttribute("class", "sensor"); g.setAttribute("tabindex", "0"); g.setAttribute("role", "button");
      const c = document.createElementNS(SVGNS, "circle");
      c.setAttribute("cx", s.x); c.setAttribute("cy", s.y); c.setAttribute("r", layout.radius);
      c.setAttribute("fill", "#eef1f3");
      const t = document.createElementNS(SVGNS, "text");
      t.setAttribute("x", s.x); t.setAttribute("y", s.y);
      t.setAttribute("font-size", Math.round(layout.radius * 0.78));
      t.textContent = "S" + s.csv_index;
      g.appendChild(c); g.appendChild(t);
      bind(g, s.csv_index, handlers);
      svg.appendChild(g);
      sensors[s.csv_index] = { g, c, t };
    });
  }

  /* values: array of 32 numbers; lo/hi: colour-scale range; above: Set of indices */
  function update(values, lo, hi, above, selected) {
    const span = Math.max(1, hi - lo);
    const paint = (i) => {
      const v = values[i], rgb = colorAt((v - lo) / span);
      return { v, rgb, css: "rgb(" + rgb.join(",") + ")", txt: textColor(rgb),
               label: "Sensor " + i + ", recorded value " + v + (above.has(i) ? ", above frame average" : "") };
    };
    cells.forEach((el, i) => {
      const p = paint(i);
      el.style.background = p.css; el.style.color = p.txt;
      el.querySelector(".val").textContent = p.v;
      el.classList.toggle("above", above.has(i));
      el.classList.toggle("sel", i === selected);
      el.setAttribute("aria-label", p.label);
    });
    sensors.forEach((s, i) => {
      if (!s) return;
      const p = paint(i);
      s.c.setAttribute("fill", p.css); s.t.setAttribute("fill", p.txt);
      s.g.classList.toggle("above", above.has(i));
      s.g.classList.toggle("sel", i === selected);
      s.g.setAttribute("aria-label", p.label);
    });
  }

  function clear() {
    cells.forEach(el => {
      el.style.background = "#eef1f3"; el.style.color = "#8a979e";
      el.querySelector(".val").textContent = "-";
      el.classList.remove("above", "sel");
    });
    sensors.forEach(s => { if (s) { s.c.setAttribute("fill", "#eef1f3"); s.g.classList.remove("above", "sel"); } });
  }

  return { build, buildDiagram, update, clear, gradientCss };
})();
