<script setup lang="ts">
import { computed, ref } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { BookOpen, Check, Lightbulb, ArrowRight } from '@lucide/vue'
import ScenePlayer from './ScenePlayer.vue'
import CodeReader from './CodeReader.vue'
import type { Block } from '../types'
const props=defineProps<{block:Block;compact?:boolean;practice?:{choice?:number;correct?:boolean;used_hint?:boolean};readOnly?:boolean;recordable?:boolean}>()
const emit=defineEmits<{askCode:[text:string];scene:[block:Block];source:[id:string];practice:[choice:number,usedHint:boolean]}>()
const selected=ref<number|null>(props.practice?.choice??null),submitted=ref(!!props.practice),hint=ref(!!props.practice?.used_hint)
const html=computed(()=>DOMPurify.sanitize(marked.parse(props.block.body||'',{async:false}) as string,{FORBID_TAGS:['img','iframe','style','script'],FORBID_ATTR:['style']}))
const correct=computed(()=>selected.value===props.block.answer)
function submit(){if(selected.value===null)return;submitted.value=true;emit('practice',selected.value,hint.value)}
</script>
<template>
  <div class="knowledge-block" :class="[block.type,{compact}]">
    <div v-if="block.type==='callout'" class="callout-icon"><Lightbulb :size="20"/></div>
    <div class="block-inner">
      <div v-if="block.type==='quiz'" class="eyebrow quiz-eyebrow">随手练一练 <span>{{recordable?'可跳过，不影响继续学习':'体验练习'}}</span></div>
      <h3 v-if="block.title">{{block.title}}</h3>
      <CodeReader v-if="block.type==='code'" :block="block" :read-only="readOnly" @ask="emit('askCode',$event)"/>
      <details v-else-if="block.type==='source'" class="original-text"><summary>展开完整原文（包括提取到的代码）</summary><pre>{{block.body}}</pre></details>
      <div v-else class="prose" v-html="html"></div>
      <template v-if="block.type==='scene' && block.scene"><button v-if="compact" class="button primary small" @click="emit('scene',block)">打开演示区 <ArrowRight :size="14"/></button><ScenePlayer v-else :scene="block.scene"/></template>
      <div v-if="block.type==='diagram' && block.steps?.length" class="legacy-steps"><small>步骤说明 · 旧内容</small><ol><li v-for="(s,i) in block.steps" :key="i"><strong>{{s.label}}</strong><p>{{s.detail}}</p></li></ol></div>
      <template v-if="block.type==='quiz'">
        <div class="quiz-options"><button v-for="(option,i) in block.options" :key="i" :disabled="submitted" :class="{chosen:selected===i,correct:submitted&&i===block.answer,incorrect:submitted&&selected===i&&!correct}" @click="selected=i"><span>{{String.fromCharCode(65+i)}}</span>{{option}}<Check v-if="submitted&&i===block.answer" :size="16"/></button></div>
        <div v-if="!submitted" class="quiz-actions"><button class="button primary small" :disabled="selected===null" @click="submit">看看我的理解 <ArrowRight :size="14"/></button><button class="text-btn" @click="hint=!hint">{{hint?'收起提示':'给我一点提示'}}</button></div>
        <p v-if="hint&&!submitted" class="quiz-hint">{{block.explanation}}</p>
        <button v-if="submitted && recordable" class="text-btn" @click="selected=null;submitted=false;hint=false">重新作答</button>
        <div v-if="submitted" class="quiz-feedback" :class="{success:correct}"><strong>{{correct?'这次理解到位了':'我们再看一下这个地方'}}</strong><p>{{block.explanation}}</p><small v-if="hint">这次使用了提示。</small></div>
      </template>
      <div v-if="block.source_ids?.length" class="citations"><button v-for="(source,i) in block.source_ids" :key="source" @click.stop="emit('source',source)"><BookOpen :size="12"/> 来源{{block.source_ids.length>1?` ${i+1}`:''}}</button></div>
    </div>
  </div>
</template>

<style scoped>
.block-inner, .prose { min-width: 0; }
.prose { overflow-x: auto; }
.prose :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin-block: .85em;
}
.prose :deep(th), .prose :deep(td) {
  padding: .55em .8em;
  text-align: start;
  vertical-align: top;
  border: 1px solid #dce4d7;
  min-width: 5em;
  overflow-wrap: anywhere;
}
.prose :deep(th) { background: #eff4eb; color: #385448; }
</style>
