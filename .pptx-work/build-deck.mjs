import fs from 'node:fs/promises';
import path from 'node:path';
import { FileBlob, PresentationFile } from '@oai/artifact-tool';

const source = 'C:/Users/MKREDDY/Downloads/Submission Template _ AI Builder Cup.pptx';
const workspace = 'C:/Users/MKREDDY/AI_builder_cup/foodbridge_v2';
const privateDir = path.join(workspace, '.pptx-work');
const outputDir = path.join(workspace, 'submission-output');
const candidate = path.join(privateDir, 'candidate.pptx');
const finalPath = path.join(outputDir, 'FoodBridge_RescueFlow_AI_Builder_Cup.pptx');
await fs.mkdir(outputDir, { recursive: true });
const p = await PresentationFile.importPptx(await FileBlob.load(source));

function addText(slide, text, pos, opts={}) {
  const shape = slide.shapes.add({
    geometry: 'textbox', name: opts.name ?? 'Submission content', position: pos,
    fill: 'none', line: { style: 'solid', fill: 'none', width: 0 },
  });
  shape.text = text;
  shape.text.style = {
    typeface: 'Google Sans Flex', fontSize: opts.size ?? 20,
    color: opts.color ?? '#202124', alignment: opts.align ?? 'left',
    verticalAlignment: 'top', wrap: 'square', autoFit: 'shrinkText',
    insets: opts.insets ?? 2,
  };
  return shape;
}
function addTitle(slide, id, title) { p.resolve(id).text = title; }
function body(i, text, pos={left:48,top:148,width:864,height:355}, opts={}) {
  addText(p.slides.items[i], text, pos, opts);
}
function card(slide, title, text, x, y, w, h, accent='#E8F2FB') {
  slide.shapes.add({ geometry:'roundRect', name:title, position:{left:x,top:y,width:w,height:h}, fill:accent, line:{style:'solid',fill:'#C7D9E8',width:1} });
  addText(slide, `${title}\n${text}`, {left:x+10,top:y+8,width:w-20,height:h-16}, {size:16,align:'center',insets:0});
}

// Cover: retain the template artwork and complete the requested team block.
const cover = p.resolve('sh/kvqx0vqd');
cover.text = 'Team Details\n\nTeam name: ProblemSolvers\nTeam leader: Manoj Srinivasan\nTeam members: Murali Krishna Reddy Gajulapalli, Sushil Subedi, Vasanth K Potturu\nProject: RescueFlow AI by FoodBridge';
cover.text.style = { typeface:'Google Sans Flex', fontSize:23, color:'#111111', verticalAlignment:'top', autoFit:'shrinkText', wrap:'square' };

// Replace the template's instruction page with a concise problem statement.
const instructions = p.resolve('sh/ihozedgj');
try { p.resolve('im/e9wz29wz').delete(); } catch {}
// The original slide uses a fixed small textbox; cover its instructional layout and
// rebuild the message at readable size while preserving the black event backdrop.
p.slides.items[1].shapes.add({geometry:'rect',name:'Problem slide background',position:{left:45,top:80,width:870,height:390},fill:'#000000',line:{style:'solid',fill:'none',width:0}});
addText(p.slides.items[1],'THE RECOVERY GAP',{left:90,top:130,width:780,height:55},{size:32,color:'#FFFFFF',align:'center'});
addText(p.slides.items[1],'Surplus food is time-sensitive. A decline, capacity mismatch, or unanswered invitation can leave safe food unclaimed while the pickup deadline approaches.\n\nRescueFlow continues matching after the first offer and routes remaining portions to the next feasible recipient.',{left:130,top:215,width:700,height:185},{size:24,color:'#FFFFFF',align:'center'});

// Idea and opportunity.
addTitle(p.slides.items[2], 'sh/8bahkrmt', 'RescueFlow AI by FoodBridge');
body(2, 'An AI-assisted surplus food recovery workflow for donors and recipient organizations.\n\nDonors publish prepared food with portions, dietary details, pickup location, and a deadline. RescueFlow finds eligible recipients, ranks feasible offers, and keeps rematching any quantity that remains available.\n\nThe system combines deterministic allocation rules with Gemini-generated explanations. The model explains decisions; it does not decide eligibility or allocate food.');

addTitle(p.slides.items[3], 'sh/3ilwvqpw', 'Opportunity and differentiation');
body(3, 'THE CHALLENGE\nA single unanswered or declined offer can stall a donation even when other recipients could collect it in time. Manual follow-up also makes it difficult to track partial quantities and pickup completion.\n\nOUR APPROACH\n• Filter for recipient eligibility, capacity, food preferences, and pickup timing.\n• Rank feasible offers using a transparent score: deadline 35%, capacity 30%, distance 20%, preferences 15%. Distance is a synthetic demo estimate, not live routing.\n• Revalidate and reserve portions on acceptance; a decline does not consume stock.\n• Expire timed-out offers and rematch remaining portions before the pickup deadline.\n\nUSP: explainable recovery with auditable state changes and pickup tracking kept separate from allocation.', {left:48,top:145,width:864,height:360},{size:18});

// Features.
addTitle(p.slides.items[4], 'sh/4r6l4n29', 'Features offered by the solution');
body(4, '01  Donation publishing — food type, quantity, dietary details, pickup location, and deadline.\n\n02  Eligibility and ranking — hard filters first, then a weighted feasibility score.\n\n03  Safe portion allocation — acceptance revalidates stock and recipient capacity before reserving.\n\n04  Recovery loop — declines and expired invitations return the remaining quantity to matching; a scheduled worker handles timeouts.\n\n05  Pickup tracking — confirmation and completion are recorded after allocation.\n\n06  Operations and trust — admin recovery queue, audit events, recipient review, and donor feedback.\n\n07  AI explanations — Gemini summarizes why an offer is feasible; matching remains deterministic.', {left:48,top:145,width:864,height:360},{size:18});

// Process flow: editable cards and labels, focused on the user-provided flow.
addTitle(p.slides.items[5], 'sh/gzy1oz21', 'Donation, response, and rematch flow');
const s6=p.slides.items[5];
card(s6,'Publish','Donor posts surplus\nwith pickup deadline',55,155,185,70);
card(s6,'Find & rank','Filter eligible recipients;\nrank feasible offers',285,155,195,70);
card(s6,'Invite','Send offer with quantity\nand response deadline',525,155,180,70);
card(s6,'Recipient response','Accept, decline,\nor time out',750,155,160,70,'#EAF3F8');
addText(s6,'→',{left:243,top:173,width:35,height:35},{size:26,align:'center'});
addText(s6,'→',{left:485,top:173,width:35,height:35},{size:26,align:'center'});
addText(s6,'→',{left:708,top:173,width:36,height:35},{size:26,align:'center'});
card(s6,'Accept','Revalidate quantity and capacity;\nreserve portions',90,285,245,78,'#DCEEFE');
card(s6,'Pickup','Track confirmation\nand completion separately',355,285,245,78,'#DCEEFE');
card(s6,'Decline / timeout','Record response or expire offer;\nkeep unaccepted stock available',630,285,265,78,'#FFF1DF');
addText(s6,'If portions remain and the deadline is open: recalculate feasible allocations → rank → invite the next recipient.\nIf the pickup deadline passes: expire the remaining quantity. No response path silently marks pickup complete.',{left:72,top:397,width:820,height:80},{size:17,align:'center'});

// Replace optional wireframes with clear role/use-case coverage, avoiding fake screenshots.
addTitle(p.slides.items[6], 'sh/w3e9sri9', 'Workspaces and primary use cases');
const s7=p.slides.items[6];
card(s7,'Donor workspace','Publish a donation, set pickup details, review active offers, and follow allocation and pickup status.',55,165,260,180);
card(s7,'Recipient workspace','Review ranked invitations, see suggested quantities and capacity, then accept or decline before the response deadline.',350,165,260,180);
card(s7,'Admin dashboard','Monitor recovery queue and audit history, inspect rematches, and review donor feedback and operating status.',645,165,260,180);
addText(s7,'The deployed prototype link is provided on the links slide. These are workflow summaries, not product screenshots.',{left:90,top:385,width:780,height:48},{size:16,align:'center',color:'#5F6368'});

// Architecture: editable layout.
addTitle(p.slides.items[7], 'sh/ob21036t', 'RescueFlow architecture');
const s8=p.slides.items[7];
card(s8,'React + TypeScript UI','Donor • Recipient • Admin workspaces',55,160,250,75);
card(s8,'FastAPI service on Cloud Run','REST API • validation • audit events',355,160,250,75);
card(s8,'Cloud SQL PostgreSQL','Donations • recipients • invitations\nallocations • reviews • audit log',655,160,250,75);
addText(s8,'→',{left:311,top:179,width:36,height:35},{size:26,align:'center'});
addText(s8,'→',{left:611,top:179,width:36,height:35},{size:26,align:'center'});
card(s8,'Deterministic matching','Eligibility filters, weighted ranking,\nrevalidation, and portion reservation',70,290,250,78,'#EAF3F8');
card(s8,'Vertex AI Gemini','Optional, bounded explanation of\nranked matches and recovery state',355,290,250,78,'#EAF3F8');
card(s8,'Timeout worker','Cloud Run Job invoked by Cloud Scheduler;\nexpires due invitations and rematches',640,290,265,78,'#EAF3F8');
addText(s8,'Matching writes are guarded by database transactions/locking. The timeout worker uses the same backend image and database configuration. Gemini is an explanation layer, not the allocation authority.',{left:75,top:410,width:810,height:55},{size:16,align:'center'});

// Technology stack.
addTitle(p.slides.items[8], 'sh/w3y9kfut', 'Technology stack');
body(8, 'FRONT END\nReact · TypeScript · Vite\n\nBACK END\nPython · FastAPI · SQLAlchemy\n\nDATA\nPostgreSQL on Cloud SQL; SQLite supports local/demo workflows.\n\nAI\nVertex AI Gemini for concise, grounded explanations. Deterministic backend logic owns matching and reservation.\n\nGOOGLE CLOUD DEPLOYMENT\nCloud Run API service · Cloud Run timeout job · Cloud Scheduler · Artifact Registry · Secret Manager', {left:75,top:145,width:810,height:355},{size:20});

// Costs: no invented prices.
addTitle(p.slides.items[9], 'sh/nedo7up8', 'Prototype cost model');
body(9, 'Usage-based components\n• Cloud Run API and timeout job compute\n• Cloud SQL instance and storage\n• Vertex AI Gemini calls when an explanation is requested\n• Cloud Scheduler executions and supporting logging\n\nNo verified bill of materials or measured monthly spend is available for this prototype. Before a pilot, enable billing reports and measure traffic, database sizing, and Gemini usage against the expected donation volume.', {left:75,top:155,width:810,height:300},{size:20});

// Prototype evidence slide: do not represent illustrations as screenshots.
addTitle(p.slides.items[10], 'sh/ixknidwn', 'Prototype workflows');
const s11=p.slides.items[10];
card(s11,'Publish & match','Create donation → filter and rank eligible recipients → issue a portion offer.',65,165,250,145);
card(s11,'Respond & reserve','Recipient accepts or declines → revalidate capacity and remaining portions → record result.',355,165,250,145);
card(s11,'Recover & complete','Timeout job rematches remaining portions → donor/recipient track pickup completion.',645,165,250,145);
addText(s11,'Live prototype: foodbridge-ui-pfkvaq3icq-el.a.run.app\nThe repository and product links are on the next slides. Add original product screenshots before final submission if the event reviewer requires visual evidence.',{left:85,top:350,width:790,height:90},{size:17,align:'center',color:'#3C4043'});

// Performance evidence, explicitly distinguishing functional checks from benchmarks.
addTitle(p.slides.items[11], 'sh/d8jipcja', 'Reliability evidence and benchmark status');
body(11, 'FUNCTIONAL SAFEGUARDS\n• Allocation is revalidated against remaining stock and recipient capacity.\n• Declines and expired invitations preserve unaccepted portions for rematching.\n• Pickup completion remains a separate state from allocation.\n• Audit events record donation, invitation, response, and recovery transitions.\n\nBENCHMARK STATUS\nNo formal latency, throughput, or load-test results are available yet. The current demo uses synthetic recipient profiles and synthetic distance estimates. A pilot should measure API latency, timeout sweep duration, rematch success, accepted portions, and completed pickups.', {left:68,top:145,width:824,height:350},{size:19});

// Roadmap.
addTitle(p.slides.items[12], 'sh/za90r298', 'Next development steps');
body(12, '1  Replace synthetic distance with live routing and pickup-time estimates.\n\n2  Add reliable email/SMS notifications and recipient response reminders.\n\n3  Strengthen production identity, organization onboarding, and role-based access.\n\n4  Run a small donor/recipient pilot; measure portions offered, accepted, picked up, and recovered after a decline or timeout.\n\n5  Improve operational monitoring for scheduled sweeps, Gemini availability, and database health.', {left:75,top:155,width:810,height:320},{size:20});

// Links: preserve project link and use the known deployed URL; flag missing demo video.
const s14=p.slides.items[13];
// The imported template link box has tightly formatted 10px paragraphs. Cover its
// body and add larger editable links, leaving the shared black header/footer intact.
s14.shapes.add({geometry:'rect',name:'Links content background',position:{left:0,top:54,width:960,height:478},fill:'#FFFFFF',line:{style:'solid',fill:'none',width:0}});
addText(s14,'Project links',{left:38,top:70,width:880,height:45},{size:25});
addText(s14,'GitHub repository\nhttps://github.com/murali7032/RescueFlow-AI\n\nLive prototype\nhttps://foodbridge-ui-pfkvaq3icq-el.a.run.app\n\nDemo video (3 minutes)\nAdd the recorded demo URL before submission.',{left:65,top:145,width:830,height:260},{size:21});

// Empty template slide becomes a truthful pilot scorecard.
const s15=p.slides.items[14];
addText(s15,'Pilot success measures',{left:28,top:69,width:900,height:55},{size:23,color:'#202124'});
body(14,'Track these outcomes during a real pilot\n\n• Portions offered, accepted, and confirmed picked up\n• Share of declined or timed-out offers successfully rematched before deadline\n• Time from donation publication to accepted allocation\n• Pickup completion rate and reasons for failed collection\n• Donor and recipient feedback over repeat uses\n\nThese are proposed measures; no real-world impact results are claimed yet.',{left:75,top:155,width:810,height:315},{size:20});

await (await PresentationFile.exportPptx(p)).save(candidate);
console.log(JSON.stringify({candidate, finalPath, slideCount:p.slides.items.length, slideSize:p.slideSize}));
