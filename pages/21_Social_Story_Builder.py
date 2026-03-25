import { useState, useEffect } from "react";

/* ══════════════════════════════════════════════════════════════
   CONFIG  ·  replace with your Supabase project values
   ══════════════════════════════════════════════════════════════ */
const SB_URL = "https://YOUR_PROJECT.supabase.co";
const SB_KEY = "YOUR_ANON_KEY";

/* ── SQL — run once in Supabase SQL Editor ─────────────────────
create table public.social_stories (
  id               uuid default gen_random_uuid() primary key,
  title            text not null,
  student_name     text,
  target_behaviour text,
  is_template      boolean default false,
  wizard_data      jsonb default '{}',
  sentences        jsonb default '[]',
  characters       jsonb default '[]',
  created_by       text,
  created_at       timestamptz default now(),
  updated_at       timestamptz default now()
);
create table public.staff_characters (
  id         uuid default gen_random_uuid() primary key,
  name       text not null,
  role       text,
  image_data text,
  color      text default '#0d7c7c',
  created_at timestamptz default now()
);
alter table public.social_stories   enable row level security;
alter table public.staff_characters enable row level security;
create policy "all" on public.social_stories   for all using (true) with check (true);
create policy "all" on public.staff_characters for all using (true) with check (true);
─────────────────────────────────────────────────────────────── */

const H = () => ({ apikey:SB_KEY, Authorization:`Bearer ${SB_KEY}`, "Content-Type":"application/json", Prefer:"return=representation" });
const sGet   = (t,q="") => fetch(`${SB_URL}/rest/v1/${t}${q}`,{headers:H()}).then(r=>r.json());
const sPost  = (t,b)    => fetch(`${SB_URL}/rest/v1/${t}`,{method:"POST",headers:H(),body:JSON.stringify(b)}).then(r=>r.json());
const sPatch = (t,id,b) => fetch(`${SB_URL}/rest/v1/${t}?id=eq.${id}`,{method:"PATCH",headers:H(),body:JSON.stringify(b)}).then(r=>r.json());
const sDel   = (t,id)   => fetch(`${SB_URL}/rest/v1/${t}?id=eq.${id}`,{method:"DELETE",headers:H()}).then(r=>r.ok);
const configured = SB_URL !== "https://YOUR_PROJECT.supabase.co";

const T = {
  teal:"#0d7c7c", teal2:"#0a6464", tealLt:"#e6f5f5", tealMid:"#b3dede",
  amber:"#f5a623", amberLt:"#fff8ec", amberMid:"#fde4a0",
  text:"#1a2e2e", sub:"#4a7070", border:"#cde8e8",
  white:"#ffffff", bg:"#f4fafa", slate:"#7a9e9e", err:"#c0392b", soft:"#e8f4f4",
};

const STYPES = {
  descriptive: {label:"Descriptive", color:T.teal,    bg:T.tealLt,  icon:"📋", desc:"Factual context — who, what, where, when"},
  perspective: {label:"Perspective", color:"#7b5ea7", bg:"#f3eeff", icon:"💭", desc:"How others feel or think"},
  directive:   {label:"Directive",   color:T.amber,   bg:T.amberLt, icon:"🎯", desc:"What the student will try to do"},
  affirmative: {label:"Affirmative", color:"#2e7d32", bg:"#e8f5e9", icon:"✨", desc:"Reassurance and praise"},
  coaching:    {label:"Coaching",    color:"#1565c0", bg:"#e3f2fd", icon:"🤝", desc:"How adults can help"},
};

const BEHAVIOURS = ["Joining a group activity","Asking for help","Managing big feelings","Taking turns","Transitioning between activities","Using hands/body safely","Waiting patiently","Following instructions","Greeting others","Staying on task","Handling unexpected changes","Custom…"];
const PRONOUNS   = ["he/him","she/her","they/them"];
const AGE_GROUPS = ["Early Childhood (3–5)","Primary (6–12)","Secondary (13–17)","Young Adult (18+)"];
const SETTINGS   = ["Classroom","Playground","Canteen/Lunch","Transitions","Community outing","Home","Group activity","1:1 with adult","Other"];
const ACOLORS    = ["#0d7c7c","#7b5ea7","#1565c0","#2e7d32","#c05621","#ad1457","#00838f","#4527a0"];
const STEPS      = ["Goal","Student","Context","Characters","Build","Preview"];
const uid        = () => Math.random().toString(36).slice(2,9);

// ── Atoms ──────────────────────────────────────────────────────
const Btn = ({children,onClick,variant="primary",disabled,style={}}) => {
  const V = {
    primary:  {background:T.teal,  color:T.white,  boxShadow:`0 2px 8px ${T.teal}30`},
    secondary:{background:T.soft,  color:T.teal2,  boxShadow:"none"},
    amber:    {background:T.amber, color:T.white,  boxShadow:`0 2px 8px ${T.amber}30`},
    ghost:    {background:"transparent",color:T.sub,boxShadow:"none"},
    danger:   {background:"#fdecea",color:T.err,   boxShadow:"none"},
  };
  return <button onClick={onClick} disabled={disabled} style={{padding:"9px 18px",borderRadius:10,fontSize:13,fontWeight:700,cursor:disabled?"not-allowed":"pointer",border:"none",transition:"all .15s",opacity:disabled?.5:1,fontFamily:"inherit",...V[variant],...style}}>{children}</button>;
};
const Card  = ({children,style={}}) => <div style={{background:T.white,borderRadius:16,border:`1px solid ${T.border}`,padding:"18px 22px",boxShadow:`0 2px 12px ${T.teal}08`,...style}}>{children}</div>;
const Field = ({label,hint,children}) => <div style={{marginBottom:15}}>{label&&<label style={{display:"block",fontSize:12,fontWeight:700,color:T.sub,marginBottom:4,letterSpacing:".04em"}}>{label}</label>}{hint&&<div style={{fontSize:12,color:T.slate,marginBottom:5}}>{hint}</div>}{children}</div>;
const Inp   = p => <input {...p} style={{width:"100%",padding:"9px 12px",borderRadius:9,border:`2px solid ${T.border}`,background:T.white,fontSize:13,color:T.text,outline:"none",boxSizing:"border-box",fontFamily:"inherit",...p.style}}/>;
const Txa   = p => <textarea {...p} style={{width:"100%",padding:"9px 12px",borderRadius:9,border:`2px solid ${T.border}`,background:T.white,fontSize:13,color:T.text,outline:"none",boxSizing:"border-box",resize:"vertical",minHeight:68,fontFamily:"inherit",...p.style}}/>;
const Chip  = ({label,selected,onClick}) => <button onClick={onClick} style={{padding:"5px 12px",borderRadius:20,fontSize:12,fontWeight:600,border:`2px solid ${selected?T.teal:T.border}`,background:selected?T.teal:T.white,color:selected?T.white:T.sub,cursor:"pointer",transition:"all .15s",fontFamily:"inherit"}}>{label}</button>;
const Badge = ({type}) => { const t=STYPES[type]; return <span style={{fontSize:11,fontWeight:700,padding:"2px 8px",borderRadius:12,background:t.bg,color:t.color,border:`1px solid ${t.color}22`,whiteSpace:"nowrap"}}>{t.icon} {t.label}</span>; };
const Avatar = ({char,size=44}) => {
  const src=char?.imageUrl||char?.image_data;
  if(src) return <img src={src} alt={char?.name||""} style={{width:size,height:size,borderRadius:"50%",objectFit:"cover",border:`2px solid ${T.teal}`,flexShrink:0}}/>;
  const init=(char?.name||"?").split(" ").map(w=>w[0]).join("").slice(0,2).toUpperCase();
  return <div style={{width:size,height:size,borderRadius:"50%",background:char?.color||T.teal,display:"flex",alignItems:"center",justifyContent:"center",color:T.white,fontWeight:800,fontSize:size*.35,flexShrink:0}}>{init}</div>;
};
const StepBar = ({current}) => (
  <div style={{display:"flex",alignItems:"center",marginBottom:22}}>
    {STEPS.map((s,i) => { const done=i<current,active=i===current; return (
      <div key={s} style={{display:"flex",alignItems:"center",flex:i<STEPS.length-1?1:"none"}}>
        <div style={{width:26,height:26,borderRadius:"50%",flexShrink:0,background:done?T.teal:active?T.amber:T.border,color:(done||active)?T.white:T.slate,display:"flex",alignItems:"center",justifyContent:"center",fontSize:10,fontWeight:800}}>{done?"✓":i+1}</div>
        <span style={{fontSize:11,color:active?T.teal:T.slate,fontWeight:active?700:500,margin:"0 4px",whiteSpace:"nowrap"}}>{s}</span>
        {i<STEPS.length-1&&<div style={{flex:1,height:2,background:done?T.teal:T.border,minWidth:8}}/>}
      </div>
    ); })}
  </div>
);

// ── Wizard Steps ───────────────────────────────────────────────
function StepGoal({d,set}) {
  return <div>
    <h2 style={{color:T.teal,fontSize:20,fontWeight:800,marginBottom:4}}>🎯 What's the goal?</h2>
    <p style={{color:T.sub,fontSize:13,marginBottom:18}}>Start with the end in mind — what skill or behaviour do we want to support?</p>
    <Field label="TARGET BEHAVIOUR">
      <div style={{display:"flex",flexWrap:"wrap",gap:6,marginBottom:8}}>{BEHAVIOURS.map(b=><Chip key={b} label={b} selected={d.targetBehaviour===b} onClick={()=>set({...d,targetBehaviour:b})}/>)}</div>
      {d.targetBehaviour==="Custom…"&&<Inp placeholder="Describe the target behaviour…" value={d.customBehaviour||""} onChange={e=>set({...d,customBehaviour:e.target.value})}/>}
    </Field>
    <Field label="WHAT DOES SUCCESS LOOK LIKE?" hint="When they've got this — what will they be doing?">
      <Txa placeholder="e.g. Sam will raise their hand and wait to be called on before speaking…" value={d.successCriteria||""} rows={2} onChange={e=>set({...d,successCriteria:e.target.value})}/>
    </Field>
    <Field label="WHY IS THIS IMPORTANT?">
      <Txa placeholder="What difference will it make for this student?" value={d.whyImportant||""} rows={2} onChange={e=>set({...d,whyImportant:e.target.value})}/>
    </Field>
  </div>;
}

function StepStudent({d,set}) {
  return <div>
    <h2 style={{color:T.teal,fontSize:20,fontWeight:800,marginBottom:4}}>👤 About the student</h2>
    <p style={{color:T.sub,fontSize:13,marginBottom:18}}>Shapes the language level, pronouns, and perspective of the story.</p>
    <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:14}}>
      <Field label="NAME / PSEUDONYM"><Inp placeholder="Sam, or a pseudonym" value={d.studentName||""} onChange={e=>set({...d,studentName:e.target.value})}/></Field>
      <Field label="PRONOUNS"><div style={{display:"flex",gap:6,paddingTop:2}}>{PRONOUNS.map(p=><Chip key={p} label={p} selected={d.pronouns===p} onClick={()=>set({...d,pronouns:p})}/>)}</div></Field>
    </div>
    <Field label="AGE GROUP"><div style={{display:"flex",flexWrap:"wrap",gap:6}}>{AGE_GROUPS.map(a=><Chip key={a} label={a} selected={d.ageGroup===a} onClick={()=>set({...d,ageGroup:a})}/>)}</div></Field>
    <Field label="STRENGTHS & INTERESTS" hint="Woven in naturally to make the story relatable">
      <Txa placeholder="e.g. loves Minecraft, strong visual learner, very caring about animals…" value={d.strengths||""} rows={2} onChange={e=>set({...d,strengths:e.target.value})}/>
    </Field>
    <Field label="WHAT CURRENTLY HAPPENS?" hint="Acknowledge their experience without judgment">
      <Txa placeholder="e.g. Sam sometimes calls out before the teacher finishes speaking…" value={d.currentBehaviour||""} rows={2} onChange={e=>set({...d,currentBehaviour:e.target.value})}/>
    </Field>
    <Field label="KNOWN TRIGGERS / CHALLENGES">
      <Txa placeholder="Sensory, emotional, environmental factors…" value={d.triggers||""} rows={2} onChange={e=>set({...d,triggers:e.target.value})}/>
    </Field>
  </div>;
}

function StepContext({d,set}) {
  return <div>
    <h2 style={{color:T.teal,fontSize:20,fontWeight:800,marginBottom:4}}>📍 The situation</h2>
    <p style={{color:T.sub,fontSize:13,marginBottom:18}}>Good social stories are specific and concrete about where and when.</p>
    <Field label="SETTING">
      <div style={{display:"flex",flexWrap:"wrap",gap:6,marginBottom:6}}>{SETTINGS.map(s=><Chip key={s} label={s} selected={d.setting===s} onClick={()=>set({...d,setting:s})}/>)}</div>
      {d.setting==="Other"&&<Inp placeholder="Describe the setting…" value={d.customSetting||""} onChange={e=>set({...d,customSetting:e.target.value})}/>}
    </Field>
    <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:14}}>
      <Field label="WHEN?"><Inp placeholder="e.g. Every morning, ~9:15am group time" value={d.when||""} onChange={e=>set({...d,when:e.target.value})}/></Field>
      <Field label="TONE">
        <div style={{display:"flex",flexWrap:"wrap",gap:6,paddingTop:2}}>{["Warm & encouraging","Matter-of-fact","Playful","Celebratory"].map(t=><Chip key={t} label={t} selected={d.tone===t} onClick={()=>set({...d,tone:t})}/>)}</div>
      </Field>
    </div>
    <Field label="WHAT USUALLY HAPPENS JUST BEFORE? (antecedent)">
      <Txa placeholder="The trigger moment — what sets this off?" value={d.antecedent||""} rows={2} onChange={e=>set({...d,antecedent:e.target.value})}/>
    </Field>
    <Field label="SUPPORTS ALREADY IN PLACE">
      <Txa placeholder="e.g. visual timer, fidget tool, 'thinking hand' gesture…" value={d.supports||""} rows={2} onChange={e=>set({...d,supports:e.target.value})}/>
    </Field>
  </div>;
}

function StepCharacters({d,set,staffChars}) {
  const [newName,setNewName]=useState(""), [newRole,setNewRole]=useState("");
  const chars=d.characters||[];
  const add=()=>{if(!newName.trim())return;set({...d,characters:[...chars,{id:uid(),name:newName.trim(),role:newRole.trim(),imageUrl:null,color:ACOLORS[chars.length%ACOLORS.length]}]});setNewName("");setNewRole("");};
  const uploadImg=(idx,file)=>{const r=new FileReader();r.onload=e=>set({...d,characters:chars.map((c,i)=>i===idx?{...c,imageUrl:e.target.result}:c)});r.readAsDataURL(file);};
  const addFromLib=sc=>{if(chars.find(c=>c.name===sc.name))return;set({...d,characters:[...chars,{id:uid(),name:sc.name,role:sc.role||"",imageUrl:sc.image_data||null,color:sc.color||T.teal}]});};

  return <div>
    <h2 style={{color:T.teal,fontSize:20,fontWeight:800,marginBottom:4}}>🧑‍🤝‍🧑 Characters</h2>
    <p style={{color:T.sub,fontSize:13,marginBottom:8}}>Add staff and peers who appear in the story. Upload your staff cartoon images!</p>
    {staffChars.length>0&&<div style={{background:T.amberLt,border:`1px solid ${T.amberMid}`,borderRadius:10,padding:"10px 14px",marginBottom:14}}>
      <div style={{fontSize:12,fontWeight:700,color:"#7a5000",marginBottom:8}}>⚡ Quick-add from Staff Library</div>
      <div style={{display:"flex",flexWrap:"wrap",gap:7}}>{staffChars.map(sc=><button key={sc.id} onClick={()=>addFromLib(sc)} style={{display:"flex",alignItems:"center",gap:6,padding:"4px 10px",borderRadius:20,border:`1px solid ${T.amber}`,background:T.white,cursor:"pointer",fontSize:12,fontFamily:"inherit"}}><Avatar char={{...sc,imageUrl:sc.image_data}} size={24}/>{sc.name}</button>)}</div>
    </div>}
    <div style={{display:"flex",flexDirection:"column",gap:8,marginBottom:12}}>
      {chars.map((c,idx)=>(
        <Card key={c.id} style={{display:"flex",alignItems:"center",gap:12,padding:"10px 14px"}}>
          <Avatar char={c} size={40}/>
          <div style={{flex:1}}><div style={{fontWeight:700,color:T.text}}>{c.name}</div><div style={{fontSize:12,color:T.slate}}>{c.role||"No role"}</div></div>
          <label style={{padding:"5px 10px",borderRadius:8,fontSize:11,fontWeight:700,background:T.soft,color:T.teal,cursor:"pointer",border:`1px solid ${T.border}`}}>
            {c.imageUrl?"Change":"Upload cartoon"}<input type="file" accept="image/*" style={{display:"none"}} onChange={e=>{if(e.target.files[0])uploadImg(idx,e.target.files[0]);}}/>
          </label>
          <button onClick={()=>set({...d,characters:chars.filter((_,i)=>i!==idx)})} style={{background:"none",border:"none",cursor:"pointer",color:T.slate,fontSize:15}}>✕</button>
        </Card>
      ))}
    </div>
    <Card style={{background:T.tealLt,borderStyle:"dashed"}}>
      <div style={{fontWeight:700,color:T.teal,marginBottom:10}}>+ Add character</div>
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10}}>
        <Field label="NAME"><Inp placeholder="e.g. Ms Chen" value={newName} onChange={e=>setNewName(e.target.value)}/></Field>
        <Field label="ROLE"><Inp placeholder="e.g. classroom teacher" value={newRole} onChange={e=>setNewRole(e.target.value)}/></Field>
      </div>
      <Btn onClick={add} disabled={!newName.trim()}>Add Character</Btn>
    </Card>
  </div>;
}

function StepBuild({d,set}) {
  const [loading,setLoading]=useState(false),[err,setErr]=useState(null);
  const [editId,setEditId]=useState(null),[editTxt,setEditTxt]=useState("");
  const sentences=d.sentences||[];
  const pr=d.pronouns||"they/them";
  const [s,o,p]=pr==="he/him"?["he","him","his"]:pr==="she/her"?["she","her","her"]:["they","them","their"];
  const beh=d.targetBehaviour==="Custom…"?d.customBehaviour:d.targetBehaviour;
  const chars=(d.characters||[]).map(c=>`${c.name} (${c.role||"support person"})`).join(", ")||"teacher, support staff";

  const prompt=`You are a speech pathologist building a Carol Gray social story.
STUDENT: ${d.studentName||"the student"} (${d.ageGroup||"primary age"}, pronouns ${s}/${o}/${p})
TARGET: ${beh} | SUCCESS: ${d.successCriteria||""} | WHY: ${d.whyImportant||""}
STRENGTHS: ${d.strengths||""} | CURRENT: ${d.currentBehaviour||""} | TRIGGERS: ${d.triggers||""}
SETTING: ${d.setting||"school"} | WHEN: ${d.when||""} | ANTECEDENT: ${d.antecedent||""}
SUPPORTS: ${d.supports||""} | TONE: ${d.tone||"warm and encouraging"} | CHARACTERS: ${chars}
CAROL GRAY RULES: First person. 60%+ DESCRIPTIVE, ~20% PERSPECTIVE, max 20% DIRECTIVE ("I will try to…").
Sprinkle AFFIRMATIVE and COACHING. Never negative. 8-12 sentences. Weave in a strength/interest.
Return ONLY JSON array, no markdown: [{"type":"descriptive","text":"..."},...]
Types: descriptive|perspective|directive|affirmative|coaching`;

  const generate=async()=>{
    setLoading(true);setErr(null);
    try{
      const res=await fetch("https://api.anthropic.com/v1/messages",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({model:"claude-sonnet-4-20250514",max_tokens:1000,messages:[{role:"user",content:prompt}]})});
      const data=await res.json();
      const raw=data.content?.find(c=>c.type==="text")?.text||"";
      set({...d,sentences:JSON.parse(raw.replace(/```json|```/g,"").trim()).map(s=>({...s,id:uid(),characterId:null}))});
    }catch{setErr("Generation failed — check all fields are complete and try again.");}
    setLoading(false);
  };

  const counts=Object.fromEntries(Object.keys(STYPES).map(k=>[k,sentences.filter(x=>x.type===k).length]));
  const ideal=!counts.directive||counts.descriptive/counts.directive>=2;
  const move=(idx,dir)=>{const a=[...sentences];const to=idx+dir;if(to<0||to>=a.length)return;[a[idx],a[to]]=[a[to],a[idx]];set({...d,sentences:a});};

  return <div>
    <h2 style={{color:T.teal,fontSize:20,fontWeight:800,marginBottom:4}}>✍️ Build the story</h2>
    <p style={{color:T.sub,fontSize:13,marginBottom:14}}>Generate a Carol Gray draft, then edit, reorder, and assign characters to sentences.</p>
    {sentences.length===0?(
      <div style={{textAlign:"center",padding:"32px 16px"}}>
        <div style={{fontSize:44,marginBottom:10}}>🤖</div>
        <div style={{fontWeight:700,color:T.text,marginBottom:6}}>Ready to generate</div>
        <div style={{color:T.sub,fontSize:13,marginBottom:18}}>AI applies the Carol Gray framework using your inputs.</div>
        <Btn variant="amber" onClick={generate} disabled={loading} style={{fontSize:14,padding:"11px 28px"}}>{loading?"✨ Generating…":"✨ Generate Story Draft"}</Btn>
        {err&&<div style={{color:T.err,marginTop:10,fontSize:12}}>{err}</div>}
      </div>
    ):(
      <>
        <div style={{display:"flex",gap:6,flexWrap:"wrap",marginBottom:12,alignItems:"center"}}>
          <span style={{fontSize:11,color:T.sub,fontWeight:700}}>MIX:</span>
          {Object.entries(counts).filter(([,v])=>v>0).map(([k,v])=><span key={k} style={{fontSize:11,padding:"2px 8px",borderRadius:10,background:STYPES[k].bg,color:STYPES[k].color,fontWeight:700}}>{STYPES[k].icon} {k}: {v}</span>)}
          {!ideal&&<span style={{fontSize:11,color:T.amber,fontWeight:700}}>⚠️ Add more descriptive sentences (2:1 vs directive)</span>}
        </div>
        <div style={{display:"flex",flexDirection:"column",gap:8,marginBottom:12}}>
          {sentences.map((s,idx)=>(
            <Card key={s.id} style={{padding:"10px 12px"}}>
              <div style={{display:"flex",alignItems:"flex-start",gap:8}}>
                <div style={{display:"flex",flexDirection:"column",gap:1}}>
                  <button onClick={()=>move(idx,-1)} disabled={idx===0} style={{background:"none",border:"none",cursor:idx===0?"not-allowed":"pointer",color:T.slate,fontSize:10,padding:0}}>▲</button>
                  <button onClick={()=>move(idx,1)} disabled={idx===sentences.length-1} style={{background:"none",border:"none",cursor:idx===sentences.length-1?"not-allowed":"pointer",color:T.slate,fontSize:10,padding:0}}>▼</button>
                </div>
                <div style={{flex:1}}>
                  <div style={{display:"flex",gap:6,marginBottom:5,flexWrap:"wrap",alignItems:"center"}}>
                    <span style={{fontSize:11,color:T.slate,fontWeight:700}}>{idx+1}.</span>
                    <select value={s.type} onChange={e=>set({...d,sentences:sentences.map(x=>x.id===s.id?{...x,type:e.target.value}:x)})} style={{border:`1px solid ${T.border}`,borderRadius:6,padding:"2px 5px",fontSize:11,background:T.white,fontFamily:"inherit",color:T.text}}>
                      {Object.entries(STYPES).map(([k,v])=><option key={k} value={k}>{v.icon} {v.label}</option>)}
                    </select>
                    {(d.characters||[]).length>0&&<select value={s.characterId||""} onChange={e=>set({...d,sentences:sentences.map(x=>x.id===s.id?{...x,characterId:e.target.value||null}:x)})} style={{border:`1px solid ${T.border}`,borderRadius:6,padding:"2px 5px",fontSize:11,background:T.white,fontFamily:"inherit",color:T.text}}>
                      <option value="">No image</option>
                      <option value="student">{d.studentName||"Student"}</option>
                      {(d.characters||[]).map(c=><option key={c.id} value={c.id}>{c.name}</option>)}
                    </select>}
                  </div>
                  {editId===s.id
                    ?<div><Txa value={editTxt} onChange={e=>setEditTxt(e.target.value)} rows={2} style={{marginBottom:6}} autoFocus/><div style={{display:"flex",gap:6}}><Btn onClick={()=>{set({...d,sentences:sentences.map(x=>x.id===s.id?{...x,text:editTxt}:x)});setEditId(null);}} style={{padding:"5px 12px",fontSize:12}}>Save</Btn><Btn variant="ghost" onClick={()=>setEditId(null)} style={{padding:"5px 12px",fontSize:12}}>Cancel</Btn></div></div>
                    :<div onClick={()=>{setEditId(s.id);setEditTxt(s.text);}} style={{fontSize:13,color:s.text?T.text:T.slate,fontStyle:s.text?"normal":"italic",lineHeight:1.5,cursor:"pointer"}}>{s.text||"Click to add text…"}</div>}
                </div>
                <button onClick={()=>set({...d,sentences:sentences.filter(x=>x.id!==s.id)})} style={{background:"none",border:"none",cursor:"pointer",color:T.slate,fontSize:15,padding:"0 2px"}}>✕</button>
              </div>
            </Card>
          ))}
        </div>
        <div style={{display:"flex",gap:6,flexWrap:"wrap",marginBottom:10}}>
          {Object.entries(STYPES).map(([k,v])=><button key={k} onClick={()=>{const ns={id:uid(),type:k,text:"",characterId:null};set({...d,sentences:[...sentences,ns]});setEditId(ns.id);setEditTxt("");}} style={{padding:"5px 10px",borderRadius:8,fontSize:11,fontWeight:700,background:v.bg,color:v.color,border:`1px solid ${v.color}33`,cursor:"pointer",fontFamily:"inherit"}}>+ {v.icon} {v.label}</button>)}
        </div>
        <Btn variant="secondary" onClick={generate} disabled={loading} style={{fontSize:12}}>{loading?"Regenerating…":"↺ Regenerate"}</Btn>
        {err&&<div style={{color:T.err,marginTop:6,fontSize:12}}>{err}</div>}
      </>
    )}
    {sentences.length>0&&<Card style={{marginTop:14,background:T.amberLt}}>
      <div style={{fontWeight:700,color:"#7a5000",marginBottom:8,fontSize:12}}>📚 CAROL GRAY'S SENTENCE TYPES</div>
      <div style={{display:"flex",flexWrap:"wrap",gap:10}}>{Object.entries(STYPES).map(([k,v])=><div key={k} style={{display:"flex",gap:5,minWidth:130,flex:1}}><span>{v.icon}</span><div><div style={{fontSize:12,fontWeight:700,color:v.color}}>{v.label}</div><div style={{fontSize:11,color:T.sub}}>{v.desc}</div></div></div>)}</div>
    </Card>}
  </div>;
}

function StepPreview({d,onBook}) {
  const sentences=d.sentences||[], chars=d.characters||[];
  const title=d.storyTitle||`${d.studentName||"My"}'s Story`;
  const beh=d.targetBehaviour==="Custom…"?d.customBehaviour:d.targetBehaviour;
  const getChar=id=>{ if(id==="student")return{name:d.studentName||"Student",imageUrl:null,color:T.amber}; return chars.find(c=>c.id===id)||null; };

  const doPrint=()=>{
    const w=window.open("","_blank");
    const chHtml=s=>{ const c=s.characterId?getChar(s.characterId):null; if(!c)return'<div style="width:72px;flex-shrink:0"></div>'; const av=c.imageUrl?`<img style="width:72px;height:72px;border-radius:50%;object-fit:cover;border:3px solid #0d7c7c" src="${c.imageUrl}"/>`:`<div style="width:72px;height:72px;border-radius:50%;background:${c.color||T.teal}22;border:3px solid ${c.color||T.teal};display:flex;align-items:center;justify-content:center;font-size:22px;font-weight:800;color:${c.color||T.teal}">${(c.name||"?").split(" ").map(w=>w[0]).join("").slice(0,2).toUpperCase()}</div>`; return`<div style="text-align:center;flex-shrink:0">${av}<div style="font-size:11px;color:#7a9e9e;margin-top:3px;font-weight:600">${c.name}</div></div>`; };
    w.document.write(`<html><head><title>${title}</title><style>body{font-family:'Trebuchet MS',sans-serif;padding:40px;max-width:700px;margin:auto;color:#1a2e2e}h1{color:#0d7c7c;text-align:center;font-size:26px;margin-bottom:4px}h2{text-align:center;color:#4a7070;font-size:14px;font-weight:400;margin-bottom:32px}.s{display:flex;align-items:flex-start;gap:16px;margin-bottom:20px;padding:14px;border-radius:12px}.text{font-size:17px;line-height:1.6}.badge{font-size:11px;font-weight:700;padding:2px 8px;border-radius:12px;margin-bottom:6px;display:inline-block}.footer{margin-top:40px;text-align:center;color:#7a9e9e;font-size:11px;border-top:1px solid #cde8e8;padding-top:16px}@media print{body{padding:20px}}</style></head><body><h1>📖 ${title}</h1><h2>${beh||""}</h2>${sentences.map(s=>{const t=STYPES[s.type];return`<div class="s" style="background:${t.bg};border-left:4px solid ${t.color}">${chHtml(s)}<div><span class="badge" style="background:${t.bg};color:${t.color}">${t.icon} ${t.label}</span><div class="text">${s.text}</div></div></div>`;}).join("")}<div class="footer">Cowandilla Learning Centre &middot; Learning &amp; Behaviour Unit<br>Created using the CLC Social Story Builder</div></body></html>`);
    w.document.close();w.print();
  };

  return <div>
    <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:14,flexWrap:"wrap",gap:10}}>
      <div><h2 style={{color:T.teal,fontSize:20,fontWeight:800,marginBottom:2}}>📖 Preview</h2><p style={{color:T.sub,fontSize:13}}>Review the finished story.</p></div>
      <div style={{display:"flex",gap:8}}><Btn variant="secondary" onClick={onBook}>📱 Student View</Btn><Btn variant="amber" onClick={doPrint}>🖨️ Print / PDF</Btn></div>
    </div>
    <div style={{background:`linear-gradient(135deg,${T.teal},${T.teal2})`,borderRadius:14,padding:"20px 28px",marginBottom:14,textAlign:"center",boxShadow:`0 4px 20px ${T.teal}25`}}>
      <div style={{fontSize:26,marginBottom:5}}>📖</div>
      <div style={{fontSize:21,fontWeight:900,color:T.white,marginBottom:3}}>{title}</div>
      <div style={{fontSize:13,color:T.tealLt}}>About: {beh}</div>
    </div>
    <div style={{display:"flex",flexDirection:"column",gap:10}}>
      {sentences.map(s=>{ const t=STYPES[s.type],ch=s.characterId?getChar(s.characterId):null; return(
        <Card key={s.id} style={{display:"flex",alignItems:"flex-start",gap:14,padding:"14px 16px",borderLeft:`4px solid ${t.color}`}}>
          {ch?<div style={{flexShrink:0,textAlign:"center"}}><Avatar char={ch} size={50}/><div style={{fontSize:10,color:T.slate,marginTop:3,fontWeight:600}}>{ch.name}</div></div>:<div style={{width:50,flexShrink:0}}/>}
          <div style={{flex:1}}><Badge type={s.type}/><div style={{fontSize:15,color:T.text,lineHeight:1.6,marginTop:5,fontWeight:500}}>{s.text}</div></div>
        </Card>
      );})}
    </div>
    <div style={{marginTop:14,padding:"10px 14px",background:T.tealLt,borderRadius:10,fontSize:11,color:T.slate,textAlign:"center"}}>
      Cowandilla Learning Centre &middot; Learning &amp; Behaviour Unit &middot; Created using the CLC Social Story Builder
    </div>
  </div>;
}

// ── Wizard Orchestrator ────────────────────────────────────────
function WizardView({initial,onSave,onBook,staffChars}) {
  const [step,setStep]=useState(0);
  const [d,setD]=useState(initial||{targetBehaviour:"",customBehaviour:"",successCriteria:"",whyImportant:"",studentName:"",pronouns:"they/them",ageGroup:"",strengths:"",currentBehaviour:"",triggers:"",setting:"",when:"",antecedent:"",supports:"",tone:"Warm & encouraging",characters:[],sentences:[],storyTitle:"",is_template:false});
  const [saving,setSaving]=useState(false),[saved,setSaved]=useState(false);

  const canNext=()=>{ if(step===0)return !!(d.targetBehaviour&&(d.targetBehaviour!=="Custom…"||d.customBehaviour)); if(step===1)return !!d.studentName; if(step===2)return !!d.setting; return true; };

  const save=async()=>{
    setSaving(true);
    const beh=d.targetBehaviour==="Custom…"?d.customBehaviour:d.targetBehaviour;
    const rec={title:d.storyTitle||`${d.studentName||"My"}'s Story`,student_name:d.studentName||"",target_behaviour:beh||"",is_template:d.is_template||false,wizard_data:d,sentences:d.sentences||[],characters:d.characters||[],updated_at:new Date().toISOString()};
    try{
      let r; if(d.id){r=await sPatch("social_stories",d.id,rec);}else{r=await sPost("social_stories",rec);}
      const nid=Array.isArray(r)?r[0]?.id:r?.id; if(nid)setD(prev=>({...prev,id:nid}));
      setSaved(true); onSave&&onSave();
    }catch{alert("Save failed — check Supabase config.");}
    setSaving(false);
  };

  return <div>
    <StepBar current={step}/>
    <Card>
      {step===0&&<StepGoal d={d} set={setD}/>}
      {step===1&&<StepStudent d={d} set={setD}/>}
      {step===2&&<StepContext d={d} set={setD}/>}
      {step===3&&<StepCharacters d={d} set={setD} staffChars={staffChars}/>}
      {step===4&&<StepBuild d={d} set={setD}/>}
      {step===5&&<StepPreview d={d} onBook={()=>onBook(d)}/>}
      {step===5&&(d.sentences||[]).length>0&&(
        <div style={{marginTop:18,padding:"14px 16px",background:T.tealLt,borderRadius:12,display:"flex",alignItems:"center",justifyContent:"space-between",flexWrap:"wrap",gap:10}}>
          <div>
            <label style={{display:"flex",alignItems:"center",gap:6,cursor:"pointer",fontSize:13,fontWeight:700,color:T.teal,marginBottom:8}}>
              <input type="checkbox" checked={d.is_template||false} onChange={e=>setD({...d,is_template:e.target.checked})} style={{width:15,height:15}}/> Mark as reusable template
            </label>
            <Inp placeholder="Story title" value={d.storyTitle||`${d.studentName||"My"}'s Story`} onChange={e=>setD({...d,storyTitle:e.target.value})} style={{maxWidth:320}}/>
          </div>
          <div style={{display:"flex",gap:8,alignItems:"center"}}>
            {saved&&<span style={{fontSize:12,color:"#2e7d32",fontWeight:700}}>✓ Saved!</span>}
            <Btn variant="amber" onClick={save} disabled={saving}>{saving?"Saving…":"💾 Save to Library"}</Btn>
          </div>
        </div>
      )}
    </Card>
    <div style={{display:"flex",justifyContent:"space-between",marginTop:14,alignItems:"center"}}>
      <Btn variant="secondary" onClick={()=>setStep(s=>s-1)} disabled={step===0}>← Back</Btn>
      <div style={{display:"flex",gap:5}}>{STEPS.map((_,i)=><div key={i} style={{width:7,height:7,borderRadius:"50%",background:i===step?T.amber:i<step?T.teal:T.border}}/>)}</div>
      {step<STEPS.length-1?<Btn onClick={()=>setStep(s=>s+1)} disabled={!canNext()}>Next: {STEPS[step+1]} →</Btn>:<Btn variant="ghost" onClick={()=>window.location.reload()}>+ New Story</Btn>}
    </div>
  </div>;
}

// ── Book View (student-facing) ─────────────────────────────────
function BookView({story,onClose}) {
  const [page,setPage]=useState(-1);
  const sentences=story.sentences||story.wizard_data?.sentences||[];
  const chars=story.characters||story.wizard_data?.characters||[];
  const title=story.storyTitle||story.title||`${story.studentName||story.student_name||"My"}'s Story`;
  const getChar=id=>{ if(!id)return null; if(id==="student")return{name:story.studentName||story.student_name||"Student",imageUrl:null,color:T.amber}; return chars.find(c=>c.id===id)||null; };
  const s=page>=0?sentences[page]:null;
  const ch=s?.characterId?getChar(s.characterId):null;

  return <div style={{position:"fixed",inset:0,background:"rgba(8,50,50,.93)",display:"flex",alignItems:"center",justifyContent:"center",zIndex:1000,padding:20}}>
    <div style={{background:T.white,borderRadius:28,maxWidth:560,width:"100%",padding:"34px 38px",position:"relative",boxShadow:"0 24px 70px rgba(0,0,0,.45)",minHeight:420,display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"space-between"}}>
      <button onClick={onClose} style={{position:"absolute",top:14,right:18,background:"none",border:"none",cursor:"pointer",fontSize:22,color:T.slate}}>✕</button>
      {page===-1?(
        <div style={{textAlign:"center",flex:1,display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center",gap:14}}>
          <div style={{fontSize:64}}>📖</div>
          <div style={{fontSize:28,fontWeight:900,color:T.teal,lineHeight:1.2,maxWidth:380}}>{title}</div>
          <div style={{fontSize:15,color:T.sub}}>{story.target_behaviour||story.targetBehaviour}</div>
          <Btn variant="amber" onClick={()=>setPage(0)} style={{marginTop:10,fontSize:16,padding:"13px 36px"}}>Start Reading →</Btn>
        </div>
      ):(
        <div style={{flex:1,width:"100%",display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center",gap:22,padding:"10px 0"}}>
          {ch?<div style={{textAlign:"center"}}><Avatar char={ch} size={100}/><div style={{fontSize:13,color:T.sub,marginTop:6,fontWeight:700}}>{ch.name}</div></div>:<div style={{fontSize:40}}>💬</div>}
          <div style={{fontSize:22,lineHeight:1.8,textAlign:"center",color:T.text,fontWeight:600,maxWidth:420}}>{s?.text}</div>
        </div>
      )}
      {page>=0&&<div style={{display:"flex",alignItems:"center",justifyContent:"space-between",width:"100%",marginTop:18}}>
        <button onClick={()=>setPage(p=>p-1)} style={{background:T.soft,border:"none",borderRadius:10,padding:"10px 20px",cursor:"pointer",color:T.teal,fontWeight:700,fontSize:14,fontFamily:"inherit"}}>← Back</button>
        <div style={{textAlign:"center"}}>
          <div style={{display:"flex",gap:5,justifyContent:"center",marginBottom:3}}>{sentences.map((_,i)=><div key={i} style={{width:8,height:8,borderRadius:"50%",background:i===page?T.amber:T.border,transition:"all .2s"}}/>)}</div>
          <div style={{fontSize:12,color:T.slate}}>{page+1} / {sentences.length}</div>
        </div>
        {page<sentences.length-1
          ?<button onClick={()=>setPage(p=>p+1)} style={{background:T.teal,border:"none",borderRadius:10,padding:"10px 20px",cursor:"pointer",color:T.white,fontWeight:700,fontSize:14,fontFamily:"inherit"}}>Next →</button>
          :<button onClick={onClose} style={{background:T.amber,border:"none",borderRadius:10,padding:"10px 20px",cursor:"pointer",color:T.white,fontWeight:700,fontSize:14,fontFamily:"inherit"}}>Finish ✓</button>}
      </div>}
    </div>
  </div>;
}

// ── Personalise View ───────────────────────────────────────────
function PersonaliseView({base,onBack,onSave}) {
  const [form,setForm]=useState({studentName:"",pronouns:"they/them",ageGroup:"",strengths:"",notes:""});
  const [result,setResult]=useState(null),[loading,setLoading]=useState(false),[err,setErr]=useState(null);
  const [saving,setSaving]=useState(false),[isTemplate,setIsTemplate]=useState(false);
  const baseSentences=base.sentences||base.wizard_data?.sentences||[];

  const personalise=async()=>{
    setLoading(true);setErr(null);
    const pr=form.pronouns||"they/them";
    const [s,o,p]=pr==="he/him"?["he","him","his"]:pr==="she/her"?["she","her","her"]:["they","them","their"];
    const prompt=`You are a speech pathologist adapting a social story for a new student.
ORIGINAL STORY: ${JSON.stringify(baseSentences.map(s=>({type:s.type,text:s.text})))}
NEW STUDENT: ${form.studentName||"the student"} (${form.ageGroup||"primary age"}, pronouns ${s}/${o}/${p})
STRENGTHS/INTERESTS: ${form.strengths||"not specified"} | NOTES: ${form.notes||"none"}
TASK: Rewrite each sentence — substitute name/pronouns, weave in interests naturally, keep same sentence types and Carol Gray structure, same sentence count, stay positive and first-person.
Return ONLY JSON array: [{"type":"descriptive","text":"..."},...]`;
    try{
      const res=await fetch("https://api.anthropic.com/v1/messages",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({model:"claude-sonnet-4-20250514",max_tokens:1000,messages:[{role:"user",content:prompt}]})});
      const data=await res.json();
      const raw=data.content?.find(c=>c.type==="text")?.text||"";
      setResult(JSON.parse(raw.replace(/```json|```/g,"").trim()).map(s=>({...s,id:uid(),characterId:null})));
    }catch{setErr("Personalisation failed — try again.");}
    setLoading(false);
  };

  const save=async()=>{
    if(!result)return;setSaving(true);
    const beh=base.target_behaviour||base.targetBehaviour||"";
    const chars=base.characters||base.wizard_data?.characters||[];
    const rec={title:`${form.studentName||"My"}'s Story — ${beh}`,student_name:form.studentName||"",target_behaviour:beh,is_template:isTemplate,wizard_data:{...base.wizard_data||base,...form,studentName:form.studentName,pronouns:form.pronouns,ageGroup:form.ageGroup,strengths:form.strengths,sentences:result,characters:chars},sentences:result,characters:chars,created_at:new Date().toISOString(),updated_at:new Date().toISOString()};
    try{await sPost("social_stories",rec);onSave&&onSave();}catch{alert("Save failed.");}
    setSaving(false);
  };

  return <div>
    <div style={{display:"flex",alignItems:"center",gap:12,marginBottom:18}}>
      <button onClick={onBack} style={{background:"none",border:"none",cursor:"pointer",color:T.teal,fontWeight:700,fontSize:14,fontFamily:"inherit"}}>← Back</button>
      <div><h2 style={{color:T.teal,fontSize:20,fontWeight:800,marginBottom:2}}>🪄 Personalise with AI</h2><div style={{fontSize:13,color:T.sub}}>Base story: <strong>{base.title}</strong></div></div>
    </div>
    <Card style={{marginBottom:14,background:T.soft}}>
      <div style={{fontSize:12,fontWeight:700,color:T.sub,marginBottom:8}}>ORIGINAL SENTENCES</div>
      <div style={{display:"flex",flexDirection:"column",gap:5}}>
        {baseSentences.map((s,i)=><div key={i} style={{display:"flex",gap:8,alignItems:"flex-start",fontSize:13}}><Badge type={s.type}/><span style={{color:T.text,lineHeight:1.5}}>{s.text}</span></div>)}
      </div>
    </Card>
    <Card style={{marginBottom:14}}>
      <div style={{fontSize:12,fontWeight:700,color:T.sub,marginBottom:12}}>NEW STUDENT DETAILS</div>
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:12}}>
        <Field label="NAME"><Inp placeholder="Student name" value={form.studentName} onChange={e=>setForm({...form,studentName:e.target.value})}/></Field>
        <Field label="PRONOUNS"><div style={{display:"flex",gap:6,paddingTop:2}}>{PRONOUNS.map(p=><Chip key={p} label={p} selected={form.pronouns===p} onClick={()=>setForm({...form,pronouns:p})}/>)}</div></Field>
      </div>
      <Field label="AGE GROUP"><div style={{display:"flex",flexWrap:"wrap",gap:6}}>{AGE_GROUPS.map(a=><Chip key={a} label={a} selected={form.ageGroup===a} onClick={()=>setForm({...form,ageGroup:a})}/>)}</div></Field>
      <Field label="STRENGTHS / INTERESTS" hint="The more specific, the better — these get woven in naturally">
        <Txa placeholder="e.g. loves AFL, enjoys art, has a pet dog called Biscuit…" value={form.strengths} rows={2} onChange={e=>setForm({...form,strengths:e.target.value})}/>
      </Field>
      <Field label="ADDITIONAL NOTES (optional)" hint="AAC use, changed context, anything else for the AI to consider">
        <Txa placeholder="e.g. this student is a wheelchair user; please reflect that in movement descriptions…" value={form.notes} rows={2} onChange={e=>setForm({...form,notes:e.target.value})}/>
      </Field>
      <Btn variant="amber" onClick={personalise} disabled={loading||!form.studentName} style={{fontSize:14,padding:"10px 24px"}}>{loading?"🪄 Personalising…":"🪄 Personalise Story"}</Btn>
      {err&&<div style={{color:T.err,marginTop:8,fontSize:12}}>{err}</div>}
    </Card>
    {result&&<Card>
      <div style={{fontSize:12,fontWeight:700,color:T.sub,marginBottom:10}}>PERSONALISED FOR {form.studentName.toUpperCase()}</div>
      <div style={{display:"flex",flexDirection:"column",gap:6,marginBottom:16}}>
        {result.map((s,i)=><div key={i} style={{display:"flex",gap:8,alignItems:"flex-start",padding:"8px 10px",borderRadius:8,background:STYPES[s.type]?.bg||T.soft}}><Badge type={s.type}/><span style={{fontSize:13,color:T.text,lineHeight:1.5}}>{s.text}</span></div>)}
      </div>
      <div style={{display:"flex",gap:10,alignItems:"center",flexWrap:"wrap"}}>
        <label style={{display:"flex",alignItems:"center",gap:6,cursor:"pointer",fontSize:13,fontWeight:700,color:T.teal}}>
          <input type="checkbox" checked={isTemplate} onChange={e=>setIsTemplate(e.target.checked)} style={{width:15,height:15}}/> Save as template
        </label>
        <Btn variant="amber" onClick={save} disabled={saving}>{saving?"Saving…":"💾 Save to Library"}</Btn>
      </div>
    </Card>}
  </div>;
}

// ── Library View ───────────────────────────────────────────────
function LibraryView({onNew,onEdit,onPersonalise,onBook}) {
  const [stories,setStories]=useState([]),[loading,setLoading]=useState(true);
  const [staffChars,setStaffChars]=useState([]),[tab,setTab]=useState("all");
  const [scName,setScName]=useState(""),[scRole,setScRole]=useState(""),[scImg,setScImg]=useState(null),[scColor,setScColor]=useState(ACOLORS[0]),[scSaving,setScSaving]=useState(false);

  const load=async()=>{ setLoading(true); try{const[s,c]=await Promise.all([sGet("social_stories","?select=*&order=created_at.desc"),sGet("staff_characters","?select=*&order=name")]);setStories(Array.isArray(s)?s:[]);setStaffChars(Array.isArray(c)?c:[]);}catch{setStories([]);setStaffChars([]);} setLoading(false); };
  useEffect(()=>{load();},[]);

  const del=async id=>{if(!window.confirm("Delete this story?"))return;await sDel("social_stories",id);load();};
  const toggleTpl=async(id,cur)=>{await sPatch("social_stories",id,{is_template:!cur,updated_at:new Date().toISOString()});load();};
  const addSC=async()=>{if(!scName.trim())return;setScSaving(true);await sPost("staff_characters",{name:scName.trim(),role:scRole.trim(),image_data:scImg||null,color:scColor});setScName("");setScRole("");setScImg(null);await load();setScSaving(false);};
  const delSC=async id=>{await sDel("staff_characters",id);load();};
  const visible=tab==="templates"?stories.filter(s=>s.is_template):stories;

  return <div>
    <div style={{display:"flex",gap:6,marginBottom:18,borderBottom:`2px solid ${T.border}`,paddingBottom:8}}>
      {[["all","📚 All Stories"],["templates","⭐ Templates"],["staff","👥 Staff Library"]].map(([k,l])=>(
        <button key={k} onClick={()=>setTab(k)} style={{padding:"7px 16px",borderRadius:"8px 8px 0 0",fontSize:13,fontWeight:700,border:"none",cursor:"pointer",fontFamily:"inherit",background:tab===k?T.teal:"transparent",color:tab===k?T.white:T.sub}}>{l}</button>
      ))}
    </div>

    {tab==="staff"?(
      <div>
        <p style={{color:T.sub,fontSize:13,marginBottom:14}}>Upload staff cartoons once here — they'll appear as quick-add options when building any story.</p>
        <div style={{display:"flex",flexDirection:"column",gap:8,marginBottom:18}}>
          {staffChars.map(c=>(
            <Card key={c.id} style={{display:"flex",alignItems:"center",gap:12,padding:"10px 14px"}}>
              <Avatar char={{...c,imageUrl:c.image_data}} size={44}/>
              <div style={{flex:1}}><div style={{fontWeight:700,color:T.text}}>{c.name}</div><div style={{fontSize:12,color:T.slate}}>{c.role}</div></div>
              <button onClick={()=>delSC(c.id)} style={{background:"none",border:"none",cursor:"pointer",color:T.slate,fontSize:16}}>✕</button>
            </Card>
          ))}
          {staffChars.length===0&&<div style={{color:T.slate,fontSize:13,fontStyle:"italic",padding:"8px 0"}}>No staff characters yet.</div>}
        </div>
        <Card style={{background:T.tealLt,borderStyle:"dashed"}}>
          <div style={{fontWeight:700,color:T.teal,marginBottom:10}}>+ Add Staff Member</div>
          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10}}>
            <Field label="NAME"><Inp placeholder="e.g. Ms Chen" value={scName} onChange={e=>setScName(e.target.value)}/></Field>
            <Field label="ROLE"><Inp placeholder="e.g. LSO, Teacher" value={scRole} onChange={e=>setScRole(e.target.value)}/></Field>
          </div>
          <Field label="CARTOON IMAGE">
            <div style={{display:"flex",alignItems:"center",gap:10}}>
              <label style={{display:"inline-block",padding:"7px 14px",borderRadius:8,background:T.soft,color:T.teal,fontWeight:700,fontSize:12,cursor:"pointer",border:`1px solid ${T.border}`}}>
                {scImg?"✓ Image loaded":"Upload cartoon PNG/JPG"}<input type="file" accept="image/*" style={{display:"none"}} onChange={e=>{const f=e.target.files[0];if(!f)return;const r=new FileReader();r.onload=ev=>setScImg(ev.target.result);r.readAsDataURL(f);}}/>
              </label>
              {scImg&&<img src={scImg} alt="" style={{width:44,height:44,borderRadius:"50%",objectFit:"cover",border:`2px solid ${T.teal}`}}/>}
            </div>
          </Field>
          <Field label="COLOUR (if no image)"><div style={{display:"flex",gap:6}}>{ACOLORS.map(c=><button key={c} onClick={()=>setScColor(c)} style={{width:24,height:24,borderRadius:"50%",background:c,border:scColor===c?"3px solid #1a2e2e":"none",cursor:"pointer"}}/>)}</div></Field>
          <Btn onClick={addSC} disabled={!scName.trim()||scSaving}>{scSaving?"Saving…":"Add to Library"}</Btn>
        </Card>
      </div>
    ):(
      <>
        <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:14}}>
          <div style={{fontSize:13,color:T.sub,fontWeight:600}}>{visible.length} stor{visible.length===1?"y":"ies"}{tab==="templates"?" marked as templates":""}</div>
          <Btn variant="amber" onClick={onNew}>+ New Story</Btn>
        </div>
        {loading?<div style={{textAlign:"center",padding:40,color:T.slate}}>Loading…</div>
         :visible.length===0?<div style={{textAlign:"center",padding:40,color:T.slate,fontStyle:"italic"}}>No stories yet — create your first one!</div>:(
          <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fill,minmax(290px,1fr))",gap:12}}>
            {visible.map(s=>(
              <Card key={s.id} style={{display:"flex",flexDirection:"column",gap:10}}>
                <div>
                  {s.is_template&&<span style={{fontSize:10,fontWeight:800,padding:"2px 8px",borderRadius:10,background:T.amberLt,color:T.amber,border:`1px solid ${T.amberMid}`,display:"inline-block",marginBottom:6}}>⭐ TEMPLATE</span>}
                  <div style={{fontWeight:800,color:T.text,fontSize:15,lineHeight:1.3}}>{s.title}</div>
                  <div style={{fontSize:12,color:T.sub,marginTop:3}}>{s.target_behaviour}</div>
                </div>
                <div style={{fontSize:11,color:T.slate}}>{(s.sentences||[]).length} sentences · {new Date(s.created_at).toLocaleDateString("en-AU",{day:"numeric",month:"short",year:"numeric"})}</div>
                <div style={{display:"flex",gap:5,flexWrap:"wrap"}}>
                  <Btn variant="secondary" onClick={()=>onBook(s)} style={{padding:"5px 9px",fontSize:11}}>📱 Read</Btn>
                  <Btn variant="secondary" onClick={()=>onPersonalise(s)} style={{padding:"5px 9px",fontSize:11}}>🪄 Personalise</Btn>
                  <Btn variant="secondary" onClick={()=>onEdit(s)} style={{padding:"5px 9px",fontSize:11}}>✏️ Edit</Btn>
                  <button onClick={()=>toggleTpl(s.id,s.is_template)} style={{padding:"5px 9px",fontSize:13,background:"none",border:"none",cursor:"pointer",color:s.is_template?T.amber:T.slate}} title={s.is_template?"Remove template":"Mark as template"}>{s.is_template?"★":"☆"}</button>
                  <Btn variant="danger" onClick={()=>del(s.id)} style={{padding:"5px 9px",fontSize:11}}>🗑</Btn>
                </div>
              </Card>
            ))}
          </div>
        )}
      </>
    )}
  </div>;
}

// ── Root App ───────────────────────────────────────────────────
export default function App() {
  const [view,setView]=useState("library");
  const [bookStory,setBookStory]=useState(null);
  const [wizardBase,setWizardBase]=useState(null);
  const [personaliseBase,setPersonaliseBase]=useState(null);
  const [staffChars,setStaffChars]=useState([]);

  useEffect(()=>{
    if(view==="wizard") sGet("staff_characters","?select=*&order=name").then(r=>setStaffChars(Array.isArray(r)?r:[])).catch(()=>{});
  },[view]);

  const openEdit=s=>{setWizardBase({...s.wizard_data||s,id:s.id,storyTitle:s.title,is_template:s.is_template,characters:s.characters||s.wizard_data?.characters||[],sentences:s.sentences||s.wizard_data?.sentences||[]});setView("wizard");};

  return <div style={{minHeight:"100vh",background:T.bg,fontFamily:"'Nunito','Segoe UI',system-ui,sans-serif"}}>
    <div style={{background:`linear-gradient(135deg,${T.teal},${T.teal2})`,padding:"15px 26px",display:"flex",alignItems:"center",justifyContent:"space-between",boxShadow:`0 2px 16px ${T.teal}22`}}>
      <div style={{display:"flex",alignItems:"center",gap:10}}>
        {view!=="library"&&<button onClick={()=>setView("library")} style={{background:"rgba(255,255,255,.15)",border:"none",borderRadius:8,padding:"6px 12px",color:T.white,cursor:"pointer",fontSize:12,fontWeight:700,fontFamily:"inherit"}}>← Library</button>}
        <div>
          <div style={{fontSize:18,fontWeight:900,color:T.white,letterSpacing:"-.3px"}}>📖 Social Story Builder</div>
          <div style={{fontSize:11,color:T.tealLt}}>CLC · Learning & Behaviour Unit</div>
        </div>
      </div>
      <div style={{display:"flex",gap:8,alignItems:"center"}}>
        {!configured&&<div style={{fontSize:11,background:"rgba(245,166,35,.3)",color:"#fff8ec",padding:"4px 10px",borderRadius:8,border:"1px solid rgba(245,166,35,.5)"}}>⚠️ Supabase not configured</div>}
        {view==="library"&&<Btn variant="amber" onClick={()=>{setWizardBase(null);setView("wizard");}}>+ New Story</Btn>}
      </div>
    </div>
    <div style={{maxWidth:830,margin:"0 auto",padding:"22px 14px"}}>
      {view==="library"&&<LibraryView onNew={()=>{setWizardBase(null);setView("wizard");}} onEdit={openEdit} onPersonalise={s=>{setPersonaliseBase(s);setView("personalise");}} onBook={s=>setBookStory(s)}/>}
      {view==="wizard"&&<WizardView initial={wizardBase} onSave={()=>setView("library")} onBook={s=>setBookStory(s)} staffChars={staffChars}/>}
      {view==="personalise"&&<PersonaliseView base={personaliseBase} onBack={()=>setView("library")} onSave={()=>setView("library")}/>}
    </div>
    {bookStory&&<BookView story={bookStory} onClose={()=>setBookStory(null)}/>}
  </div>;
}
