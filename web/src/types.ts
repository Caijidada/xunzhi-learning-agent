export type Scene = {
  goal:string; nodes:{id:string;label:string;x:number;y:number}[];
  groups:{label:string;x:number;y:number;width:number;height:number}[];
  edges:{id:string;source:string;target:string;label:string}[];
  scenarios:{label:string;frames:{caption:string;active_nodes:string[];active_edges:string[];states:{node_id:string;text:string;x?:number|null;y?:number|null}[]}[]}[]
}
export type Step = { label: string; detail: string }
export type Block = { recall?:{question:string;answer:string}|null; code_trace?:{line_start:number;line_end:number;explanation:string;variables:string}[]; scene?:Scene; type: 'text'|'callout'|'diagram'|'quiz'|'code'|'scene'|'source'; title: string; body: string; source_ids: string[]; steps?: Step[]; options?: string[]; answer?: number; explanation?: string }
export type Lesson = { depth?:string; coverage?:{included:number;total:number}; revision?: number; title: string; summary: string; blocks: Block[]; mode: 'demo'|'extractive'|'ai'; status?: string }
export type Unit = { category?: 'learn'|'guide'|'skip'; reason?: string; id: string; title: string; chapter: number; chapter_title: string; source_ids: string[]; ready: boolean; minutes: number; page_start: number; page_end: number }
export type Progress = { course_id: string; unit_id: string; block_index: number; version: number; updated: number }
export type ReviewStatus = "pending" | "resolved"
export type LearningEvent = { request_id?:string; review_status?:ReviewStatus|null; review_note?:string|null; id: string; unit_id: string; kind: string; created: number; data: { text: string; chosen_answer?:string; selected_text?:string; turn_id?:string; correct?: boolean; choice?: number; block_index?: number; lesson_revision?: number; used_hint?: boolean; strategy?: string; target_id?: string } }
export type Course = { rewards?:{xp:number;level:number;title:string;levels:{level:number;title:string;required_xp:number}[]}; id: string; title: string; description: string; document_id: string; demo: boolean; units: Unit[]; progress: Progress; events: LearningEvent[]; document: { title: string; pages: number; missing_pages: number[]; warnings: string[] } }
export type CourseItem = Pick<Course,'id'|'title'|'description'|'demo'|'document_id'|'progress'> & { units_count: number }
export type Turn = { id: string; data: { message: string; selected_text: string; mode: string; response: { action: string; reason: string; blocks: Block[] } } }
export type Job = { id: string; kind: string; status: string; message: string; result?: {course_id?: string; unit_id?: string}; error?: {message: string; code: string} }
export type Source = { id: string; text: string; page: number; title: string }
