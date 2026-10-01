(function(){
  'use strict';
  var avatar=document.querySelector('.mercy-digital-human');
  var visualStatus=document.querySelector('[data-avatar-visual-status]');
  if(!avatar){window.MercyAvatar3D={setState:function(){},setViseme:function(){},pulseSpeech:function(){}};return;}
  var visemeTimer=null;
  function setState(state){
    state=state||'idle';
    avatar.dataset.state=state;
    if(visualStatus)visualStatus.textContent=state==='idle'?'Ready':state.charAt(0).toUpperCase()+state.slice(1);
    if(state!=='speaking')avatar.style.setProperty('--mouth-open','0');
  }
  function setViseme(value){
    var v=Math.max(0,Math.min(1,Number(value)||0));
    avatar.style.setProperty('--mouth-open',String(v));
  }
  function pulseSpeech(){
    clearTimeout(visemeTimer);
    setViseme(.35+Math.random()*.65);
    visemeTimer=setTimeout(function(){setViseme(.12);},100);
  }
  window.MercyAvatar3D={setState:setState,setViseme:setViseme,pulseSpeech:pulseSpeech};
  setState('idle');
})();