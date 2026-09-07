(function(){
  function languageHref(isKh,path,name,query){
    if(isKh){
      if(path.indexOf('/kh/pages/')!==-1)return '../../pages/'+name+query;
      return '../index.html'+query;
    }
    if(path.indexOf('/pages/')!==-1)return '../kh/pages/'+name+query;
    return 'kh/index.html'+query;
  }

  function findLanguageControl(){
    var links=document.querySelectorAll('.topbar a.theme-btn');
    var i,text;
    for(i=0;i<links.length;i++){
      text=(links[i].textContent||'').replace(/^\s+|\s+$/g,'').toLowerCase();
      if(text==='khasi'||text==='english')return links[i];
    }
    return null;
  }

  function bindNavigation(){
    var nav=document.getElementById('main-nav');
    var oldMenu=document.querySelector('.menu-btn');
    var oldTheme=document.querySelector('button.theme-btn');
    var path=window.location.pathname||'';
    var isKh=path.indexOf('/kh/')!==-1;
    var parts=path.split('/');
    var name=parts[parts.length-1]||'index.html';
    var query=window.location.search||'';
    var menu,themeBtn,lang;

    /* Replace the menu button so stale/duplicate event handlers cannot interfere. */
    if(oldMenu&&nav&&oldMenu.parentNode){
      menu=oldMenu.cloneNode(true);
      oldMenu.parentNode.replaceChild(menu,oldMenu);
      menu.onclick=function(e){
        var open;
        if(e&&e.preventDefault)e.preventDefault();
        if(nav.className.indexOf('open')===-1){
          nav.className=(nav.className?nav.className+' ':'')+'open';
          open=true;
        }else{
          nav.className=nav.className.replace(/(?:^|\s)open(?:\s|$)/g,' ').replace(/^\s+|\s+$/g,'');
          open=false;
        }
        menu.setAttribute('aria-expanded',open?'true':'false');
        return false;
      };
    }

    /* Repair an existing language control or create it if the modern script failed. */
    lang=findLanguageControl();
    if(!lang&&oldTheme&&oldTheme.parentNode){
      lang=document.createElement('a');
      lang.className='theme-btn';
      lang.style.textDecoration='none';
      oldTheme.parentNode.insertBefore(lang,oldTheme);
    }
    if(lang){
      lang.textContent=isKh?'English':'Khasi';
      lang.setAttribute('aria-label',isKh?'Switch to English':'Switch to Khasi');
      lang.title=isKh?'Open the same page in English':'Open the same page in Khasi';
      lang.href=languageHref(isKh,path,name,query);
      lang.onclick=function(e){
        if(e&&e.preventDefault)e.preventDefault();
        window.location.href=lang.href;
        return false;
      };
    }

    /* Replace and bind the theme button as well so the header remains fully usable. */
    if(oldTheme&&oldTheme.parentNode){
      themeBtn=oldTheme.cloneNode(true);
      oldTheme.parentNode.replaceChild(themeBtn,oldTheme);
      themeBtn.onclick=function(e){
        var body=document.body;
        var dark=body.className.indexOf('dark')!==-1;
        if(e&&e.preventDefault)e.preventDefault();
        if(dark){
          body.className=body.className.replace(/(?:^|\s)dark(?:\s|$)/g,' ').replace(/^\s+|\s+$/g,'');
        }else{
          body.className=(body.className?body.className+' ':'')+'dark';
        }
        try{window.localStorage.setItem('mercy-theme',dark?'light':'dark');}catch(err){}
        return false;
      };
    }
  }

  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded',function(){window.setTimeout(bindNavigation,0);});
  }else{
    window.setTimeout(bindNavigation,0);
  }
})();
