const fs=require("fs"),path=require("path"),H=require("./harness.js");
const COURSES=JSON.parse(fs.readFileSync(path.join(__dirname,"..","site","data","courses.json"),"utf8"));
(async()=>{const tmp=path.join(__dirname,"sw.db");fs.copyFileSync(path.join(__dirname,"base.db"),tmp);
const JS=await new H.JsServer(tmp).init();let tok=null;
async function c(m,u,b){const r=await JS.request(tok,m,u,b,"id");if(r.ctx&&r.ctx.setCookie)tok=r.ctx.setCookie[0];return r.body;}
const R=[];const chk=(n,ok,i)=>{R.push([n,!!ok,i||""]);console.log((ok?"LULUS ":"GAGAL ")+n,i||"");};
await c("POST","/api/auth/login",{email:"student@metta.sch",password:"Student#2026!",role:"student"});
const cur=(await c("GET","/api/student/plan")).plan;
const ids=Object.keys(COURSES).map(Number).filter(x=>x!==cur.career_id);const A=ids[0],B=ids[1];
const tasks=p=>p.milestones.flatMap(m=>m.tasks);
await c("POST","/api/student/plan",{career_id:A});let pA=await c("GET","/api/student/plan");
for(const t of tasks(pA).slice(0,2)){const l=await c("GET","/api/student/learn/"+t.id);for(let i=0;i<(l.steps||[]).length;i++)await c("POST","/api/student/learn/"+t.id+"/step",{idx:i,done:true});await c("PATCH","/api/student/tasks/"+t.id,{status:"COMPLETED"});}
pA=await c("GET","/api/student/plan");const doneA=tasks(pA).filter(t=>t.status==="COMPLETED").length;
const dA=await c("GET","/api/student/dashboard");const cA=await c("GET","/api/student/course");
chk("Plan A aktif, ada tugas selesai",pA.plan.career_id===A&&doneA>=1,pA.plan.career+", "+doneA+" tugas selesai, kursus="+cA.career);
await c("POST","/api/student/plan",{career_id:B});const pB=await c("GET","/api/student/plan");
const dB=await c("GET","/api/student/dashboard");const cB=await c("GET","/api/student/course");
const idsA=new Set(tasks(pA).map(t=>t.id));
chk("Ganti ke B: plan, tugas, kursus, dashboard ikut B",pB.plan.career_id===B&&cB.career===pB.plan.career&&dB.target===pB.plan.career&&!tasks(pB).some(t=>idsA.has(t.id))&&tasks(pB).every(t=>t.status!=="COMPLETED"),"target="+dB.target+", kesiapan="+dB.readiness+"%");
await c("POST","/api/student/plan",{career_id:A});const pA2=await c("GET","/api/student/plan");const dA2=await c("GET","/api/student/dashboard");
chk("Kembali ke A: progres pulih",pA2.plan.career_id===A&&tasks(pA2).filter(t=>t.status==="COMPLETED").length===doneA&&dA2.readiness===dA.readiness,doneA+" tugas, kesiapan "+dA2.readiness+"%");
const re=await JS.replayFresh();const a=H.dump(JS.a),b=H.dump(re);[a,b].forEach(d=>d.users.forEach(u=>delete u.last_active_at));
chk("Replay database artifact identik",JSON.stringify(a.plans)===JSON.stringify(b.plans)&&JSON.stringify(a.tasks)===JSON.stringify(b.tasks));
fs.writeFileSync(process.argv[2]||"/dev/null",JSON.stringify(R));console.log("TOTAL",R.filter(r=>r[1]).length,"/",R.length);fs.unlinkSync(tmp);})();
