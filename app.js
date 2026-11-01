(() => {
  'use strict';
  const $ = (s) => document.querySelector(s);
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const validUrl = (u) => { try { const x = new URL(u); return ['https:','http:'].includes(x.protocol) ? x.href : ''; } catch { return ''; } };
  const yt = (v) => v?.provider === 'youtube' && /^[a-zA-Z0-9_-]{11}$/.test(v.id) ? v.id : '';
  const dateText = (s) => s && /^\d{4}-\d\d-\d\d$/.test(s) ? new Date(`${s}T12:00:00`).toLocaleDateString('en-US',{month:'short',day:'numeric'}) : '';
  let items = [], view = 'home', query = '', category = 'All', selected = null, focusBeforeModal = null, heroIndex = 0, showAllTopics = false, mobileMenuOpen = false, mobileSearchOpen = false;
  let saved = new Set(); try { saved = new Set(JSON.parse(localStorage.getItem('ss_watch_saved') || '[]').map(String)); } catch {}
  const builtinTopics = ['All','Redfish','Snook','Seatrout','Flounder','Tides','Oyster Bars','Marshes','Structure','Topwater','Paddletails','Rigging','Gear Tests'];
  // Always prefer the highest *real* YouTube artwork. Some missing maxres
  // URLs return a 120x90 placeholder with HTTP 200, so check naturalWidth.
  const image = (it) => {
    const id = yt(it.video);
    const articleFallback = validUrl(it.image_fallback) || (!id ? validUrl(it.image) : '');
    if (id) return `<img src="https://i.ytimg.com/vi/${id}/maxresdefault.jpg" data-yt-id="${esc(id)}" data-article-fallback="${esc(articleFallback)}" alt="Thumbnail for ${esc(it.title)}" loading="lazy">`;
    return `<img src="${esc(articleFallback || './assets/thumbnail-fallback.svg')}" alt="Thumbnail for ${esc(it.title)}" loading="lazy">`;
  };
  // Allow existing saltstrong.com/shopify-sso redirects through unchanged.
  // For direct Fish Strong URLs, route through the SAME first-party SSO endpoint
  // that WordPress articles use. Do not rewrite other merchants or wrap twice.
  const ssoGearUrl = (source) => {
    const url = validUrl(source);
    if (!url) return '';
    const parsed = new URL(url);
    const host = parsed.hostname.toLowerCase();
    if ((host === 'saltstrong.com' || host === 'www.saltstrong.com') &&
        parsed.pathname === '/shopify-sso/product.php') return url;
    if (host === 'fishstrong.com' || host === 'www.fishstrong.com') {
      return `https://www.saltstrong.com/shopify-sso/product.php?shopurl=${encodeURIComponent(url)}`;
    }
    return url;
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
  function chipBar(){
    const list = tagsInCatalog();
    const shortList = showAllTopics ? list : list.slice(0,12);
    return `<div class="topic-controls"><div class="chips" role="group" aria-label="Fishing topics">${shortList.map(t=>`<button type="button" class="chip ${category===t?'active':''}" data-tag="${esc(t)}" aria-pressed="${category===t}">${esc(t)}</button>`).join('')}</div>${list.length>12?`<button class="chip more-topics" type="button" data-more-topics aria-expanded="${showAllTopics}">${showAllTopics?'Show fewer':'More topics'} <span aria-hidden="true">${showAllTopics?'−':'+'}</span></button>`:''}</div>`;
  }
  function card(it){
    const yes=saved.has(String(it.id));
    return `<article class="video-card"><button type="button" class="poster" data-open="${esc(it.id)}" aria-label="Watch ${esc(it.title)}">${image(it)}<span class="play" aria-hidden="true">▶</span><span class="cardbadge">${esc((it.tags||[])[0]||'Fishing Tips')}</span></button><div class="card-body"><button type="button" class="card-title" data-open="${esc(it.id)}">${esc(it.title)}</button><div class="cardline"><span>${esc(it.author||'Salt Strong')}${dateText(it.date)?` · ${esc(dateText(it.date))}`:''}</span><button type="button" class="savebtn ${yes?'saved':''}" data-save="${esc(it.id)}" aria-label="${yes?'Remove saved':'Save'}: ${esc(it.title)}" aria-pressed="${yes}">${yes?'♥':'♡'}</button></div></div></article>`;
  }
  function reel(title,subtitle,list){
    if(!list.length)return '';
    const id='reel-'+title.toLowerCase().replace(/[^a-z0-9]+/g,'-');
    return `<section class="section" aria-label="${esc(title)}"><div class="sectionhead"><div><h2>${esc(title)}</h2><p>${esc(subtitle)}</p></div><button class="more" type="button" data-view="browse">Explore all <span aria-hidden="true">→</span></button></div><div class="reel-wrap"><button type="button" class="reel-arrow prev" data-scroll="${esc(id)}" data-dir="-1" aria-label="Previous videos in ${esc(title)}">‹</button><div class="reel" id="${esc(id)}" tabindex="0" aria-label="Scroll videos in ${esc(title)}">${list.slice(0,22).map(card).join('')}</div><button type="button" class="reel-arrow next" data-scroll="${esc(id)}" data-dir="1" aria-label="More videos in ${esc(title)}">›</button></div></section>`;
  }
  function heroSection(newest){
    const slides=newest.slice(0,Math.min(5,newest.length));
    if(!slides.length)return '';
    heroIndex=((heroIndex%slides.length)+slides.length)%slides.length;
    const it=slides[heroIndex];
    return `<section class="hero" aria-label="Featured fishing lessons" id="featured-hero">
      <div class="hero-image" aria-hidden="true">${image(it)}</div>
      <div class="hero-shade"></div>
      <div class="shell hero-content">
        <div class="hero-copy"><div class="eyebrow">Latest lessons <span class="hero-mini-index">${heroIndex+1} / ${slides.length}</span></div><h1>${esc(it.title)}</h1><p>${esc(it.excerpt||'Real on-the-water tips to help you catch more fish.')}</p><div class="hero-actions"><button type="button" class="btn primary" data-open="${esc(it.id)}"><span aria-hidden="true">▶</span> Watch now</button><button type="button" class="btn ghost" data-related="${esc((it.tags||[])[0]||'All')}">More like this</button></div></div>
      </div>
      ${slides.length>1?`<button class="hero-arrow left" type="button" data-hero="prev" aria-label="Previous featured lesson">‹</button><button class="hero-arrow right" type="button" data-hero="next" aria-label="Next featured lesson">›</button><div class="hero-dots" role="group" aria-label="Featured lesson selection">${slides.map((_,i)=>`<button class="hero-dot ${i===heroIndex?'current':''}" type="button" data-hero-index="${i}" aria-label="Featured lesson ${i+1}" aria-pressed="${i===heroIndex}"></button>`).join('')}</div>`:''}
    </section>`;
  }
  function collectionTiles(newest){
    const definitions = [
      {title:'Redfish essentials',tags:['Redfish']},
      {title:'Oyster bar strategies',tags:['Oyster Bars']},
      {title:'Lure strategies',tags:['Lures','Artificial Lures','Topwater','Paddletails']},
      {title:'Marsh fishing',tags:['Marshes','Creek Mouths']},
      {title:'Understanding the tides',tags:['Tides']},
      {title:'Rigging & knots',tags:['Rigging']},
      {title:'Gear tests',tags:['Gear Tests']},
      {title:'Snook lessons',tags:['Snook']},
      {title:'Seatrout lessons',tags:['Seatrout']},
      {title:'Fishing structure',tags:['Structure']},
    ];
    const available=definitions.map(def=>{
      const matches=newest.filter(it=>(it.tags||[]).some(t=>def.tags.includes(t)));
      return {...def,matches};
    }).filter(def=>def.matches.length);
    const cards=available.slice(0,4).map(def=>{
      const sample=def.matches[0];
      const primaryTag=def.tags.find(t=>(sample.tags||[]).includes(t)) || def.tags[0];
      return `<button type="button" class="collection-card" data-collection="${esc(primaryTag)}" aria-label="Explore ${esc(def.title)} lessons">${image(sample)}<span class="collection-gradient" aria-hidden="true"></span><span class="collection-title">${esc(def.title)}</span><span class="collection-arrow" aria-hidden="true">→</span></button>`;
    });
    if(!cards.length)return '';
    return `<section class="section collections-section"><div class="sectionhead"><div><h2>Popular collections</h2><p>Find the fishing lessons that match your next goal.</p></div><button class="more" type="button" data-view="browse">Explore collections →</button></div><div class="collections">${cards.join('')}</div></section>`;
  }
  function home(){
    const newest=sorted(items);
    if(!newest.length)return `<main class="shell"><div class="empty"><strong>No videos available yet.</strong>Import the newest public articles using GitHub Actions.</div></main>`;
    const featuredTopic = category !== 'All' ? newest.filter(it => (it.tags || []).includes(category)) : [];
    return `${heroSection(newest)}<main class="shell">
      <section class="chooser" aria-label="Browse fishing topics"><div class="chooser-heading"><h2>What do you want to<br>master on the water?</h2><span class="orange-swoosh" aria-hidden="true"></span></div>${chipBar()}</section>
      ${category !== 'All' ? `<div id="topic-spotlight">${reel(`${category} lessons`, `Explore ${featuredTopic.length} lesson${featuredTopic.length === 1 ? '' : 's'} about ${category.toLowerCase()}.`, featuredTopic)}${featuredTopic.length === 0 ? '<div class="empty">No matching lessons in the current catalog.</div>' : ''}</div>` : ''}
      ${reel('New on WATCH','The latest fishing lessons, tips, and on-the-water reports.',newest)}
      ${collectionTiles(newest)}
      <section class="feature-banner"><div class="course-banner-icon" aria-hidden="true">✦</div><div class="feature-copy"><div class="eyebrow">Go deeper</div><h2>Go deeper with Salt Strong courses</h2><p>Step-by-step lessons to build your skills and catch more fish.</p></div><a class="btn outline" href="https://www.saltstrong.com/courses/">Explore courses →</a></section>

    </main>`;
  }
  function browse(){const list=sorted(items.filter(matches));return `<main class="shell"><div class="browse-intro"><div class="eyebrow">Find the lesson you need</div><h1>${query?'Search results':'All fishing videos'}</h1><p>Filter by species, structure, conditions and tackle. Tags are generated from the articles, not just existing WordPress labels.</p></div><section class="section">${chipBar()}<div class="resultsbar"><span><strong>${list.length}</strong> video${list.length===1?'':'s'} found</span><span>Newest first</span></div>${list.length?`<div class="gridcards">${list.map(card).join('')}</div>`:`<div class="empty"><strong>No matches this time.</strong>Try a different search or category.<br><button class="btn light" data-reset="1">Clear search and filters</button></div>`}</section></main>`}
  function savedPage(){const list=sorted(items.filter(it=>saved.has(String(it.id))&&matches(it)));return `<main class="shell"><div class="browse-intro"><div class="eyebrow">Your fishing shortlist</div><h1>Saved videos</h1><p>Favorites are stored in this browser for the prototype. Cross-device WordPress account sync is a future integration.</p></div><section class="section">${chipBar()}<div class="resultsbar">${list.length} saved lesson${list.length===1?'':'s'}</div>${list.length?`<div class="gridcards">${list.map(card).join('')}</div>`:`<div class="empty"><strong>Nothing saved yet.</strong>Click the heart beside any video to keep it handy.<br><button class="btn light" data-view="browse">Find videos →</button></div>`}</section></main>`}
  function courses(){return `<main class="shell"><div class="browse-intro"><div class="eyebrow">Learn at your pace</div><h1>Salt Strong courses</h1><p>A discovery preview for existing premium courses. Actual Insider, VIP and purchase access will need the WordPress/Memberium integration.</p></div><section class="section"><div class="courses-list"><div class="course-card"><div class="eyebrow">Future course integration</div><h3>Structured fishing lessons</h3><p>Continue learning after watching a free fishing tip. Course recommendations will link to verified purchase pages.</p><a class="btn light" href="https://www.saltstrong.com/courses/" target="_blank" rel="noopener noreferrer">See current courses ↗</a></div><div class="course-card"><div class="eyebrow">Member-aware in the future</div><h3>Insider & VIP access</h3><p>WATCH will never grant course access based on a tag or a thumbnail. Current permissions will come from WordPress.</p><button class="btn light" data-view="browse">Explore public lessons →</button></div></div></section></main>`}
  function hydrateImages(root){
    root.querySelectorAll('img[data-yt-id]').forEach(img => {
      const id = img.dataset.ytId;
      const urls = [`https://i.ytimg.com/vi/${id}/maxresdefault.jpg`,
                    `https://i.ytimg.com/vi/${id}/sddefault.jpg`,
                    `https://i.ytimg.com/vi/${id}/hqdefault.jpg`];
      const extra = img.dataset.articleFallback;
      if(extra && !urls.includes(extra)) urls.push(extra);
      urls.push('./assets/thumbnail-fallback.svg');
      let stage=0;
      const advance=()=>{ stage++; if(stage < urls.length) img.src = urls[stage]; };
      img.addEventListener('error', advance);
      img.addEventListener('load', ()=>{
        // Missing maxres/sd versions can return a tiny 120px image, not an error.
        if(stage < 2 && img.naturalWidth <= 320) advance();
      });
      if(img.complete && img.naturalWidth) {
        if(img.naturalWidth <= 320) advance();
      }
    });
  }
  function render(){
    const main=$('#app');
    main.innerHTML=({home,browse,saved:savedPage,courses}[view]||home)()+`<footer class="site-footer"><div class="shell"><span>Salt Strong WATCH · Public fishing video library</span><a href="https://www.saltstrong.com/fishing-tips/" target="_blank" rel="noopener noreferrer">Original Salt Strong articles ↗</a></div></footer>`;
    hydrateImages(main);
    const count=$('#saved-count');if(count)count.textContent=saved.size?`(${saved.size})`:'';
    document.querySelectorAll('.nav, .mobile-tab').forEach(n=>{n.classList.toggle('active',n.dataset.view===view);n.setAttribute('aria-current',n.dataset.view===view?'page':'false');});
    document.body.classList.toggle('mobile-menu-open',mobileMenuOpen);
    document.body.classList.toggle('mobile-search-open',mobileSearchOpen);
  }
  function switchView(name){view=name;mobileMenuOpen=false;render();window.scrollTo({top:0,behavior:'instant'});}
  function toggleSave(id){id=String(id);if(saved.has(id))saved.delete(id);else saved.add(id);try{localStorage.setItem('ss_watch_saved',JSON.stringify([...saved]));}catch{}if(selected&&String(selected.id)===id)openModal(selected,false);render();}
  function openModal(it,saveFocus=true){
    if(saveFocus)focusBeforeModal=document.activeElement;selected=it;
    const gear=(it.gear||[]).filter(g=>g.name&&ssoGearUrl(g.url)).map(g=>`<a class="gearpill" href="${esc(ssoGearUrl(g.url))}" target="_blank" rel="noopener noreferrer"><span>${esc(g.name)}</span><span>Shop ↗</span></a>`).join('');
    $('#modal-body').innerHTML=`<div class="modal-header"><div class="modal-heading"><h2 id="modal-title">${esc(it.title)}</h2><div class="byline"><strong>${esc(it.author||'Salt Strong')}</strong><span aria-hidden="true">·</span><span>${esc(dateText(it.date))}</span></div></div><button type="button" class="close" data-close aria-label="Close video">×</button></div><div class="player">${image(it)}${yt(it.video)?`<div class="preplay"><button type="button" class="btn primary modal-play" data-play="1">▶ Play video</button></div>`:`<div class="no-video"><p>Video player unavailable in this record.</p><a class="btn primary" href="${esc(validUrl(it.url))}" target="_blank" rel="noopener">Read original article ↗</a></div>`}</div><div class="modcontent"><p>${esc(it.excerpt||'')}</p><div class="metarow">${(it.tags||[]).slice(0,10).map(t=>`<button type="button" class="tag" data-tag="${esc(t)}">${esc(t)}</button>`).join('')}</div><div class="modbottom"><div><h3>Keep learning</h3><p>Read the full Salt Strong article for written details, comments and additional resources.</p><div class="modlinks"><a class="btn light" href="${esc(validUrl(it.url))}" target="_blank" rel="noopener noreferrer">Read full article ↗</a><button type="button" class="btn light" data-save="${esc(it.id)}">${saved.has(String(it.id))?'♥ Saved':'♡ Save for later'}</button></div></div><div><h3>Featured gear</h3>${gear||'<p>For tackle recommendations, see the full article.</p>'}</div></div></div>`;
    const overlay=$('#overlay');overlay.classList.add('open');overlay.setAttribute('aria-hidden','false');document.body.style.overflow='hidden';hydrateImages($('#modal-body'));$('#modal-body .close').focus();
  }
  function closeModal(){const overlay=$('#overlay');if(!overlay.classList.contains('open'))return;overlay.classList.remove('open');overlay.setAttribute('aria-hidden','true');$('#modal-body').replaceChildren();selected=null;document.body.style.overflow='';focusBeforeModal?.focus?.();}
  document.addEventListener('click',ev=>{
    const el=ev.target.closest('[data-open],[data-view],[data-tag],[data-save],[data-close],[data-play],[data-coach],[data-reset],[data-hero],[data-hero-index],[data-related],[data-collection],[data-scroll],[data-more-topics],[data-toggle-search],[data-toggle-menu]');
    if(!el){if(ev.target.id==='overlay')closeModal();return;}
    if(el.hasAttribute('data-toggle-search')){mobileSearchOpen=!mobileSearchOpen;render();if(mobileSearchOpen)$('#search').focus();return;}
    if(el.hasAttribute('data-toggle-menu')){mobileMenuOpen=!mobileMenuOpen;render();return;}
    if(el.hasAttribute('data-hero')||el.hasAttribute('data-hero-index')){const n=Math.min(5,items.length);heroIndex=el.hasAttribute('data-hero-index')?Number(el.dataset.heroIndex):(heroIndex+(el.dataset.hero==='next'?1:-1)+n)%n;render();return;}
    if(el.dataset.related||el.dataset.collection){const target=el.dataset.related||el.dataset.collection;category=target;query='';$('#search').value='';switchView('browse');return;}
    if(el.hasAttribute('data-more-topics')){showAllTopics=!showAllTopics;render();return;}
    if(el.hasAttribute('data-scroll')){const x=document.getElementById(el.dataset.scroll);if(x)x.scrollBy({left:Number(el.dataset.dir)*Math.max(270,x.clientWidth*.83),behavior:'smooth'});return;}
    if(el.dataset.open){const it=items.find(x=>String(x.id)===el.dataset.open);if(it)openModal(it);return;}
    if(el.hasAttribute('data-close')){closeModal();return;}
    if(el.hasAttribute('data-play')){if(!selected)return;const id=yt(selected.video);if(!id)return;const f=document.createElement('iframe');f.title=`YouTube player: ${selected.title}`;f.src=`https://www.youtube-nocookie.com/embed/${encodeURIComponent(id)}?autoplay=1&rel=0`;f.allow='autoplay; encrypted-media; picture-in-picture; fullscreen';f.allowFullscreen=true;f.referrerPolicy='strict-origin-when-cross-origin';$('#modal-body .player').replaceChildren(f);return;}
    if(el.dataset.save){toggleSave(el.dataset.save);return;}
    if(el.dataset.tag){
      const inPopup = Boolean(el.closest('#modal-body'));
      category=el.dataset.tag;query='';$('#search').value='';closeModal();
      if(inPopup){switchView('browse');return;}
      render();
      if(view==='home' && category!=='All')requestAnimationFrame(()=>document.querySelector('#topic-spotlight')?.scrollIntoView({behavior:'smooth',block:'start'}));
      return;
    }
    if(el.dataset.coach){category='All';query=el.dataset.coach;$('#search').value=query;switchView('browse');return;}
    if(el.hasAttribute('data-reset')){category='All';query='';$('#search').value='';switchView('browse');return;}
    if(el.dataset.view){if(el.dataset.view==='courses'){window.location.assign('https://www.saltstrong.com/courses/');return;}if(el.dataset.view==='home' || el.dataset.view==='saved'){category='All';query='';$('#search').value='';}switchView(el.dataset.view);return;}
  });
  $('#search').addEventListener('input',e=>{query=e.target.value;category='All';view='browse';render();});
  let heroTouchX=null;document.addEventListener('touchstart',e=>{if(e.target.closest('#featured-hero'))heroTouchX=e.changedTouches[0]?.screenX??null;},{passive:true});document.addEventListener('touchend',e=>{if(heroTouchX==null||!e.target.closest('#featured-hero'))return;const diff=(e.changedTouches[0]?.screenX??heroTouchX)-heroTouchX;heroTouchX=null;if(Math.abs(diff)>65){const n=Math.min(5,items.length);heroIndex=(heroIndex+(diff<0?1:-1)+n)%n;render();}},{passive:true});
  document.addEventListener('keydown',e=>{if(e.key==='Escape')closeModal();});
  async function init(){let data=null;let isSample=false;try{const r=await fetch('./catalog.json',{cache:'no-store'});if(r.ok)data=await r.json();}catch{}if(!data){try{const r=await fetch('./catalog.sample.json',{cache:'no-store'});if(r.ok){data=await r.json();isSample=true;}}catch{}}if(!data){console.warn('WATCH catalog unavailable');return;}
    items=(data.items||[]).filter(x=>x.id&&x.title&&validUrl(x.url)&&yt(x.video));
    // A real catalog may still include legacy, unresolved records. They must not appear as playable videos.
    items=sorted(items);console.info(`WATCH: ${items.length} playable videos${isSample?' (sample catalog)':''}`);render();
  }
  init();
})();
