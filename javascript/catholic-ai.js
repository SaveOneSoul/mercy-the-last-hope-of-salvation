(function(){
  var DEFAULT_API_BASE='https://mercy-api-h6icv7sk7a-el.a.run.app';
  var scriptEl=document.currentScript;
  var scriptUrl=scriptEl&&scriptEl.src?scriptEl.src:'';
  var form=document.querySelector('[data-catholic-ai-form]');
  var input=document.querySelector('[data-catholic-ai-input]');
  var status=document.querySelector('[data-catholic-ai-status]');
  var answerBox=document.querySelector('[data-catholic-ai-answer]');
  var answerText=document.querySelector('[data-catholic-ai-text]');
  var sourceBox=document.querySelector('[data-catholic-ai-sources]');
  var relatedBox=document.querySelector('[data-catholic-ai-related]');
  var actionBar=document.querySelector('[data-catholic-ai-actions]');
  var clearBtn=document.querySelector('[data-catholic-ai-clear]');
  var undoBtn=document.querySelector('[data-catholic-ai-undo]');

  // Only the core question/answer UI is required. Optional action controls must
  // never prevent the AI form from working when an older page is cached.
  if(!form||!input||!status||!answerBox||!answerText||!sourceBox||!relatedBox)return;

  var isKh=location.pathname.indexOf('/kh/')!==-1;
  function t(en,kh){return isKh?kh:en;}
  var currentResult=null;
  var clearedResult=null;

  function clearNode(node){while(node.firstChild)node.removeChild(node.firstChild);}

  async function apiBase(){
    var base=(window.MERCY_API_BASE||DEFAULT_API_BASE).replace(/\/$/,'');
    if(!scriptUrl)return base;
    try{
      var r=await fetch(new URL('analytics-config.json',scriptUrl),{cache:'no-store'});
      if(r.ok){
        var j=await r.json();
        base=(j.mercy_api_base||base||DEFAULT_API_BASE).replace(/\/$/,'');
      }
    }catch(e){
      // The Cloud Run URL is public configuration, not a secret. Keep using the
      // known-good endpoint when mobile caching or config retrieval fails.
      base=(base||DEFAULT_API_BASE).replace(/\/$/,'');
    }
    return base||DEFAULT_API_BASE;
  }

  function resetDisplay(){
    answerBox.hidden=true;
    clearNode(answerText);
    clearNode(sourceBox);
    clearNode(relatedBox);
  }

  function updateActions(){
    if(!actionBar||!clearBtn||!undoBtn)return;
    actionBar.hidden=!currentResult&&!clearedResult;
    clearBtn.disabled=!currentResult||answerBox.hidden;
    undoBtn.disabled=!clearedResult;
  }

  function appendInline(parent,text){
    var pattern=/(\[\^(\d+)\])|(\*\*([^*\n]+)\*\*)|(`([^`\n]+)`)|(\[([^\]\n]+)\]\((https?:\/\/[^\s)]+)\))|(\*([^*\n]+)\*)/g;
    var last=0,match;
    while((match=pattern.exec(text))!==null){
      if(match.index>last)parent.appendChild(document.createTextNode(text.slice(last,match.index)));
      if(match[2]){
        var n=match[2],sup=document.createElement('sup'),a=document.createElement('a');
        sup.className='ai-citation-ref';a.href='#ai-source-'+n;a.textContent='['+n+']';
        a.setAttribute('aria-label',t('Go to source '+n,'Peit ia ka source '+n));
        sup.appendChild(a);parent.appendChild(sup);
      }else if(match[4]){var strong=document.createElement('strong');strong.textContent=match[4];parent.appendChild(strong);
      }else if(match[6]){var code=document.createElement('code');code.textContent=match[6];parent.appendChild(code);
      }else if(match[8]&&match[9]){var link=document.createElement('a');link.href=match[9];link.target='_blank';link.rel='noopener noreferrer';link.textContent=match[8];parent.appendChild(link);
      }else if(match[11]){var em=document.createElement('em');em.textContent=match[11];parent.appendChild(em);}
      last=pattern.lastIndex;
    }
    if(last<text.length)parent.appendChild(document.createTextNode(text.slice(last)));
  }

  function renderMarkdown(text){
    clearNode(answerText);
    answerText.classList.add('ai-markdown');
    var lines=String(text||'').replace(/\r\n?/g,'\n').split('\n');
    var paragraph=[],list=null,listType='';
    function flushParagraph(){if(!paragraph.length)return;var p=document.createElement('p');appendInline(p,paragraph.join(' ').trim());answerText.appendChild(p);paragraph=[];}
    function closeList(){list=null;listType='';}
    function ensureList(type){if(list&&listType===type)return list;closeList();list=document.createElement(type);listType=type;answerText.appendChild(list);return list;}
    lines.forEach(function(raw){
      var line=raw.trim();
      if(!line){flushParagraph();closeList();return;}
      var heading=line.match(/^(#{1,6})\s+(.+)$/);
      if(heading){flushParagraph();closeList();var h=document.createElement(heading[1].length<=2?'h3':'h4');appendInline(h,heading[2].trim());answerText.appendChild(h);return;}
      var ordered=line.match(/^\d+[.)]\s+(.+)$/);
      if(ordered){flushParagraph();var ol=ensureList('ol'),oli=document.createElement('li');appendInline(oli,ordered[1]);ol.appendChild(oli);return;}
      var unordered=line.match(/^[-*+]\s+(.+)$/);
      if(unordered){flushParagraph();var ul=ensureList('ul'),uli=document.createElement('li');appendInline(uli,unordered[1]);ul.appendChild(uli);return;}
      if(/^>\s?/.test(line)){flushParagraph();closeList();var q=document.createElement('blockquote');appendInline(q,line.replace(/^>\s?/,''));answerText.appendChild(q);return;}
      closeList();paragraph.push(line);
    });
    flushParagraph();
  }

  function sourceNumber(source,index){
    var id=source&&source.id?source.id:'';
    var match=String(id).match(/(?:mag-|source-)?(\d+)$/i);
    return match?match[1]:String(index+1);
  }

  function renderSources(sources){
    clearNode(sourceBox);
    if(!Array.isArray(sources)||!sources.length)return;
    var h=document.createElement('h3');h.textContent=t('Catholic sources','Ki Catholic source');sourceBox.appendChild(h);
    var ol=document.createElement('ol');ol.className='source-list ai-source-list';
    sources.forEach(function(source,index){
      var n=sourceNumber(source,index),li=document.createElement('li');li.id='ai-source-'+n;li.value=Number(n)||index+1;
      var title=(source.title||t('Catholic source','Catholic source')).trim();
      if(source.url){var a=document.createElement('a');a.href=source.url;a.target='_blank';a.rel='noopener noreferrer';a.textContent=title;li.appendChild(a);}else{var strong=document.createElement('strong');strong.textContent=title;li.appendChild(strong);}
      var details=[];if(source.authority)details.push(source.authority);if(source.reference)details.push(source.reference);
      if(details.length)li.appendChild(document.createTextNode(' — '+details.join(' · ')));
      var back=document.createElement('a');back.className='ai-source-back';back.href='#main';back.textContent=' ↥';back.setAttribute('aria-label',t('Back to answer','Phai sha ka jubab'));li.appendChild(back);
      ol.appendChild(li);
    });
    sourceBox.appendChild(ol);
  }

  function renderRelated(questions){
    clearNode(relatedBox);
    if(!Array.isArray(questions)||!questions.length)return;
    var h=document.createElement('h3');h.textContent=t('Related questions','Kiwei ki jingkylli kiba iadei');relatedBox.appendChild(h);
    var div=document.createElement('div');div.className='btns';
    questions.forEach(function(question){var b=document.createElement('button');b.type='button';b.className='btn secondary';b.textContent=question;b.addEventListener('click',function(){input.value=question;input.focus();window.scrollTo({top:form.getBoundingClientRect().top+window.scrollY-110,behavior:'smooth'});});div.appendChild(b);});
    relatedBox.appendChild(div);
  }

  function renderResult(data,restored){
    renderMarkdown(data.reply||'');renderSources(data.sources||[]);renderRelated(data.related_questions||[]);
    answerBox.hidden=false;currentResult=data;updateActions();
    status.textContent=restored?t('Cleared response restored.','La pynphai biang ia ka jubab ba la clear.'):t('Answer provided by '+(data.provider||'Magisterium AI')+'.','La ai jubab da '+(data.provider||'Magisterium AI')+'.');
    try{answerBox.scrollIntoView({behavior:'smooth',block:'start'});}catch(e){answerBox.scrollIntoView();}
  }

  if(clearBtn)clearBtn.addEventListener('click',function(){if(!currentResult)return;clearedResult=currentResult;currentResult=null;resetDisplay();status.textContent=t('Response cleared. Use Undo Clear to restore it.','La clear ia ka jubab. Pyndonkam Undo Clear ban pynphai biang.');updateActions();try{clearBtn.blur();}catch(e){}});
  if(undoBtn)undoBtn.addEventListener('click',function(){if(!clearedResult)return;var restore=clearedResult;clearedResult=null;renderResult(restore,true);try{undoBtn.blur();}catch(e){}});

  function errorMessage(statusCode,detail){
    if(detail==='magisterium_not_configured')return t('Catholic AI is installed, but the Magisterium API key has not yet been configured on the Mercy backend.','La install ia ka Catholic AI, hynrei ym pat configure ia ka Magisterium API key ha Mercy backend.');
    if(statusCode===429)return t('The Catholic AI request limit has been reached. Please try again later.','La poi sha ka request limit jong Catholic AI. Sngewbha pyrshang biang hadien.');
    if(statusCode===504)return t('Magisterium AI took too long to respond. Please try again.','Magisterium AI ka shim por palat ban jubab. Sngewbha pyrshang biang.');
    return t('Catholic AI is temporarily unavailable. Please try again later.','Catholic AI kam treikam shipor. Sngewbha pyrshang biang hadien.');
  }

  async function fetchChat(url,options){
    var lastError=null;
    for(var attempt=0;attempt<2;attempt++){
      try{return await fetch(url,options);}catch(e){lastError=e;if(attempt===0)await new Promise(function(resolve){setTimeout(resolve,700);});}
    }
    throw lastError||new Error('network_error');
  }

  form.addEventListener('submit',async function(e){
    e.preventDefault();
    var question=input.value.trim();if(question.length<2)return;
    resetDisplay();currentResult=null;updateActions();
    status.textContent=t('Connecting to Catholic AI…','Dang connect sha Catholic AI…');
    var api=await apiBase();
    var submit=form.querySelector('button[type="submit"]');if(submit)submit.disabled=true;
    status.textContent=t('Consulting Magisterium AI and Catholic sources…','Dang wad ha Magisterium AI bad ki Catholic source…');
    try{
      var r=await fetchChat(api+'/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:question,language:isKh?'kha':'en'}),cache:'no-store'});
      var data={};try{data=await r.json();}catch(parseError){}
      if(!r.ok){status.textContent=errorMessage(r.status,data.detail);return;}
      clearedResult=null;renderResult(data,false);
    }catch(err){
      status.textContent=t('Could not reach the Mercy Catholic AI service. Check your connection and try again.','Ym lah ban ioh ia ka Mercy Catholic AI service. Peit ia ka internet connection bad pyrshang biang.');
    }finally{if(submit)submit.disabled=false;updateActions();}
  });

  updateActions();
})();
