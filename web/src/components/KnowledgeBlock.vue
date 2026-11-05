<script setup lang="ts">
import { computed, ref } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { BookOpen, Check, Lightbulb, ArrowRight } from '@lucide/vue'
import StepDiagram from './StepDiagram.vue'
import type { Block } from '../types'
const props=defineProps<{block:Block;compact?:boolean;practice?:{choice?:number;correct?:boolean;used_hint?:boolean};recordable?:boolean}>()
const emit=defineEmits<{source:[id:string];practice:[choice:number,usedHint:boolean]}>()
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
      <pre v-if="block.type==='code'" class="code-block"><code>{{block.body}}</code></pre>
      <div v-else class="prose" v-html="html"></div>
      <StepDiagram v-if="block.type==='diagram' && block.steps?.length" :steps="block.steps"/>
      <template v-if="block.type==='quiz'">
        <div class="quiz-options"><button v-for="(option,i) in block.options" :key="i" :disabled="submitted" :class="{chosen:selected===i,correct:submitted&&i===block.answer,incorrect:submitted&&selected===i&&!correct}" @click="selected=i"><span>{{String.fromCharCode(65+i)}}</span>{{option}}<Check v-if="submitted&&i===block.answer" :size="16"/></button></div>
        <div v-if="!submitted" class="quiz-actions"><button class="button primary small" :disabled="selected===null" @click="submit">看看我的理解 <ArrowRight :size="14"/></button><button class="text-btn" @click="hint=!hint">{{hint?'收起提示':'给我一点提示'}}</button></div>
        <p v-if="hint&&!submitted" class="quiz-hint">{{block.explanation}}</p>
        <div v-if="submitted" class="quiz-feedback" :class="{success:correct}"><strong>{{correct?'这次理解到位了':'我们再看一下这个地方'}}</strong><p>{{block.explanation}}</p><small v-if="hint">这次使用了提示。</small></div>
      </template>
      <div v-if="block.source_ids?.length" class="citations"><button v-for="(source,i) in block.source_ids" :key="source" @click.stop="emit('source',source)"><BookOpen :size="12"/> 来源{{block.source_ids.length>1?` ${i+1}`:''}}</button></div>
    </div>
  </div>
</template>
