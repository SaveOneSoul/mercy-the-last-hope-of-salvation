(function(){
  'use strict';
  var DEFAULT_API='https://mercy-api-h6icv7sk7a-el.a.run.app';
  var script=document.currentScript;
  var scriptUrl=script&&script.src?script.src:'';
  var isKh=location.pathname.indexOf('/kh/')!==-1;
  function t(en,kh){return isKh?kh:en;}
  function stripSlash(v){return String(v||'').replace(/\/$/,'');}
  function safeJson(text){try{return JSON.parse(text||'{}');}catch(e){return {};}}
  function configUrl(){
    if(!scriptUrl)return '';
    var clean=scriptUrl.split('#')[0].split('?')[0];
    return clean.substring(0,clean.lastIndexOf('/')+1)+'analytics-config.json';
  }
  function resolveApi(){
    return new Promise(function(resolve){
      var fallback=stripSlash(window.MERCY_API_BASE||DEFAULT_API)||DEFAULT_API;
      var url=configUrl();
      if(!url){resolve(fallback);return;}
      try{
        fetch(url,{cache:'no-store'}).then(function(r){return r.ok?r.json():{};}).then(function(cfg){resolve(stripSlash(cfg.mercy_api_base||fallback)||fallback);}).catch(function(){resolve(fallback);});
      }catch(e){resolve(fallback);}
    });
  }
  function ensureStatus(form){
    var status=form.querySelector('.status,[data-form-status]');
    if(status)return status;
    status=document.createElement('div');status.className='status';status.setAttribute('role','status');status.setAttribute('aria-live','polite');form.appendChild(status);return status;
  }
  function setBusy(form,busy,label){
    var btn=form.querySelector('button[type="submit"],input[type="submit"]');
    if(!btn)return;
    if(busy){btn.dataset.originalText=btn.tagName==='INPUT'?btn.value:btn.textContent;btn.disabled=true;if(btn.tagName==='INPUT')btn.value=label;else btn.textContent=label;}
    else{btn.disabled=false;var old=btn.dataset.originalText;if(old){if(btn.tagName==='INPUT')btn.value=old;else btn.textContent=old;delete btn.dataset.originalText;}}
  }
  function fieldValue(form,name){var el=form.elements&&form.elements[name];return el?String(el.value||'').trim():'';}
  function submitJson(form,endpoint,payload,successText){
    var status=ensureStatus(form);
    setBusy(form,true,t('Sending…','Dang phah…'));
    status.textContent=t('Sending securely…','Dang phah secure…');
    status.classList.remove('error','success');
    resolveApi().then(function(api){
      return fetch(api+endpoint,{method:'POST',headers:{'Content-Type':'application/json','Accept':'application/json'},body:JSON.stringify(payload),cache:'no-store'});
    }).then(function(r){
      return r.text().then(function(text){var data=safeJson(text);if(!r.ok){var err=new Error((data&&data.detail)||('HTTP '+r.status));err.status=r.status;throw err;}return data;});
    }).then(function(data){
      form.reset();
      status.textContent=successText+(data&&data.id?' #'+data.id:'');
      status.classList.remove('error');status.classList.add('success');
    }).catch(function(err){
      status.textContent=t('Your message could not be sent right now. Please check your connection and try again.','Ym lah ban phah ia ka message mynta. Sngewbha check ia ka internet bad pyrshang biang.');
      status.classList.remove('success');status.classList.add('error');
      try{console.error('Mercy form submission failed',err);}catch(e){}
    }).finally(function(){setBusy(form,false,'');});
  }
  function bindPrayer(form){
    form.addEventListener('submit',function(e){
      e.preventDefault();e.stopImmediatePropagation();
      var intention=fieldValue(form,'intention');
      if(intention.length<2){var s=ensureStatus(form);s.textContent=t('Please enter your prayer intention before sending.','Sngewbha thoh ia ka prayer intention shwa ban phah.');s.classList.add('error');return;}
      submitJson(form,'/api/prayer-intentions',{name:fieldValue(form,'name')||null,intention:intention,website:fieldValue(form,'website')},t('Your prayer intention was received securely.','La pdiang secure ia ka prayer intention jong phi.'));
    },true);
  }
  function bindContact(form){
    form.addEventListener('submit',function(e){
      e.preventDefault();e.stopImmediatePropagation();
      var name=fieldValue(form,'name'),email=fieldValue(form,'email'),topic=fieldValue(form,'subject')||fieldValue(form,'topic')||'Website message',message=fieldValue(form,'message'),phone=fieldValue(form,'phone');
      var finalMessage=(phone?'WhatsApp / phone: '+phone+'\n\n':'')+message;
      var payload={name:name,email:email,subject:topic.slice(0,160),message:finalMessage,website:fieldValue(form,'website')};
      if(!payload.name||!payload.email||payload.message.length<2){var s=ensureStatus(form);s.textContent=t('Please complete your name, email and message before sending.','Sngewbha pyndep ia ka kyrteng, email bad message shwa ban phah.');s.classList.add('error');return;}
      submitJson(form,'/api/contact',payload,t('Your message was received securely.','La pdiang secure ia ka message jong phi.'));
    },true);
  }
  document.querySelectorAll('[data-prayer-form]').forEach(bindPrayer);
  document.querySelectorAll('[data-contact-form]').forEach(bindContact);
})();
