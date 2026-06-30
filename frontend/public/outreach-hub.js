(function (global) {
  "use strict";

  function $(id) {
    return document.getElementById(id);
  }

  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\"/g, "&quot;");
  }

  function setButtonState(id, loading, label) {
    const button = $(id);
    if (!button) return;
    button.disabled = loading;
    button.dataset.originalLabel = button.dataset.originalLabel || button.textContent;
    button.textContent = loading ? label : button.dataset.originalLabel;
  }

  function showStatus(message, kind = "info") {
    const el = $("campaignStatus");
    if (!el) return;
    el.className = "text-sm mt-3 " + ({ info: "text-sky-400", success: "text-emerald-400", error: "text-red-400" })[kind] || "text-sky-400";
    el.textContent = message;
  }

  function initCampaignComposer() {
    const form = $("campaignComposer");
    const subject = $("campaignSubject");
    const recipients = $("campaignRecipients");
    const body = $("campaignBody");
    const button = $("launchCampaignBtn");

    if (!form || !button) return;

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const list = recipients.value
        .split(/[,\n]/)
        .map((item) => item.trim())
        .filter(Boolean);

      if (!subject.value.trim() || !body.value.trim() || !list.length) {
        showStatus("Add a subject, message, and at least one recipient to launch a campaign.", "error");
        return;
      }

      setButtonState("launchCampaignBtn", true, "Launching…");
      showStatus("Dispatching your outreach campaign…", "info");

      try {
        const result = await global.SwarmAPI.outreach.campaign({
          recipients: list,
          subject: subject.value.trim(),
          body: body.value.trim(),
          from_name: "SwarmOS",
        });
        if (result && result.status === "queued") {
          showStatus(`Campaign queued for ${result.queued || list.length} contact(s).`, "success");
          form.reset();
        } else {
          showStatus("The campaign could not be queued. Please try again.", "error");
        }
      } catch (error) {
        showStatus(error.message || "The campaign could not be queued.", "error");
      } finally {
        setButtonState("launchCampaignBtn", false, "Launch Campaign");
      }
    });
  }

  function renderGrowthHero() {
    const panel = $("growthHero");
    if (!panel) return;
    panel.innerHTML = `
      <div class="grid gap-6 lg:grid-cols-[1.2fr_0.8fr] items-center">
        <div>
          <div class="inline-flex items-center rounded-full border border-sky-500/40 bg-sky-500/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.25em] text-sky-300">
            Growth OS
          </div>
          <h2 class="mt-4 text-3xl font-semibold text-white">Automated outreach that feels like a world-class revenue engine.</h2>
          <p class="mt-3 text-sm leading-7 text-slate-400">Launch polished campaigns, nurture prospects, and convert momentum into pipeline in minutes using the same resilient stack that powers your backend automation.</p>
          <div class="mt-6 flex flex-wrap gap-3">
            <button class="btn-primary" onclick="document.getElementById('campaignComposer').scrollIntoView({behavior:'smooth'})">Launch campaign</button>
            <button class="btn-ghost" onclick="document.getElementById('opsStatusPanel').scrollIntoView({behavior:'smooth'})">View operations</button>
          </div>
        </div>
        <div class="rounded-2xl border border-slate-800 bg-slate-950/70 p-5 shadow-[0_0_60px_rgba(56,189,248,0.18)]">
          <div class="text-xs uppercase tracking-[0.25em] text-slate-500">Live metrics</div>
          <div class="mt-4 flex items-end justify-between">
            <div>
              <div class="text-4xl font-semibold text-white">98%</div>
              <div class="text-sm text-slate-400">deliverability confidence</div>
            </div>
            <div class="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-sm text-emerald-300">Autopilot ON</div>
          </div>
          <div class="mt-6 space-y-3 text-sm text-slate-400">
            <div class="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-900/70 px-3 py-2"><span>Queued campaigns</span><span class="font-semibold text-slate-200">24</span></div>
            <div class="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-900/70 px-3 py-2"><span>Pipeline velocity</span><span class="font-semibold text-slate-200">+18%</span></div>
            <div class="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-900/70 px-3 py-2"><span>Lead response SLA</span><span class="font-semibold text-slate-200">5 min</span></div>
          </div>
        </div>
      </div>`;
  }

  document.addEventListener("DOMContentLoaded", () => {
    renderGrowthHero();
    initCampaignComposer();
  });
})(window);
