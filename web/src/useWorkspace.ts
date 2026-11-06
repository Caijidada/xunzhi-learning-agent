import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { rememberReading } from './waitReview'
import { api, requestId } from './api'
import type { Course, CourseItem, Unit, Lesson, Turn, Job, Source, Progress, LearningEvent } from './types'

export function useWorkspace() {
  const courses = ref<CourseItem[]>([]), course = ref<Course|null>(null), unit = ref<Unit|null>(null)
  const lesson = ref<Lesson|null>(null), turns = ref<Turn[]>([]), health = ref({api_revision:'',model_configured:false,model:'',provider:'DeepSeek'})
  const selectionBlock = ref<number|null>(null)
  const locationNotice = ref('')
  const rewardNotice = ref<{unitId:string; blockIndex:number; points:number} | null>(null)
  let rewardTimeout: ReturnType<typeof setTimeout> | undefined
  const stoppedNotice = ref('')
  let stopTimeout: ReturnType<typeof setTimeout> | undefined
  let pollVersion = 0
  const error = ref(''), loading = ref(true), view = ref('learn'), source = ref<Source|null>(null), selected = ref('')
  const message = ref(''), job = ref<Job|null>(null), minutes = ref(Number(localStorage.getItem('xunzhi.minutes')) || 15)
  const plan = ref<{tasks:{event_id?:string;title:string;description:string;minutes:number}[]}>({tasks:[]})
  const switchingDepth = ref(false)
  const busy = computed(() => switchingDepth.value || !!job.value && ['queued','running'].includes(job.value.status))
  type WaitState = {id:string; status:string; message:string}
  const waiting = ref<Record<string,WaitState>>(JSON.parse(localStorage.getItem('xunzhi.lesson-waits') || '{}'))
  const waitKey = computed(() => course.value?.id + '/' + unit.value?.id)
  const reviewWait = computed(() => waiting.value[waitKey.value])
  function setWait(key:string, state?:WaitState) {
    if (state) waiting.value[key] = state
    else delete waiting.value[key]
    localStorage.setItem('xunzhi.lesson-waits', JSON.stringify(waiting.value))
  }
  async function enterPrepared(question:string) {
    const key = waitKey.value
    if (!unit.value || reviewWait.value?.status !== 'completed') return
    await guard(async () => {
      await loadUnit(unit.value!.id)
      setWait(key)
      if (question) message.value=question
      if (lesson.value && course.value && unit.value) rememberReading(course.value.id, unit.value.id)
      window.scrollTo({top:0})
    })
  }
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
    unit.value = result.unit; lesson.value = (result.lesson?.status==='generating'?null:result.lesson); turns.value = result.turns; selected.value = ''; selectionBlock.value=null; locationNotice.value=''
    if (result.lesson?.depth === 'quick' || result.lesson?.depth === 'full') depth.value=result.lesson.depth
    if (result.lesson?.status !== 'generating' && result.lesson && !waiting.value[course.value.id+'/'+id])
      rememberReading(course.value.id, id)
    if(restore) {
      await nextTick()
      const saved = course.value.progress.block_index
      const target = document.getElementById(`block-${saved}`)
      if (target && saved > 0) {
        for (let parent = target.parentElement; parent; parent = parent.parentElement) {
          if (parent instanceof HTMLDetailsElement) parent.open = true
        }
        target.scrollIntoView({block:'center'})
      }
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
  async function watchJob(initial:Job, context:{courseId?:string;unitId?:string;review?:boolean}={}) {
    const version = ++pollVersion
    const key = context.courseId + '/' + context.unitId
    function updateWait(j:Job) {
      if (context.review) {
        if (['queued','running','completed'].includes(j.status))
          setWait(key,{id:j.id,status:j.status,message:j.message})
        else setWait(key)
      }
    }
    job.value = initial
    updateWait(initial)
    localStorage.setItem('xunzhi.pending',JSON.stringify({id:initial.id,...context}))
    try {
      while(alive && ['queued','running'].includes(job.value.status)) {
        await new Promise(r=>setTimeout(r,900))
        if(!alive || version !== pollVersion) return
        const latest = await api<Job>(`/jobs/${initial.id}`)
        if(version !== pollVersion) return
        job.value = latest
        updateWait(job.value)
      }
      const done = job.value
      if(done.status==='completed') {
        if(done.kind==='import' && done.result?.course_id) { await refreshCourses(); await openCourse(done.result.course_id) }
        else if(context.courseId===course.value?.id) {
          await refreshCourse()
          if(!context.review && context.unitId===unit.value?.id) await loadUnit(context.unitId!)
          await refreshPlan()
        }
      }
      if(done.status==='completed') localStorage.removeItem('xunzhi.pending')
    } catch(e) { error.value = e instanceof Error ? e.message : '连接中断，重新打开后可以继续。' }
  }
  async function switchDepth() {
    const current = lesson.value, courseId = course.value?.id, unitId = unit.value?.id
    const requested = depth.value
    localStorage.setItem('xunzhi.depth',requested)
    if (!current || !courseId || !unitId || current.depth === requested) return
    switchingDepth.value=true
    try {
      const result=await api<{lesson:Lesson|null}>(`/courses/${courseId}/units/${unitId}/activate?depth=${requested}&revision=${current.revision??0}`,{method:'POST'})
      if (!result.lesson || course.value?.id!==courseId || unit.value?.id!==unitId) return
      lesson.value=result.lesson
      selected.value=''
      selectionBlock.value=null
      await refreshCourse()
      await nextTick()
      const saved=course.value?.progress.block_index
      if (saved) document.getElementById(`block-${saved}`)?.scrollIntoView({block:'center'})
    } catch(e) {
      if(current.depth==='quick'||current.depth==='full') depth.value=current.depth
      error.value=e instanceof Error?e.message:'切换讲义失败，请重试'
    } finally { switchingDepth.value=false }
  }
  async function regenerate() {
    if(!course.value || !unit.value || busy.value) return
    await guard(async()=>{
      const context={courseId:course.value!.id,unitId:unit.value!.id,review:depth.value==='full'}
      const j=await api<Job>(`/courses/${course.value!.id}/units/${unit.value!.id}/regenerate`,{method:'POST',body:JSON.stringify({request_id:requestId(),expected_revision:lesson.value?.revision??0,depth:depth.value})})
      await watchJob(j,context)
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
      const context={courseId:course.value!.id,unitId:unit.value!.id,review:depth.value==='full'}
      const j = await api<Job>(`/courses/${course.value!.id}/units/${unit.value!.id}/prepare?depth=${depth.value}`,{method:'POST'})
      await watchJob(j,context)
    })
  }
  async function send(intent='ask', prompt?:string) {
    if(!course.value || !unit.value || busy.value) return
    const content = prompt || message.value.trim()
    if(!content) return
    error.value = ''
    await guard(async()=>{
      const j = await api<Job>(`/courses/${course.value!.id}/tutor-turns`,{method:'POST',body:JSON.stringify({request_id:requestId(),unit_id:unit.value!.id,message:content,selected_text:selected.value,block_index:selected.value?selectionBlock.value:null,lesson_revision:lesson.value?.revision??0,intent})})
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
      const unitId = unit.value!.id
      const result=await api<{xp_awarded:number}>(`/courses/${course.value!.id}/learning-events`,{method:'POST',body:JSON.stringify({request_id:requestId(),unit_id:unit.value!.id,kind,text,...extras})})
      if (result.xp_awarded && typeof extras.block_index === 'number') {
        clearTimeout(rewardTimeout)
        rewardNotice.value = {unitId, blockIndex: extras.block_index, points: result.xp_awarded}
        rewardTimeout = setTimeout(() => { rewardNotice.value = null }, 1300)
      }
      await refreshCourse(); await refreshPlan()
    })
  }
  async function openSource(id:string) { await guard(async()=>{source.value=await api<Source>(`/documents/${course.value!.document_id}/chunks/${id}`)}) }
  async function cancel() {
    const active = job.value
    if(!active) return
    await guard(async () => {
      const stopped = await api<Job>(`/jobs/${active.id}/cancel`,{method:'POST'})
      if(stopped.status !== 'cancelled' || !['prepare','regenerate'].includes(active.kind) || job.value?.id !== active.id) return
      ++pollVersion
      job.value = stopped
      for (const [key, state] of Object.entries(waiting.value)) {
        if (state.id === active.id) setWait(key)
      }
      localStorage.removeItem('xunzhi.pending')
      stoppedNotice.value = '已停止。下次开始时会接着已保存的部分继续。'
      clearTimeout(stopTimeout)
      stopTimeout = setTimeout(() => {stoppedNotice.value=''}, 2800)
    })
  }
  async function retry() {
    if(!job.value || busy.value) return
    await guard(async()=>{
      const context = JSON.parse(localStorage.getItem('xunzhi.pending')||'{}')
      await watchJob(await api<Job>(`/jobs/${job.value!.id}/retry`,{method:'POST'}),context)
    })
  }
  function selectText() {
    const selection = window.getSelection()
    const text = selection?.toString().trim()
    if (!selection || !selection.rangeCount || !text) return
    const node = selection.getRangeAt(0).startContainer
    const element = node instanceof Element ? node : node.parentElement
    const anchor = element?.closest('[id^="block-"]')
    selectionBlock.value = anchor ? Number(anchor.id.slice(6)) : null
    selected.value = text.slice(0,3000)
  }
  async function revisit(event:LearningEvent) {
    await guard(async () => {
      await loadUnit(event.unit_id)
      const index = event.data.block_index
      const sameRevision = (event.data.lesson_revision ?? 0) === (lesson.value?.revision ?? 0)
      const exact = index != null && sameRevision && !!lesson.value?.blocks[index]
      await savePosition(event.unit_id, exact ? index! : 0)
      view.value = 'learn'
      await nextTick()
      const target = exact ? document.getElementById(`block-${index}`) : null
      if (target) {
        for (let parent = target.parentElement; parent; parent = parent.parentElement) {
          if (parent instanceof HTMLDetailsElement) parent.open = true
        }
        target.scrollIntoView({block:'center'})
        target.setAttribute('tabindex','-1')
        target.focus({preventScroll:true})
      } else {
        locationNotice.value = sameRevision ? '已回到这条记录所在的小节。' : '本节讲义已更新，已回到小节开头。'
        window.scrollTo({top:0})
      }
    })
  }
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
  onUnmounted(()=>{alive=false;clearTimeout(rewardTimeout);clearTimeout(stopTimeout)})
  return {switchDepth,stoppedNotice,reviewWait,enterPrepared,selectionBlock,locationNotice,revisit,reloadRecords:async()=>{await refreshCourse();await refreshPlan()},rewardNotice,depth,regenerate,showExtras,learningUnits,curate,courses,course,unit,lesson,turns,health,error,loading,view,source,selected,message,job,minutes,plan,busy,index,chapters,
          guard,openCourse,selectUnit,bookmark,prepare,send,upload,record,openSource,cancel,retry,selectText,practiceFor,refreshPlan}
}
