// LATEST - added the smart rule-based AI recommendation:
// app.js
const apiUrl = "https://dyuhlzv7gd.execute-api.us-east-1.amazonaws.com/learningProgressTracker"; // keep your API

// Bind Enter on the UserID input
document.getElementById("userId").addEventListener("keydown", (e) => {
  if (e.key === "Enter") loadDashboard();
});

// Main loader
async function loadDashboard() {
  const userId = document.getElementById("userId").value.trim();
  console.log("loadDashboard called with:", userId); // debug

  if (!userId) {
    alert("Please enter a UserID (e.g., student201)");
    return;
  }

  try {
    const response = await fetch(apiUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "get_all_progress", UserID: userId })
    });

    const payload = await response.json();
    if (response.status !== 200) {
      console.error("API error:", payload);
      alert("API Error: " + (payload.error || "Unknown"));
      return;
    }

    const items = Array.isArray(payload) ? payload : payload.Items || payload; // safety
    renderDashboard(normalizeItems(items));
  } catch (err) {
    console.error(err);
    alert("Fetch failed — check console (CORS or network).");
  }
}

// Convert ProgressPercent and other fields to usable JS types
function normalizeItems(items) {
  return (items || []).map(item => {
    // ProgressPercent may be string/Decimal/number; ensure numeric
    const progress = Number(item.ProgressPercent ?? item.progress ?? item.Progress ?? 0) || 0;
    const attempts = Number(item.attempts ?? 0) || 0;

    // CompletedModules might be an array, a stringified JSON, or empty
    let completed = item.CompletedModules ?? item.completedModules ?? item.CompletedModules;
    if (!Array.isArray(completed) && typeof completed === "string") {
      try { completed = JSON.parse(completed); } catch (e) { completed = []; }
    }
    const completedCount = Array.isArray(completed) ? completed.length : 0;

    return {
      TopicID: item.TopicID || item.topic || item.Topic || "unknown",
      ProgressPercent: progress,
      attempts,
      CompletedModules: Array.isArray(completed) ? completed : [],
      CompletedCount: completedCount,
      LastAccessed: item.LastAccessed || item.lastAccessed || item.lastUpdated || ""
    };
  });
}

// Rule-based recommendation function
function getRecommendationForTopic(item) {
  const p = Number(item.ProgressPercent) || 0;
  const attempts = Number(item.attempts) || 0;

  // Base rules
  if (p >= 80) {
    return { label: "Mastered", cls: "rec-mastered", message: "Strong mastery — try advanced quizzes or a summary for retention." };
  }
  if (attempts >= 3 && p < 60) {
    // Many attempts but stuck
    return { label: "Needs Help", cls: "rec-help", message: "Multiple attempts detected. Consider tutor help or targeted practice." };
  }
  if (p >= 50) {
    return { label: "Practice", cls: "rec-practice", message: "Good progress — practice problems recommended to improve speed and accuracy." };
  }
  // p < 50
  return { label: "Review", cls: "rec-review", message: "Low progress — review the summary and fundamentals first." };
}

// Render table, chart, overall recommendation
function renderDashboard(items) {
  renderTable(items);
  renderChart(items);
  renderOverall(items);
}

function renderTable(items) {
  const tbody = document.querySelector("#progressTable tbody");
  tbody.innerHTML = "";
  if (!items || items.length === 0) {
    tbody.innerHTML = "<tr><td colspan='5'>No progress found for this user.</td></tr>";
    return;
  }

  items.forEach(item => {
    const rec = getRecommendationForTopic(item);
    const tr = document.createElement("tr");

    const topicTd = document.createElement("td"); topicTd.textContent = item.TopicID;
    const completedTd = document.createElement("td"); completedTd.textContent = item.CompletedCount;
    const progressTd = document.createElement("td");
    progressTd.innerHTML = `
      <div style="background:#E4CAA5;border-radius:8px;height:16px;width:100%;position:relative;">
        <div style="background:#AD8B73;height:100%;border-radius:8px;width:${item.ProgressPercent}%;text-align:right;padding-right:6px;color:white;font-size:12px;">
          ${item.ProgressPercent}%
        </div>
      </div>
    `;

    const recTd = document.createElement("td");
    recTd.innerHTML = `<span class="rec-pill ${rec.cls}">${rec.label}</span>
                       <div class="recommendation-text">${rec.message}</div>
                       <div style="margin-top:6px;">
                         <button onclick='alert("${escapeForAlert(rec.message)}")'>Suggest Activity</button>
                       </div>`;

    const lastTd = document.createElement("td"); lastTd.textContent = item.LastAccessed ? new Date(item.LastAccessed).toLocaleString() : "-";

    tr.appendChild(topicTd);
    tr.appendChild(completedTd);
    tr.appendChild(progressTd);
    tr.appendChild(recTd);
    tr.appendChild(lastTd);
    tbody.appendChild(tr);
  });
}

function escapeForAlert(s) {
  return String(s).replace(/"/g, '\\"').replace(/\n/g, "\\n");
}

let chartInstance = null;
function renderChart(items) {
  const labels = items.map(i => i.TopicID);
  const data = items.map(i => i.ProgressPercent);

  const ctx = document.getElementById("progressChart").getContext("2d");
  if (chartInstance) chartInstance.destroy();
  chartInstance = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "Progress (%)",
        data,
        backgroundColor: labels.map((_,idx) => ["#AD8B73","#CEAB93","#E4CAA5"][idx % 3])
      }]
    },
    options: { responsive: true, scales: { y: { beginAtZero: true, max: 100 } } }
  });
}

// Overall recommendation: pick the weakest topic or topic with many attempts & low progress
function renderOverall(items) {
  const div = document.getElementById("overallRecommendation");
  if (!items || items.length === 0) {
    div.style.display = "none";
    return;
  }

  // compute avg safely
  const total = items.reduce((s, it) => s + (Number(it.ProgressPercent) || 0), 0);
  const avg = (total / items.length) || 0;

  // pick focus topic: lowest progress or highest attempts with low progress
  let focus = items[0];
  items.forEach(it => {
    if ((Number(it.ProgressPercent) || 0) < (Number(focus.ProgressPercent) || 0)) focus = it;
    if ((Number(it.attempts) || 0) >= 3 && (Number(it.ProgressPercent) || 0) < (Number(focus.ProgressPercent) || 100)) focus = it;
  });

  div.style.display = "block";
  div.innerHTML = `
    <strong>Overall progress: ${avg.toFixed(1)}%</strong>
    <div><strong style="color:#654321">Recommended focus: </strong><strong>${focus.TopicID}</strong> — current progress ${focus.ProgressPercent}%</div>
    <div style="margin-top:8px;">Recommendation: ${getRecommendationForTopic(focus).message}</div>
  `;
}
