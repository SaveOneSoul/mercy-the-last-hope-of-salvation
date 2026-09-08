(function(){
  var root=document.querySelector('[data-contact-assistant]');
  if(!root)return;

  var buttons=root.querySelectorAll('[data-contact-choice]');
  var panels=root.querySelectorAll('[data-contact-panel]');
  var reset=root.querySelector('[data-contact-reset]');

  function hidePanels(){
    var i;
    for(i=0;i<panels.length;i++)panels[i].hidden=true;
    for(i=0;i<buttons.length;i++)buttons[i].setAttribute('aria-pressed','false');
  }

  function showPanel(name,button){
    var i,panel=null;
    hidePanels();
    for(i=0;i<panels.length;i++){
      if(panels[i].getAttribute('data-contact-panel')===name){
        panel=panels[i];
        panel.hidden=false;
        break;
      }
    }
    if(button)button.setAttribute('aria-pressed','true');
    if(reset)reset.hidden=false;
    if(panel){
      panel.setAttribute('tabindex','-1');
      try{panel.focus();}catch(e){}
    }
  }

  var i;
  for(i=0;i<buttons.length;i++){
    (function(button){
      button.addEventListener('click',function(){
        showPanel(button.getAttribute('data-contact-choice'),button);
      });
    })(buttons[i]);
  }

  if(reset){
    reset.addEventListener('click',function(){
      hidePanels();
      reset.hidden=true;
      if(buttons.length){
        try{buttons[0].focus();}catch(e){}
      }
    });
  }

  hidePanels();
  if(reset)reset.hidden=true;
})();