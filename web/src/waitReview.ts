import { api } from './api'
import type { Course, Lesson, Block } from './types'

export type RecallCard = {
  chapter: string
  blocks: Block[]
  blockIndex: number
  prompt: string
  answer: string
  options?: string[]
  correct?: number
}

function visitsKey(courseId: string) { return 'xunzhi.read-units.' + courseId }

function visited(courseId: string): string[] {
  return JSON.parse(localStorage.getItem(visitsKey(courseId)) || '[]')
}

export function rememberReading(courseId: string, unitId: string) {
  const ids = visited(courseId).filter(id => id !== unitId)
  localStorage.setItem(visitsKey(courseId), JSON.stringify([unitId, ...ids].slice(0, 30)))
}

export async function recallCards(course: Course, targetId: string): Promise<RecallCard[]> {
  const events = course.events
  const difficult = events.filter(e => e.review_status === 'pending' || (e.kind === 'practice' && e.data.correct === false && e.review_status !== 'resolved'))
  const ids = [...new Set([...difficult.map(e => e.unit_id), ...visited(course.id), ...events.map(e => e.unit_id)])]
  const cards: RecallCard[] = []
  const seen = new Set<string>()
  function add(card: RecallCard) {
    if (!seen.has(card.prompt) && card.answer) { cards.push(card); seen.add(card.prompt) }
  }
  for (const id of ids.filter(id => id !== targetId).slice(0, 4)) {
    const unit = course.units.find(u => u.id === id)
    if (!unit) continue
    const chapter = unit.title
    const {lesson} = await api<{lesson:Lesson|null}>(`/courses/${course.id}/units/${id}`)
    if (!lesson || lesson.status === 'generating') continue
    const blocks = lesson.blocks
    const missed = difficult.find(e => e.unit_id === id && e.data.lesson_revision === (lesson.revision ?? 0))
    const ordered = blocks.map((block, blockIndex) => ({block, blockIndex}))
    ordered.sort((a,b) => Number(b.blockIndex === missed?.data.block_index) - Number(a.blockIndex === missed?.data.block_index)
      || Number(b.block.type === 'quiz') - Number(a.block.type === 'quiz'))
    const before = cards.length
    const note = events.find(e => e.unit_id === id && e.review_note?.trim() && usableQuestion(e.data.text)
      && e.data.block_index != null && (e.data.lesson_revision ?? 0) === (lesson.revision ?? 0)
      && blocks[e.data.block_index] && !isOverview(blocks[e.data.block_index]))
    if (note) add({chapter, blocks, blockIndex:note.data.block_index!, prompt:note.data.text,
      answer:'你的复习笔记：' + note.review_note})
    for (const {block, blockIndex} of ordered) {
      if (isOverview(block)) continue
      const origin = {chapter, blocks, blockIndex}
      if (block.type === 'quiz' && usableQuestion(block.body) && block.options && block.answer != null && block.options[block.answer]) {
        add({...origin, prompt:block.body, options:block.options, correct:block.answer,
          answer:[block.options[block.answer],block.explanation].filter(Boolean).join('\n')})
      } else if (block.recall && usableQuestion(block.recall.question)) {
        add({...origin, prompt:block.recall.question, answer:block.recall.answer})
      } else if (['text','callout'].includes(block.type)) {
        const pair = fromPassage(block.body, chapter)
        if (pair) add({...origin, ...pair})
      }
      if (cards.length - before >= 3) break
    }
  }
  return cards
}

function isOverview(block: Block) {
  return /覆盖范围|阅读指南|章节导读|目录导航/.test(block.title)
    || /(?:本批|本节|本章)(?:次)?(?:是.{0,16}的前半部分|覆盖|将介绍|主要介绍|包含以下|不含)|原文将其留给后续章节/.test(block.body)
}

function usableQuestion(question: string) {
  return question.trim().length >= 12 && !/讲了什么|还记得.{0,30}吗|^以下哪项正确[。？]?$/u.test(question)
}

// Older lessons have no authored recall pair. Only split an explicit relation in the text.
function fromPassage(body: string, chapter: string) {
  for (const raw of body.split(/\n+/)) {
    const line = raw.replace(/\*\*/g,'').trim()
    const condition = line.match(/^(如果|当|若)(.{4,80}?)[，,](.{8,260})$/)
    if (condition) return {prompt:`在「${chapter}」中，${condition[1]}${condition[2]}，接下来会发生什么？`, answer:line}
    const definition = line.match(/^([\p{L}\d][\p{L}\d ()（）_-]{0,30})[：:](.{8,350})$/u)
    if (definition && !/示例|小结|提示|范围|总结|注意|结论|步骤|本节|本批|^例如$/.test(definition[1])) {
      return {prompt:`在「${chapter}」的语境中，怎样向别人解释「${definition[1]}」？请说出它的含义，并用本节的细节说明。`, answer:line}
    }
  }
}
