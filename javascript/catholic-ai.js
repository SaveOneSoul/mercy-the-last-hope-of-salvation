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

  if(!form||!input||!status||!answerBox||!answerText||!sourceBox||!relatedBox)return;

  var isKh=location.pathname.indexOf('/kh/')!==-1;
  var currentResult=null;
  var clearedResult=null;

  function t(en,kh){return isKh?kh:en;}
  function clearNode(node){while(node.firstChild)node.removeChild(node.firstChild);}
  function safeJson(text){try{return JSON.parse(text||'{}');}catch(e){return {};}}
  function stripSlash(value){return String(value||'').replace(/\/$/,'');}

  function getConfigUrl(){
    if(!scriptUrl)return '';
    var clean=scriptUrl.split('#')[0].split('?')[0];
    var slash=clean.lastIndexOf('/');
    return slash>=0?clean.substring(0,slash+1)+'analytics-config.json':'';
  }

  function resolveApiBase(done){
    var base=stripSlash(window.MERCY_API_BASE||DEFAULT_API_BASE)||DEFAULT_API_BASE;
    var url=getConfigUrl();
    if(!url){done(base);return;}
    try{
      var xhr=new XMLHttpRequest();
      xhr.open('GET',url,true);
      xhr.timeout=8000;
      xhr.setRequestHeader('Cache-Control','no-cache');
      xhr.onreadystatechange=function(){
        if(xhr.readyState!==4)return;
        if(xhr.status>=200&&xhr.status<300){
          var cfg=safeJson(xhr.responseText);
          done(stripSlash(cfg.mercy_api_base||base||DEFAULT_API_BASE)||DEFAULT_API_BASE);
        }else{
          done(base);
        }
      };
      xhr.onerror=function(){done(base);};
      xhr.ontimeout=function(){done(base);};
      xhr.send(null);
    }catch(e){done(base);}
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
      }else if(match[4]){
        var strong=document.createElement('strong');strong.textContent=match[4];parent.appendChild(strong);
      }else if(match[6]){
        var code=document.createElement('code');code.textContent=match[6];parent.appendChild(code);
      }else if(match[8]&&match[9]){
        var link=document.createElement('a');link.href=match[9];link.target='_blank';link.rel='noopener noreferrer';link.textContent=match[8];parent.appendChild(link);
      }else if(match[11]){
        var em=document.createElement('em');em.textContent=match[11];parent.appendChild(em);
      }
      last=pattern.lastIndex;
    }
    if(last<text.length)parent.appendChild(document.createTextNode(text.slice(last)));
  }

  function renderMarkdown(text){
    clearNode(answerText);
    if(answerText.classList)answerText.classList.add('ai-markdown');
    var lines=String(text||'').replace(/\r\n?/g,'\n').split('\n');
    var paragraph=[],list=null,listType='';
    function flushParagraph(){
      if(!paragraph.length)return;
      var p=document.createElement('p');appendInline(p,paragraph.join(' ').trim());answerText.appendChild(p);paragraph=[];
    }
    function closeList(){list=null;listType='';}
    function ensureList(type){
      if(list&&listType===type)return list;
      closeList();list=document.createElement(type);listType=type;answerText.appendChild(list);return list;
    }
    for(var i=0;i<lines.length;i++){
      var line=lines[i].trim();
      if(!line){flushParagraph();closeList();continue;}
      var heading=line.match(/^(#{1,6})\s+(.+)$/);
      if(heading){
        flushParagraph();closeList();
        var h=document.createElement(heading[1].length<=2?'h3':'h4');appendInline(h,heading[2].trim());answerText.appendChild(h);continue;
      }
      var ordered=line.match(/^\d+[.)]\s+(.+)$/);
      if(ordered){
        flushParagraph();var ol=ensureList('ol'),oli=document.createElement('li');appendInline(oli,ordered[1]);ol.appendChild(oli);continue;
      }
      var unordered=line.match(/^[-*+]\s+(.+)$/);
      if(unordered){
        flushParagraph();var ul=ensureList('ul'),uli=document.createElement('li');appendInline(uli,unordered[1]);ul.appendChild(uli);continue;
      }
      if(/^>\s?/.test(line)){
        flushParagraph();closeList();var q=document.createElement('blockquote');appendInline(q,line.replace(/^>\s?/,''));answerText.appendChild(q);continue;
      }
      closeList();paragraph.push(line);
    }
    flushParagraph();
  }

  function sourceNumber(source,index){
    var id=source&&source.id?source.id:'';
    var match=String(id).match(/(?:mag-|source-)?(\d+)$/i);
    return match?match[1]:String(index+1);
  }

  function renderSources(sources){
    clearNode(sourceBox);
    if(!sources||Object.prototype.toString.call(sources)!=='[object Array]'||!sources.length)return;
    var h=document.createElement('h3');h.textContent=t('Catholic sources','Ki Catholic source');sourceBox.appendChild(h);
    var ol=document.createElement('ol');ol.className='source-list ai-source-list';
    for(var i=0;i<sources.length;i++){
      var source=sources[i]||{},n=sourceNumber(source,i),li=document.createElement('li');
      li.id='ai-source-'+n;li.value=Number(n)||i+1;
      var title=String(source.title||t('Catholic source','Catholic source')).trim();
      if(source.url){
        var a=document.createElement('a');a.href=source.url;a.target='_blank';a.rel='noopener noreferrer';a.textContent=title;li.appendChild(a);
      }else{
        var strong=document.createElement('strong');strong.textContent=title;li.appendChild(strong);
      }
      var details=[];if(source.authority)details.push(source.authority);if(source.reference)details.push(source.reference);
      if(details.length)li.appendChild(document.createTextNode(' — '+details.join(' · ')));
      var back=document.createElement('a');back.className='ai-source-back';back.href='#main';back.textContent=' ↥';back.setAttribute('aria-label',t('Back to answer','Phai sha ka jubab'));li.appendChild(back);
      ol.appendChild(li);
    }
    sourceBox.appendChild(ol);
  }

  function renderRelated(questions){
    clearNode(relatedBox);
    if(!questions||Object.prototype.toString.call(questions)!=='[object Array]'||!questions.length)return;
    var h=document.createElement('h3');h.textContent=t('Related questions','Kiwei ki jingkylli kiba iadei');relatedBox.appendChild(h);
    var div=document.createElement('div');div.className='btns';
    for(var i=0;i<questions.length;i++){
      (function(question){
        var b=document.createElement('button');b.type='button';b.className='btn secondary';b.textContent=question;
        b.addEventListener('click',function(){input.value=question;input.focus();try{window.scrollTo(0,form.getBoundingClientRect().top+window.pageYOffset-110);}catch(e){}});
        div.appendChild(b);
      })(questions[i]);
    }
    relatedBox.appendChild(div);
  }

  function renderResult(data,restored){
    renderMarkdown(data.reply||'');renderSources(data.sources||[]);renderRelated(data.related_questions||[]);
    answerBox.hidden=false;currentResult=data;updateActions();
    status.textContent=restored?t('Cleared response restored.','La pynphai biang ia ka jubab ba la clear.'):t('Answer provided by '+(data.provider||'Magisterium AI')+'.','La ai jubab da '+(data.provider||'Magisterium AI')+'.');
    try{answerBox.scrollIntoView();}catch(e){}
  }

  if(clearBtn)clearBtn.addEventListener('click',function(){
    if(!currentResult)return;clearedResult=currentResult;currentResult=null;resetDisplay();
    status.textContent=t('Response cleared. Use Undo Clear to restore it.','La clear ia ka jubab. Pyndonkam Undo Clear ban pynphai biang.');updateActions();
  });
  if(undoBtn)undoBtn.addEventListener('click',function(){
    if(!clearedResult)return;var restore=clearedResult;clearedResult=null;renderResult(restore,true);
  });

  function errorMessage(statusCode,detail){
    if(detail==='magisterium_not_configured')return t('Catholic AI is installed, but the Magisterium API key has not yet been configured on the Mercy backend.','La install ia ka Catholic AI, hynrei ym pat configure ia ka Magisterium API key ha Mercy backend.');
    if(statusCode===429)return t('The Catholic AI request limit has been reached. Please wait one minute and try again.','La poi sha ka request limit jong Catholic AI. Sngewbha ap shi minit bad pyrshang biang.');
    if(statusCode===504)return t('Magisterium AI took too long to respond. Please try again.','Magisterium AI ka shim por palat ban jubab. Sngewbha pyrshang biang.');
    return t('Catholic AI returned an error ('+statusCode+'). Please try again.','Catholic AI ka pynphai error ('+statusCode+'). Sngewbha pyrshang biang.');
  }

  function buildWireQuestion(question){
    if(!isKh)return question;
    var instruction='IMPORTANT: Answer ONLY in Khasi. Do not introduce yourself. Answer the Catholic question directly. Keep headings, explanations, conclusions and related-question suggestions in Khasi. English or Latin may appear only for proper names, official document titles, quotations, or unavoidable technical Church terms. Question: ';
    if(instruction.length+question.length<=2000)return instruction+question;
    return question;
  }

  function sendChat(api,question,attempt,done){
    var xhr;
    try{xhr=new XMLHttpRequest();}catch(e){done('unsupported',0,{});return;}
    xhr.open('POST',api+'/api/chat',true);
    xhr.timeout=115000;
    xhr.setRequestHeader('Content-Type','application/json');
    xhr.setRequestHeader('Accept','application/json');
    xhr.onreadystatechange=function(){
      if(xhr.readyState!==4)return;
      var data=safeJson(xhr.responseText);
      if(xhr.status>=200&&xhr.status<300){done(null,xhr.status,data);return;}
      if(xhr.status===0){
        if(attempt<1){setTimeout(function(){sendChat(api,question,attempt+1,done);},700);return;}
        done('network',0,data);return;
      }
      done('http',xhr.status,data);
    };
    xhr.onerror=function(){
      if(attempt<1){setTimeout(function(){sendChat(api,question,attempt+1,done);},700);return;}
      done('network',0,{});
    };
    xhr.ontimeout=function(){done('timeout',0,{});};
    try{
      xhr.send(JSON.stringify({message:buildWireQuestion(question),language:isKh?'kha':'en'}));
    }catch(e){done('network',0,{});}
  }

  form.addEventListener('submit',function(e){
    e.preventDefault();
    var question=input.value.replace(/^\s+|\s+$/g,'');
    if(question.length<2)return;
    resetDisplay();currentResult=null;updateActions();
    var submit=form.querySelector('button[type="submit"]');if(submit)submit.disabled=true;
    status.textContent=t('Connecting to Catholic AI…','Dang connect sha Catholic AI…');

    resolveApiBase(function(api){
      status.textContent=t('Consulting Magisterium AI and Catholic sources…','Dang wad ha Magisterium AI bad ki Catholic source…');
      sendChat(api,question,0,function(kind,statusCode,data){
        if(submit)submit.disabled=false;
        updateActions();
        if(!kind){clearedResult=null;renderResult(data,false);return;}
        if(kind==='timeout'){
          status.textContent=t('The mobile request timed out. Please try again on a stable connection.','Ka mobile request ka la timeout. Sngewbha pyrshang biang da ka internet connection kaba biang.');return;
        }
        if(kind==='unsupported'){
          status.textContent=t('This browser is too old to run Catholic AI. Please update Chrome/Safari or use another browser.','Kane ka browser ka rim palat ban pyniaid Catholic AI. Sngewbha update Chrome/Safari ne pyndonkam da kawei pat ka browser.');return;
        }
        if(kind==='network'){
          status.textContent=t('The phone could not reach the Mercy Cloud API. Try Wi-Fi/mobile data again or another browser.','Ka phone kam lah ban poi sha Mercy Cloud API. Pyrshang biang da Wi-Fi/mobile data ne da kawei pat ka browser.');return;
        }
        status.textContent=errorMessage(statusCode,data&&data.detail);
      });
    });
  });

  updateActions();
})();
