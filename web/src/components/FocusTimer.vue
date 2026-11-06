<script setup lang="ts">
import { computed, ref, onUnmounted, watch } from 'vue'
const props=defineProps<{courseId:string;minutes:number}>()
const key=`xunzhi.focus.${props.courseId}`
let saved:{remaining:number;total:number;state:string;deadline:number}|null=null
try{saved=JSON.parse(localStorage.getItem(key)||'null')}catch{}
const total=ref(saved?.total||props.minutes*60),remaining=ref(saved?.remaining??total.value)
const state=ref(saved?.state||'idle'),deadline=ref(saved?.deadline||0),now=ref(Date.now())
const seconds=computed(()=>state.value==='running'?Math.max(0,Math.ceil((deadline.value-now.value)/1000)):remaining.value)
const display=computed(()=>`${String(Math.floor(seconds.value/60)).padStart(2,'0')}:${String(seconds.value%60).padStart(2,'0')}`)
const progress=computed(()=>Math.min(100,Math.max(0,(1-seconds.value/total.value)*100)))
function save(){localStorage.setItem(key,JSON.stringify({remaining:remaining.value,total:total.value,state:state.value,deadline:deadline.value}))}
function start(){if(state.value==='done'||state.value==='ended'){total.value=props.minutes*60;remaining.value=total.value}now.value=Date.now();deadline.value=now.value+remaining.value*1000;state.value='running';save()}
function pause(){remaining.value=seconds.value;state.value='paused';save()}
function end(){remaining.value=seconds.value;state.value='ended';save()}
const timer=setInterval(()=>{now.value=Date.now();if(state.value==='running'&&seconds.value===0){remaining.value=0;state.value='done';save()}},250)
watch(()=>props.minutes,v=>{if(state.value==='idle'||state.value==='ended'||state.value==='done'){total.value=v*60;remaining.value=total.value;state.value='idle';save()}})
onUnmounted(()=>clearInterval(timer))
</script>
<template>
  <section class="focus-timer" aria-label="专注倒计时"><div><strong>{{display}}</strong><span>{{state==='done'?'目标达成 ✨':state==='paused'?'已暂停':state==='running'?'专注进行中':state==='ended'?'本次已结束':'准备好就开始'}}</span></div><progress :value="progress" max="100" aria-label="本次专注进度"></progress><div class="timer-actions"><button v-if="state!=='running'" class="button small" @click="start">{{state==='paused'?'继续':state==='done'||state==='ended'?'再来一轮':'开始'}}</button><button v-else class="button small" @click="pause">暂停</button><button :disabled="!['running','paused'].includes(state)" class="text-btn" @click="end">结束</button></div><p v-if="state==='done'" role="status">完成了自己设定的 {{Math.round(total/60)}} 分钟，给这次坚持点个赞！</p><p v-else-if="state==='ended'">本次计时 {{Math.floor((total-seconds)/60)}} 分钟。随时可以再开始。</p></section>
</template>
<style scoped>
.focus-timer{padding:14px 0;border-top:1px solid #dde5d7;margin-top:12px}.focus-timer>div{display:flex;justify-content:space-between;align-items:center;gap:12px}.focus-timer strong{font-size:28px;font-variant-numeric:tabular-nums}.focus-timer span,.focus-timer p{font-size:12px;color:#536c4d}.focus-timer progress{width:100%;height:9px;accent-color:#4a7751;margin:12px 0}.focus-timer .timer-actions{justify-content:flex-start}.focus-timer p{margin:12px 0 0;line-height:1.7}
</style>
