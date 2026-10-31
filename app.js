(function(){
'use strict';
const $=(q)=>document.querySelector(q);
const esc=(v)=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const safeUrl=(u)=>{try{let p=new URL(u);return p.protocol==='https:'||p.protocol==='http:'?p.href:'#'}catch{return '#'}};
const dateFmt=(d)=>{try{return new Date(d+'T12:00:00').toLocaleDateString('en-US',{month:'short',day:'numeric'})}catch{return ''}};
// V3: An offline, readable cover renders instantly. The matching external
// YouTube image (when an ID exists) or the article cover replaces it on load.
// This keeps a single-file prototype usable when preview apps block remote images.
const youtubeId = (it)=>it.video?.provider==='youtube' && /^[\w-]{11}$/.test(it.video.id)?it.video.id:null;
function remoteThumbnailList(it){
  const urls=[];const id=youtubeId(it);
  if(id){
    // Real YouTube CDN thumbnails. Choose the best available on each device,
    // and don't leave a broken image if one resolution is unavailable.
    urls.push(`https://i.ytimg.com/vi/${id}/maxresdefault.jpg`);
    urls.push(`https://i.ytimg.com/vi/${id}/sddefault.jpg`);
    urls.push(`https://i.ytimg.com/vi/${id}/hqdefault.jpg`);
    urls.push(`https://img.youtube.com/vi/${id}/hqdefault.jpg`);
  }
  if(it.image)urls.push(safeUrl(it.image));
  if(it.image_fallback)urls.push(safeUrl(it.image_fallback));
  return [...new Set(urls.filter(u=>u&&u!=='#'))];
}
function previewCover(it){
  const s=(v)=>String(v||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'}[c]));
  const tag=it.tags?.[0]||'Fishing Tips';
  const colors={Redfish:['#152c52','#244f78'],Tides:['#112d52','#366587'],Lures:['#172d56','#42568e'],Rigging:['#17345f','#306e8c'],'Gear Tests':['#263857','#607992'],Structure:['#112e4a','#32627a'],Flounder:['#142e4e','#32617a']};
  const [a,b]=colors[tag]||['#152c52','#366582'];
  const title=String(it.title||'Fishing lesson').replace(/\s+/g,' ').trim();
  let words=title.split(' '),lines=[],current='';
  for(const w of words){if((current+' '+w).trim().length>25&&current&&lines.length<3){lines.push(current);current=w}else{current=(current+' '+w).trim()}}
  if(current)lines.push(current);
  if(lines.length>3){lines=lines.slice(0,3);lines[2]=lines[2].slice(0,23)+'…'}
  const lineSVG=lines.map((t,i)=>`<text x="68" y="${282+i*70}" fill="white" font-family="Arial,sans-serif" font-size="53" font-weight="800">${s(t)}</text>`).join('');
  const svg=`<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="675" viewBox="0 0 1200 675">
<defs><linearGradient id="g"><stop stop-color="${a}"/><stop offset="1" stop-color="${b}"/></linearGradient><pattern id="p" width="120" height="120" patternUnits="userSpaceOnUse"><path d="M0 80 Q60 20 120 80" fill="none" stroke="#b4d6ed" stroke-width="2" opacity=".17"/></pattern></defs>
<rect width="1200" height="675" fill="url(#g)"/><rect width="1200" height="675" fill="url(#p)"/>
<circle cx="1120" cy="90" r="370" fill="none" stroke="#d6e6f2" opacity=".11" stroke-width="64"/><circle cx="1120" cy="90" r="245" fill="none" stroke="#d6e6f2" opacity=".12" stroke-width="22"/>
<rect x="0" y="0" width="14" height="675" fill="#ff5100"/>
<rect x="68" y="58" width="300" height="56" rx="11" fill="#fff" opacity=".97"/>
<text x="90" y="97" fill="#152c52" font-family="Arial,sans-serif" font-size="27" font-weight="900" letter-spacing="2">SALT STRONG WATCH</text>
<text x="68" y="188" fill="#ffb187" font-family="Arial,sans-serif" font-size="25" font-weight="800" letter-spacing="2">${s(tag.toUpperCase())} · LESSON COVER</text>
${lineSVG}
<line x1="68" x2="1134" y1="568" y2="568" stroke="#cbdfe9" opacity=".45" stroke-width="2"/>
<text x="68" y="618" fill="#e0edf7" font-family="Arial,sans-serif" font-size="26" font-weight="600">${s(it.author||'Salt Strong')}</text>
<text x="1133" y="618" fill="#ffb187" font-family="Arial,sans-serif" font-size="23" font-weight="700" text-anchor="end">THUMBNAIL PREVIEW</text>
</svg>`;
  return 'data:image/svg+xml;charset=utf-8,'+encodeURIComponent(svg);
}
function thumb(it,cls=''){
  const fallback=previewCover(it),remote=remoteThumbnailList(it);
  return `<img class="${esc(cls)}" src="${esc(fallback)}" data-remote-sources="${esc(JSON.stringify(remote))}" data-thumb-kind="preview" loading="eager" alt="${esc(it.title||'Fishing lesson')} cover"/>`;
}
function loadRemoteThumbnail(img){
  if(img.dataset.thumbAttempted)return;
  img.dataset.thumbAttempted='1';
  let urls;try{urls=JSON.parse(img.dataset.remoteSources||'[]')}catch{urls=[]}
  let index=0;
  function next(){
    if(index>=urls.length||!img.isConnected)return;
    const url=urls[index++],test=new Image();
    test.onload=()=>{
      // YouTube uses a tiny generic image if a resolution does not exist.
      if(test.naturalWidth<300||test.naturalHeight<150){next();return}
      if(img.isConnected){img.src=url;img.dataset.thumbKind=url.includes('ytimg.com')?'youtube':'article';}
    };
    test.onerror=next;
    test.src=url;
  }
  next();
}
const thumbnailObserver=typeof IntersectionObserver!=='undefined'?new IntersectionObserver(entries=>{
  for(const e of entries)if(e.isIntersecting){thumbnailObserver.unobserve(e.target);loadRemoteThumbnail(e.target)}
},{rootMargin:'350px'}):null;
function hydrateThumbnails(scope=document){
  for(const img of scope.querySelectorAll('img[data-remote-sources]:not([data-thumb-attempted])')){
    if(thumbnailObserver)thumbnailObserver.observe(img);else loadRemoteThumbnail(img);
  }
}

const app=$('#app');let items=[],source='sample',view='home',filter='All',search='',sort='newest',selected=null;
let saved=new Set();try{saved=new Set(JSON.parse(localStorage.getItem('ss_watch_saved')||'[]'))}catch{}
const topics=['All','Redfish','Seatrout','Snook','Flounder','Marshes','Oyster Bars','Tides','Structure','Lures','Rigging','Gear Tests'];
const icons={All:'✳',Redfish:'🐟',Seatrout:'〰',Snook:'↝',Flounder:'◈',Marshes:'♧','Oyster Bars':'◉',Tides:'≈',Structure:'⌖',Lures:'◆',Rigging:'⌁','Gear Tests':'⚗'};
function setView(v){view=v;document.querySelectorAll('.navbtn').forEach(b=>b.classList.toggle('active',b.dataset.view===v));render();window.scrollTo({top:0,behavior:'smooth'})}
function matches(it){const s=search.trim().toLowerCase();let fields=[it.title,it.author,it.excerpt,(it.tags||[]).join(' '),it.search_text||''].join(' ').toLowerCase();const okSearch=!s||s.split(/\s+/).every(k=>fields.includes(k));const okTag=filter==='All'||(it.tags||[]).includes(filter)||(filter==='Oyster Bars'&&fields.includes('oyster'));return okSearch&&okTag}
function sorted(a){return [...a].sort((x,y)=>sort==='az'?x.title.localeCompare(y.title):sort==='oldest'?String(x.date).localeCompare(String(y.date)):String(y.date).localeCompare(String(x.date)))}
function card(it){let isSaved=saved.has(String(it.id));return `<article class="video-card"><button class="poster" data-open="${esc(it.id)}" aria-label="Open ${esc(it.title)}">${thumb(it)}<span class="play" aria-hidden="true">▶</span><span class="cardbadge">${esc(it.tags?.[0]||'Fishing Tips')}</span></button><div class="card-body"><a class="card-title" href="${esc(safeUrl(it.url))}" target="_blank" rel="noopener">${esc(it.title)}</a><div class="cardline"><span>${esc(it.author||'Salt Strong')} · ${esc(dateFmt(it.date))}</span><button class="savebtn ${isSaved?'saved':''}" data-save="${esc(it.id)}" title="${isSaved?'Remove from saved':'Save for later'}" aria-label="${isSaved?'Remove from saved':'Save'} ${esc(it.title)}">${isSaved?'♥':'♡'}</button></div></div></article>`}
function reelSection(title,subtitle,subset,tag){if(!subset.length)return '';return `<section class="section"><div class="sectionhead"><div><h2>${esc(title)}</h2><p>${esc(subtitle)}</p></div><button class="sectionlink" data-browse-tag="${esc(tag||'All')}">Explore all →</button></div><div class="reel">${sorted(subset).map(card).join('')}</div></section>`}
function chips(){return `<div class="chips">${topics.map(t=>`<button class="chip ${filter===t?'active':''}" data-tag="${esc(t)}" aria-pressed="${filter===t}"><span>${icons[t]}</span>${esc(t)}</button>`).join('')}</div>`}
function coursesBanner(){return `<section class="section"><div class="upsell"><div><div class="eyebrow"><span class="dot"></span> KEEP LEARNING</div><h2>Go deeper with Salt Strong courses</h2><p>From a quick fishing tip to step-by-step instruction. Discover courses with purchase options and access that varies by Insider and VIP membership.</p></div><button class="secondary" data-view="courses">Explore courses →</button></div></section>`}
function home(){let feat=items.find(x=>x.id==='marshes')||items[0];if(!feat)return emptyPage();return `<section class="hero">${thumb(feat,'heroimg')}<div class="shell"><div class="hero-copy"><div class="eyebrow"><span class="dot"></span> LEARN MORE. SEARCH LESS. CATCH MORE.</div><h1>All the fishing know-how.<br/><em>One place.</em></h1><p>Find the exact Salt Strong lesson you need, whether you're planning a trip, rigging a lure, or just looking for your next big idea.</p><div class="metarow"><span class="tag author">Featured: ${esc(feat.author||'Salt Strong')}</span><span class="tag">${esc(feat.tags?.[0]||'Fishing tips')}</span><span class="tag">New lessons from your existing blogs</span></div><div class="actions"><button class="primary" data-open="${esc(feat.id)}">▶ View featured lesson</button><button class="secondary" data-view="browse">Browse the library →</button></div><div class="tiny hero-note">Featured lesson: ${esc(feat.title)}</div></div></div><div class="hero-count">${source==='live'?'Live WordPress catalog':'10 public article examples'} · Demo</div></section><main class="shell"><div class="chooser"><div class="sectionhead"><div><h2>What do you want to learn?</h2><p>Choose a topic or search for something specific.</p></div><button class="sectionlink" data-view="browse">All topics →</button></div>${chips()}<p class="tip">Try it: select <b>Oyster Bars</b> or search <b>popping cork</b>. Results update instantly.</p></div>${reelSection('Fresh from the water','Recent public Salt Strong lessons, pulled from the article catalog.',items.slice(0,7),'All')}${reelSection('Find fish faster','Structure, tides, water movement, and where fish position.',items.filter(x=>x.tags.some(t=>['Structure','Tides','Marshes','Oyster Bars'].includes(t))),'Structure')}${reelSection('Lures, rigging & experiments','Practical techniques and gear knowledge you can use on your next trip.',items.filter(x=>x.tags.some(t=>['Lures','Rigging','Gear Tests'].includes(t))),'Lures')}${coursesBanner()}<section class="section"><div class="sectionhead"><div><h2>Learn from your favorite coach</h2><p>Jump straight to lessons with Luke, Pat, or Tony.</p></div></div><div class="coach-row">${['Luke Simonds','Pat Ogletree','Tony Acevedo'].map(n=>`<button class="coach" data-coach="${esc(n)}">${esc(n.split(' ')[0])}<span>${items.filter(i=>i.author===n).length} sample lessons →</span></button>`).join('')}</div></section></main>`}
function emptyPage(){return `<main class="shell"><div class="empty" style="margin-top:40px"><strong>No lessons loaded</strong>Check that the catalog is available.</div></main>`}
function browse(){let a=sorted(items.filter(matches));return `<main class="shell"><div class="subhero"><div class="eyebrow"><span class="dot"></span> SEARCH FIRST. FISH SMARTER.</div><h1>${search?'Search results':'All fishing lessons'}</h1><p>Forget hunting through blog archives. Filter by species, conditions, tackle, or what you're trying to learn. Every lesson stays connected to its original Salt Strong article.</p></div><div class="filterbar">${chips()}</div><div class="resultsbar"><span><b>${a.length}</b> lesson${a.length===1?'':'s'} ${search?'matching “'+esc(search)+'”':''}</span><select id="sort" class="sort" aria-label="Sort videos"><option value="newest" ${sort==='newest'?'selected':''}>Newest first</option><option value="oldest" ${sort==='oldest'?'selected':''}>Oldest first</option><option value="az" ${sort==='az'?'selected':''}>A–Z</option></select></div>${a.length?`<div class="gridcards">${a.map(card).join('')}</div>`:`<div class="empty"><strong>No exact matches yet.</strong>Try another species, a technique, or clear the current filters.<p><button class="primary" data-reset>Clear filters</button></p></div>`}</main>`}
function quick(){let a=sorted(items.filter(matches));return `<main class="shell"><div class="subhero"><div class="eyebrow"><span class="dot"></span> MOBILE-FIRST EXPLORATION</div><h1>Quick Browse</h1><p>A swipe-friendly way to discover a lesson while you're on the move. <b>Concept mode:</b> these preview cards link to existing long-form articles. Actual vertical shorts will appear here only after they're identified in the imported catalog.</p></div><div class="shorts">${a.slice(0,8).map(it=>`<button class="shortcard" data-open="${esc(it.id)}">${thumb(it)}<span class="shortbadge">Lesson preview</span><span class="shortcopy"><strong>${esc(it.title)}</strong><span>${esc(it.author||'Salt Strong')}</span><span>Open lesson →</span></span></button>`).join('')}</div>${a.length?'':'<div class="empty">No matching lessons.</div>'}</main>`}
function courses(){return `<main class="shell"><div class="subhero"><div class="eyebrow"><span class="dot"></span> PREMIUM LEARNING</div><h1>Learn it. Practice it. Master it.</h1><p>This is a proposed surface for the existing course catalog, not a rebuild of the course platform. Final cards would be sourced from a separate verified course feed with access and pricing determined by the actual course system.</p></div><div class="coursegrid"><div class="coursecard"><div><span class="badge">Course Discovery · Concept</span><h3>Learn the complete system</h3><p>Free fishing lessons could recommend relevant paid courses, helping anglers find more structured learning when they're ready for it.</p></div><a class="secondary" style="align-self:flex-start" href="https://www.saltstrong.com/my-courses/" target="_blank" rel="noopener">Visit existing course area ↗</a></div><div class="coursecard" style="background:linear-gradient(125deg,#193342,#23382a)"><div><span class="badge">Entitlement-Aware · Future</span><h3>The right offer for every angler</h3><p>Eligible Insider or VIP access, purchased courses, and pay-to-enroll options should appear only after authenticating and checking entitlements.</p></div><button class="secondary" style="align-self:flex-start" data-view="browse">Explore free lessons →</button></div></div>${coursesBanner()}</main>`}
function savedView(){let a=sorted(items.filter(i=>saved.has(String(i.id))&&matches(i)));return `<main class="shell"><div class="subhero"><div class="eyebrow"><span class="dot"></span> YOUR SHORTLIST</div><h1>Saved lessons</h1><p>Keep a few useful videos handy for your next trip. Saving works in this browser for the prototype; member-account syncing would be a later feature.</p></div>${a.length?`<div class="gridcards">${a.map(card).join('')}</div>`:`<div class="empty"><strong>No saved lessons ${search?'matching your search':'yet'}.</strong>Tap the ♡ beside any lesson to save it here.<p><button class="primary" data-view="browse">Explore lessons →</button></p></div>`}</main>`}
function footer(){return `<footer class="footer"><div class="shell"><div>Salt Strong WATCH · Exploratory prototype only · Existing WordPress content remains unchanged</div><div><a href="https://www.saltstrong.com/fishing-tips/" target="_blank" rel="noopener">Current Fishing Tips archive ↗</a></div></div></footer>`}
function render(){if(view==='home'&&(search||filter!=='All')){view='browse';document.querySelectorAll('.navbtn').forEach(b=>b.classList.toggle('active',b.dataset.view===view))}app.innerHTML=({home,browse,quick,courses,saved:savedView}[view]||home)()+footer();$('#saved-count').textContent=saved.size?`(${saved.size})`:'';$('#clear-search').classList.toggle('hidden',!search);hydrateThumbnails(app)}
function showModal(it){selected=it;const video=it.video||null;let player='';
if(video&&((video.provider==='youtube'&&/^[A-Za-z0-9_-]{11}$/.test(video.id))||(video.provider==='vimeo'&&/^\d+$/.test(video.id)))){
  player=`${thumb(it,'player-cover')}<div class="preplay"><button class="modal-play-button" data-start-video aria-label="Play ${esc(it.title)}">▶ Play video</button></div>`;
}else{
  player=`${thumb(it,'player-cover')}<div class="missing"><div class="eyebrow" style="justify-content:center">ARTICLE-CONNECTED LESSON</div><h3>Ready to watch?</h3><p>This sample has a verified article, but its playable embed URL has not been verified. Open the original lesson to watch it now.</p><a class="primary" href="${esc(safeUrl(it.url))}" target="_blank" rel="noopener">▶ Watch on SaltStrong.com ↗</a></div>`;
}
let gear=(it.gear||[]).map(g=>{const u=safeUrl(g.url||'');return u!=='#'?`<a class="gearpill linked" href="${esc(u)}" target="_blank" rel="noopener noreferrer"><span class="gear-name">${esc(g.name)}</span><span class="gear-cta">Shop gear ↗</span></a>`:`<a class="gearpill" href="${esc(safeUrl(it.url))}" target="_blank" rel="noopener noreferrer"><span class="gear-name">${esc(g.name)}</span><span class="gear-cta">See in blog ↗</span></a>`}).join('');$('#modal-body').innerHTML=`<div class="player">${player}</div><div class="modcontent"><div class="eyebrow" style="margin-bottom:8px">${esc(it.author||'Salt Strong')} · ${esc(dateFmt(it.date))}</div><h2>${esc(it.title)}</h2><p>${esc(it.excerpt||'')}</p><div class="metarow">${(it.tags||[]).slice(0,5).map(t=>`<button class="tag" data-tag="${esc(t)}">${esc(t)}</button>`).join('')}</div><div class="modbottom"><div><h3>Keep learning</h3><p>Every lesson connects to the full blog post, where the original written tips, comments, and relevant gear links remain available. This helps protect the existing article experience.</p><div class="modlinks"><a class="smallaction" href="${esc(safeUrl(it.url))}" target="_blank" rel="noopener">Read full lesson + gear ↗</a><button class="smallaction" data-save="${esc(it.id)}">${saved.has(String(it.id))?'♥ Saved':'♡ Save for later'}</button></div></div><div><h3>Featured gear</h3>${gear||'<p>See the article for recommended gear and resources.</p>'}<a class="smallaction" href="${esc(safeUrl(it.url))}" target="_blank" rel="noopener" style="display:inline-block;margin-top:10px">All gear details in the article ↗</a></div></div></div>`;$('#overlay').classList.add('open');$('#overlay').setAttribute('aria-hidden','false');document.body.style.overflow='hidden';$('#close').focus();hydrateThumbnails($('#modal-body'))}
function closeModal(){if(!$('#overlay').classList.contains('open'))return;$('#overlay').classList.remove('open');$('#overlay').setAttribute('aria-hidden','true');document.body.style.overflow='';$('#modal-body').innerHTML='';selected=null}
function save(id){const k=String(id);if(saved.has(k))saved.delete(k);else saved.add(k);try{localStorage.setItem('ss_watch_saved',JSON.stringify([...saved]))}catch{}if(selected?.id===id)showModal(selected);render()}
document.addEventListener('click',e=>{if(e.target.closest('[data-start-video]')){if(!selected?.video)return;const v=selected.video;const src=v.provider==='youtube'?`https://www.youtube-nocookie.com/embed/${encodeURIComponent(v.id)}?autoplay=1`:`https://player.vimeo.com/video/${encodeURIComponent(v.id)}?autoplay=1`;const frame=document.createElement('iframe');frame.src=src;frame.title=selected.title;frame.allow='autoplay; encrypted-media; fullscreen; picture-in-picture';frame.allowFullscreen=true;frame.referrerPolicy='strict-origin-when-cross-origin';const el=$('#modal-body .player');if(el)el.replaceChildren(frame);return}const btn=e.target.closest('[data-open],[data-save],[data-tag],[data-browse-tag],[data-view],[data-coach],[data-reset]');if(!btn)return;if(btn.dataset.open){const it=items.find(i=>String(i.id)===btn.dataset.open);if(it)showModal(it)}else if(btn.dataset.save){save(btn.dataset.save)}else if(btn.dataset.tag){filter=btn.dataset.tag;search='';$('#search').value='';closeModal();setView('browse')}else if(btn.dataset.browseTag){filter=btn.dataset.browseTag;search='';$('#search').value='';setView('browse')}else if(btn.dataset.view){e.preventDefault();if(btn.dataset.view==='home'){filter='All';search='';$('#search').value=''}setView(btn.dataset.view)}else if(btn.dataset.coach){const name=btn.dataset.coach;filter='All';search=name;$('#search').value=name;setView('browse')}else if(btn.hasAttribute('data-reset')){filter='All';search='';$('#search').value='';render()}});
$('#search').addEventListener('input',e=>{search=e.target.value;filter='All';if(search||view==='browse'||view==='saved')setView(search?'browse':(view==='saved'?'saved':'browse'));else render()});$('#clear-search').addEventListener('click',()=>{search='';$('#search').value='';filter='All';setView('browse');$('#search').focus()});document.addEventListener('change',e=>{if(e.target.id==='sort'){sort=e.target.value;render()}});
$('#close').addEventListener('click',closeModal);$('#overlay').addEventListener('click',e=>{if(e.target===$('#overlay'))closeModal});document.addEventListener('keydown',e=>{if(e.key==='Escape')closeModal()});
async function init(){let data=null;try{let r=await fetch('./catalog.json',{cache:'no-store'});if(r.ok){data=await r.json();source='live'}}catch{}if(!data){try{let r=await fetch('./catalog.sample.json');if(r.ok)data=await r.json()}catch{}}if(!data&&window.SALT_STRONG_WATCH_SEED)data=window.SALT_STRONG_WATCH_SEED;if(!data){$('#data-status').textContent='Catalog unavailable';return}items=(data.items||[]).filter(x=>x.title&&x.url);if(data.demo)source='sample';const withVideo=items.filter(i=>i.video&&((i.video.provider==='youtube'&&/^[A-Za-z0-9_-]{11}$/.test(i.video.id))||(i.video.provider==='vimeo'&&/^\d+$/.test(i.video.id)))).length;
$('#data-status').textContent=source==='live'?`${withVideo} playable · ${items.length} imported lessons`:`${withVideo} with video IDs · ${items.length} demo examples`;render()}
init();
})();
