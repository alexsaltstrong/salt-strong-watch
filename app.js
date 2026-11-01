/* WATCH Search Relevance V2: deliberately weighted and testable. */
const WatchSearch = (() => {
  'use strict';
  function normalize(value) {
    return String(value ?? '')
      .normalize('NFKD').replace(/[\u0300-\u036f]/g, '')
      .toLowerCase().replace(/&/g, ' and ').replace(/[^a-z0-9]+/g, ' ')
      .trim().replace(/\s+/g, ' ');
  }
  const bounded = value => ` ${value} `;
  function hasPhrase(haystack, phrase) {
    return Boolean(haystack && phrase && bounded(haystack).includes(` ${phrase} `));
  }
  function countPhrase(haystack, phrase) {
    if (!haystack || !phrase) return 0;
    let count = 0, from = 0;
    const all = bounded(haystack), needle = ` ${phrase} `;
    while ((from = all.indexOf(needle, from)) !== -1) { count++; from += needle.length - 1; }
    return count;
  }
  // Avoid generic fishing words driving results for focused queries.
  // Do not remove the only meaningful word in a query.
  const stop = new Set([
    'the','a','an','and','or','of','to','in','on','at','for','from','with','about',
    'around','under','over','near','using','use','how','where','why','when','do','i',
    'can','my','your','you','best','easy','way','tips','tip','video','videos','lesson',
    'lessons','fishing','fish','saltwater','inshore','catch','find','during'
  ]);
  // Explicit, conservative fishing synonyms. These apply to *high-signal*
  // fields only. A passing word in article body never activates a synonym.
  const concepts = [
    {terms:['night fishing','fishing at night','nighttime fishing','night bite','after dark','dock lights','night'], aliases:['night fishing','nighttime','night','after dark','dock lights','night bite','fishing at night']},
    {terms:['soft plastics','soft plastic'], aliases:['soft plastics','soft plastic','paddletails','paddletail','jerk shad','jerk shads','artificial shrimp']},
    {terms:['high water','high tide'], aliases:['high water','high tide','flooded grass','flooded shoreline','flooded shorelines']},
    {terms:['redfish','red drum'], aliases:['redfish','red drum']},
    {terms:['oyster bars','oyster bar'], aliases:['oyster bars','oyster bar','oyster reefs','oyster reef']},
    {terms:['paddletails','paddletail'], aliases:['paddletails','paddletail','paddle tail','paddle tails']}
  ];
  function wordVariants(token) {
    const a = [token];
    if (token.length > 4 && token.endsWith('ies')) a.push(token.slice(0, -3) + 'y');
    else if (token.length > 4 && token.endsWith('s') && !token.endsWith('ss')) a.push(token.slice(0, -1));
    if (token.length > 4 && !token.endsWith('s')) a.push(token + 's');
    return [...new Set(a)];
  }
  function parseQuery(input) {
    const text = normalize(input);
    if (!text) return {text:'', groups:[], exact:''};
    const concept = concepts.find(c => c.terms.includes(text));
    if (concept) return {text, groups:[{term:text, aliases:concept.aliases.map(normalize)}], exact:text};
    let tokens = text.split(' ');
    const relevant = tokens.filter(t => !stop.has(t));
    if (relevant.length) tokens = relevant;
    // Long queries are all-concepts searches, not "match any random word".
    const groups = [...new Set(tokens)].map(t => ({term:t,aliases:wordVariants(t)}));
    return {text, groups, exact:text};
  }
  function compile(item, visibleTags) {
    return {
      title:normalize(item.title),
      tags:normalize((visibleTags ?? item.tags ?? []).join(' ')),
      headings:normalize(item.content_headings),
      summary:normalize(item.excerpt),
      keywords:normalize((item.search_terms ?? []).join(' ')),
      body:normalize(item.search_text)
    };
  }
  const highFields = [['title',100],['tags',95],['headings',70],['summary',52]];
  function evidence(doc, aliases) {
    for (const [field,weight] of highFields) {
      for (const phrase of aliases) {
        if (hasPhrase(doc[field], phrase)) return {field, weight, phrase};
      }
    }
    return null;
  }
  function evaluate(doc, input) {
    const query = typeof input === 'string' ? parseQuery(input) : input;
    if (!query || !query.groups.length) return {score:1, reason:'Newest videos'};
    const hits = query.groups.map(group => evidence(doc,group.aliases));
    const matched = hits.filter(Boolean);
    // Single words must be central to the video, not a passing body mention.
    // Multiword queries require every significant concept, not OR-matching.
    if (matched.length === hits.length) {
      // Common filler words in a single excerpt sentence are not lesson topics.
      // A title, approved topic, or heading still qualifies such a query.
      const weakSingles = new Set(['day','days','today','search','searching','time','times','new','more','thing','things']);
      if (hits.length === 1 && matched[0].field === 'summary' && weakSingles.has(query.groups[0].term)) {
        return {score:0,reason:'Incidental summary wording'};
      }
      // "night fishing" should not match a random mention that a lure
      // happens to work at night. A summary-only result needs an explicit
      // nighttime technique phrase, not merely the word night.
      const nightTopic = ['night','night fishing','fishing at night','nighttime fishing','night bite','after dark','dock lights'].includes(query.text);
      if (nightTopic && hits.length === 1 && matched[0].field === 'summary' &&
          !['night fishing','fishing at night','night bite','dock lights','after dark','nighttime fishing'].some(term => hasPhrase(doc.summary,term))) {
        return {score:0,reason:'Passing nighttime mention in summary'};
      }
      let score = matched.reduce((sum,hit) => sum + hit.weight,0) / hits.length;
      const fields = [['title',60],['tags',50],['headings',35],['summary',24]];
      const phrase = fields.find(([field]) => hasPhrase(doc[field],query.exact));
      if (phrase) score += phrase[1];
      // Search terms may boost a *supported* result, never create one.
      if (hasPhrase(doc.keywords,query.exact)) score += 8;
      const unique = [...new Set(matched.map(hit => hit.field))];
      return {score:Math.round(score), reason:`Matched ${unique.join(' + ')}${phrase ? ' (exact phrase)' : ''}`};
    }
    // Full article text is searchable, but a phrase must clearly recur.
    // Never use this fallback for one-word queries or "night fishing"/other
    // single-concept synonyms where incidental mentions are notorious.
    if (query.groups.length >= 2 && query.text.split(' ').length >= 2) {
      const frequency = countPhrase(doc.body,query.exact);
      if (frequency >= 3) return {score:28,reason:`Repeated in article body (${frequency} mentions)`};
    }
    return {score:0,reason:'No sufficiently relevant match'};
  }
  return Object.freeze({normalize, hasPhrase, countPhrase, parseQuery, compile, evaluate});
})();

(() => {
  'use strict';
  const $ = (s) => document.querySelector(s);
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const validUrl = (u) => { try { const x = new URL(u); return ['https:','http:'].includes(x.protocol) ? x.href : ''; } catch { return ''; } };
  const yt = (v) => v?.provider === 'youtube' && /^[a-zA-Z0-9_-]{11}$/.test(v.id) ? v.id : '';
  const dateText = (s) => s && /^\d{4}-\d\d-\d\d$/.test(s) ? new Date(`${s}T12:00:00`).toLocaleDateString('en-US',{month:'short',day:'numeric'}) : '';
  let items = [], view = 'home', query = '', category = 'All', selected = null, focusBeforeModal = null, heroIndex = 0, showAllTopics = false, topicSearch = '', mobileMenuOpen = false, mobileSearchOpen = false;
  let saved = new Set(); try { saved = new Set(JSON.parse(localStorage.getItem('ss_watch_saved') || '[]').map(String)); } catch {}
  // A deliberate, finite browse vocabulary. Search can still discover much
  // more detailed phrases; only reviewed topics become public filter chips.
  const builtinTopics = ['All','Redfish','Snook','Seatrout','Flounder','Tides','Oyster Bars','Marshes','Topwater','Lure Selection','Soft Plastics','Rigging','Gear Tests'];
  const approvedTopics = new Set([
    'Redfish','Seatrout','Snook','Flounder','Tarpon','Sheepshead','Mangrove Snapper','Black Drum',
    'Oyster Bars','Marshes','Mangroves','Grass Flats','Docks','Bridges','Creek Mouths','Structure',
    'Tides','High Water','Low Tide','Current','Wind','Cold Fronts','Fall Fishing','Night Fishing',
    'Lure Selection','Topwater','Soft Plastics','Paddletails','Shrimp Lures','Popping Corks',
    'Rigging','Sight Fishing','Live Bait','Weedless Lures','Jigheads',
    'Leader Line','Fishing Rods','Hardbaits','Gear Tests','Experiments'
  ]);
  // Old machine-generated labels (e.g. Match The Hatch) don't appear as
  // browse chips while awaiting a new resync. Explicit human tags are allowed.
  const publicTags = it => [...new Set((it.tags || []).filter(t =>
    approvedTopics.has(t) || (it.manual_tags || []).includes(t)))];
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
  // Search V2: content is indexed once. Search uses title, reviewed tags,
  // article headings and the author summary as primary relevance signals.
  // Full article text can only qualify a repeated, exact multiword phrase.
  const searchDocuments = new Map();
  const searchHit = (it) => {
    let document = searchDocuments.get(String(it.id));
    if (!document) {
      document = WatchSearch.compile(it, publicTags(it));
      searchDocuments.set(String(it.id), document);
    }
    return WatchSearch.evaluate(document, query);
  };
  const searchScore = (it) => searchHit(it).score;
  const matches = (it) =>
    (category === 'All' || publicTags(it).includes(category)) && searchScore(it) > 0;
  const sorted = (arr) => [...arr].sort((a,b) => String(b.date || '').localeCompare(String(a.date || '')));
  const tagsInCatalog = () => {
    const counts = new Map();
    items.forEach(it => publicTags(it).forEach(t => {if(t)counts.set(t,(counts.get(t)||0)+1)}));
    const priorities=builtinTopics.filter(t => t === 'All' || counts.has(t));
    const rest=[...counts].sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0])).map(([tag])=>tag);
    return [...new Set([...priorities,...rest])];
  };
  function chipBar(){
    const all=tagsInCatalog();
    const visible=showAllTopics
      ? all.filter(t=>t==='All'||t.toLowerCase().includes(topicSearch.trim().toLowerCase())).slice(0,80)
      : all.slice(0,12);
    // A filter reached from an in-video tag must NEVER become invisible.
    if(category!=='All' && !visible.includes(category))visible.splice(1,0,category);
    const hasMore=all.length>12;
    const matches=all.filter(t=>t==='All'||t.toLowerCase().includes(topicSearch.trim().toLowerCase()));
    return `<div class="topic-controls">${showAllTopics?`<label class="topic-search-label" for="topic-filter">Find a topic<input id="topic-filter" type="search" value="${esc(topicSearch)}" placeholder="Search all ${all.length-1} topics..." autocomplete="off"></label>`:''}<div class="chips" role="group" aria-label="Fishing topics">${visible.map(t=>`<button type="button" class="chip ${category===t?'active':''}" data-tag="${esc(t)}" aria-pressed="${category===t}">${esc(t)}</button>`).join('')}</div>${showAllTopics&&matches.length>80?`<p class="topic-count">${matches.length-80} more topics. Refine your search above.</p>`:''}${hasMore?`<button class="chip more-topics" type="button" data-more-topics aria-expanded="${showAllTopics}">${showAllTopics?'Show fewer':'More topics'} <span aria-hidden="true">${showAllTopics?'−':'+'}</span></button>`:''}</div>`;
  }
  function card(it){
    const yes=saved.has(String(it.id));
    return `<article class="video-card"><button type="button" class="poster" data-open="${esc(it.id)}" aria-label="Watch ${esc(it.title)}">${image(it)}<span class="play" aria-hidden="true">▶</span><span class="cardbadge">${esc(publicTags(it)[0]||'Fishing Tips')}</span></button><div class="card-body"><button type="button" class="card-title" data-open="${esc(it.id)}">${esc(it.title)}</button><div class="cardline"><span>${esc(it.author||'Salt Strong')}${dateText(it.date)?` · ${esc(dateText(it.date))}`:''}</span><button type="button" class="savebtn ${yes?'saved':''}" data-save="${esc(it.id)}" aria-label="${yes?'Remove saved':'Save'}: ${esc(it.title)}" aria-pressed="${yes}">${yes?'♥':'♡'}</button></div></div></article>`;
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
        <div class="hero-copy"><div class="eyebrow">Latest lessons <span class="hero-mini-index">${heroIndex+1} / ${slides.length}</span></div><h1>${esc(it.title)}</h1><p>${esc(it.excerpt||'Real on-the-water tips to help you catch more fish.')}</p><div class="hero-actions"><button type="button" class="btn primary" data-open="${esc(it.id)}"><span aria-hidden="true">▶</span> Watch now</button><button type="button" class="btn ghost" data-related="${esc(publicTags(it)[0]||'All')}">More like this</button></div></div>
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
      const matches=newest.filter(it=>publicTags(it).some(t=>def.tags.includes(t)));
      return {...def,matches};
    }).filter(def=>def.matches.length);
    const cards=available.slice(0,4).map(def=>{
      const sample=def.matches[0];
      const primaryTag=def.tags.find(t=>publicTags(sample).includes(t)) || def.tags[0];
      return `<button type="button" class="collection-card" data-collection="${esc(primaryTag)}" aria-label="Explore ${esc(def.title)} lessons">${image(sample)}<span class="collection-gradient" aria-hidden="true"></span><span class="collection-title">${esc(def.title)}</span><span class="collection-arrow" aria-hidden="true">→</span></button>`;
    });
    if(!cards.length)return '';
    return `<section class="section collections-section"><div class="sectionhead"><div><h2>Popular collections</h2><p>Find the fishing lessons that match your next goal.</p></div><button class="more" type="button" data-view="browse">Explore collections →</button></div><div class="collections">${cards.join('')}</div></section>`;
  }
  function home(){
    const newest=sorted(items);
    if(!newest.length)return `<main class="shell"><div class="empty"><strong>No videos available yet.</strong>Import the newest public articles using GitHub Actions.</div></main>`;
    const featuredTopic = category !== 'All' ? newest.filter(it => publicTags(it).includes(category)) : [];
    return `${heroSection(newest)}<main class="shell">
      <section class="chooser" aria-label="Browse fishing topics"><div class="chooser-heading"><h2>What do you want to<br>master on the water?</h2><span class="orange-swoosh" aria-hidden="true"></span></div>${chipBar()}</section>
      ${category !== 'All' ? `<div id="topic-spotlight">${reel(`${category} lessons`, `Explore ${featuredTopic.length} lesson${featuredTopic.length === 1 ? '' : 's'} about ${category.toLowerCase()}.`, featuredTopic)}${featuredTopic.length === 0 ? '<div class="empty">No matching lessons in the current catalog.</div>' : ''}</div>` : ''}
      ${reel('New on WATCH','The latest fishing lessons, tips, and on-the-water reports.',newest)}
      ${collectionTiles(newest)}
      <section class="feature-banner"><div class="course-banner-icon" aria-hidden="true">✦</div><div class="feature-copy"><div class="eyebrow">Go deeper</div><h2>Go deeper with Salt Strong courses</h2><p>Step-by-step lessons to build your skills and catch more fish.</p></div><a class="btn outline" href="https://www.saltstrong.com/courses/">Explore courses →</a></section>

    </main>`;
  }
  function browse(){const list=items.filter(matches).sort((a,b) => query.trim() ? (searchScore(b)-searchScore(a) || String(b.date||'').localeCompare(String(a.date||''))) : String(b.date||'').localeCompare(String(a.date||'')));
    if (query.trim() && new URLSearchParams(window.location.search).has('watch_search_debug')) {
      console.table(list.map(it => ({title:it.title, score:searchScore(it), why:searchHit(it).reason})));
    }
    return `<main class="shell"><div class="browse-intro"><div class="eyebrow">Find the lesson you need</div><h1>${query?'Search results':'All fishing videos'}</h1><p>Filter by species, structure, conditions and tackle. Tags are generated from the articles, not just existing WordPress labels.</p></div><section class="section">${chipBar()}<div class="resultsbar"><span><strong>${list.length}</strong> video${list.length===1?'':'s'} found</span><span>${query.trim()?'Best match':'Newest first'}</span></div>${list.length?`<div class="gridcards">${list.map(card).join('')}</div>`:`<div class="empty"><strong>No matches this time.</strong>Try a different search or category.<br><button class="btn light" data-reset="1">Clear search and filters</button></div>`}</section></main>`}
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
    $('#modal-body').innerHTML=`<div class="modal-header"><div class="modal-heading"><h2 id="modal-title">${esc(it.title)}</h2><div class="byline"><strong>${esc(it.author||'Salt Strong')}</strong><span aria-hidden="true">·</span><span>${esc(dateText(it.date))}</span></div></div><button type="button" class="close" data-close aria-label="Close video">×</button></div><div class="player">${image(it)}${yt(it.video)?`<div class="preplay"><button type="button" class="btn primary modal-play" data-play="1">▶ Play video</button></div>`:`<div class="no-video"><p>Video player unavailable in this record.</p><a class="btn primary" href="${esc(validUrl(it.url))}" target="_blank" rel="noopener">Read original article ↗</a></div>`}</div><div class="modcontent"><p>${esc(it.excerpt||'')}</p><div class="metarow">${publicTags(it).slice(0,8).map(t=>`<button type="button" class="tag" data-tag="${esc(t)}">${esc(t)}</button>`).join('')}</div><div class="modbottom"><div><h3>Keep learning</h3><p>Read the full Salt Strong article for written details, comments and additional resources.</p><div class="modlinks"><a class="btn light" href="${esc(validUrl(it.url))}" target="_blank" rel="noopener noreferrer">Read full article ↗</a><button type="button" class="btn light" data-save="${esc(it.id)}">${saved.has(String(it.id))?'♥ Saved':'♡ Save for later'}</button></div></div><div><h3>Featured gear</h3>${gear||'<p>For tackle recommendations, see the full article.</p>'}</div></div></div>`;
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
    if(el.hasAttribute('data-more-topics')){showAllTopics=!showAllTopics;topicSearch='';render();return;}
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
  document.addEventListener('input',e=>{
    if(e.target.id!=='topic-filter')return;
    const start=e.target.selectionStart;
    topicSearch=e.target.value;
    render();
    const input=$('#topic-filter');
    if(input){input.focus();input.setSelectionRange(start,start);}
  });
  $('#search').addEventListener('input',e=>{query=e.target.value;category='All';view='browse';render();});
  let heroTouchX=null;document.addEventListener('touchstart',e=>{if(e.target.closest('#featured-hero'))heroTouchX=e.changedTouches[0]?.screenX??null;},{passive:true});document.addEventListener('touchend',e=>{if(heroTouchX==null||!e.target.closest('#featured-hero'))return;const diff=(e.changedTouches[0]?.screenX??heroTouchX)-heroTouchX;heroTouchX=null;if(Math.abs(diff)>65){const n=Math.min(5,items.length);heroIndex=(heroIndex+(diff<0?1:-1)+n)%n;render();}},{passive:true});
  document.addEventListener('keydown',e=>{if(e.key==='Escape')closeModal();});
  async function init(){let data=null;let isSample=false;try{const r=await fetch('./catalog.json',{cache:'no-store'});if(r.ok)data=await r.json();}catch{}if(!data){try{const r=await fetch('./catalog.sample.json',{cache:'no-store'});if(r.ok){data=await r.json();isSample=true;}}catch{}}if(!data){console.warn('WATCH catalog unavailable');return;}
    items=(data.items||[]).filter(x=>x.id&&x.title&&validUrl(x.url)&&yt(x.video));
    // A real catalog may still include legacy, unresolved records. They must not appear as playable videos.
    items=sorted(items);searchDocuments.clear();console.info(`WATCH: ${items.length} playable videos${isSample?' (sample catalog)':''}`);render();
  }
  init();
})();
