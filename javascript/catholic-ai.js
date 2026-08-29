(()=>{
  const scriptUrl=document.currentScript?.src||'';
  const form=document.querySelector('[data-catholic-ai-form]');
  const input=document.querySelector('[data-catholic-ai-input]');
  const status=document.querySelector('[data-catholic-ai-status]');
  const answerBox=document.querySelector('[data-catholic-ai-answer]');
  const answerText=document.querySelector('[data-catholic-ai-text]');
  const sourceBox=document.querySelector('[data-catholic-ai-sources]');
  const relatedBox=document.querySelector('[data-catholic-ai-related]');
  if(!form||!input||!status||!answerBox||!answerText||!sourceBox||!relatedBox)return;

  const isKh=location.pathname.includes('/kh/');
  const t=(en,kh)=>isKh?kh:en;

  async function apiBase(){
    let base=(window.MERCY_API_BASE||'').replace(/\/$/,'');
    if(!scriptUrl)return base;
    try{
      const r=await fetch(new URL('analytics-config.json',scriptUrl),{cache:'no-store'});
      if(r.ok){const j=await r.json();base=(j.mercy_api_base||base||'').replace(/\/$/,'')}
    }catch(e){}
    return base;
  }

  function clearResult(){
    answerBox.hidden=true;
    answerText.replaceChildren();
    sourceBox.replaceChildren();
    relatedBox.replaceChildren();
  }

  function appendInline(parent,text){
    const pattern=/(\[\^(\d+)\])|(\*\*([^*\n]+)\*\*)|(`([^`\n]+)`)|(\[([^\]\n]+)\]\((https?:\/\/[^\s)]+)\))|(\*([^*\n]+)\*)/g;
    let last=0,match;
    while((match=pattern.exec(text))!==null){
      if(match.index>last)parent.appendChild(document.createTextNode(text.slice(last,match.index)));
      if(match[2]){
        const n=match[2];
        const sup=document.createElement('sup');
        sup.className='ai-citation-ref';
        const a=document.createElement('a');
        a.href='#ai-source-'+n;
        a.textContent='['+n+']';
        a.setAttribute('aria-label',t('Go to source '+n,'Peit ia ka source '+n));
        sup.appendChild(a);
        parent.appendChild(sup);
      }else if(match[4]){
        const strong=document.createElement('strong');strong.textContent=match[4];parent.appendChild(strong);
      }else if(match[6]){
        const code=document.createElement('code');code.textContent=match[6];parent.appendChild(code);
      }else if(match[8]&&match[9]){
        const a=document.createElement('a');a.href=match[9];a.target='_blank';a.rel='noopener noreferrer';a.textContent=match[8];parent.appendChild(a);
      }else if(match[11]){
        const em=document.createElement('em');em.textContent=match[11];parent.appendChild(em);
      }
      last=pattern.lastIndex;
    }
    if(last<text.length)parent.appendChild(document.createTextNode(text.slice(last)));
  }

  function renderMarkdown(text){
    answerText.replaceChildren();
    answerText.classList.add('ai-markdown');
    const lines=String(text||'').replace(/\r\n?/g,'\n').split('\n');
    let paragraph=[];
    let list=null;
    let listType='';

    const flushParagraph=()=>{
      if(!paragraph.length)return;
      const p=document.createElement('p');
      appendInline(p,paragraph.join(' ').trim());
      answerText.appendChild(p);
      paragraph=[];
    };
    const closeList=()=>{list=null;listType=''};
    const ensureList=type=>{
      if(list&&listType===type)return list;
      closeList();
      list=document.createElement(type);
      listType=type;
      answerText.appendChild(list);
      return list;
    };

    lines.forEach(raw=>{
      const line=raw.trim();
      if(!line){flushParagraph();closeList();return}

      const heading=line.match(/^(#{1,6})\s+(.+)$/);
      if(heading){
        flushParagraph();closeList();
        const level=heading[1].length<=2?'h3':'h4';
        const h=document.createElement(level);
        appendInline(h,heading[2].trim());
        answerText.appendChild(h);
        return;
      }

      const ordered=line.match(/^\d+[.)]\s+(.+)$/);
      if(ordered){
        flushParagraph();
        const ol=ensureList('ol');
        const li=document.createElement('li');appendInline(li,ordered[1]);ol.appendChild(li);
        return;
      }

      const unordered=line.match(/^[-*+]\s+(.+)$/);
      if(unordered){
        flushParagraph();
        const ul=ensureList('ul');
        const li=document.createElement('li');appendInline(li,unordered[1]);ul.appendChild(li);
        return;
      }

      if(/^>\s?/.test(line)){
        flushParagraph();closeList();
        const q=document.createElement('blockquote');appendInline(q,line.replace(/^>\s?/,''));answerText.appendChild(q);
        return;
      }

      closeList();
      paragraph.push(line);
    });
    flushParagraph();
  }

  function renderSources(sources){
    sourceBox.replaceChildren();
    if(!Array.isArray(sources)||!sources.length)return;
    const h=document.createElement('h3');h.textContent=t('Catholic sources','Ki Catholic source');sourceBox.appendChild(h);
    const ul=document.createElement('ol');ul.className='source-list ai-source-list';
    sources.forEach((source,index)=>{
      const li=document.createElement('li');
      li.id='ai-source-'+(index+1);
      const title=(source.title||t('Catholic source','Catholic source')).trim();
      if(source.url){
        const a=document.createElement('a');a.href=source.url;a.target='_blank';a.rel='noopener noreferrer';a.textContent=title;li.appendChild(a);
      }else{
        const strong=document.createElement('strong');strong.textContent=title;li.appendChild(strong);
      }
      const details=[];
      if(source.authority)details.push(source.authority);
      if(source.reference)details.push(source.reference);
      if(details.length)li.appendChild(document.createTextNode(' — '+details.join(' · ')));
      const back=document.createElement('a');back.className='ai-source-back';back.href='#main';back.textContent=' ↥';back.setAttribute('aria-label',t('Back to answer','Phai sha ka jubab'));li.appendChild(back);
      ul.appendChild(li);
    });
    sourceBox.appendChild(ul);
  }

  function renderRelated(questions){
    relatedBox.replaceChildren();
    if(!Array.isArray(questions)||!questions.length)return;
    const h=document.createElement('h3');h.textContent=t('Related questions','Kiwei ki jingkylli kiba iadei');relatedBox.appendChild(h);
    const div=document.createElement('div');div.className='btns';
    questions.forEach(question=>{
      const b=document.createElement('button');b.type='button';b.className='btn secondary';b.textContent=question;
      b.addEventListener('click',()=>{input.value=question;input.focus();window.scrollTo({top:form.getBoundingClientRect().top+window.scrollY-110,behavior:'smooth'})});
      div.appendChild(b);
    });
    relatedBox.appendChild(div);
  }

  function errorMessage(statusCode,detail){
    if(detail==='magisterium_not_configured')return t('Catholic AI is installed, but the Magisterium API key has not yet been configured on the Mercy backend.','La install ia ka Catholic AI, hynrei ym pat configure ia ka Magisterium API key ha Mercy backend.');
    if(statusCode===429)return t('The Catholic AI request limit has been reached. Please try again later.','La poi sha ka request limit jong Catholic AI. Sngewbha pyrshang biang hadien.');
    if(statusCode===504)return t('Magisterium AI took too long to respond. Please try again.','Magisterium AI ka shim por palat ban jubab. Sngewbha pyrshang biang.');
    return t('Catholic AI is temporarily unavailable. Please try again later.','Catholic AI kam treikam shipor. Sngewbha pyrshang biang hadien.');
  }

  form.addEventListener('submit',async e=>{
    e.preventDefault();
    const question=input.value.trim();
    if(question.length<2)return;
    clearResult();
    const api=await apiBase();
    if(!api){
      status.textContent=t('The Catholic AI interface is ready, but the live Mercy API URL has not yet been connected.','Ka Catholic AI interface ka la ready, hynrei ym pat connect ia ka live Mercy API URL.');
      return;
    }
    const submit=form.querySelector('button[type="submit"]');
    if(submit)submit.disabled=true;
    status.textContent=t('Consulting Magisterium AI and Catholic sources…','Dang wad ha Magisterium AI bad ki Catholic source…');
    try{
      const r=await fetch(api+'/api/chat',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({message:question,language:isKh?'kha':'en'})
      });
      let data={};
      try{data=await r.json()}catch(e){}
      if(!r.ok){status.textContent=errorMessage(r.status,data.detail);return}
      renderMarkdown(data.reply||'');
      renderSources(data.sources||[]);
      renderRelated(data.related_questions||[]);
      answerBox.hidden=false;
      status.textContent=t(`Answer provided by ${data.provider||'Magisterium AI'}.`,`La ai jubab da ${data.provider||'Magisterium AI'}.`);
      answerBox.scrollIntoView({behavior:'smooth',block:'start'});
    }catch(e){
      status.textContent=t('Could not reach the Mercy Catholic AI service. Please try again later.','Ym lah ban ioh ia ka Mercy Catholic AI service. Sngewbha pyrshang biang hadien.');
    }finally{
      if(submit)submit.disabled=false;
    }
  });
})();
