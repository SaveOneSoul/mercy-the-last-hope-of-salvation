import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {VRMLoaderPlugin,VRMUtils} from '@pixiv/three-vrm';

const viewport=document.querySelector('[data-avatar-viewport]');
const canvas=document.querySelector('[data-avatar-canvas]');
const placeholder=document.querySelector('[data-avatar-placeholder]');
const label=document.querySelector('[data-avatar-visual-status]');
const detail=document.querySelector('[data-avatar-load-detail]');
let vrm=null,renderer=null,clock=null,frame=0,visemeTimer=0,state='idle';

function status(title,message){if(label)label.textContent=title;if(detail)detail.textContent=message||'';}
function expression(name,value){
  const manager=vrm&&vrm.expressionManager;
  if(!manager)return;
  try{manager.setValue(name,Math.max(0,Math.min(1,Number(value)||0)));}catch(_){}
}
function setViseme(value){expression('aa',value);}
function setState(next){
  state=next||'idle';
  if(viewport)viewport.dataset.state=state;
  if(!vrm){status('3D avatar not installed','The renderer is ready for a reviewed, redistribution-approved VRM/GLB character asset.');return;}
  status(state==='idle'?'Ready':state.charAt(0).toUpperCase()+state.slice(1),'Mercy 3D avatar');
  expression('happy',state==='listening'?.12:0);
  if(state!=='speaking')setViseme(0);
}
function pulseSpeech(){clearTimeout(visemeTimer);setViseme(.25+Math.random()*.55);visemeTimer=setTimeout(()=>setViseme(.05),105);}
window.MercyAvatar3D={setState,setViseme,pulseSpeech};

function startRender(){
  if(renderer)return;
  renderer=new THREE.WebGLRenderer({canvas,alpha:true,antialias:true,powerPreference:'high-performance'});
  renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,2));
  renderer.outputColorSpace=THREE.SRGBColorSpace;
  const scene=new THREE.Scene();
  const camera=new THREE.PerspectiveCamera(28,1,.1,20);camera.position.set(0,1.42,2.25);
  scene.add(new THREE.HemisphereLight(0xfff6e8,0x6b5260,2.4));
  const key=new THREE.DirectionalLight(0xffffff,2.2);key.position.set(1.8,2.6,2.5);scene.add(key);
  const loader=new GLTFLoader();loader.register(parser=>new VRMLoaderPlugin(parser));
  const modelUrl=viewport&&viewport.dataset.modelUrl;
  if(!modelUrl){setState('idle');return;}
  status('Loading 3D avatar…','Loading the reviewed local character asset.');
  loader.load(modelUrl,gltf=>{
    vrm=gltf.userData.vrm;
    if(!vrm)throw new Error('VRM metadata missing');
    VRMUtils.removeUnnecessaryVertices(gltf.scene);VRMUtils.combineSkeletons(gltf.scene);
    vrm.scene.rotation.y=Math.PI;scene.add(vrm.scene);
    if(placeholder)placeholder.hidden=true;canvas.hidden=false;clock=new THREE.Clock();setState('idle');
    const resize=()=>{const r=viewport.getBoundingClientRect();renderer.setSize(r.width,r.height,false);camera.aspect=r.width/r.height;camera.updateProjectionMatrix();};resize();addEventListener('resize',resize,{passive:true});
    const tick=()=>{frame=requestAnimationFrame(tick);const dt=Math.min(clock.getDelta(),.05);vrm.update(dt);renderer.render(scene,camera);};tick();
  },undefined,err=>{canvas.hidden=true;if(placeholder)placeholder.hidden=false;status('3D avatar unavailable','The reviewed avatar asset could not be loaded.');console.warn('Mercy avatar model load failed:',err&&err.name?err.name:'load_error');});
}
if(canvas)canvas.hidden=true;
try{startRender();}catch(err){status('3D renderer unavailable','This browser could not initialize the 3D renderer.');console.warn('Mercy avatar renderer failed:',err&&err.name?err.name:'renderer_error');}
setState('idle');
