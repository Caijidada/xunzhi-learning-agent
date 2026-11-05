<script setup lang="ts">
import { ref, onUnmounted } from 'vue'
import { Play, Pause, ChevronRight, RotateCcw, ArrowDown } from '@lucide/vue'
import type { Step } from '../types'
const props=defineProps<{steps:Step[]}>()
const current=ref(0),playing=ref(false)
let timer:ReturnType<typeof setInterval>|undefined
function stop(){ clearInterval(timer);playing.value=false }
function toggle(){
  if(playing.value){stop();return}
  if(current.value>=props.steps.length-1)current.value=0
  playing.value=true
  timer=setInterval(()=>{if(current.value<props.steps.length-1)current.value++;else stop()},2600)
}
function select(i:number){stop();current.value=i}
onUnmounted(stop)
</script>
<template>
  <div class="step-demo">
    <div class="diagram-label"><span class="pulse-dot"></span> 跟着信息走一遍 <span>交互演示</span></div>
    <div class="flow-steps">
      <template v-for="(step,i) in steps" :key="i">
        <button class="flow-node" :class="{active:i===current,passed:i<current}" @click="select(i)" :aria-label="`第 ${i+1} 步：${step.label}`"><span class="step-number">{{String(i+1).padStart(2,'0')}}</span>{{step.label}}<ChevronRight :size="15"/></button>
        <div v-if="i<steps.length-1" class="flow-connector" :class="{passed:i<current}"><ArrowDown :size="14"/></div>
      </template>
    </div>
    <div class="step-explanation" aria-live="polite"><span>此刻发生了什么</span><p>{{steps[current]?.detail}}</p></div>
    <div class="playback"><button class="icon-btn" @click="toggle" :aria-label="playing?'暂停演示':'播放演示'"><Pause v-if="playing" :size="17"/><Play v-else :size="17"/></button><button class="text-btn" @click="select(Math.min(current+1,steps.length-1))" :disabled="current===steps.length-1">下一步 <ChevronRight :size="15"/></button><span>{{current+1}} / {{steps.length}}</span><button class="icon-btn" @click="select(0)" aria-label="重新播放"><RotateCcw :size="15"/></button></div>
  </div>
</template>
