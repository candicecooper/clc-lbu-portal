<title>Window of Tolerance Builder</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght,ital@9..144,400..700,0..1&family=IBM+Plex+Sans:wght@400;500;600;700&family=Newsreader:ital,wght@0,400;0,500;0,600;1,400;1,500&family=Work+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">

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
    background:var(--print-navy);
    color:#fff;
    text-align:center;
    padding:6px 1px;
  }
  .axis-cell .rot{ font-weight:700; font-size:11px; letter-spacing:.06em; }
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
    color:#161616;
  }
  .zone-label-cell .zn{ display:block; font-weight:700; font-size:11px; margin-bottom:2px; }
  .zone-label-cell .zd{ font-style:italic; }
  .content-cell{
    vertical-align:top;
    font-size:10px;
    line-height:1.3;
    background:#F4F7FA;
  }
  .content-cell ul{ margin:0; padding-left:14px; }
  .content-cell li{ margin-bottom:2px; }
  .content-cell .empty{ color:#9AA0A6; font-style:italic; }

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
    .masthead, .ladder-key, .view-toggle, .bank, .toolbar-actions, .add-own, .rline .remove, .footnote, .layout, .print-style-toggle{ display:none !important; }
    body{ background:#fff; color:#000; }
    .app{ padding:6px; max-width:none; }
    body[data-print-style="map"] .wot-print-sheet{ display:none !important; }
    body[data-print-style="map"] .wot-print-map{ display:block !important; }
    body:not([data-print-style="map"]) .wot-print-sheet{ display:block !important; }
    @page{ size:landscape; margin:9mm; }
  }
</style>

<div class="app">
  <header class="masthead">
    <div>
      <h1>Window of Tolerance Builder</h1>
      <p class="org">Cowandilla Learning Centre — Learning and Behaviour Unit</p>
    </div>
    <p class="tagline">Click an example on the left to send it into the student's personalised plan on the right. Your own saved phrases carry over into every future report.</p>
  </header>

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
        <div class="student-field">
          <label for="studentName">Student</label>
          <input id="studentName" type="text" placeholder="Student name" autocomplete="off">
        </div>
        <div class="progress" id="progress"></div>
        <div class="print-style-toggle" id="printStyleToggle">
          <span class="lbl">Print layout:</span>
          <button type="button" id="btnStyleGrid" aria-pressed="true">Grid template</button>
          <button type="button" id="btnStyleMap" aria-pressed="false">Regulation Map</button>
        </div>
        <div class="toolbar-actions">
          <button class="btn primary" id="btnExport">Export text</button>
          <button class="btn" id="btnPrint">Print / save PDF</button>
          <button class="btn ghost" id="btnManageBank">My phrase bank</button>
          <button class="btn ghost" id="btnClear">New report</button>
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
          Prepared by: <b>[staff name]</b> &nbsp;·&nbsp; Reviewed: <b>[term, year]</b>
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
    <p class="hint">Anything you've typed with "Add your own…" is saved here on this device and shows up in the example lists on every future report, for every student. Remove one for good with the trash icon — that won't affect any report it's already been added to.</p>
    <div class="bank-manage" id="bankManageBody"></div>
    <div class="overlay-actions">
      <button class="btn" id="btnCloseBank">Close</button>
    </div>
  </div>
</div>

<script>
(function(){
  "use strict";

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
  var STORAGE_KEY = "wot-builder-draft-v1";
  var BANK_KEY = "wot-builder-phrasebank-v1";

  // ---- report state (one student's plan) ----
  var state = { studentName:"", items:{} };
  ZONES.forEach(function(z){ state.items[z.id] = { context:[], behaviour:[], interventions:[] }; });

  function loadState(){
    try{
      var raw = localStorage.getItem(STORAGE_KEY);
      if(!raw) return;
      var parsed = JSON.parse(raw);
      if(parsed && parsed.items){
        state.studentName = parsed.studentName || "";
        ZONES.forEach(function(z){
          if(parsed.items[z.id]){
            COLS.forEach(function(c){
              if(Array.isArray(parsed.items[z.id][c])) state.items[z.id][c] = parsed.items[z.id][c];
            });
          }
        });
      }
    }catch(e){ /* storage unavailable - continue with blank state */ }
  }
  function saveState(){
    try{ localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); }catch(e){ /* ignore */ }
  }
  loadState();

  // ---- personal phrase bank (persists across every future report, on this device) ----
  var bank = { };
  ZONES.forEach(function(z){ bank[z.id] = { context:[], behaviour:[], interventions:[] }; });
  var bankIdCounter = 1;

  function loadBank(){
    try{
      var raw = localStorage.getItem(BANK_KEY);
      if(!raw) return;
      var parsed = JSON.parse(raw);
      if(parsed && parsed.bank){
        ZONES.forEach(function(z){
          if(parsed.bank[z.id]){
            COLS.forEach(function(c){
              if(Array.isArray(parsed.bank[z.id][c])) bank[z.id][c] = parsed.bank[z.id][c];
            });
          }
        });
        if(typeof parsed.counter === "number") bankIdCounter = parsed.counter;
      }
    }catch(e){ /* ignore */ }
  }
  function saveBank(){
    try{ localStorage.setItem(BANK_KEY, JSON.stringify({ bank:bank, counter:bankIdCounter })); }catch(e){ /* ignore */ }
  }
  loadBank();

  function addToPersonalBank(zoneId, colKey, text){
    var norm = text.trim().toLowerCase();
    var exists = bank[zoneId][colKey].some(function(p){ return p.text.trim().toLowerCase() === norm; });
    if(exists) return;
    bank[zoneId][colKey].push({ id: "p" + (bankIdCounter++), text: text.trim() });
    saveBank();
  }
  function removeFromPersonalBank(zoneId, colKey, id){
    bank[zoneId][colKey] = bank[zoneId][colKey].filter(function(p){ return p.id !== id; });
    saveBank();
  }
  function bankPhraseCount(){
    var n = 0;
    ZONES.forEach(function(z){ COLS.forEach(function(c){ n += bank[z.id][c].length; }); });
    return n;
  }

  // ---- downloads capability (optional; export overlay upgrades if present) ----
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

  // ---- bank rendering ----
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

  function flash(el){
    el.classList.remove("flash");
    void el.offsetWidth;
    el.classList.add("flash");
  }

  function escapeHtml(s){
    return String(s).replace(/[&<>"]/g, function(c){
      return { "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;" }[c];
    });
  }

  // ---- tidy wording: light, deterministic clean-up (not AI) ----
  function tidyWording(raw){
    var t = raw.replace(/\s+/g," ").trim();
    if(!t) return t;
    t = t.replace(/[\s.]+$/,"");
    t = t.charAt(0).toUpperCase() + t.slice(1);
    return t;
  }

  // ---- report rendering ----
  var reportBody = document.getElementById("reportBody");
  var progressEl = document.getElementById("progress");
  var studentInput = document.getElementById("studentName");
  studentInput.value = state.studentName;
  studentInput.addEventListener("input", function(){
    state.studentName = studentInput.value;
    saveState();
  });

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
    progressEl.textContent = usedCount() + " of " + totalExamples() + " built-in prompts used";
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
          saveState();
        });
        var remove = document.createElement("button");
        remove.className = "remove";
        remove.setAttribute("aria-label","Remove line");
        remove.innerHTML = "×";
        remove.addEventListener("click", function(){
          items.splice(idx,1);
          saveState();
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
    saveState();
    renderReport();
    renderBank();
  }

  // ---- toolbar actions ----
  document.getElementById("btnClear").addEventListener("click", function(){
    var any = usedCount() > 0;
    if(any && !window.confirm("Start a new report? This clears the student name and every line from the current report. Your saved phrase bank is not affected.")) return;
    state.studentName = "";
    studentInput.value = "";
    ZONES.forEach(function(z){ state.items[z.id] = { context:[], behaviour:[], interventions:[] }; });
    saveState();
    renderReport();
    renderBank();
  });

  document.getElementById("btnPrint").addEventListener("click", function(){
    renderPrintSheet();
    renderPrintMap();
    try{ window.print(); }catch(e){ /* ignore */ }
  });

  // ---- print style choice (grid template vs. Regulation Map), persisted per device ----
  var PRINT_STYLE_KEY = "wot-builder-print-style-v1";
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

  // ---- print sheet: single grid matching the org's regulation-profile template ----
  var PRINT_COLORS = { hyper:"var(--print-red)", copingup:"var(--print-amber)", wot:"var(--print-green)", copingdown:"var(--print-amber)", hypo:"var(--print-red)" };

  function renderPrintSheet(){
    var printMeta = document.getElementById("printMeta");
    if(printMeta){
      var name = state.studentName.trim() || "[Student name]";
      printMeta.textContent = "Student: " + name;
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
      html += '<tr>';
      html += '<td class="zone-label-cell" style="background:' + (PRINT_COLORS[zone.id] || "#eee") + '">' +
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

  // ---- print sheet 2: "Regulation Map" (open bands + gradient rail) ----
  function renderPrintMap(){
    var nameEl = document.getElementById("mapName");
    if(nameEl){
      var name = state.studentName.trim();
      nameEl.textContent = name || "[Student name]";
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

  // ---- export overlay ----
  var overlay = document.getElementById("exportOverlay");
  var exportText = document.getElementById("exportText");
  var copyMsg = document.getElementById("copyMsg");

  function buildExportText(){
    var lines = [];
    var name = state.studentName.trim() || "[Student name]";
    lines.push("Personalised Window of Tolerance — " + name);
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
    var name = (state.studentName.trim() || "student").toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/(^-|-$)/g,"");
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

  // ---- manage-phrase-bank overlay ----
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

  // ---- mobile view toggle ----
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

  // safety net: keep the print sheet in sync even if the user prints via
  // the browser's own shortcut (Ctrl/Cmd+P) instead of the Print button
  try{ window.addEventListener("beforeprint", function(){ renderPrintSheet(); renderPrintMap(); }); }catch(e){ /* ignore */ }

  // ---- init ----
  renderBank();
  renderReport();
})();
</script>
