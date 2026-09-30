(function(){
  'use strict';
  var cfg=window.MERCY_SITE_CONFIG||{};
  var base=String(cfg.apiBaseUrl||'').replace(/\/$/,'');
  var log=document.querySelector('[data-avatar-log]');
  var form=document.querySelector('[data-avatar-form]');
  var input=document.querySelector('[data-avatar-input]');
  var status=document.querySelector('[data-avatar-status]');
  var mic=document.querySelector('[data-avatar-mic]');
  var speak=document.querySelector('[data-avatar-speak]');
  var clear=document.querySelector('[data-avatar-clear]');
  var face=document.querySelector('[data-avatar-face]');
  if(!form||!input||!log||!status)return;

  var history=[],lastReply='',recognition=null,listening=false,speaking=false;
  function add(role,text){
    var wrap=document.createElement('div');wrap.className='avatar-msg '+role;
    var who=document.createElement('strong');who.textContent=role==='user'?'You':'Mercy Avatar';
    var p=document.createElement('p');p.textContent=text;
    wrap.append(who,p);log.append(wrap);log.scrollTop=log.scrollHeight;
  }
  function setState(name,text){
    if(face)face.dataset.state=name;
    status.textContent=text||name;
  }
  function speakText(text){
    if(!('speechSynthesis' in window)){setState('idle','Speech output is not supported by this browser.');return;}
    window.speechSynthesis.cancel();
    var u=new SpeechSynthesisUtterance(text);
    u.lang=document.documentElement.lang==='kha'?'en-IN':'en-IN';
    u.rate=.96;u.pitch=1;
    u.onstart=function(){speaking=true;setState('speaking','Speaking…');if(window.MercyAvatar3D)window.MercyAvatar3D.setViseme(.55);};
    u.onboundary=function(){if(window.MercyAvatar3D)window.MercyAvatar3D.pulseSpeech();};\n    u.onend=function(){speaking=false;if(window.MercyAvatar3D)window.MercyAvatar3D.setViseme(0);setState('idle','Ready.');};
    u.onerror=function(){speaking=false;if(window.MercyAvatar3D)window.MercyAvatar3D.setViseme(0);setState('idle','Speech output stopped.');};
    window.speechSynthesis.speak(u);
  }
  if(speak)speak.addEventListener('click',function(){
    if(speaking){window.speechSynthesis.cancel();speaking=false;setState('idle','Speech stopped.');}
    else if(lastReply)speakText(lastReply);
  });

  var SR=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(SR&&mic){
    recognition=new SR();recognition.continuous=false;recognition.interimResults=false;recognition.lang='en-IN';
    recognition.onstart=function(){listening=true;setState('listening','Listening…');mic.setAttribute('aria-pressed','true');};
    recognition.onend=function(){listening=false;mic.setAttribute('aria-pressed','false');if(!speaking)setState('idle','Ready.');};
    recognition.onerror=function(){setState('idle','Microphone recognition stopped. You can type instead.');};
    recognition.onresult=function(e){
      var text=e.results&&e.results[0]&&e.results[0][0]?e.results[0][0].transcript:'';
      if(text){input.value=text;input.focus();}
    };
    mic.addEventListener('click',function(){
      if(listening)recognition.stop();else{try{recognition.start();}catch(e){}}
    });
  }else if(mic){mic.disabled=true;mic.title='Speech recognition is not supported by this browser';}

  if(clear)clear.addEventListener('click',function(){
    history=[];lastReply='';log.replaceChildren();window.speechSynthesis&&window.speechSynthesis.cancel();
    add('assistant','Conversation cleared. I do not keep a transcript on this page.');setState('idle','Ready.');
  });

  form.addEventListener('submit',async function(e){
    e.preventDefault();
    var text=input.value.trim();if(text.length<2||!base)return;
    input.value='';add('user',text);setState('thinking','Thinking…');
    var body={message:text,language:document.documentElement.lang==='kha'?'kha':'en',history:history.slice(-8),faith_encouragement:true};
    try{
      var r=await fetch(base+'/api/avatar/chat',{method:'POST',cache:'no-store',credentials:'omit',referrerPolicy:'no-referrer',
        headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
      var data=await r.json().catch(function(){return {};});
      if(!r.ok)throw new Error(data.detail||'Avatar service unavailable');
      lastReply=String(data.reply||'').trim();if(!lastReply)throw new Error('Empty reply');
      add('assistant',lastReply);
      history.push({role:'user',content:text},{role:'assistant',content:lastReply.slice(0,2000)});
      if(history.length>8)history.splice(0,history.length-8);
      setState('idle','Ready · '+String(data.domain||'mission'));
      if(document.querySelector('[data-avatar-auto-speak]').checked)speakText(lastReply);
    }catch(err){
      add('assistant','The avatar service is unavailable right now. You can still use the Catholic AI and Counselling & Support pages.');
      setState('idle','Service unavailable.');
    }
  });
  add('assistant','Peace be with you. Ask about Catholic theology, philosophy, logic, science, psychology education, spiritual formation, or pastoral support.');
  setState('idle','Ready.');
})();