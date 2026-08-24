<title>Window of Tolerance Builder</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght,ital@9..144,400..700,0..1&family=IBM+Plex+Sans:wght@400;500;600;700&family=Newsreader:ital,wght@0,400;0,500;0,600;1,400;1,500&family=Work+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/dist/umd/supabase.js"></script>

<style>
  :root{
    --bg:#F1F4EF;
    --surface:#FFFFFF;
    --surface-2:#E7ECE3;
    --surface-3:#DEE5D9;
    --ink:#1B211C;
    --ink-soft:#57604F;
    --ink-faint:#818B77;
    --border:#D2DACB;
    --accent:#2F6F6A;
    --accent-ink:#FFFFFF;
    --accent-wash:#DEEAE7;
    --shadow: 0 1px 2px rgba(27,33,28,0.06), 0 6px 20px -8px rgba(27,33,28,0.18);

    --hyper:#AF3A2C;       --hyper-wash:#F5E1DC;
    --copingup:#B9761A;    --copingup-wash:#F3E5CC;
    --wot:#2E7A48;         --wot-wash:#DDEBE0;
    --copingdown:#2A6693;  --copingdown-wash:#DCE7EF;
    --hypo:#3C4C6B;        --hypo-wash:#E1E4EB;

    /* fixed print palette — always renders the same on paper, regardless of screen theme */
    --print-red:#E14B3D;
    --print-amber:#F2A93C;
    --print-green:#8BC24A;
    --print-navy:#1F2A38;

    /* regulation-map print style — its own fixed palette, independent of screen theme */
    --map-paper:#F3F5F7;
    --map-ink:#1E2530;
    --map-ink-soft:#565F6E;
    --map-ink-faint:#8892A0;
    --map-rule:#D6DBE1;
    --map-hyper:#C1543A;     --map-hyper-tint:#F3E2DC;
    --map-copeup:#C98A2E;    --map-copeup-tint:#F3E7D3;
    --map-wot:#4C7A5A;       --map-wot-tint:#E1EBE3;
    --map-copedown:#3E6E8E;  --map-copedown-tint:#DEE7ED;
    --map-hypo:#38456B;      --map-hypo-tint:#DFE2EA;

    --font-display:'Fraunces', 'Iowan Old Style', Georgia, serif;
    --font-body:'IBM Plex Sans', 'Segoe UI', system-ui, sans-serif;
    --font-serif-map:'Newsreader', 'Iowan Old Style', Georgia, serif;
    --font-sans-map:'Work Sans', 'Segoe UI', system-ui, sans-serif;
  }

  @media (prefers-color-scheme: dark){
    :root:not([data-theme="light"]){
      --bg:#12160F;
      --surface:#191F17;
      --surface-2:#212820;
      --surface-3:#2A3227;
      --ink:#E8ECE2;
      --ink-soft:#AEB8A2;
      --ink-faint:#7C8672;
      --border:#333D2C;
      --accent:#6FB6AC;
      --accent-ink:#0C1512;
      --accent-wash:#1E3230;

      --hyper:#E2705F;      --hyper-wash:#3A2420;
      --copingup:#E3A64C;   --copingup-wash:#3A2F18;
      --wot:#63BD82;        --wot-wash:#1F3324;
      --copingdown:#6AA8D6; --copingdown-wash:#1E2C38;
      --hypo:#8E9DBE;       --hypo-wash:#252B3A;

      --shadow: 0 1px 2px rgba(0,0,0,0.35), 0 10px 26px -10px rgba(0,0,0,0.5);
    }
  }
  :root[data-theme="dark"]{
    --bg:#12160F;
    --surface:#191F17;
    --surface-2:#212820;
    --surface-3:#2A3227;
    --ink:#E8ECE2;
    --ink-soft:#AEB8A2;
    --ink-faint:#7C8672;
    --border:#333D2C;
    --accent:#6FB6AC;
    --accent-ink:#0C1512;
    --accent-wash:#1E3230;

    --hyper:#E2705F;      --hyper-wash:#3A2420;
    --copingup:#E3A64C;   --copingup-wash:#3A2F18;
    --wot:#63BD82;        --wot-wash:#1F3324;
    --copingdown:#6AA8D6; --copingdown-wash:#1E2C38;
    --hypo:#8E9DBE;       --hypo-wash:#252B3A;

    --shadow: 0 1px 2px rgba(0,0,0,0.35), 0 10px 26px -10px rgba(0,0,0,0.5);
  }

  *{box-sizing:border-box;}
  html,body{margin:0;padding:0;}
  body{
    background:var(--bg);
    color:var(--ink);
    font-family:var(--font-body);
    font-size:15px;
    line-height:1.5;
    -webkit-font-smoothing:antialiased;
  }
  ::selection{ background:var(--accent); color:var(--accent-ink); }
  button{ font-family:inherit; }
  h1,h2,h3{ text-wrap:balance; font-family:var(--font-display); margin:0; }

  /* ---------- app shell ---------- */
  .app{
    max-width:1440px;
    margin:0 auto;
    padding:28px 28px 80px;
  }
  .masthead{
    display:flex;
    align-items:flex-end;
    justify-content:space-between;
    gap:24px;
    flex-wrap:wrap;
    margin-bottom:6px;
  }
  .masthead h1{
    font-size:clamp(28px,3.4vw,40px);
    font-weight:600;
    letter-spacing:-0.01em;
  }
  .masthead .org{
    color:var(--ink-soft);
    font-size:14px;
    margin-top:6px;
  }
  .masthead .tagline{
    max-width:46ch;
    color:var(--ink-soft);
    font-size:14.5px;
    text-align:right;
  }
  .ladder-key{
    display:flex;
    gap:6px;
    margin-top:18px;
    margin-bottom:22px;
    border-radius:8px;
    overflow:hidden;
    box-shadow:var(--shadow);
  }
  .ladder-key span{
    flex:1;
    padding:7px 4px;
    text-align:center;
    font-size:11.5px;
    font-weight:600;
    letter-spacing:.02em;
    color:#fff;
  }

  /* ---------- mobile view toggle ---------- */
  .view-toggle{ display:none; gap:8px; margin-bottom:16px; }
  .view-toggle button{
    flex:1;
    padding:10px;
    border-radius:9px;
    border:1px solid var(--border);
    background:var(--surface);
    color:var(--ink-soft);
    font-weight:600;
    font-size:13.5px;
    cursor:pointer;
  }
  .view-toggle button[aria-pressed="true"]{
    background:var(--accent);
    color:var(--accent-ink);
    border-color:var(--accent);
  }

  /* ---------- layout ---------- */
  .layout{
    display:grid;
    grid-template-columns:1.35fr 1fr;
    gap:24px;
    align-items:start;
  }
  .bank, .report{ min-width:0; }
  .report{
    position:sticky;
    top:20px;
    max-height:calc(100vh - 40px);
    overflow-y:auto;
    background:var(--surface);
    border:1px solid var(--border);
    border-radius:14px;
    box-shadow:var(--shadow);
  }

  /* ---------- zone accordion (bank) ---------- */
  .zone{
    background:var(--surface);
    border:1px solid var(--border);
    border-radius:14px;
    margin-bottom:14px;
    overflow:hidden;
    box-shadow:var(--shadow);
  }
  .zone-head{
    width:100%;
    display:flex;
    align-items:center;
    gap:14px;
    padding:16px 18px;
    background:none;
    border:0;
    cursor:pointer;
    text-align:left;
    color:var(--ink);
  }
  .zone-stripe{
    width:7px;
    align-self:stretch;
    border-radius:4px;
    flex:0 0 auto;
  }
  .zone-head .txt{ flex:1; min-width:0; }
  .zone-head h2{ font-size:19px; font-weight:600; }
  .zone-head p{ margin:3px 0 0; font-size:13px; color:var(--ink-soft); font-style:italic; }
  .zone-count{
    font-family:var(--font-body);
    font-variant-numeric:tabular-nums;
    font-size:11.5px;
    font-weight:600;
    color:var(--ink-soft);
    background:var(--surface-2);
    border-radius:20px;
    padding:4px 10px;
    white-space:nowrap;
  }
  .chevron{
    transition:transform .18s ease;
    color:var(--ink-faint);
    flex:0 0 auto;
  }
  .zone[data-open="true"] .chevron{ transform:rotate(180deg); }
  .zone-body{
    display:none;
    padding:4px 18px 20px;
    border-top:1px solid var(--border);
  }
  .zone[data-open="true"] .zone-body{ display:block; }

  .col-grid{
    display:grid;
    grid-template-columns:repeat(3,1fr);
    gap:16px;
    margin-top:14px;
  }
  .col h3{
    display:flex;
    align-items:baseline;
    gap:6px;
    font-family:var(--font-body);
    font-size:11.5px;
    font-weight:700;
    text-transform:uppercase;
    letter-spacing:.06em;
    color:var(--ink-soft);
    margin-bottom:8px;
  }
  .col h3 .n{ font-weight:500; text-transform:none; letter-spacing:0; font-variant-numeric:tabular-nums; opacity:.7; }
  .ex-list{ display:flex; flex-direction:column; gap:6px; }
  .ex-row{
    display:flex;
    align-items:flex-start;
    gap:8px;
    width:100%;
    text-align:left;
    background:var(--surface-2);
    border:1px solid transparent;
    border-radius:8px;
    padding:8px 8px 8px 10px;
    color:var(--ink);
    font-size:13px;
    line-height:1.42;
    cursor:pointer;
    transition:background .12s ease, border-color .12s ease, transform .12s ease;
  }
  .ex-row:hover{ background:var(--surface-3); }
  .ex-row:active{ transform:scale(0.99); }
  .ex-row:focus-visible{ outline:2px solid var(--accent); outline-offset:1px; }
  .ex-row .arrow{
    flex:0 0 auto;
    color:var(--accent);
    font-weight:600;
    margin-left:auto;
    padding-left:4px;
    opacity:.55;
  }
  .ex-row:hover .arrow, .ex-row:focus-visible .arrow{ opacity:1; }
  .ex-row.used{ opacity:.45; }
  .ex-row.flash{ animation:flashAdd .5s ease; }
  @keyframes flashAdd{
    0%{ background:var(--accent-wash); }
    100%{ background:var(--surface-2); }
  }
  @media (prefers-reduced-motion:reduce){
    .ex-row, .chevron{ transition:none; }
    .ex-row.flash{ animation:none; }
  }

  .mine-divider{
    display:flex;
    align-items:center;
    gap:8px;
    margin:10px 0 6px;
    font-size:10.5px;
    font-weight:700;
    text-transform:uppercase;
    letter-spacing:.06em;
    color:var(--accent);
  }
  .mine-divider::after{
    content:"";
    flex:1;
    height:1px;
    background:var(--border);
  }
  .ex-row.mine{ padding-right:6px; }
  .ex-row.mine .txt{ flex:1; }
  .ex-row.mine .trash{
    flex:0 0 auto;
    background:none;
    border:0;
    color:var(--ink-faint);
    cursor:pointer;
    font-size:13px;
    padding:2px 5px;
    border-radius:5px;
    margin-left:2px;
  }
  .ex-row.mine .trash:hover{ color:var(--hyper); background:var(--hyper-wash); }

  /* ---------- report pane ---------- */
  .report-toolbar{
    position:sticky; top:0;
    background:var(--surface);
    border-bottom:1px solid var(--border);
    padding:16px 18px 14px;
    border-radius:14px 14px 0 0;
    z-index:2;
  }
  .report-toolbar h2{ font-size:19px; font-weight:600; margin-bottom:10px; }
  .student-field{
    display:flex;
    align-items:center;
    gap:8px;
    background:var(--surface-2);
    border:1px solid var(--border);
    border-radius:9px;
    padding:6px 6px 6px 12px;
    margin-bottom:10px;
  }
  .student-field label{ font-size:12px; color:var(--ink-soft); white-space:nowrap; }
  .student-field input{
    flex:1;
    border:0;
    background:none;
    font-size:14px;
    color:var(--ink);
    padding:6px 4px;
    min-width:0;
    font-family:var(--font-body);
  }
  .student-field input:focus{ outline:none; }
  .progress{
    font-size:12px;
    color:var(--ink-soft);
    margin-bottom:12px;
    font-variant-numeric:tabular-nums;
  }
  .toolbar-actions{ display:flex; gap:8px; flex-wrap:wrap; }
  .btn{
    border-radius:8px;
    border:1px solid var(--border);
    background:var(--surface);
    color:var(--ink);
    padding:8px 13px;
    font-size:13px;
    font-weight:600;
    cursor:pointer;
    display:inline-flex;
    align-items:center;
    gap:6px;
  }
  .btn:hover{ background:var(--surface-2); }
  .btn.primary{ background:var(--accent); color:var(--accent-ink); border-color:var(--accent); }
  .btn.primary:hover{ filter:brightness(1.05); }
  .btn.ghost{ background:none; }
  .btn:disabled{ opacity:.45; cursor:not-allowed; }
  .btn:focus-visible{ outline:2px solid var(--accent); outline-offset:2px; }
  .btn.small{ padding:5px 10px; font-size:12px; }

  .report-body{ padding:6px 18px 20px; }
  .rzone{ margin-top:18px; }
  .rzone:first-child{ margin-top:14px; }
  .rzone-title{
    display:flex;
    align-items:center;
    gap:8px;
    font-size:14.5px;
    font-weight:700;
    margin-bottom:8px;
  }
  .rzone-dot{ width:10px; height:10px; border-radius:3px; flex:0 0 auto; }
  .rcol{ margin-bottom:10px; }
  .rcol h4{
    font-size:11px;
    font-weight:700;
    text-transform:uppercase;
    letter-spacing:.05em;
    color:var(--ink-soft);
    margin:0 0 6px;
  }
  .rline{
    display:flex;
    align-items:flex-start;
    gap:8px;
    background:var(--surface-2);
    border-radius:7px;
    padding:6px 6px 6px 10px;
    margin-bottom:5px;
    font-size:13px;
  }
  .rline .text{ flex:1; outline:none; }
  .rline .remove{
    flex:0 0 auto;
    background:none;
    border:0;
    color:var(--ink-faint);
    cursor:pointer;
    font-size:15px;
    line-height:1;
    padding:2px 4px;
    border-radius:5px;
  }
  .rline .remove:hover{ color:var(--hyper); background:var(--hyper-wash); }
  .rempty{
    font-size:12.5px;
    color:var(--ink-faint);
    font-style:italic;
    padding:4px 2px 8px;
  }
  .add-own{
    display:flex;
    gap:6px;
    margin-top:2px;
  }
  .add-own input{
    flex:1;
    font-size:12.5px;
    border:1px dashed var(--border);
    background:none;
    border-radius:7px;
    padding:6px 9px;
    color:var(--ink);
    font-family:var(--font-body);
  }
  .add-own input:focus{ outline:none; border-color:var(--accent); }
  .add-own button{
    border:1px dashed var(--border);
    background:none;
    border-radius:7px;
    color:var(--ink-soft);
    padding:0 11px;
    cursor:pointer;
    font-size:14px;
    flex:0 0 auto;
  }
  .add-own button:hover{ border-color:var(--accent); color:var(--accent); }
  .add-own button.tidy{ font-size:11px; padding:0 9px; font-weight:600; }
  .add-hint{
    font-size:10.5px;
    color:var(--ink-faint);
    margin:3px 2px 8px;
  }

  .footnote{
    padding:14px 18px 4px;
    font-size:11.5px;
    color:var(--ink-faint);
    border-top:1px solid var(--border);
  }

  /* ---------- overlays ---------- */
  .overlay{
    position:fixed; inset:0;
    background:rgba(10,14,9,0.5);
    display:none;
    align-items:center;
    justify-content:center;
    padding:24px;
    z-index:50;
  }
  .overlay.open{ display:flex; }
  .overlay-card{
    background:var(--surface);
    border-radius:14px;
    border:1px solid var(--border);
    box-shadow:var(--shadow);
    width:min(680px,100%);
    max-height:85vh;
    display:flex;
    flex-direction:column;
    padding:20px;
  }
  .overlay-card.wide{ width:min(820px,100%); }
  .overlay-card h3{ font-size:17px; margin-bottom:4px; }
  .overlay-card p.hint{ font-size:12.5px; color:var(--ink-soft); margin:0 0 12px; }
  .overlay-card textarea{
    flex:1;
    min-height:280px;
    resize:vertical;
    border-radius:9px;
    border:1px solid var(--border);
    background:var(--surface-2);
    color:var(--ink);
    font-family:'IBM Plex Sans',monospace;
    font-size:12.5px;
    padding:12px;
    line-height:1.5;
  }
  .overlay-actions{ display:flex; justify-content:flex-end; gap:8px; margin-top:12px; flex-wrap:wrap; }
  .copy-msg{ font-size:12.5px; color:var(--wot); margin-right:auto; align-self:center; }

  .bank-manage{ overflow-y:auto; flex:1; margin:-4px -4px 0; padding:4px; }
  .bank-zone-group{ margin-bottom:14px; }
  .bank-zone-group h4{
    display:flex; align-items:center; gap:8px;
    font-size:13px; font-weight:700; margin:0 0 6px;
  }
  .bank-zone-group .dot{ width:9px; height:9px; border-radius:3px; }
  .bank-col-group{ margin-bottom:8px; }
  .bank-col-group h5{
    font-size:10.5px; text-transform:uppercase; letter-spacing:.05em;
    color:var(--ink-soft); margin:0 0 4px; font-weight:700;
  }
  .bank-phrase-row{
    display:flex; align-items:flex-start; gap:8px;
    background:var(--surface-2); border-radius:7px;
    padding:6px 6px 6px 10px; margin-bottom:4px; font-size:12.5px;
  }
  .bank-phrase-row .txt{ flex:1; }
  .bank-empty-msg{ font-size:12.5px; color:var(--ink-faint); font-style:italic; padding:8px 2px; }

  @media (max-width:900px){
    .layout{ grid-template-columns:1fr; }
    .view-toggle{ display:flex; }
    .bank[data-mobile-hide="true"], .report[data-mobile-hide="true"]{ display:none; }
    .report{ position:static; max-height:none; }
    .col-grid{ grid-template-columns:1fr; }
    .masthead .tagline{ text-align:left; }
  }

  /* ---------- print sheet: single grid, zone rows x Context/Behaviour/Interventions columns ---------- */
  .wot-print-sheet{ display:none; }
  .print-meta{
    font-family:var(--font-body);
    font-size:13px;
    color:#000;
    margin-bottom:8px;
    font-weight:600;
  }
  .print-table{
    width:100%;
    border-collapse:collapse;
    table-layout:fixed;
    background:#fff;
  }
  .print-table th, .print-table td{
    border:1px solid #333;
    padding:5px 7px;
    vertical-align:middle;
    color:#161616;
  }
  .print-table col.axis-col{ width:22px; }
  .print-table col.label-col{ width:135px; }
  .rot{
    writing-mode:vertical-rl;
    transform:rotate(180deg);
    white-space:nowrap;
    display:inline-block;
  }
  .axis-cell{
    background:linear-gradient(180deg,
      var(--map-hyper) 0%, var(--map-hyper) 12%,
      var(--map-copeup) 26%,
      var(--map-wot) 50%,
      var(--map-copedown) 74%,
      var(--map-hypo) 88%, var(--map-hypo) 100%);
    color:#fff;
    text-align:center;
    padding:6px 1px;
  }
  .axis-cell .rot{ font-weight:700; font-size:11px; letter-spacing:.06em; text-shadow:0 1px 2px rgba(0,0,0,.35); }
  .print-table th.title-cell{
    background:var(--print-navy);
    color:#fff;
    text-align:center;
    height:56px;
  }
  .title-cell .rot{ font-weight:700; font-size:10.5px; line-height:1.25; }
  .print-table th.col-head{
    background:#fff;
    text-align:center;
    height:56px;
  }
  .col-head .rot{ font-weight:700; font-size:10.5px; letter-spacing:.02em; }
  .zone-label-cell{
    vertical-align:middle;
    padding:5px 7px;
    font-size:9.5px;
    line-height:1.25;
  }
  .print-table td.zone-label-cell{ color:#fff; }
  .zone-label-cell .zn{ display:block; font-weight:700; font-size:11px; margin-bottom:2px; }
  .zone-label-cell .zd{ font-style:italic; opacity:.92; }
  .content-cell{
    vertical-align:top;
    font-size:10px;
    line-height:1.3;
    background:#F4F7FA;
  }
  .content-cell ul{ margin:0; padding-left:14px; }
  .content-cell li{ margin-bottom:2px; }
  .content-cell .empty{ color:#9AA0A6; font-style:italic; }

  /* per-zone colour glow: a soft wash of the zone's colour across its whole row, plus a
     glow highlight behind the zone name, using the same 5-hue arousal palette as the rail */
  .print-table tr[data-zone="hyper"] .zone-label-cell{ background:radial-gradient(120% 160% at 22% 20%, rgba(255,255,255,.4), rgba(255,255,255,0) 55%), var(--map-hyper); }
  .print-table tr[data-zone="hyper"] .content-cell{ background:var(--map-hyper-tint); }
  .print-table tr[data-zone="copingup"] .zone-label-cell{ background:radial-gradient(120% 160% at 22% 20%, rgba(255,255,255,.4), rgba(255,255,255,0) 55%), var(--map-copeup); }
  .print-table tr[data-zone="copingup"] .content-cell{ background:var(--map-copeup-tint); }
  .print-table tr[data-zone="wot"] .zone-label-cell{ background:radial-gradient(120% 160% at 22% 20%, rgba(255,255,255,.4), rgba(255,255,255,0) 55%), var(--map-wot); }
  .print-table tr[data-zone="wot"] .content-cell{ background:var(--map-wot-tint); }
  .print-table tr[data-zone="copingdown"] .zone-label-cell{ background:radial-gradient(120% 160% at 22% 20%, rgba(255,255,255,.4), rgba(255,255,255,0) 55%), var(--map-copedown); }
  .print-table tr[data-zone="copingdown"] .content-cell{ background:var(--map-copedown-tint); }
  .print-table tr[data-zone="hypo"] .zone-label-cell{ background:radial-gradient(120% 160% at 22% 20%, rgba(255,255,255,.4), rgba(255,255,255,0) 55%), var(--map-hypo); }
  .print-table tr[data-zone="hypo"] .content-cell{ background:var(--map-hypo-tint); }

  /* ---------- print style 2: "Regulation Map" — open bands + gradient rail ---------- */
  .print-style-toggle{ display:flex; gap:8px; align-items:center; flex-wrap:wrap; margin:0 0 10px; font-family:var(--font-body); font-size:12.5px; color:var(--ink-soft); }
  .print-style-toggle span.lbl{ margin-right:2px; }
  .print-style-toggle button{
    font-family:var(--font-body); font-size:12.5px; font-weight:600;
    padding:6px 12px; border-radius:20px; border:1px solid var(--border);
    background:var(--surface); color:var(--ink-soft); cursor:pointer;
  }
  .print-style-toggle button[aria-pressed="true"]{ background:var(--accent); border-color:var(--accent); color:var(--accent-ink); }

  .wot-print-map{ display:none; }
  .wot-print-map, .wot-print-map *{ box-sizing:border-box; }
  .wot-print-map{
    background:var(--map-paper);
    color:var(--map-ink);
    font-family:var(--font-sans-map);
    -webkit-font-smoothing:antialiased;
  }
  .wot-print-map .map-page{
    width:100%;
    margin:0;
    padding:0;
    position:relative;
  }
  .wot-print-map .map-head{
    display:flex; justify-content:space-between; align-items:flex-end; gap:24px;
    padding-bottom:4mm; border-bottom:1px solid var(--map-rule); margin-bottom:4mm;
  }
  .wot-print-map .map-head .id{ max-width:70%; }
  .wot-print-map .map-eyebrow{
    font-family:var(--font-sans-map); font-size:10.5px; font-weight:600;
    letter-spacing:.12em; text-transform:uppercase; color:var(--map-ink-faint); margin:0 0 6px;
  }
  .wot-print-map .map-name{
    font-family:var(--font-serif-map); font-weight:500; font-size:34px;
    color:var(--map-ink); margin:0; letter-spacing:-0.01em;
  }
  .wot-print-map .map-subtitle{
    font-family:var(--font-serif-map); font-style:italic; font-size:15px;
    color:var(--map-ink-soft); margin:5px 0 0;
  }
  .wot-print-map .map-meta{ text-align:right; font-size:11.5px; color:var(--map-ink-soft); line-height:1.8; white-space:nowrap; }
  .wot-print-map .map-meta b{ color:var(--map-ink); font-weight:600; }

  .wot-print-map .map-col-header{ display:grid; grid-template-columns:30px 1fr; margin-bottom:5px; }
  .wot-print-map .map-col-header .spacer{ margin-right:14px; }
  .wot-print-map .map-col-header .inner{ display:grid; grid-template-columns:225px 1fr 1fr 1fr; gap:22px; }
  .wot-print-map .map-col-header .inner > div{
    font-family:var(--font-sans-map); font-size:9.5px; font-weight:700;
    letter-spacing:.1em; text-transform:uppercase; color:var(--map-ink-faint);
  }

  .wot-print-map .map-ladder{ display:grid; grid-template-columns:30px 1fr; gap:0; }
  .wot-print-map .map-rail{
    position:relative; border-radius:5px; margin-right:14px;
    background:linear-gradient(180deg,
      var(--map-hyper) 0%, var(--map-hyper) 12%,
      var(--map-copeup) 26%,
      var(--map-wot) 50%,
      var(--map-copedown) 74%,
      var(--map-hypo) 88%, var(--map-hypo) 100%);
  }
  .wot-print-map .map-rail .map-tag{
    position:absolute; left:50%; top:50%; translate:0 50%;
    transform:translateX(-50%) rotate(180deg); writing-mode:vertical-rl;
    font-family:var(--font-sans-map); font-weight:600; font-size:10.5px;
    letter-spacing:.16em; color:rgba(255,255,255,0.88); text-transform:uppercase;
  }

  .wot-print-map .map-bands{ display:flex; flex-direction:column; }
  .wot-print-map .map-band{
    display:grid; grid-template-columns:225px 1fr 1fr 1fr; gap:22px;
    padding:2px 0; border-bottom:1px solid var(--map-rule);
  }
  .wot-print-map .map-band:last-child{ border-bottom:none; }

  .wot-print-map .map-zone{ padding-right:6px; }
  .wot-print-map .map-zn{
    font-family:var(--font-serif-map); font-weight:500; font-size:16.5px;
    color:var(--map-ink); margin:0 0 3px; line-height:1.2;
  }
  .wot-print-map .map-tagpill{
    display:inline-block; font-size:9.5px; font-weight:600; letter-spacing:.05em;
    text-transform:uppercase; padding:2px 7px; border-radius:20px; margin-bottom:5px;
  }
  .wot-print-map .map-zd{ font-size:10.5px; color:var(--map-ink-soft); line-height:1.4; font-style:italic; }

  .wot-print-map .map-col{ padding-top:2px; }
  .wot-print-map .map-col ul{ margin:0; padding:0; list-style:none; }
  .wot-print-map .map-col li{
    font-size:11px; line-height:1.35; color:var(--map-ink);
    margin-bottom:3px; padding-left:11px; position:relative;
  }
  .wot-print-map .map-col li::before{
    content:""; position:absolute; left:0; top:6px; width:4px; height:4px;
    border-radius:50%; background:var(--map-ink-faint);
  }
  .wot-print-map .map-col li.empty{ color:var(--map-ink-faint); font-style:italic; }
  .wot-print-map .map-col li.empty::before{ display:none; }

  .wot-print-map .map-band[data-zone="hyper"] .map-tagpill{ background:var(--map-hyper-tint); color:var(--map-hyper); }
  .wot-print-map .map-band[data-zone="copingup"] .map-tagpill{ background:var(--map-copeup-tint); color:var(--map-copeup); }
  .wot-print-map .map-band[data-zone="wot"] .map-tagpill{ background:var(--map-wot-tint); color:var(--map-wot); }
  .wot-print-map .map-band[data-zone="copingdown"] .map-tagpill{ background:var(--map-copedown-tint); color:var(--map-copedown); }
  .wot-print-map .map-band[data-zone="hypo"] .map-tagpill{ background:var(--map-hypo-tint); color:var(--map-hypo); }

  .wot-print-map .map-band[data-zone="hyper"] .map-col li::before{ background:var(--map-hyper); }
  .wot-print-map .map-band[data-zone="copingup"] .map-col li::before{ background:var(--map-copeup); }
  .wot-print-map .map-band[data-zone="wot"] .map-col li::before{ background:var(--map-wot); }
  .wot-print-map .map-band[data-zone="copingdown"] .map-col li::before{ background:var(--map-copedown); }
  .wot-print-map .map-band[data-zone="hypo"] .map-col li::before{ background:var(--map-hypo); }

  .wot-print-map .map-foot{
    margin-top:3mm; padding-top:2.5mm; border-top:1px solid var(--map-rule);
    display:flex; justify-content:space-between; font-size:9.5px; color:var(--map-ink-faint);
  }

  @media print{
    .masthead, .ladder-key, .view-toggle, .bank, .toolbar-actions, .add-own, .rline .remove, .footnote, .layout, .print-style-toggle, .builder-topbar{ display:none !important; }
    body{ background:#fff; color:#000; }
    .app{ padding:6px; max-width:none; }
    body[data-print-style="map"] .wot-print-sheet{ display:none !important; }
    body[data-print-style="map"] .wot-print-map{ display:block !important; }
    body:not([data-print-style="map"]) .wot-print-sheet{ display:block !important; }
    @page{ size:landscape; margin:9mm; }
  }

  /* ---------- multi-screen shell (teacher gate / student picker / builder) ---------- */
  .screen{ display:none; }
  .screen.active{ display:block; }

  .center-shell{
    min-height:100vh;
    display:flex;
    align-items:center;
    justify-content:center;
    padding:28px;
  }
  .gate-card{
    width:min(480px,100%);
    background:var(--surface);
    border:1px solid var(--border);
    border-radius:16px;
    box-shadow:var(--shadow);
    padding:32px 30px;
  }
  .gate-card h1{ font-size:24px; margin-bottom:6px; }
  .gate-card .sub{ color:var(--ink-soft); font-size:13.5px; margin-bottom:22px; }
  .gate-field{ margin-bottom:16px; }
  .gate-field label{ display:block; font-size:12px; font-weight:600; color:var(--ink-soft); margin-bottom:6px; text-transform:uppercase; letter-spacing:.04em; }
  .gate-field input{
    width:100%;
    font-size:15px;
    padding:11px 13px;
    border-radius:9px;
    border:1px solid var(--border);
    background:var(--surface-2);
    color:var(--ink);
    font-family:var(--font-body);
  }
  .gate-field input:focus{ outline:2px solid var(--accent); outline-offset:1px; }
  .gate-hint{ font-size:11.5px; color:var(--ink-faint); margin-top:16px; }
  .gate-error{ font-size:12.5px; color:var(--hyper); margin-top:8px; min-height:1.2em; }

  /* ---------- student picker screen ---------- */
  .picker-shell{ max-width:1100px; margin:0 auto; padding:32px 28px 60px; }
  .picker-header{ display:flex; align-items:flex-end; justify-content:space-between; gap:20px; flex-wrap:wrap; margin-bottom:18px; }
  .picker-header h1{ font-size:28px; }
  .picker-header .whoami{ font-size:13px; color:var(--ink-soft); text-align:right; }
  .picker-header .whoami button{
    background:none; border:0; color:var(--accent); font-weight:600; font-size:13px; cursor:pointer; padding:0; font-family:inherit;
  }
  .picker-search{
    width:100%;
    font-size:15px;
    padding:12px 16px;
    border-radius:11px;
    border:1px solid var(--border);
    background:var(--surface);
    color:var(--ink);
    margin-bottom:20px;
    box-shadow:var(--shadow);
    font-family:var(--font-body);
  }
  .picker-search:focus{ outline:2px solid var(--accent); outline-offset:1px; }
  .student-grid{
    display:grid;
    grid-template-columns:repeat(auto-fill,minmax(150px,1fr));
    gap:14px;
  }
  .student-tile{
    background:var(--surface);
    border:1px solid var(--border);
    border-radius:14px;
    padding:16px 14px;
    text-align:left;
    cursor:pointer;
    box-shadow:var(--shadow);
    transition:transform .12s ease, box-shadow .12s ease;
    display:flex;
    flex-direction:column;
    gap:6px;
  }
  .student-tile:hover{ transform:translateY(-2px); box-shadow:0 4px 16px -4px rgba(0,0,0,0.25); }
  .student-tile .initials{
    font-family:var(--font-display);
    font-size:26px;
    font-weight:700;
    color:var(--accent);
  }
  .student-tile .fullname{ font-size:12.5px; color:var(--ink-soft); line-height:1.3; }
  .student-tile .status-pill{
    align-self:flex-start;
    font-size:10px;
    font-weight:600;
    letter-spacing:.03em;
    text-transform:uppercase;
    padding:3px 8px;
    border-radius:20px;
    margin-top:2px;
  }
  .student-tile .status-pill.not-started{ background:var(--surface-2); color:var(--ink-faint); }
  .student-tile .status-pill.draft{ background:var(--copingup-wash); color:var(--copingup); }
  .student-tile .status-pill.archived{ background:var(--wot-wash); color:var(--wot); }
  .picker-empty{ color:var(--ink-faint); font-size:13.5px; font-style:italic; padding:30px 4px; }
  .picker-loading{ color:var(--ink-soft); font-size:13.5px; padding:20px 4px; }

  /* ---------- builder breadcrumb / identity strip ---------- */
  .builder-topbar{
    display:flex; align-items:center; justify-content:space-between; gap:16px; flex-wrap:wrap;
    margin-bottom:8px; font-size:13px;
  }
  .builder-topbar .crumb{ color:var(--accent); font-weight:600; cursor:pointer; background:none; border:0; padding:0; font-family:inherit; font-size:13px; }
  .builder-topbar .who{ color:var(--ink-soft); }
  .builder-topbar .who button{ background:none; border:0; color:var(--accent); font-weight:600; cursor:pointer; padding:0; font-family:inherit; font-size:13px; }
  .student-heading{ margin-bottom:4px; }
  .student-heading .name{ font-size:22px; font-weight:700; font-family:var(--font-display); }
  .student-heading .prog{ font-size:12.5px; color:var(--ink-soft); margin-left:8px; font-weight:400; font-family:var(--font-body); }

  /* ---------- save status + toasts ---------- */
  .save-status{ font-size:12px; color:var(--ink-soft); margin:2px 0 10px; min-height:1.3em; }
  .save-status.ok{ color:var(--wot); }
  .save-status.err{ color:var(--hyper); }
  .save-status.busy{ color:var(--copingup); }
  .offline-banner{
    background:var(--copingup-wash); color:var(--copingup); border:1px solid var(--copingup);
    border-radius:9px; padding:8px 12px; font-size:12.5px; margin-bottom:12px; display:none;
  }
  .offline-banner.show{ display:block; }

  /* ---------- archive dialog extras ---------- */
  .archive-fields{ display:flex; gap:10px; margin:12px 0; flex-wrap:wrap; }
  .archive-fields label{ font-size:12px; color:var(--ink-soft); display:block; margin-bottom:4px; font-weight:600; }
  .archive-fields input, .archive-fields select{
    font-size:13.5px; padding:8px 10px; border-radius:8px; border:1px solid var(--border);
    background:var(--surface-2); color:var(--ink); font-family:var(--font-body);
  }
  .archive-fields .field{ flex:1; min-width:120px; }

</style>

<div class="screen active" id="screenTeacher">
  <div class="center-shell">
    <div class="gate-card">
      <h1>Window of Tolerance Builder</h1>
      <p class="sub">Who's completing reports right now? This is used to save your reports and build your own reusable phrase bank.</p>
      <div class="gate-field">
        <label for="teacherInput">Your name</label>
        <input id="teacherInput" type="text" list="teacherList" placeholder="Start typing your name…" autocomplete="off">
        <datalist id="teacherList"></datalist>
      </div>
      <button class="btn primary" id="btnTeacherContinue" style="width:100%; justify-content:center;">Continue</button>
      <p class="gate-error" id="teacherError"></p>
      <p class="gate-hint">Not listed? Just type your name — it will be remembered on this device.</p>
    </div>
  </div>
</div>

<div class="screen" id="screenStudents">
  <div class="picker-shell">
    <div class="picker-header">
      <h1>Select a student</h1>
      <div class="whoami">Signed in as <strong id="whoamiName"></strong><br><button type="button" id="btnSwitchTeacherFromList">Switch</button></div>
    </div>
    <input type="text" class="picker-search" id="studentSearch" placeholder="Search by name or initials…" autocomplete="off">
    <div id="studentGrid" class="student-grid"></div>
    <p class="picker-loading" id="studentLoading">Loading students…</p>
    <p class="picker-empty" id="studentEmpty" style="display:none;">No students match that search.</p>
  </div>
</div>

<div class="screen" id="screenBuilder">
<div class="app">
  <div class="builder-topbar">
    <button type="button" class="crumb" id="btnBackToStudents">← All students</button>
    <span class="who">Teacher: <strong id="builderTeacherName"></strong> · <button type="button" id="btnSwitchTeacherFromBuilder">Switch</button></span>
  </div>

  <header class="masthead">
    <div>
      <div class="student-heading"><span class="name" id="studentHeadingName">Student</span><span class="prog" id="studentHeadingProgram"></span></div>
      <p class="org">Cowandilla Learning Centre — Learning and Behaviour Unit</p>
    </div>
    <p class="tagline">Click an example on the left to send it into the student's personalised plan on the right. Your own saved phrases carry over into every future report.</p>
  </header>

  <div class="offline-banner" id="offlineBanner">Showing the last locally saved version of this report — couldn't reach the shared database just now. Changes will keep working here, but won't be visible to other staff until you can save again.</div>

  <div class="ladder-key" aria-hidden="true">
    <span style="background:var(--hyper)">Hyperarousal</span>
    <span style="background:var(--copingup)">Coping — rising</span>
    <span style="background:var(--wot)">Window of Tolerance</span>
    <span style="background:var(--copingdown)">Coping — falling</span>
    <span style="background:var(--hypo)">Hypoarousal</span>
  </div>

  <div class="view-toggle">
    <button type="button" id="tabBank" aria-pressed="true">Examples</button>
    <button type="button" id="tabReport" aria-pressed="false">Report</button>
  </div>

  <div class="layout">
    <main class="bank" id="bankPane"></main>

    <aside class="report" id="reportPane">
      <div class="report-toolbar">
        <h2>Your report</h2>
        <div class="save-status" id="saveStatus"></div>
        <div class="print-style-toggle" id="printStyleToggle">
          <span class="lbl">Print layout:</span>
          <button type="button" id="btnStyleGrid" aria-pressed="true">Grid template</button>
          <button type="button" id="btnStyleMap" aria-pressed="false">Regulation Map</button>
        </div>
        <div class="toolbar-actions">
          <button class="btn primary" id="btnSave">Save</button>
          <button class="btn" id="btnExport">Export text</button>
          <button class="btn" id="btnPrint">Print / save PDF</button>
          <button class="btn" id="btnDownload">Download report</button>
          <button class="btn ghost" id="btnManageBank">My phrase bank</button>
          <button class="btn ghost" id="btnArchive">Archive to Document Archive</button>
          <button class="btn ghost" id="btnClear">Clear this report</button>
        </div>
      </div>
      <div class="report-body" id="reportBody"></div>
      <p class="footnote">Read alongside this student's individual behaviour support plan and any safety plan already in place.</p>
    </aside>
  </div>

  <div class="wot-print-sheet" id="printSheet">
    <div class="print-meta" id="printMeta">Student:</div>
    <table class="print-table">
      <colgroup>
        <col class="axis-col"><col class="label-col"><col><col><col>
      </colgroup>
      <tbody id="printTableBody"></tbody>
    </table>
  </div>

  <div class="wot-print-map" id="printMap">
    <div class="map-page">
      <div class="map-head">
        <div class="id">
          <p class="map-eyebrow">Personalised regulation profile</p>
          <h1 class="map-name" id="mapName">[Student name]</h1>
          <p class="map-subtitle" id="mapSubtitle">A map of this student's window of tolerance, and what helps at each stage</p>
        </div>
        <div class="map-meta">
          Cowandilla Learning Centre — Learning and Behaviour Unit<br>
          Prepared by: <b id="mapPreparedBy">[staff name]</b> &nbsp;·&nbsp; Reviewed: <b id="mapReviewed">[term, year]</b>
        </div>
      </div>

      <div class="map-col-header">
        <div class="spacer"></div>
        <div class="inner">
          <div></div>
          <div>Context</div>
          <div>Behaviour descriptors</div>
          <div>What helps</div>
        </div>
      </div>
      <div class="map-ladder">
        <div class="map-rail"><span class="map-tag">Arousal</span></div>
        <div class="map-bands" id="mapBands"></div>
      </div>

      <div class="map-foot">
        <span>Read alongside this student's individual behaviour support plan and any safety plan already in place.</span>
        <span>Window of Tolerance Builder — Regulation Map</span>
      </div>
    </div>
  </div>
</div>

<div class="overlay" id="exportOverlay">
  <div class="overlay-card">
    <h3>Export report as text</h3>
    <p class="hint">Save it as a file, or copy it into Word, an email, or your case-notes system.</p>
    <textarea id="exportText" readonly></textarea>
    <div class="overlay-actions">
      <span class="copy-msg" id="copyMsg"></span>
      <button class="btn" id="btnCloseExport">Close</button>
      <button class="btn" id="btnDoCopy">Copy to clipboard</button>
      <button class="btn primary" id="btnDoSave" style="display:none;">Save as file</button>
    </div>
  </div>
</div>

<div class="overlay" id="bankOverlay">
  <div class="overlay-card wide">
    <h3>My phrase bank</h3>
    <p class="hint">Anything you've typed with "Add your own…" is saved here against your name and shows up in the example lists on every future report, for every student. Remove one for good with the trash icon — that won't affect any report it's already been added to.</p>
    <div class="bank-manage" id="bankManageBody"></div>
    <div class="overlay-actions">
      <button class="btn" id="btnCloseBank">Close</button>
    </div>
  </div>
</div>

<div class="overlay" id="archiveOverlay">
  <div class="overlay-card">
    <h3>Archive to Document Archive</h3>
    <p class="hint">This files the current report as a completed document in the shared Document Archive, alongside PDPs, BAPs and safety plans. The report stays editable here afterwards — archiving again files an updated copy.</p>
    <div class="archive-fields">
      <div class="field">
        <label for="archiveTerm">Term</label>
        <input type="text" id="archiveTerm" placeholder="e.g. Term 3">
      </div>
      <div class="field">
        <label for="archiveYear">Year</label>
        <input type="text" id="archiveYear" placeholder="e.g. 2026">
      </div>
    </div>
    <p class="gate-error" id="archiveError"></p>
    <div class="overlay-actions">
      <span class="copy-msg" id="archiveMsg"></span>
      <button class="btn" id="btnCloseArchive">Cancel</button>
      <button class="btn primary" id="btnDoArchive">File to Document Archive</button>
    </div>
  </div>
</div>
</div>


<script>
(function(){
  "use strict";

  // ---------------- Supabase config ----------------
  var SUPABASE_URL = "https://lvzaebjrxrgguypqvdcq.supabase.co";
  var SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imx2emFlYmpyeHJnZ3V5cHF2ZGNxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQwMzQ1NjEsImV4cCI6MjA3OTYxMDU2MX0._FRXmevMwE-ij5phtY3DAq-olBuTsfGrr6xRNKHqE9I";
  // TODO: confirm this matches the bucket name already used by the Document Archive
  // tool for PDPs / BAPs / safety plans, then update this constant if it differs.
  var ARCHIVE_BUCKET = "document-archive";

  var sb = null;
  try{
    if(window.supabase && typeof window.supabase.createClient === "function"){
      sb = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
    }
  }catch(e){ sb = null; }

  var ZONES = [
      {
        id:"hyper", label:"Mobilisation — Hyperarousal", color:"hyper",
        mapName:"Mobilisation", mapTag:"Hyperarousal",
        desc:"Too much arousal to integrate. Sympathetic nervous system activation (fight / flight / freeze) — the student cannot process what is happening, who is around them, or what staff are saying.",
        short:"Too much arousal to integrate. Activation of the sympathetic nervous system (fight / flight / freeze).",
        cols:{
          context:[
            "Non-preferred instruction given during a transition between tasks",
            "Recess, lunch play or yard time",
            "A relief teacher (TRT) is in the room",
            "Being told to stop a preferred activity (basketball, iPad)",
            "A peer they've had a recent negative interaction with is nearby",
            "Loud, crowded or unpredictable spaces (hallway, assembly, canteen line)",
            "First thing after arriving at school, before they've had a chance to settle",
            "Sudden, unexpected touch, or someone entering their personal space quickly",
            "Being corrected or disciplined in front of peers",
            "A high-stakes or timed assessment task",
            "A sudden loud noise — alarm, siren, bell, shout",
            "Overhearing an adult talking about them",
            "The crowded rush of end-of-day dismissal",
            "A specific sensory trigger once identified (a smell, texture, taste)"
          ],
          behaviour:[
            "Instant reaction — shouting or swearing that escalates in volume and intensity",
            "Making verbal threats of violence",
            "Throwing or slamming objects",
            "Tense, agitated body; pacing; difficulty finding stillness",
            "Attempting to kick, hit or grab a staff member or peer",
            "Running from the space or refusing to enter it",
            "Wide or darting eyes, scanning the room as if for an exit",
            "Voice pitch rises sharply; speech speeds up or becomes fragmented",
            "A sudden silence that tips into an explosive reaction without warning",
            "Gripping or clenching objects, furniture, or their own body",
            "Repeating the same phrase or demand with rising volume",
            "Trying to leave the classroom or school grounds without permission"
          ],
          interventions:[
            "Maintain a safe distance and a calm, neutral tone",
            "Remove the audience / onlooking peers as a safety measure",
            "Give one firm, simple direction for safety (“Stop”)",
            "Offer the student's pre-planned escape route or quiet space",
            "Remove hazardous objects if it's safe to do so",
            "Phone home and inform leadership per the safety plan",
            "Use short, concrete sentences — avoid reasoning or negotiating in this state",
            "Slow and lower your own voice and movements; avoid sudden gestures",
            "Stand at an angle rather than square-on; ease off direct eye contact if it escalates them",
            "Use the student's name calmly and repeat one simple instruction only",
            "Pre-agree a signal they can give staff before reaching this point",
            "Debrief later, once fully back in the window — never during or straight after"
          ]
        }
      },
      {
        id:"copingup", label:"Coping Mechanisms — moving toward Hyperarousal", color:"copingup",
        mapName:"Coping — rising", mapTag:"Early warning",
        desc:"Early warning signs as arousal climbs toward this student's threshold. Reduced capacity to learn and interact, but co-regulation and choice can often still land.",
        short:"Reduced capacity to learn and interact.",
        cols:{
          context:[
            "Asked to pack away or stop a preferred activity",
            "Losing a competitive game (basketball, soccer, board game)",
            "A change in routine or an unfamiliar staff member",
            "Being asked to wait, or to accept a teacher decision",
            "Using a device for something not school-appropriate",
            "A peer copying or antagonising them from a distance",
            "Anticipating a non-preferred activity later in the day",
            "Ambiguous or open-ended instructions (“just get started”)",
            "Sitting near a peer who is fidgeting or off-task",
            "Being partly corrected — told they're “nearly right” or “not quite”",
            "Waiting in a queue or for their turn",
            "A task that's slightly too hard without enough scaffolding"
          ],
          behaviour:[
            "Short, terse answers; refusing instructions",
            "Swearing or name-calling that hasn't yet peaked in intensity",
            "Muttering under their breath",
            "Snatching objects or touching things that aren't theirs",
            "Saying “you're not the boss of me” or similar",
            "Antagonising peers who are also dysregulated",
            "Increased fidgeting, foot-tapping, or seeking sensory input (chewing, clicking a pen)",
            "Testing limits with small rule-breaks, short of full defiance",
            "Asking the same question repeatedly for reassurance",
            "Sarcastic or pointed comments aimed at staff or peers",
            "Watching staff closely to gauge their reaction",
            "Sudden interest in leaving the room “for a reason” (toilet, drink)"
          ],
          interventions:[
            "Offer a genuine choice, or an if/then (“when you finish X, then Y”)",
            "Co-regulate with a quiet, preferred activity (drawing, shooting hoops)",
            "Name what you're noticing (“I can see you're a bit outside your window”)",
            "Give a little time and space to process the instruction",
            "Negotiate a re-entry plan before things escalate further",
            "Offer a check-in call with a trusted adult or family member",
            "Pre-empt with a heads-up about what's coming next, and why",
            "Break the task into two smaller, clearly-bounded steps",
            "Use humour or a light aside to defuse, if this student responds well to it",
            "Offer movement disguised as a job (hand out books, deliver a message)",
            "Validate the feeling before addressing the behaviour (“makes sense you're annoyed”)",
            "Check in privately rather than in front of the group"
          ]
        }
      },
      {
        id:"wot", label:"Window of Tolerance", color:"wot",
        mapName:"Window of Tolerance", mapTag:"Regulated",
        desc:"The student feels safe enough to learn, connect with others, reflect, and make good decisions. Protect and expand this zone through proactive support.",
        short:"Student feels safe to learn and interact with others.",
        cols:{
          context:[
            "Working 1:1 or in a small group on a well-scaffolded task",
            "Morning check-in or morning circle",
            "Drawing, colouring or a preferred activity with a trusted adult",
            "A structured game with clear, simple rules",
            "Helping a peer, or being given a small job or responsibility",
            "Predictable routine with visual and verbal transition warnings",
            "Physical activity or sport where they feel competent",
            "Being asked their opinion, or given a genuine choice",
            "A well-rehearsed, predictable part of the daily routine",
            "One-on-one conversation about a topic they know a lot about",
            "Contributing to a class job or roster",
            "Arriving to a calm, organised classroom space"
          ],
          behaviour:[
            "Relaxed body and facial expression; smiling",
            "Uses kind words and a calm, friendly tone",
            "Follows instructions with minimal reminders",
            "Accepts teacher decisions without protest",
            "Shares ideas, asks for help, or names their own needs",
            "Engages with and starts learning tasks independently",
            "Initiates conversation or play with peers appropriately",
            "Uses humour that lands well and includes others",
            "Tolerates minor frustration without needing adult support",
            "Offers to help a peer or staff member unprompted",
            "Can name their own emotional state accurately",
            "Transitions between activities without a reminder"
          ],
          interventions:[
            "Greet warmly and check in on arrival",
            "Give specific, immediate positive feedback",
            "Build in movement or sensory breaks proactively",
            "Keep routines, expectations and seating options predictable",
            "Show genuine interest in their activities outside school",
            "Reinforce character strengths in the moment (“that's persistence”)",
            "Bank strengths-based observations to reference later in a harder moment",
            "Rotate a class job or responsibility to this student regularly",
            "With their consent, use their own regulation strategies as a model for peers",
            "Keep a visual schedule visible and refer to it together",
            "Briefly debrief a recent success, in their own words",
            "Protect this state by not over-testing it — avoid stacking demands"
          ]
        }
      },
      {
        id:"copingdown", label:"Coping Mechanisms — moving toward Hypoarousal", color:"copingdown",
        mapName:"Coping — falling", mapTag:"Early withdrawal",
        desc:"Early signs of withdrawal as arousal drops below this student's threshold. Reduced capacity to learn and interact; the student is beginning to disengage rather than escalate.",
        short:"Reduced capacity to learn and interact.",
        cols:{
          context:[
            "Negative feedback or teasing from peers",
            "Losing, or being caught out, in a game",
            "A task or piece of work being damaged or interrupted",
            "Feeling tired, unwell, hungry or in pain",
            "A quiet, unstructured moment after a big activity",
            "Being asked a question they can't answer",
            "End of a long or demanding block of learning",
            "Being left out of a game or group by peers",
            "A reminder of a past difficult experience",
            "Feeling embarrassed, or having made a visible mistake",
            "Extended quiet or unstructured time with no clear task",
            "A change of adult they feel safest with"
          ],
          behaviour:[
            "Head down, shoulders slumped, minimal eye contact",
            "Going quiet; short or no verbal response",
            "Negative self-talk (“I'm dumb”, “I hate myself”)",
            "Retreating to a desk, corner, or facing the wall",
            "Hiding under a table or behind furniture",
            "Repeating a request for reassurance (“I want my mum”)",
            "Voice drops to barely audible; only short yes/no answers",
            "Stops making requests altogether, even for things they need",
            "Physically curls inward — arms crossed tightly, knees to chest",
            "Stares at one spot without engaging with surroundings",
            "Apologises repeatedly for small or imagined mistakes",
            "Loses interest in an activity they usually enjoy"
          ],
          interventions:[
            "Give time and space, and say clearly you're available when ready",
            "Get curious rather than corrective (“I'm noticing your shoulders are low—help me understand?”)",
            "Offer food, water, or a softer space (couch, hammock)",
            "Lower your own voice and tone to match theirs",
            "Offer a short break with a clear return time",
            "Avoid demanding an immediate verbal response",
            "Sit alongside rather than opposite; ease off direct eye contact",
            "Use fewer words, longer pauses, and a slower pace",
            "Offer a favoured object, fidget, or comfort item",
            "Keep instructions optional (“when you're ready” rather than “now”)",
            "Quietly check basic needs — temperature, hunger, tiredness, pain",
            "Stay nearby without requiring interaction — presence over prompts"
          ]
        }
      },
      {
        id:"hypo", label:"Immobilisation — Hypoarousal", color:"hypo",
        mapName:"Immobilisation", mapTag:"Hypoarousal",
        desc:"Too little arousal to integrate. Dorsal vagal activation (submit / collapse / shutdown) — the student may appear flat, numb or empty, and unable to respond.",
        short:"Too little arousal to integrate. Activation of the dorsal vagal system (shutdown / collapse).",
        cols:{
          context:[
            "A long stretch of high demand without a break",
            "Straight after a distressing incident",
            "Sustained noise or sensory overload",
            "Extreme tiredness, hunger, or being unwell",
            "Feeling completely unheard or unseen",
            "Being highly restricted or held for safety",
            "Well past this student's own regulation threshold with no earlier intervention",
            "A significant unmet sleep, food or medical need",
            "Repeated failure or correction across a session",
            "A space that feels unsafe or overwhelming to this student specifically",
            "Being talked about, rather than to, in their presence",
            "The recovery period straight after a hyperarousal episode"
          ],
          behaviour:[
            "Blank, vacant stare; fixed or pinpoint pupils",
            "Collapsed or slumped posture; loose muscle tone",
            "No verbal response; appears not to hear you",
            "Slowed movement, slowed breathing or heart rate",
            "Appears flat, numb, empty or “checked out”",
            "No visible distress — easy to mistake for calm",
            "Breathing becomes very shallow or barely visible",
            "Noticeable change in skin colour or temperature (pale, cold to touch)",
            "Eyes open but unfocused; doesn't track movement or speech",
            "Doesn't initiate movement even when physically able to",
            "May not register pain, cold or discomfort as expected",
            "Comes across as unusually compliant — easy to overlook as regulated"
          ],
          interventions:[
            "Short, sharp present-moment prompts (name something green, describe 3 things you can see)",
            "Offer gentle physical grounding (weighted blanket, textured cushion)",
            "Use a soft, warm tone without demanding a response",
            "Allow recovery time before expecting engagement",
            "Reduce sensory input (dim lights, lower noise, fewer people)",
            "Check physical safety and comfort first (seated, warm, safe)",
            "Prioritise physiological needs first — warmth, food, water, comfort",
            "Use very brief, simple, single-step prompts only",
            "Reintroduce sensory input gradually — light touch, gentle movement — not all at once",
            "Avoid crowding: one familiar adult, quiet space, reduced stimulation",
            "Note the duration and pattern to inform the next review of this plan",
            "Resume demands only once clear signs of re-engagement return"
          ]
        }
      }
    ];

  var COL_LABELS = { context:"Context", behaviour:"Behaviour descriptors", interventions:"Interventions" };
  var COLS = ["context","behaviour","interventions"];
  var TEACHER_KEY = "wot-builder-teacher-v2";
  var CACHE_PREFIX = "wot-builder-cache-v2-";

  function blankItems(){
    var obj = {};
    ZONES.forEach(function(z){ obj[z.id] = { context:[], behaviour:[], interventions:[] }; });
    return obj;
  }

  // ---------------- app-level state ----------------
  var teacherName = null;
  var currentStudent = null;
  var currentReportId = null;
  var currentReportStatus = "draft";
  var reportsIndex = {};
  var studentsCache = [];
  var lastSavedSnapshot = null;

  var state = { items: blankItems() };

  var bank = {};
  ZONES.forEach(function(z){ bank[z.id] = { context:[], behaviour:[], interventions:[] }; });

  function escapeHtml(s){
    return String(s).replace(/[&<>"]/g, function(c){
      return { "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;" }[c];
    });
  }
  function flash(el){
    el.classList.remove("flash");
    void el.offsetWidth;
    el.classList.add("flash");
  }
  function tidyWording(raw){
    var t = raw.replace(/\s+/g," ").trim();
    if(!t) return t;
    t = t.replace(/[\s.]+$/,"");
    t = t.charAt(0).toUpperCase() + t.slice(1);
    return t;
  }
  function formatDate(iso){
    if(!iso) return "";
    try{
      var d = new Date(iso);
      return d.toLocaleDateString(undefined, { day:"numeric", month:"short" });
    }catch(e){ return ""; }
  }

  // ================= SCREENS =================
  function showScreen(id){
    var all = document.querySelectorAll(".screen");
    for(var i=0;i<all.length;i++){ all[i].classList.remove("active"); }
    document.getElementById(id).classList.add("active");
  }

  // ================= TEACHER GATE =================
  var teacherInput = document.getElementById("teacherInput");
  var teacherListEl = document.getElementById("teacherList");
  var teacherError = document.getElementById("teacherError");

  function loadStaffOptions(){
    if(!sb) return;
    sb.from("staff_directory").select("name").order("name").then(function(res){
      if(res.error || !res.data) return;
      teacherListEl.innerHTML = "";
      res.data.forEach(function(row){
        if(!row.name) return;
        var opt = document.createElement("option");
        opt.value = row.name;
        teacherListEl.appendChild(opt);
      });
    }).catch(function(){ /* free-text entry still works without this */ });
  }

  function getSavedTeacher(){
    try{ return localStorage.getItem(TEACHER_KEY) || null; }catch(e){ return null; }
  }
  function setTeacher(name){
    teacherName = name;
    try{ localStorage.setItem(TEACHER_KEY, name); }catch(e){ /* ignore */ }
    document.getElementById("whoamiName").textContent = name;
    document.getElementById("builderTeacherName").textContent = name;
  }

  document.getElementById("btnTeacherContinue").addEventListener("click", function(){
    var v = teacherInput.value.trim();
    if(!v){ teacherError.textContent = "Please enter your name to continue."; return; }
    teacherError.textContent = "";
    setTeacher(v);
    enterStudentPicker();
  });
  teacherInput.addEventListener("keydown", function(e){
    if(e.key === "Enter"){ e.preventDefault(); document.getElementById("btnTeacherContinue").click(); }
  });

  function switchTeacher(){
    try{ localStorage.removeItem(TEACHER_KEY); }catch(e){ /* ignore */ }
    teacherName = null;
    teacherInput.value = "";
    teacherError.textContent = "";
    showScreen("screenTeacher");
  }
  document.getElementById("btnSwitchTeacherFromList").addEventListener("click", switchTeacher);
  document.getElementById("btnSwitchTeacherFromBuilder").addEventListener("click", function(){
    if(hasUnsavedChanges() && !window.confirm("You have changes that haven't been saved yet. Switch teacher anyway?")) return;
    switchTeacher();
  });

  // ================= STUDENT PICKER =================
  var studentGrid = document.getElementById("studentGrid");
  var studentSearch = document.getElementById("studentSearch");
  var studentLoading = document.getElementById("studentLoading");
  var studentEmpty = document.getElementById("studentEmpty");

  function statusForStudent(studentId){
    var r = reportsIndex[studentId];
    if(!r) return { cls:"not-started", label:"Not started" };
    if(r.status === "archived") return { cls:"archived", label:"Archived · " + formatDate(r.updated_at) };
    return { cls:"draft", label:"Draft · " + formatDate(r.updated_at) };
  }

  function renderStudentGrid(){
    var q = studentSearch.value.trim().toLowerCase();
    var filtered = studentsCache.filter(function(s){
      if(!q) return true;
      return (s.full_name||"").toLowerCase().indexOf(q) !== -1 || (s.initials||"").toLowerCase().indexOf(q) !== -1;
    });
    studentGrid.innerHTML = "";
    studentEmpty.style.display = filtered.length ? "none" : "block";
    filtered.forEach(function(s){
      var tile = document.createElement("button");
      tile.type = "button";
      tile.className = "student-tile";
      var st = statusForStudent(s.id);
      tile.innerHTML =
        '<span class="initials">'+escapeHtml(s.initials||"?")+'</span>' +
        '<span class="fullname">'+escapeHtml(s.full_name||"")+'</span>' +
        '<span class="status-pill '+st.cls+'">'+escapeHtml(st.label)+'</span>';
      tile.addEventListener("click", function(){ openStudent(s); });
      studentGrid.appendChild(tile);
    });
  }
  studentSearch.addEventListener("input", renderStudentGrid);

  function enterStudentPicker(){
    document.getElementById("whoamiName").textContent = teacherName;
    showScreen("screenStudents");
    loadStudentsAndReports();
  }

  function loadStudentsAndReports(){
    if(!sb){
      studentLoading.style.display = "block";
      studentLoading.textContent = "Can't reach the student list right now — check your connection and reload the page.";
      return;
    }
    studentLoading.style.display = "block";
    studentLoading.textContent = "Loading students…";
    Promise.all([
      sb.from("student_directory").select("*").order("full_name"),
      sb.from("wot_builder_reports").select("id,student_register_id,status,updated_at")
    ]).then(function(results){
      var studentsRes = results[0], reportsRes = results[1];
      if(studentsRes.error){
        studentLoading.textContent = "Couldn't load the student list. Check your connection and try reloading.";
        return;
      }
      studentsCache = studentsRes.data || [];
      reportsIndex = {};
      (reportsRes.data || []).forEach(function(r){
        var existing = reportsIndex[r.student_register_id];
        if(!existing || new Date(r.updated_at) > new Date(existing.updated_at)){
          reportsIndex[r.student_register_id] = r;
        }
      });
      studentLoading.style.display = "none";
      renderStudentGrid();
    }).catch(function(){
      studentLoading.textContent = "Couldn't load the student list. Check your connection and try reloading.";
    });
  }

  document.getElementById("btnBackToStudents").addEventListener("click", function(){
    if(hasUnsavedChanges() && !window.confirm("You have changes that haven't been saved yet. Leave without saving?")) return;
    showScreen("screenStudents");
    loadStudentsAndReports();
  });

  // ================= OPEN / LOAD A STUDENT'S REPORT =================
  function hasUnsavedChanges(){
    if(lastSavedSnapshot === null) return false;
    try{ return JSON.stringify(state.items) !== lastSavedSnapshot; }catch(e){ return false; }
  }

  function openStudent(s){
    currentStudent = s;
    currentReportId = null;
    currentReportStatus = "draft";
    state.items = blankItems();
    lastSavedSnapshot = null;

    document.getElementById("studentHeadingName").textContent = s.full_name + " (" + s.initials + ")";
    document.getElementById("studentHeadingProgram").textContent = s.program ? ("· " + s.program) : "";
    document.getElementById("offlineBanner").classList.remove("show");
    setSaveStatus("", "");

    showScreen("screenBuilder");
    loadBankForTeacher();
    loadReportForCurrentStudent();
  }

  function mergeItems(data){
    var obj = blankItems();
    if(data && typeof data === "object"){
      ZONES.forEach(function(z){
        if(data[z.id]){
          COLS.forEach(function(c){
            if(Array.isArray(data[z.id][c])) obj[z.id][c] = data[z.id][c];
          });
        }
      });
    }
    return obj;
  }

  function cacheKeyForCurrentStudent(){ return CACHE_PREFIX + currentStudent.id; }
  function cacheReportLocally(){
    try{
      localStorage.setItem(cacheKeyForCurrentStudent(), JSON.stringify({ items: state.items, printStyle: printStyle, savedAt: Date.now() }));
    }catch(e){ /* ignore */ }
  }
  function loadFromLocalCache(showBanner){
    try{
      var raw = localStorage.getItem(cacheKeyForCurrentStudent());
      if(raw){
        var parsed = JSON.parse(raw);
        state.items = mergeItems(parsed.items);
        if(parsed.printStyle === "map" || parsed.printStyle === "grid"){ printStyle = parsed.printStyle; applyPrintStyle(); }
        if(showBanner) document.getElementById("offlineBanner").classList.add("show");
      }
    }catch(e){ /* ignore */ }
  }

  function loadReportForCurrentStudent(){
    if(!sb){
      loadFromLocalCache(true);
      lastSavedSnapshot = JSON.stringify(state.items);
      renderBank(); renderReport();
      return;
    }
    sb.from("wot_builder_reports")
      .select("*")
      .eq("student_register_id", currentStudent.id)
      .order("updated_at", { ascending:false })
      .limit(1)
      .then(function(res){
        if(res.error){
          loadFromLocalCache(true);
        } else {
          var rows = res.data || [];
          if(rows.length){
            var row = rows[0];
            currentReportId = row.id;
            currentReportStatus = row.status || "draft";
            state.items = mergeItems(row.data);
            if(row.print_style === "map" || row.print_style === "grid") printStyle = row.print_style;
            applyPrintStyle();
            cacheReportLocally();
          } else {
            loadFromLocalCache(false);
          }
        }
        lastSavedSnapshot = JSON.stringify(state.items);
        renderBank(); renderReport();
      })
      .catch(function(){
        loadFromLocalCache(true);
        lastSavedSnapshot = JSON.stringify(state.items);
        renderBank(); renderReport();
      });
  }

  // ================= SAVE =================
  function setSaveStatus(text, cls){
    var el = document.getElementById("saveStatus");
    el.textContent = text;
    el.className = "save-status" + (cls ? " " + cls : "");
  }

  function saveReport(onDone){
    cacheReportLocally();
    if(!sb){
      setSaveStatus("Saved locally on this device only — couldn't reach the shared database.", "err");
      if(onDone) onDone(false);
      return;
    }
    setSaveStatus("Saving…", "busy");
    var nowIso = new Date().toISOString();
    var payload = {
      student_register_id: currentStudent.id,
      student_initials: currentStudent.initials,
      student_name: currentStudent.full_name,
      data: state.items,
      print_style: printStyle,
      updated_by: teacherName,
      updated_at: nowIso
    };
    var query;
    if(currentReportId){
      query = sb.from("wot_builder_reports").update(payload).eq("id", currentReportId).select().single();
    } else {
      payload.created_by = teacherName;
      payload.status = "draft";
      query = sb.from("wot_builder_reports").insert(payload).select().single();
    }
    query.then(function(res){
      if(res.error){
        setSaveStatus("Couldn't save — check your connection and try again.", "err");
        if(onDone) onDone(false);
        return;
      }
      currentReportId = res.data.id;
      currentReportStatus = res.data.status;
      lastSavedSnapshot = JSON.stringify(state.items);
      reportsIndex[currentStudent.id] = { id: res.data.id, student_register_id: currentStudent.id, status: res.data.status, updated_at: res.data.updated_at };
      setSaveStatus("Saved just now.", "ok");
      if(onDone) onDone(true);
    }).catch(function(){
      setSaveStatus("Couldn't save — check your connection and try again.", "err");
      if(onDone) onDone(false);
    });
  }
  document.getElementById("btnSave").addEventListener("click", function(){ saveReport(); });

  document.getElementById("btnClear").addEventListener("click", function(){
    if(!window.confirm("Clear every line from " + currentStudent.full_name + "'s report? This can't be undone unless you've saved a previous version.")) return;
    state.items = blankItems();
    renderReport();
    saveReport();
  });

  // ================= PHRASE BANK (Supabase, per teacher) =================
  function loadBankForTeacher(){
    ZONES.forEach(function(z){ bank[z.id] = { context:[], behaviour:[], interventions:[] }; });
    if(!sb || !teacherName){ renderBank(); return; }
    sb.from("wot_phrase_bank").select("*").eq("teacher_name", teacherName).order("created_at").then(function(res){
      if(!res.error && res.data){
        res.data.forEach(function(row){
          if(bank[row.zone_id] && bank[row.zone_id][row.column_key]){
            bank[row.zone_id][row.column_key].push({ id: row.id, text: row.phrase });
          }
        });
      }
      renderBank();
    }).catch(function(){ renderBank(); });
  }

  function addToPersonalBank(zoneId, colKey, text){
    var norm = text.trim().toLowerCase();
    var exists = bank[zoneId][colKey].some(function(p){ return p.text.trim().toLowerCase() === norm; });
    if(exists) return;
    var localId = "local-" + Math.random().toString(36).slice(2);
    bank[zoneId][colKey].push({ id: localId, text: text.trim() });
    if(sb && teacherName){
      sb.from("wot_phrase_bank").insert({ teacher_name: teacherName, zone_id: zoneId, column_key: colKey, phrase: text.trim() })
        .select().single().then(function(res){
          if(!res.error && res.data){
            var item = null;
            for(var i=0;i<bank[zoneId][colKey].length;i++){ if(bank[zoneId][colKey][i].id === localId) item = bank[zoneId][colKey][i]; }
            if(item) item.id = res.data.id;
          }
        }).catch(function(){ /* stays local-only for this session */ });
    }
  }
  function removeFromPersonalBank(zoneId, colKey, id){
    bank[zoneId][colKey] = bank[zoneId][colKey].filter(function(p){ return p.id !== id; });
    if(sb && typeof id === "string" && id.indexOf("local-") !== 0){
      sb.from("wot_phrase_bank").delete().eq("id", id).then(function(){}).catch(function(){});
    }
  }
  function bankPhraseCount(){
    var n = 0;
    ZONES.forEach(function(z){ COLS.forEach(function(c){ n += bank[z.id][c].length; }); });
    return n;
  }

  // ================= downloads capability (optional Claude-artifact feature) =================
  var downloadsNS = null;
  (function(){
    try{
      if(window.claude && typeof window.claude.use === "function"){
        window.claude.use("downloads").then(function(ns){
          downloadsNS = ns;
          var btn = document.getElementById("btnDoSave");
          if(btn) btn.style.display = ns ? "inline-flex" : "none";
        }).catch(function(){ /* leave hidden */ });
      }
    }catch(e){ /* leave hidden */ }
  })();

  // ================= BANK RENDERING =================
  var bankPane = document.getElementById("bankPane");
  var openZoneId = ZONES[0].id;

  function totalExamples(){
    var n = 0;
    ZONES.forEach(function(z){ COLS.forEach(function(c){ n += z.cols[c].length; }); });
    return n;
  }
  function usedCount(){
    var n = 0;
    ZONES.forEach(function(z){ COLS.forEach(function(c){ n += state.items[z.id][c].length; }); });
    return n;
  }

  function renderBank(){
    bankPane.innerHTML = "";
    ZONES.forEach(function(zone){
      var isOpen = zone.id === openZoneId;
      var wrap = document.createElement("section");
      wrap.className = "zone";
      wrap.dataset.open = isOpen ? "true" : "false";

      var head = document.createElement("button");
      head.type = "button";
      head.className = "zone-head";
      head.setAttribute("aria-expanded", isOpen ? "true" : "false");
      head.innerHTML =
        '<span class="zone-stripe" style="background:var(--'+zone.color+')"></span>' +
        '<span class="txt"><h2>'+zone.label+'</h2><p>'+zone.desc+'</p></span>' +
        '<span class="zone-count">'+countInZone(zone)+'</span>' +
        '<svg class="chevron" width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M6 9l6 6 6-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
      head.addEventListener("click", function(){
        openZoneId = (openZoneId === zone.id) ? null : zone.id;
        renderBank();
      });
      wrap.appendChild(head);

      var body = document.createElement("div");
      body.className = "zone-body";
      var grid = document.createElement("div");
      grid.className = "col-grid";
      COLS.forEach(function(colKey){
        grid.appendChild(renderBankColumn(zone, colKey));
      });
      body.appendChild(grid);
      wrap.appendChild(body);

      bankPane.appendChild(wrap);
    });
  }

  function countInZone(zone){
    var used = 0, total = 0;
    COLS.forEach(function(c){
      total += zone.cols[c].length + bank[zone.id][c].length;
      used += state.items[zone.id][c].length;
    });
    return used + " of " + total + " used";
  }

  function renderBankColumn(zone, colKey){
    var col = document.createElement("div");
    col.className = "col";
    var h3 = document.createElement("h3");
    h3.innerHTML = escapeHtml(COL_LABELS[colKey]) + ' <span class="n">' + zone.cols[colKey].length + "</span>";
    col.appendChild(h3);

    var list = document.createElement("div");
    list.className = "ex-list";
    zone.cols[colKey].forEach(function(text){
      list.appendChild(makeExRow(zone, colKey, text));
    });
    col.appendChild(list);

    var mine = bank[zone.id][colKey];
    if(mine.length){
      var divider = document.createElement("div");
      divider.className = "mine-divider";
      divider.textContent = "Your saved phrases";
      col.appendChild(divider);
      var mineList = document.createElement("div");
      mineList.className = "ex-list";
      mine.forEach(function(p){
        mineList.appendChild(makeMineRow(zone, colKey, p));
      });
      col.appendChild(mineList);
    }

    return col;
  }

  function makeExRow(zone, colKey, text){
    var already = state.items[zone.id][colKey].some(function(it){ return it.text === text; });
    var row = document.createElement("button");
    row.type = "button";
    row.className = "ex-row" + (already ? " used" : "");
    row.innerHTML = '<span>'+escapeHtml(text)+'</span><span class="arrow" aria-hidden="true">→</span>';
    row.title = already ? "Already added — click to add again" : "Add to report";
    row.addEventListener("click", function(){ addItem(zone.id, colKey, text, false); flash(row); });
    return row;
  }

  function makeMineRow(zone, colKey, phrase){
    var already = state.items[zone.id][colKey].some(function(it){ return it.text === phrase.text; });
    var row = document.createElement("div");
    row.className = "ex-row mine" + (already ? " used" : "");
    var txt = document.createElement("span");
    txt.className = "txt";
    txt.textContent = phrase.text;
    var arrow = document.createElement("span");
    arrow.className = "arrow";
    arrow.setAttribute("aria-hidden","true");
    arrow.textContent = "→";
    var trash = document.createElement("button");
    trash.type = "button";
    trash.className = "trash";
    trash.title = "Remove permanently from your phrase bank";
    trash.setAttribute("aria-label","Delete saved phrase");
    trash.innerHTML = "&#128465;";
    row.appendChild(txt);
    row.appendChild(arrow);
    row.appendChild(trash);
    row.addEventListener("click", function(){ addItem(zone.id, colKey, phrase.text, false); flash(row); });
    trash.addEventListener("click", function(e){
      e.stopPropagation();
      removeFromPersonalBank(zone.id, colKey, phrase.id);
      renderBank();
    });
    return row;
  }

  // ================= REPORT RENDERING =================
  var reportBody = document.getElementById("reportBody");

  function renderReport(){
    reportBody.innerHTML = "";
    ZONES.forEach(function(zone){
      var rz = document.createElement("div");
      rz.className = "rzone";
      var title = document.createElement("div");
      title.className = "rzone-title";
      title.innerHTML = '<span class="rzone-dot" style="background:var(--'+zone.color+')"></span>'+escapeHtml(zone.label);
      rz.appendChild(title);

      COLS.forEach(function(colKey){
        rz.appendChild(renderReportColumn(zone, colKey));
      });
      reportBody.appendChild(rz);
    });
    renderPrintSheet();
    renderPrintMap();
  }

  function renderReportColumn(zone, colKey){
    var wrap = document.createElement("div");
    wrap.className = "rcol";
    var h4 = document.createElement("h4");
    h4.textContent = COL_LABELS[colKey];
    wrap.appendChild(h4);

    var items = state.items[zone.id][colKey];
    if(items.length === 0){
      var empty = document.createElement("div");
      empty.className = "rempty";
      empty.textContent = "Nothing added yet.";
      wrap.appendChild(empty);
    } else {
      items.forEach(function(item, idx){
        var line = document.createElement("div");
        line.className = "rline";
        var text = document.createElement("div");
        text.className = "text";
        text.contentEditable = "true";
        text.spellcheck = false;
        text.textContent = item.text;
        text.addEventListener("blur", function(){
          item.text = text.textContent.trim() || item.text;
          text.textContent = item.text;
        });
        var remove = document.createElement("button");
        remove.className = "remove";
        remove.setAttribute("aria-label","Remove line");
        remove.innerHTML = "×";
        remove.addEventListener("click", function(){
          items.splice(idx,1);
          renderReport();
          renderBank();
        });
        line.appendChild(text);
        line.appendChild(remove);
        wrap.appendChild(line);
      });
    }

    var addRow = document.createElement("div");
    addRow.className = "add-own";
    var input = document.createElement("input");
    input.type = "text";
    input.placeholder = "Add your own…";
    var tidyBtn = document.createElement("button");
    tidyBtn.type = "button";
    tidyBtn.className = "tidy";
    tidyBtn.textContent = "Tidy";
    tidyBtn.title = "Auto-format this wording (capitalisation, spacing) — not AI rewriting";
    tidyBtn.addEventListener("click", function(){ input.value = tidyWording(input.value); input.focus(); });
    var addBtn = document.createElement("button");
    addBtn.type = "button";
    addBtn.textContent = "+";
    addBtn.setAttribute("aria-label","Add custom line");
    function commit(){
      var v = input.value.trim();
      if(!v) return;
      addItem(zone.id, colKey, v, true);
      addToPersonalBank(zone.id, colKey, v);
      input.value = "";
      renderBank();
    }
    addBtn.addEventListener("click", commit);
    input.addEventListener("keydown", function(e){ if(e.key === "Enter"){ e.preventDefault(); commit(); } });
    addRow.appendChild(input);
    addRow.appendChild(tidyBtn);
    addRow.appendChild(addBtn);
    wrap.appendChild(addRow);

    var hint = document.createElement("div");
    hint.className = "add-hint";
    hint.textContent = "Saved to your phrase bank automatically, for reuse on future reports.";
    wrap.appendChild(hint);

    return wrap;
  }

  function addItem(zoneId, colKey, text, custom){
    var list = state.items[zoneId][colKey];
    if(!custom && list.some(function(it){ return it.text === text; })){
      renderReport();
      return;
    }
    list.push({ text:text, custom:!!custom });
    renderReport();
    renderBank();
  }

  // ================= PRINT STYLE CHOICE =================
  var PRINT_STYLE_KEY = "wot-builder-print-style-v2";
  var printStyle = "grid";
  try{ var savedStyle = localStorage.getItem(PRINT_STYLE_KEY); if(savedStyle === "map" || savedStyle === "grid") printStyle = savedStyle; }catch(e){ /* ignore */ }

  var btnStyleGrid = document.getElementById("btnStyleGrid");
  var btnStyleMap = document.getElementById("btnStyleMap");

  function applyPrintStyle(){
    document.body.setAttribute("data-print-style", printStyle);
    if(btnStyleGrid) btnStyleGrid.setAttribute("aria-pressed", printStyle === "grid" ? "true" : "false");
    if(btnStyleMap) btnStyleMap.setAttribute("aria-pressed", printStyle === "map" ? "true" : "false");
    try{ localStorage.setItem(PRINT_STYLE_KEY, printStyle); }catch(e){ /* ignore */ }
  }
  applyPrintStyle();

  if(btnStyleGrid) btnStyleGrid.addEventListener("click", function(){ printStyle = "grid"; applyPrintStyle(); });
  if(btnStyleMap) btnStyleMap.addEventListener("click", function(){ printStyle = "map"; applyPrintStyle(); });

  document.getElementById("btnPrint").addEventListener("click", function(){
    renderPrintSheet();
    renderPrintMap();
    try{ window.print(); }catch(e){ /* ignore */ }
  });

  document.getElementById("btnDownload").addEventListener("click", function(){
    var html = buildArchiveSnapshotHtml();
    var studentSlug = (currentStudent ? currentStudent.initials : "student").toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/(^-|-$)/g,"");
    var fileName = "window-of-tolerance-" + (studentSlug || "report") + ".html";
    if(downloadsNS){
      downloadsNS.save({ filename: fileName, data: html }).catch(function(){ downloadHtmlFallback(fileName, html); });
    } else {
      downloadHtmlFallback(fileName, html);
    }
  });

  function downloadHtmlFallback(fileName, html){
    try{
      var blob = new Blob([html], { type: "text/html" });
      var url = URL.createObjectURL(blob);
      var a = document.createElement("a");
      a.href = url;
      a.download = fileName;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(function(){ URL.revokeObjectURL(url); }, 1000);
    }catch(e){ /* ignore */ }
  }

  // ---- print sheet: single grid matching the org's regulation-profile template ----

  function studentDisplayName(){
    return currentStudent ? currentStudent.full_name : "[Student name]";
  }

  function getCurrentTermYear(){
    var now = new Date();
    var month = now.getMonth(); // 0 = Jan
    var term = month <= 2 ? 1 : month <= 5 ? 2 : month <= 8 ? 3 : 4;
    return { term: term, year: now.getFullYear() };
  }

  function renderPrintSheet(){
    var printMeta = document.getElementById("printMeta");
    if(printMeta){
      var ty = getCurrentTermYear();
      printMeta.innerHTML = "Student: " + escapeHtml(studentDisplayName()) +
        " &nbsp;·&nbsp; Prepared by: " + escapeHtml(teacherName || "[staff name]") +
        " &nbsp;·&nbsp; Reviewed: Term " + ty.term + ", " + ty.year;
    }

    var body = document.getElementById("printTableBody");
    if(!body) return;

    var html = "";
    html += "<tr>" +
      '<th class="axis-cell" rowspan="' + (ZONES.length + 1) + '"><span class="rot">AROUSAL</span></th>' +
      '<th class="title-cell"><span class="rot">Regulation profile and strategies</span></th>' +
      '<th class="col-head"><span class="rot">Context</span></th>' +
      '<th class="col-head"><span class="rot">Behaviour descriptors</span></th>' +
      '<th class="col-head"><span class="rot">Interventions</span></th>' +
    "</tr>";

    ZONES.forEach(function(zone){
      var labelParts = zone.label.split(" — ");
      var zn = labelParts.length > 1 ? (labelParts[0] + " — " + labelParts[1]) : zone.label;
      html += '<tr data-zone="' + zone.id + '">';
      html += '<td class="zone-label-cell">' +
        '<span class="zn">' + escapeHtml(zn) + '</span>' +
        '<span class="zd">' + escapeHtml(zone.short || zone.desc) + '</span>' +
      '</td>';
      COLS.forEach(function(colKey){
        var items = state.items[zone.id][colKey];
        if(items.length){
          html += '<td class="content-cell"><ul>' + items.map(function(it){ return "<li>" + escapeHtml(it.text) + "</li>"; }).join("") + '</ul></td>';
        } else {
          html += '<td class="content-cell"><span class="empty">—</span></td>';
        }
      });
      html += '</tr>';
    });

    body.innerHTML = html;
  }

  function renderPrintMap(){
    var nameEl = document.getElementById("mapName");
    if(nameEl) nameEl.textContent = studentDisplayName();

    var preparedByEl = document.getElementById("mapPreparedBy");
    if(preparedByEl) preparedByEl.textContent = teacherName || "[staff name]";

    var reviewedEl = document.getElementById("mapReviewed");
    if(reviewedEl){
      var ty = getCurrentTermYear();
      reviewedEl.textContent = "Term " + ty.term + ", " + ty.year;
    }

    var bandsEl = document.getElementById("mapBands");
    if(!bandsEl) return;

    var html = "";
    ZONES.forEach(function(zone){
      html += '<div class="map-band" data-zone="' + zone.id + '">';
      html += '<div class="map-zone">' +
        '<div class="map-zn">' + escapeHtml(zone.mapName || zone.label) + '</div>' +
        '<span class="map-tagpill">' + escapeHtml(zone.mapTag || "") + '</span>' +
        '<p class="map-zd">' + escapeHtml(zone.short || zone.desc) + '</p>' +
      '</div>';
      COLS.forEach(function(colKey){
        var items = state.items[zone.id][colKey];
        if(items.length){
          html += '<div class="map-col"><ul>' + items.map(function(it){ return "<li>" + escapeHtml(it.text) + "</li>"; }).join("") + '</ul></div>';
        } else {
          html += '<div class="map-col"><ul><li class="empty">—</li></ul></div>';
        }
      });
      html += '</div>';
    });

    bandsEl.innerHTML = html;
  }

  // ================= EXPORT OVERLAY =================
  var overlay = document.getElementById("exportOverlay");
  var exportText = document.getElementById("exportText");
  var copyMsg = document.getElementById("copyMsg");

  function buildExportText(){
    var lines = [];
    lines.push("Personalised Window of Tolerance — " + studentDisplayName());
    lines.push("");
    ZONES.forEach(function(zone){
      lines.push(zone.label.toUpperCase());
      lines.push(zone.desc);
      COLS.forEach(function(colKey){
        lines.push("");
        lines.push(COL_LABELS[colKey] + ":");
        var items = state.items[zone.id][colKey];
        if(items.length === 0){
          lines.push("  (none added)");
        } else {
          items.forEach(function(it){ lines.push("  - " + it.text); });
        }
      });
      lines.push("");
      lines.push("----------------------------------------");
      lines.push("");
    });
    return lines.join("\n");
  }

  document.getElementById("btnExport").addEventListener("click", function(){
    exportText.value = buildExportText();
    copyMsg.textContent = "";
    overlay.classList.add("open");
    exportText.focus();
    exportText.select();
  });
  document.getElementById("btnCloseExport").addEventListener("click", function(){
    overlay.classList.remove("open");
  });
  overlay.addEventListener("click", function(e){ if(e.target === overlay) overlay.classList.remove("open"); });

  document.getElementById("btnDoCopy").addEventListener("click", function(){
    exportText.focus();
    exportText.select();
    var done = false;
    try{
      if(navigator.clipboard && navigator.clipboard.writeText){
        navigator.clipboard.writeText(exportText.value).then(function(){
          copyMsg.textContent = "Copied.";
        }).catch(function(){
          fallbackCopy();
        });
        done = true;
      }
    }catch(e){ /* fall through */ }
    if(!done) fallbackCopy();
    function fallbackCopy(){
      try{
        var ok = document.execCommand("copy");
        copyMsg.textContent = ok ? "Copied." : "Select the text above and press Ctrl/Cmd+C.";
      }catch(e){
        copyMsg.textContent = "Select the text above and press Ctrl/Cmd+C.";
      }
    }
  });

  document.getElementById("btnDoSave").addEventListener("click", function(){
    if(!downloadsNS){ copyMsg.textContent = "File saving isn't available here — use Copy instead."; return; }
    var name = (currentStudent ? currentStudent.initials : "student").toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/(^-|-$)/g,"");
    copyMsg.textContent = "Saving…";
    downloadsNS.save({ filename: "window-of-tolerance-" + (name || "report") + ".txt", data: exportText.value })
      .then(function(){ copyMsg.textContent = "Saved."; })
      .catch(function(err){
        var code = err && err.code;
        if(code === "declined") copyMsg.textContent = "Not saved.";
        else if(code === "rate_limited") copyMsg.textContent = "Try again in a moment.";
        else copyMsg.textContent = "Couldn't save a file — try Copy instead.";
      });
  });

  // ================= MANAGE PHRASE BANK OVERLAY =================
  var bankOverlay = document.getElementById("bankOverlay");
  var bankManageBody = document.getElementById("bankManageBody");

  function renderBankManage(){
    bankManageBody.innerHTML = "";
    if(bankPhraseCount() === 0){
      var empty = document.createElement("p");
      empty.className = "bank-empty-msg";
      empty.textContent = "You haven't saved any of your own phrases yet. Anything you type with “Add your own…” on a report will appear here, ready to reuse next time.";
      bankManageBody.appendChild(empty);
      return;
    }
    ZONES.forEach(function(zone){
      var anyInZone = COLS.some(function(c){ return bank[zone.id][c].length; });
      if(!anyInZone) return;
      var group = document.createElement("div");
      group.className = "bank-zone-group";
      var h4 = document.createElement("h4");
      h4.innerHTML = '<span class="dot" style="background:var(--'+zone.color+')"></span>' + escapeHtml(zone.label);
      group.appendChild(h4);
      COLS.forEach(function(colKey){
        var phrases = bank[zone.id][colKey];
        if(!phrases.length) return;
        var colGroup = document.createElement("div");
        colGroup.className = "bank-col-group";
        var h5 = document.createElement("h5");
        h5.textContent = COL_LABELS[colKey];
        colGroup.appendChild(h5);
        phrases.forEach(function(p){
          var row = document.createElement("div");
          row.className = "bank-phrase-row";
          var txt = document.createElement("span");
          txt.className = "txt";
          txt.textContent = p.text;
          var trash = document.createElement("button");
          trash.className = "remove";
          trash.setAttribute("aria-label","Delete saved phrase");
          trash.innerHTML = "×";
          trash.addEventListener("click", function(){
            removeFromPersonalBank(zone.id, colKey, p.id);
            renderBankManage();
            renderBank();
          });
          row.appendChild(txt);
          row.appendChild(trash);
          colGroup.appendChild(row);
        });
        group.appendChild(colGroup);
      });
      bankManageBody.appendChild(group);
    });
  }

  document.getElementById("btnManageBank").addEventListener("click", function(){
    renderBankManage();
    bankOverlay.classList.add("open");
  });
  document.getElementById("btnCloseBank").addEventListener("click", function(){
    bankOverlay.classList.remove("open");
  });
  bankOverlay.addEventListener("click", function(e){ if(e.target === bankOverlay) bankOverlay.classList.remove("open"); });

  // ================= ARCHIVE TO DOCUMENT ARCHIVE =================
  var ROOT_VARS_CSS = ":root{\n    --bg:#F1F4EF;\n    --surface:#FFFFFF;\n    --surface-2:#E7ECE3;\n    --surface-3:#DEE5D9;\n    --ink:#1B211C;\n    --ink-soft:#57604F;\n    --ink-faint:#818B77;\n    --border:#D2DACB;\n    --accent:#2F6F6A;\n    --accent-ink:#FFFFFF;\n    --accent-wash:#DEEAE7;\n    --shadow: 0 1px 2px rgba(27,33,28,0.06), 0 6px 20px -8px rgba(27,33,28,0.18);\n\n    --hyper:#AF3A2C;       --hyper-wash:#F5E1DC;\n    --copingup:#B9761A;    --copingup-wash:#F3E5CC;\n    --wot:#2E7A48;         --wot-wash:#DDEBE0;\n    --copingdown:#2A6693;  --copingdown-wash:#DCE7EF;\n    --hypo:#3C4C6B;        --hypo-wash:#E1E4EB;\n\n    /* fixed print palette — always renders the same on paper, regardless of screen theme */\n    --print-red:#E14B3D;\n    --print-amber:#F2A93C;\n    --print-green:#8BC24A;\n    --print-navy:#1F2A38;\n\n    /* regulation-map print style — its own fixed palette, independent of screen theme */\n    --map-paper:#F3F5F7;\n    --map-ink:#1E2530;\n    --map-ink-soft:#565F6E;\n    --map-ink-faint:#8892A0;\n    --map-rule:#D6DBE1;\n    --map-hyper:#C1543A;     --map-hyper-tint:#F3E2DC;\n    --map-copeup:#C98A2E;    --map-copeup-tint:#F3E7D3;\n    --map-wot:#4C7A5A;       --map-wot-tint:#E1EBE3;\n    --map-copedown:#3E6E8E;  --map-copedown-tint:#DEE7ED;\n    --map-hypo:#38456B;      --map-hypo-tint:#DFE2EA;\n\n    --font-display:'Fraunces', 'Iowan Old Style', Georgia, serif;\n    --font-body:'IBM Plex Sans', 'Segoe UI', system-ui, sans-serif;\n    --font-serif-map:'Newsreader', 'Iowan Old Style', Georgia, serif;\n    --font-sans-map:'Work Sans', 'Segoe UI', system-ui, sans-serif;\n  }";
  var PRINT_CSS = "/* ---------- print sheet: single grid, zone rows x Context/Behaviour/Interventions columns ---------- */\n  .wot-print-sheet{ display:none; }\n  .print-meta{\n    font-family:var(--font-body);\n    font-size:13px;\n    color:#000;\n    margin-bottom:8px;\n    font-weight:600;\n  }\n  .print-table{\n    width:100%;\n    border-collapse:collapse;\n    table-layout:fixed;\n    background:#fff;\n  }\n  .print-table th, .print-table td{\n    border:1px solid #333;\n    padding:5px 7px;\n    vertical-align:middle;\n    color:#161616;\n  }\n  .print-table col.axis-col{ width:22px; }\n  .print-table col.label-col{ width:135px; }\n  .rot{\n    writing-mode:vertical-rl;\n    transform:rotate(180deg);\n    white-space:nowrap;\n    display:inline-block;\n  }\n  .axis-cell{\n    background:linear-gradient(180deg,\n      var(--map-hyper) 0%, var(--map-hyper) 12%,\n      var(--map-copeup) 26%,\n      var(--map-wot) 50%,\n      var(--map-copedown) 74%,\n      var(--map-hypo) 88%, var(--map-hypo) 100%);\n    color:#fff;\n    text-align:center;\n    padding:6px 1px;\n  }\n  .axis-cell .rot{ font-weight:700; font-size:11px; letter-spacing:.06em; text-shadow:0 1px 2px rgba(0,0,0,.35); }\n  .print-table th.title-cell{\n    background:var(--print-navy);\n    color:#fff;\n    text-align:center;\n    height:56px;\n  }\n  .title-cell .rot{ font-weight:700; font-size:10.5px; line-height:1.25; }\n  .print-table th.col-head{\n    background:#fff;\n    text-align:center;\n    height:56px;\n  }\n  .col-head .rot{ font-weight:700; font-size:10.5px; letter-spacing:.02em; }\n  .zone-label-cell{\n    vertical-align:middle;\n    padding:5px 7px;\n    font-size:9.5px;\n    line-height:1.25;\n  }\n  .print-table td.zone-label-cell{ color:#fff; }\n  .zone-label-cell .zn{ display:block; font-weight:700; font-size:11px; margin-bottom:2px; }\n  .zone-label-cell .zd{ font-style:italic; opacity:.92; }\n  .content-cell{\n    vertical-align:top;\n    font-size:10px;\n    line-height:1.3;\n    background:#F4F7FA;\n  }\n  .content-cell ul{ margin:0; padding-left:14px; }\n  .content-cell li{ margin-bottom:2px; }\n  .content-cell .empty{ color:#9AA0A6; font-style:italic; }\n\n  .print-table tr[data-zone=\"hyper\"] .zone-label-cell{ background:radial-gradient(120% 160% at 22% 20%, rgba(255,255,255,.4), rgba(255,255,255,0) 55%), var(--map-hyper); }\n  .print-table tr[data-zone=\"hyper\"] .content-cell{ background:var(--map-hyper-tint); }\n  .print-table tr[data-zone=\"copingup\"] .zone-label-cell{ background:radial-gradient(120% 160% at 22% 20%, rgba(255,255,255,.4), rgba(255,255,255,0) 55%), var(--map-copeup); }\n  .print-table tr[data-zone=\"copingup\"] .content-cell{ background:var(--map-copeup-tint); }\n  .print-table tr[data-zone=\"wot\"] .zone-label-cell{ background:radial-gradient(120% 160% at 22% 20%, rgba(255,255,255,.4), rgba(255,255,255,0) 55%), var(--map-wot); }\n  .print-table tr[data-zone=\"wot\"] .content-cell{ background:var(--map-wot-tint); }\n  .print-table tr[data-zone=\"copingdown\"] .zone-label-cell{ background:radial-gradient(120% 160% at 22% 20%, rgba(255,255,255,.4), rgba(255,255,255,0) 55%), var(--map-copedown); }\n  .print-table tr[data-zone=\"copingdown\"] .content-cell{ background:var(--map-copedown-tint); }\n  .print-table tr[data-zone=\"hypo\"] .zone-label-cell{ background:radial-gradient(120% 160% at 22% 20%, rgba(255,255,255,.4), rgba(255,255,255,0) 55%), var(--map-hypo); }\n  .print-table tr[data-zone=\"hypo\"] .content-cell{ background:var(--map-hypo-tint); }\n\n  /* ---------- print style 2: \"Regulation Map\" — open bands + gradient rail ---------- */\n  .print-style-toggle{ display:flex; gap:8px; align-items:center; flex-wrap:wrap; margin:0 0 10px; font-family:var(--font-body); font-size:12.5px; color:var(--ink-soft); }\n  .print-style-toggle span.lbl{ margin-right:2px; }\n  .print-style-toggle button{\n    font-family:var(--font-body); font-size:12.5px; font-weight:600;\n    padding:6px 12px; border-radius:20px; border:1px solid var(--border);\n    background:var(--surface); color:var(--ink-soft); cursor:pointer;\n  }\n  .print-style-toggle button[aria-pressed=\"true\"]{ background:var(--accent); border-color:var(--accent); color:var(--accent-ink); }\n\n  .wot-print-map{ display:none; }\n  .wot-print-map, .wot-print-map *{ box-sizing:border-box; }\n  .wot-print-map{\n    background:var(--map-paper);\n    color:var(--map-ink);\n    font-family:var(--font-sans-map);\n    -webkit-font-smoothing:antialiased;\n  }\n  .wot-print-map .map-page{\n    width:100%;\n    margin:0;\n    padding:0;\n    position:relative;\n  }\n  .wot-print-map .map-head{\n    display:flex; justify-content:space-between; align-items:flex-end; gap:24px;\n    padding-bottom:4mm; border-bottom:1px solid var(--map-rule); margin-bottom:4mm;\n  }\n  .wot-print-map .map-head .id{ max-width:70%; }\n  .wot-print-map .map-eyebrow{\n    font-family:var(--font-sans-map); font-size:10.5px; font-weight:600;\n    letter-spacing:.12em; text-transform:uppercase; color:var(--map-ink-faint); margin:0 0 6px;\n  }\n  .wot-print-map .map-name{\n    font-family:var(--font-serif-map); font-weight:500; font-size:34px;\n    color:var(--map-ink); margin:0; letter-spacing:-0.01em;\n  }\n  .wot-print-map .map-subtitle{\n    font-family:var(--font-serif-map); font-style:italic; font-size:15px;\n    color:var(--map-ink-soft); margin:5px 0 0;\n  }\n  .wot-print-map .map-meta{ text-align:right; font-size:11.5px; color:var(--map-ink-soft); line-height:1.8; white-space:nowrap; }\n  .wot-print-map .map-meta b{ color:var(--map-ink); font-weight:600; }\n\n  .wot-print-map .map-col-header{ display:grid; grid-template-columns:30px 1fr; margin-bottom:5px; }\n  .wot-print-map .map-col-header .spacer{ margin-right:14px; }\n  .wot-print-map .map-col-header .inner{ display:grid; grid-template-columns:225px 1fr 1fr 1fr; gap:22px; }\n  .wot-print-map .map-col-header .inner > div{\n    font-family:var(--font-sans-map); font-size:9.5px; font-weight:700;\n    letter-spacing:.1em; text-transform:uppercase; color:var(--map-ink-faint);\n  }\n\n  .wot-print-map .map-ladder{ display:grid; grid-template-columns:30px 1fr; gap:0; }\n  .wot-print-map .map-rail{\n    position:relative; border-radius:5px; margin-right:14px;\n    background:linear-gradient(180deg,\n      var(--map-hyper) 0%, var(--map-hyper) 12%,\n      var(--map-copeup) 26%,\n      var(--map-wot) 50%,\n      var(--map-copedown) 74%,\n      var(--map-hypo) 88%, var(--map-hypo) 100%);\n  }\n  .wot-print-map .map-rail .map-tag{\n    position:absolute; left:50%; top:50%; translate:0 50%;\n    transform:translateX(-50%) rotate(180deg); writing-mode:vertical-rl;\n    font-family:var(--font-sans-map); font-weight:600; font-size:10.5px;\n    letter-spacing:.16em; color:rgba(255,255,255,0.88); text-transform:uppercase;\n  }\n\n  .wot-print-map .map-bands{ display:flex; flex-direction:column; }\n  .wot-print-map .map-band{\n    display:grid; grid-template-columns:225px 1fr 1fr 1fr; gap:22px;\n    padding:2px 0; border-bottom:1px solid var(--map-rule);\n  }\n  .wot-print-map .map-band:last-child{ border-bottom:none; }\n\n  .wot-print-map .map-zone{ padding-right:6px; }\n  .wot-print-map .map-zn{\n    font-family:var(--font-serif-map); font-weight:500; font-size:16.5px;\n    color:var(--map-ink); margin:0 0 3px; line-height:1.2;\n  }\n  .wot-print-map .map-tagpill{\n    display:inline-block; font-size:9.5px; font-weight:600; letter-spacing:.05em;\n    text-transform:uppercase; padding:2px 7px; border-radius:20px; margin-bottom:5px;\n  }\n  .wot-print-map .map-zd{ font-size:10.5px; color:var(--map-ink-soft); line-height:1.4; font-style:italic; }\n\n  .wot-print-map .map-col{ padding-top:2px; }\n  .wot-print-map .map-col ul{ margin:0; padding:0; list-style:none; }\n  .wot-print-map .map-col li{\n    font-size:11px; line-height:1.35; color:var(--map-ink);\n    margin-bottom:3px; padding-left:11px; position:relative;\n  }\n  .wot-print-map .map-col li::before{\n    content:\"\"; position:absolute; left:0; top:6px; width:4px; height:4px;\n    border-radius:50%; background:var(--map-ink-faint);\n  }\n  .wot-print-map .map-col li.empty{ color:var(--map-ink-faint); font-style:italic; }\n  .wot-print-map .map-col li.empty::before{ display:none; }\n\n  .wot-print-map .map-band[data-zone=\"hyper\"] .map-tagpill{ background:var(--map-hyper-tint); color:var(--map-hyper); }\n  .wot-print-map .map-band[data-zone=\"copingup\"] .map-tagpill{ background:var(--map-copeup-tint); color:var(--map-copeup); }\n  .wot-print-map .map-band[data-zone=\"wot\"] .map-tagpill{ background:var(--map-wot-tint); color:var(--map-wot); }\n  .wot-print-map .map-band[data-zone=\"copingdown\"] .map-tagpill{ background:var(--map-copedown-tint); color:var(--map-copedown); }\n  .wot-print-map .map-band[data-zone=\"hypo\"] .map-tagpill{ background:var(--map-hypo-tint); color:var(--map-hypo); }\n\n  .wot-print-map .map-band[data-zone=\"hyper\"] .map-col li::before{ background:var(--map-hyper); }\n  .wot-print-map .map-band[data-zone=\"copingup\"] .map-col li::before{ background:var(--map-copeup); }\n  .wot-print-map .map-band[data-zone=\"wot\"] .map-col li::before{ background:var(--map-wot); }\n  .wot-print-map .map-band[data-zone=\"copingdown\"] .map-col li::before{ background:var(--map-copedown); }\n  .wot-print-map .map-band[data-zone=\"hypo\"] .map-col li::before{ background:var(--map-hypo); }\n\n  .wot-print-map .map-foot{\n    margin-top:3mm; padding-top:2.5mm; border-top:1px solid var(--map-rule);\n    display:flex; justify-content:space-between; font-size:9.5px; color:var(--map-ink-faint);\n  }\n\n  ";

  var archiveOverlay = document.getElementById("archiveOverlay");
  var archiveMsg = document.getElementById("archiveMsg");
  var archiveError = document.getElementById("archiveError");

  document.getElementById("btnArchive").addEventListener("click", function(){
    archiveError.textContent = "";
    archiveMsg.textContent = "";
    var ty = getCurrentTermYear();
    if(!document.getElementById("archiveYear").value){
      document.getElementById("archiveYear").value = String(ty.year);
    }
    if(!document.getElementById("archiveTerm").value){
      document.getElementById("archiveTerm").value = "Term " + ty.term;
    }
    archiveOverlay.classList.add("open");
  });
  document.getElementById("btnCloseArchive").addEventListener("click", function(){
    archiveOverlay.classList.remove("open");
  });
  archiveOverlay.addEventListener("click", function(e){ if(e.target === archiveOverlay) archiveOverlay.classList.remove("open"); });

  function buildArchiveSnapshotHtml(){
    renderPrintSheet();
    renderPrintMap();
    var activeEl = printStyle === "map" ? document.getElementById("printMap") : document.getElementById("printSheet");
    var markup = activeEl.outerHTML;
    return "<!DOCTYPE html><html><head><meta charset=\"utf-8\"><title>Window of Tolerance — " +
      escapeHtml(studentDisplayName()) + "</title><style>" + ROOT_VARS_CSS + "\n" + PRINT_CSS +
      "\nbody{background:#fff;margin:0;padding:24px;} .wot-print-sheet{display:block;max-width:1200px;margin:0 auto;} .wot-print-map{display:block;}" +
      "</style></head><body>" + markup + "</body></html>";
  }

  document.getElementById("btnDoArchive").addEventListener("click", function(){
    if(!sb){ archiveError.textContent = "Can't reach the shared database right now."; return; }
    var term = document.getElementById("archiveTerm").value.trim();
    var year = document.getElementById("archiveYear").value.trim();
    archiveError.textContent = "";
    archiveMsg.textContent = "Saving report…";

    saveReport(function(ok){
      if(!ok){ archiveError.textContent = "Couldn't save the report first — check your connection and try again."; archiveMsg.textContent = ""; return; }

      archiveMsg.textContent = "Building document…";
      var html = buildArchiveSnapshotHtml();
      var studentSlug = (currentStudent.initials || "student").toLowerCase().replace(/[^a-z0-9]+/g,"-");
      var stamp = new Date().toISOString().replace(/[:.]/g,"-");
      var fileName = "window-of-tolerance-" + studentSlug + "-" + stamp + ".html";
      var path = "wot-builder/" + fileName;

      archiveMsg.textContent = "Uploading…";
      sb.storage.from(ARCHIVE_BUCKET).upload(path, new Blob([html], { type:"text/html" }), { upsert:true, contentType:"text/html" })
        .then(function(uploadRes){
          if(uploadRes.error){
            archiveError.textContent = "Couldn't upload the document (" + uploadRes.error.message + "). The bucket name may need updating in the tool's config.";
            archiveMsg.textContent = "";
            return;
          }
          var docRow = {
            source_tool: "wot_builder",
            doc_type: "Window of Tolerance",
            title: "Window of Tolerance — " + currentStudent.full_name,
            student_initials: currentStudent.initials,
            term: term || null,
            year: year ? parseInt(year,10) : null,
            tags: ["window-of-tolerance"],
            storage_path: path,
            file_name: fileName,
            confidential: true,
            created_by: teacherName
          };
          sb.from("document_archive").insert(docRow).select().single().then(function(archRes){
            if(archRes.error){
              archiveError.textContent = "Uploaded, but couldn't file it in the archive (" + archRes.error.message + ").";
              archiveMsg.textContent = "";
              return;
            }
            sb.from("wot_builder_reports").update({
              status: "archived",
              archived_at: new Date().toISOString(),
              archived_document_id: archRes.data.id
            }).eq("id", currentReportId).then(function(){
              currentReportStatus = "archived";
              if(reportsIndex[currentStudent.id]) reportsIndex[currentStudent.id].status = "archived";
              archiveMsg.textContent = "Filed to Document Archive.";
              setTimeout(function(){
                archiveOverlay.classList.remove("open");
                archiveMsg.textContent = "";
              }, 1300);
            });
          }).catch(function(){
            archiveError.textContent = "Uploaded, but couldn't file it in the archive — check your connection.";
            archiveMsg.textContent = "";
          });
        }).catch(function(){
          archiveError.textContent = "Couldn't upload the document — check your connection.";
          archiveMsg.textContent = "";
        });
    });
  });

  // ================= MOBILE VIEW TOGGLE =================
  var tabBank = document.getElementById("tabBank");
  var tabReport = document.getElementById("tabReport");
  var bankPaneEl = document.getElementById("bankPane");
  var reportPaneEl = document.getElementById("reportPane");
  function setMobileView(view){
    tabBank.setAttribute("aria-pressed", view === "bank" ? "true":"false");
    tabReport.setAttribute("aria-pressed", view === "report" ? "true":"false");
    bankPaneEl.dataset.mobileHide = view === "bank" ? "false":"true";
    reportPaneEl.dataset.mobileHide = view === "report" ? "false":"true";
  }
  tabBank.addEventListener("click", function(){ setMobileView("bank"); });
  tabReport.addEventListener("click", function(){ setMobileView("report"); });
  setMobileView("bank");

  try{ window.addEventListener("beforeprint", function(){ renderPrintSheet(); renderPrintMap(); }); }catch(e){ /* ignore */ }

  window.addEventListener("beforeunload", function(e){
    if(hasUnsavedChanges()){
      e.preventDefault();
      e.returnValue = "";
    }
  });

  // ================= INIT =================
  loadStaffOptions();
  var saved = getSavedTeacher();
  if(saved){
    setTeacher(saved);
    enterStudentPicker();
  }
})();
</script>
