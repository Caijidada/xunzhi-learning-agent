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


def test_curriculum_routes_existing_content_without_losing_progress(client):
    store=client.app.state.store
    with store.connection() as db:
        row=db.execute('SELECT data FROM units WHERE id=?',('demo_unit_1',)).fetchone()
        unit=json.loads(row[0]); unit['title']='致谢'
        db.execute('UPDATE units SET data=? WHERE id=?',(json.dumps(unit),'demo_unit_1'))
    course=client.get('/api/courses/course_demo').json()
    assert course['units'][0]['category']=='skip'
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
    assert calls[0]['response_format']=={'type':'json_object'}
    assert lesson['blocks'][0]['source_ids']==['real-source']


def test_model_auth_error_is_not_leaked(tmp_path):
    gateway=ModelGateway(Settings(tmp_path,api_key='secret-value'),httpx.MockTransport(lambda req:httpx.Response(401,text='secret-value invalid')))
    with pytest.raises(AppError) as exc:
        asyncio.run(gateway.generate('Teach',{'sources':[]},Lesson))
    assert 'secret-value' not in exc.value.message
    assert exc.value.code=='MODEL_AUTH'


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
