// Source for fusion-light.svg and fusion-dark.svg. Needs the Inter and Inter Display fonts.
//   typst compile assets/fusion.typ assets/fusion-light.svg
//   typst compile --input theme=dark assets/fusion.typ assets/fusion-dark.svg
#import "@preview/lilaq:0.6.0" as lq

#let dark = sys.inputs.at("theme", default: "light") == "dark"
#let fg = if dark { rgb("#F2F2F2") } else { rgb("#0D0D09") }
#let muted = if dark { rgb("#8D9199") } else { rgb("#8B8B88") }
#let track = if dark { rgb("#262B33") } else { rgb("#E2E2DF") }
#let accent = rgb("#4576F5")

#set page(width: 660pt, height: auto, margin: (x: 2pt, y: 4pt), fill: none)
#set text(font: "Inter", size: 11pt, fill: fg)

// Each pair is (competitor, Fusion); each entry is (label, cost per run, score).
#let pairs = (
  (("Claude Code · Fable 5.1", 12.36, "62.2"), ("Devin Fusion · Fable 5.1 + SWE-2", 7.90, "61.7")),
  (("Codex · Astra 6", 7.47, "61.6"), ("Devin Fusion · Astra 6 + SWE-2", 4.54, "58.9")),
)
#let top = calc.max(..pairs.flatten().filter(v => type(v) == float))
#let saving(p) = str(calc.round((1 - p.at(1).at(1) / p.at(0).at(1)) * 100)) + "%"

#let money(v) = {
  let s = str(calc.round(v, digits: 2))
  let frac = s.split(".").at(1, default: "")
  "$" + s + if frac.len() == 0 { ".00" } else { "0" * (2 - frac.len()) }
}
#let figure = text.with(font: "Inter Display", size: 10.5pt, number-width: "tabular")

// One pair: label above each bar, bar on a full-width track, cost and score at the right.
#let bars(pair, width) = {
  let score-w = 44pt / width * top
  let rows = pair.enumerate().map(((i, r)) => (
    label: r.at(0), cost: r.at(1), score: r.at(2), fusion: i == 1, y: 1.5 - i,
  ))
  lq.diagram(
    width: width,
    height: 80pt,
    xlim: (0, top),
    ylim: (0, 2),
    grid: none,
    xaxis: none,
    yaxis: none,
    ..rows.map(r => lq.rect(0, r.y - 0.27, width: top, height: 0.14, radius: 3pt, stroke: none, fill: track)),
    ..rows.map(r => lq.rect(
      0, r.y - 0.27,
      width: r.cost, height: 0.14, radius: 3pt, stroke: none,
      fill: if r.fusion { accent } else { muted },
    )),
    ..rows.map(r => lq.place(0, r.y - 0.02, align: left + bottom, text(
      fill: if r.fusion { fg } else { muted },
      weight: if r.fusion { 500 } else { 400 },
      r.label,
    ))),
    ..rows.map(r => lq.place(top - score-w, r.y - 0.02, align: right + bottom, figure(
      fill: if r.fusion { fg } else { muted },
      money(r.cost),
    ))),
    ..rows.map(r => lq.place(top, r.y - 0.02, align: right + bottom, figure(fill: muted, r.score))),
  )
}

#grid(
  columns: (226pt, 1fr),
  column-gutter: 24pt,
  inset: (y: 6pt),
  align: horizon,
  ..pairs.map(p => (
    stack(
      spacing: 14pt,
      text(
        font: "Inter Display", size: 40pt, weight: 500, fill: accent, tracking: -0.04em,
        top-edge: "cap-height", bottom-edge: "baseline", saving(p),
      ),
      text(size: 10pt, fill: muted, "Lower cost than " + p.at(0).at(0).replace(" · ", " with ") + "."),
    ),
    bars(p, 406pt),
  )).intersperse((grid.hline(stroke: 0.6pt + track),)).flatten(),
)
