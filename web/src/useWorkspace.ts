import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { api, requestId } from './api'
import type { Course, CourseItem, Unit, Lesson, Turn, Job, Source, Progress, LearningEvent } from './types'

export function useWorkspace() {
  const courses = ref<CourseItem[]>([]), course = ref<Course|null>(null), unit = ref<Unit|null>(null)
  const lesson = ref<Lesson|null>(null), turns = ref<Turn[]>([]), health = ref({api_revision:'',model_configured:false,model:'',provider:'DeepSeek'})
  const rewardNotice = ref('')
  const error = ref(''), loading = ref(true), view = ref('learn'), source = ref<Source|null>(null), selected = ref('')
  const message = ref(''), job = ref<Job|null>(null), minutes = ref(Number(localStorage.getItem('xunzhi.minutes')) || 15)
  const plan = ref<{tasks:{title:string;description:string;minutes:number}[]}>({tasks:[]})
  const busy = computed(() => !!job.value && ['queued','running'].includes(job.value.status))
  const index = computed(() => course.value?.units.findIndex(u=>u.id===unit.value?.id) ?? 0)
  const depth = ref<'quick'|'full'>(localStorage.getItem('xunzhi.depth')==='quick'?'quick':'full')
  const showExtras = ref(false)
  const learningUnits = computed(() => course.value?.units.filter(u=>u.category==='learn'||!u.category) ?? [])
  const chapters = computed(() => {
    const groups: {number:number;title:string;units:Unit[]}[] = []
    for (const u of course.value?.units ?? []) {
      if(!showExtras.value && u.category && u.category!=='learn') continue
      let group = groups.find(g=>g.number===u.chapter)
      if (!group) { group = {number:u.chapter,title:u.chapter_title,units:[]}; groups.push(group) }
      group.units.push(u)
    }
    return groups
  })
  let alive = true
  async function guard(fn:()=>Promise<void>) { try { await fn() } catch(e) { error.value = e instanceof Error ? e.message : '暂时未能完成，请重试。' } }
  async function refreshCourses() { courses.value = await api<CourseItem[]>('/courses') }
  async function refreshCourse() { if(course.value) course.value = await api<Course>(`/courses/${course.value.id}`) }
  async function refreshPlan() {
    localStorage.setItem('xunzhi.minutes', String(minutes.value))
    if(course.value) plan.value = await api(`/courses/${course.value.id}/session-plan?minutes=${minutes.value}`)
  }
  async function loadUnit(id:string, restore=false) {
    if(!course.value) return
    const result = await api<{unit:Unit;lesson:Lesson|null;turns:Turn[]}>(`/courses/${course.value.id}/units/${id}`)
    unit.value = result.unit; lesson.value = result.lesson; turns.value = result.turns; selected.value = ''
    if(restore) {
      await nextTick()
      const saved = course.value.progress.block_index
      if(saved > 0) document.getElementById(`block-${saved}`)?.scrollIntoView({block:'center'})
    }
  }
  async function openCourse(id:string) {
    course.value = await api<Course>(`/courses/${id}`)
    localStorage.setItem('xunzhi.course', id)
    await loadUnit(course.value.progress.unit_id, true)
    await refreshPlan()
    view.value = 'learn'
  }
  async function selectUnit(u:Unit) {
    if(!course.value) return
    await guard(async()=>{
      await savePosition(u.id,0)
      await loadUnit(u.id)
      await refreshPlan()
      window.scrollTo({top:0,behavior:'smooth'})
    })
  }
  async function savePosition(unitId:string, blockIndex:number) {
    if(!course.value) return
    const next = await api<Progress>(`/courses/${course.value.id}/progress`,{method:'PATCH',body:JSON.stringify({request_id:requestId(),unit_id:unitId,block_index:blockIndex,expected_version:course.value.progress.version})})
    course.value.progress = next
  }
  async function bookmark(blockIndex:number) { if(unit.value) await guard(()=>savePosition(unit.value!.id,blockIndex)) }
  async function watchJob(initial:Job, context:{courseId?:string;unitId?:string}={}) {
    job.value = initial
    localStorage.setItem('xunzhi.pending',JSON.stringify({id:initial.id,...context}))
    try {
      while(alive && ['queued','running'].includes(job.value.status)) {
        await new Promise(r=>setTimeout(r,900))
        if(!alive) return
        job.value = await api<Job>(`/jobs/${initial.id}`)
      }
      const done = job.value
      if(done.status==='completed') {
        if(done.kind==='import' && done.result?.course_id) { await refreshCourses(); await openCourse(done.result.course_id) }
        else if(context.courseId===course.value?.id) {
          await refreshCourse()
          if(context.unitId===unit.value?.id) await loadUnit(context.unitId!)
          await refreshPlan()
        }
      }
      if(done.status==='failed') error.value = done.error?.message || done.message
      if(['completed','cancelled'].includes(done.status)) localStorage.removeItem('xunzhi.pending')
    } catch(e) { error.value = e instanceof Error ? e.message : '连接中断，重新打开后可以继续。' }
  }
  async function regenerate() {
    if(!course.value || !unit.value || busy.value) return
    await guard(async()=>{
      const j=await api<Job>(`/courses/${course.value!.id}/units/${unit.value!.id}/regenerate`,{method:'POST',body:JSON.stringify({request_id:requestId(),expected_revision:lesson.value?.revision??0,depth:depth.value})})
      await watchJob(j,{courseId:course.value!.id,unitId:unit.value!.id})
    })
  }
  async function curate() {
    if(!course.value || busy.value) return
    await guard(async()=>{
      const j=await api<Job>(`/courses/${course.value!.id}/curriculum`,{method:'POST'})
      await watchJob(j,{courseId:course.value!.id})
    })
  }
  async function prepare() {
    if(!course.value || !unit.value || busy.value) return
    await guard(async()=>{
      const j = await api<Job>(`/courses/${course.value!.id}/units/${unit.value!.id}/prepare?depth=${depth.value}`,{method:'POST'})
      await watchJob(j,{courseId:course.value!.id,unitId:unit.value!.id})
    })
  }
  async function send(intent='ask', prompt?:string) {
    if(!course.value || !unit.value || busy.value) return
    const content = prompt || message.value.trim()
    if(!content) return
    error.value = ''
    await guard(async()=>{
      const j = await api<Job>(`/courses/${course.value!.id}/tutor-turns`,{method:'POST',body:JSON.stringify({request_id:requestId(),unit_id:unit.value!.id,message:content,selected_text:selected.value,intent})})
      message.value = ''
      await watchJob(j,{courseId:course.value!.id,unitId:unit.value!.id})
      await nextTick()
      document.querySelector('.chat-messages')?.scrollTo({top:999999,behavior:'smooth'})
    })
  }
  async function upload(file:File) {
    if(busy.value) return
    await guard(async()=>{
      if(file.size>50*1024*1024) throw new Error('文件不能超过 50 MB')
      const form = new FormData(); form.append('file',file)
      const j = await api<Job>('/documents',{method:'POST',body:form})
      await watchJob(j)
    })
  }
  async function record(kind:string, text='', extras:Record<string,unknown>={}) {
    if(!course.value || !unit.value) return
    await guard(async()=>{
      const result=await api<{xp_awarded:number}>(`/courses/${course.value!.id}/learning-events`,{method:'POST',body:JSON.stringify({request_id:requestId(),unit_id:unit.value!.id,kind,text,...extras})})
      rewardNotice.value=result.xp_awarded?'答对了，经验 +1！':''
      await refreshCourse(); await refreshPlan()
    })
  }
  async function correct(event:LearningEvent,text:string) { await record('correction',text,{unit_id:event.unit_id,target_id:event.id}) }
  async function openSource(id:string) { await guard(async()=>{source.value=await api<Source>(`/documents/${course.value!.document_id}/chunks/${id}`)}) }
  async function cancel() {
    if(job.value) await guard(async()=>{job.value=await api<Job>(`/jobs/${job.value!.id}/cancel`,{method:'POST'})})
  }
  async function retry() {
    if(!job.value || busy.value) return
    await guard(async()=>{
      const context = JSON.parse(localStorage.getItem('xunzhi.pending')||'{}')
      await watchJob(await api<Job>(`/jobs/${job.value!.id}/retry`,{method:'POST'}),context)
    })
  }
  function selectText() { const text=window.getSelection()?.toString().trim(); if(text) selected.value=text.slice(0,3000) }
  function practiceFor(blockIndex:number) { return course.value?.events.find(e=>e.unit_id===unit.value?.id && e.kind==='practice' && e.data.block_index===blockIndex && (e.data.lesson_revision??0)===(lesson.value?.revision??0))?.data }
  onMounted(async()=>{
    await guard(async()=>{
      health.value=await api('/health'); await refreshCourses()
      const saved=localStorage.getItem('xunzhi.course')
      const target=courses.value.find(c=>c.id===saved)||courses.value[0]
      if(target) await openCourse(target.id)
      loading.value=false
      const pending=localStorage.getItem('xunzhi.pending')
      if(pending) { const p=JSON.parse(pending); await watchJob(await api<Job>(`/jobs/${p.id}`),p) }
    })
    loading.value=false
  })
  onUnmounted(()=>{alive=false})
  return {rewardNotice,depth,regenerate,showExtras,learningUnits,curate,courses,course,unit,lesson,turns,health,error,loading,view,source,selected,message,job,minutes,plan,busy,index,chapters,
          guard,openCourse,selectUnit,bookmark,prepare,send,upload,record,correct,openSource,cancel,retry,selectText,practiceFor,refreshPlan}
}
