(function(){
  function hasLanguageControl(){
    var links=document.querySelectorAll('.topbar a.theme-btn');
    var i,text;
    for(i=0;i<links.length;i++){
      text=(links[i].textContent||'').replace(/^\s+|\s+$/g,'').toLowerCase();
      if(text==='khasi'||text==='english')return true;
    }
    return false;
  }

  function languageHref(isKh,path,name,query){
    if(isKh){
      if(path.indexOf('/kh/pages/')!==-1)return '../../pages/'+name+query;
      return '../index.html'+query;
    }
    if(path.indexOf('/pages/')!==-1)return '../kh/pages/'+name+query;
    return 'kh/index.html'+query;
  }

  function bindFallback(){
    /* If the modern site script completed navigation setup, do nothing. */
    if(hasLanguageControl())return;

    var menu=document.querySelector('.menu-btn');
    var nav=document.getElementById('main-nav');
    var themeBtn=document.querySelector('button.theme-btn');
    var path=window.location.pathname||'';
    var isKh=path.indexOf('/kh/')!==-1;
    var parts=path.split('/');
    var name=parts[parts.length-1]||'index.html';
    var query=window.location.search||'';

    if(menu&&nav){
      menu.onclick=function(){
        var open;
        if(nav.className.indexOf('open')===-1){
          nav.className=(nav.className?nav.className+' ':'')+'open';
          open=true;
        }else{
          nav.className=nav.className.replace(/(?:^|\s)open(?:\s|$)/g,' ').replace(/^\s+|\s+$/g,'');
          open=false;
        }
        menu.setAttribute('aria-expanded',open?'true':'false');
      };
    }

    if(themeBtn&&!hasLanguageControl()){
      var lang=document.createElement('a');
      lang.className='theme-btn';
      lang.style.textDecoration='none';
      lang.textContent=isKh?'English':'Khasi';
      lang.setAttribute('aria-label',isKh?'Switch to English':'Switch to Khasi');
      lang.title=isKh?'Open the same page in English':'Open the same page in Khasi';
      lang.href=languageHref(isKh,path,name,query);
      themeBtn.parentNode.insertBefore(lang,themeBtn);
    }

    /* Keep the theme control usable when the modern script failed early. */
    if(themeBtn){
      themeBtn.onclick=function(){
        var body=document.body;
        var dark=body.className.indexOf('dark')!==-1;
        if(dark){
          body.className=body.className.replace(/(?:^|\s)dark(?:\s|$)/g,' ').replace(/^\s+|\s+$/g,'');
        }else{
          body.className=(body.className?body.className+' ':'')+'dark';
        }
        try{window.localStorage.setItem('mercy-theme',dark?'light':'dark');}catch(e){}
      };
    }
  }

  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded',function(){window.setTimeout(bindFallback,0);});
  }else{
    window.setTimeout(bindFallback,0);
  }
})();
