<script setup lang="ts">
import {computed,onMounted,onUnmounted,ref,watch} from 'vue'
import {ArrowRight,BookOpen} from '@lucide/vue'
import {recallCards, type RecallCard} from '../waitReview'
import type {Course,Unit} from '../types'

const props=defineProps<{course:Course;unit:Unit;state:{status:string;message:string}}>()
defineEmits<{enter:[question:string];cancel:[]}>()
const cards=ref<RecallCard[]>([]), loaded=ref(false), index=ref(0), revealed=ref(false)
const choice=ref<number|null>(null), response=ref(''), progress=ref(12)
const card=computed(()=>cards.value[index.value])
const ready=computed(()=>props.state.status==='completed')
const batch=computed(()=>props.state.message?.match(/第 (\d+)\/(\d+) 部分/))
const statusText=computed(()=>ready.value?'讲义已准备好':batch.value?`正在整理第 ${batch.value[1]} / ${batch.value[2]} 部分`:props.state.message||'正在准备讲义')
let interval:ReturnType<typeof setInterval>
function advance(){
  if (ready.value) {progress.value=100;return}
  const n=Number(batch.value?.[1]), total=Number(batch.value?.[2])
  const base=total?12+82*(n-1)/total:12
  const cap=total?12+82*n/total:props.state.message?.includes('已保存')?97:36
  progress.value=Math.max(progress.value,base)
  progress.value+=Math.max(0,cap-progress.value)*.04
}
watch(()=>props.state,advance,{immediate:true})
onMounted(async()=>{
  interval=setInterval(advance,700)
  try {cards.value=await recallCards(props.course,props.unit.id)}
  catch {loadFailed.value=true}
  finally {loaded.value=true}
})
onUnmounted(()=>clearInterval(interval))
const loadFailed=ref(false)
function move(delta:number){
  index.value+=delta
  revealed.value=false
  choice.value=null
}
</script>
<template>
  <section class="wait-review" aria-label="等待时复习">
    <header><span role="status">{{statusText}}</span><button v-if="!ready" class="text-btn" @click="$emit('cancel')">停止生成</button></header>
    <div class="wait-track" role="progressbar" :aria-label="statusText" :aria-valuemin="0" :aria-valuemax="100" :aria-valuenow="ready?100:undefined"><i :style="{width:progress+'%'}"></i></div>
    <template v-if="card">
      <small>{{card.chapter}} · 复习 {{index+1}} / {{cards.length}}</small>
      <h2>{{card.prompt}}</h2>
      <div v-if="card.options" class="quiz-options"><button v-for="(option,i) in card.options" :key="i" :disabled="revealed" :class="{chosen:choice===i,correct:revealed&&i===card.correct,incorrect:revealed&&choice===i&&i!==card.correct}" @click="choice=i;revealed=true">{{option}}</button></div>
      <button v-if="!revealed" class="text-btn" @click="revealed=true">{{card.options?'查看答案':'回看讲解'}}</button>
      <div v-else class="recall-answer"><strong v-if="choice!==null">{{choice===card.correct?'答对了':'再看一下'}}</strong><p>{{card.answer}}</p></div>
      <nav v-if="cards.length>1" aria-label="复习卡翻页"><button class="text-btn" :disabled="index===0" @click="move(-1)">上一张</button><button class="text-btn" :disabled="index===cards.length-1" @click="move(1)">下一张</button></nav>
    </template>
    <template v-else-if="loaded">
      <small>{{loadFailed?'暂时无法读取复习内容':'课前热身'}}</small>
      <h2>关于「{{unit.title}}」，你最想弄懂什么？</h2>
      <textarea v-model="response" aria-label="课前想法" rows="3" placeholder="写下想问的问题，进入本节后可继续提问"></textarea>
    </template>
    <p v-else>正在取回之前的学习内容…</p>
    <footer v-if="ready"><button class="button primary" @click="$emit('enter',response.trim())"><BookOpen :size="16"/>进入本节学习 <ArrowRight :size="15"/></button></footer>
  </section>
</template>
<style scoped>
.wait-review {background:#fffefb;border:1px solid #dbe4d6;border-radius:16px;padding:clamp(18px,4vw,36px);margin:20px 0;color:#355445}
header,nav,footer {display:flex;align-items:center;justify-content:space-between;gap:1rem}
header,small {font-size:.82rem;color:#5e755f}
.wait-track {height:6px;border-radius:4px;background:#e7ecdf;overflow:hidden;margin:12px 0 28px}
.wait-track i {display:block;height:100%;background:#658868;transition:width .7s ease-out}
h2 {font-size:1.2rem;line-height:1.6;margin:.6rem 0 1rem}
.recall-answer {background:#f1f5eb;padding:14px;border-radius:8px;max-height:45vh;overflow:auto}
.recall-answer p {white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.7}
nav,footer {margin-top:18px}
textarea {width:100%;border:1px solid #c9d8c6;border-radius:8px;padding:10px}
@media(prefers-reduced-motion:reduce){.wait-track i{transition:none}}
</style>
