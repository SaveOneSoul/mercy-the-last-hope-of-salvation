(function(){
  var root=document.querySelector('[data-save-one-soul-campaign]');
  if(!root)return;

  /* Own the campaign controls on this page. This prevents the generic
     mercury.js handler from attaching a second set of click listeners. */
  root.removeAttribute('data-save-one-soul-campaign');

  var script=document.currentScript;
  var scriptUrl=script&&script.src?script.src:'';
  var configUrl=scriptUrl?scriptUrl.replace(/save-one-soul-campaign\.js(?:\?.*)?$/,'analytics-config.json'):'';
  var isKh=location.pathname.indexOf('/kh/')!==-1;
  var tokenKey='mercy-save-one-soul-token-v1';
  var statusEl=root.querySelector('[data-campaign-status]');
  var joinBtn=root.querySelector('[data-campaign-join]');
  var completeBtn=root.querySelector('[data-campaign-complete]');
  var dayBtns=root.querySelectorAll('[data-campaign-day]');
  var joinedCount=root.querySelector('[data-campaign-joined-count]');
  var completedCount=root.querySelector('[data-campaign-completed-count]');
  var apiBase='';
  var busy=false;
  var currentState={joined:false,days:[false,false,false,false,false,false,false],days_completed:0,completed:false};

  function msg(en,kh){return isKh?kh:en;}
  function setStatus(text){if(statusEl)statusEl.textContent=text;}
  function getToken(){try{return localStorage.getItem(tokenKey)||'';}catch(e){return '';}}
  function saveToken(token){try{localStorage.setItem(tokenKey,token);}catch(e){}}

  function makeToken(){
    try{
      if(window.crypto&&typeof window.crypto.randomUUID==='function')return window.crypto.randomUUID();
      if(window.crypto&&typeof window.crypto.getRandomValues==='function'){
        var bytes=new Uint8Array(24);window.crypto.getRandomValues(bytes);var out='';
        for(var i=0;i<bytes.length;i++)out+=('0'+bytes[i].toString(16)).slice(-2);
        return out;
      }
    }catch(e){}
    return String(Date.now())+'-'+String(Math.random()).slice(2)+'-'+String(Math.random()).slice(2);
  }

  function dayLabel(day,done){
    return isKh?'Sngi '+day+(done?' ✓':''):'Day '+day+(done?' ✓':'');
  }

  function setBusy(value){
    busy=value;
    render(currentState);
  }

  function render(state){
    if(state)currentState=state;
    var joined=!!currentState.joined;
    var days=currentState.days&&currentState.days.length===7?currentState.days:[false,false,false,false,false,false,false];
    if(joinBtn){
      joinBtn.disabled=busy||joined;
      joinBtn.textContent=joined?msg('Mission joined','La rung sha ka mission'):msg('Join the 7-Day Mission','Rung sha ka 7-Sngi Mission');
    }
    for(var i=0;i<dayBtns.length;i++){
      var day=Number(dayBtns[i].getAttribute('data-campaign-day'));
      var done=!!days[day-1];
      dayBtns[i].disabled=busy||!joined||done;
      if(done)dayBtns[i].classList.add('primary');else dayBtns[i].classList.remove('primary');
      dayBtns[i].textContent=dayLabel(day,done);
    }
    if(completeBtn){
      var allDone=true;
      for(var j=0;j<7;j++)if(!days[j])allDone=false;
      completeBtn.disabled=busy||!joined||!allDone||!!currentState.completed;
      completeBtn.textContent=currentState.completed?msg('Mission completed ✓','La pyndep ia ka mission ✓'):msg('I completed the 7 days','Nga la pyndep 7 sngi');
    }
  }

  function request(method,path,payload,callback){
    if(!apiBase){callback(new Error('api_not_configured'));return;}
    var xhr=new XMLHttpRequest();
    xhr.open(method,apiBase+path,true);
    xhr.timeout=20000;
    if(payload!==null)xhr.setRequestHeader('Content-Type','application/json');
    xhr.onreadystatechange=function(){
      if(xhr.readyState!==4)return;
      var body=null;
      try{body=xhr.responseText?JSON.parse(xhr.responseText):null;}catch(e){}
      if(xhr.status>=200&&xhr.status<300){callback(null,body,xhr.status);return;}
      var err=new Error('api_error');err.status=xhr.status;err.body=body;callback(err,body,xhr.status);
    };
    xhr.onerror=function(){callback(new Error('network_error'));};
    xhr.ontimeout=function(){callback(new Error('timeout'));};
    try{xhr.send(payload===null?null:JSON.stringify(payload));}catch(e){callback(e);}
  }

  function loadConfig(callback){
    if(window.MERCY_API_BASE){apiBase=String(window.MERCY_API_BASE).replace(/\/$/,'');callback();return;}
    if(!configUrl){callback(new Error('config_missing'));return;}
    var xhr=new XMLHttpRequest();xhr.open('GET',configUrl,true);xhr.timeout=10000;
    xhr.onreadystatechange=function(){
      if(xhr.readyState!==4)return;
      if(xhr.status>=200&&xhr.status<300){
        try{var cfg=JSON.parse(xhr.responseText);apiBase=String(cfg.mercy_api_base||'').replace(/\/$/,'');}catch(e){}
      }
      callback(apiBase?null:new Error('config_missing'));
    };
    xhr.onerror=function(){callback(new Error('config_missing'));};
    xhr.ontimeout=function(){callback(new Error('config_missing'));};
    xhr.send(null);
  }

  function loadStats(){
    request('GET','/api/save-one-soul/stats',null,function(err,s){
      if(err){if(joinedCount)joinedCount.textContent='—';if(completedCount)completedCount.textContent='—';return;}
      if(joinedCount)joinedCount.textContent=String(Number(s.joined||0));
      if(completedCount)completedCount.textContent=String(Number(s.completed||0));
    });
  }

  function verifyDay(token,day,attempt){
    request('GET','/api/save-one-soul/status/'+encodeURIComponent(token),null,function(err,state){
      if(!err&&state&&state.days&&state.days[day-1]){
        currentState=state;setBusy(false);render(state);loadStats();
        setStatus(msg('Day '+day+' saved securely. '+(state.days_completed||0)+' of 7 days completed.','La save bha ia ka Sngi '+day+'. La pyndep '+(state.days_completed||0)+' na 7 sngi.'));
        return;
      }
      if(attempt<1){
        setStatus(msg('Verifying Day '+day+'… retrying once.','Dang verify ia ka Sngi '+day+'… pyrshang biang shisien.'));
        saveDay(token,day,attempt+1);return;
      }
      setBusy(false);
      setStatus(msg('Day '+day+' was not confirmed by the server. Please tap it again.','Ym pat confirm ka server ia ka Sngi '+day+'. Sngewbha nion biang.'));
    });
  }

  function saveDay(token,day,attempt){
    request('POST','/api/save-one-soul/day',{token:token,language:isKh?'kha':'en',day:day},function(err,state){
      if(err){
        if(attempt<1){saveDay(token,day,attempt+1);return;}
        setBusy(false);
        setStatus(msg('Could not save Day '+day+'. Check your connection and tap it again.','Ym lah ban save ia ka Sngi '+day+'. Check internet bad nion biang.'));
        return;
      }
      if(state)currentState=state;
      verifyDay(token,day,attempt);
    });
  }

  function onDayClick(btn){
    if(busy){setStatus(msg('Please wait while the previous day is being saved.','Sngewbha ap katba dang save ia ka sngi kaba shuwa.'));return;}
    var token=getToken();if(!token){setStatus(msg('Join the mission first.','Rung shwa sha ka mission.'));return;}
    var day=Number(btn.getAttribute('data-campaign-day'));
    if(!day||day<1||day>7)return;
    busy=true;render(currentState);
    setStatus(msg('Saving Day '+day+'…','Dang save ia ka Sngi '+day+'…'));
    saveDay(token,day,0);
  }

  function joinMission(){
    if(busy)return;
    var token=getToken();if(!token){token=makeToken();saveToken(token);}
    busy=true;render(currentState);setStatus(msg('Joining anonymously…','Dang rung anonymously…'));
    request('POST','/api/save-one-soul/join',{token:token,language:isKh?'kha':'en'},function(err,state){
      setBusy(false);
      if(err){setStatus(msg('Could not join right now. Please try again.','Ym lah ban rung mynta. Sngewbha pyrshang biang.'));return;}
      render(state);loadStats();setStatus(msg('Mission joined. Your anonymous progress is now saved securely.','La rung sha ka mission. Ka anonymous progress jong phi ka la save securely.'));
    });
  }

  function completeMission(){
    if(busy)return;
    var token=getToken();if(!token)return;
    busy=true;render(currentState);setStatus(msg('Recording mission completion…','Dang save ia ka jingpyndep mission…'));
    request('POST','/api/save-one-soul/complete',{token:token,language:isKh?'kha':'en'},function(err,state){
      setBusy(false);
      if(err){
        setStatus(err.status===409?msg('Please save all seven days first.','Sngewbha save shwa ia baroh 7 sngi.'):msg('Could not complete the mission right now.','Ym lah ban pyndep ia ka mission mynta.'));
        return;
      }
      render(state);loadStats();setStatus(msg('Thank you. Your seven-day mission has been recorded as completed.','Khublei. La record ba phi la pyndep ia ka 7-sngi mission.'));
    });
  }

  if(joinBtn)joinBtn.addEventListener('click',joinMission);
  for(var b=0;b<dayBtns.length;b++)(function(btn){btn.addEventListener('click',function(){onDayClick(btn);});})(dayBtns[b]);
  if(completeBtn)completeBtn.addEventListener('click',completeMission);

  render(currentState);
  loadConfig(function(err){
    if(err){setStatus(msg('The Mercy API is not configured on this page.','Ym pat configure ia ka Mercy API ha kane ka page.'));return;}
    loadStats();
    var token=getToken();
    if(!token){setStatus(msg('No personal data is requested. Join when you are ready.','Ym kyrpad personal data. Rung haba phi la ready.'));return;}
    request('GET','/api/save-one-soul/status/'+encodeURIComponent(token),null,function(statusErr,state){
      if(statusErr){render({joined:false,days:[false,false,false,false,false,false,false],days_completed:0,completed:false});return;}
      render(state);
      setStatus(state.completed?msg('Thank you for completing the seven-day prayer journey.','Khublei ba phi la pyndep ia ka lynti jingduwai 7 sngi.'):msg((state.days_completed||0)+' of 7 days are securely recorded.','La save bha '+(state.days_completed||0)+' na 7 sngi.'));
    });
  });
})();