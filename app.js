(() => {
  'use strict';
  const $ = (s) => document.querySelector(s);
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const validUrl = (u) => { try { const x = new URL(u); return ['https:','http:'].includes(x.protocol) ? x.href : ''; } catch { return ''; } };
  const yt = (v) => v?.provider === 'youtube' && /^[a-zA-Z0-9_-]{11}$/.test(v.id) ? v.id : '';
  const dateText = (s) => s && /^\d{4}-\d\d-\d\d$/.test(s) ? new Date(`${s}T12:00:00`).toLocaleDateString('en-US',{month:'short',day:'numeric'}) : '';
  let items = [], view = 'home', query = '', category = 'All', selected = null, focusBeforeModal = null;
  let saved = new Set(); try { saved = new Set(JSON.parse(localStorage.getItem('ss_watch_saved') || '[]').map(String)); } catch {}
  const builtinTopics = ['All','Redfish','Snook','Seatrout','Flounder','Tides','Oyster Bars','Marshes','Structure','Topwater','Paddletails','Rigging','Gear Tests'];
  const image = (it) => {
    const id = yt(it.video);
    const primary = id ? `https://i.ytimg.com/vi/${id}/hqdefault.jpg` : validUrl(it.image) || validUrl(it.image_fallback);
    const fallback = validUrl(it.image_fallback) || validUrl(it.image);
    return `<img src="${esc(primary || './assets/thumbnail-fallback.svg')}" data-backup="${esc(fallback)}" alt="Thumbnail for ${esc(it.title)}" loading="lazy">`;
  };
  const matches = (it) => {
    const haystack = [it.title,it.author,it.excerpt,it.search_text,(it.tags||[]).join(' '),(it.suggested_tags||[]).join(' ')].join(' ').toLowerCase();
    return (category === 'All' || (it.tags||[]).includes(category)) && query.trim().toLowerCase().split(/\s+/).every(t=>!t||haystack.includes(t));
  };
  const sorted = (arr) => [...arr].sort((a,b) => String(b.date || '').localeCompare(String(a.date || '')));
  const tagsInCatalog = () => {
    const counts = new Map();items.forEach(it=>(it.tags||[]).forEach(t=>counts.set(t,(counts.get(t)||0)+1)));
    const list = builtinTopics.filter(t=>t==='All'||counts.has(t));
    [...counts].sort((a,b)=>b[1]-a[1]).forEach(([t])=>{if(!list.includes(t)&&list.length<27)list.push(t)});
    return list;
  };
  function chipBar(){return `<div class="chips">${tagsInCatalog().map(t=>`<button type="button" class="chip ${category===t?'active':''}" data-tag="${esc(t)}" aria-pressed="${category===t}">${esc(t)}</button>`).join('')}</div>`;}
  function card(it){
    const yes = saved.has(String(it.id));
    return `<article class="video-card"><button type="button" class="poster" data-open="${esc(it.id)}" aria-label="Watch ${esc(it.title)}">${image(it)}<span class="play" aria-hidden="true">▶</span><span class="cardbadge">${esc((it.tags||[])[0]||'Fishing Tips')}</span></button><div class="card-body"><button type="button" class="card-title" data-open="${esc(it.id)}">${esc(it.title)}</button><div class="cardline"><span>${esc(it.author||'Salt Strong')} · ${esc(dateText(it.date))}</span><button type="button" class="savebtn ${yes?'saved':''}" data-save="${esc(it.id)}" aria-label="${yes?'Remove saved':'Save'}: ${esc(it.title)}" aria-pressed="${yes}">${yes?'♥':'♡'}</button></div></div></article>`;
  }
  function reel(title,subtitle,list){if(!list.length)return '';return `<section class="section"><div class="sectionhead"><div><h2>${esc(title)}</h2><p>${esc(subtitle)}</p></div><button class="more" type="button" data-view="browse">Explore all →</button></div><div class="reel">${list.slice(0,22).map(card).join('')}</div></section>`}
  function home(){
    const newest=sorted(items);const hero=newest[0];
    if(!hero)return `<main class="shell"><div class="empty"><strong>No videos available yet.</strong>Import the newest 100 public articles using GitHub Actions.</div></main>`;
    const around=(topics)=>newest.filter(i=>(i.tags||[]).some(t=>topics.includes(t)));
    return `<section class="hero"><div class="shell hero-content"><div class="eyebrow">Salt Strong WATCH · Fishing education, simplified</div><h1>All the fishing know-how.<br><em>One place.</em></h1><p>Find what you need to catch more fish. Browse the latest lessons or search by species, structure, tides and tackle.</p><div class="hero-actions"><button class="btn primary" data-open="${esc(hero.id)}">▶ Watch the latest lesson</button><button class="btn outline" data-view="browse">Browse all videos →</button></div><div class="headline-lesson">Latest lesson: ${esc(hero.title)}</div></div></section><main class="shell"><section class="chooser"><div class="sectionhead"><div><h2>What do you want to learn?</h2><p>Browse a topic or search for something specific.</p></div></div>${chipBar()}</section>${reel('Fresh from the water','The newest public Salt Strong video lessons.',newest)}${reel('Find fish faster','Tides, structure, oyster bars, current and high-water patterns.',around(['Structure','Tides','Oyster Bars','Marshes','High Water']))}${reel('Tackle and techniques','Artificial lures, rigging, experiments and tackle tests.',around(['Topwater','Paddletails','Lures','Rigging','Gear Tests','Jigheads']))}<section class="feature-banner"><div><div class="eyebrow" style="color:#ffb58f">More ways to learn</div><h2>Go deeper with Salt Strong courses</h2><p>Browse structured lessons and existing course options.</p></div><button class="btn outline" data-view="courses">Explore courses</button></section><section class="section"><div class="sectionhead"><div><h2>Learn from your favorite coach</h2><p>Find videos from Luke, Pat and Tony.</p></div></div><div class="coach-row">${['Luke Simonds','Pat Ogletree','Tony Acevedo'].map(name=>`<button class="coach" data-coach="${esc(name)}">${esc(name)}<span>${items.filter(it=>it.author===name).length} lessons →</span></button>`).join('')}</div></section></main>`;
  }
  function browse(){const list=sorted(items.filter(matches));return `<main class="shell"><div class="browse-intro"><div class="eyebrow">Find the lesson you need</div><h1>${query?'Search results':'All fishing videos'}</h1><p>Filter by species, structure, conditions and tackle. Tags are generated from the articles, not just existing WordPress labels.</p></div><section class="section">${chipBar()}<div class="resultsbar"><span><strong>${list.length}</strong> video${list.length===1?'':'s'} found</span><span>Newest first</span></div>${list.length?`<div class="gridcards">${list.map(card).join('')}</div>`:`<div class="empty"><strong>No matches this time.</strong>Try a different search or category.<br><button class="btn light" data-reset="1">Clear search and filters</button></div>`}</section></main>`}
  function savedPage(){const list=sorted(items.filter(it=>saved.has(String(it.id))&&matches(it)));return `<main class="shell"><div class="browse-intro"><div class="eyebrow">Your fishing shortlist</div><h1>Saved videos</h1><p>Favorites are stored in this browser for the prototype. Cross-device WordPress account sync is a future integration.</p></div><section class="section">${chipBar()}<div class="resultsbar">${list.length} saved lesson${list.length===1?'':'s'}</div>${list.length?`<div class="gridcards">${list.map(card).join('')}</div>`:`<div class="empty"><strong>Nothing saved yet.</strong>Click the heart beside any video to keep it handy.<br><button class="btn light" data-view="browse">Find videos →</button></div>`}</section></main>`}
  function courses(){return `<main class="shell"><div class="browse-intro"><div class="eyebrow">Learn at your pace</div><h1>Salt Strong courses</h1><p>A discovery preview for existing premium courses. Actual Insider, VIP and purchase access will need the WordPress/Memberium integration.</p></div><section class="section"><div class="courses-list"><div class="course-card"><div class="eyebrow">Future course integration</div><h3>Structured fishing lessons</h3><p>Continue learning after watching a free fishing tip. Course recommendations will link to verified purchase pages.</p><a class="btn light" href="https://www.saltstrong.com/my-courses/" target="_blank" rel="noopener noreferrer">See current courses ↗</a></div><div class="course-card"><div class="eyebrow">Member-aware in the future</div><h3>Insider & VIP access</h3><p>WATCH will never grant course access based on a tag or a thumbnail. Current permissions will come from WordPress.</p><button class="btn light" data-view="browse">Explore public lessons →</button></div></div></section></main>`}
  function hydrateImages(root){root.querySelectorAll('img[data-backup]').forEach(img=>{img.addEventListener('error',()=>{const backup=img.dataset.backup;if(backup&&img.src!==backup){img.dataset.backup='';img.src=backup;}else{img.onerror=null;img.src='./assets/thumbnail-fallback.svg';}});});}
  function render(){const main=$('#app');main.innerHTML=({home,browse,saved:savedPage,courses}[view]||home)()+`<footer class="site-footer"><div class="shell"><span>Salt Strong WATCH · Public article library prototype</span><a href="https://www.saltstrong.com/fishing-tips/" target="_blank" rel="noopener noreferrer">Original Salt Strong articles ↗</a></div></footer>`;hydrateImages(main);$('#saved-count').textContent=saved.size?`(${saved.size})`:'';document.querySelectorAll('.nav').forEach(n=>n.classList.toggle('active',n.dataset.view===view));}
  function switchView(name){view=name;render();window.scrollTo({top:0,behavior:'instant'});}
  function toggleSave(id){id=String(id);if(saved.has(id))saved.delete(id);else saved.add(id);try{localStorage.setItem('ss_watch_saved',JSON.stringify([...saved]));}catch{}if(selected&&String(selected.id)===id)openModal(selected,false);render();}
  function openModal(it,saveFocus=true){
    if(saveFocus)focusBeforeModal=document.activeElement;selected=it;
    const gear=(it.gear||[]).filter(g=>g.name&&validUrl(g.url)).map(g=>`<a class="gearpill" href="${esc(validUrl(g.url))}" target="_blank" rel="noopener noreferrer"><span>${esc(g.name)}</span><span>Shop ↗</span></a>`).join('');
    $('#modal-body').innerHTML=`<div class="modal-header"><div class="modal-heading"><h2 id="modal-title">${esc(it.title)}</h2><div class="byline"><strong>${esc(it.author||'Salt Strong')}</strong><span aria-hidden="true">·</span><span>${esc(dateText(it.date))}</span></div></div><button type="button" class="close" data-close aria-label="Close video">×</button></div><div class="player">${image(it)}${yt(it.video)?`<div class="preplay"><button type="button" class="btn primary modal-play" data-play="1">▶ Play video</button></div>`:`<div class="no-video"><p>Video player unavailable in this record.</p><a class="btn primary" href="${esc(validUrl(it.url))}" target="_blank" rel="noopener">Read original article ↗</a></div>`}</div><div class="modcontent"><p>${esc(it.excerpt||'')}</p><div class="metarow">${(it.tags||[]).slice(0,10).map(t=>`<button type="button" class="tag" data-tag="${esc(t)}">${esc(t)}</button>`).join('')}</div><div class="modbottom"><div><h3>Keep learning</h3><p>Read the full Salt Strong article for written details, comments and additional resources.</p><div class="modlinks"><a class="btn light" href="${esc(validUrl(it.url))}" target="_blank" rel="noopener noreferrer">Read full article ↗</a><button type="button" class="btn light" data-save="${esc(it.id)}">${saved.has(String(it.id))?'♥ Saved':'♡ Save for later'}</button></div></div><div><h3>Featured gear</h3>${gear||'<p>For tackle recommendations, see the full article.</p>'}</div></div></div>`;
    const overlay=$('#overlay');overlay.classList.add('open');overlay.setAttribute('aria-hidden','false');document.body.style.overflow='hidden';hydrateImages($('#modal-body'));$('#modal-body .close').focus();
  }
  function closeModal(){const overlay=$('#overlay');if(!overlay.classList.contains('open'))return;overlay.classList.remove('open');overlay.setAttribute('aria-hidden','true');$('#modal-body').replaceChildren();selected=null;document.body.style.overflow='';focusBeforeModal?.focus?.();}
  document.addEventListener('click',ev=>{
    const el=ev.target.closest('[data-open],[data-view],[data-tag],[data-save],[data-close],[data-play],[data-coach],[data-reset]');
    if(!el){if(ev.target.id==='overlay')closeModal();return;}
    if(el.dataset.open){const it=items.find(x=>String(x.id)===el.dataset.open);if(it)openModal(it);return;}
    if(el.hasAttribute('data-close')){closeModal();return;}
    if(el.hasAttribute('data-play')){if(!selected)return;const id=yt(selected.video);if(!id)return;const f=document.createElement('iframe');f.title=`YouTube player: ${selected.title}`;f.src=`https://www.youtube-nocookie.com/embed/${encodeURIComponent(id)}?autoplay=1&rel=0`;f.allow='autoplay; encrypted-media; picture-in-picture; fullscreen';f.allowFullscreen=true;f.referrerPolicy='strict-origin-when-cross-origin';$('#modal-body .player').replaceChildren(f);return;}
    if(el.dataset.save){toggleSave(el.dataset.save);return;}
    if(el.dataset.tag){category=el.dataset.tag;query='';$('#search').value='';closeModal();switchView('browse');return;}
    if(el.dataset.coach){category='All';query=el.dataset.coach;$('#search').value=query;switchView('browse');return;}
    if(el.hasAttribute('data-reset')){category='All';query='';$('#search').value='';switchView('browse');return;}
    if(el.dataset.view){if(el.dataset.view==='home'){category='All';query='';$('#search').value='';}switchView(el.dataset.view);return;}
  });
  $('#search').addEventListener('input',e=>{query=e.target.value;category='All';view='browse';render();});
  document.addEventListener('keydown',e=>{if(e.key==='Escape')closeModal();});
  async function init(){let data=null;let isSample=false;try{const r=await fetch('./catalog.json',{cache:'no-store'});if(r.ok)data=await r.json();}catch{}if(!data){try{const r=await fetch('./catalog.sample.json',{cache:'no-store'});if(r.ok){data=await r.json();isSample=true;}}catch{}}if(!data){$('#data-status').textContent='Catalog unavailable';return;}
    items=(data.items||[]).filter(x=>x.id&&x.title&&validUrl(x.url)&&yt(x.video));
    // A real catalog may still include legacy, unresolved records. They must not appear as playable videos.
    items=sorted(items);$('#data-status').textContent=`${items.length} playable videos${isSample?' · sample catalog':''}`;render();
  }
  init();
})();
