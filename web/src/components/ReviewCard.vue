<script setup lang="ts">
import {computed,ref} from 'vue'
import {api} from '../api'
import type {LearningEvent,ReviewStatus,Turn,Unit} from '../types'
import KnowledgeBlock from './KnowledgeBlock.vue'
import SceneDialog from './SceneDialog.vue'
import type {Block} from '../types'

const props=defineProps<{event:LearningEvent;courseId:string;unit?:Unit;label:string;time:string}>()
const emit=defineEmits<{revisit:[];saved:[];source:[id:string]}>()
const editing=ref(false), saving=ref(false), loading=ref(false), expanded=ref(false)
const note=ref(''), status=ref<ReviewStatus>('pending'), error=ref('')
const exchange=ref<Turn|null>(null), scene=ref<Block|null>(null)
const turnId=computed(()=>props.event.data.turn_id ?? (props.event.request_id?.startsWith('confusion:') ? props.event.request_id.slice(10) : null))
function edit(){
  note.value=props.event.review_note??''
  status.value=props.event.review_status??'pending'
  editing.value=true
}
async function save(){
  saving.value=true
  error.value=''
  try {
    await api('/courses/'+props.courseId+'/learning-events/'+props.event.id+'/review',{method:'PUT',body:JSON.stringify({status:status.value,note:note.value.trim()})})
    editing.value=false
    emit('saved')
  } catch(e){error.value=String(e)} finally {saving.value=false}
}
async function toggleAnswer(){
  if(exchange.value){expanded.value=!expanded.value;return}
  loading.value=true
  error.value=''
  try {
    exchange.value=await api<Turn>('/courses/'+props.courseId+'/tutor-turns/'+turnId.value)
    expanded.value=true
  } catch(e){error.value=String(e)} finally {loading.value=false}
}
</script>
<template>
  <article class="memory-item review-card">
    <header><strong>{{label}}</strong><time>{{time}}</time></header>
    <small>{{unit?.chapter_title}} · {{unit?.title}}</small>
    <p>{{event.data.text}}</p>
    <blockquote v-if="event.data.selected_text">{{event.data.selected_text}}</blockquote>
    <p v-if="event.kind==='practice'">当时选了 {{event.data.chosen_answer ?? String.fromCharCode(65+(event.data.choice??0))}} · {{event.data.correct?'答对':'答错'}} · {{event.data.used_hint?'看过提示':'独立作答'}}</p>
    <p v-if="event.review_status"><b>{{event.review_status==='resolved'?'已掌握':'待复习'}}</b> {{event.review_note}}</p>
    <footer>
      <button class="text-btn" @click="emit('revisit')">{{event.data.block_index!=null?'回到学习位置':'回到本节'}}</button>
      <button v-if="turnId" class="text-btn" :disabled="loading" :aria-expanded="expanded" @click="toggleAnswer">{{expanded?'收起回答':'回看当时回答'}}</button>
      <button class="text-btn" @click="edit" v-if="!editing">记录复习结果</button>
    </footer>
    <section v-if="expanded && exchange">
      <KnowledgeBlock v-for="(block,i) in exchange.data.response.blocks" :key="i" :block="block" :compact="true" :read-only="true" @source="emit('source',$event)" @scene="scene=$event"/>
    </section>
    <form v-if="editing" @submit.prevent="save">
      <label><input type="radio" value="pending" v-model="status"> 待复习</label>
      <label><input type="radio" value="resolved" v-model="status"> 已掌握</label>
      <textarea v-model="note" maxlength="3000" rows="3" aria-label="复习笔记" placeholder="用自己的话再解释一次，或记下还卡在哪里"></textarea>
      <button class="button primary small" :disabled="saving">保存复习结果</button>
      <button type="button" class="text-btn" :disabled="saving" @click="editing=false">取消</button>
    </form>
    <small v-if="error" role="alert">{{error}}</small>
    <SceneDialog v-if="scene" :block="scene" @close="scene=null"/>
  </article>
</template>
<style scoped>
.review-card { display:grid; gap:.65rem; min-width:0; color:#345045; }
header,footer {display:flex;gap:1rem;align-items:center;flex-wrap:wrap}
time,small {font-size:.78rem;color:#63756b}
p,blockquote {margin:0;line-height:1.65;overflow-wrap:anywhere;white-space:pre-wrap}
blockquote {border-left:3px solid #afc4aa;padding-left:.7rem;max-height:9rem;overflow:auto}
form {border-top:1px solid #dde6da;padding-top:1rem}
label,form button {margin-right:1rem}
textarea {display:block;width:100%;margin:.8rem 0;padding:.65rem;border:1px solid #b9cbb7;border-radius:8px}
</style>
