/* Plantorix - sensor grid. Cells are laid out by CSV index, row by row.
   This is NOT an anatomical foot layout (the mapping is unverified). */
const Heatmap = (() => {
    // One-hue colour scale, light to dark teal-blue.
    const STOPS = ["#eaf4f3", "#a6d3d0", "#4aa0a8", "#1d6a8a", "#0b3c55"];
    let cells = [];

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

    function build(container, count, handlers) {
        container.innerHTML = "";
        cells = [];
        for (let i = 0; i < count; i++) {
            const b = document.createElement("button");
            b.type = "button";
            b.className = "cell";
            b.innerHTML = '<span class="i">S' + i + '</span><span class="val">-</span>';
            b.addEventListener("mouseenter", () => handlers.onHover(i));
            b.addEventListener("focus", () => handlers.onHover(i));
            b.addEventListener("mouseleave", () => handlers.onLeave());
            b.addEventListener("blur", () => handlers.onLeave());
            b.addEventListener("click", () => handlers.onSelect(i));
            container.appendChild(b);
            cells.push(b);
        }
    }

    /* values: array of 32 numbers; lo/hi: colour-scale range; above: Set of indices */
    function update(values, lo, hi, above, selected) {
        const span = Math.max(1, hi - lo);
        cells.forEach((el, i) => {
            const v = values[i];
            const rgb = colorAt((v - lo) / span);
            el.style.background = "rgb(" + rgb.join(",") + ")";
            el.style.color = textColor(rgb);
            el.querySelector(".val").textContent = v;
            el.classList.toggle("above", above.has(i));
            el.classList.toggle("sel", i === selected);
            el.setAttribute("aria-label", "Sensor " + i + ", recorded value " + v +
                (above.has(i) ? ", above frame average" : ""));
        });
    }

    function clear() {
        cells.forEach(el => {
            el.style.background = "#eef1f3"; el.style.color = "#8a979e";
            el.querySelector(".val").textContent = "-";
            el.classList.remove("above", "sel");
        });
    }

    return { build, update, clear, gradientCss };
})();