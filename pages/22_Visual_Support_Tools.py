<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Visual Support Builder · CLC-LBU</title>
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=Nunito+Sans:wght@400;600;700&display=swap" rel="stylesheet">
<style>
:root {
  --teal:     #1A5C78; --teal-lt:#2A8AAF; --teal-bg:#EBF5FA;
  --amber:    #D4860A; --amber-lt:#E8A832; --amber-bg:#FEF7EA;
  --green:    #2D7D4F; --green-bg:#E8F5EE;
  --red:      #C0392B; --red-bg:#FDF0EF;
  --purple:   #5A3B8C; --purple-bg:#F2EEF8;
  --navy:     #1A2E44;
  --cream:    #F7F9FB;
  --white:    #FFFFFF;
  --border:   #DDE6EE;
  --text:     #1A2E44;
  --text-md:  #4A5568;
  --text-sm:  #718096;
  --shadow:   0 2px 12px rgba(0,0,0,.08);
  --radius:   12px; --radius-sm:8px; --radius-lg:16px;
  --font:     'Nunito', sans-serif;
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html{font-size:15px}
body{font-family:var(--font);background:var(--cream);color:var(--text);min-height:100vh}
button,input,textarea,select{font-family:var(--font)}
button{cursor:pointer}

/* ── Header ── */
.app-header{background:linear-gradient(135deg,var(--teal) 0%,#0F3D54 100%);color:#fff;padding:.7rem 1.5rem;display:flex;align-items:center;gap:.85rem;box-shadow:0 3px 16px rgba(0,0,0,.18);position:sticky;top:0;z-index:100}
.app-header .logo{font-size:1.6rem;line-height:1}
.app-header h1{font-size:1.15rem;font-weight:900;letter-spacing:-.02em}
.app-header .sub{font-size:.72rem;opacity:.72;margin-top:.1rem}
.hdr-spacer{flex:1}
.hdr-student{background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.25);border-radius:20px;padding:.3rem .9rem;font-size:.8rem;font-weight:700;cursor:pointer;transition:background .2s;display:flex;align-items:center;gap:.4rem}
.hdr-student:hover{background:rgba(255,255,255,.25)}
.hdr-badge{background:var(--amber);color:#fff;border-radius:20px;padding:.25rem .75rem;font-size:.75rem;font-weight:800;cursor:pointer;display:flex;align-items:center;gap:.35rem}
.hdr-btn{background:rgba(255,255,255,.15);border:none;color:#fff;width:34px;height:34px;border-radius:50%;font-size:1rem;display:flex;align-items:center;justify-content:center;transition:background .2s}
.hdr-btn:hover{background:rgba(255,255,255,.28)}

/* ── Tabs ── */
.tabs-nav{background:#fff;border-bottom:2px solid var(--border);display:flex;overflow-x:auto;padding:0 1rem;position:sticky;top:56px;z-index:99;scrollbar-width:none}
.tabs-nav::-webkit-scrollbar{display:none}
.tab-btn{background:none;border:none;padding:.8rem 1rem;font-size:.8rem;font-weight:700;color:var(--text-md);border-bottom:3px solid transparent;white-space:nowrap;margin-bottom:-2px;transition:all .2s;display:flex;align-items:center;gap:.35rem}
.tab-btn:hover{color:var(--teal)}
.tab-btn.active{color:var(--teal);border-bottom-color:var(--teal)}
.tab-icon{font-size:.95rem}

/* ── Panels ── */
.tab-panel{display:none;padding:1.5rem;max-width:1100px;margin:0 auto}
.tab-panel.active{display:block}
.panel-hdr{background:#fff;border-radius:var(--radius);padding:1.1rem 1.4rem;margin-bottom:1.25rem;border-left:4px solid var(--teal);box-shadow:var(--shadow);display:flex;align-items:center;gap:1rem}
.ph-icon{font-size:1.9rem}
.ph-title{font-size:1.1rem;font-weight:800;color:var(--teal)}
.ph-desc{font-size:.8rem;color:var(--text-sm);margin-top:.1rem}
.ph-action{margin-left:auto;display:flex;gap:.5rem;flex-wrap:wrap}

/* ── Buttons ── */
.btn{padding:.5rem 1rem;border-radius:var(--radius-sm);font-size:.83rem;font-weight:700;border:none;cursor:pointer;transition:all .2s;display:inline-flex;align-items:center;gap:.35rem}
.btn-primary{background:var(--teal);color:#fff}.btn-primary:hover{background:var(--teal-lt);transform:translateY(-1px)}
.btn-amber{background:var(--amber);color:#fff}.btn-amber:hover{background:var(--amber-lt)}
.btn-outline{background:#fff;color:var(--teal);border:2px solid var(--teal)}.btn-outline:hover{background:var(--teal-bg)}
.btn-ghost{background:var(--teal-bg);color:var(--teal);border:none}.btn-ghost:hover{background:var(--teal);color:#fff}
.btn-sm{padding:.32rem .7rem;font-size:.76rem}
.btn-danger{background:var(--red-bg);color:var(--red);border:1px solid #fca5a5}.btn-danger:hover{background:var(--red);color:#fff}
.btn-green{background:var(--green-bg);color:var(--green);border:1px solid #86efac}.btn-green:hover{background:var(--green);color:#fff}

/* ── Forms ── */
.form-group{margin-bottom:.8rem}
.form-group label{display:block;font-size:.78rem;font-weight:700;margin-bottom:.3rem;color:var(--text-md)}
.form-control{width:100%;padding:.5rem .8rem;border:1.5px solid var(--border);border-radius:var(--radius-sm);font-size:.87rem;transition:border-color .2s;background:#fff}
.form-control:focus{outline:none;border-color:var(--teal);box-shadow:0 0 0 3px rgba(26,92,120,.1)}
textarea.form-control{resize:vertical;min-height:75px}
.section-title{font-size:.78rem;font-weight:800;color:var(--text-sm);text-transform:uppercase;letter-spacing:.08em;margin:1.25rem 0 .7rem;display:flex;align-items:center;gap:.5rem}
.section-title::after{content:'';flex:1;height:1px;background:var(--border)}
.grid-2{display:grid;grid-template-columns:1fr 1fr;gap:1rem}
.grid-3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:1rem}
@media(max-width:680px){.grid-2,.grid-3{grid-template-columns:1fr}}
.card{background:#fff;border-radius:var(--radius);border:1px solid var(--border);padding:1rem 1.2rem;box-shadow:var(--shadow)}

/* ── Framework badges ── */
.fw{display:inline-flex;align-items:center;padding:.1rem .45rem;border-radius:20px;font-size:.62rem;font-weight:700;margin:.1rem .1rem 0 0;letter-spacing:.01em}

/* ═══════════════════════════════════════════════
   TAB 1 — CARD BUILDER
═══════════════════════════════════════════════ */
.filter-bar{display:flex;gap:.4rem;flex-wrap:wrap;margin-bottom:1rem;align-items:center}
.fpill{padding:.28rem .7rem;border-radius:20px;font-size:.77rem;font-weight:700;border:2px solid var(--border);background:#fff;cursor:pointer;transition:all .2s}
.fpill:hover,.fpill.on{color:#fff}
.fpill.on.all{background:var(--navy);border-color:var(--navy)}
.fpill.on.regulation{background:var(--amber);border-color:var(--amber)}
.fpill.on.communication{background:var(--teal);border-color:var(--teal)}
.fpill.on.routine{background:var(--green);border-color:var(--green)}
.fpill.on.attention{background:#C97B1A;border-color:#C97B1A}
.fpill.on.places{background:var(--purple);border-color:var(--purple)}
.cards-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(135px,1fr));gap:.65rem}
.sc{background:#fff;border-radius:var(--radius-sm);border:2px solid var(--border);padding:.7rem .55rem;text-align:center;cursor:pointer;transition:all .18s;position:relative;user-select:none}
.sc:hover{transform:translateY(-2px);box-shadow:0 4px 12px rgba(0,0,0,.1)}
.sc.sel{border-color:var(--teal);box-shadow:0 0 0 2px var(--teal)}
.sc.sel::after{content:'✓';position:absolute;top:4px;right:5px;background:var(--teal);color:#fff;border-radius:50%;width:18px;height:18px;font-size:.62rem;font-weight:900;display:flex;align-items:center;justify-content:center}
.sc-em{font-size:1.7rem;line-height:1;margin-bottom:.3rem}
.sc-ti{font-size:.76rem;font-weight:700;color:var(--text);line-height:1.25}
.sc-su{font-size:.62rem;color:var(--text-sm);margin-top:.15rem}
.sc-fws{margin-top:.3rem}
.sel-bar{background:var(--teal-bg);border:1px solid var(--teal);border-radius:var(--radius-sm);padding:.6rem 1rem;display:flex;align-items:center;gap:.75rem;flex-wrap:wrap;margin-top:1rem}
.sel-bar .cnt{font-size:.82rem;font-weight:700;color:var(--teal)}

/* ═══════════════════════════════════════════════
   TAB 2 — FIRST-THEN / NOW-NEXT
═══════════════════════════════════════════════ */
.board-toggles{display:flex;gap:.5rem;margin-bottom:1.25rem}
.ttbtn{flex:1;padding:.6rem;border-radius:var(--radius-sm);font-weight:700;font-size:.87rem;border:2px solid var(--border);background:#fff;color:var(--text-md);cursor:pointer;transition:all .2s}
.ttbtn.on{border-color:var(--teal);background:var(--teal);color:#fff}
.ft-grid{display:grid;gap:.75rem}
.ft-grid.g2{grid-template-columns:1fr 1fr}
.ft-grid.g3{grid-template-columns:1fr 1fr 1fr}
.ft-slot{background:#fff;border-radius:var(--radius);border:2px dashed var(--border);padding:1.25rem 1rem;text-align:center;min-height:150px;display:flex;flex-direction:column;align-items:center;justify-content:center;cursor:pointer;transition:all .2s;position:relative}
.ft-slot.filled{border-style:solid;border-color:var(--teal);background:var(--teal-bg)}
.ft-slot:hover{border-color:var(--teal-lt);background:var(--teal-bg)}
.ft-lbl{font-size:.68rem;font-weight:800;text-transform:uppercase;letter-spacing:.1em;margin-bottom:.5rem;color:var(--text-sm)}
.ft-slot.filled .ft-lbl{color:var(--teal)}
.ft-em{font-size:2.8rem;line-height:1;margin-bottom:.45rem}
.ft-tx{font-size:.9rem;font-weight:700}
.ft-ph{font-size:.82rem;color:var(--text-sm)}
.ft-clr{position:absolute;top:6px;right:8px;background:var(--red-bg);border:none;color:var(--red);border-radius:50%;width:22px;height:22px;font-size:.75rem;display:flex;align-items:center;justify-content:center;cursor:pointer}
.act-picker{background:#fff;border-radius:var(--radius);border:1px solid var(--border);padding:1rem;margin-top:1rem}
.act-picker h4{font-size:.85rem;font-weight:700;margin-bottom:.75rem;color:var(--text)}
.act-search{width:100%;padding:.42rem .8rem;border:1.5px solid var(--border);border-radius:var(--radius-sm);font-size:.83rem;margin-bottom:.65rem}
.act-search:focus{outline:none;border-color:var(--teal)}
.act-cats{display:flex;gap:.35rem;flex-wrap:wrap;margin-bottom:.65rem}
.act-cat{padding:.22rem .6rem;border-radius:20px;font-size:.72rem;font-weight:700;border:1.5px solid var(--border);background:#fff;cursor:pointer;transition:all .2s}
.act-cat.on{background:var(--teal);border-color:var(--teal);color:#fff}
.act-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(68px,1fr));gap:.4rem;max-height:220px;overflow-y:auto}
.act-item{background:var(--cream);border-radius:var(--radius-sm);padding:.45rem .2rem;text-align:center;cursor:pointer;transition:all .15s;border:2px solid transparent}
.act-item:hover{background:var(--teal-bg);border-color:var(--teal)}
.act-item .aiem{font-size:1.35rem}
.act-item .ailb{font-size:.62rem;font-weight:600;color:var(--text-sm);margin-top:.1rem}
.custom-act{display:flex;gap:.5rem;margin-top:.65rem;border-top:1px solid var(--border);padding-top:.65rem}
.arrow-sep{display:flex;align-items:center;justify-content:center;font-size:1.8rem;color:var(--text-sm)}

/* ═══════════════════════════════════════════════
   TAB 3 — VISUAL SCHEDULE
═══════════════════════════════════════════════ */
.sched-types{display:flex;gap:.5rem;margin-bottom:1rem;flex-wrap:wrap}
.sched-type{padding:.32rem .8rem;border-radius:20px;font-size:.78rem;font-weight:700;border:2px solid var(--border);background:#fff;cursor:pointer;transition:all .2s}
.sched-type.on{border-color:var(--teal);background:var(--teal);color:#fff}
.slot-row{background:#fff;border-radius:var(--radius-sm);border:1px solid var(--border);padding:.55rem .85rem;display:flex;align-items:center;gap:.7rem;margin-bottom:.4rem}
.slot-row:hover{box-shadow:var(--shadow)}
.slot-drag{color:var(--text-sm);cursor:grab;font-size:1rem;padding:.1rem}
.slot-em{font-size:1.5rem;cursor:pointer;min-width:1.8rem}
.slot-body{flex:1}
.slot-time{font-size:.7rem;font-weight:700;color:var(--text-sm)}
.slot-act{font-size:.87rem;font-weight:700}
.slot-acts{display:flex;gap:.3rem}
.slot-acts button{padding:.25rem .5rem;border-radius:4px;border:none;background:var(--cream);color:var(--text-sm);font-size:.75rem;cursor:pointer}
.slot-acts button:hover{background:var(--red-bg);color:var(--red)}
.add-slot-bar{background:var(--teal-bg);border:1px dashed var(--teal);border-radius:var(--radius-sm);padding:.65rem 1rem;cursor:pointer;text-align:center;font-size:.83rem;font-weight:700;color:var(--teal);transition:background .2s;margin-top:.5rem}
.add-slot-bar:hover{background:var(--teal);color:#fff}

/* ═══════════════════════════════════════════════
   TAB 4 — COMMUNICATION BOARD
═══════════════════════════════════════════════ */
.grid-opts{display:flex;gap:.4rem;flex-wrap:wrap;margin-bottom:1rem}
.grid-opt{padding:.3rem .75rem;border-radius:20px;font-size:.77rem;font-weight:700;border:2px solid var(--border);background:#fff;cursor:pointer;transition:all .2s}
.grid-opt.on{border-color:var(--teal);background:var(--teal);color:#fff}
.cat-presets{display:flex;gap:.4rem;flex-wrap:wrap;margin-bottom:1rem}
.cat-preset{padding:.28rem .7rem;border-radius:20px;font-size:.75rem;font-weight:700;border:1.5px solid var(--border);background:#fff;cursor:pointer;transition:all .2s}
.cat-preset:hover{border-color:var(--teal);color:var(--teal)}
.comm-grid{display:grid;gap:.5rem;margin-bottom:1rem}
.comm-cell{background:#fff;border-radius:var(--radius-sm);border:2px solid var(--border);padding:.75rem .4rem;text-align:center;min-height:90px;display:flex;flex-direction:column;align-items:center;justify-content:center;cursor:pointer;transition:all .2s;position:relative}
.comm-cell:hover{border-color:var(--teal);box-shadow:0 2px 8px rgba(0,0,0,.08)}
.cc-em{font-size:1.8rem}
.cc-tx{font-size:.75rem;font-weight:700;margin-top:.3rem}
.cc-ed{position:absolute;top:3px;right:4px;font-size:.65rem;color:var(--text-sm);opacity:0;transition:opacity .2s}
.comm-cell:hover .cc-ed{opacity:1}

/* ═══════════════════════════════════════════════
   TAB 5 — REGULATION TOOLS
═══════════════════════════════════════════════ */
.reg-types{display:flex;gap:.5rem;flex-wrap:wrap;margin-bottom:1.25rem}
.reg-type{flex:1;min-width:130px;padding:.65rem .75rem;border-radius:var(--radius-sm);font-weight:700;font-size:.83rem;border:2px solid var(--border);background:#fff;color:var(--text-md);cursor:pointer;transition:all .2s;text-align:center}
.reg-type.on{border-color:var(--teal);background:var(--teal);color:#fff}
.reg-panel{display:none}.reg-panel.active{display:block}
/* Zones */
.zones-grid{display:grid;grid-template-columns:1fr 1fr;gap:.75rem}
.zone-card{border-radius:var(--radius);padding:1rem;border:2px solid transparent}
.zone-card.zb{background:#DBEAFE;border-color:#93C5FD}
.zone-card.zg{background:#DCFCE7;border-color:#86EFAC}
.zone-card.zy{background:#FEF9C3;border-color:#FDE047}
.zone-card.zr{background:#FEE2E2;border-color:#FCA5A5}
.zone-name{font-size:1rem;font-weight:800;margin-bottom:.4rem}
.zone-feels{display:flex;flex-wrap:wrap;gap:.25rem;margin-bottom:.4rem}
.zone-feel{padding:.12rem .45rem;border-radius:20px;font-size:.7rem;font-weight:600;background:rgba(255,255,255,.65)}
.zone-strats{font-size:.77rem;line-height:1.6;color:var(--text-md)}
.zone-input{margin-top:.5rem}
.zone-input input{width:100%;padding:.35rem .6rem;border:1.5px solid rgba(255,255,255,.7);border-radius:var(--radius-sm);font-size:.78rem;background:rgba(255,255,255,.6)}
/* 5 point scale */
.five-scale{display:flex;gap:.5rem;margin-bottom:1rem}
.sp{flex:1;border-radius:var(--radius-sm);padding:.75rem .35rem;text-align:center;border:2px solid var(--border);cursor:pointer;transition:all .2s}
.sp.on{border-color:transparent;transform:translateY(-2px);box-shadow:0 4px 12px rgba(0,0,0,.12)}
.sp-num{font-size:1.5rem;font-weight:900;line-height:1}
.sp-em{font-size:1.1rem;margin:.2rem 0}
.sp-lb{font-size:.64rem;font-weight:700}
.sp-input{width:100%;margin-top:.3rem;padding:.25rem;border:1.5px solid var(--border);border-radius:4px;font-size:.68rem;text-align:center}
/* Calm-down */
.str-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(115px,1fr));gap:.55rem}
.str-card{background:#fff;border-radius:var(--radius-sm);border:2px solid var(--border);padding:.6rem .4rem;text-align:center;cursor:pointer;transition:all .2s}
.str-card:hover{border-color:var(--teal);background:var(--teal-bg)}
.str-card.on{border-color:var(--teal);background:var(--teal);color:#fff}
.str-em{font-size:1.5rem;margin-bottom:.2rem}
.str-lb{font-size:.72rem;font-weight:700}

/* ═══════════════════════════════════════════════
   TAB 6 — SOCIAL SCRIPTS
═══════════════════════════════════════════════ */
.script-situ{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:.5rem;margin-bottom:1rem}
.situ-btn{background:#fff;border-radius:var(--radius-sm);border:2px solid var(--border);padding:.65rem .75rem;cursor:pointer;transition:all .2s;display:flex;align-items:center;gap:.5rem;font-size:.83rem;font-weight:700}
.situ-btn:hover{border-color:var(--teal);background:var(--teal-bg)}
.situ-btn.on{border-color:var(--teal);background:var(--teal);color:#fff}
.script-steps{margin:.75rem 0}
.step-row{background:#fff;border-radius:var(--radius-sm);border:1px solid var(--border);padding:.55rem .8rem;display:flex;align-items:center;gap:.7rem;margin-bottom:.4rem}
.step-num{width:26px;height:26px;border-radius:50%;background:var(--teal);color:#fff;font-size:.8rem;font-weight:800;display:flex;align-items:center;justify-content:center;flex-shrink:0}
.step-em{font-size:1.25rem;cursor:pointer;min-width:1.4rem}
.step-tx{flex:1;font-size:.87rem;font-weight:600}
.step-dels{display:flex;gap:.3rem}
.step-dels button{padding:.22rem .45rem;border-radius:4px;border:none;background:var(--cream);color:var(--text-sm);font-size:.72rem;cursor:pointer}
.step-dels button:hover{background:var(--red-bg);color:var(--red)}

/* ═══════════════════════════════════════════════
   TAB 7 — AI SUGGEST
═══════════════════════════════════════════════ */
.ai-banner{background:linear-gradient(135deg,var(--teal-bg) 0%,var(--green-bg) 100%);border-radius:var(--radius);padding:1.2rem;border:1px solid var(--teal);margin-bottom:1.25rem}
.ai-banner h3{color:var(--teal);font-size:1rem;font-weight:800;margin-bottom:.4rem}
.ai-banner p{font-size:.82rem;color:var(--text-md)}
.fw-refs{display:flex;flex-wrap:wrap;gap:.3rem;margin:.75rem 0}
.fw-ref{display:inline-flex;align-items:center;padding:.22rem .6rem;border-radius:var(--radius-sm);font-size:.75rem;font-weight:700;cursor:pointer;transition:all .2s;border:1.5px solid transparent}
.fw-ref:hover{transform:translateY(-1px);box-shadow:0 2px 8px rgba(0,0,0,.1)}
.ai-results{margin-top:1rem}
.ai-sug{background:#fff;border-radius:var(--radius-sm);border:1px solid var(--border);padding:.85rem;margin-bottom:.55rem;border-left:3px solid var(--teal)}
.sug-header{display:flex;align-items:center;justify-content:space-between;gap:.75rem}
.sug-title{font-size:.9rem;font-weight:700}
.sug-type{font-size:.68rem;font-weight:700;background:var(--teal-bg);color:var(--teal);padding:.1rem .4rem;border-radius:4px}
.sug-why{font-size:.78rem;color:var(--text-md);margin-top:.3rem;line-height:1.5}
.sug-fws{margin-top:.4rem}
.ai-loading{text-align:center;padding:2rem;color:var(--text-sm)}
.ai-spinner{font-size:2rem;animation:spin 1.2s linear infinite;display:inline-block}
@keyframes spin{to{transform:rotate(360deg)}}

/* ═══════════════════════════════════════════════
   TAB 8 — PRINT QUEUE
═══════════════════════════════════════════════ */
.pf-selector{display:grid;grid-template-columns:repeat(3,1fr);gap:.7rem;margin-bottom:1.25rem}
.pf-opt{background:#fff;border-radius:var(--radius);border:2px solid var(--border);padding:1rem;text-align:center;cursor:pointer;transition:all .2s}
.pf-opt.on{border-color:var(--teal);background:var(--teal-bg)}
.pf-icon{font-size:1.8rem;margin-bottom:.4rem}
.pf-name{font-size:.85rem;font-weight:700}
.pf-desc{font-size:.7rem;color:var(--text-sm);margin-top:.2rem}
.q-item{background:#fff;border-radius:var(--radius-sm);border:1px solid var(--border);padding:.7rem 1rem;display:flex;align-items:center;gap:.75rem;margin-bottom:.4rem}
.qi-icon{font-size:1.4rem}
.qi-name{font-size:.87rem;font-weight:700}
.qi-type{font-size:.7rem;color:var(--text-sm)}
.q-empty{text-align:center;padding:2.5rem;color:var(--text-sm);background:#fff;border-radius:var(--radius);border:2px dashed var(--border)}

/* ── Modals ── */
.modal-ov{position:fixed;inset:0;background:rgba(0,0,0,.48);z-index:200;display:flex;align-items:center;justify-content:center;padding:1rem;opacity:0;pointer-events:none;transition:opacity .2s}
.modal-ov.open{opacity:1;pointer-events:all}
.modal{background:#fff;border-radius:var(--radius-lg);max-width:540px;width:100%;padding:1.5rem;max-height:88vh;overflow-y:auto;transform:translateY(20px);transition:transform .2s;box-shadow:0 20px 60px rgba(0,0,0,.22)}
.modal-ov.open .modal{transform:translateY(0)}
.modal-hdr{display:flex;align-items:center;justify-content:space-between;margin-bottom:1.2rem}
.modal-title{font-size:1.05rem;font-weight:800;color:var(--teal)}
.modal-close{background:var(--cream);border:none;width:30px;height:30px;border-radius:50%;font-size:1.1rem;cursor:pointer;display:flex;align-items:center;justify-content:center}
.emoji-grid{display:grid;grid-template-columns:repeat(8,1fr);gap:.2rem;max-height:200px;overflow-y:auto}
.ep-em{font-size:1.25rem;padding:.28rem;text-align:center;cursor:pointer;border-radius:4px;transition:background .15s}
.ep-em:hover{background:var(--teal-bg)}

/* ── Toast ── */
.toast{position:fixed;bottom:1.5rem;right:1.5rem;background:var(--navy);color:#fff;padding:.7rem 1.2rem;border-radius:var(--radius-sm);font-size:.84rem;font-weight:700;transform:translateY(20px);opacity:0;z-index:999;transition:all .3s;box-shadow:var(--shadow)}
.toast.show{transform:translateY(0);opacity:1}
.toast.ok{background:var(--green)}
.toast.err{background:var(--red)}
</style>
</head>
<body>

<!-- ═══════════ HEADER ═══════════ -->
<header class="app-header">
  <div class="logo">🎨</div>
  <div><div class="h1" style="font-size:1.15rem;font-weight:900;letter-spacing:-.02em">Visual Support Builder</div><div class="sub">CLC-LBU · Evidence-based visual tools for all learners</div></div>
  <div class="hdr-spacer"></div>
  <button class="hdr-student" onclick="openModal('student')">👤 <span id="hdr-sname">Set student</span></button>
  <button class="hdr-badge" onclick="switchTab('print')">🖨️ Queue <span id="hdr-qcount">0</span></button>
  <button class="hdr-btn" onclick="openModal('settings')" title="Settings">⚙️</button>
</header>

<!-- ═══════════ TAB NAV ═══════════ -->
<nav class="tabs-nav">
  <button class="tab-btn active" onclick="switchTab('cards')"><span class="tab-icon">🃏</span>Card Builder</button>
  <button class="tab-btn" onclick="switchTab('firstthen')"><span class="tab-icon">🔄</span>First-Then</button>
  <button class="tab-btn" onclick="switchTab('schedule')"><span class="tab-icon">📅</span>Visual Schedule</button>
  <button class="tab-btn" onclick="switchTab('board')"><span class="tab-icon">💬</span>Comm Board</button>
  <button class="tab-btn" onclick="switchTab('regulation')"><span class="tab-icon">🧘</span>Regulation</button>
  <button class="tab-btn" onclick="switchTab('scripts')"><span class="tab-icon">📖</span>Social Scripts</button>
  <button class="tab-btn" onclick="switchTab('ai')"><span class="tab-icon">✨</span>AI Suggest</button>
  <button class="tab-btn" onclick="switchTab('print')"><span class="tab-icon">🖨️</span>Print Queue</button>
</nav>

<main>

<!-- ═══════════════════════════════════════════════
     TAB 1 — CARD BUILDER
═══════════════════════════════════════════════ -->
<section id="tab-cards" class="tab-panel active">
  <div class="panel-hdr">
    <div class="ph-icon">🃏</div>
    <div><div class="ph-title">Lanyard & Desk Cards</div><div class="ph-desc">Browse, select and customise visual support cards with research framework references</div></div>
    <div class="ph-action">
      <button class="btn btn-outline btn-sm" onclick="openModal('customcard')">+ Custom card</button>
      <button class="btn btn-amber btn-sm" onclick="addCardsToQueue()">🖨️ Add to queue</button>
    </div>
  </div>
  <div class="filter-bar">
    <button class="fpill on all" onclick="filterCards('all',this)">All</button>
    <button class="fpill" onclick="filterCards('regulation',this)" style="--c:#D4860A">🟡 Regulation</button>
    <button class="fpill" onclick="filterCards('communication',this)">🔵 Communication</button>
    <button class="fpill" onclick="filterCards('routine',this)">🟢 Routine</button>
    <button class="fpill" onclick="filterCards('attention',this)">🟠 Attention</button>
    <button class="fpill" onclick="filterCards('places',this)">🟣 Places</button>
    <input type="search" placeholder="Search cards…" oninput="searchCards(this.value)" style="padding:.3rem .7rem;border:1.5px solid var(--border);border-radius:20px;font-size:.78rem;margin-left:auto;width:160px">
  </div>
  <div id="cards-grid" class="cards-grid"></div>
  <div class="sel-bar" id="sel-bar" style="display:none">
    <span class="cnt" id="sel-count">0 selected</span>
    <button class="btn btn-sm btn-ghost" onclick="clearCards()">Clear all</button>
    <button class="btn btn-sm btn-amber" onclick="addCardsToQueue()">🖨️ Add selected to print queue</button>
  </div>
</section>

<!-- ═══════════════════════════════════════════════
     TAB 2 — FIRST-THEN / NOW-NEXT
═══════════════════════════════════════════════ -->
<section id="tab-firstthen" class="tab-panel">
  <div class="panel-hdr">
    <div class="ph-icon">🔄</div>
    <div><div class="ph-title">First-Then / Now-Next</div><div class="ph-desc">Build visual sequence boards using TEACCH structured teaching principles</div></div>
    <div class="ph-action">
      <button class="btn btn-amber btn-sm" onclick="addFTToQueue()">🖨️ Add to queue</button>
    </div>
  </div>
  <div class="board-toggles">
    <button class="ttbtn on" onclick="setFTType('ft',this)">First → Then (2 panels)</button>
    <button class="ttbtn" onclick="setFTType('nnt',this)">Now · Next · Then (3 panels)</button>
  </div>
  <div class="grid-2" style="gap:1rem;margin-bottom:1rem">
    <div class="form-group" style="margin:0"><label>Student name (optional)</label><input id="ft-student" class="form-control" placeholder="e.g. Alex" style="padding:.45rem .75rem"></div>
    <div class="form-group" style="margin:0"><label>Board title (optional)</label><input id="ft-title" class="form-control" placeholder="e.g. Morning routine"></div>
  </div>
  <div id="ft-grid" class="ft-grid g2">
    <div class="ft-slot" id="ft-slot-0" onclick="openActPicker(0)">
      <div class="ft-lbl" id="ft-lbl-0">FIRST</div>
      <div class="ft-em" id="ft-em-0">➕</div>
      <div class="ft-ph">Click to choose activity</div>
    </div>
    <div class="ft-slot" id="ft-slot-1" onclick="openActPicker(1)">
      <div class="ft-lbl" id="ft-lbl-1">THEN</div>
      <div class="ft-em" id="ft-em-1">➕</div>
      <div class="ft-ph">Click to choose activity</div>
    </div>
  </div>
  <div id="act-picker" class="act-picker" style="display:none">
    <h4>Choose an activity</h4>
    <input type="search" class="act-search" placeholder="Search activities…" oninput="searchActs(this.value)">
    <div class="act-cats" id="act-cats"></div>
    <div id="act-grid" class="act-grid"></div>
    <div class="custom-act">
      <input id="custom-act-em" class="form-control" placeholder="Emoji" style="width:70px;padding:.4rem .5rem;text-align:center">
      <input id="custom-act-tx" class="form-control" placeholder="Activity name">
      <button class="btn btn-primary btn-sm" onclick="addCustomAct()">Add</button>
    </div>
  </div>
  <div style="margin-top:.75rem;padding:.65rem 1rem;background:var(--teal-bg);border:1px solid var(--teal);border-radius:var(--radius-sm);font-size:.8rem;color:var(--teal)">
    💡 <strong>Research base:</strong> First-Then and visual sequence boards are core components of TEACCH Structured Teaching (Mesibov, Shea & Schopler) and are consistently supported by PBS research for reducing transition anxiety and task avoidance in students with ASD + ID.
  </div>
</section>

<!-- ═══════════════════════════════════════════════
     TAB 3 — VISUAL SCHEDULE
═══════════════════════════════════════════════ -->
<section id="tab-schedule" class="tab-panel">
  <div class="panel-hdr">
    <div class="ph-icon">📅</div>
    <div><div class="ph-title">Visual Schedule Builder</div><div class="ph-desc">Daily, half-day and strip schedules — TEACCH structured teaching, temporal organisation</div></div>
    <div class="ph-action">
      <button class="btn btn-amber btn-sm" onclick="addSchedToQueue()">🖨️ Add to queue</button>
    </div>
  </div>
  <div class="grid-2" style="margin-bottom:1rem">
    <div class="form-group" style="margin:0"><label>Schedule title</label><input id="sched-title" class="form-control" placeholder="e.g. Monday Schedule / Morning Routine"></div>
    <div class="form-group" style="margin:0"><label>Student name (optional)</label><input id="sched-student" class="form-control" placeholder="e.g. Abdulaziz"></div>
  </div>
  <div class="sched-types">
    <button class="sched-type on" onclick="setSchedType('daily',this)">📋 Full day</button>
    <button class="sched-type" onclick="setSchedType('morning',this)">🌅 Morning only</button>
    <button class="sched-type" onclick="setSchedType('afternoon',this)">🌤️ Afternoon only</button>
    <button class="sched-type" onclick="setSchedType('strip',this)">▶️ Now-Next-Later strip</button>
  </div>
  <div class="section-title">Schedule slots</div>
  <div id="sched-slots"></div>
  <div class="add-slot-bar" onclick="addSchedSlot()">+ Add time slot</div>
</section>

<!-- ═══════════════════════════════════════════════
     TAB 4 — COMMUNICATION BOARD
═══════════════════════════════════════════════ -->
<section id="tab-board" class="tab-panel">
  <div class="panel-hdr">
    <div class="ph-icon">💬</div>
    <div><div class="ph-title">Communication Choice Board</div><div class="ph-desc">AAC-informed choice boards — core vocabulary, PODD principles, UDL multiple means of expression</div></div>
    <div class="ph-action">
      <button class="btn btn-amber btn-sm" onclick="addBoardToQueue()">🖨️ Add to queue</button>
    </div>
  </div>
  <div class="grid-2" style="margin-bottom:1rem">
    <div class="form-group" style="margin:0"><label>Board title</label><input id="board-title" class="form-control" placeholder="e.g. I want…  / How am I feeling?"></div>
    <div class="form-group" style="margin:0"><label>Student name (optional)</label><input id="board-student" class="form-control" placeholder="e.g. Priya"></div>
  </div>
  <div class="section-title">Grid size</div>
  <div class="grid-opts">
    <button class="grid-opt on" onclick="setGrid('2x2',this)">2×2</button>
    <button class="grid-opt" onclick="setGrid('2x3',this)">2×3</button>
    <button class="grid-opt" onclick="setGrid('3x3',this)">3×3</button>
    <button class="grid-opt" onclick="setGrid('3x4',this)">3×4</button>
    <button class="grid-opt" onclick="setGrid('4x4',this)">4×4</button>
  </div>
  <div class="section-title">Load category preset</div>
  <div class="cat-presets">
    <button class="cat-preset" onclick="loadPreset('feelings')">😊 Feelings</button>
    <button class="cat-preset" onclick="loadPreset('food')">🍎 Food & Drink</button>
    <button class="cat-preset" onclick="loadPreset('places')">🏫 Places</button>
    <button class="cat-preset" onclick="loadPreset('activities')">🎨 Activities</button>
    <button class="cat-preset" onclick="loadPreset('requests')">🙋 Requests</button>
    <button class="cat-preset" onclick="loadPreset('people')">👥 People</button>
    <button class="cat-preset" onclick="loadPreset('core')">💬 Core words</button>
  </div>
  <div class="section-title">Board</div>
  <div id="comm-grid" class="comm-grid"></div>
</section>

<!-- ═══════════════════════════════════════════════
     TAB 5 — REGULATION TOOLS
═══════════════════════════════════════════════ -->
<section id="tab-regulation" class="tab-panel">
  <div class="panel-hdr">
    <div class="ph-icon">🧘</div>
    <div><div class="ph-title">Regulation & Wellbeing Tools</div><div class="ph-desc">Zones of Regulation, 5-Point Scale, Calm-Down strategies — BSEM, Trauma-Informed, OT/Sensory frameworks</div></div>
    <div class="ph-action">
      <button class="btn btn-amber btn-sm" onclick="addRegToQueue()">🖨️ Add to queue</button>
    </div>
  </div>
  <div class="reg-types">
    <button class="reg-type on" onclick="setRegType('zones',this)">🟢 Zones of Regulation</button>
    <button class="reg-type" onclick="setRegType('fivepoint',this)">5️⃣ 5-Point Scale</button>
    <button class="reg-type" onclick="setRegType('calmdown',this)">🌬️ Calm-Down Menu</button>
    <button class="reg-type" onclick="setRegType('feelings',this)">😊 Feelings Check-In</button>
  </div>

  <!-- ZONES -->
  <div id="reg-zones" class="reg-panel active">
    <div class="zones-grid">
      <div class="zone-card zb">
        <div class="zone-name">🔵 Blue Zone</div>
        <div class="zone-feels" id="z-blue-feels"></div>
        <div class="zone-strats" id="z-blue-strats"></div>
        <div class="zone-input"><input id="z-blue-add" placeholder="Add a strategy for this student…" onkeydown="if(event.key==='Enter')addZoneStrat('blue')"></div>
      </div>
      <div class="zone-card zg">
        <div class="zone-name">🟢 Green Zone</div>
        <div class="zone-feels" id="z-green-feels"></div>
        <div class="zone-strats" id="z-green-strats"></div>
        <div class="zone-input"><input id="z-green-add" placeholder="Add a strategy for this student…" onkeydown="if(event.key==='Enter')addZoneStrat('green')"></div>
      </div>
      <div class="zone-card zy">
        <div class="zone-name">🟡 Yellow Zone</div>
        <div class="zone-feels" id="z-yellow-feels"></div>
        <div class="zone-strats" id="z-yellow-strats"></div>
        <div class="zone-input"><input id="z-yellow-add" placeholder="Add a strategy for this student…" onkeydown="if(event.key==='Enter')addZoneStrat('yellow')"></div>
      </div>
      <div class="zone-card zr">
        <div class="zone-name">🔴 Red Zone</div>
        <div class="zone-feels" id="z-red-feels"></div>
        <div class="zone-strats" id="z-red-strats"></div>
        <div class="zone-input"><input id="z-red-add" placeholder="Add a strategy for this student…" onkeydown="if(event.key==='Enter')addZoneStrat('red')"></div>
      </div>
    </div>
    <div style="margin-top:.75rem;font-size:.78rem;color:var(--text-sm);background:var(--teal-bg);padding:.6rem .9rem;border-radius:var(--radius-sm)">
      📚 <strong>Zones of Regulation</strong> (Leah Kuypers, 2011) — aligns with Berry Street Education Model body-brain connection and Polyvagal co-regulation theory (Porges). Supports identification and self-management of emotional states.
    </div>
  </div>

  <!-- 5-POINT SCALE -->
  <div id="reg-fivepoint" class="reg-panel">
    <div class="form-group"><label>Student name</label><input id="fps-student" class="form-control" placeholder="e.g. Jordan" style="max-width:240px"></div>
    <div class="five-scale" id="five-scale"></div>
    <div style="margin-top:.75rem;font-size:.78rem;color:var(--text-sm);background:var(--teal-bg);padding:.6rem .9rem;border-radius:var(--radius-sm)">
      📚 <strong>5-Point Scale</strong> (Buron & Curtis, 2003) — a cognitive-behavioural tool widely used with ASD + ADHD + anxiety. Provides concrete anchors for abstract emotional concepts. Highly effective for EALD learners due to visual/numeric structure.
    </div>
  </div>

  <!-- CALM DOWN -->
  <div id="reg-calmdown" class="reg-panel">
    <div class="grid-2" style="margin-bottom:1rem">
      <div class="form-group" style="margin:0"><label>Student name</label><input id="cd-student" class="form-control" placeholder="e.g. Mia"></div>
      <div class="form-group" style="margin:0"><label>Title on card</label><input id="cd-title" class="form-control" placeholder="My calm-down toolkit"></div>
    </div>
    <div class="section-title">Select strategies to include</div>
    <div id="str-grid" class="str-grid"></div>
    <div style="margin-top:.75rem;font-size:.78rem;color:var(--text-sm);background:var(--teal-bg);padding:.6rem .9rem;border-radius:var(--radius-sm)">
      📚 <strong>Sensory-based strategies</strong> (Jean Ayres SPD framework, Winnie Dunn's Sensory Profile) + <strong>BSEM self-regulation curriculum</strong>. Research supports providing student-specific regulation menus rather than generic lists.
    </div>
  </div>

  <!-- FEELINGS CHECK-IN -->
  <div id="reg-feelings" class="reg-panel">
    <div class="grid-2" style="margin-bottom:1rem">
      <div class="form-group" style="margin:0"><label>Student name</label><input id="fc-student" class="form-control" placeholder="e.g. Sam"></div>
      <div class="form-group" style="margin:0"><label>Style</label>
        <select id="fc-style" class="form-control">
          <option value="faces">Simple faces</option>
          <option value="words">Words + faces</option>
          <option value="zones">Zones colours</option>
        </select>
      </div>
    </div>
    <div id="feelings-preview" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(90px,1fr));gap:.5rem;margin-top:.5rem"></div>
    <div style="margin-top:.75rem;font-size:.78rem;color:var(--text-sm);background:var(--teal-bg);padding:.6rem .9rem;border-radius:var(--radius-sm)">
      📚 Supports <strong>affective labelling</strong> (a Zones of Regulation core skill) and <strong>interoceptive awareness</strong> (Mahler, 2019). For EALD learners, visual feelings check-ins reduce the language barrier for emotional communication (ACARA EAL/D framework).
    </div>
  </div>
</section>

<!-- ═══════════════════════════════════════════════
     TAB 6 — SOCIAL SCRIPTS
═══════════════════════════════════════════════ -->
<section id="tab-scripts" class="tab-panel">
  <div class="panel-hdr">
    <div class="ph-icon">📖</div>
    <div><div class="ph-title">Social Scripts & Situation Guides</div><div class="ph-desc">Carol Gray Social Stories™ framework — step-by-step visual guides for navigating social situations</div></div>
    <div class="ph-action">
      <button class="btn btn-outline btn-sm" onclick="generateScript()">🤖 AI generate</button>
      <button class="btn btn-amber btn-sm" onclick="addScriptToQueue()">🖨️ Add to queue</button>
    </div>
  </div>
  <div class="grid-2" style="margin-bottom:1rem">
    <div class="form-group" style="margin:0"><label>Student name</label><input id="sc-student" class="form-control" placeholder="e.g. Nico"></div>
    <div class="form-group" style="margin:0"><label>Script title</label><input id="sc-title" class="form-control" placeholder="e.g. What happens at lunch"></div>
  </div>
  <div class="section-title">Choose a situation template</div>
  <div class="script-situ" id="script-situations"></div>
  <div class="section-title">Script steps <button class="btn btn-sm btn-ghost" style="margin-left:.5rem" onclick="addScriptStep()">+ Add step</button></div>
  <div id="script-steps" class="script-steps"></div>
  <div style="margin-top:.75rem;font-size:.78rem;color:var(--text-sm);background:var(--teal-bg);padding:.6rem .9rem;border-radius:var(--radius-sm)">
    📚 <strong>Carol Gray Social Stories™</strong> (1991, 10th criterion 2015): use descriptive, perspective, directive, and affirmative sentences. Research supports use with ASD + ID (Sansosti et al., 2004 meta-analysis). For EALD learners, visual step format significantly reduces language processing demands.
  </div>
</section>

<!-- ═══════════════════════════════════════════════
     TAB 7 — AI SUGGEST
═══════════════════════════════════════════════ -->
<section id="tab-ai" class="tab-panel">
  <div class="panel-hdr">
    <div class="ph-icon">✨</div>
    <div><div class="ph-title">AI Visual Support Suggestions</div><div class="ph-desc">Groq-powered suggestions drawing on 12 evidence-based frameworks for your student's specific profile</div></div>
  </div>
  <div class="ai-banner">
    <h3>🔬 Research Frameworks Used in AI Suggestions</h3>
    <p>Click any badge to see full reference details</p>
    <div class="fw-refs" id="fw-refs"></div>
  </div>
  <div class="card" style="margin-bottom:1.25rem">
    <div class="section-title" style="margin-top:0">Student profile</div>
    <div class="grid-2">
      <div class="form-group"><label>Student name</label><input id="ai-name" class="form-control" placeholder="e.g. Abdulaziz"></div>
      <div class="form-group"><label>Age / year level</label><input id="ai-age" class="form-control" placeholder="e.g. 8 yrs, Junior Primary"></div>
    </div>
    <div class="form-group"><label>Diagnoses / learning profile</label><input id="ai-diag" class="form-control" placeholder="e.g. ASD, ADHD, Intellectual Disability, EALD (Arabic L1)"></div>
    <div class="form-group"><label>Communication style & AAC</label><input id="ai-comm" class="form-control" placeholder="e.g. Emerging verbal, uses some PECS, approx. 50 spoken words"></div>
    <div class="form-group" style="margin:0"><label>Key behaviours / needs / triggers (the more detail, the better)</label><textarea id="ai-notes" class="form-control" placeholder="e.g. Seeks constant social engagement, enters peers' personal space, loud vocalisations to get attention, difficulty with transitions, strong food motivation..."></textarea></div>
  </div>
  <div style="display:flex;gap:.75rem;align-items:center">
    <button class="btn btn-primary" onclick="generateAI()" id="ai-btn">✨ Generate suggestions</button>
    <span style="font-size:.78rem;color:var(--text-sm)">Results are organised by tool type with framework references</span>
  </div>
  <div id="ai-results" class="ai-results"></div>
</section>

<!-- ═══════════════════════════════════════════════
     TAB 8 — PRINT QUEUE
═══════════════════════════════════════════════ -->
<section id="tab-print" class="tab-panel">
  <div class="panel-hdr">
    <div class="ph-icon">🖨️</div>
    <div><div class="ph-title">Print Queue</div><div class="ph-desc">Select print format then print all queued items — A4 lanyard, A4 desk mat, or A3 desk mat</div></div>
    <div class="ph-action">
      <button class="btn btn-danger btn-sm" onclick="clearQueue()">Clear queue</button>
      <button class="btn btn-primary" onclick="doPrint()">🖨️ Print all</button>
    </div>
  </div>
  <div class="section-title">Print format</div>
  <div class="pf-selector">
    <div class="pf-opt on" onclick="setFormat('lanyard',this)">
      <div class="pf-icon">🏷️</div>
      <div class="pf-name">A4 Lanyard cards</div>
      <div class="pf-desc">Credit card size · 2 cols · laminate & punch</div>
    </div>
    <div class="pf-opt" onclick="setFormat('desk-a4',this)">
      <div class="pf-icon">📄</div>
      <div class="pf-name">A4 Desk mat</div>
      <div class="pf-desc">Larger format · laminate for desk surface</div>
    </div>
    <div class="pf-opt" onclick="setFormat('desk-a3',this)">
      <div class="pf-icon">📋</div>
      <div class="pf-name">A3 Desk mat</div>
      <div class="pf-desc">Full A3 · ideal for personal space mats</div>
    </div>
  </div>
  <div class="section-title">Queued items (<span id="q-count">0</span>)</div>
  <div id="queue-list"></div>
</section>

</main>

<!-- ═══════════ MODALS ═══════════ -->
<!-- Student profile -->
<div class="modal-ov" id="modal-student">
  <div class="modal">
    <div class="modal-hdr"><div class="modal-title">👤 Student Profile</div><button class="modal-close" onclick="closeModal('student')">✕</button></div>
    <div class="form-group"><label>Student name</label><input id="sp-name" class="form-control" placeholder="e.g. Abdulaziz"></div>
    <div class="grid-2">
      <div class="form-group"><label>Age / year level</label><input id="sp-age" class="form-control" placeholder="e.g. 8 yrs, Yr 2"></div>
      <div class="form-group"><label>Program / class</label><input id="sp-class" class="form-control" placeholder="e.g. LBU Group A"></div>
    </div>
    <div class="form-group"><label>Diagnoses</label><input id="sp-diag" class="form-control" placeholder="e.g. ASD, ADHD, ID, EALD"></div>
    <div class="form-group"><label>Communication approach</label><input id="sp-comm" class="form-control" placeholder="e.g. PECS Phase 3, emerging verbal, Auslan signs"></div>
    <div class="form-group"><label>Key needs / notes</label><textarea id="sp-notes" class="form-control" placeholder="Key behaviours, sensory needs, triggers, motivators…"></textarea></div>
    <button class="btn btn-primary" onclick="saveProfile()" style="width:100%">Save profile</button>
  </div>
</div>

<!-- Custom card -->
<div class="modal-ov" id="modal-customcard">
  <div class="modal">
    <div class="modal-hdr"><div class="modal-title">➕ Custom Card</div><button class="modal-close" onclick="closeModal('customcard')">✕</button></div>
    <div class="form-group"><label>Emoji / symbol</label><input id="cc-em" class="form-control" placeholder="Paste an emoji e.g. 🚿" style="font-size:1.2rem"></div>
    <div class="form-group"><label>Card title</label><input id="cc-title" class="form-control" placeholder="e.g. Shower time"></div>
    <div class="form-group"><label>Subtitle / instruction (optional)</label><input id="cc-sub" class="form-control" placeholder="e.g. Wash hair and body"></div>
    <div class="form-group"><label>Category colour</label>
      <select id="cc-cat" class="form-control">
        <option value="regulation">🟡 Regulation</option>
        <option value="communication">🔵 Communication</option>
        <option value="routine">🟢 Routine</option>
        <option value="attention">🟠 Attention</option>
        <option value="places">🟣 Places</option>
      </select>
    </div>
    <button class="btn btn-primary" onclick="addCustomCard()" style="width:100%">Add card</button>
  </div>
</div>

<!-- Cell editor -->
<div class="modal-ov" id="modal-cell">
  <div class="modal" style="max-width:360px">
    <div class="modal-hdr"><div class="modal-title">Edit cell</div><button class="modal-close" onclick="closeModal('cell')">✕</button></div>
    <div class="form-group"><label>Emoji / symbol</label><input id="cell-em" class="form-control" placeholder="e.g. 🍎" style="font-size:1.4rem;text-align:center"></div>
    <div class="form-group"><label>Word / label</label><input id="cell-tx" class="form-control" placeholder="e.g. Apple"></div>
    <div class="form-group"><label>Background colour (optional)</label><input id="cell-bg" type="color" class="form-control" value="#FFFFFF" style="height:38px;padding:.2rem"></div>
    <div style="display:flex;gap:.5rem">
      <button class="btn btn-primary" onclick="saveCell()" style="flex:1">Save</button>
      <button class="btn btn-danger" onclick="clearCell()" style="flex:1">Clear</button>
    </div>
  </div>
</div>

<!-- Emoji picker (for steps/slots) -->
<div class="modal-ov" id="modal-emoji">
  <div class="modal" style="max-width:380px">
    <div class="modal-hdr"><div class="modal-title">Pick an emoji</div><button class="modal-close" onclick="closeModal('emoji')">✕</button></div>
    <div id="emoji-grid" class="emoji-grid"></div>
  </div>
</div>

<!-- Framework reference -->
<div class="modal-ov" id="modal-fw">
  <div class="modal">
    <div class="modal-hdr"><div class="modal-title" id="fw-modal-title">Framework</div><button class="modal-close" onclick="closeModal('fw')">✕</button></div>
    <div id="fw-modal-body" style="font-size:.87rem;line-height:1.7;color:var(--text-md)"></div>
  </div>
</div>

<!-- Settings -->
<div class="modal-ov" id="modal-settings">
  <div class="modal" style="max-width:400px">
    <div class="modal-hdr"><div class="modal-title">⚙️ Settings</div><button class="modal-close" onclick="closeModal('settings')">✕</button></div>
    <div class="form-group"><label>Groq Proxy URL</label><input id="set-proxy" class="form-control" placeholder="https://groq-proxy.yourname.workers.dev"></div>
    <p style="font-size:.78rem;color:var(--text-sm);margin-bottom:1rem">Used for AI suggestions. Deploy the Cloudflare Worker from the CLC portal setup and paste the URL here. Your Groq key stays server-side.</p>
    <button class="btn btn-primary" onclick="saveSettings()" style="width:100%">Save</button>
  </div>
</div>

<!-- Print root -->
<div id="print-root"></div>

<!-- Toast -->
<div class="toast" id="toast"></div>

<script>
// ════════════════════════════════════════════════════════════
// CONFIG & STATE
// ════════════════════════════════════════════════════════════
const CFG = { proxyUrl: localStorage.getItem('vsb_proxy') || '' };

const STATE = {
  student: JSON.parse(localStorage.getItem('vsb_student')||'{}'),
  selectedCards: new Set(),
  customCards: [],
  ftType: 'ft',
  ftSlots: [null, null, null],
  ftActiveSlot: 0,
  actCat: 'all',
  schedType: 'daily',
  schedSlots: [],
  gridSize: '2x2',
  boardCells: [],
  boardTitle: '',
  regType: 'zones',
  zoneStrats: { blue:[], green:[], yellow:[], red:[] },
  fiveScaleLabels: ['Calm & Still','Happy & Ready','A bit wobbly','Really upset','Cannot stop'],
  selectedStrats: new Set(),
  scriptSteps: [],
  scriptSituations: [],
  printQueue: [],
  printFormat: 'lanyard',
  editingCell: -1,
  emojiCallback: null,
};

// ════════════════════════════════════════════════════════════
// FRAMEWORK DATA
// ════════════════════════════════════════════════════════════
const FW = {
  BSEM:   { label:'Berry Street', color:'#1A5C78', bg:'#EBF5FA',
    desc:'Berry Street Education Model (BSEM) — a trauma-informed, strengths-based framework developed in Australia. Focuses on body, relationships, stamina, engagement and character. Emphasises felt sense, co-regulation and body-based learning readiness.',
    refs:'Berry Street (2012). Berry Street Education Model. Bundoora: Berry Street; Brunzell, T., Stokes, H. & Waters, L. (2016). Trauma-informed positive education. CSHE.' },
  TI:     { label:'Trauma-Informed', color:'#5A3B8C', bg:'#F2EEF8',
    desc:'Trauma-Informed Practice draws on Bruce Perry\'s Neurosequential Model (brain-stem → limbic → cortex), Bessel van der Kolk\'s somatic trauma theory, and Stephen Porges\' Polyvagal Theory. Visual supports reduce the cognitive demand that trauma-activated nervous systems struggle with.',
    refs:'Perry, B. (2006). Applying Principles of Neurodevelopment. In N. Webb (Ed.), Working with traumatized youth in child welfare. Guilford; van der Kolk, B. (2014). The Body Keeps the Score. Penguin; Porges, S. (2011). The Polyvagal Theory. Norton.' },
  TEACCH: { label:'TEACCH', color:'#2D7D4F', bg:'#E8F5EE',
    desc:'TEACCH Structured Teaching (University of North Carolina) — organises the physical environment and tasks using visual structure, clarity, and predictability. Core components: physical organisation, visual schedules, work systems, and task organisation. Particularly effective for ASD + ID.',
    refs:'Mesibov, G., Shea, V. & Schopler, E. (2005). The TEACCH Approach to Autism Spectrum Disorders. Springer; Dettmer, S. et al. (2000). Use of visual supports to facilitate transitions. JABA, 33(4).' },
  PBS:    { label:'PBS', color:'#C97B1A', bg:'#FEF7EA',
    desc:'Positive Behaviour Support (PBS) — a function-based, antecedent-focused framework. Identifies the communicative function of behaviour and teaches replacement skills. Visual supports serve as antecedent modifications reducing triggers and supporting expected behaviour.',
    refs:'Sugai, G. & Horner, R. (2009). Responsiveness-to-Intervention and School-Wide PBS. Exceptionality, 17(4); Carr, E. et al. (2002). Positive Behavior Support: Evolution of an Applied Science. JEIBI.' },
  OT:     { label:'OT/Sensory', color:'#1A4D8C', bg:'#EBF2FC',
    desc:'Occupational Therapy frameworks: Jean Ayres\' Sensory Integration (1972) — sensory processing as foundational for learning; Winnie Dunn\'s Sensory Profile model (1997) — four sensory processing patterns. Sensory diet strategies and environmental modifications support regulation.',
    refs:'Ayres, A.J. (1972). Sensory Integration and Learning Disorders. Western Psychological Services; Dunn, W. (1997). The Impact of Sensory Processing Abilities. OTJR, 17(1).' },
  AAC:    { label:'AAC/PECS', color:'#8C2D5A', bg:'#F8EDF3',
    desc:'Augmentative and Alternative Communication (AAC) — core vocabulary approach (most frequently used words across contexts), PECS (Picture Exchange Communication System, Bondy & Frost), Makaton symbols. Visual supports for AAC users must align with their symbol system for consistency.',
    refs:'Beukelman, D. & Mirenda, P. (2013). Augmentative & Alternative Communication (4th ed.). Brookes; Bondy, A. & Frost, L. (2001). The Picture Exchange Communication System. Behavior Modification, 25(5); Ganz, J. et al. (2012). AAC meta-analysis. RAISD, 37(4).' },
  ZOR:    { label:'Zones of Reg', color:'#1E6F75', bg:'#E8F5F6',
    desc:'Zones of Regulation (Leah Kuypers, 2011) — categorises emotional and regulatory states into four colour-coded zones (Blue, Green, Yellow, Red). Teaches self-identification, triggers, and tool use. Pairs well with BSEM\'s co-regulation emphasis and Polyvagal theory.',
    refs:'Kuypers, L. (2011). The Zones of Regulation. Think Social Publishing; Winner, M.G. (2007). Thinking About You, Thinking About Me. Think Social Publishing.' },
  PODD:   { label:'PODD', color:'#7B3B8C', bg:'#F4EEF8',
    desc:'Pragmatic Organisation Dynamic Display (PODD) — developed by Gayle Porter at Royal Children\'s Hospital Melbourne. An AAC communication book/display system organised by communication function. Core vocabulary and fringe vocabulary systematically structured for robust communication.',
    refs:'Porter, G. & Cafiero, J. (2009). Pragmatic Organization Dynamic Display (PODD) Communication Books. Perspectives on AAC, 18(4); RCH Melbourne PODD resources.' },
  CG:     { label:'Social Stories™', color:'#3730A3', bg:'#EEEEF9',
    desc:'Social Stories™ (Carol Gray, 1991; 10th criterion updated 2015) — short, personalised narratives using a specific ratio of descriptive, perspective, directive, and affirmative sentences. Research supports effectiveness for ASD in understanding social situations.',
    refs:'Gray, C. (2015). The New Social Story Book. Future Horizons; Sansosti, F., Powell-Smith, K. & Kincaid, D. (2004). A research synthesis of Social Story interventions. Focus on ASD, 19(4).' },
  EALD:   { label:'EAL/D', color:'#2D5A8C', bg:'#EBF2FC',
    desc:'EAL/D (English as an Additional Language or Dialect) — ACARA EAL/D Framework and AITSL guidelines. Multimodal input (visual + verbal + gesture) significantly improves comprehension. Symbol + single word format reduces English processing demand while supporting language acquisition.',
    refs:'ACARA (2014). English as an Additional Language or Dialect Teacher Resource. ACARA; AITSL (2019). Supporting EAL/D students with additional needs. Melbourne: AITSL.' },
  UDL:    { label:'UDL', color:'#B83232', bg:'#FDF0EF',
    desc:'Universal Design for Learning (CAST, 2018) — three principles: multiple means of Representation, Action & Expression, and Engagement. Visual supports directly address UDL Representation guidelines (3.1–3.4: offering alternatives for auditory/visual info, comprehension supports).',
    refs:'CAST (2018). Universal Design for Learning Guidelines version 2.2. cast.org; Meyer, A., Rose, D. & Gordon, D. (2014). Universal Design for Learning: Theory and Practice. CAST.' },
  ABLES:  { label:'ABLES', color:'#1A5C78', bg:'#EBF5FA',
    desc:'ABLES (Abilities Based Learning and Education Support) — Victorian DET assessment framework for students with disabilities. Focuses on functional, strengths-based assessment across eight domains. Informs visual support selection based on individual learning profiles.',
    refs:'Victoria DET (2018). ABLES Assessment and Planning Resource. Education State Victoria; Foreman, P. (2014). Inclusion in Action (4th ed.). Cengage.' },
};

// ════════════════════════════════════════════════════════════
// CARD DATA
// ════════════════════════════════════════════════════════════
const CARDS = [
  {id:'feelings',cat:'regulation',color:'#D4860A',bg:'#FEF7EA',em:'😊😐😢😠',ti:'How am I feeling?',sub:'Point to show your feeling',fw:['BSEM','TI','ZOR']},
  {id:'calmdown',cat:'regulation',color:'#D4860A',bg:'#FEF7EA',em:'🧘',ti:"Let's calm down",sub:'Breathe · Move · Squeeze',fw:['BSEM','TI','OT']},
  {id:'break',cat:'regulation',color:'#D4860A',bg:'#FEF7EA',em:'⏸️',ti:'I need a break',sub:'I will come back soon',fw:['TI','PBS','BSEM']},
  {id:'bodycheck',cat:'regulation',color:'#D4860A',bg:'#FEF7EA',em:'🫁',ti:'Body check',sub:'What does my body feel?',fw:['OT','BSEM','TI']},
  {id:'zones',cat:'regulation',color:'#D4860A',bg:'#FEF7EA',em:'🔵🟢🟡🔴',ti:'What zone am I in?',sub:'Blue · Green · Yellow · Red',fw:['ZOR','BSEM']},
  {id:'welldown',cat:'regulation',color:'#D4860A',bg:'#FEF7EA',em:'🌟',ti:'Well done!',sub:"You're doing great",fw:['PBS','BSEM']},
  {id:'volume',cat:'regulation',color:'#D4860A',bg:'#FEF7EA',em:'🔊',ti:'Volume check 1–5',sub:'What level is my voice?',fw:['OT','PBS']},
  {id:'voicein',cat:'regulation',color:'#D4860A',bg:'#FEF7EA',em:'🏠',ti:'Inside voice',sub:'Quiet, calm voice inside',fw:['OT','EALD']},
  {id:'ineed',cat:'communication',color:'#1A5C78',bg:'#EBF5FA',em:'🙋',ti:'I need…',sub:'Toilet · Water · Food · Help',fw:['AAC','EALD']},
  {id:'corewords',cat:'communication',color:'#1A5C78',bg:'#EBF5FA',em:'💬',ti:'Core words',sub:'Yes · No · Want · Stop · More',fw:['AAC','EALD','UDL']},
  {id:'waiting',cat:'communication',color:'#1A5C78',bg:'#EBF5FA',em:'⏳',ti:"I'm waiting",sub:'Someone is coming',fw:['TEACCH','AAC']},
  {id:'quiet',cat:'communication',color:'#1A5C78',bg:'#EBF5FA',em:'🤫',ti:'Quiet time',sub:'This is a calm space',fw:['OT','BSEM']},
  {id:'goodtrying',cat:'communication',color:'#1A5C78',bg:'#EBF5FA',em:'👍',ti:'Good trying!',sub:'That was hard. You tried.',fw:['PBS','BSEM']},
  {id:'talktome',cat:'communication',color:'#1A5C78',bg:'#EBF5FA',em:'🗣️',ti:'I want to talk',sub:'I have something to say',fw:['AAC','BSEM']},
  {id:'question',cat:'communication',color:'#1A5C78',bg:'#EBF5FA',em:'❓',ti:'I have a question',sub:'Please listen to me',fw:['AAC','EALD']},
  {id:'help',cat:'communication',color:'#1A5C78',bg:'#EBF5FA',em:'🤝',ti:'I need help',sub:'Please help me',fw:['AAC','PBS']},
  {id:'play',cat:'communication',color:'#1A5C78',bg:'#EBF5FA',em:'🎮',ti:'Can I play?',sub:'Can I join in?',fw:['CG','BSEM']},
  {id:'poddcard',cat:'communication',color:'#1A5C78',bg:'#EBF5FA',em:'📱',ti:'My device',sub:'I will use my device',fw:['PODD','AAC']},
  {id:'firstthencard',cat:'routine',color:'#2D7D4F',bg:'#E8F5EE',em:'1️⃣→2️⃣',ti:'First → Then',sub:'First work, then reward',fw:['TEACCH','PBS']},
  {id:'nownext',cat:'routine',color:'#2D7D4F',bg:'#E8F5EE',em:'▶️⏭️',ti:'Now → Next',sub:"Here's what's coming next",fw:['TEACCH','PBS']},
  {id:'finished',cat:'routine',color:'#2D7D4F',bg:'#E8F5EE',em:'✅',ti:'Finished!',sub:'I am done with this task',fw:['TEACCH','PBS']},
  {id:'transition',cat:'routine',color:'#2D7D4F',bg:'#E8F5EE',em:'🔔',ti:'Time to change',sub:'We are finishing soon',fw:['TEACCH','TI']},
  {id:'fivemins',cat:'routine',color:'#2D7D4F',bg:'#E8F5EE',em:'⏱️',ti:'5 more minutes',sub:'Almost time to stop',fw:['TEACCH','PBS']},
  {id:'packup',cat:'routine',color:'#2D7D4F',bg:'#E8F5EE',em:'📦',ti:'Pack up time',sub:"Let's pack away",fw:['TEACCH','PBS']},
  {id:'steps',cat:'attention',color:'#C97B1A',bg:'#FEF7EA',em:'1️⃣2️⃣3️⃣',ti:'Task steps 1-2-3',sub:'Step · by · step',fw:['TEACCH','UDL']},
  {id:'choice',cat:'attention',color:'#C97B1A',bg:'#FEF7EA',em:'🤔',ti:'My choices',sub:'Choose one',fw:['UDL','PBS']},
  {id:'tokens',cat:'attention',color:'#C97B1A',bg:'#FEF7EA',em:'⭐⭐⭐',ti:'Token board',sub:'Earn your reward',fw:['PBS','BSEM']},
  {id:'listen',cat:'attention',color:'#C97B1A',bg:'#FEF7EA',em:'👂',ti:'Listening body',sub:'Eyes · Ears · Still body',fw:['BSEM','PBS']},
  {id:'seat',cat:'attention',color:'#C97B1A',bg:'#FEF7EA',em:'💺',ti:'Stay in your seat',sub:'Stay here to learn',fw:['PBS','TEACCH']},
  {id:'hands',cat:'attention',color:'#C97B1A',bg:'#FEF7EA',em:'🙌',ti:'Safe hands',sub:'Hands to yourself',fw:['BSEM','TI','PBS']},
  {id:'sensory',cat:'attention',color:'#C97B1A',bg:'#FEF7EA',em:'🎯',ti:'My sensory tools',sub:'Fidget · Squeeze · Stretch',fw:['OT','BSEM']},
  {id:'bubble',cat:'attention',color:'#C97B1A',bg:'#FEF7EA',em:'🫧',ti:'Body bubble',sub:'My space · Your space',fw:['BSEM','TI','CG']},
  {id:'myspace',cat:'places',color:'#5A3B8C',bg:'#F2EEF8',em:'🏷️',ti:'My learning space',sub:'This is my place',fw:['TEACCH','ABLES']},
  {id:'playground',cat:'places',color:'#5A3B8C',bg:'#F2EEF8',em:'🛝',ti:'Playground',sub:'Outside play time',fw:['TEACCH']},
  {id:'classroom',cat:'places',color:'#5A3B8C',bg:'#F2EEF8',em:'🏫',ti:'Classroom',sub:'Learning room',fw:['TEACCH']},
  {id:'kitchen',cat:'places',color:'#5A3B8C',bg:'#F2EEF8',em:'🍽️',ti:'Kitchen / dining',sub:'Food and eating area',fw:['TEACCH']},
  {id:'backseat',cat:'places',color:'#5A3B8C',bg:'#F2EEF8',em:'↩️',ti:'Back to your seat',sub:'Return to your spot',fw:['TEACCH','PBS']},
  {id:'yard',cat:'places',color:'#5A3B8C',bg:'#F2EEF8',em:'🌳',ti:'Outside / Yard',sub:'Outdoor learning space',fw:['TEACCH']},
  {id:'backspace',cat:'places',color:'#5A3B8C',bg:'#F2EEF8',em:'🏠',ti:'Back to learning space',sub:'Come back to your area',fw:['TEACCH','PBS']},
];

// ════════════════════════════════════════════════════════════
// ACTIVITY DATA (for First-Then/Schedule)
// ════════════════════════════════════════════════════════════
const ACTIVITIES = [
  // School
  {cat:'school',em:'✏️',lb:'Writing'},{cat:'school',em:'📚',lb:'Reading'},{cat:'school',em:'🔢',lb:'Maths'},{cat:'school',em:'🎨',lb:'Art'},{cat:'school',em:'🎵',lb:'Music'},{cat:'school',em:'🖥️',lb:'ICT / iPad'},{cat:'school',em:'📐',lb:'STEM'},{cat:'school',em:'🌍',lb:'HASS'},{cat:'school',em:'🏃',lb:'P.E. / Sport'},{cat:'school',em:'🔬',lb:'Science'},
  // Routine
  {cat:'routine',em:'🍎',lb:'Lunch'},{cat:'routine',em:'🥐',lb:'Breakfast'},{cat:'routine',em:'☕',lb:'Morning snack'},{cat:'routine',em:'🧹',lb:'Pack up'},{cat:'routine',em:'🎒',lb:'Bag time'},{cat:'routine',em:'🚌',lb:'Bus'},{cat:'routine',em:'🚶',lb:'Transition'},{cat:'routine',em:'🛁',lb:'Sensory break'},{cat:'routine',em:'🤸',lb:'Interoception'},{cat:'routine',em:'🧘',lb:'Calm down'},
  // Social
  {cat:'social',em:'🎮',lb:'Free play'},{cat:'social',em:'🧩',lb:'Puzzle / game'},{cat:'social',em:'🗺️',lb:'Group work'},{cat:'social',em:'👥',lb:'Circle time'},{cat:'social',em:'🤝',lb:'Chat time'},{cat:'social',em:'📸',lb:'Show & tell'},{cat:'social',em:'🎲',lb:'Board game'},{cat:'social',em:'🏐',lb:'Ball game'},
  // Reward
  {cat:'reward',em:'⭐',lb:'Star reward'},{cat:'reward',em:'🎉',lb:'Celebration'},{cat:'reward',em:'📺',lb:'Video time'},{cat:'reward',em:'🎧',lb:'Music time'},{cat:'reward',em:'🍫',lb:'Treat'},{cat:'reward',em:'💬',lb:'Chat time'},{cat:'reward',em:'🎨',lb:'Free draw'},{cat:'reward',em:'🏆',lb:'Trophy'},
  // Places
  {cat:'places',em:'🏫',lb:'Classroom'},{cat:'places',em:'🛝',lb:'Playground'},{cat:'places',em:'🍽️',lb:'Kitchen'},{cat:'places',em:'🚽',lb:'Toilet'},{cat:'places',em:'🌳',lb:'Outside'},{cat:'places',em:'📚',lb:'Library'},{cat:'places',em:'🏋️',lb:'Gym'},
];
const ACT_CATS = ['all','school','routine','social','reward','places'];

// ════════════════════════════════════════════════════════════
// PRESETS — Communication Board
// ════════════════════════════════════════════════════════════
const PRESETS = {
  feelings: [{em:'😊',tx:'Happy'},{em:'😢',tx:'Sad'},{em:'😠',tx:'Angry'},{em:'😰',tx:'Worried'},{em:'😴',tx:'Tired'},{em:'😐',tx:'Okay'},{em:'🤢',tx:'Sick'},{em:'🤩',tx:'Excited'},{em:'😮',tx:'Surprised'},{em:'🥱',tx:'Bored'},{em:'😤',tx:'Frustrated'},{em:'🥰',tx:'Loved'},{em:'😣',tx:'In pain'},{em:'🤔',tx:'Thinking'},{em:'😌',tx:'Calm'},{em:'😎',tx:'Cool'}],
  food: [{em:'🍎',tx:'Apple'},{em:'🥪',tx:'Sandwich'},{em:'🍌',tx:'Banana'},{em:'💧',tx:'Water'},{em:'🥛',tx:'Milk'},{em:'🥕',tx:'Carrot'},{em:'🍞',tx:'Bread'},{em:'🍫',tx:'Chocolate'},{em:'🥜',tx:'Nuts'},{em:'🍊',tx:'Orange'},{em:'🧃',tx:'Juice'},{em:'🍇',tx:'Grapes'}],
  places: [{em:'🏫',tx:'School'},{em:'🏠',tx:'Home'},{em:'🛝',tx:'Playground'},{em:'🍽️',tx:'Kitchen'},{em:'🚽',tx:'Toilet'},{em:'📚',tx:'Library'},{em:'🏋️',tx:'Gym'},{em:'🌳',tx:'Outside'}],
  activities: [{em:'🎨',tx:'Art'},{em:'✏️',tx:'Writing'},{em:'📚',tx:'Reading'},{em:'🎮',tx:'Play'},{em:'🎵',tx:'Music'},{em:'🏃',tx:'Exercise'},{em:'🧩',tx:'Puzzle'},{em:'🖥️',tx:'Computer'}],
  requests: [{em:'🙋',tx:'Help me'},{em:'💧',tx:'Water'},{em:'🚽',tx:'Toilet'},{em:'⏸️',tx:'Break'},{em:'❓',tx:'Question'},{em:'👍',tx:'Yes'},{em:'👎',tx:'No'},{em:'🔄',tx:'Again'},{em:'✅',tx:'Finished'},{em:'😊',tx:'I\'m okay'},{em:'😢',tx:'Not okay'},{em:'⏳',tx:'Wait'}],
  people: [{em:'👩‍🏫',tx:'Teacher'},{em:'👦',tx:'Me'},{em:'👥',tx:'Friends'},{em:'👩',tx:'Mum'},{em:'👨',tx:'Dad'},{em:'👴',tx:'Grandpa'},{em:'👵',tx:'Grandma'},{em:'🧑‍⚕️',tx:'Doctor'},{em:'🏫',tx:'School'}],
  core: [{em:'✅',tx:'Yes'},{em:'❌',tx:'No'},{em:'🙋',tx:'Want'},{em:'🛑',tx:'Stop'},{em:'➕',tx:'More'},{em:'✅',tx:'Done'},{em:'🤝',tx:'Help'},{em:'🔄',tx:'Go'},{em:'❤️',tx:'Like'},{em:'💔',tx:'Don\'t like'},{em:'👀',tx:'Look'},{em:'👂',tx:'Listen'}],
};

// ════════════════════════════════════════════════════════════
// CALM-DOWN STRATEGIES
// ════════════════════════════════════════════════════════════
const STRATEGIES = [
  {em:'🌬️',lb:'Deep breaths'},{em:'🧘',lb:'Mindful pause'},{em:'🚶',lb:'Walk it out'},{em:'💦',lb:'Cold water'},{em:'🎧',lb:'Music'},{em:'🤲',lb:'Squeeze ball'},{em:'🏃',lb:'Jump / move'},{em:'🎨',lb:'Draw / colour'},{em:'📖',lb:'Quiet reading'},{em:'🌟',lb:'Think happy'},{em:'🫂',lb:'Ask for hug'},{em:'🏋️',lb:'Heavy work'},{em:'🧩',lb:'Fidget toy'},{em:'💺',lb:'Sit quietly'},{em:'🌳',lb:'Go outside'},{em:'🐾',lb:'Animal breathing'},{em:'🫶',lb:'Self-hug'},{em:'⏱️',lb:'Count to 10'},
];

// ════════════════════════════════════════════════════════════
// SCRIPT SITUATIONS
// ════════════════════════════════════════════════════════════
const SITUATIONS = [
  {em:'🏫',ti:'Arriving at school',steps:['I come to school in the morning','I put my bag away','I say hello to my teacher','I find my seat','I am ready to learn']},
  {em:'🙋',ti:'Asking for help',steps:['I notice I need help','I raise my hand or use my card','I wait for my teacher','I ask my question','My teacher helps me']},
  {em:'🎮',ti:'Joining in play',steps:['I watch what my friends are doing','I say "Can I play?"','I wait for the answer','If they say yes, I join in','I share and take turns']},
  {em:'😞',ti:'Feeling disappointed',steps:['Sometimes things don\'t go my way','I might feel upset or sad','That is okay','I take a breath','I can try again later']},
  {em:'🍽️',ti:'Lunchtime',steps:['It is time for lunch','I find my lunchbox','I sit in my spot','I eat my food','When I\'m done I pack up']},
  {em:'🔔',ti:'Moving to next activity',steps:['I hear the signal for change','I finish what I am doing','I pack up my things','I move to the next activity','I am ready to start']},
  {em:'😠',ti:'When I feel angry',steps:['I notice my body feels hot/tight','I am in the red zone','I stop and breathe','I use a strategy from my toolkit','I feel better when I\'m calm']},
  {em:'🤝',ti:'Making an apology',steps:['I did something that hurt someone','I notice how they feel','I say "I\'m sorry"','I listen to their answer','We both feel better']},
];

// ════════════════════════════════════════════════════════════
// ZONES DATA
// ════════════════════════════════════════════════════════════
const ZONE_DATA = {
  blue:   { name:'Blue Zone — Low, Slow', feels:['Tired','Sad','Bored','Sick','Moving slowly'], strats:['Do some movement','Splash cold water on face','Listen to upbeat music','Have a snack','Do jumping jacks'] },
  green:  { name:'Green Zone — Ready to Learn', feels:['Happy','Calm','Focused','Ready','Content'], strats:['Keep going!','Use your tools if needed','Check in with teacher','You\'re in the best zone'] },
  yellow: { name:'Yellow Zone — Wobbly, Busy', feels:['Worried','Frustrated','Silly','Excited','Overwhelmed'], strats:['Take 3 deep breaths','Squeeze a fidget tool','Ask for a movement break','Get a drink of water','Use your calm-down menu'] },
  red:    { name:'Red Zone — Out of Control', feels:['Furious','Terrified','Panicking','Explosive','Out of control'], strats:['Move to your safe space','Take slow breaths','Use your sensory tool','Wait until Green Zone returns','Ask for help if needed'] },
};

const FIVE_SCALE_COLORS = ['#DBEAFE','#DCFCE7','#FEF9C3','#FED7AA','#FEE2E2'];
const FIVE_SCALE_EMOJIS = ['😌','😊','😬','😤','🤯'];

// ════════════════════════════════════════════════════════════
// EMOJI SETS
// ════════════════════════════════════════════════════════════
const COMMON_EMOJIS = ['😊','😢','😠','😰','😴','😐','🤢','🤩','😮','🥱','😤','🥰','😣','🤔','😌','😎','👍','👎','✅','❌','⭐','🌟','❤️','💔','🎉','🙋','🤝','👏','🫂','💡','🔔','⏱️','🏃','🧘','🌬️','💧','🎨','📚','✏️','🎵','🎮','🏫','🏠','🌳','🚌','🍎','🥪','🍫','💬','🔄','📦','⏳','💺','🛝'];

// ════════════════════════════════════════════════════════════
// UTILITY
// ════════════════════════════════════════════════════════════
function toast(msg, type='') {
  const el = document.getElementById('toast');
  el.textContent = msg; el.className = 'toast show ' + type;
  setTimeout(() => el.classList.remove('show'), 2500);
}
function openModal(id) { document.getElementById('modal-'+id).classList.add('open'); }
function closeModal(id) { document.getElementById('modal-'+id).classList.remove('open'); }
function switchTab(id) {
  document.querySelectorAll('.tab-panel').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));
  document.getElementById('tab-'+id).classList.add('active');
  document.querySelectorAll('.tab-btn').forEach(b=>{ if(b.textContent.toLowerCase().includes(id.slice(0,3))||b.onclick?.toString().includes("'"+id+"'")) b.classList.add('active'); });
  // Simpler: match by onclick
  document.querySelectorAll('.tab-btn').forEach(b=>{ const m = b.getAttribute('onclick')||''; if(m.includes("'"+id+"'")) b.classList.add('active'); });
}
function fwBadge(key) {
  const f = FW[key]; if(!f) return '';
  return `<span class="fw" style="background:${f.bg};color:${f.color}">${f.label}</span>`;
}
function updateQueueBadge() {
  document.getElementById('hdr-qcount').textContent = STATE.printQueue.length;
  document.getElementById('q-count').textContent = STATE.printQueue.length;
}

// ════════════════════════════════════════════════════════════
// STUDENT PROFILE
// ════════════════════════════════════════════════════════════
function saveProfile() {
  STATE.student = {
    name: document.getElementById('sp-name').value,
    age: document.getElementById('sp-age').value,
    cls: document.getElementById('sp-class').value,
    diag: document.getElementById('sp-diag').value,
    comm: document.getElementById('sp-comm').value,
    notes: document.getElementById('sp-notes').value,
  };
  localStorage.setItem('vsb_student', JSON.stringify(STATE.student));
  document.getElementById('hdr-sname').textContent = STATE.student.name || 'Set student';
  closeModal('student');
  // Pre-fill AI tab
  if(STATE.student.name) document.getElementById('ai-name').value = STATE.student.name;
  if(STATE.student.diag) document.getElementById('ai-diag').value = STATE.student.diag;
  if(STATE.student.notes) document.getElementById('ai-notes').value = STATE.student.notes;
  toast('Profile saved', 'ok');
}
function saveSettings() {
  CFG.proxyUrl = document.getElementById('set-proxy').value.trim();
  localStorage.setItem('vsb_proxy', CFG.proxyUrl);
  closeModal('settings');
  toast('Settings saved', 'ok');
}

// ════════════════════════════════════════════════════════════
// CARD BUILDER
// ════════════════════════════════════════════════════════════
let cardFilter = 'all', cardSearch = '';
function renderCards() {
  const all = [...CARDS, ...STATE.customCards];
  const filtered = all.filter(c => {
    const matchCat = cardFilter==='all' || c.cat===cardFilter;
    const matchSrch = !cardSearch || c.ti.toLowerCase().includes(cardSearch) || c.sub.toLowerCase().includes(cardSearch);
    return matchCat && matchSrch;
  });
  const grid = document.getElementById('cards-grid');
  grid.innerHTML = filtered.map(c => `
    <div class="sc${STATE.selectedCards.has(c.id)?' sel':''}" onclick="toggleCard('${c.id}')" style="border-top:3px solid ${c.color}">
      <div class="sc-em">${c.em}</div>
      <div class="sc-ti">${c.ti}</div>
      <div class="sc-su">${c.sub}</div>
      <div class="sc-fws">${(c.fw||[]).map(fwBadge).join('')}</div>
    </div>`).join('');
  updateSelBar();
}
function toggleCard(id) {
  if(STATE.selectedCards.has(id)) STATE.selectedCards.delete(id);
  else STATE.selectedCards.add(id);
  renderCards();
}
function filterCards(cat, el) {
  cardFilter = cat;
  document.querySelectorAll('.fpill').forEach(p=>p.classList.remove('on'));
  el.classList.add('on');
  renderCards();
}
function searchCards(q) { cardSearch = q.toLowerCase(); renderCards(); }
function clearCards() { STATE.selectedCards.clear(); renderCards(); }
function updateSelBar() {
  const bar = document.getElementById('sel-bar');
  const cnt = STATE.selectedCards.size;
  bar.style.display = cnt ? 'flex' : 'none';
  document.getElementById('sel-count').textContent = cnt + ' card' + (cnt!==1?'s':'') + ' selected';
}
function addCardsToQueue() {
  if(!STATE.selectedCards.size) { toast('Select cards first'); return; }
  const all = [...CARDS,...STATE.customCards];
  const selected = all.filter(c=>STATE.selectedCards.has(c.id));
  STATE.printQueue.push({ type:'cards', label:`${selected.length} lanyard card(s)`, icon:'🃏', data: selected });
  updateQueueBadge(); renderQueue();
  toast(`${selected.length} card(s) added to print queue`, 'ok');
}
function addCustomCard() {
  const em = document.getElementById('cc-em').value.trim();
  const ti = document.getElementById('cc-title').value.trim();
  const sub = document.getElementById('cc-sub').value.trim();
  const cat = document.getElementById('cc-cat').value;
  if(!em||!ti) { toast('Emoji and title required'); return; }
  const catColors = {regulation:'#D4860A',communication:'#1A5C78',routine:'#2D7D4F',attention:'#C97B1A',places:'#5A3B8C'};
  const catBgs = {regulation:'#FEF7EA',communication:'#EBF5FA',routine:'#E8F5EE',attention:'#FEF7EA',places:'#F2EEF8'};
  const id = 'custom-'+Date.now();
  STATE.customCards.push({id,cat,color:catColors[cat],bg:catBgs[cat],em,ti,sub,fw:[]});
  closeModal('customcard');
  renderCards();
  toast('Custom card added', 'ok');
}

// ════════════════════════════════════════════════════════════
// FIRST-THEN / NOW-NEXT
// ════════════════════════════════════════════════════════════
function setFTType(type, el) {
  STATE.ftType = type;
  STATE.ftSlots = [null,null,null];
  document.querySelectorAll('.ttbtn').forEach(b=>b.classList.remove('on'));
  el.classList.add('on');
  const grid = document.getElementById('ft-grid');
  if(type==='ft') {
    grid.className='ft-grid g2';
    grid.innerHTML = ftSlotHTML(0,'FIRST') + ftSlotHTML(1,'THEN');
  } else {
    grid.className='ft-grid g3';
    grid.innerHTML = ftSlotHTML(0,'NOW') + ftSlotHTML(1,'NEXT') + ftSlotHTML(2,'THEN');
  }
}
function ftSlotHTML(i, label) {
  return `<div class="ft-slot" id="ft-slot-${i}" onclick="openActPicker(${i})">
    <div class="ft-lbl" id="ft-lbl-${i}">${label}</div>
    <div class="ft-em" id="ft-em-${i}">➕</div>
    <div class="ft-ph" id="ft-ph-${i}">Click to choose activity</div>
  </div>`;
}
function openActPicker(slotIdx) {
  STATE.ftActiveSlot = slotIdx;
  const picker = document.getElementById('act-picker');
  picker.style.display = 'block';
  renderActCats();
  renderActGrid('all');
}
function renderActCats() {
  const el = document.getElementById('act-cats');
  el.innerHTML = ACT_CATS.map(c=>`<button class="act-cat${c===STATE.actCat?' on':''}" onclick="setActCat('${c}',this)">${c.charAt(0).toUpperCase()+c.slice(1)}</button>`).join('');
}
function setActCat(cat, el) {
  STATE.actCat = cat;
  document.querySelectorAll('.act-cat').forEach(b=>b.classList.remove('on'));
  el.classList.add('on');
  renderActGrid(cat);
}
function renderActGrid(cat, search='') {
  const el = document.getElementById('act-grid');
  let acts = cat==='all' ? ACTIVITIES : ACTIVITIES.filter(a=>a.cat===cat);
  if(search) acts = acts.filter(a=>a.lb.toLowerCase().includes(search));
  el.innerHTML = acts.map(a=>`<div class="act-item" onclick="selectAct('${a.em}','${a.lb}')"><div class="aiem">${a.em}</div><div class="ailb">${a.lb}</div></div>`).join('');
}
function searchActs(q) { renderActGrid(STATE.actCat, q.toLowerCase()); }
function selectAct(em, lb) {
  const i = STATE.ftActiveSlot;
  STATE.ftSlots[i] = {em, lb};
  const slot = document.getElementById('ft-slot-'+i);
  slot.classList.add('filled');
  const emEl = document.getElementById('ft-em-'+i);
  const phEl = document.getElementById('ft-ph-'+i);
  if(emEl) emEl.textContent = em;
  if(phEl) { phEl.textContent = lb; phEl.className='ft-tx'; }
  // Add clear button
  if(!document.getElementById('ft-clr-'+i)) {
    const clr = document.createElement('button');
    clr.className='ft-clr'; clr.id='ft-clr-'+i; clr.textContent='✕';
    clr.onclick=(e)=>{e.stopPropagation();clearFTSlot(i);};
    slot.appendChild(clr);
  }
  document.getElementById('act-picker').style.display='none';
}
function clearFTSlot(i) {
  STATE.ftSlots[i]=null;
  const labels = STATE.ftType==='ft' ? ['FIRST','THEN'] : ['NOW','NEXT','THEN'];
  const slot = document.getElementById('ft-slot-'+i);
  slot.classList.remove('filled');
  document.getElementById('ft-em-'+i).textContent='➕';
  document.getElementById('ft-ph-'+i).textContent='Click to choose activity';
  document.getElementById('ft-ph-'+i).className='ft-ph';
  const clr = document.getElementById('ft-clr-'+i);
  if(clr) clr.remove();
}
function addCustomAct() {
  const em = document.getElementById('custom-act-em').value.trim()||'📌';
  const lb = document.getElementById('custom-act-tx').value.trim();
  if(!lb) return;
  selectAct(em, lb);
  document.getElementById('custom-act-em').value='';
  document.getElementById('custom-act-tx').value='';
}
function addFTToQueue() {
  const filled = STATE.ftSlots.filter(Boolean);
  if(!filled.length) { toast('Add at least one activity'); return; }
  STATE.printQueue.push({ type:'firstthen', label: STATE.ftType==='ft'?'First-Then board':'Now-Next-Then board', icon:'🔄', data:{ type:STATE.ftType, slots:STATE.ftSlots, student:document.getElementById('ft-student').value, title:document.getElementById('ft-title').value } });
  updateQueueBadge(); renderQueue(); toast('Board added to print queue','ok');
}

// ════════════════════════════════════════════════════════════
// VISUAL SCHEDULE
// ════════════════════════════════════════════════════════════
function setSchedType(t, el) {
  STATE.schedType=t;
  document.querySelectorAll('.sched-type').forEach(b=>b.classList.remove('on'));
  el.classList.add('on');
  if(t==='strip' && STATE.schedSlots.length===0) {
    // Pre-fill 3 slots for strip
    STATE.schedSlots=[{time:'Now',em:'📌',act:'Current activity'},{time:'Next',em:'📌',act:'Next activity'},{time:'Later',em:'📌',act:'After that'}];
    renderSchedSlots();
  }
}
function addSchedSlot() {
  STATE.schedSlots.push({time:'',em:'📌',act:''});
  renderSchedSlots();
}
function removeSchedSlot(i) { STATE.schedSlots.splice(i,1); renderSchedSlots(); }
function renderSchedSlots() {
  const el = document.getElementById('sched-slots');
  if(!STATE.schedSlots.length) { el.innerHTML='<div style="text-align:center;padding:1.5rem;color:var(--text-sm);font-size:.83rem">No slots yet — click "+ Add time slot" below</div>'; return; }
  el.innerHTML = STATE.schedSlots.map((s,i)=>`
    <div class="slot-row">
      <span class="slot-drag">⠿</span>
      <span class="slot-em" onclick="openEmojiFor('slot',${i})">${s.em}</span>
      <div class="slot-body">
        <input value="${s.time}" placeholder="Time (e.g. 9:00am)" style="width:100%;border:none;background:transparent;font-size:.7rem;font-weight:700;color:var(--text-sm);margin-bottom:.1rem" oninput="STATE.schedSlots[${i}].time=this.value">
        <input value="${s.act}" placeholder="Activity name…" style="width:100%;border:none;background:transparent;font-size:.87rem;font-weight:700" oninput="STATE.schedSlots[${i}].act=this.value">
      </div>
      <div class="slot-acts">
        <button onclick="moveSlot(${i},-1)" title="Move up">▲</button>
        <button onclick="moveSlot(${i},1)" title="Move down">▼</button>
        <button onclick="removeSchedSlot(${i})" style="color:var(--red)">✕</button>
      </div>
    </div>`).join('');
}
function moveSlot(i, dir) {
  const j = i+dir;
  if(j<0||j>=STATE.schedSlots.length) return;
  [STATE.schedSlots[i],STATE.schedSlots[j]]=[STATE.schedSlots[j],STATE.schedSlots[i]];
  renderSchedSlots();
}
function openEmojiFor(type, idx) {
  STATE.emojiCallback = (em) => {
    if(type==='slot') { STATE.schedSlots[idx].em=em; renderSchedSlots(); }
    else if(type==='step') { STATE.scriptSteps[idx].em=em; renderScriptSteps(); }
    closeModal('emoji');
  };
  const grid = document.getElementById('emoji-grid');
  grid.innerHTML = COMMON_EMOJIS.map(e=>`<div class="ep-em" onclick="STATE.emojiCallback('${e}');this.closest('.modal-ov').classList.remove('open')">${e}</div>`).join('');
  openModal('emoji');
}
function addSchedToQueue() {
  if(!STATE.schedSlots.length) { toast('Add schedule slots first'); return; }
  STATE.printQueue.push({ type:'schedule', label: (document.getElementById('sched-title').value||'Visual Schedule'), icon:'📅', data:{ title:document.getElementById('sched-title').value, student:document.getElementById('sched-student').value, type:STATE.schedType, slots:[...STATE.schedSlots] } });
  updateQueueBadge(); renderQueue(); toast('Schedule added to print queue','ok');
}

// ════════════════════════════════════════════════════════════
// COMMUNICATION BOARD
// ════════════════════════════════════════════════════════════
function setGrid(size, el) {
  STATE.gridSize=size;
  document.querySelectorAll('.grid-opt').forEach(b=>b.classList.remove('on'));
  el.classList.add('on');
  const [cols,rows]=size.split('x').map(Number);
  const total=cols*rows;
  while(STATE.boardCells.length<total) STATE.boardCells.push({em:'',tx:''});
  STATE.boardCells = STATE.boardCells.slice(0,total);
  renderCommGrid();
}
function loadPreset(cat) {
  const items = PRESETS[cat]||[];
  const [cols,rows]=STATE.gridSize.split('x').map(Number);
  const total=cols*rows;
  STATE.boardCells = items.slice(0,total).map(i=>({...i,bg:''}));
  while(STATE.boardCells.length<total) STATE.boardCells.push({em:'',tx:''});
  renderCommGrid();
  toast(cat.charAt(0).toUpperCase()+cat.slice(1)+' preset loaded','ok');
}
function renderCommGrid() {
  const [cols]=STATE.gridSize.split('x').map(Number);
  const grid = document.getElementById('comm-grid');
  grid.style.gridTemplateColumns = `repeat(${cols},1fr)`;
  grid.innerHTML = STATE.boardCells.map((c,i)=>`
    <div class="comm-cell" onclick="editCell(${i})" style="${c.bg?'background:'+c.bg:''}">
      <span class="cc-ed">✏️</span>
      <div class="cc-em">${c.em||'＋'}</div>
      <div class="cc-tx">${c.tx||'<span style="color:#aaa;font-size:.7rem">click to edit</span>'}</div>
    </div>`).join('');
}
function editCell(i) {
  STATE.editingCell=i;
  document.getElementById('cell-em').value=STATE.boardCells[i].em||'';
  document.getElementById('cell-tx').value=STATE.boardCells[i].tx||'';
  document.getElementById('cell-bg').value=STATE.boardCells[i].bg||'#ffffff';
  openModal('cell');
}
function saveCell() {
  STATE.boardCells[STATE.editingCell]={
    em:document.getElementById('cell-em').value,
    tx:document.getElementById('cell-tx').value,
    bg:document.getElementById('cell-bg').value==='#ffffff'?'':document.getElementById('cell-bg').value,
  };
  closeModal('cell'); renderCommGrid();
}
function clearCell() {
  STATE.boardCells[STATE.editingCell]={em:'',tx:''};
  closeModal('cell'); renderCommGrid();
}
function addBoardToQueue() {
  const filled = STATE.boardCells.filter(c=>c.em||c.tx);
  if(!filled.length) { toast('Fill in some cells first'); return; }
  STATE.printQueue.push({ type:'board', label:(document.getElementById('board-title').value||'Communication Board'), icon:'💬', data:{ title:document.getElementById('board-title').value, student:document.getElementById('board-student').value, gridSize:STATE.gridSize, cells:[...STATE.boardCells] } });
  updateQueueBadge(); renderQueue(); toast('Board added to print queue','ok');
}

// ════════════════════════════════════════════════════════════
// REGULATION TOOLS
// ════════════════════════════════════════════════════════════
function setRegType(type, el) {
  STATE.regType=type;
  document.querySelectorAll('.reg-type').forEach(b=>b.classList.remove('on'));
  el.classList.add('on');
  document.querySelectorAll('.reg-panel').forEach(p=>p.classList.remove('active'));
  document.getElementById('reg-'+type).classList.add('active');
}
function renderZones() {
  ['blue','green','yellow','red'].forEach(z=>{
    const d = ZONE_DATA[z];
    document.getElementById('z-'+z+'-feels').innerHTML = d.feels.map(f=>`<span class="zone-feel">${f}</span>`).join('');
    const strats = [...d.strats, ...STATE.zoneStrats[z]];
    document.getElementById('z-'+z+'-strats').innerHTML = strats.map(s=>`• ${s}`).join('<br>');
  });
}
function addZoneStrat(zone) {
  const input = document.getElementById('z-'+zone+'-add');
  const val = input.value.trim();
  if(!val) return;
  STATE.zoneStrats[zone].push(val);
  input.value='';
  renderZones();
}
function renderFiveScale() {
  const el = document.getElementById('five-scale');
  el.innerHTML = [1,2,3,4,5].map(n=>`
    <div class="sp${STATE.fiveScaleLabels[n-1]?'':''}" style="background:${FIVE_SCALE_COLORS[n-1]};border-color:${FIVE_SCALE_COLORS[n-1]}">
      <div class="sp-num">${n}</div>
      <div class="sp-em">${FIVE_SCALE_EMOJIS[n-1]}</div>
      <input class="sp-input" value="${STATE.fiveScaleLabels[n-1]}" oninput="STATE.fiveScaleLabels[${n-1}]=this.value" placeholder="Label…">
    </div>`).join('');
}
function renderStratGrid() {
  const el = document.getElementById('str-grid');
  el.innerHTML = STRATEGIES.map((s,i)=>`
    <div class="str-card${STATE.selectedStrats.has(i)?' on':''}" onclick="toggleStrat(${i})">
      <div class="str-em">${s.em}</div>
      <div class="str-lb">${s.lb}</div>
    </div>`).join('');
}
function toggleStrat(i) {
  if(STATE.selectedStrats.has(i)) STATE.selectedStrats.delete(i);
  else STATE.selectedStrats.add(i);
  renderStratGrid();
}
function renderFeelingsPreview() {
  const style = document.getElementById('fc-style')?.value || 'faces';
  const feels = style==='zones' ? 
    [{em:'🔵',tx:'Blue'},{em:'🟢',tx:'Green'},{em:'🟡',tx:'Yellow'},{em:'🔴',tx:'Red'}] :
    [{em:'😊',tx:'Happy'},{em:'😐',tx:'Okay'},{em:'😢',tx:'Sad'},{em:'😠',tx:'Angry'},{em:'😰',tx:'Worried'},{em:'😴',tx:'Tired'}];
  const el = document.getElementById('feelings-preview');
  el.innerHTML = feels.map(f=>`<div style="background:#fff;border:2px solid var(--border);border-radius:8px;padding:.75rem .5rem;text-align:center"><div style="font-size:2rem">${f.em}</div><div style="font-size:.78rem;font-weight:700;margin-top:.3rem">${f.tx}</div></div>`).join('');
}
function addRegToQueue() {
  const type = STATE.regType;
  const labels = {zones:'Zones of Regulation',fivepoint:'5-Point Scale',calmdown:'Calm-Down Menu',feelings:'Feelings Check-In'};
  const icons = {zones:'🟢',fivepoint:'5️⃣',calmdown:'🌬️',feelings:'😊'};
  const data = type==='zones' ? { zones:ZONE_DATA, custom:STATE.zoneStrats } :
    type==='fivepoint' ? { labels:STATE.fiveScaleLabels, student:document.getElementById('fps-student')?.value||'' } :
    type==='calmdown' ? { strats:[...STATE.selectedStrats].map(i=>STRATEGIES[i]), student:document.getElementById('cd-student')?.value||'', title:document.getElementById('cd-title')?.value||'' } :
    { style:document.getElementById('fc-style')?.value||'faces', student:document.getElementById('fc-student')?.value||'' };
  STATE.printQueue.push({ type:'regulation', label:labels[type], icon:icons[type], data });
  updateQueueBadge(); renderQueue(); toast('Added to print queue','ok');
}

// ════════════════════════════════════════════════════════════
// SOCIAL SCRIPTS
// ════════════════════════════════════════════════════════════
function renderSituations() {
  const el = document.getElementById('script-situations');
  el.innerHTML = SITUATIONS.map((s,i)=>`<button class="situ-btn" onclick="loadSituation(${i})">${s.em} ${s.ti}</button>`).join('');
}
function loadSituation(i) {
  const s = SITUATIONS[i];
  document.getElementById('sc-title').value = s.ti;
  STATE.scriptSteps = s.steps.map((t,j)=>({em:'📌',tx:t}));
  renderScriptSteps();
  document.querySelectorAll('.situ-btn').forEach((b,j)=>b.classList.toggle('on',j===i));
}
function renderScriptSteps() {
  const el = document.getElementById('script-steps');
  if(!STATE.scriptSteps.length) { el.innerHTML='<div style="text-align:center;padding:1rem;color:var(--text-sm);font-size:.83rem">Choose a situation above or click "+ Add step"</div>'; return; }
  el.innerHTML = STATE.scriptSteps.map((s,i)=>`
    <div class="step-row">
      <div class="step-num">${i+1}</div>
      <span class="step-em" onclick="openEmojiFor('step',${i})">${s.em}</span>
      <input class="step-tx" value="${s.tx}" placeholder="What happens at this step…" oninput="STATE.scriptSteps[${i}].tx=this.value" style="border:none;background:transparent;font-size:.87rem;font-weight:600;flex:1">
      <div class="step-dels">
        <button onclick="moveStep(${i},-1)">▲</button>
        <button onclick="moveStep(${i},1)">▼</button>
        <button onclick="removeStep(${i})" style="color:var(--red)">✕</button>
      </div>
    </div>`).join('');
}
function addScriptStep() { STATE.scriptSteps.push({em:'📌',tx:''}); renderScriptSteps(); }
function removeStep(i) { STATE.scriptSteps.splice(i,1); renderScriptSteps(); }
function moveStep(i, dir) {
  const j=i+dir;
  if(j<0||j>=STATE.scriptSteps.length) return;
  [STATE.scriptSteps[i],STATE.scriptSteps[j]]=[STATE.scriptSteps[j],STATE.scriptSteps[i]];
  renderScriptSteps();
}
async function generateScript() {
  const student = document.getElementById('sc-student').value;
  const title = document.getElementById('sc-title').value;
  const notes = STATE.student.notes || '';
  if(!title) { toast('Enter a script title first'); return; }
  if(!CFG.proxyUrl) { openModal('settings'); toast('Set your Groq proxy URL in settings first'); return; }
  toast('Generating script…');
  try {
    const prompt = `Write a Social Story™ following Carol Gray's framework for ${student||'a student'} about: "${title}".
Student profile: ${notes||'No additional details provided'}.
Return ONLY a JSON array of steps: [{"em":"emoji","tx":"step text"}, ...]
Use 5-7 steps. Keep language simple, positive, first-person. Use descriptive, perspective, directive and affirmative sentences.`;
    const res = await fetch(CFG.proxyUrl, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({ model:'llama3-70b-8192', max_tokens:800, messages:[{role:'user',content:prompt}] })
    });
    const d = await res.json();
    let text = d.choices?.[0]?.message?.content||'';
    text = text.replace(/```json?|```/g,'').trim();
    const steps = JSON.parse(text);
    STATE.scriptSteps = steps;
    renderScriptSteps();
    toast('Script generated!','ok');
  } catch(e) { toast('Generation failed — check proxy URL','err'); }
}
function addScriptToQueue() {
  if(!STATE.scriptSteps.length) { toast('Add steps first'); return; }
  STATE.printQueue.push({ type:'script', label:document.getElementById('sc-title').value||'Social Script', icon:'📖', data:{ title:document.getElementById('sc-title').value, student:document.getElementById('sc-student').value, steps:[...STATE.scriptSteps] } });
  updateQueueBadge(); renderQueue(); toast('Script added to print queue','ok');
}

// ════════════════════════════════════════════════════════════
// AI SUGGEST
// ════════════════════════════════════════════════════════════
function renderFWRefs() {
  const el = document.getElementById('fw-refs');
  el.innerHTML = Object.entries(FW).map(([k,f])=>`
    <button class="fw-ref" style="background:${f.bg};color:${f.color};border-color:${f.color}44" onclick="showFWDetail('${k}')">${f.label}</button>`).join('');
}
function showFWDetail(key) {
  const f = FW[key];
  document.getElementById('fw-modal-title').textContent = f.label;
  document.getElementById('fw-modal-body').innerHTML = `
    <p style="margin-bottom:.75rem">${f.desc}</p>
    <div style="background:var(--cream);padding:.75rem;border-radius:var(--radius-sm);font-size:.8rem;line-height:1.6">
      <strong>Key references:</strong><br>${f.refs}
    </div>`;
  openModal('fw');
}
async function generateAI() {
  const name = document.getElementById('ai-name').value.trim();
  const age = document.getElementById('ai-age').value.trim();
  const diag = document.getElementById('ai-diag').value.trim();
  const comm = document.getElementById('ai-comm').value.trim();
  const notes = document.getElementById('ai-notes').value.trim();
  if(!diag && !notes) { toast('Enter at least a diagnosis or key needs'); return; }
  if(!CFG.proxyUrl) { openModal('settings'); toast('Set your Groq proxy URL in settings first'); return; }
  const resultsEl = document.getElementById('ai-results');
  resultsEl.innerHTML = '<div class="ai-loading"><div class="ai-spinner">🔄</div><br>Analysing student profile across 12 research frameworks…</div>';
  document.getElementById('ai-btn').disabled=true;
  const systemPrompt = `You are an expert special education and AAC specialist drawing on these frameworks:
1. Berry Street Education Model (BSEM) - trauma-informed, body-brain connection, co-regulation
2. Trauma-Informed Practice - Perry's neurosequential model, van der Kolk, Polyvagal Theory (Porges)
3. PODD (Gayle Porter, RCH Melbourne) - robust AAC, pragmatic organisation
4. Zones of Regulation (Kuypers, 2011) - emotional regulatory states
5. TEACCH / Structured Teaching (Mesibov, Shea & Schopler) - visual structure, temporal organisation
6. PBS (Positive Behaviour Support) - function-based, antecedent modification
7. Sensory Processing / OT (Ayres SPD, Winnie Dunn's Sensory Profile) - sensory diet strategies
8. AAC / Core Vocabulary (Beukelman & Mirenda, Ganz meta-analyses, PECS, Makaton)
9. Social Stories™ (Carol Gray) - descriptive/perspective/directive/affirmative sentence types
10. ABLES (Victorian DET) - functional, strengths-based assessment
11. EALD/EAL/D (ACARA EAL/D Framework, AITSL) - multimodal input for multilingual learners
12. UDL (CAST, 2018) - multiple means of representation, expression, engagement

Return ONLY a JSON array. No preamble, no markdown. Format:
[{"tool":"tool type","title":"specific visual support name","why":"1-2 sentence evidence-based rationale","frameworks":["FW1","FW2"],"priority":"high/medium"}]

Tool types: "lanyard_card", "first_then", "schedule", "comm_board", "regulation", "social_script"
Framework keys must be from: BSEM, TI, TEACCH, PBS, OT, AAC, ZOR, PODD, CG, EALD, UDL, ABLES`;

  const userPrompt = `Student: ${name||'unnamed'}, ${age||'age unknown'}
Diagnoses/profile: ${diag||'not specified'}
Communication: ${comm||'not specified'}
Key needs & behaviours: ${notes||'not specified'}

Provide 8-10 specific visual support recommendations ordered by priority. Be specific — name exact cards or tools.`;

  try {
    const res = await fetch(CFG.proxyUrl, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({ model:'llama3-70b-8192', max_tokens:1500,
        messages:[{role:'system',content:systemPrompt},{role:'user',content:userPrompt}] })
    });
    const d = await res.json();
    let text = d.choices?.[0]?.message?.content||'';
    text = text.replace(/```json?|```/g,'').trim();
    const suggestions = JSON.parse(text);
    renderAISuggestions(suggestions);
  } catch(e) {
    resultsEl.innerHTML = '<div class="card" style="color:var(--red)">Generation failed. Check your proxy URL in settings. Error: '+e.message+'</div>';
  }
  document.getElementById('ai-btn').disabled=false;
}
function renderAISuggestions(suggestions) {
  const toolIcons = {lanyard_card:'🃏',first_then:'🔄',schedule:'📅',comm_board:'💬',regulation:'🧘',social_script:'📖'};
  const toolLabels = {lanyard_card:'Lanyard Card',first_then:'First-Then Board',schedule:'Visual Schedule',comm_board:'Comm Board',regulation:'Regulation Tool',social_script:'Social Script'};
  const el = document.getElementById('ai-results');
  el.innerHTML = `<div class="section-title">AI Recommendations (${suggestions.length} suggestions)</div>` +
    suggestions.map(s=>`
      <div class="ai-sug" style="border-left-color:${s.priority==='high'?'var(--amber)':'var(--teal)'}">
        <div class="sug-header">
          <span class="sug-title">${toolIcons[s.tool]||'📌'} ${s.title}</span>
          <span class="sug-type">${toolLabels[s.tool]||s.tool}</span>
        </div>
        <div class="sug-why">${s.why}</div>
        <div class="sug-fws">${(s.frameworks||[]).map(fwBadge).join('')}</div>
      </div>`).join('');
}

// ════════════════════════════════════════════════════════════
// PRINT QUEUE
// ════════════════════════════════════════════════════════════
function setFormat(fmt, el) {
  STATE.printFormat=fmt;
  document.querySelectorAll('.pf-opt').forEach(o=>o.classList.remove('on'));
  el.classList.add('on');
}
function renderQueue() {
  updateQueueBadge();
  const el = document.getElementById('queue-list');
  if(!STATE.printQueue.length) {
    el.innerHTML='<div class="q-empty">🗂️<br><br>Nothing in the queue yet.<br>Build a card set, schedule, board or script then click "Add to queue".</div>';
    return;
  }
  el.innerHTML = STATE.printQueue.map((item,i)=>`
    <div class="q-item">
      <div class="qi-icon">${item.icon}</div>
      <div style="flex:1"><div class="qi-name">${item.label}</div><div class="qi-type">${item.type}</div></div>
      <button class="btn btn-sm btn-danger" onclick="removeFromQueue(${i})">Remove</button>
    </div>`).join('');
}
function removeFromQueue(i) { STATE.printQueue.splice(i,1); renderQueue(); }
function clearQueue() { STATE.printQueue=[]; renderQueue(); }

function doPrint() {
  if(!STATE.printQueue.length) { toast('Queue is empty'); return; }
  const fmt = STATE.printFormat;
  const win = window.open('','_blank');
  win.document.write(buildPrintHTML(fmt));
  win.document.close();
  setTimeout(()=>win.print(), 600);
}

function buildPrintHTML(fmt) {
  const isA3 = fmt==='desk-a3';
  const isLanyard = fmt==='lanyard';
  const pageSize = isA3 ? '297mm 420mm' : '210mm 297mm';
  const cols = isLanyard ? 2 : isA3 ? 2 : 2;
  const cardW = isLanyard ? '85mm' : isA3 ? '130mm' : '90mm';
  const cardH = isLanyard ? '54mm' : isA3 ? '90mm' : '75mm';

  let cards = [];
  STATE.printQueue.forEach(item => {
    if(item.type==='cards') {
      item.data.forEach(c => cards.push(buildCardHTML(c, isLanyard)));
    } else if(item.type==='firstthen') {
      cards.push(buildFTCardHTML(item.data, isLanyard));
    } else if(item.type==='schedule') {
      cards.push(buildSchedCardHTML(item.data, isLanyard));
    } else if(item.type==='board') {
      cards.push(buildBoardCardHTML(item.data, isLanyard));
    } else if(item.type==='regulation') {
      cards.push(buildRegCardHTML(item.data, isLanyard));
    } else if(item.type==='script') {
      cards.push(buildScriptCardHTML(item.data, isLanyard));
    }
  });

  // Group into pages
  const perPage = isLanyard ? 8 : isA3 ? 4 : 4;
  const pages = [];
  for(let i=0;i<cards.length;i+=perPage) pages.push(cards.slice(i,i+perPage));

  return `<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&display=swap');
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Nunito',sans-serif;background:#fff}
@page{size:${pageSize};margin:6mm}
.page{width:100%;display:grid;grid-template-columns:repeat(${cols},1fr);gap:4mm;page-break-after:always;align-content:start}
.page:last-child{page-break-after:avoid}
.card{width:100%;min-height:${cardH};border-radius:8px;border:1.5px solid #dde;overflow:hidden;display:flex;flex-direction:column;position:relative}
.card-body{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:${isLanyard?'6px 5px':'10px 8px'};text-align:center}
.card-top{width:100%;height:6px}
.card-em{font-size:${isLanyard?'22px':'32px'};line-height:1;margin-bottom:4px}
.card-ti{font-size:${isLanyard?'9px':'13px'};font-weight:800;color:#1a2e44;line-height:1.2}
.card-su{font-size:${isLanyard?'7px':'10px'};color:#718096;margin-top:2px;line-height:1.3}
.card-fws{margin-top:4px;display:flex;flex-wrap:wrap;justify-content:center;gap:2px}
.fw-p{padding:1px 5px;border-radius:10px;font-size:${isLanyard?'5.5px':'7px'};font-weight:700}
.punch{width:8px;height:8px;border-radius:50%;border:1.5px solid #dde;position:absolute;top:4px;left:50%;transform:translateX(-50%);background:#fff}
/* FT card */
.ft-card-body{flex:1;display:grid;align-content:start}
.ft-panel{display:flex;flex-direction:column;align-items:center;justify-content:center;padding:6px 4px;border:1px solid #eee;text-align:center;border-radius:4px;background:#f8f9fa}
.ft-lbl-p{font-size:${isLanyard?'7px':'9px'};font-weight:800;text-transform:uppercase;letter-spacing:.05em;color:#718096;margin-bottom:3px}
.ft-em-p{font-size:${isLanyard?'20px':'28px'};line-height:1}
.ft-tx-p{font-size:${isLanyard?'8px':'11px'};font-weight:700;margin-top:2px}
/* Schedule */
.sched-slot-p{display:flex;align-items:center;gap:4px;padding:3px 6px;border-bottom:1px solid #f0f0f0;font-size:${isLanyard?'7px':'10px'}}
.sched-time-p{font-size:${isLanyard?'6px':'8px'};color:#718096;min-width:28px;font-weight:700}
.sched-em-p{font-size:${isLanyard?'12px':'18px'}}
.sched-act-p{font-weight:700;font-size:${isLanyard?'7px':'10px'}}
/* Comm board */
.board-grid-p{display:grid;gap:2px;flex:1;padding:4px}
.board-cell-p{border:1px solid #dde;border-radius:4px;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:2px;text-align:center}
.board-cell-em{font-size:${isLanyard?'14px':'20px'}}
.board-cell-tx{font-size:${isLanyard?'6px':'8px'};font-weight:700;margin-top:1px}
</style>
</head><body>
${pages.map(pg=>`<div class="page">${pg.join('')}</div>`).join('')}
</body></html>`;
}

function buildCardHTML(c, isLanyard) {
  const fwHtml = (c.fw||[]).map(k=>{ const f=FW[k]; return f?`<span class="fw-p" style="background:${f.bg};color:${f.color}">${f.label}</span>`:'';}).join('');
  return `<div class="card">
    <div class="card-top" style="background:${c.color}"></div>
    <div class="punch"></div>
    <div class="card-body">
      <div class="card-em">${c.em||'📌'}</div>
      <div class="card-ti">${c.ti}</div>
      <div class="card-su">${c.sub}</div>
      ${isLanyard?`<div class="card-fws">${fwHtml}</div>`:''}
    </div>
  </div>`;
}

function buildFTCardHTML(data, isLanyard) {
  const slots = data.type==='ft' ? [data.slots[0],data.slots[1]] : data.slots;
  const labels = data.type==='ft' ? ['FIRST','THEN'] : ['NOW','NEXT','THEN'];
  const gridCols = data.type==='ft' ? '1fr auto 1fr' : '1fr auto 1fr auto 1fr';
  const name = data.student ? `${data.student}'s ` : '';
  return `<div class="card">
    <div class="card-top" style="background:#2D7D4F"></div>
    <div class="punch"></div>
    <div class="card-body" style="padding:6px 5px">
      <div style="font-size:8px;font-weight:800;color:#1a2e44;margin-bottom:4px">${name}${data.title||''}</div>
      <div style="display:grid;grid-template-columns:${gridCols};gap:2px;width:100%;align-items:center">
        ${slots.filter((_,i)=>i<(data.type==='ft'?2:3)).map((s,i)=>`
          ${i>0?'<div style="font-size:14px;color:#718096">→</div>':''}
          <div class="ft-panel">
            <div class="ft-lbl-p">${labels[i]}</div>
            <div class="ft-em-p">${s?s.em:'?'}</div>
            <div class="ft-tx-p">${s?s.lb:''}</div>
          </div>`).join('')}
      </div>
    </div>
  </div>`;
}

function buildSchedCardHTML(data, isLanyard) {
  const slots = data.slots.slice(0, isLanyard?5:8);
  return `<div class="card">
    <div class="card-top" style="background:#1A5C78"></div>
    <div class="punch"></div>
    <div class="card-body" style="padding:4px 0;justify-content:flex-start;align-items:stretch">
      <div style="text-align:center;font-size:8px;font-weight:800;color:#1a2e44;padding:2px 6px 4px">${data.student?data.student+"'s ":""} ${data.title||'Schedule'}</div>
      ${slots.map(s=>`<div class="sched-slot-p"><span class="sched-time-p">${s.time}</span><span class="sched-em-p">${s.em}</span><span class="sched-act-p">${s.act}</span></div>`).join('')}
    </div>
  </div>`;
}

function buildBoardCardHTML(data, isLanyard) {
  const [cols,rows] = data.gridSize.split('x').map(Number);
  return `<div class="card">
    <div class="card-top" style="background:#8C2D5A"></div>
    <div class="punch"></div>
    <div style="flex:1;display:flex;flex-direction:column;padding:3px">
      <div style="text-align:center;font-size:8px;font-weight:800;color:#1a2e44;margin-bottom:2px">${data.title||'Communication Board'}</div>
      <div class="board-grid-p" style="grid-template-columns:repeat(${cols},1fr);flex:1">
        ${data.cells.map(c=>`<div class="board-cell-p" style="${c.bg?'background:'+c.bg:''}"><span class="board-cell-em">${c.em||''}</span><span class="board-cell-tx">${c.tx||''}</span></div>`).join('')}
      </div>
    </div>
  </div>`;
}

function buildRegCardHTML(data, isLanyard) {
  if(data.zones) {
    const zones=[['blue','🔵','#DBEAFE'],['green','🟢','#DCFCE7'],['yellow','🟡','#FEF9C3'],['red','🔴','#FEE2E2']];
    return `<div class="card">
      <div class="card-top" style="background:linear-gradient(to right,#3B82F6,#22C55E,#EAB308,#EF4444)"></div>
      <div class="punch"></div>
      <div class="card-body" style="padding:4px;align-items:stretch;justify-content:flex-start">
        <div style="text-align:center;font-size:8px;font-weight:800;margin-bottom:3px">Zones of Regulation</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:2px;flex:1">
          ${zones.map(([z,em,bg])=>`<div style="background:${bg};border-radius:4px;padding:3px 4px"><div style="font-size:8px;font-weight:800">${em} ${z.charAt(0).toUpperCase()+z.slice(1)}</div><div style="font-size:6.5px;line-height:1.4">${ZONE_DATA[z].feels.slice(0,3).join(' · ')}</div></div>`).join('')}
        </div>
      </div>
    </div>`;
  } else if(data.labels) {
    return `<div class="card">
      <div class="card-top" style="background:var(--teal,#1A5C78)"></div>
      <div class="punch"></div>
      <div class="card-body" style="padding:4px">
        <div style="font-size:8px;font-weight:800;margin-bottom:3px">${data.student?""+data.student+"'s ":""} 5-Point Scale</div>
        <div style="display:flex;gap:2px;width:100%">
          ${[0,1,2,3,4].map(i=>`<div style="flex:1;background:${FIVE_SCALE_COLORS[i]};border-radius:4px;text-align:center;padding:2px"><div style="font-size:11px">${FIVE_SCALE_EMOJIS[i]}</div><div style="font-size:8px;font-weight:800">${i+1}</div><div style="font-size:5.5px;font-weight:600">${data.labels[i]||''}</div></div>`).join('')}
        </div>
      </div>
    </div>`;
  } else if(data.strats) {
    return `<div class="card">
      <div class="card-top" style="background:#2D7D4F"></div>
      <div class="punch"></div>
      <div class="card-body" style="padding:4px;align-items:flex-start;justify-content:flex-start">
        <div style="font-size:8px;font-weight:800;margin-bottom:3px;width:100%;text-align:center">${data.title||'Calm-Down Toolkit'}</div>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:2px;width:100%">
          ${data.strats.slice(0,9).map(s=>`<div style="text-align:center;padding:2px"><div style="font-size:12px">${s.em}</div><div style="font-size:6px;font-weight:700">${s.lb}</div></div>`).join('')}
        </div>
      </div>
    </div>`;
  }
  return buildCardHTML({em:'😊',ti:'Feelings Check-In',sub:'How am I feeling?',color:'#D4860A',fw:['ZOR','BSEM']}, isLanyard);
}

function buildScriptCardHTML(data, isLanyard) {
  return `<div class="card">
    <div class="card-top" style="background:#3730A3"></div>
    <div class="punch"></div>
    <div class="card-body" style="padding:4px;align-items:flex-start;justify-content:flex-start">
      <div style="font-size:8px;font-weight:800;margin-bottom:2px;width:100%;text-align:center">${data.student?data.student+"'s ":""} ${data.title||'Social Script'}</div>
      ${data.steps.slice(0,isLanyard?4:6).map((s,i)=>`<div style="display:flex;align-items:flex-start;gap:3px;margin-bottom:2px;width:100%"><div style="min-width:14px;height:14px;border-radius:50%;background:#3730A3;color:#fff;font-size:7px;font-weight:800;display:flex;align-items:center;justify-content:center">${i+1}</div><div style="font-size:7px;font-weight:600;line-height:1.3">${s.em} ${s.tx}</div></div>`).join('')}
    </div>
  </div>`;
}

// ════════════════════════════════════════════════════════════
// INIT
// ════════════════════════════════════════════════════════════
function init() {
  renderCards();
  renderActCats();
  renderActGrid('all');
  renderSchedSlots();
  setGrid('2x2', document.querySelector('.grid-opt.on'));
  renderCommGrid();
  renderZones();
  renderFiveScale();
  renderStratGrid();
  renderFeelingsPreview();
  renderSituations();
  renderScriptSteps();
  renderFWRefs();
  renderQueue();
  // Restore student
  if(STATE.student.name) {
    document.getElementById('hdr-sname').textContent = STATE.student.name;
    document.getElementById('sp-name').value = STATE.student.name || '';
    document.getElementById('sp-age').value = STATE.student.age || '';
    document.getElementById('sp-class').value = STATE.student.cls || '';
    document.getElementById('sp-diag').value = STATE.student.diag || '';
    document.getElementById('sp-comm').value = STATE.student.comm || '';
    document.getElementById('sp-notes').value = STATE.student.notes || '';
    if(STATE.student.name) document.getElementById('ai-name').value = STATE.student.name;
    if(STATE.student.diag) document.getElementById('ai-diag').value = STATE.student.diag;
    if(STATE.student.notes) document.getElementById('ai-notes').value = STATE.student.notes;
  }
  if(CFG.proxyUrl) document.getElementById('set-proxy').value = CFG.proxyUrl;
  // Close modals on overlay click
  document.querySelectorAll('.modal-ov').forEach(ov=>{
    ov.addEventListener('click', e=>{ if(e.target===ov) ov.classList.remove('open'); });
  });
  // Feelings preview listener
  document.getElementById('fc-style')?.addEventListener('change', renderFeelingsPreview);
}
document.addEventListener('DOMContentLoaded', init);
</script>
</body>
</html>
