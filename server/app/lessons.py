"""Bounded generation across all source batches, with resumable checkpoints."""
from .domain import Lesson, AppError
from .pedagogy import LESSON_TASK, DISPLAY_CAPABILITIES


async def build_lesson(service, job_id, course, unit, depth):
    ids=set(unit['source_ids'])
    sources=[c for c in service.store.chunks(course['document_id']) if c['id'] in ids]
    if not sources:
        raise AppError('本节没有可用原文','SOURCE_UNAVAILABLE')
    selected=sources if depth=='full' else sources[:7]
    draft=service.store.generation(job_id) or {'blocks':[], 'next':0, 'metrics':[]}
    if service.settings.configured:
        batches=[selected[i:i+4] for i in range(0,len(selected),4)]
        for i in range(draft['next'],len(batches)):
            batch=batches[i]
            service.store.update_job(job_id,'running',f'正在准备第 {i+1}/{len(batches)} 部分，已保存内容可继续恢复')
            instruction=LESSON_TASK+(' 完整学习：逐个解释本批原文的重要定义、条件、限制、反例及代码，不能只做摘要。有代码必须保留关键代码并解释，可用 code_trace 标注执行顺序；不得伪称执行过。这里只是本节的一部分，不要每批重复引言和结尾。' if depth=='full' else ' 快速学习：聚焦重点，明确省略范围；关键代码仍应保留。')
            try:
                lesson,metrics=await service.gateway.generate(instruction,{'unit':unit['title'],'part':i+1,'parts':len(batches),'sources':batch,'display_capabilities':DISPLAY_CAPABILITIES},Lesson)
            except AppError as exc:
                if exc.code == 'OUTPUT_INVALID':
                    raise AppError(f"第 {i+1}/{len(batches)} 批：{exc.message}。重试会从本批继续。", exc.code, exc.status) from exc
                raise
            draft['blocks'].extend(lesson['blocks']);draft['metrics'].append(metrics)
            draft['summary']=draft.get('summary',lesson['summary']);draft['next']=i+1
            service.store.save_generation(job_id,draft)
        blocks=draft['blocks']
    else:
        blocks=[]
    # Preserve every supplied character independently of what the model chooses to summarize.
    originals=[{'type':'source','title':f"原文对照 · 文件第 {c['page']+1} 页",'body':c['text'],'source_ids':[c['id']]} for c in selected]
    return {'title':unit['title'],'summary':draft.get('summary','逐段阅读材料原文；配置模型后可以加入讲解。'),
            'blocks':blocks+originals,'status':'ready','mode':'ai' if service.settings.configured else 'extractive',
            'depth':depth,'coverage':{'included':len(selected),'total':len(sources)},'metrics':{'batches':draft['metrics']}}
