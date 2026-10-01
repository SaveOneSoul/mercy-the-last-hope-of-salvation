(function(){
'use strict';
var avatar=document.querySelector('[data-avatar-face]');
var label=document.querySelector('[data-avatar-visual-status]');
var mouth=document.querySelector('.mercy-svg-mouth');
var inner=document.querySelector('.mercy-svg-mouth-inner');
if(!avatar){window.MercyAvatar3D={setState:function(){},setViseme:function(){},pulseSpeech:function(){}};return;}
var timer=null;
function setState(s){s=s||'idle';avatar.dataset.state=s;if(label)label.textContent=s==='idle'?'Ready':s.charAt(0).toUpperCase()+s.slice(1);if(s!=='speaking')setViseme(0);}
function setViseme(v){v=Math.max(0,Math.min(1,Number(v)||0));if(mouth)mouth.setAttribute('transform','translate(0 '+(v*3).toFixed(1)+') scale(1 '+(1+v*.55).toFixed(2)+') translate(0 '+(-310*v*.55/(1+v*.55)).toFixed(1)+')');if(inner){inner.style.opacity=String(.15+v*.8);inner.setAttribute('transform','scale(1 '+(1+v*2.4).toFixed(2)+')');}}
function pulseSpeech(){clearTimeout(timer);setViseme(.35+Math.random()*.65);timer=setTimeout(function(){setViseme(.08);},105);}
window.MercyAvatar3D={setState:setState,setViseme:setViseme,pulseSpeech:pulseSpeech};setState('idle');
})();