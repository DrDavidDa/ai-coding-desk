/* Full-frame context compressor.
 *
 * Frame order matches desk154-live.html .pack-frame index:
 *   0  01-idle.png         piston up
 *   1  03-feeding.png      paper in, piston still up
 *   2  04-compressing.png  piston down / hit (particles, 摘要)
 *   3  02-reward.png       capsule eject
 *
 * CSS .pack-frame uses opacity 35ms steps(1, end), so the hit frame
 * only becomes visible 35ms after it is selected. knockAt is that
 * delay: wood plays on the visible strike, not on the tap.
 */
(function (global) {
  const SAVE_KEY = "desk154PackTokens";
  const INITIAL = 0;
  const TIMELINE = [
    { f: 1, ms: 220 },
    { f: 2, ms: 200, knockAt: 35 },
    { f: 3, ms: 280, reward: true },
    { f: 0, ms: 160 }
  ];

  function formatTokens(n) {
    const units = ["", "K", "M", "B", "T", "Qa", "Qi"];
    let v = Number(n);
    if (!Number.isFinite(v) || v < 0) v = 0;
    let u = 0;
    while (v >= 1000 && u < units.length - 1) {
      v /= 1000;
      u++;
    }
    if (u === 0) return v === 0 ? "0K" : String(Math.round(v));
    let shown = Math.round(v * 10) / 10;
    if (shown >= 1000 && u < units.length - 1) {
      shown = Math.round(shown / 1000 * 10) / 10;
      u++;
    }
    const s = Number.isInteger(shown) ? String(shown) : shown.toFixed(1);
    return s + units[u];
  }

  function loadSaved() {
    const raw = Number(localStorage.getItem(SAVE_KEY));
    return Number.isFinite(raw) && raw >= 0 ? raw : INITIAL;
  }

  function Game() {
    this.totalTokens = loadSaved();
    this.pending = 0;
    this.busy = false;
    this.step = 0;
    this.stepAt = 0;
    this.pressUntil = 0;
    this.knocked = false;
    this.rng = 0xC05EED;
    this.stage = null;
    this.frames = [];
    this.totalEl = null;
    this.plusEl = null;
    this.counterEl = null;
    this.queueEl = null;
    this.onKnock = null;
  }

  Game.prototype.attach = function (opts) {
    this.stage = opts.stage;
    this.frames = opts.frames;
    this.totalEl = opts.total;
    this.plusEl = opts.plus;
    this.counterEl = opts.counter;
    this.queueEl = opts.queue;
    this.onKnock = opts.onKnock || null;
    this.show(0);
    this.drawTotal();
    this.drawQueue();
  };

  Game.prototype.rand = function (min, max) {
    this.rng = (Math.imul(1664525, this.rng) + 1013904223) >>> 0;
    return min + (this.rng % (max - min + 1));
  };

  Game.prototype.show = function (i) {
    this.frames.forEach(function (el, idx) {
      el.classList.toggle("active", idx === i);
    });
  };

  Game.prototype.drawTotal = function () {
    if (this.totalEl) this.totalEl.textContent = formatTokens(this.totalTokens);
  };

  Game.prototype.drawQueue = function () {
    if (!this.queueEl) return;
    this.queueEl.innerHTML = "";
    for (let i = 0; i < this.pending; i++) {
      this.queueEl.appendChild(document.createElement("i"));
    }
  };

  Game.prototype.fireKnock = function () {
    if (this.knocked) return;
    this.knocked = true;
    if (this.onKnock) this.onKnock();
  };

  Game.prototype.enterStep = function (now, step) {
    this.step = step;
    this.stepAt = now;
    this.knocked = false;
    const cur = TIMELINE[step];
    this.show(cur.f);
    if (cur.reward) this.reward();
    if (cur.knockAt === 0) this.fireKnock();
  };

  Game.prototype.reward = function () {
    const delta = this.rand(1000, 1500);
    this.totalTokens += delta;
    localStorage.setItem(SAVE_KEY, String(this.totalTokens));
    this.drawTotal();
    if (this.plusEl) this.plusEl.textContent = "+" + formatTokens(delta);
    if (this.counterEl) {
      this.counterEl.classList.remove("bump");
      void this.counterEl.offsetWidth;
      this.counterEl.classList.add("bump");
    }
    if (this.plusEl) {
      this.plusEl.classList.remove("show");
      void this.plusEl.offsetWidth;
      this.plusEl.classList.add("show");
    }
  };

  Game.prototype.startCycle = function (now) {
    this.busy = true;
    this.enterStep(now, 0);
  };

  Game.prototype.press = function (now) {
    if (this.stage) {
      this.stage.classList.add("press");
      this.pressUntil = now + 70;
    }
    if (this.busy) {
      this.pending = Math.min(8, this.pending + 1);
      this.drawQueue();
      return;
    }
    this.startCycle(now);
  };

  Game.prototype.reset = function () {
    this.totalTokens = INITIAL;
    this.pending = 0;
    this.busy = false;
    this.step = 0;
    this.knocked = false;
    localStorage.setItem(SAVE_KEY, String(this.totalTokens));
    this.show(0);
    this.drawTotal();
    this.drawQueue();
    if (this.plusEl) this.plusEl.classList.remove("show");
  };

  Game.prototype.tick = function (now) {
    if (this.stage && now >= this.pressUntil) this.stage.classList.remove("press");
    if (!this.busy) return;
    const cur = TIMELINE[this.step];
    const elapsed = now - this.stepAt;
    if (cur.knockAt != null && elapsed >= cur.knockAt) this.fireKnock();
    if (elapsed < cur.ms) return;
    if (this.step + 1 >= TIMELINE.length) {
      this.busy = false;
      this.show(0);
      if (this.pending > 0) {
        this.pending -= 1;
        this.drawQueue();
        this.startCycle(now);
      }
      return;
    }
    this.enterStep(now, this.step + 1);
  };

  global.DeskCompressor = { Game: Game, formatTokens: formatTokens, TIMELINE: TIMELINE };
})(window);
