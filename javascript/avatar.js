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

  var history=[],lastReply='',recognition=null,listening=false,speaking=false,currentAudio=null;
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
  function browserSpeak(text){
    if(!('speechSynthesis' in window)){setState('idle','Speech output is not supported by this browser.');return;}
    window.speechSynthesis.cancel();
    var u=new SpeechSynthesisUtterance(text);
    u.lang='en-IN';
    var voices=window.speechSynthesis.getVoices?window.speechSynthesis.getVoices():[];
    var preferred=voices.find(function(v){return /female|woman|zira|samantha|veena|google uk english female/i.test((v.name||"")+" "+(v.voiceURI||""));})||voices.find(function(v){return /^en[-_](IN|GB|US)/i.test(v.lang||"");});
    if(preferred)u.voice=preferred;
    u.rate=.9;u.pitch=1.08;u.volume=.92;
    u.onstart=function(){speaking=true;setState('speaking','Speaking…');if(window.MercyAvatar3D)window.MercyAvatar3D.setViseme(.55);};
    u.onboundary=function(){if(window.MercyAvatar3D)window.MercyAvatar3D.pulseSpeech();};
    u.onend=function(){speaking=false;if(window.MercyAvatar3D)window.MercyAvatar3D.setViseme(0);setState('idle','Ready.');};
    u.onerror=function(){speaking=false;if(window.MercyAvatar3D)window.MercyAvatar3D.setViseme(0);setState('idle','Speech output stopped.');};
    window.speechSynthesis.speak(u);
  }
  async function speakText(text){
    if(currentAudio){try{currentAudio.pause();}catch(e){}currentAudio=null;}
    try{
      var r=await fetch(base+'/api/avatar/speak',{method:'POST',cache:'no-store',credentials:'omit',referrerPolicy:'no-referrer',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text,language:document.documentElement.lang==='kha'?'kha':'en',history:[],faith_encouragement:true})});
      if(!r.ok)throw new Error('tts unavailable');
      var data=await r.json();if(!data.audio_base64)throw new Error('empty tts');
      var audio=new Audio('data:'+(data.mime_type||'audio/mpeg')+';base64,'+data.audio_base64);currentAudio=audio;
      var timers=[];(data.timings||[]).forEach(function(t,i){if(i%3!==0)return;timers.push(setTimeout(function(){if(window.MercyAvatar3D)window.MercyAvatar3D.pulseSpeech();},Math.max(0,Number(t.start)||0)*1000));});
      audio.onplay=function(){speaking=true;setState('speaking','Speaking…');};
      audio.onended=function(){timers.forEach(clearTimeout);speaking=false;currentAudio=null;if(window.MercyAvatar3D)window.MercyAvatar3D.setViseme(0);setState('idle','Ready.');};
      audio.onerror=function(){timers.forEach(clearTimeout);currentAudio=null;browserSpeak(text);};
      await audio.play();
    }catch(err){browserSpeak(text);}
  }
  if(speak)speak.addEventListener('click',function(){
    if(speaking){if(currentAudio){try{currentAudio.pause();}catch(e){}currentAudio=null;}window.speechSynthesis&&window.speechSynthesis.cancel();speaking=false;if(window.MercyAvatar3D)window.MercyAvatar3D.setViseme(0);setState('idle','Speech stopped.');}
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
    history=[];lastReply='';log.replaceChildren();if(currentAudio){try{currentAudio.pause();}catch(e){}currentAudio=null;}window.speechSynthesis&&window.speechSynthesis.cancel();
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