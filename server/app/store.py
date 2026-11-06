"""SQLite repositories. Each mutation owns its transaction, including progress events."""
import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from .domain import AppError


def uid(prefix="id"):
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def encode(value):
    return json.dumps(value, ensure_ascii=False)


class Store:
    def __init__(self, directory: Path):
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / "study.sqlite3"
        with self.connection() as db:
            db.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS chunks(id TEXT PRIMARY KEY, document_id TEXT NOT NULL, page INTEGER NOT NULL, title TEXT NOT NULL, text TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS chunk_document ON chunks(document_id,page);
            CREATE TABLE IF NOT EXISTS courses(id TEXT PRIMARY KEY, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS units(id TEXT PRIMARY KEY, course_id TEXT NOT NULL, position INTEGER NOT NULL, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS lessons(unit_id TEXT PRIMARY KEY, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS lesson_versions(unit_id TEXT NOT NULL, revision INTEGER NOT NULL, data TEXT NOT NULL, PRIMARY KEY(unit_id,revision));
            CREATE TABLE IF NOT EXISTS generation_drafts(id TEXT PRIMARY KEY, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS rewards(id TEXT PRIMARY KEY, course_id TEXT NOT NULL, points INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS progress(course_id TEXT PRIMARY KEY, unit_id TEXT NOT NULL, block_index INTEGER NOT NULL DEFAULT 0, version INTEGER NOT NULL DEFAULT 0, updated REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS reviews(event_id TEXT PRIMARY KEY, status TEXT NOT NULL, note TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY, course_id TEXT NOT NULL, unit_id TEXT NOT NULL, kind TEXT NOT NULL, data TEXT NOT NULL, created REAL NOT NULL, request_id TEXT UNIQUE NOT NULL, superseded INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS turns(id TEXT PRIMARY KEY, course_id TEXT NOT NULL, unit_id TEXT NOT NULL, data TEXT NOT NULL, created REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, dedup_key TEXT UNIQUE NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL, message TEXT NOT NULL DEFAULT '', result TEXT, error TEXT, created REAL NOT NULL, updated REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS requests(id TEXT PRIMARY KEY, result TEXT NOT NULL);
            ''')

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def put(self, table, key, data):
        assert table in {"documents", "courses"}
        with self.connection() as db:
            db.execute(f"INSERT OR REPLACE INTO {table}(id,data) VALUES(?,?)", (key, encode(data)))

    def get(self, table, key):
        assert table in {"documents", "courses"}
        with self.connection() as db:
            row = db.execute(f"SELECT data FROM {table} WHERE id=?", (key,)).fetchone()
        if not row:
            raise AppError("找不到这份资料或课程", "NOT_FOUND", 404)
        return json.loads(row[0])

    def all(self, table):
        assert table in {"documents", "courses"}
        with self.connection() as db:
            return [json.loads(r[0]) for r in db.execute(f"SELECT data FROM {table} ORDER BY rowid DESC")]

    def add_chunks(self, document_id, chunks):
        with self.connection() as db:
            db.execute("DELETE FROM chunks WHERE document_id=?", (document_id,))
            db.executemany("INSERT INTO chunks VALUES(?,?,?,?,?)", [(c["id"], document_id, c["page"], c["title"], c["text"]) for c in chunks])

    def chunks(self, document_id):
        with self.connection() as db:
            return [dict(r) for r in db.execute("SELECT * FROM chunks WHERE document_id=? ORDER BY page,rowid", (document_id,))]

    def chunk(self, chunk_id, document_id):
        with self.connection() as db:
            row = db.execute("SELECT * FROM chunks WHERE id=? AND document_id=?", (chunk_id, document_id)).fetchone()
        if not row:
            raise AppError("引用不属于当前资料", "SOURCE_UNAVAILABLE", 404)
        return dict(row)

    def create_course(self, course, units):
        with self.connection() as db:
            db.execute("INSERT INTO courses VALUES(?,?)", (course["id"], encode(course)))
            for i, unit in enumerate(units):
                db.execute("INSERT INTO units VALUES(?,?,?,?)", (unit["id"], course["id"], i, encode(unit)))
            db.execute("INSERT INTO progress VALUES(?,?,0,0,?)", (course["id"], units[0]["id"], time.time()))

    def units(self, course_id):
        with self.connection() as db:
            rows = db.execute("SELECT u.data,l.data AS lesson FROM units u LEFT JOIN lessons l ON u.id=l.unit_id WHERE course_id=? ORDER BY position", (course_id,)).fetchall()
        return [{**json.loads(r["data"]), "ready": bool(r["lesson"]) and json.loads(r["lesson"]).get("status", "ready") == "ready"} for r in rows]

    def unit(self, course_id, unit_id):
        with self.connection() as db:
            row = db.execute("SELECT data FROM units WHERE id=? AND course_id=?", (unit_id, course_id)).fetchone()
        if not row:
            raise AppError("这个学习单元不属于当前课程", "NOT_FOUND", 404)
        return json.loads(row[0])

    def lesson(self, unit_id):
        with self.connection() as db:
            r = db.execute("SELECT data FROM lessons WHERE unit_id=?", (unit_id,)).fetchone()
        return json.loads(r[0]) if r else None

    def save_lesson(self, unit_id, lesson):
        with self.connection() as db:
            db.execute("INSERT OR REPLACE INTO lessons VALUES(?,?)", (unit_id, encode(lesson)))

    def progress(self, course_id):
        with self.connection() as db:
            r = db.execute("SELECT * FROM progress WHERE course_id=?", (course_id,)).fetchone()
        if not r:
            raise AppError("课程不存在", "NOT_FOUND", 404)
        return dict(r)

    def generation(self, job_id):
        with self.connection() as db:
            r=db.execute('SELECT data FROM generation_drafts WHERE id=?',(job_id,)).fetchone()
        return json.loads(r[0]) if r else None

    def award(self, key, course_id):
        with self.connection() as db:
            inserted=db.execute('INSERT OR IGNORE INTO rewards VALUES(?,?,1)',(key,course_id)).rowcount
        return bool(inserted)

    def experience(self, course_id):
        with self.connection() as db:
            return db.execute('SELECT COALESCE(SUM(points),0) FROM rewards WHERE course_id=?',(course_id,)).fetchone()[0]

    def save_generation(self, job_id, data):
        with self.connection() as db:
            db.execute('INSERT OR REPLACE INTO generation_drafts VALUES(?,?)',(job_id,encode(data)))

    def replace_lesson(self, course_id, unit_id, lesson, expected_revision):
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT data FROM lessons WHERE unit_id=?', (unit_id,)).fetchone()
            old = json.loads(row[0]) if row else None
            if not old or old.get('revision', 0) != expected_revision:
                raise AppError('讲解已变化，请刷新后重试', 'VERSION_CONFLICT', 409)
            db.execute('INSERT OR IGNORE INTO lesson_versions VALUES(?,?,?)', (unit_id, expected_revision, encode(old)))
            lesson['revision'] = expected_revision + 1
            db.execute('UPDATE lessons SET data=? WHERE unit_id=?', (encode(lesson), unit_id))
            db.execute('UPDATE progress SET block_index=0,version=version+1 WHERE course_id=? AND unit_id=?', (course_id, unit_id))

    def lesson_versions(self, unit_id):
        with self.connection() as db:
            return [json.loads(r[0]) for r in db.execute('SELECT data FROM lesson_versions WHERE unit_id=? ORDER BY revision DESC', (unit_id,))]

    def move(self, course_id, req):
        self.unit(course_id, req.unit_id)
        request_key = f"progress:{course_id}:{req.request_id}"
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute("SELECT result FROM requests WHERE id=?", (request_key,)).fetchone()
            if existing:
                saved = json.loads(existing[0])
                if saved["request"] != req.model_dump():
                    raise AppError("同一请求标识不能用于不同操作", "REQUEST_CONFLICT", 409)
                return saved["result"]
            changed = db.execute("UPDATE progress SET unit_id=?,block_index=?,version=version+1,updated=? WHERE course_id=? AND version=?", (req.unit_id, req.block_index, time.time(), course_id, req.expected_version))
            if not changed.rowcount:
                raise AppError("学习位置已在另一页面更新，请同步后重试", "VERSION_CONFLICT", 409)
            result = dict(db.execute("SELECT * FROM progress WHERE course_id=?", (course_id,)).fetchone())
            db.execute("INSERT INTO requests VALUES(?,?)", (request_key, encode({"request": req.model_dump(), "result": result})))
        return result

    def events(self, course_id):
        with self.connection() as db:
            rows = db.execute("SELECT e.*, r.status AS review_status,r.note AS review_note FROM events e LEFT JOIN reviews r ON r.event_id=e.id WHERE course_id=? AND superseded=0 ORDER BY created DESC LIMIT 100", (course_id,)).fetchall()
        return [{**dict(r), "data": json.loads(r["data"])} for r in rows]

    def save_review(self, course_id, event_id, review):
        with self.connection() as db:
            updated = db.execute(
                "INSERT OR REPLACE INTO reviews(event_id,status,note) "
                "SELECT id,?,? FROM events WHERE id=? AND course_id=? AND superseded=0",
                (review.status, review.note, event_id, course_id))
            if not updated.rowcount:
                raise AppError("找不到这条学习记录", "NOT_FOUND", 404)

    def turn(self, course_id, turn_id):
        with self.connection() as db:
            row = db.execute("SELECT id,data FROM turns WHERE course_id=? AND id=?", (course_id, turn_id)).fetchone()
        if not row:
            raise AppError("找不到这次问答", "NOT_FOUND", 404)
        return {"id": row["id"], "data": json.loads(row["data"])}

    def add_event(self, course_id, unit_id, kind, data, request_id, target_id=None):
        self.unit(course_id, unit_id)
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute("SELECT * FROM events WHERE request_id=?", (request_id,)).fetchone()
            if existing:
                if (existing['course_id'], existing['unit_id'], existing['kind'], json.loads(existing['data'])) != (course_id, unit_id, kind, {**data, 'target_id': target_id}):
                    raise AppError("同一请求标识不能用于不同记录", "REQUEST_CONFLICT", 409)
                return existing['id']
            if target_id:
                target = db.execute("SELECT id FROM events WHERE id=? AND course_id=? AND unit_id=? AND superseded=0", (target_id, course_id, unit_id)).fetchone()
                if not target:
                    raise AppError("这条学习记录已被更正或不属于当前单元", "VERSION_CONFLICT", 409)
                db.execute("UPDATE events SET superseded=1 WHERE id=?", (target_id,))
            event_id = uid("event")
            db.execute("INSERT INTO events VALUES(?,?,?,?,?,?,?,0)", (event_id, course_id, unit_id, kind, encode({**data, "target_id": target_id}), time.time(), request_id))
        return event_id

    def turns(self, course_id, unit_id=None):
        with self.connection() as db:
            if unit_id:
                rows = db.execute("SELECT * FROM turns WHERE course_id=? AND unit_id=? ORDER BY created DESC LIMIT 12", (course_id, unit_id)).fetchall()
            else:
                rows = db.execute("SELECT * FROM turns WHERE course_id=? ORDER BY created DESC LIMIT 12", (course_id,)).fetchall()
        return [{**dict(r), "data": json.loads(r["data"])} for r in reversed(rows)]

    def save_turn(self, turn_id, course_id, unit_id, data):
        with self.connection() as db:
            db.execute("INSERT OR REPLACE INTO turns VALUES(?,?,?,?,?)", (turn_id, course_id, unit_id, encode(data), time.time()))

    def new_job(self, key, kind, payload):
        with self.connection() as db:
            db.execute("INSERT OR IGNORE INTO jobs(id,dedup_key,kind,payload,status,created,updated) VALUES(?,?,?,?,?,?,?)", (uid("job"), key, kind, encode(payload), "queued", time.time(), time.time()))
            row = db.execute("SELECT id,payload FROM jobs WHERE dedup_key=?", (key,)).fetchone()
            if json.loads(row["payload"]) != payload:
                raise AppError("同一请求标识不能用于不同内容", "REQUEST_CONFLICT", 409)
        return self.job(row[0])

    def job(self, job_id):
        with self.connection() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not row:
            raise AppError("找不到任务", "NOT_FOUND", 404)
        result = dict(row)
        for key in ["payload", "result", "error"]:
            result[key] = json.loads(result[key]) if result[key] else None
        return result

    def update_job(self, job_id, status, message="", result=None, error=None):
        with self.connection() as db:
            db.execute("UPDATE jobs SET status=?,message=?,result=?,error=?,updated=? WHERE id=?", (status, message, encode(result) if result is not None else None, encode(error) if error else None, time.time(), job_id))

    def interrupt_running(self):
        with self.connection() as db:
            db.execute("UPDATE jobs SET status='interrupted',message='服务已重启，可从已保存内容继续',updated=? WHERE status IN ('running','queued')", (time.time(),))
