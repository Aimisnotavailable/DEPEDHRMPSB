document.addEventListener("DOMContentLoaded", () => {
  const btn     = document.getElementById("toggle-details");
  const details = document.getElementById("details-container");
  const form    = document.getElementById("eval-form");
  const totalIn = document.getElementById("total_score");

  // our five fields now
  const fields = [
    "aptitude",
    "character_traits",
    "fitness",
    "leadership",
    "communication"
  ];

  if (!btn || !details || !form || !totalIn) return;

  // hide by default
  details.style.display = "none";

  btn.addEventListener("click", () => {
    const showing = details.style.display !== "none";
    details.style.display = showing ? "none" : "grid";
    btn.innerHTML = showing
      ? '<i class="fa fa-edit"></i> View / Update Evaluation'
      : '<i class="fa fa-eye-slash"></i> Hide Evaluation';
  });

  function computeTotal() {
    let sum = 0;
    fields.forEach(name => {
      const inp = form.querySelector(`[name="${name}"]`);
      sum += parseFloat(inp.value) || 0;
    });
    totalIn.value = sum.toFixed(2);
  }

  // recalc as you type
  fields.forEach(name => {
    const inp = form.querySelector(`[name="${name}"]`);
    if (inp) inp.addEventListener("input", computeTotal);
  });

  computeTotal();
});
