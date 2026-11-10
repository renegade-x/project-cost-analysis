"use strict";

(async function () {
  const section = document.querySelector("[data-chart-url]");
  if (!section) return;
  const message = document.getElementById("chart-message");
  const grid = document.getElementById("charts-grid");
  try {
    const response = await fetch(section.dataset.chartUrl, {
      credentials: "same-origin", headers: {Accept: "application/json"}
    });
    if (!response.ok) throw new Error("Chart request failed");
    const data = await response.json();
    if (!data.labels.length) {
      message.textContent = "No data yet. Add costs to see your charts.";
      return;
    }
    if (typeof Chart === "undefined") throw new Error("Chart library unavailable");
    grid.hidden = false;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const options = (title) => ({
      responsive: true, maintainAspectRatio: false, animation: reducedMotion ? false : {duration: 300},
      plugins: {legend: {position: "bottom", labels: {boxWidth: 10, padding: 18}}, tooltip: {mode: "index", intersect: false}},
      scales: {
        x: {grid: {display: false}, title: {display: true, text: "Category"}, ticks: {maxRotation: 55, minRotation: 25, callback: function (value) {
          const label = this.getLabelForValue(value);
          return label.length > 18 ? label.slice(0, 17) + "…" : label;
        }}},
        y: {beginAtZero: true, title: {display: true, text: title}, grid: {color: "#e9ede7"}}
      }
    });
    Chart.defaults.font.family = '"Segoe UI", Arial, sans-serif';
    Chart.defaults.color = "#5c6b65";
    new Chart(document.getElementById("comparison-chart"), {
      type: "bar", data: {labels: data.labels, datasets: [
        {label: "Estimated", data: data.estimated, backgroundColor: "#bbcab7", borderRadius: 3},
        {label: "Actual", data: data.actual, backgroundColor: "#245b47", borderRadius: 3}
      ]}, options: options("Cost (currency units)")
    });
    const varianceOptions = options("Actual − Estimated");
    varianceOptions.plugins.legend.display = false;
    new Chart(document.getElementById("variance-chart"), {
      type: "bar", data: {labels: data.labels, datasets: [{
        label: "Variance", data: data.variance,
        backgroundColor: data.variance.map(value => value > 0 ? "#a56349" : "#245b47"), borderRadius: 3
      }]}, options: varianceOptions
    });
    message.hidden = true;
  } catch (error) {
    grid.hidden = true;
    message.textContent = "Charts could not be loaded. Your full cost data is available in the table above.";
  }
})();
