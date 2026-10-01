(function(){
  'use strict';
  var canvas=document.querySelector('[data-avatar-canvas]');
  var fallback=document.querySelector('[data-avatar-face]');
  if(!canvas){return;}
  var gl=canvas.getContext('webgl',{alpha:true,antialias:true,premultipliedAlpha:true});
  if(!gl){canvas.hidden=true;if(fallback)fallback.hidden=false;window.MercyAvatar3D={setState:function(){},setViseme:function(){}};return;}
  if(fallback)fallback.hidden=true;

  var vs='attribute vec3 p;attribute vec3 n;uniform mat4 mvp;uniform mat4 model;varying vec3 N;varying vec3 P;void main(){vec4 w=model*vec4(p,1.0);P=w.xyz;N=normalize((model*vec4(n,0.0)).xyz);gl_Position=mvp*vec4(p,1.0);}';
  var fs='precision mediump float;uniform vec3 color;uniform vec3 light;varying vec3 N;varying vec3 P;void main(){float d=max(dot(normalize(N),normalize(light-P)),0.0);float rim=pow(1.0-max(dot(normalize(N),normalize(-P)),0.0),2.0);gl_FragColor=vec4(color*(.34+.66*d)+rim*.08,1.0);}';
  function shader(t,s){var x=gl.createShader(t);gl.shaderSource(x,s);gl.compileShader(x);return x;}
  var pr=gl.createProgram();gl.attachShader(pr,shader(gl.VERTEX_SHADER,vs));gl.attachShader(pr,shader(gl.FRAGMENT_SHADER,fs));gl.linkProgram(pr);gl.useProgram(pr);
  var loc={p:gl.getAttribLocation(pr,'p'),n:gl.getAttribLocation(pr,'n'),mvp:gl.getUniformLocation(pr,'mvp'),model:gl.getUniformLocation(pr,'model'),color:gl.getUniformLocation(pr,'color'),light:gl.getUniformLocation(pr,'light')};
  function sphere(lat,lon){
    var a=[],idx=[];for(var y=0;y<=lat;y++){var v=y/lat*Math.PI;for(var x=0;x<=lon;x++){var u=x/lon*Math.PI*2,sv=Math.sin(v);a.push(Math.cos(u)*sv,Math.cos(v),Math.sin(u)*sv);}}
    for(y=0;y<lat;y++)for(x=0;x<lon;x++){var i=y*(lon+1)+x;idx.push(i,i+lon+1,i+1,i+1,i+lon+1,i+lon+2);}
    return mesh(a,idx);
  }
  function mesh(a,idx){var b=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,b);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(a),gl.STATIC_DRAW);var ib=gl.createBuffer();gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,ib);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,new Uint16Array(idx),gl.STATIC_DRAW);return{b:b,ib:ib,count:idx.length};}
  var ball=sphere(20,28);
  function I(){return[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1];}
  function mul(a,b){var o=new Array(16);for(var c=0;c<4;c++)for(var r=0;r<4;r++){o[c*4+r]=0;for(var k=0;k<4;k++)o[c*4+r]+=a[k*4+r]*b[c*4+k];}return o;}
  function T(x,y,z){var m=I();m[12]=x;m[13]=y;m[14]=z;return m;}function S(x,y,z){var m=I();m[0]=x;m[5]=y;m[10]=z;return m;}
  function RY(a){var m=I(),c=Math.cos(a),s=Math.sin(a);m[0]=c;m[2]=-s;m[8]=s;m[10]=c;return m;}
  function perspective(f,a,n,f2){var t=1/Math.tan(f/2),m=new Array(16).fill(0);m[0]=t/a;m[5]=t;m[10]=(f2+n)/(n-f2);m[11]=-1;m[14]=2*f2*n/(n-f2);return m;}
  var state='idle',viseme=0,targetViseme=0,started=performance.now(),blink=0;
  var reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
  function drawPart(x,y,z,sx,sy,sz,color,rot){
    var model=mul(T(x,y,z),mul(RY(rot||0),S(sx,sy,sz)));
    var view=T(0,0,-6.2),proj=perspective(.72,canvas.width/canvas.height,.1,50);
    gl.uniformMatrix4fv(loc.model,false,new Float32Array(model));gl.uniformMatrix4fv(loc.mvp,false,new Float32Array(mul(proj,mul(view,model))));
    gl.uniform3fv(loc.color,new Float32Array(color));gl.bindBuffer(gl.ARRAY_BUFFER,ball.b);gl.enableVertexAttribArray(loc.p);gl.vertexAttribPointer(loc.p,3,gl.FLOAT,false,0,0);gl.enableVertexAttribArray(loc.n);gl.vertexAttribPointer(loc.n,3,gl.FLOAT,false,0,0);gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,ball.ib);gl.drawElements(gl.TRIANGLES,ball.count,gl.UNSIGNED_SHORT,0);
  }
  function resize(){var d=Math.min(devicePixelRatio||1,2),w=Math.max(1,canvas.clientWidth),h=Math.max(1,canvas.clientHeight);if(canvas.width!==w*d||canvas.height!==h*d){canvas.width=w*d;canvas.height=h*d;gl.viewport(0,0,canvas.width,canvas.height);}}
  function frame(now){
    resize();gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.enable(gl.DEPTH_TEST);gl.enable(gl.CULL_FACE);
    gl.uniform3fv(loc.light,new Float32Array([2.5,4.5,4.5]));
    var t=(now-started)/1000,bob=reduced?0:Math.sin(t*1.1)*.025,turn=reduced?0:Math.sin(t*.35)*.045;
    if(state==='thinking')turn+=Math.sin(t*1.6)*.06;if(state==='listening')turn*=.3;
    viseme+=(targetViseme-viseme)*.22;
    blink=reduced?0:(Math.sin(t*.83)>0.996?1:Math.max(0,blink-.16));
    // Stylised fictional lay Catholic guide: feminine proportions without
    // imitating Mary, a saint, a religious sister, or a real person.
    var skin=[.82,.64,.54],skinSoft=[.88,.70,.61],hair=[.11,.065,.055],dress=[.28,.075,.13],white=[.98,.97,.94],eye=[.10,.065,.055],iris=[.24,.16,.12],lip=[.52,.17,.23],gold=[.78,.60,.30];
    // Upper torso and shoulders: fitted modest lay clothing, not a habit/veil.
    drawPart(0,-1.72+bob,.00,1.20,1.08,.58,dress,turn);
    drawPart(-.88,-1.32+bob,.02,.52,.45,.48,dress,turn);drawPart(.88,-1.32+bob,.02,.52,.45,.48,dress,turn);
    // Neck and softly tapered face.
    drawPart(0,-.73+bob,.04,.32,.42,.32,skinSoft,turn);
    drawPart(0,.12+bob,0,.82,1.06,.78,skin,turn);
    drawPart(0,-.43+bob,.06,.69,.49,.69,skinSoft,turn);
    // Long side/back hair framing the face; no head covering.
    drawPart(0,.68+bob,-.25,.88,.58,.72,hair,turn);
    drawPart(-.73,.02+bob,-.12,.25,.91,.50,hair,turn);drawPart(.73,.02+bob,-.12,.25,.91,.50,hair,turn);
    drawPart(0,.91+bob,.02,.68,.26,.65,hair,turn);
    // Eyes, irises and subtle brows.
    drawPart(-.30,.27+bob,.70,.18,.075*(1-blink),.050,white,turn);drawPart(.30,.27+bob,.70,.18,.075*(1-blink),.050,white,turn);
    drawPart(-.30,.27+bob,.755,.066,.066,.035,iris,turn);drawPart(.30,.27+bob,.755,.066,.066,.035,iris,turn);
    drawPart(-.30,.40+bob,.69,.22,.027,.035,eye,turn-.04);drawPart(.30,.40+bob,.69,.22,.027,.035,eye,turn+.04);
    // Small nose, cheek warmth and animated lips.
    drawPart(0,.00+bob,.76,.075,.16,.055,skinSoft,turn);
    drawPart(-.39,-.02+bob,.69,.16,.09,.025,[.88,.54,.53],turn);drawPart(.39,-.02+bob,.69,.16,.09,.025,[.88,.54,.53],turn);
    drawPart(0,-.31+bob,.77,.22,.035+viseme*.105,.038,lip,turn);
    // Small cross pendant: Catholic identity without religious-habit styling.
    drawPart(0,-.94+bob,.61,.025,.17,.020,gold,turn);drawPart(0,-.94+bob,.61,.115,.025,.020,gold,turn);
    requestAnimationFrame(frame);
  }
  window.MercyAvatar3D={
    setState:function(s){state=s||'idle';if(state!=='speaking')targetViseme=0;},
    setViseme:function(v){targetViseme=Math.max(0,Math.min(1,Number(v)||0));},
    pulseSpeech:function(){targetViseme=.35+Math.random()*.65;setTimeout(function(){targetViseme=.12;},90);}
  };
  requestAnimationFrame(frame);
})();