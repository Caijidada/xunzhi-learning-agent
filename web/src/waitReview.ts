import { api } from './api'
import type { Course, Lesson } from './types'

export type RecallCard = {
  chapter: string
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
    const related = events.filter(e => e.unit_id === id)
    for (const event of related.filter(e => e.review_note).slice(0, 1)) {
      add({chapter, prompt: event.data.text, answer: '你的复习笔记：' + event.review_note})
    }
    const {lesson} = await api<{lesson:Lesson|null}>(`/courses/${course.id}/units/${id}`)
    if (!lesson || lesson.status === 'generating') continue
    const missed = difficult.find(e => e.unit_id === id && e.data.lesson_revision === (lesson.revision ?? 0))
    const quiz = lesson.blocks[missed?.data.block_index ?? -1]?.type === 'quiz'
      ? lesson.blocks[missed!.data.block_index!] : lesson.blocks.find(b => b.type === 'quiz')
    if (quiz?.options && quiz.answer != null && quiz.options[quiz.answer]) {
      add({chapter, prompt: quiz.body || quiz.title, options: quiz.options, correct: quiz.answer,
        answer: quiz.options[quiz.answer] + (quiz.explanation ? '\n' + quiz.explanation : '')})
    }
    const passage = lesson.blocks.find(b => ['text','callout','source'].includes(b.type) && b.body.trim())
    if (passage) add({chapter, prompt: '你还记得「' + (passage.title || chapter) + '」讲了什么吗？', answer: passage.body})
  }
  return cards
}
