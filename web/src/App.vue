<script setup lang="ts">
import { ref, computed } from 'vue'
import { BookOpen, ArrowUpRight, ArrowRight, ChevronRight, ChevronDown, Plus, Upload, X, Sparkles, Clock3, Bookmark, Check, MessageCircle, Send, FileText, Settings2, CircleHelp, Layers3, Leaf, Library, History, RotateCcw, LoaderCircle, PanelLeftClose, Menu, Quote, Lightbulb, SlidersHorizontal } from '@lucide/vue'
import KnowledgeBlock from './components/KnowledgeBlock.vue'
import { useWorkspace } from './useWorkspace'
import type { LearningEvent } from './types'
const {showExtras,learningUnits,curate,courses,course,unit,lesson,turns,health,error,loading,view,source,selected,message,job,minutes,plan,busy,index,chapters,
  guard,openCourse,selectUnit,bookmark,prepare,send,upload,record,correct,openSource,cancel,retry,selectText,practiceFor,refreshPlan}=useWorkspace()
const showUpload=ref(false),showSettings=ref(false),sidebar=ref(false),dragging=ref(false),fileInput=ref<HTMLInputElement|null>(null)
const editEvent=ref<LearningEvent|null>(null),editText=ref('')
const activeEvents=computed(()=>course.value?.events??[])
const understanding=computed(()=>activeEvents.value.some(e=>e.unit_id===unit.value?.id&&e.kind==='understood'))
const nextLearningUnit=computed(()=>course.value?.units.slice(index.value+1).find(u=>u.category==='learn'||!u.category))
const modeLabel=computed(()=>lesson.value?.mode==='ai'?'AI 讲解':lesson.value?.mode==='demo'?'内置体验材料':'原文导读')
const actionLabels:Record<string,string>={answer:'围绕你的问题',clarify:'先弄清卡在哪里',reexplain:'换一种讲法',worked_example:'用一个例子理解',step_diagram:'我们分步看',micro_exercise:'试着用一下'}
const eventLabels:Record<string,string>={understood:'自述已理解',confused:'待解疑问',practice:'练习记录',skip:'已跳过',correction:'你的更正',note:'学习笔记'}
async function handleFile(file?:File){if(!file)return;showUpload.value=false;await upload(file)}
function onDrop(e:DragEvent){dragging.value=false;handleFile(e.dataTransfer?.files[0])}
function beginEdit(e:LearningEvent){editEvent.value=e;editText.value=e.data.text}
async function saveCorrection(){if(editEvent.value&&editText.value.trim()){await correct(editEvent.value,editText.value.trim());editEvent.value=null}}
function formatTime(t:number){return new Date(t*1000).toLocaleString('zh-CN',{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'})}
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <button class="brand" @click="view='learn'"><span class="brand-symbol"><Layers3 :size="23" :stroke-width="1.7"/></span><span>循知<small>让理解发生</small></span></button>
      <nav class="main-nav" aria-label="主导航"><button :class="{active:view==='learn'}" @click="view='learn'"><BookOpen :size="16"/>学习空间</button><button :class="{active:view==='library'}" @click="view='library'"><Library :size="16"/>我的资料</button><button :class="{active:view==='memory'}" @click="view='memory'"><History :size="16"/>学习记录</button></nav>
      <div class="top-actions"><button class="button subtle small" @click="showUpload=true" :disabled="busy"><Plus :size="16"/> 导入资料</button><button class="icon-btn settings-button" @click="showSettings=true" aria-label="模型设置"><Settings2 :size="19"/></button><span class="avatar">我</span></div>
    </header>

    <div v-if="error" class="error-banner" role="alert"><CircleHelp :size="17"/><span>{{error}}</span><button class="icon-btn" @click="error=''" aria-label="关闭提示"><X :size="16"/></button></div>
    <div v-if="job && job.status!=='completed'" class="job-banner" :class="{'job-error':['failed','interrupted'].includes(job.status)}"><LoaderCircle v-if="busy" :size="15" class="spin"/><span>{{job.message||'正在准备…'}}</span><button v-if="busy" class="text-btn" @click="cancel">停止</button><button v-else-if="['failed','interrupted','cancelled'].includes(job.status)" class="text-btn" @click="retry"><RotateCcw :size="13"/>继续尝试</button></div>

    <div v-if="loading" class="initial-loading"><span class="brand-symbol"><Layers3 :size="28"/></span><p>打开你的学习空间…</p><LoaderCircle class="spin" :size="20"/></div>

    <template v-else-if="view==='learn'&&course">
      <div class="workspace-heading"><div class="breadcrumbs"><button class="icon-btn mobile-menu" @click="sidebar=!sidebar" aria-label="展开学习目录"><Menu :size="19"/></button><span>我的学习</span><ChevronRight :size="13"/><span>{{course.title}}</span></div><span class="quiet-status"><span class="status-dot"></span>进度自动保留</span></div>
      <div class="workspace-layout">
        <aside class="course-sidebar" :class="{open:sidebar}">
          <div class="sidebar-label">你的学习路径 <button class="icon-btn" @click="sidebar=false" aria-label="收起目录"><PanelLeftClose :size="16"/></button></div>
          <div class="course-mini-cover"><span class="eyebrow">LEARNING JOURNEY</span><BookOpen :size="32" :stroke-width="1.3"/><h2>{{course.title}}</h2><span>{{course.units.length}} 个学习单元 · 随时开始</span><div class="cover-orbit orbit-one"></div><div class="cover-orbit orbit-two"></div></div>
          <div class="course-selector"><select aria-label="切换课程" :value="course.id" @change="guard(()=>openCourse(($event.target as HTMLSelectElement).value))"><option v-for="c in courses" :key="c.id" :value="c.id">{{c.title}}</option></select><ChevronDown :size="14"/></div>
          <div class="path-controls"><button class="text-btn" @click="showExtras=!showExtras">{{showExtras?'收起导读与附属内容':'查看导读与附属内容'}}</button><button class="text-btn" @click="curate" :disabled="busy||!health.model_configured">根据原文优化路径</button><small>正文优先；导读和致谢仍可查看。</small></div>
          <div class="chapter-list"><div v-for="chapter in chapters" :key="chapter.number" class="chapter-group"><h3><span>{{String(chapter.number).padStart(2,'0')}}</span>{{chapter.title}}</h3><button v-for="u in chapter.units" :key="u.id" class="unit-link" :class="{active:unit?.id===u.id}" @click="selectUnit(u);sidebar=false"><span class="unit-state" :class="{prepared:u.ready}"><BookOpen v-if="unit?.id===u.id" :size="13"/><span v-else></span></span><span>{{u.title}}<small>{{unit?.id===u.id?'正在学习':u.ready?'已准备':'按需准备'}}</small></span><ChevronRight v-if="unit?.id===u.id" :size="14"/></button></div></div>
          <div class="sidebar-bottom"><Leaf :size="16"/><p>不用赶进度。<br/>每次弄懂一点，就很好。</p></div>
        </aside>

        <main class="lesson-content" v-if="unit" @mouseup="selectText">
          <div class="lesson-kicker"><span class="pill">{{modeLabel}}</span><span><Clock3 :size="13"/>约 {{unit.minutes}} 分钟</span><span>{{index+1}} / {{course.units.length}} 节</span></div>
          <h1>{{unit.title}}</h1>
          <div v-if="unit.category && unit.category!=='learn'" class="reading-notice"><span>{{unit.category==='skip'?'这部分默认不纳入学习路径。':'这部分作为可选导读。'}} {{unit.reason}}</span><button v-if="nextLearningUnit" class="text-btn" @click="selectUnit(nextLearningUnit)">直接进入正文 <ArrowRight :size="14"/></button></div>
          <p class="lesson-summary">{{lesson?.summary||'这一节还没有准备。开始时，我们再把它整理成易于消化的内容。'}}</p>
          <div class="lesson-divider"><span></span><Leaf :size="15"/><span></span></div>
          <template v-if="lesson">
            <div v-if="lesson.mode==='extractive'" class="reading-notice"><FileText :size="17"/><span>以下是材料原文，保留真实出处。{{health.model_configured?'可以把这一节整理为 AI 讲解。':'连接 DeepSeek 后可获得重新讲解与按需演示。'}}</span><button v-if="health.model_configured" class="text-btn" @click="prepare" :disabled="busy">准备讲解 <ArrowRight :size="14"/></button><button v-else class="text-btn" @click="showSettings=true">连接模型</button></div>
            <article v-for="(b,i) in lesson.blocks" :key="`${unit.id}-${lesson.mode}-${i}`" :id="`block-${i}`" class="lesson-card" :class="{'saved-block':course.progress.block_index===i}">
              <KnowledgeBlock :block="b" :recordable="true" :practice="practiceFor(i)" @source="openSource" @practice="(choice,usedHint)=>record('practice',b.body,{block_index:i,choice,used_hint:usedHint})"/>
              <button class="save-position" @click.stop="bookmark(i)" :aria-label="`将阅读位置保存到${b.title}`"><Bookmark :size="12" :fill="course.progress.block_index===i?'currentColor':'none'"/>{{course.progress.block_index===i?'上次读到这里':'记住读到这里'}}</button>
            </article>
            <div class="lesson-footer"><div><span class="eyebrow">TAKE YOUR TIME</span><h3>这一小步，理解了吗？</h3><p>可以再问一次，也可以按自己的节奏继续。</p></div><div class="completion-actions"><button class="button" :class="{understood:understanding}" @click="record('understood','用户表示已理解本节内容')"><Check :size="16"/>{{understanding?'已记录你的理解':'我理解了'}}</button><button class="button primary" v-if="nextLearningUnit" @click="selectUnit(nextLearningUnit)">继续下一节 <ArrowRight :size="16"/></button></div></div>
          </template>
          <div v-else class="prepare-card"><span class="round-icon"><Sparkles :size="27"/></span><h2>只准备你现在想学的</h2><p>从这一节开始，保留来源，慢慢往前走。<br/>{{health.model_configured?'DeepSeek 会根据原文准备本节讲解。':'当前可先阅读原文，连接模型后再生成讲解。'}}</p><button class="button primary" @click="prepare" :disabled="busy"><LoaderCircle v-if="busy" class="spin" :size="17"/><BookOpen v-else :size="17"/>{{busy?'正在准备…':'开始这一节'}}</button></div>
          <p class="footer-note">由你决定下一步 · 练习不会限制章节进度</p>
        </main>

        <aside class="companion-sidebar">
          <section class="session-card"><div class="session-top"><span><Leaf :size="16"/>这次，留一点时间给自己</span><select aria-label="本次学习时间" v-model.number="minutes" @change="guard(refreshPlan)"><option :value="10">10 分钟</option><option :value="15">15 分钟</option><option :value="25">25 分钟</option><option :value="40">40 分钟</option></select></div><div v-for="(task,i) in plan.tasks" :key="i" class="session-task"><span class="task-circle">{{i+1}}</span><div><strong>{{task.title}}</strong><p>{{task.description}}</p></div></div><div class="session-caption">根据实际进度安排，今天学多少都可以。</div></section>
          <section class="chat-card">
            <div class="chat-heading"><span class="assistant-avatar"><Sparkles :size="19"/></span><div><h2>你的学习伙伴</h2><p>不明白的地方，我们一起拆开看。</p></div><span class="chat-status" :class="{online:health.model_configured}" :title="health.model_configured?'已配置模型':'示例 / 原文模式'"></span></div>
            <div class="chat-messages" aria-live="polite">
              <div v-if="!turns.length" class="chat-welcome"><span class="welcome-symbol"><MessageCircle :size="25" :stroke-width="1.4"/></span><h3>卡住，也是一种开始。</h3><p>选中左边的一段内容，或直接告诉我<br/>哪里还没明白。</p><div class="suggestion-stack"><button @click="send('confused','这里我还是不太明白，可以换一种方式讲讲吗？')" :disabled="busy"><CircleHelp :size="15"/>这里我还没懂<ArrowUpRight :size="14"/></button><button @click="send('example','能给我一个贴近日常生活的例子吗？')" :disabled="busy"><Lightbulb :size="15"/>给我一个具体的例子<ArrowUpRight :size="14"/></button><button @click="send('diagram','可以用步骤图演示这个过程吗？')" :disabled="busy"><Layers3 :size="15"/>让这个过程动起来<ArrowUpRight :size="14"/></button></div></div>
              <template v-for="turn in turns" :key="turn.id"><div class="user-message"><small v-if="turn.data.selected_text"><Quote :size="12"/>{{turn.data.selected_text.slice(0,90)}}</small><p>{{turn.data.message}}</p></div><div class="assistant-message"><div class="response-label"><Sparkles :size="13"/>{{actionLabels[turn.data.response.action]||'一起理解'}}<span v-if="turn.data.mode==='demo'">预设示例</span><span v-if="turn.data.mode==='extractive'">原文检索</span></div><KnowledgeBlock v-for="(b,i) in turn.data.response.blocks" :key="i" :block="b" :compact="true" @source="openSource"/></div></template>
              <div v-if="busy&&job?.kind==='tutor'" class="thinking"><span></span><span></span><span></span>正在结合原文整理…</div>
            </div>
            <div class="chat-composer"><div v-if="selected" class="selection-chip"><Quote :size="13"/><span>{{selected.slice(0,55)}}{{selected.length>55?'…':''}}</span><button @click="selected=''" aria-label="清除选中文字"><X :size="12"/></button></div><form @submit.prevent="send()"><textarea v-model="message" placeholder="这个地方，我想再问问…" aria-label="向学习伙伴提问" rows="2" @keydown.enter.exact.prevent="send()"></textarea><div class="composer-bottom"><span>跟着你的问题，换一种讲法</span><button :disabled="busy||!message.trim()" type="submit" aria-label="发送问题"><Send :size="16"/></button></div></form><p v-if="!health.model_configured" class="connection-note"><span></span>{{course.demo?'示例体验：回答为预设内容':'未连接模型：当前仅检索原文'}}<button @click="showSettings=true">连接 DeepSeek</button></p><p v-else class="connection-note"><span class="connected"></span>已连接 {{health.provider}} · 重要内容请核对出处</p></div>
          </section>
        </aside>
      </div>
    </template>

    <main v-else-if="view==='library'" class="collection-page"><div class="page-intro"><div><span class="eyebrow">YOUR KNOWLEDGE, YOUR PACE</span><h1>每一份资料，都可以慢慢学。</h1><p>放下从头读完的压力，从一个想弄懂的地方开始。</p></div><button class="button primary" @click="showUpload=true" :disabled="busy"><Plus :size="17"/>导入 PDF</button></div><div class="library-grid"><button v-for="c in courses" :key="c.id" class="library-card" @click="guard(()=>openCourse(c.id))"><div class="library-art"><BookOpen :size="42" :stroke-width="1.2"/><span>{{c.demo?'体验课程':'我的资料'}}</span><div class="library-art-circle"></div></div><div class="library-body"><h2>{{c.title}}</h2><p>{{c.description}}</p><div><span>{{c.units_count}} 个学习单元</span><ArrowUpRight :size="18"/></div></div></button><button class="library-card library-add" @click="showUpload=true" :disabled="busy"><Plus :size="32" :stroke-width="1.2"/><h3>添加一份学习资料</h3><p>文本型 PDF · 最大 50 MB</p></button></div></main>

    <main v-else-if="view==='memory'" class="collection-page memory-page"><div class="page-intro"><div><span class="eyebrow">A LITTLE FURTHER, EVERY TIME</span><h1>记住你走过的每一小步。</h1><p>读过、觉得懂了、独立做过，是不同的学习证据。你可以更正记录。</p></div><span class="pill"><History :size="14"/>{{course?.title}}</span></div><div class="memory-layout"><div class="memory-list"><div v-if="!activeEvents.length" class="empty-state"><Bookmark :size="35" :stroke-width="1.3"/><h2>你的第一条学习记录，正在路上</h2><p>提一个疑问、完成一道练习，或告诉我你理解了。<br/>这些真实的反馈，会留在这里。</p><button class="button" @click="view='learn'">回到学习 <ArrowRight :size="15"/></button></div><article v-for="e in activeEvents" :key="e.id" class="memory-item"><span class="memory-icon" :class="e.kind"><CircleHelp v-if="e.kind==='confused'" :size="18"/><Check v-else-if="e.kind==='understood'" :size="18"/><History v-else :size="18"/></span><div class="memory-copy"><div><strong>{{eventLabels[e.kind]||e.kind}}</strong><time>{{formatTime(e.created)}}</time></div><p>{{e.data.text}}</p><small v-if="e.kind==='practice'">{{e.data.correct?'本次答对':'本次尚未答对'}} · {{e.data.used_hint?'使用了提示':'未使用提示'}}</small><small>{{course?.units.find(u=>u.id===e.unit_id)?.title}}</small></div><button class="text-btn" @click="beginEdit(e)">更正</button></article></div><aside class="memory-explanation"><Leaf :size="23"/><h3>记忆，可以由你修正。</h3><p>这里保存实际发生的学习行为，不给你贴上固定的能力标签。</p><p>“我理解了”记录你的感受，练习记录实际结果。章节始终由你自由选择。</p></aside></div></main>

    <main v-else class="empty-state"><h1>暂时没有打开课程</h1><p>检查服务连接，或导入一份 PDF 开始。</p><button class="button primary" @click="showUpload=true">导入资料</button></main>

    <div v-if="showUpload" class="modal-backdrop" @click.self="showUpload=false"><section class="modal upload-modal" role="dialog" aria-modal="true" aria-label="导入学习资料"><button class="modal-close icon-btn" @click="showUpload=false" aria-label="关闭"><X :size="20"/></button><span class="eyebrow">START WITH SOMETHING CURIOUS</span><h2>把想学的，放进来。</h2><p>先整理目录，再准备你想学的那一节。</p><div class="drop-zone" :class="{dragging}" @dragover.prevent="dragging=true" @dragleave.prevent="dragging=false" @drop.prevent="onDrop" @click="fileInput?.click()" role="button" tabindex="0" @keydown.enter="fileInput?.click()"><span><Upload :size="28" :stroke-width="1.4"/></span><strong>拖放 PDF 到这里</strong><p>或点击选择文件</p><small>支持文本型 PDF · 最大 50 MB / 600 页</small></div><input ref="fileInput" class="visually-hidden" type="file" accept="application/pdf,.pdf" @change="handleFile(($event.target as HTMLInputElement).files?.[0])"/><div class="upload-note"><BookOpen :size="17"/><p>扫描页、图表或公式可能无法完整提取。导入后会显示缺漏情况，并保留查看原文的入口。</p></div></section></div>

    <div v-if="source" class="modal-backdrop source-backdrop" @click.self="source=null"><section class="source-drawer" role="dialog" aria-modal="true" aria-label="原文出处"><div class="drawer-heading"><span><BookOpen :size="19"/>原文出处</span><button class="icon-btn" @click="source=null" aria-label="关闭出处"><X :size="19"/></button></div><span class="pill">{{course?.demo?'自编体验材料':`文件第 ${source.page+1} 页`}}</span><h2>{{source.title}}</h2><p class="source-document">{{course?.document.title}}</p><blockquote>{{source.text}}</blockquote><a v-if="!course?.demo" class="button primary" :href="`/api/documents/${course?.document_id}/file#page=${source.page+1}`" target="_blank" rel="noopener">打开 PDF 原页 <ArrowUpRight :size="16"/></a><p v-else class="source-note">这段内容为项目内置示例，不是你上传的教材摘录。</p></section></div>

    <div v-if="showSettings" class="modal-backdrop" @click.self="showSettings=false"><section class="modal settings-modal" role="dialog" aria-modal="true" aria-label="模型连接设置"><button class="modal-close icon-btn" @click="showSettings=false" aria-label="关闭"><X :size="20"/></button><span class="round-icon"><SlidersHorizontal :size="25"/></span><h2>连接你的学习伙伴</h2><p>已为 DeepSeek 准备好接口。密钥通过本机配置读取，不会发送给前端。</p><div class="setting-row"><span>模型</span><strong>{{health.model}}</strong></div><div class="setting-row"><span>连接状态</span><strong>{{health.model_configured?'已配置，调用时验证':'等待密钥'}}</strong></div><div class="config-instructions"><p>在项目根目录复制 <code>.env.example</code> 为 <code>.env</code>，填写：</p><pre>LLM_API_KEY=你的 DeepSeek 密钥</pre><p>保存后重启后端，再刷新页面。示例材料和已保存进度会保留。</p></div><button class="button primary" @click="showSettings=false">知道了 <Check :size="16"/></button></section></div>

    <div v-if="editEvent" class="modal-backdrop" @click.self="editEvent=null"><section class="modal" role="dialog" aria-modal="true" aria-label="更正学习记录"><button class="modal-close icon-btn" @click="editEvent=null" aria-label="关闭"><X :size="20"/></button><h2>这条记录，听你的。</h2><p>写下更准确的情况。后续辅导将使用新的记录。</p><textarea class="correction-input" v-model="editText" rows="5" aria-label="更正后的记录"></textarea><button class="button primary" :disabled="!editText.trim()" @click="saveCorrection">保存更正 <Check :size="16"/></button></section></div>
  </div>
</template>
