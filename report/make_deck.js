// Project deck — "control chart" design system. Builds the presentation.
const pptxgen = require("pptxgenjs");
const path = require("path");
const A = (n) => path.join(__dirname, "deck_assets", n);

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
const W = 13.333, H = 7.5, M = 0.75;

// ---- design tokens ------------------------------------------------------
const INK = "1A2B30", INK2 = "223840", PORC = "ECEFEF", PAPER = "F5F7F6",
      TEAL = "2E6E63", AMBER = "C77400", STEEL = "5E7A99",
      MUT = "71807F", INKMUT = "93A0A0", HAIR = "CDD4D3", HAIRDK = "38484E",
      ONINK = "E7ECEB", ONINKMUT = "9DAEAD";
const HEAD = "Cambria", BODY = "Calibri";

pres.theme = { headFontFace: HEAD, bodyFontFace: BODY };
pres.author = "A. Hannish Reddi, B. Keshav, E. Sai Mohan";
pres.company = "CBIT AI and DS";

// ---- masters ------------------------------------------------------------
pres.defineSlideMaster({ title: "COVER", background: { color: PORC } });
pres.defineSlideMaster({ title: "DARK", background: { color: INK } });
pres.defineSlideMaster({
  title: "CONTENT", background: { color: PORC },
  objects: [
    { text: { text: "", options: { placeholder: "title", x: M, y: 0.52, w: W - 2 * M, h: 0.8,
      color: INK, fontSize: 29, bold: false, fontFace: HEAD, align: "left", valign: "middle" } } },
    { text: { text: "Adaptive anomaly detection in network traffic", options: {
      x: M, y: H - 0.42, w: 7, h: 0.3, color: INKMUT, fontSize: 9, align: "left", fontFace: BODY } } },
  ],
  slideNumber: { x: W - 1.0, y: H - 0.42, w: 0.5, h: 0.3, color: INKMUT, fontSize: 9, align: "right" },
});

// ---- helpers ------------------------------------------------------------
function hline(s, x, y, w, color = HAIR, h = 0.012) {
  s.addShape(pres.ShapeType.rect, { x, y, w, h, fill: { color }, line: { type: "none" } });
}
function vline(s, x, y, h, color = HAIR, w = 0.012) {
  s.addShape(pres.ShapeType.rect, { x, y, w, h, fill: { color }, line: { type: "none" } });
}
function reading(s, x, y, w, num, label, color = INK, numSize = 48, onDark = false) {
  s.addText(num, { x, y, w, h: numSize / 60, isTextBox: true, margin: 0, align: "left",
    color, fontSize: numSize, bold: true, fontFace: HEAD });
  s.addText(label, { x, y: y + numSize / 60 - 0.02, w, h: 0.55, isTextBox: true, margin: 0,
    align: "left", color: onDark ? ONINKMUT : MUT, fontSize: 12.5, fontFace: BODY });
}
function body(s, runs, opt) {
  s.addText(runs, Object.assign({ isTextBox: true, margin: 0, fontFace: BODY,
    color: INK, fontSize: 15, align: "left", lineSpacingMultiple: 1.12 }, opt));
}

// ======================================================================
// 1. COVER
// ======================================================================
let s = pres.addSlide({ masterName: "COVER" });
s.addImage({ path: A("hero.png"), x: 0, y: 0.0, w: W, h: W / 3.456 * 1.0 * 0.0 + 3.86,
  sizing: { type: "contain", w: W, h: 3.86 } });
// title block lower-left
s.addText("Adaptive Network Traffic\nAnomaly Detection", { x: M, y: 4.35, w: 11.8, h: 1.7,
  isTextBox: true, margin: 0, color: INK, fontSize: 46, bold: true, fontFace: HEAD,
  align: "left", lineSpacingMultiple: 0.98 });
body(s, "Catching the anomalies that volume monitors miss — with lightweight online statistics.",
  { x: M, y: 6.15, w: 10.5, h: 0.4, color: MUT, fontSize: 16, italic: true });
hline(s, M, 6.75, W - 2 * M, HAIR);
body(s, [
  { text: "A. Hannish Reddi,   B. Keshav,   E. Sai Mohan", options: { color: INK, fontSize: 12.5, bold: true, breakLine: true } },
  { text: "Dept. of AI & Data Science, CBIT Hyderabad      Computer Networks (22ITC10N)", options: { color: MUT, fontSize: 11 } },
], { x: M, y: 6.9, w: 11.8, h: 0.5 });
s.addNotes("Our question: can a cheap, training-free statistical detector catch the network anomalies that simple volume monitors miss? The graphic shows the idea — a band of normal traffic that drifts over time, with a few anomalies breaching it.");

// ======================================================================
// 2. THE PROBLEM
// ======================================================================
s = pres.addSlide({ masterName: "CONTENT" });
s.addText("The quiet anomalies are the hard ones", { placeholder: "title" });
body(s, "A fixed threshold catches a tenfold spike easily. It cannot see a port scan that moves almost no traffic, or a shift in the protocol mix that moves none at all. And on a busy but harmless flash crowd, a naive monitor cries wolf.",
  { x: M, y: 1.7, w: 6.5, h: 2.2, fontSize: 17, lineSpacingMultiple: 1.25 });
body(s, [
  { text: "The gap.  ", options: { bold: true, color: INK, fontSize: 15.5 } },
  { text: "Cheap monitors are blind to the last two kinds. Accurate ML detectors see them, but need training, memory, and retraining.", options: { color: MUT, fontSize: 15.5 } },
], { x: M, y: 4.35, w: 6.5, h: 1.6, lineSpacingMultiple: 1.2 });
// right: three behaviours, color-coded by difficulty, hairline separated
const beh = [
  ["Flood / DDoS", "Volume spikes — easy to see", TEAL],
  ["Port scan", "Many destination ports, little volume", AMBER],
  ["Protocol shift", "The traffic mix changes, volume doesn't", AMBER],
];
let by = 1.85;
vline(s, 8.0, 1.75, 4.1, HAIR);
beh.forEach((b, i) => {
  s.addShape(pres.ShapeType.ellipse, { x: 8.4, y: by + 0.08, w: 0.18, h: 0.18, fill: { color: b[2] }, line: { type: "none" } });
  s.addText(b[0], { x: 8.75, y: by, w: 4.0, h: 0.4, isTextBox: true, margin: 0, color: INK, fontSize: 17, bold: true, fontFace: HEAD });
  body(s, b[1], { x: 8.75, y: by + 0.42, w: 3.9, h: 0.5, color: MUT, fontSize: 13.5 });
  if (i < beh.length - 1) hline(s, 8.4, by + 1.05, 4.2, HAIR);
  by += 1.35;
});
s.addNotes("The hard part is not the dramatic spike — it is the stealthy scan and the protocol shift, which move little or no volume, while not firing on normal busy periods.");

// ======================================================================
// 3. RESEARCH QUESTION (statement)
// ======================================================================
s = pres.addSlide({ masterName: "CONTENT" });
s.addText("The question", { placeholder: "title" });
s.addText([
  { text: "Can a ", options: {} },
  { text: "training-free", options: {} },
  { text: " statistical detector catch what volume monitors miss, keep false alarms low, and stay accurate when normal traffic ", options: {} },
  { text: "drifts", options: {} },
  { text: "?", options: {} },
], { x: M, y: 2.0, w: 11.4, h: 2.4, isTextBox: true, margin: 0, color: INK, fontSize: 36,
  fontFace: HEAD, align: "left", lineSpacingMultiple: 1.1 });
hline(s, M, 4.9, 2.4, AMBER, 0.03);
body(s, [
  { text: "What's missing in practice: ", options: { bold: true, color: INK, fontSize: 16 } },
  { text: "a detector that is at once lightweight, multi-feature, and robust to non-stationary traffic — and a clear account of which of those properties actually earns the detection.", options: { color: MUT, fontSize: 16 } },
], { x: M, y: 5.2, w: 10.8, h: 1.3, lineSpacingMultiple: 1.25 });
s.addNotes("This is the honest framing of the whole project: we separate what each property contributes rather than claiming one method wins everything.");

// ======================================================================
// 4. FIVE FAMILIES (color encodes difficulty)
// ======================================================================
s = pres.addSlide({ masterName: "CONTENT" });
s.addText("Five anomaly families we detect", { placeholder: "title" });
const fam = [
  ["Burst", "Volumetric surge from a few sources", TEAL],
  ["SYN flood", "Many small packets; the SYN ratio climbs", TEAL],
  ["Port scan", "Many destination ports; little volume", AMBER],
  ["Protocol shift", "UDP share jumps; total volume stays normal", AMBER],
  ["Slow ramp", "Gradual growth over a long period", AMBER],
];
let fy = 1.75;
fam.forEach((f, i) => {
  s.addShape(pres.ShapeType.rect, { x: M, y: fy + 0.07, w: 0.1, h: 0.56, fill: { color: f[2] }, line: { type: "none" } });
  s.addText(f[0], { x: M + 0.35, y: fy, w: 3.4, h: 0.7, isTextBox: true, margin: 0, valign: "middle",
    color: INK, fontSize: 19, bold: true, fontFace: HEAD });
  body(s, f[1], { x: 4.7, y: fy, w: 8.0, h: 0.7, color: MUT, fontSize: 15.5, valign: "middle" });
  if (i < fam.length - 1) hline(s, M, fy + 0.84, W - 2 * M, HAIR);
  fy += 0.95;
});
s.addShape(pres.ShapeType.ellipse, { x: M, y: 6.75, w: 0.14, h: 0.14, fill: { color: TEAL }, line: { type: "none" } });
body(s, "Volumetric and easy", { x: M + 0.25, y: 6.68, w: 2.6, h: 0.3, color: MUT, fontSize: 12 });
s.addShape(pres.ShapeType.ellipse, { x: 3.1, y: 6.75, w: 0.14, h: 0.14, fill: { color: AMBER }, line: { type: "none" } });
body(s, "Non-volumetric — the real test", { x: 3.35, y: 6.68, w: 4, h: 0.3, color: MUT, fontSize: 12 });
s.addNotes("These five are injected into the simulator with ground-truth labels. The amber families — scan, protocol shift — are what separate multivariate detectors from volume monitors.");

// ======================================================================
// 5. PIPELINE (a real sequence -> arrows ok)
// ======================================================================
s = pres.addSlide({ masterName: "CONTENT" });
s.addText("One pipeline, simulated and real", { placeholder: "title" });
const steps = [["Traffic", "flows / packets"], ["Window", "1-sec or 1-min bins"],
  ["Eight features", "logs + ratios"], ["Detector", "causal score"], ["Alarm", "threshold + events"]];
const sw = 2.18, gap = 0.52, startx = (W - (5 * sw + 4 * gap)) / 2;
steps.forEach((st, i) => {
  const x = startx + i * (sw + gap), hot = i === 3;
  s.addShape(pres.ShapeType.roundRect, { x, y: 2.5, w: sw, h: 1.35, rectRadius: 0.06,
    fill: { color: hot ? AMBER : PAPER }, line: { color: hot ? AMBER : HAIR, width: 1 } });
  s.addText(st[0], { x, y: 2.68, w: sw, h: 0.5, isTextBox: true, margin: 0, align: "center",
    color: hot ? "FFFFFF" : INK, fontSize: 17, bold: true, fontFace: HEAD });
  s.addText(st[1], { x, y: 3.2, w: sw, h: 0.45, isTextBox: true, margin: 0, align: "center",
    color: hot ? "F4E6D5" : MUT, fontSize: 12.5, fontFace: BODY });
  if (i < 4) s.addText("→", { x: x + sw, y: 2.5, w: gap, h: 1.35, isTextBox: true, margin: 0,
    align: "center", valign: "middle", color: HAIR === HAIR ? MUT : MUT, fontSize: 20 });
});
body(s, [
  { text: "The same causal pipeline runs on simulated and on real CIC-IDS2017 traffic. ", options: { color: INK, fontSize: 16 } },
  { text: "Two ratio features — packets-per-source and bytes-per-packet — are what expose the non-volumetric attacks.", options: { color: MUT, fontSize: 16 } },
], { x: M, y: 4.6, w: W - 2 * M, h: 1.0, align: "center", lineSpacingMultiple: 1.25 });
s.addNotes("Using one pipeline for both data sources makes simulated and real results directly comparable. The detector step is highlighted because that is where our contribution sits.");

// ======================================================================
// 6. DETECTORS (comparison table — legitimate here)
// ======================================================================
s = pres.addSlide({ masterName: "CONTENT" });
s.addText("Six detectors, one honest comparison", { placeholder: "title" });
const det = [
  ["Fixed threshold", "1 feature (volume)", "baseline", false],
  ["Moving average", "1 feature (volume)", "baseline", false],
  ["Z-score (static)", "1 feature (volume)", "baseline", false],
  ["Mahalanobis (static)", "8 features", "strong baseline", false],
  ["Isolation Forest", "8 features", "heavy-ML reference", false],
  ["Adaptive (proposed)", "8 features, online", "proposed", true],
];
const tx = M, tw = 7.9, c1 = 3.5, c2 = 2.6, ry0 = 1.85, rh = 0.62;
body(s, "Detector", { x: tx, y: ry0 - 0.42, w: c1, h: 0.35, color: MUT, fontSize: 12, bold: true });
body(s, "Features", { x: tx + c1, y: ry0 - 0.42, w: c2, h: 0.35, color: MUT, fontSize: 12, bold: true });
body(s, "Role", { x: tx + c1 + c2, y: ry0 - 0.42, w: tw - c1 - c2, h: 0.35, color: MUT, fontSize: 12, bold: true });
hline(s, tx, ry0 - 0.05, tw, INK, 0.02);
det.forEach((d, i) => {
  const y = ry0 + i * rh, col = d[3] ? AMBER : INK;
  s.addText(d[0], { x: tx, y, w: c1, h: rh, isTextBox: true, margin: 0, valign: "middle",
    color: col, fontSize: 15.5, bold: d[3], fontFace: HEAD });
  body(s, d[1], { x: tx + c1, y, w: c2, h: rh, color: d[3] ? INK : MUT, fontSize: 14, valign: "middle" });
  body(s, d[2], { x: tx + c1 + c2, y, w: tw - c1 - c2, h: rh, color: d[3] ? AMBER : MUT, fontSize: 14, valign: "middle", bold: d[3] });
  if (i < det.length - 1) hline(s, tx, y + rh, tw, HAIR);
});
vline(s, 9.1, 1.85, 4.3, HAIR);
body(s, [
  { text: "Why two extra detectors?\n\n", options: { bold: true, color: INK, fontSize: 16, fontFace: HEAD } },
  { text: "Static Mahalanobis and the Isolation Forest are controls. They let us attribute every gain — to multi-feature scoring, to online adaptation, or to both — instead of simply declaring a winner.", options: { color: MUT, fontSize: 14.5 } },
], { x: 9.45, y: 1.9, w: 3.2, h: 4.2, isTextBox: true, margin: 0, lineSpacingMultiple: 1.2, valign: "top" });
s.addNotes("The honesty controls matter for the viva: the big win turns out to be multi-feature scoring, shared by two detectors — not something unique to ours.");

// ======================================================================
// 7. PROPOSED DETECTOR
// ======================================================================
s = pres.addSlide({ masterName: "CONTENT" });
s.addText("The proposed detector", { placeholder: "title" });
body(s, "An online estimate of the mean m and covariance S of the eight features. The score is how far a window sits from normal:",
  { x: M, y: 1.7, w: 7.2, h: 1.0, fontSize: 16, color: INK, lineSpacingMultiple: 1.2 });
s.addShape(pres.ShapeType.roundRect, { x: M, y: 2.75, w: 7.2, h: 1.1, rectRadius: 0.06,
  fill: { color: PAPER }, line: { color: HAIR, width: 1 } });
s.addText("s  =  √ (xₜ − m)ᵀ S⁻¹ (xₜ − m) / p", { x: M, y: 2.75, w: 7.2, h: 1.1, isTextBox: true,
  margin: 0, align: "center", valign: "middle", color: INK, fontSize: 22, italic: true, fontFace: HEAD });
body(s, [{ text: "The gated update — the idea that makes it work", options: { bold: true, color: INK, fontSize: 16, fontFace: HEAD } }],
  { x: M, y: 4.2, w: 11.8, h: 0.4 });
// two steps (a real sequence)
const gsteps = [
  ["Normal window", "m and S update as usual — the baseline tracks slow, honest change."],
  ["Suspicious window", "the mean barely creeps and the covariance freezes — an attack cannot become the new normal."],
];
let gy = 4.75;
gsteps.forEach((g, i) => {
  s.addShape(pres.ShapeType.ellipse, { x: M, y: gy, w: 0.4, h: 0.4, fill: { color: i ? AMBER : TEAL }, line: { type: "none" } });
  s.addText(String(i + 1), { x: M, y: gy, w: 0.4, h: 0.4, isTextBox: true, margin: 0, align: "center", valign: "middle", color: "FFFFFF", fontSize: 15, bold: true, fontFace: HEAD });
  s.addText(g[0], { x: M + 0.6, y: gy - 0.03, w: 3.0, h: 0.45, isTextBox: true, margin: 0, color: INK, fontSize: 15.5, bold: true, fontFace: HEAD });
  body(s, g[1], { x: M + 3.5, y: gy - 0.03, w: 9.0, h: 0.6, color: MUT, fontSize: 14.5, valign: "top" });
  gy += 0.82;
});
// right readings
vline(s, 9.1, 1.7, 2.3, HAIR);
reading(s, 9.45, 1.75, 3.2, "72", "numbers of state — no stored history", INK, 40);
reading(s, 9.45, 2.95, 3.2, "0", "training passes required", TEAL, 40);
s.addNotes("The gating is the contribution. Without it an earlier version let attacks inflate the baseline and went blind — the ablation shows exactly that.");

// ======================================================================
// 8. EXPERIMENTAL SETUP (two columns, no cards)
// ======================================================================
s = pres.addSlide({ masterName: "CONTENT" });
s.addText("How we tested it", { placeholder: "title" });
vline(s, W / 2, 1.8, 3.6, HAIR);
s.addText("Simulated — for ground truth", { x: M, y: 1.75, w: 5.5, h: 0.45, isTextBox: true, margin: 0, color: TEAL, fontSize: 17, bold: true, fontFace: HEAD });
body(s, "6000 one-second windows: a benign daily cycle, noise, and realistic flash crowds. Fourteen labelled anomaly events per trace across the five families, with an optional drift control. Tuned on development seeds; reported on 30 untouched held-out seeds.",
  { x: M, y: 2.35, w: 5.6, h: 3.0, fontSize: 15.5, color: INK, lineSpacingMultiple: 1.25 });
s.addText("Real — CIC-IDS2017", { x: W / 2 + 0.4, y: 1.75, w: 5.5, h: 0.45, isTextBox: true, margin: 0, color: AMBER, fontSize: 17, bold: true, fontFace: HEAD });
body(s, "The official labelled flow captures (checksum-verified): the Friday port-scan and DDoS traffic, aggregated to one-minute windows. The method is frozen — only the alarm threshold is calibrated on a benign period, as a deployed monitor would be.",
  { x: W / 2 + 0.4, y: 2.35, w: 5.6, h: 3.0, fontSize: 15.5, color: INK, lineSpacingMultiple: 1.25 });
hline(s, M, 5.75, W - 2 * M, HAIR);
body(s, [
  { text: "Measured by  ", options: { bold: true, color: INK, fontSize: 14.5 } },
  { text: "window and event metrics, 95% confidence intervals, paired Wilcoxon tests with Holm correction, and threshold-free ROC and PR on the real data.", options: { color: MUT, fontSize: 14.5 } },
], { x: M, y: 5.95, w: W - 2 * M, h: 0.8, lineSpacingMultiple: 1.2 });
s.addNotes("Strict seed hygiene: debug seeds were discarded; the final numbers come from seeds the method never saw.");

// ======================================================================
// 9. MAIN RESULT (figure + big-number readings)
// ======================================================================
s = pres.addSlide({ masterName: "CONTENT" });
s.addText("Multivariate scoring wins across the board", { placeholder: "title" });
s.addImage({ path: A("f1.png"), x: M, y: 1.7, w: 7.4, h: 4.55, sizing: { type: "contain", w: 7.4, h: 4.55 } });
vline(s, 8.75, 1.9, 4.2, HAIR);
reading(s, 9.1, 1.95, 3.6, "0.924", "Event F1 — the best of six detectors", AMBER, 50);
reading(s, 9.1, 3.35, 3.6, "+0.19–0.37", "F1 over every volume-only baseline (p < 0.0001)", INK, 36);
reading(s, 9.1, 4.75, 3.6, "0.11", "false alarms per 1,000 windows — the lowest", TEAL, 44);
s.addNotes("Headline: the two multivariate detectors clear every single-feature baseline by a wide, significant margin, and the proposed detector raises the fewest false alarms.");

// ======================================================================
// 10. DRIFT FINDING (dark statement)
// ======================================================================
s = pres.addSlide({ masterName: "DARK" });
s.addText("The finding that matters", { x: M, y: 0.52, w: 11, h: 0.8, isTextBox: true, margin: 0,
  color: "FFFFFF", fontSize: 29, fontFace: HEAD, valign: "middle" });
// light inset panel for the figure
s.addShape(pres.ShapeType.roundRect, { x: M, y: 1.6, w: 6.5, h: 4.9, rectRadius: 0.05, fill: { color: PORC }, line: { type: "none" } });
s.addImage({ path: A("drift.png"), x: M + 0.25, y: 1.8, w: 6.0, h: 4.5, sizing: { type: "contain", w: 6.0, h: 4.5 } });
s.addText("When normal traffic drifts, the static model mis-calibrates.\nThe online detector tracks the change.",
  { x: 7.6, y: 1.9, w: 5.1, h: 1.7, isTextBox: true, margin: 0, color: ONINK, fontSize: 21, fontFace: HEAD, lineSpacingMultiple: 1.1 });
hline(s, 7.6, 3.75, 2.2, AMBER, 0.03);
reading(s, 7.6, 3.95, 5.1, "+0.118", "Event F1 over the best static baseline at the strongest drift (Wilcoxon p = 0.002)", AMBER, 46, true);
body(s, "In stationary traffic the two tie (p = 0.90). Online adaptation earns its keep only when traffic is non-stationary — the realistic case for a monitor left running for days.",
  { x: 7.6, y: 5.55, w: 5.1, h: 1.4, color: ONINKMUT, fontSize: 14, lineSpacingMultiple: 1.2 });
s.addNotes("This is the central, defensible claim. We do not overclaim a blanket win — adaptation wins specifically under drift, and we show exactly that.");

// ======================================================================
// 11. PER-TYPE
// ======================================================================
s = pres.addSlide({ masterName: "CONTENT" });
s.addText("Where the advantage comes from", { placeholder: "title" });
s.addImage({ path: A("pertype.png"), x: M, y: 1.75, w: 7.6, h: 4.3, sizing: { type: "contain", w: 7.6, h: 4.3 } });
vline(s, 9.0, 1.9, 4.0, HAIR);
body(s, [
  { text: "Scans and protocol shifts\n", options: { bold: true, color: INK, fontSize: 16, fontFace: HEAD } },
  { text: "are caught only by the multivariate detectors — the volume monitors score zero.\n\n", options: { color: MUT, fontSize: 15 } },
  { text: "Slow ramps\n", options: { bold: true, color: INK, fontSize: 16, fontFace: HEAD } },
  { text: "are the proposed detector's weak point: its own adaptation absorbs a gradual attack.", options: { color: MUT, fontSize: 15 } },
], { x: 9.35, y: 1.95, w: 3.3, h: 4.2, isTextBox: true, margin: 0, lineSpacingMultiple: 1.2 });
s.addNotes("The heatmap makes the mechanism visible — the win is on the two non-volumetric columns. We show the slow-ramp weakness openly rather than hiding it.");

// ======================================================================
// 12. REAL DATA
// ======================================================================
s = pres.addSlide({ masterName: "CONTENT" });
s.addText("It holds on real traffic", { placeholder: "title" });
s.addImage({ path: A("roc.png"), x: M, y: 1.85, w: 7.8, h: 4.0, sizing: { type: "contain", w: 7.8, h: 4.0 } });
vline(s, 9.0, 1.9, 4.2, HAIR);
s.addText("Port scan", { x: 9.35, y: 1.95, w: 3.3, h: 0.4, isTextBox: true, margin: 0, color: AMBER, fontSize: 16, bold: true, fontFace: HEAD });
body(s, "Multivariate: ROC-AUC 0.999, recall 1.0.  Volume monitors miss most of it (recall 0.4).",
  { x: 9.35, y: 2.35, w: 3.3, h: 1.2, color: MUT, fontSize: 14.5, lineSpacingMultiple: 1.2 });
s.addText("DDoS", { x: 9.35, y: 3.75, w: 3.3, h: 0.4, isTextBox: true, margin: 0, color: TEAL, fontSize: 16, bold: true, fontFace: HEAD });
body(s, "An easy volumetric case — even a fixed threshold is perfect; the multivariate detectors are close behind.",
  { x: 9.35, y: 4.15, w: 3.3, h: 1.3, color: MUT, fontSize: 14.5, lineSpacingMultiple: 1.2 });
hline(s, 9.35, 5.5, 3.1, HAIR);
body(s, "Each capture is ~1 hour and stationary, so adaptive ties static here — as the simulation predicts.",
  { x: 9.35, y: 5.65, w: 3.3, h: 0.9, color: INK, fontSize: 13.5, italic: true, lineSpacingMultiple: 1.2 });
s.addNotes("The simulated finding reappears on real traffic: multivariate scoring catches the stealthy port scan.");

// ======================================================================
// 13. ABLATION & COST
// ======================================================================
s = pres.addSlide({ masterName: "CONTENT" });
s.addText("What earns its place — and what we cut", { placeholder: "title" });
s.addImage({ path: A("ablation.png"), x: M, y: 1.75, w: 7.2, h: 4.2, sizing: { type: "contain", w: 7.2, h: 4.2 } });
vline(s, 8.5, 1.9, 2.5, HAIR);
body(s, [
  { text: "Gated update — essential.  ", options: { bold: true, color: INK, fontSize: 15 } },
  { text: "0.91 → 0.82 without it.\n", options: { color: MUT, fontSize: 15 } },
  { text: "Full covariance — matters under drift.\n", options: { bold: true, color: INK, fontSize: 15 } },
  { text: "Persistence & CUSUM — ", options: { bold: true, color: INK, fontSize: 15 } },
  { text: "tested, discarded.", options: { color: MUT, fontSize: 15 } },
], { x: 8.85, y: 1.95, w: 3.9, h: 2.3, isTextBox: true, margin: 0, lineSpacingMultiple: 1.35 });
hline(s, 8.85, 4.4, 3.7, HAIR);
reading(s, 8.85, 4.6, 3.9, "~33 µs", "per window — about 30,000 windows per second", TEAL, 40);
s.addNotes("The ablation justifies every design choice with data, including three features we removed. Lightweight holds on memory and the absence of retraining — the constraints that matter for a long-running monitor.");

// ======================================================================
// 14. CONCLUSION (dark)
// ======================================================================
s = pres.addSlide({ masterName: "DARK" });
s.addText("What we showed", { x: M, y: 0.6, w: 11, h: 0.8, isTextBox: true, margin: 0,
  color: "FFFFFF", fontSize: 30, fontFace: HEAD, valign: "middle" });
s.addText([
  { text: "Multi-feature statistical scoring", options: { color: ONINK, bold: true, fontFace: HEAD } },
  { text: " defeats non-volumetric attacks — in simulation and on real traffic. ", options: { color: ONINK } },
  { text: "Online adaptation", options: { color: ONINK, bold: true, fontFace: HEAD } },
  { text: " ties the static baseline when traffic is steady and wins when it drifts. No training; 72 numbers of state.", options: { color: ONINK } },
], { x: M, y: 1.7, w: 11.6, h: 1.8, isTextBox: true, margin: 0, fontSize: 21, lineSpacingMultiple: 1.25, align: "left" });
hline(s, M, 3.85, W - 2 * M, HAIRDK);
s.addText("Where it goes next", { x: M, y: 4.1, w: 11, h: 0.4, isTextBox: true, margin: 0, color: ONINKMUT, fontSize: 14, bold: true });
const fut = ["A real-data drift study on multi-day captures",
  "A two-timescale variant to fix the slow-ramp weakness",
  "An incremental covariance inverse to scale to larger feature sets"];
let fuy = 4.55;
fut.forEach((t) => {
  s.addShape(pres.ShapeType.ellipse, { x: M, y: fuy + 0.08, w: 0.12, h: 0.12, fill: { color: AMBER }, line: { type: "none" } });
  s.addText(t, { x: M + 0.35, y: fuy, w: 11, h: 0.35, isTextBox: true, margin: 0, color: ONINK, fontSize: 15, fontFace: BODY });
  fuy += 0.5;
});
s.addText("Thank you", { x: M, y: 6.35, w: 6, h: 0.5, isTextBox: true, margin: 0, color: AMBER, fontSize: 20, bold: true, italic: true, fontFace: HEAD });
s.addText("A. Hannish Reddi    B. Keshav    E. Sai Mohan", { x: 6.5, y: 6.45, w: 6.3, h: 0.4,
  isTextBox: true, margin: 0, align: "right", color: ONINKMUT, fontSize: 12, fontFace: BODY });
s.addNotes("Summary for the panel: cheap and multivariate beats cheap and single-feature everywhere; adaptation is the piece that keeps a long-running monitor honest under drift.");

pres.writeFile({ fileName: path.join(__dirname, "CN_AnomalyDetection_Presentation.pptx") })
  .then(f => console.log("wrote", f));
