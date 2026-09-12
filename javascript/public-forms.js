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
  function isChecked(form,name){var el=form.elements&&form.elements[name];return !!(el&&el.checked);}
  function fail(form,message){var s=ensureStatus(form);s.textContent=message;s.classList.remove('success');s.classList.add('error');}
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
      var message=t('Your message could not be sent right now. Please check the required fields and your connection, then try again.','Ym lah ban phah ia ka message mynta. Sngewbha check ia ki field ba donkam bad internet, nangta pyrshang biang.');
      if(err&&err.message==='explicit_name_sharing_consent_required')message=t('Worldwide sharing requires explicit consent to share your name and intention.','Ka worldwide sharing ka donkam explicit consent ban share ia ka kyrteng bad intention jong phi.');
      if(err&&err.message==='priest_distribution_consent_required')message=t('Please consent to sharing the Mass intention with verified priests.','Sngewbha ai consent ban share ia ka Mass intention bad ki verified priest.');
      status.textContent=message;
      status.classList.remove('success');status.classList.add('error');
      try{console.error('Mercy form submission failed',err);}catch(e){}
    }).finally(function(){setBusy(form,false,'');});
  }
  function bindPrayer(form){
    form.addEventListener('submit',function(e){
      e.preventDefault();e.stopImmediatePropagation();
      var intention=fieldValue(form,'intention');
      if(intention.length<2){fail(form,t('Please enter your prayer intention before sending.','Sngewbha thoh ia ka prayer intention shwa ban phah.'));return;}
      submitJson(form,'/api/prayer-intentions',{name:fieldValue(form,'name')||null,intention:intention,website:fieldValue(form,'website')},t('Your prayer intention was received securely.','La pdiang secure ia ka prayer intention jong phi.'));
    },true);
  }
  function bindPrayerNetwork(form){
    form.addEventListener('submit',function(e){
      e.preventDefault();e.stopImmediatePropagation();
      var name=fieldValue(form,'name'),intention=fieldValue(form,'intention'),share=isChecked(form,'share_worldwide');
      if(name.length<2){fail(form,t('Please enter the name to accompany this prayer intention.','Sngewbha thoh ia ka kyrteng bad ka prayer intention.'));return;}
      if(intention.length<2){fail(form,t('Please enter your prayer intention before sending.','Sngewbha thoh ia ka prayer intention shwa ban phah.'));return;}
      submitJson(form,'/api/prayer-network/requests',{
        name:name,
        intention:intention,
        country:fieldValue(form,'country')||null,
        language:isKh?'kha':'en',
        share_worldwide:share,
        consent_name_sharing:share,
        website:fieldValue(form,'website')
      },share?t('Your prayer intention was received and is eligible for approved worldwide prayer sharing.','La pdiang ia ka prayer intention bad ka long eligible na ka bynta worldwide prayer sharing ba la approve.'):t('Your prayer intention was received securely by Mercy Admin.','La pdiang secure ia ka prayer intention jong phi ha Mercy Admin.'));
    },true);
  }
  function bindMass(form){
    form.addEventListener('submit',function(e){
      e.preventDefault();e.stopImmediatePropagation();
      var consent=isChecked(form,'consent_priest_distribution');
      if(!consent){fail(form,t('Please consent to sharing this Mass intention with verified Catholic priests.','Sngewbha ai consent ban share ia kane ka Mass intention bad ki verified Catholic priest.'));return;}
      var payload={
        requester_name:fieldValue(form,'requester_name'),
        requester_email:fieldValue(form,'requester_email'),
        intention_for_name:fieldValue(form,'intention_for_name'),
        intention_text:fieldValue(form,'intention_text'),
        life_status:fieldValue(form,'life_status')||'living',
        masses_requested:Number(fieldValue(form,'masses_requested')||1),
        consent_priest_distribution:true,
        website:fieldValue(form,'website')
      };
      if(payload.requester_name.length<2||!payload.requester_email||payload.intention_for_name.length<2||payload.intention_text.length<2){fail(form,t('Please complete the requester, email, person/name and Mass intention fields.','Sngewbha pyndep ia ki field jong requester, email, kyrteng bad Mass intention.'));return;}
      submitJson(form,'/api/mass-intentions',payload,t('Your Mass intention was received for verified-priest assignment. Mercy does not collect a Mass offering in this phase.','La pdiang ia ka Mass intention jong phi na ka bynta verified-priest assignment. Mercy kam shim Mass offering ha kane ka phase.'));
    },true);
  }
  function bindPriest(form){
    form.addEventListener('submit',function(e){
      e.preventDefault();e.stopImmediatePropagation();
      if(!isChecked(form,'declaration_authorized')){fail(form,t('Please confirm the priest authorization and verification declaration.','Sngewbha pynskhem ia ka priest authorization bad verification declaration.'));return;}
      var payload={
        full_name:fieldValue(form,'full_name'),
        email:fieldValue(form,'email'),
        country:fieldValue(form,'country'),
        diocese_or_institute:fieldValue(form,'diocese_or_institute'),
        parish_or_community:fieldValue(form,'parish_or_community')||null,
        bishop_or_superior:fieldValue(form,'bishop_or_superior'),
        verification_contact:fieldValue(form,'verification_contact'),
        declaration_authorized:true,
        website:fieldValue(form,'website')
      };
      if(payload.full_name.length<3||!payload.email||payload.country.length<2||payload.diocese_or_institute.length<2||payload.bishop_or_superior.length<2||payload.verification_contact.length<3){fail(form,t('Please complete all required priest-verification fields.','Sngewbha pyndep ia baroh ki priest-verification field ba donkam.'));return;}
      submitJson(form,'/api/priest-network/register',payload,t('Priest registration received. It remains pending until Mercy Admin independently verifies the diocese, institute or superior.','La pdiang ia ka priest registration. Kan dang pending tad haduh ba Mercy Admin ka verify ia ka diocese, institute ne superior.'));
    },true);
  }
  function bindContact(form){
    form.addEventListener('submit',function(e){
      e.preventDefault();e.stopImmediatePropagation();
      var name=fieldValue(form,'name'),email=fieldValue(form,'email'),topic=fieldValue(form,'subject')||fieldValue(form,'topic')||'Website message',message=fieldValue(form,'message'),phone=fieldValue(form,'phone');
      var finalMessage=(phone?'WhatsApp / phone: '+phone+'\n\n':'')+message;
      var payload={name:name,email:email,subject:topic.slice(0,160),message:finalMessage,website:fieldValue(form,'website')};
      if(!payload.name||!payload.email||payload.message.length<2){fail(form,t('Please complete your name, email and message before sending.','Sngewbha pyndep ia ka kyrteng, email bad message shwa ban phah.'));return;}
      submitJson(form,'/api/contact',payload,t('Your message was received securely.','La pdiang secure ia ka message jong phi.'));
    },true);
  }
  document.querySelectorAll('[data-prayer-form]').forEach(bindPrayer);
  document.querySelectorAll('[data-prayer-network-form]').forEach(bindPrayerNetwork);
  document.querySelectorAll('[data-mass-intention-form]').forEach(bindMass);
  document.querySelectorAll('[data-priest-registration-form]').forEach(bindPriest);
  document.querySelectorAll('[data-contact-form]').forEach(bindContact);
})();
