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
    answerText.textContent='';
    sourceBox.innerHTML='';
    relatedBox.innerHTML='';
  }

  function renderSources(sources){
    sourceBox.innerHTML='';
    if(!Array.isArray(sources)||!sources.length)return;
    const h=document.createElement('h3');h.textContent=t('Catholic sources','Ki Catholic source');sourceBox.appendChild(h);
    const ul=document.createElement('ul');ul.className='source-list';
    sources.forEach(source=>{
      const li=document.createElement('li');
      const title=(source.title||t('Catholic source','Catholic source')).trim();
      if(source.url){
        const a=document.createElement('a');a.href=source.url;a.target='_blank';a.rel='noopener';a.textContent=title;li.appendChild(a);
      }else{
        const strong=document.createElement('strong');strong.textContent=title;li.appendChild(strong);
      }
      const details=[];
      if(source.authority)details.push(source.authority);
      if(source.reference)details.push(source.reference);
      if(details.length)li.appendChild(document.createTextNode(' — '+details.join(' · ')));
      ul.appendChild(li);
    });
    sourceBox.appendChild(ul);
  }

  function renderRelated(questions){
    relatedBox.innerHTML='';
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
      answerText.textContent=data.reply||'';
      renderSources(data.sources||[]);
      renderRelated(data.related_questions||[]);
      answerBox.hidden=false;
      status.textContent=t(`Answer provided by ${data.provider||'Magisterium AI'}.`,`La ai jubab da ${data.provider||'Magisterium AI'}.`);
    }catch(e){
      status.textContent=t('Could not reach the Mercy Catholic AI service. Please try again later.','Ym lah ban ioh ia ka Mercy Catholic AI service. Sngewbha pyrshang biang hadien.');
    }finally{
      if(submit)submit.disabled=false;
    }
  });
})();
