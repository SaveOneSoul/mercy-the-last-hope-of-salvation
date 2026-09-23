(function(){
'use strict';
// Curated, original vector illustrations. No third-party images or user-supplied URLs.
var themes=[['eucharist','Eucharist'],['bible','Bible'],['flowers','Flowers'],['cross','Cross'],['jesus','Jesus · Sacred Heart'],['mercy','Divine Mercy'],['spirit','Holy Spirit'],['saints','Saints']];
function ellipse(ctx,x,y,rx,ry,color){ctx.beginPath();ctx.ellipse(x,y,rx,ry,0,0,Math.PI*2);ctx.fillStyle=color;ctx.fill();}
function line(ctx,x,y,toX,toY,color,width){ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(toX,toY);ctx.strokeStyle=color;ctx.lineWidth=width;ctx.lineCap='round';ctx.stroke();}
function halo(ctx,x,y,r){ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.strokeStyle='#e0b961';ctx.lineWidth=12;ctx.stroke();}
function heart(ctx,x,y,scale){ctx.save();ctx.translate(x,y);ctx.scale(scale,scale);ctx.beginPath();ctx.moveTo(0,33);ctx.bezierCurveTo(-115,-32,-45,-87,0,-28);ctx.bezierCurveTo(45,-87,115,-32,0,33);ctx.fillStyle='#941c3b';ctx.fill();ctx.restore();}
function cross(ctx,x,y,scale){ctx.fillStyle='#6d283c';ctx.fillRect(x-13*scale,y-100*scale,26*scale,200*scale);ctx.fillRect(x-70*scale,y-45*scale,140*scale,26*scale);}
function dove(ctx,x,y){ctx.save();ctx.translate(x,y);ctx.beginPath();ctx.moveTo(0,64);ctx.bezierCurveTo(-24,30,-85,24,-130,-28);ctx.bezierCurveTo(-83,-22,-51,-8,-26,-22);ctx.bezierCurveTo(-85,-95,-35,-101,0,-45);ctx.bezierCurveTo(35,-101,85,-95,26,-22);ctx.bezierCurveTo(51,-8,83,-22,130,-28);ctx.bezierCurveTo(85,24,24,30,0,64);ctx.fillStyle='#fffdf4';ctx.fill();ctx.strokeStyle='#b19056';ctx.lineWidth=4;ctx.stroke();ellipse(ctx,11,-22,4,4,'#613b3b');ctx.restore();}
function christ(ctx,x,y){halo(ctx,x,y-85,78);ellipse(ctx,x,y-83,52,67,'#44283b');ellipse(ctx,x,y-81,39,51,'#edc8a7');ellipse(ctx,x,y-43,24,19,'#6b3940');ellipse(ctx,x,y+115,120,150,'#f8eee0');ctx.fillStyle='#e1b39f';ctx.fillRect(x-8,y+17,16,182);line(ctx,x-100,y+130,x-166,y+55,'#f8eee0',34);line(ctx,x+100,y+130,x+166,y+55,'#f8eee0',34);heart(ctx,x,y+77,.62);}
function draw(ctx,theme){var gradient=ctx.createLinearGradient(0,0,1080,450);gradient.addColorStop(0,'#4d1834');gradient.addColorStop(1,'#99566a');ctx.fillStyle=gradient;ctx.fillRect(0,0,1080,450);ctx.save();ctx.shadowColor='#e6b968';ctx.shadowBlur=32;
if(theme==='eucharist'){ellipse(ctx,540,151,74,74,'#fff9e7');halo(ctx,540,151,82);cross(ctx,540,151,.36);ctx.fillStyle='#efcf80';ctx.beginPath();ctx.moveTo(455,255);ctx.lineTo(625,255);ctx.lineTo(595,351);ctx.lineTo(485,351);ctx.closePath();ctx.fill();line(ctx,540,350,540,389,'#efcf80',18);line(ctx,478,394,602,394,'#efcf80',15);}
else if(theme==='bible'){ctx.fillStyle='#d8b16a';ctx.fillRect(332,84,415,280);ctx.fillStyle='#fff7e7';ctx.fillRect(345,94,385,253);ctx.fillStyle='#862f48';ctx.fillRect(345,94,30,253);cross(ctx,545,220,.7);}
else if(theme==='flowers'){for(var i=0;i<5;i++){var x=305+i*118,y=165+(i%2)*75;line(ctx,x,y+35,x+25,390,'#b2d8a6',7);for(var j=0;j<6;j++){var a=j*Math.PI/3;ellipse(ctx,x+Math.cos(a)*27,y+Math.sin(a)*27,23,23,['#f7d4d9','#fff0be','#e5d2f2'][i%3]);}ellipse(ctx,x,y,17,17,'#d7a344');}}
else if(theme==='cross'){halo(ctx,540,210,150);cross(ctx,540,235,1.35);}
else if(theme==='jesus'){christ(ctx,540,204);}
else if(theme==='mercy'){for(var k=0;k<11;k++){line(ctx,532+k*3,286,210+k*18,447,'#f1d7df',5);line(ctx,548+k*3,286,640+k*20,447,'#b6d6f5',5);}christ(ctx,540,190);}
else if(theme==='spirit'){for(var s=0;s<12;s++){var angle=s*Math.PI/6;line(ctx,540+Math.cos(angle)*145,193+Math.sin(angle)*145,540+Math.cos(angle)*190,193+Math.sin(angle)*190,'#eac77e',8);}dove(ctx,540,207);}
else if(theme==='saints'){for(var n=0;n<3;n++){var xx=390+n*150;halo(ctx,xx,142,48);ellipse(ctx,xx,150,32,42,'#f6ddc3');ellipse(ctx,xx,320,70,122,['#b597ac','#cab0a6','#9ba9bf'][n]);}cross(ctx,540,283,.32);}
ctx.restore();}
window.MercyLogosArt={themes:themes,draw:draw};
})();
