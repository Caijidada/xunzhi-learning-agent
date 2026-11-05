<script setup lang="ts">
import { computed, ref, watch, onUnmounted } from 'vue'
import { Play, Pause, RotateCcw, Maximize2, X } from '@lucide/vue'
import type { Scene } from '../types'
const props=defineProps<{scene:Scene}>()
const scenarioIndex=ref(0),frameIndex=ref(0),playing=ref(false),expanded=ref(false)
const scenario=computed(()=>props.scene.scenarios[scenarioIndex.value]!)
const frame=computed(()=>scenario.value.frames[frameIndex.value]!)
const nodes=computed(()=>props.scene.nodes.map(n=>{
  const s=frame.value.states.find(s=>s.node_id===n.id)
  return {...n,x:s?.x??n.x,y:s?.y??n.y,text:s?.text??''}
}))
const edges=computed(()=>props.scene.edges.map(e=>{
  const a=nodes.value.find(n=>n.id===e.source)!,b=nodes.value.find(n=>n.id===e.target)!
  const horizontal=Math.abs(a.x-b.x)>Math.abs(a.y-b.y)
  const ax=horizontal?(a.x<b.x?a.x+160:a.x):a.x+80
  const ay=horizontal?a.y+40:(a.y<b.y?a.y+80:a.y)
  const bx=horizontal?(a.x<b.x?b.x:b.x+160):b.x+80
  const by=horizontal?b.y+40:(a.y<b.y?b.y:b.y+80)
  return {...e,ax,ay,bx,by,path:`M ${ax} ${ay} L ${bx} ${by}`}
}))
let timer:ReturnType<typeof setInterval>|undefined
function stop(){clearInterval(timer);playing.value=false}
function seek(i:number){stop();frameIndex.value=i}
function toggle(){
  if(playing.value){stop();return}
  if(frameIndex.value===scenario.value.frames.length-1)frameIndex.value=0
  playing.value=true
  timer=setInterval(()=>{if(frameIndex.value<scenario.value.frames.length-1)frameIndex.value++;else stop()},3600)
}
function changeScenario(i:number){stop();scenarioIndex.value=i;frameIndex.value=0}
watch(()=>props.scene,()=>{stop();scenarioIndex.value=0;frameIndex.value=0})
function escape(e:KeyboardEvent){if(e.key==='Escape')expanded.value=false}
watch(expanded,v=>{if(v)window.addEventListener('keydown',escape);else window.removeEventListener('keydown',escape)})
onUnmounted(()=>{stop();window.removeEventListener('keydown',escape)})
</script>
<template>
  <section class="scene-player" :class="{expanded,playing}" aria-label="知识演示区">
    <header><div><span class="scene-eyebrow">探索与演示</span><p>{{scene.goal}}</p></div><button class="icon-btn" :aria-label="expanded?'收起演示':'放大演示'" @click="expanded=!expanded"><X v-if="expanded" :size="18"/><Maximize2 v-else :size="18"/></button></header>
    <div v-if="scene.scenarios.length>1" class="scenario-tabs" aria-label="比较不同情境"><button v-for="(s,i) in scene.scenarios" :key="i" :aria-pressed="i===scenarioIndex" @click="changeScenario(i)">{{s.label}}</button></div>
    <div class="scene-canvas">
      <svg viewBox="0 0 900 500" role="img" :aria-label="`${scenario.label}：${frame.caption}`">
        <g v-for="(group,i) in scene.groups" :key="`group-${i}`"><rect :x="group.x" :y="group.y" :width="group.width" :height="group.height" rx="24" class="scene-group"/><text :x="group.x+15" :y="group.y+25" class="group-label">{{group.label}}</text></g>
        <g v-for="edge in edges" :key="edge.id" :class="{active:frame.active_edges.includes(edge.id)}" class="scene-edge">
          <path :d="edge.path"/><path d="M -9 -5 L 0 0 L -9 5" :transform="`translate(${edge.bx} ${edge.by}) rotate(${Math.atan2(edge.by-edge.ay,edge.bx-edge.ax)*180/Math.PI})`"/>
          <text :x="(edge.ax+edge.bx)/2" :y="(edge.ay+edge.by)/2-10" text-anchor="middle">{{edge.label}}</text>
          <circle v-if="frame.active_edges.includes(edge.id)" :key="`${scenarioIndex}-${frameIndex}-${edge.id}`" r="5" class="signal" :style="{offsetPath:`path('${edge.path}')`}"/>
        </g>
        <g v-for="node in nodes" :key="node.id" :style="{transform:`translate(${node.x}px,${node.y}px)`}" class="scene-node" :class="{active:frame.active_nodes.includes(node.id)}">
          <rect width="160" height="80" rx="18"/>
          <foreignObject x="10" y="8" width="140" height="66"><div class="node-copy"><strong>{{node.label}}</strong><span>{{node.text}}</span></div></foreignObject>
        </g>
      </svg>
    </div>
    <div class="scene-caption" aria-live="polite"><span>{{frameIndex+1}} / {{scenario.frames.length}}</span><p>{{frame.caption}}</p></div>
    <footer><button class="button small" @click="toggle"><Pause v-if="playing" :size="16"/><Play v-else :size="16"/>{{playing?'暂停':'播放变化'}}</button><button class="icon-btn" aria-label="重置演示" @click="seek(0)"><RotateCcw :size="17"/></button><input type="range" min="0" :max="scenario.frames.length-1" :value="frameIndex" aria-label="演示时间线" @input="seek(Number(($event.target as HTMLInputElement).value))"/><button class="text-btn" :disabled="frameIndex===scenario.frames.length-1" @click="seek(frameIndex+1)">下一幕</button></footer>
    <small class="scene-note">教学情境示意 · 可拖动时间线逐幕观察，并继续提问</small>
  </section>
</template>
<style scoped>
.scene-player{background:#f7f9f5;border:1px solid #cdd8c7;border-radius:20px;overflow:hidden;margin:16px 0;color:#263c32}.scene-player.expanded{position:fixed;inset:20px;z-index:1000;margin:0;overflow:auto;box-shadow:0 0 0 60px #15241ecc}.scene-player.expanded{display:flex;flex-direction:column}.expanded .scene-canvas{flex:1;min-height:140px}.expanded .scene-canvas svg{height:100%;max-height:none;min-width:0}.expanded .scene-caption{min-height:0}.scene-player header{display:flex;justify-content:space-between;align-items:start;padding:20px 22px}.scene-player header p{margin:6px 0 0;font-size:15px;line-height:1.7}.scene-eyebrow{font-size:11px;letter-spacing:2px;color:#586e58}.scenario-tabs{display:flex;flex-wrap:wrap;gap:8px;padding:0 22px 16px}.scenario-tabs button{padding:8px 14px;border:1px solid #ccd6c8;border-radius:24px;background:white;font-size:13px;color:#425642}.scenario-tabs button[aria-pressed=true]{background:#355c49;color:white}.scene-canvas{background:radial-gradient(#cdd7c8 1px,transparent 1px);background-size:18px 18px;overflow:auto}.scene-canvas svg{display:block;width:100%;min-width:450px;max-height:65vh}.scene-group{fill:#e8eee650;stroke:#83997e;stroke-width:1.5;stroke-dasharray:7 5}.group-label{font-size:16px;fill:#496247}.scene-node{transition:transform 850ms cubic-bezier(.22,.75,.25,1)}.scene-node rect{fill:#fff;stroke:#afbdaa;stroke-width:1.5;transition:fill .6s,stroke .6s,stroke-width .6s}.scene-node.active rect{fill:#e0efdf;stroke:#48764f;stroke-width:3}.node-copy{height:100%;display:flex;flex-direction:column;justify-content:center;text-align:center;gap:5px;overflow:hidden}.node-copy strong{white-space:pre-line;font-size:15px;line-height:1.2}.node-copy span{font-size:12px;line-height:1.3;color:#55704e;overflow-wrap:anywhere}.scene-edge path{fill:none;stroke:#b3c0ad;stroke-width:2;stroke-dasharray:5 5}.scene-edge.active path{stroke:#4c8052;stroke-width:3;stroke-dasharray:none}.scene-edge text{font-size:12px;fill:#5c6e54;paint-order:stroke;stroke:#f7f9f5;stroke-width:5px}.signal{fill:#2c7b51;offset-distance:0%;animation:travel 1.7s ease-in-out infinite;animation-play-state:paused}.playing .signal{animation-play-state:running}.scene-caption{padding:18px 22px;display:flex;gap:16px;min-height:90px;border-top:1px solid #dce4d7}.scene-caption span{white-space:nowrap;color:#6d805f;font-size:12px;padding-top:4px}.scene-caption p{margin:0;font-size:14px;line-height:1.8}.scene-player footer{display:flex;gap:12px;align-items:center;padding:0 22px 15px}.scene-player input{flex:1;min-width:30px;accent-color:#42664b}.scene-note{display:block;font-size:11px;color:#687762;padding:0 22px 16px}@keyframes travel{to{offset-distance:100%}}@media(prefers-reduced-motion:reduce){.scene-node,.scene-node rect{transition:none}.signal{animation:none;offset-distance:50%}}
</style>
