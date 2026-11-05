from contextlib import asynccontextmanager
from pathlib import Path
import hashlib
import time
from fastapi import FastAPI, UploadFile, File, Query
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from .config import Settings, ROOT
from .store import Store, uid
from .service import LearningService
from .demo import seed_demo
from .domain import AppError, TurnRequest, ProgressRequest, EventRequest, RegenerateRequest


def create_app(settings=None, gateway=None):
    settings = settings or Settings.load()
    store = Store(settings.data_dir)
    service = LearningService(settings, store, gateway)

    @asynccontextmanager
    async def lifespan(app):
        store.interrupt_running()
        seed_demo(store)
        yield
        await service.close()

    app = FastAPI(title="循知 Learning API", version="0.1.0", lifespan=lifespan)
    app.state.store, app.state.service = store, service

    @app.exception_handler(AppError)
    async def handle_error(request, exc):
        return JSONResponse(status_code=exc.status, content={"error": {"code": exc.code, "message": exc.message}})

    @app.get("/api/health")
    def health():
        return {"ok": True, "model_configured": settings.configured, "model": settings.model,
                "provider": "DeepSeek" if "deepseek" in settings.base_url else "兼容接口"}

    @app.get("/api/courses")
    def courses():
        return [{**c, "units_count": len(store.units(c["id"])), "progress": store.progress(c["id"])} for c in store.all("courses")]

    @app.get("/api/courses/{course_id}")
    def course(course_id: str):
        return service.course(course_id)

    @app.get("/api/courses/{course_id}/units/{unit_id}")
    def lesson(course_id: str, unit_id: str):
        unit = store.unit(course_id, unit_id)
        data = store.lesson(unit_id)
        if data:
            data = {k: v for k, v in data.items() if k != "pending_blocks"}
        return {"unit": unit, "lesson": data, "turns": store.turns(course_id, unit_id)}

    @app.post("/api/courses/{course_id}/units/{unit_id}/prepare", status_code=202)
    async def prepare(course_id: str, unit_id: str):
        store.unit(course_id, unit_id)
        mode = settings.model if settings.configured else "extractive"
        return service.submit(f"prepare:{course_id}:{unit_id}:{mode}", "prepare", {"course_id": course_id, "unit_id": unit_id})

    @app.post("/api/courses/{course_id}/tutor-turns", status_code=202)
    async def tutor(course_id: str, req: TurnRequest):
        store.unit(course_id, req.unit_id)
        return service.submit(f"turn:{course_id}:{req.request_id}", "tutor", {"course_id": course_id, "request": req.model_dump()})

    @app.post('/api/courses/{course_id}/units/{unit_id}/regenerate', status_code=202)
    async def regenerate(course_id: str, unit_id: str, req: RegenerateRequest):
        store.unit(course_id, unit_id)
        if not settings.configured:
            raise AppError('请先配置模型', 'MODEL_NOT_CONFIGURED', 503)
        return service.submit(f'regenerate:{course_id}:{unit_id}:{req.request_id}', 'regenerate',
                              {'course_id': course_id, 'unit_id': unit_id, 'expected_revision': req.expected_revision})

    @app.get('/api/courses/{course_id}/units/{unit_id}/versions')
    def versions(course_id: str, unit_id: str):
        store.unit(course_id, unit_id)
        return store.lesson_versions(unit_id)

    @app.post('/api/courses/{course_id}/curriculum', status_code=202)
    async def curriculum(course_id: str):
        store.get('courses', course_id)
        if not settings.configured:
            raise AppError('请先配置模型，再结合原文优化学习路径', 'MODEL_NOT_CONFIGURED', 503)
        return service.submit(f'curriculum:{course_id}:v1', 'curriculum', {'course_id': course_id})

    @app.patch("/api/courses/{course_id}/progress")
    def progress(course_id: str, req: ProgressRequest):
        return store.move(course_id, req)

    @app.get("/api/courses/{course_id}/resume")
    def resume(course_id: str):
        return {"progress": store.progress(course_id), "events": store.events(course_id)}

    @app.get("/api/courses/{course_id}/session-plan")
    def plan(course_id: str, minutes: int = Query(default=15, ge=5, le=90)):
        return service.plan(course_id, minutes)

    @app.post("/api/courses/{course_id}/learning-events")
    def event(course_id: str, req: EventRequest):
        data = {"text": req.text, "used_hint": req.used_hint}
        if req.kind == "correction" and not req.target_id:
            raise AppError("更正需要指定原记录")
        if req.kind == "practice":
            lesson = store.lesson(req.unit_id)
            if lesson and lesson.get('revision', 0) != req.lesson_revision:
                raise AppError('练习内容已更新，请刷新后再回答', 'VERSION_CONFLICT', 409)
            if not lesson or req.block_index is None or req.block_index >= len(lesson["blocks"]):
                raise AppError("练习不存在")
            block = lesson["blocks"][req.block_index]
            if block["type"] != "quiz" or req.choice is None or not 0 <= req.choice < len(block["options"]):
                raise AppError("练习提交无效")
            data.update({"lesson_revision": req.lesson_revision, "correct": req.choice == block["answer"], "choice": req.choice, "block_index": req.block_index,
                         "text": req.text or block["body"]})
        event_id = store.add_event(course_id, req.unit_id, req.kind, data, f"{course_id}:{req.request_id}", req.target_id)
        return {"id": event_id, "data": data}

    @app.post("/api/documents", status_code=202)
    async def upload(file: UploadFile = File(...)):
        document_id, course_id = uid("doc"), uid("course")
        directory = settings.data_dir / "documents"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{document_id}.pdf"
        size, digest = 0, hashlib.sha256()
        try:
            with path.open("wb") as output:
                while chunk := await file.read(1024 * 1024):
                    if size == 0 and not chunk.startswith(b"%PDF-"):
                        raise AppError("请上传有效的 PDF 文件", "PDF_INVALID")
                    size += len(chunk)
                    if size > 50 * 1024 * 1024:
                        raise AppError("文件不能超过 50 MB", "PDF_TOO_LARGE", 413)
                    digest.update(chunk)
                    output.write(chunk)
            if size == 0:
                raise AppError("文件为空", "PDF_INVALID")
        except Exception:
            path.unlink(missing_ok=True)
            raise
        finally:
            await file.close()
        store.put("documents", document_id, {"id": document_id, "title": Path(file.filename or "学习材料.pdf").stem,
            "filename": Path(file.filename or "学习材料.pdf").name, "path": str(path), "hash": digest.hexdigest(),
            "status": "processing", "created": time.time(), "demo": False})
        return service.submit(f"import:{document_id}", "import", {"document_id": document_id, "course_id": course_id})

    @app.get("/api/documents/{document_id}/chunks/{chunk_id}")
    def source(document_id: str, chunk_id: str):
        return store.chunk(chunk_id, document_id)

    @app.get("/api/documents/{document_id}/file")
    def source_file(document_id: str):
        doc = store.get("documents", document_id)
        if not doc.get("path"):
            raise AppError("内置示例没有 PDF 文件", "NOT_FOUND", 404)
        return FileResponse(doc["path"], media_type="application/pdf", content_disposition_type="inline", filename=doc["filename"])

    @app.get("/api/jobs/{job_id}")
    def job(job_id: str):
        return service.public_job(store.job(job_id))

    @app.post("/api/jobs/{job_id}/retry", status_code=202)
    async def retry(job_id: str):
        return service.retry(job_id)

    @app.post("/api/jobs/{job_id}/cancel")
    async def cancel(job_id: str):
        await service.cancel(job_id)
        return service.public_job(store.job(job_id))

    dist = ROOT / "web" / "dist"
    if dist.exists():
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
    return app


app = create_app()
