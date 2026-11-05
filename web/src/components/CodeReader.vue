<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Block } from '../types'
const props=defineProps<{block:Block}>()
const emit=defineEmits<{ask:[text:string]}>()
const step=ref(0),line=ref(1)
const lines=computed(()=>props.block.body.split('\n'))
const trace=computed(()=>props.block.code_trace??[])
const current=computed(()=>trace.value[step.value])
function ask(){const start=current.value?.line_start??line.value,end=current.value?.line_end??line.value;emit('ask',`关于「${props.block.title||'代码'}」第 ${start}–${end} 行：\n${lines.value.slice(start-1,end).join('\n')}\n\n完整代码上下文：\n${props.block.body}`)}
</script>
<template>
  <section class="code-reader">
    <div class="code-toolbar"><span>{{current?'逐步推演 · 非实际执行':'代码阅读 · 点击行号定位'}}</span><button class="text-btn" @click="ask">询问当前代码</button></div>
    <div class="code-lines"><div v-for="(text,i) in lines" :key="i" :class="{highlight:current?i+1>=current.line_start&&i+1<=current.line_end:i+1===line}"><button :aria-label="`选择代码第 ${i+1} 行`" @click="line=i+1;step=-1">{{i+1}}</button><code>{{text||' '}}</code></div></div>
    <div v-if="trace.length" class="code-trace"><div><button :disabled="step<=0" @click="step--">上一步</button><span>{{step+1}} / {{trace.length}}</span><button :disabled="step>=trace.length-1" @click="step++">下一步</button></div><p>{{current?.explanation||'点击下一步开始推演'}}</p><pre v-if="current?.variables">{{current.variables}}</pre></div>
  </section>
</template>
<style scoped>
.code-reader{border:1px solid #d9e1d5;border-radius:12px;overflow:hidden;margin:15px 0}.code-toolbar,.code-trace>div{display:flex;justify-content:space-between;gap:12px;padding:12px;background:#edf2e8;font-size:12px}.code-lines{overflow:auto;background:#172c26;color:#e3eee7;padding:12px 0;max-height:540px}.code-lines>div{display:flex;min-width:max-content;line-height:1.8;font-size:13px}.code-lines button{flex:0 0 45px;color:#a5b7a9;user-select:none}.code-lines code{white-space:pre;padding-right:20px;font-family:ui-monospace,monospace}.code-lines .highlight{background:#37684f}.code-trace p,.code-trace pre{margin:12px;white-space:pre-wrap;font-size:13px;line-height:1.7}
</style>
