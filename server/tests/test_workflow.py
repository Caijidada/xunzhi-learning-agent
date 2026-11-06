import asyncio
import io
import json
import time
from pathlib import Path
import httpx
import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
from server.app.config import Settings
from server.app.main import create_app
from server.app.domain import Lesson, AppError
from server.app.provider import ModelGateway


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(Settings(tmp_path))) as c:
        yield c


def wait_job(c, job_id):
    for _ in range(300):
        job = c.get(f"/api/jobs/{job_id}").json()
        if job["status"] not in ("running", "queued"):
            return job
        time.sleep(.01)
    raise AssertionError("job timed out")


def make_pdf():
    writer = PdfWriter()
    for text in ["Chapter One: Tools. A tool executes an action. The result returns to context.", "Chapter Two: Memory. Progress is different from mastery. Store user decisions."]:
        page = writer.add_blank_page(width=500, height=700)
        font = DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
        content = DecodedStreamObject()
        content.set_data(f"BT /F1 12 Tf 30 600 Td ({text}) Tj ET".encode())
        page[NameObject('/Contents')] = writer._add_object(content)
    writer.add_outline_item("Tools", 0)
    writer.add_outline_item("Memory", 1)
    output=io.BytesIO(); writer.write(output)
    return output.getvalue()


def test_progress_is_manual_versioned_and_idempotent(client):
    body={"request_id":"navigation-001","unit_id":"demo_unit_2","expected_version":0,"block_index":0}
    first=client.patch('/api/courses/course_demo/progress',json=body)
    assert first.status_code==200 and first.json()['version']==1
    assert client.patch('/api/courses/course_demo/progress',json=body).json()==first.json()
    body['unit_id']='demo_unit_3'
    assert client.patch('/api/courses/course_demo/progress',json=body).status_code==409
    body['request_id']='navigation-002'
    assert client.patch('/api/courses/course_demo/progress',json=body).status_code==409


def test_tutor_does_not_advance_and_records_confusion(client):
    req={"request_id":"tutor-request-1","unit_id":"demo_unit_1","message":"为什么还需要一次调用？","intent":"confused"}
    job=client.post('/api/courses/course_demo/tutor-turns',json=req).json()
    result=wait_job(client,job['id'])
    assert result['status']=='completed'
    assert result['result']['mode']=='demo'
    assert result['result']['response']['action']=='step_diagram'
    course=client.get('/api/courses/course_demo').json()
    assert course['progress']['unit_id']=='demo_unit_1'
    assert course['progress']['version']==0
    assert course['events'][0]['kind']=='confused'
    assert client.post('/api/courses/course_demo/tutor-turns',json=req).json()['id']==job['id']
    req['message']='a different request'
    assert client.post('/api/courses/course_demo/tutor-turns',json=req).status_code==409


def test_memory_correction_replaces_effective_record(client):
    original=client.post('/api/courses/course_demo/learning-events',json={"request_id":"event-confused-1","unit_id":"demo_unit_1","kind":"confused","text":"我不理解工具结果"}).json()
    result=client.post('/api/courses/course_demo/learning-events',json={"request_id":"event-correction-1","unit_id":"demo_unit_1","kind":"correction","text":"现在我理解了工具结果如何传回","target_id":original['id']})
    assert result.status_code==200
    events=client.get('/api/courses/course_demo/resume').json()['events']
    assert len(events)==1 and events[0]['kind']=='correction'
    plan=client.get('/api/courses/course_demo/session-plan').json()
    assert all(t['title']!='回到上次的疑问' for t in plan['tasks'])


def test_practice_is_graded_on_server(client):
    req={"request_id":"quiz-attempt-01","unit_id":"demo_unit_1","kind":"practice","block_index":4,"choice":0,"correct":True,"used_hint":True}
    result=client.post('/api/courses/course_demo/learning-events',json=req)
    assert result.status_code==200
    assert result.json()['data']['correct'] is False
    assert result.json()['data']['used_hint'] is True
    assert client.get('/api/courses/course_demo/resume').json()['progress']['version']==0


def test_pdf_import_citations_and_lazy_preparation(client):
    uploaded=client.post('/api/documents',files={'file':('tiny.pdf',make_pdf(),'application/pdf')})
    assert uploaded.status_code==202
    result=wait_job(client,uploaded.json()['id'])
    assert result['status']=='completed',result
    course_id=result['result']['course_id']
    course=client.get(f'/api/courses/{course_id}').json()
    assert len(course['units'])==2
    assert not any(u['ready'] for u in course['units'])
    unit=course['units'][0]
    job=client.post(f'/api/courses/{course_id}/units/{unit["id"]}/prepare').json()
    assert wait_job(client,job['id'])['status']=='completed'
    lesson=client.get(f'/api/courses/{course_id}/units/{unit["id"]}').json()['lesson']
    assert lesson['mode']=='extractive'
    assert 'pending_blocks' not in lesson
    source_id=lesson['blocks'][0]['source_ids'][0]
    source=client.get(f'/api/documents/{course["document_id"]}/chunks/{source_id}').json()
    assert source['page']==0 and 'Tools' in source['text']
    assert client.get(f'/api/documents/document_demo/chunks/{source_id}').status_code==404
    assert sum(u['ready'] for u in client.get(f'/api/courses/{course_id}').json()['units'])==1


def test_invalid_upload_rejected(client):
    assert client.post('/api/documents',files={'file':('x.pdf',b'not a pdf','application/pdf')}).status_code==400


def test_quiz_experience_is_awarded_once_per_question(client):
    body={'request_id':'reward-answer-001','unit_id':'demo_unit_1','kind':'practice','block_index':4,'choice':1}
    first=client.post('/api/courses/course_demo/learning-events',json=body)
    assert first.json()['xp_awarded']==1
    assert client.post('/api/courses/course_demo/learning-events',json=body).json()['xp_awarded']==0
    body['request_id']='reward-answer-002'
    assert client.post('/api/courses/course_demo/learning-events',json=body).json()['xp_awarded']==0
    rewards=client.get('/api/courses/course_demo').json()['rewards']
    assert rewards['xp']==1 and rewards['level']==1
    assert len(rewards['levels'])==3


def test_curriculum_routes_existing_content_without_losing_progress(client):
    store=client.app.state.store
    with store.connection() as db:
        row=db.execute('SELECT data FROM units WHERE id=?',('demo_unit_1',)).fetchone()
        unit=json.loads(row[0]); unit['title']='致谢'
        db.execute('UPDATE units SET data=? WHERE id=?',(json.dumps(unit),'demo_unit_1'))
    course=client.get('/api/courses/course_demo').json()
    assert course['units'][0]['category']=='skip'
    assert client.get('/api/courses/course_demo/units/demo_unit_1').json()['unit']['category']=='skip'
    assert course['progress']['unit_id']=='demo_unit_1'
    assert client.get('/api/courses/course_demo/units/demo_unit_1').json()['lesson']
    course_data=store.get('courses','course_demo')
    course_data['curriculum']={'demo_unit_1':{'category':'learn','reason':'原文包含核心知识'}}
    store.put('courses','course_demo',course_data)
    assert client.get('/api/courses/course_demo').json()['units'][0]['category']=='learn'


def test_event_request_id_cannot_overwrite_memory(client):
    req={'request_id':'memory-dedup-01','unit_id':'demo_unit_1','kind':'note','text':'first'}
    first=client.post('/api/courses/course_demo/learning-events',json=req)
    assert first.status_code==200
    assert client.post('/api/courses/course_demo/learning-events',json=req).json()==first.json()
    req['text']='different'
    assert client.post('/api/courses/course_demo/learning-events',json=req).status_code==409


def test_cancelled_generation_does_not_publish_or_advance(tmp_path):
    class SlowGateway:
        async def generate(self,*args):
            await asyncio.sleep(30)
            raise AssertionError('cancelled work must not reach here')
    with TestClient(create_app(Settings(tmp_path,api_key='test-only'),SlowGateway())) as c:
        job=c.post('/api/courses/course_demo/tutor-turns',json={'request_id':'cancel-turn-001','unit_id':'demo_unit_1','message':'explain'}).json()
        assert c.post('/api/jobs/'+job['id']+'/cancel').json()['status']=='cancelled'
        assert c.get('/api/courses/course_demo/units/demo_unit_1').json()['turns']==[]
        assert c.get('/api/courses/course_demo/resume').json()['progress']['version']==0


def test_resume_survives_process_recreation(tmp_path):
    settings=Settings(tmp_path)
    with TestClient(create_app(settings)) as c:
        c.patch('/api/courses/course_demo/progress',json={"request_id":"persist-progress-1","unit_id":"demo_unit_3","block_index":1,"expected_version":0})
    with TestClient(create_app(settings)) as c:
        progress=c.get('/api/courses/course_demo/resume').json()['progress']
        assert progress['unit_id']=='demo_unit_3' and progress['block_index']==1


def test_interrupted_job_can_resume_saved_blocks(tmp_path):
    settings=Settings(tmp_path)
    app=create_app(settings)
    with TestClient(app) as c:
        store=app.state.store
        lesson=store.lesson('demo_unit_1')
        lesson['pending_blocks']=lesson['blocks'][2:]
        lesson['blocks']=lesson['blocks'][:2]
        lesson['status']='generating'
        store.save_lesson('demo_unit_1',lesson)
        job=store.new_job('restart-case','prepare',{'course_id':'course_demo','unit_id':'demo_unit_1'})
        store.update_job(job['id'],'running')
    with TestClient(create_app(settings)) as c:
        assert c.get('/api/jobs/'+job['id']).json()['status']=='interrupted'
        c.post('/api/jobs/'+job['id']+'/retry')
        assert wait_job(c,job['id'])['status']=='completed'
        lesson=c.get('/api/courses/course_demo/units/demo_unit_1').json()['lesson']
        assert len(lesson['blocks'])==5


def test_deepseek_output_validated_with_bounded_repair(tmp_path):
    calls=[]
    def handle(request):
        calls.append(json.loads(request.content))
        source='wrong-id' if len(calls)==1 else 'real-source'
        body={'title':'A lesson','summary':'A summary','blocks':[{'type':'text','body':'Grounded content','source_ids':[source]}]}
        return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps(body)}}],'usage':{'total_tokens':10}})
    gateway=ModelGateway(Settings(tmp_path,api_key='test-not-real'),httpx.MockTransport(handle))
    lesson,metrics=asyncio.run(gateway.generate('Teach',{'sources':[{'id':'real-source','text':'Source text'}]},Lesson))
    assert len(calls)==2 and metrics['calls']==2 and metrics['usage']['total_tokens']==20
    assert '第 1 个内容块引用了本批材料以外的来源 ID' in calls[1]['messages'][-1]['content']
    assert calls[0]['response_format']=={'type':'json_object'}
    assert lesson['blocks'][0]['source_ids']==['real-source']


def test_model_auth_error_is_not_leaked(tmp_path):
    gateway=ModelGateway(Settings(tmp_path,api_key='secret-value'),httpx.MockTransport(lambda req:httpx.Response(401,text='secret-value invalid')))
    with pytest.raises(AppError) as exc:
        asyncio.run(gateway.generate('Teach',{'sources':[]},Lesson))
    assert 'secret-value' not in exc.value.message
    assert exc.value.code=='MODEL_AUTH'


def test_legacy_step_cards_are_repaired_in_new_generation(tmp_path):
    calls=[]
    def handle(request):
        calls.append(request)
        block={'type':'diagram','source_ids':['s'],'steps':[{'label':'A','detail':'a'},{'label':'B','detail':'b'}]} if len(calls)==1 else {'type':'text','body':'用对照解释即可','source_ids':['s']}
        return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps({'title':'解释','summary':'说明','blocks':[block]})}}]})
    gateway=ModelGateway(Settings(tmp_path,api_key='test'),httpx.MockTransport(handle))
    result,_=asyncio.run(gateway.generate('解释',{'sources':[{'id':'s','text':'source'}]},Lesson))
    assert len(calls)==2 and result['blocks'][0]['type']=='text'


def test_code_trace_cannot_reference_missing_lines():
    from server.app.domain import Block
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Block(type='code',body='print(1)',code_trace=[{'line_start':1,'line_end':2,'explanation':'错误行范围'}])


def test_tutor_can_choose_nonvisual_method_and_retain_feedback(tmp_path):
    contexts=[]
    def handle(request):
        context=json.loads(json.loads(request.content)['messages'][1]['content'])['context']
        contexts.append(context)
        approach='日常类比并说明局限' if len(contexts)==1 else '正反例对照'
        body={'action':'reexplain','reason':'针对当前问题选择说明方式',
              'teaching':{'goal':'区分工具和工具处理的对象','approach':approach,'success_signal':'能解释一个新例子中的区别'},
              'blocks':[{'type':'text','body':'先区分执行操作的工具与被操作的数据。','source_ids':[context['sources'][0]['id']]}]}
        return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps(body)}}]})
    settings=Settings(tmp_path,api_key='test-only')
    gateway=ModelGateway(settings,httpx.MockTransport(handle))
    with TestClient(create_app(settings,gateway)) as c:
        for request_id,message,intent in [('teaching-turn-01','也可以用图说明','diagram'),('teaching-turn-02','这个类比我还是不懂','confused')]:
            job=c.post('/api/courses/course_demo/tutor-turns',json={'request_id':request_id,'unit_id':'demo_unit_1','message':message,'intent':intent}).json()
            assert wait_job(c,job['id'])['status']=='completed'
        turns=c.get('/api/courses/course_demo/units/demo_unit_1').json()['turns']
        assert [t['data']['response']['teaching']['approach'] for t in turns]==['日常类比并说明局限','正反例对照']
        assert all(t['data']['response']['blocks'][0]['type']=='text' for t in turns)
        assert contexts[1]['history'][0]['response']['teaching']['approach']=='日常类比并说明局限'
        assert contexts[1]['current_explanation']
        assert c.get('/api/courses/course_demo/resume').json()['progress']['version']==0


def test_regeneration_archives_content_and_rejects_stale_practice(tmp_path):
    class Gateway:
        calls=0
        async def generate(self,*args):
            self.calls+=1
            return {'title':'新讲解','summary':'换个角度','blocks':[{'type':'text','body':'新内容','source_ids':['demo_source_1']}]}, {}
    gateway=Gateway()
    with TestClient(create_app(Settings(tmp_path,api_key='test-only'),gateway)) as c:
        path='/api/courses/course_demo/units/demo_unit_1'
        old=c.get(path).json()['lesson']
        req={'request_id':'regenerate-test-01','expected_revision':0}
        job=c.post(path+'/regenerate',json=req).json()
        assert wait_job(c,job['id'])['status']=='completed'
        assert c.get(path).json()['lesson']['revision']==1
        assert c.get(path+'/versions').json()[0]==old
        repeated=c.post(path+'/regenerate',json=req).json()
        assert repeated['id']==job['id'] and gateway.calls==1
        assert c.get('/api/courses/course_demo/resume').json()['progress']['unit_id']=='demo_unit_1'
        stale=c.post('/api/courses/course_demo/learning-events',json={'request_id':'stale-practice-01','unit_id':'demo_unit_1','kind':'practice','block_index':0,'choice':0,'lesson_revision':0})
        assert stale.status_code==409


def test_regeneration_failure_preserves_original(tmp_path):
    class Gateway:
        async def generate(self,*args):
            raise AppError('模型不可用','MODEL_UNAVAILABLE',503)
    with TestClient(create_app(Settings(tmp_path,api_key='test-only'),Gateway())) as c:
        path='/api/courses/course_demo/units/demo_unit_1'
        old=c.get(path).json()['lesson']
        job=c.post(path+'/regenerate',json={'request_id':'regenerate-fail-01','expected_revision':0}).json()
        assert wait_job(c,job['id'])['status']=='failed'
        assert c.get(path).json()['lesson']==old


def test_scene_references_and_bounds_are_validated():
    from server.app.domain import Block
    from pydantic import ValidationError
    scene={'goal':'观察输入如何改变输出','nodes':[{'id':'a','label':'输入','x':40,'y':100},{'id':'b','label':'输出','x':500,'y':100}],
           'edges':[{'id':'e','source':'a','target':'b'}], 'scenarios':[{'label':'输入改变','frames':[
               {'caption':'输入尚未提交','states':[{'node_id':'b','text':'等待'}]},
               {'caption':'输入传递后得到结果','active_edges':['e'],'states':[{'node_id':'b','text':'结果出现'}]}]}]}
    block=Block(type='scene',body='示意',source_ids=['source'],scene=scene)
    assert block.scene.scenarios[0].frames[1].states[0].text=='结果出现'
    scene['edges'][0]['target']='missing'
    with pytest.raises(ValidationError): Block(type='scene',scene=scene)

    scene['edges'][0]['target']='b'
    scene['nodes'][0]['x']=1000
    with pytest.raises(ValidationError): Block(type='scene',scene=scene)


def test_full_lesson_batches_resume_and_preserve_all_source_code(tmp_path):
    class Gateway:
        seen=[]
        fail=True
        async def generate(self,instruction,context,schema):
            self.seen.append(context['sources'][0]['id'])
            if len(self.seen)==2 and self.fail:
                self.fail=False
                raise AppError('retry','MODEL_UNAVAILABLE')
            return {'title':'完整','summary':'讲解','blocks':[{'type':'text','body':'说明','source_ids':[context['sources'][0]['id']]}]},{}
    g=Gateway();app=create_app(Settings(tmp_path,api_key='test'),g)
    with TestClient(app) as c:
        store=app.state.store
        chunks=[{'id':f's{i}','title':'code','page':i,'text':f'def f{i}():\n    return {i}'} for i in range(11)]
        store.add_chunks('document_demo',chunks)
        with store.connection() as db:
            u=store.unit('course_demo','demo_unit_1');u['source_ids']=[x['id'] for x in chunks]
            db.execute('UPDATE units SET data=? WHERE id=?',(json.dumps(u),'demo_unit_1'))
        url='/api/courses/course_demo/units/demo_unit_1'
        job=c.post(url+'/regenerate',json={'request_id':'full-batches-001','expected_revision':0,'depth':'full'}).json()
        assert wait_job(c,job['id'])['status']=='failed'
        c.post('/api/jobs/'+job['id']+'/retry')
        assert wait_job(c,job['id'])['status']=='completed'
        lesson=c.get(url).json()['lesson']
        assert lesson['coverage']=={'included':11,'total':11}
        assert [b['body'] for b in lesson['blocks'] if b['type']=='source']==[x['text'] for x in chunks]
        assert g.seen==['s0','s4','s4','s8']


def test_curriculum_model_cannot_invent_unit_ids(tmp_path):
    from server.app.domain import CurriculumReview
    def handle(request):
        return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps({'choices':[{'unit_id':'invented','category':'skip','reason':'wrong'}]})}}]})
    gateway=ModelGateway(Settings(tmp_path,api_key='test-only'),httpx.MockTransport(handle))
    with pytest.raises(AppError) as error:
        asyncio.run(gateway.generate('审阅',{'units':[{'unit_id':'real','title':'正文'}]},CurriculumReview))
    assert error.value.code=='OUTPUT_INVALID'


def test_review_keeps_question_location_and_original_exchange(client):
    base = '/api/courses/course_demo'
    question = {'request_id':'review-question-1','unit_id':'demo_unit_1','message':'这里做了什么？',
                'selected_text':'当前片段','block_index':1,'lesson_revision':0}
    job = client.post(base+'/tutor-turns', json=question).json()
    assert wait_job(client, job['id'])['status'] == 'completed'
    event = client.get(base).json()['events'][0]
    assert event['kind'] == 'question' and event['data']['block_index'] == 1
    turn = client.get(base+'/tutor-turns/'+event['data']['turn_id']).json()
    assert turn['data']['selected_text'] == '当前片段' and turn['data']['response']['blocks']
    url = base+'/learning-events/'+event['id']+'/review'
    for status in ('pending','resolved'):
        assert client.put(url,json={'status':status,'note':'我的解释'}).status_code == 200
        latest = client.get(base).json()['events'][0]
        assert latest['data'] == event['data'] and latest['review_status'] == status
        tasks = client.get(base+'/session-plan').json()['tasks']
        assert any(t['title']=='回到上次的疑问' for t in tasks) == (status=='pending')


def test_start_button_resumes_cancelled_prepare(client):
    store = client.app.state.store
    payload = {'course_id':'course_demo','unit_id':'demo_unit_1','depth':'full'}
    job = store.new_job('prepare:course_demo:demo_unit_1:extractive:full','prepare',payload)
    store.update_job(job['id'],'cancelled')
    resumed = client.post('/api/courses/course_demo/units/demo_unit_1/prepare?depth=full').json()
    assert resumed['id'] == job['id']
    assert wait_job(client, resumed['id'])['status'] == 'completed'


def test_switch_depth_reuses_revisions_and_bookmarks(client):
    store = client.app.state.store
    base = '/api/courses/course_demo/units/demo_unit_1'
    quick = store.lesson('demo_unit_1')
    quick['depth'] = 'quick'
    store.save_lesson('demo_unit_1', quick)
    assert client.post(base+'/activate?depth=full&revision=0').json()['lesson'] is None
    with store.connection() as db:
        db.execute("UPDATE progress SET block_index=2 WHERE course_id='course_demo'")
    full = {**quick, 'depth':'full'}
    store.replace_lesson('course_demo','demo_unit_1', full, 0)
    for _ in range(2):
        assert client.post(base+'/activate?depth=quick&revision=1').json()['lesson']['depth'] == 'quick'
        assert store.progress('course_demo')['block_index'] == 2
        assert client.post(base+'/activate?depth=full&revision=0').json()['lesson']['revision'] == 1
        assert store.progress('course_demo')['block_index'] == 0
    client.post(base+'/activate?depth=quick&revision=1')
    store.replace_lesson('course_demo','demo_unit_1', dict(quick), 0)
    assert store.lesson('demo_unit_1')['revision'] == 2
    assert client.post(base+'/activate?depth=full&revision=0').status_code == 409


def test_truncated_lesson_reports_batch(tmp_path):
    attempts = []
    def respond(request):
        attempts.append(request)
        return httpx.Response(200,json={'choices':[{'finish_reason':'length','message':{'content':'{'}}]})
    settings = Settings(tmp_path,api_key='test')
    app = create_app(settings,ModelGateway(settings,httpx.MockTransport(respond)))
    with TestClient(app) as c:
        url='/api/courses/course_demo/units/demo_unit_1/regenerate'
        job=c.post(url,json={'request_id':'truncated-lesson-01','expected_revision':0}).json()
        failure=wait_job(c,job['id'])['error']
        assert failure['code']=='OUTPUT_INVALID' and len(attempts)==2
        assert '第 1/1 批' in failure['message'] and '输出长度上限' in failure['message']
