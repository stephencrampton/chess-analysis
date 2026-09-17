"""Create a standalone browser UI for exploring analysis insights and moves."""

import argparse
import json
from pathlib import Path

import chess

from chess_analysis.filenames import timestamped_filename
from chess_analysis.summarize import (
    DEFAULT_LIMIT,
    DEFAULT_MIN_SAMPLES,
    action_for,
    build_insights,
    collect_segments,
    read_rows,
    segment_names,
)

TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Chess analysis explorer</title>
<style>
:root{--ink:#17211b;--muted:#68736b;--paper:#f4f0e7;--panel:#fffdf8;--line:#d9d4c9;--accent:#b34b32;--soft:#f5ded4;--light:#eadfca;--dark:#577b6b}*{box-sizing:border-box}body{margin:0;color:var(--ink);background:radial-gradient(circle at 85% 0,#fffaf0,var(--paper) 48%);font-family:Georgia,"Times New Roman",serif}.app{display:grid;grid-template-columns:minmax(260px,350px) 1fr;min-height:100vh}.side{padding:28px 22px;border-right:1px solid var(--line);background:#fffdf8c7}.eyebrow{margin:0 0 8px;color:var(--accent);font:700 11px ui-monospace,monospace;letter-spacing:.08em;text-transform:uppercase}h1{margin:0;font-size:clamp(28px,4vw,42px);line-height:.98}.intro{color:var(--muted);line-height:1.45;margin:14px 0 25px}.insights{display:grid;gap:9px}.insight{width:100%;padding:13px 14px;border:1px solid var(--line);border-radius:7px;background:var(--panel);color:var(--ink);text-align:left;cursor:pointer}.insight.active,.insight:hover{border-color:var(--accent);background:var(--soft)}.insight strong,.insight small{display:block}.insight small{margin-top:5px;color:var(--muted);font:12px ui-monospace,monospace}.main{max-width:1200px;padding:34px clamp(20px,5vw,64px)}.header{display:flex;justify-content:space-between;align-items:end;gap:18px;margin-bottom:24px}.header h2{margin:0;font-size:clamp(25px,4vw,40px)}.header p{margin:8px 0 0;color:var(--muted)}select{padding:9px;border:1px solid var(--line);border-radius:5px;background:var(--panel);color:var(--ink)}.workspace{display:grid;grid-template-columns:minmax(300px,610px) minmax(260px,1fr);gap:28px;align-items:start}.board-wrap{padding:10px;background:#263b32;box-shadow:0 16px 40px #17211b1f}.board{display:grid;grid-template-columns:repeat(8,1fr);aspect-ratio:1;overflow:hidden}.square{display:grid;place-items:center;position:relative;font:clamp(24px,7vw,62px)/1 "DejaVu Sans","Noto Sans Symbols 2",sans-serif}.light{background:var(--light)}.dark{background:var(--dark)}.played{box-shadow:inset 0 0 0 5px #b34b32c7}.best{box-shadow:inset 0 0 0 4px #fff59df0}.to:after{content:"";position:absolute;inset:12%;border:2px solid #b34b32d9;border-radius:50%}.piece{filter:drop-shadow(1px 2px 0 #0004)}.coords{display:flex;justify-content:space-between;padding:5px 4px 0;color:#d8e6d8;font:10px ui-monospace,monospace}.kicker{margin:0 0 8px;color:var(--accent);font:700 11px ui-monospace,monospace;text-transform:uppercase}.details h3{margin:0;font-size:clamp(26px,4vw,40px);line-height:1}.action{margin:14px 0 22px;padding:14px;border-left:4px solid var(--accent);background:var(--soft);line-height:1.45}.stats{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}.stat{padding:12px;border:1px solid var(--line);background:var(--panel)}.stat b{display:block;font-size:21px}.stat span{color:var(--muted);font:10px ui-monospace,monospace;text-transform:uppercase}.nav{display:flex;gap:8px;margin:15px 0}.nav button{padding:8px 13px;border:1px solid var(--line);border-radius:5px;background:var(--panel);cursor:pointer}.move{padding:17px;border-top:2px solid #2f6755;background:var(--panel)}.move h4{margin:0 0 8px;font-size:24px}.meta{color:var(--muted);font:12px/1.6 ui-monospace,monospace}.meta strong{color:var(--ink)}.note{color:var(--muted);font-size:13px;line-height:1.4}@media(max-width:850px){.app{grid-template-columns:1fr}.side{border:0;border-bottom:1px solid var(--line)}.insights{grid-template-columns:repeat(auto-fit,minmax(220px,1fr))}.workspace{grid-template-columns:1fr}.board-wrap{max-width:610px;margin:auto}.header{display:grid}}
</style></head><body><div class="app"><aside class="side"><p class="eyebrow">Pattern explorer</p><h1>Turn engine data into practice.</h1><p class="intro">Select a recurring weakness, then step through the positions that created the signal.</p><div class="insights" id="insights"></div></aside><main class="main"><div class="header"><div><p class="eyebrow">Move review</p><h2 id="title">Loading</h2><p id="subtitle"></p></div><select id="positions"></select></div><section class="workspace"><div class="board-wrap"><div class="board" id="board"></div><div class="coords"><span>a</span><span>b</span><span>c</span><span>d</span><span>e</span><span>f</span><span>g</span><span>h</span></div></div><section class="details"><p class="kicker">Selected pattern</p><h3 id="detail"></h3><div class="action" id="action"></div><div class="stats" id="stats"></div><div class="nav"><button id="prev">&#8592; Previous</button><button id="next">Next &#8594;</button></div><div class="move" id="move"></div><p class="note">Red marks the played move. Gold marks Stockfish's preferred move. The board shows the position before the selected move.</p></section></section></main></div><script>
const DATA=__DATA__, pieces={P:"♙",N:"♘",B:"♗",R:"♖",Q:"♕",K:"♔",p:"♟",n:"♞",b:"♝",r:"♜",q:"♛",k:"♚"};
const fallback={name:"All analyzed moves",dimension:"",action:"Review the positions with the largest evaluation losses.",moves:DATA.rows.length,error_rate:0,baseline_rate:0,average_loss:0};const insights=DATA.insights.length?DATA.insights:[fallback];const state={i:0,p:0};
const rows=()=>{let x=insights[state.i];return x.dimension?DATA.rows.filter(r=>r.tags[x.dimension]===x.name):DATA.rows};
const formatTime=value=>{if(value===""||value===null||value===undefined)return "not recorded";let seconds=Number(value);if(!Number.isFinite(seconds))return "not recorded";let minutes=Math.floor(seconds/60);let remainder=Math.round(seconds%60);if(remainder===60){minutes++;remainder=0}return `${minutes}:${String(remainder).padStart(2,"0")}`};
const idx=s=>s?56-(Number(s[1])-1)*8+s.charCodeAt(0)-97:-1;
function board(r){let cells=[];for(const rank of r.fen.split(" ")[0].split("/")){for(const c of rank){if(Number.isInteger(Number(c)))cells.push(...Array(Number(c)).fill(""));else cells.push(c)}}let pf=idx(r.played_from),pt=idx(r.played_to),bf=idx(r.best_from),bt=idx(r.best_to);document.getElementById("board").innerHTML=cells.map((p,i)=>{let c=["square",((Math.floor(i/8)+i)%2)?"dark":"light"];if(i===pf||i===pt)c.push("played");if(i===bf||i===bt)c.push("best");if(i===pt)c.push("to");return `<div class="${c.join(" ")}"><span class="piece">${pieces[p]||""}</span></div>`}).join("")}
function draw(){let x=insights[state.i],rs=rows();if(!rs.length)return;state.p=Math.min(state.p,rs.length-1);let r=rs[state.p];document.getElementById("title").textContent=x.name;document.getElementById("detail").textContent=x.name;document.getElementById("subtitle").textContent=`${rs.length} matching positions from the analysis CSV`;document.getElementById("action").textContent=x.action;document.getElementById("stats").innerHTML=`<div class="stat"><b>${x.error_rate.toFixed(1)}%</b><span>serious errors</span></div><div class="stat"><b>${x.baseline_rate.toFixed(1)}%</b><span>overall baseline</span></div><div class="stat"><b>${x.average_loss.toFixed(1)}</b><span>average loss</span></div><div class="stat"><b>${r.centipawn_loss.toFixed(0)} cp</b><span>selected loss</span></div>`;document.getElementById("positions").innerHTML=rs.map((v,i)=>`<option value="${i}">${i+1}. move ${v.move_number} ${v.move} · ${v.classification}</option>`).join("");document.getElementById("positions").value=state.p;document.getElementById("positions").onchange=e=>{state.p=Number(e.target.value);draw()};document.getElementById("move").innerHTML=`<h4>${r.move_number}. ${r.move}</h4><div class="meta"><strong>${r.classification}</strong> · ${r.phase} · ${r.piece} · ${r.color}<br>Stockfish preferred: <strong>${r.best_move||"not recorded"}</strong><br>Time used: <strong>${formatTime(r.time_used)}</strong> · Time left: <strong>${formatTime(r.time_left)}</strong><br>Opponent: ${r.opponent||"unknown"} · Result: ${r.result||"unknown"}</div>`;board(r);document.getElementById("insights").innerHTML=insights.map((v,i)=>`<button class="insight ${i===state.i?"active":""}" data-i="${i}"><strong>${v.name}</strong><small>${v.error_rate.toFixed(1)}% serious errors · ${v.moves} moves</small></button>`).join("");document.querySelectorAll(".insight").forEach(b=>b.onclick=()=>{state.i=Number(b.dataset.i);state.p=0;draw()})}
document.getElementById("prev").onclick=()=>{state.p=Math.max(0,state.p-1);draw()};document.getElementById("next").onclick=()=>{state.p=Math.min(rows().length-1,state.p+1);draw()};draw();
</script></body></html>"""


def move_squares(row, field):
    """Parse a SAN move from the row's pre-move position."""
    value = row.get(field, "")
    if not value:
        return None, None
    try:
        move = chess.Board(row["fen"]).parse_san(value.split()[0])
    except (ValueError, chess.InvalidMoveError, chess.IllegalMoveError):
        return None, None
    return chess.square_name(move.from_square), chess.square_name(move.to_square)


def browser_row(row):
    """Keep only fields used by the browser UI."""
    played_from, played_to = move_squares(row, "move")
    best_from, best_to = move_squares(row, "best_move")
    return {
        "result": row.get("result", ""),
        "color": row.get("color", ""),
        "opponent": row.get("opponent", ""),
        "time_used": row.get("time_since_my_last_move", ""),
        "time_left": row.get("my_time_remaining", ""),
        "move_number": row["move_number"],
        "phase": row.get("phase", ""),
        "piece": row.get("piece", ""),
        "move": row.get("move", ""),
        "best_move": row.get("best_move", ""),
        "classification": row.get("classification", ""),
        "centipawn_loss": row["centipawn_loss"],
        "fen": row["fen"],
        "played_from": played_from,
        "played_to": played_to,
        "best_from": best_from,
        "best_to": best_to,
        "tags": segment_names(row),
    }


def insight_dict(insight):
    """Convert an insight to JSON-friendly values."""
    segment, baseline = insight.segment, insight.baseline
    return {
        "dimension": insight.dimension,
        "name": segment.name,
        "moves": segment.moves,
        "error_rate": segment.serious_error_rate * 100,
        "baseline_rate": baseline.serious_error_rate * 100,
        "average_loss": segment.average_centipawn_loss,
        "action": action_for(insight),
    }


def generate_html(csv_file, min_samples, limit):
    """Build the standalone visualization document."""
    rows = list(read_rows(csv_file))
    baseline, grouped = collect_segments(rows)
    insights = build_insights(baseline, grouped, min_samples)[:limit]
    payload = {
        "rows": [browser_row(row) for row in rows],
        "insights": [insight_dict(i) for i in insights],
    }
    html = TEMPLATE.replace(
        "__DATA__", json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    )
    html = html.replace(
        "</style>",
        ".board{grid-template-rows:repeat(8,minmax(0,1fr));width:100%;aspect-ratio:1 / 1}</style>",
        1,
    )
    orientation_script = """<script>
const orientationObserver=new MutationObserver(() => {
  orientationObserver.disconnect();
  const row=rows()[state.p];
  const black=row&&row.color==="Black";
  if(black){
    const boardElement=document.getElementById("board");
    boardElement.replaceChildren(...Array.from(boardElement.children).reverse());
  }
    document.querySelector(".coords").innerHTML=(black?["h","g","f","e","d","c","b","a"]:["a","b","c","d","e","f","g","h"]).map(file=>`<span>${file}</span>`).join("");
  orientationObserver.observe(document.getElementById("board"),{childList:true});
});
const initialRow=rows()[state.p];
if(initialRow&&initialRow.color==="Black"){
  const boardElement=document.getElementById("board");
  boardElement.replaceChildren(...Array.from(boardElement.children).reverse());
}
document.querySelector(".coords").innerHTML=(initialRow&&initialRow.color==="Black"?["h","g","f","e","d","c","b","a"]:["a","b","c","d","e","f","g","h"]).map(file=>`<span>${file}</span>`).join("");
orientationObserver.observe(document.getElementById("board"),{childList:true});
</script>"""
    return html.replace("</body>", orientation_script + "</body>")


def main():
    parser = argparse.ArgumentParser(
        description="Create a browser UI for analysis insights and moves."
    )
    parser.add_argument(
        "csv_file", nargs="?", help="analysis CSV (default: newest analysis_*.csv)"
    )
    parser.add_argument("--min-samples", type=int, default=DEFAULT_MIN_SAMPLES)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--output", help="HTML output file")
    args = parser.parse_args()
    if args.min_samples < 1 or args.limit < 1:
        parser.error("--min-samples and --limit must be positive")
    csv_file = args.csv_file
    if csv_file is None:
        candidates = sorted(
            Path.cwd().glob("analysis_*.csv"), key=lambda p: p.stat().st_mtime
        )
        if not candidates:
            parser.error("no analysis CSV found; pass a CSV filename")
        csv_file = str(candidates[-1])
    output = args.output or timestamped_filename("visualization", "html")
    Path(output).write_text(
        generate_html(csv_file, args.min_samples, args.limit), encoding="utf-8"
    )
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
