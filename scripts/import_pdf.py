"""Import a PDF into the running local app and prepare only its first unit."""
import argparse
from pathlib import Path
import time
import httpx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('pdf', type=Path)
    args = parser.parse_args()
    with httpx.Client(base_url='http://127.0.0.1:8000', timeout=120, trust_env=False) as client:
        def wait(job):
            deadline = time.monotonic() + 300
            while job['status'] in ('queued', 'running'):
                if time.monotonic() > deadline:
                    raise RuntimeError('任务仍在处理，可在页面继续查看')
                time.sleep(.5)
                response = client.get('/api/jobs/' + job['id'])
                response.raise_for_status()
                job = response.json()
            if job['status'] != 'completed':
                raise RuntimeError(job.get('error', job['message']))
            return job['result']
        with args.pdf.open('rb') as f:
            response = client.post('/api/documents', files={'file': (args.pdf.name, f, 'application/pdf')})
        response.raise_for_status()
        result = wait(response.json())
        course = client.get('/api/courses/' + result['course_id']).json()
        unit = course['units'][0]
        response = client.post(f"/api/courses/{course['id']}/units/{unit['id']}/prepare")
        response.raise_for_status()
        wait(response.json())
        print({'course_id': course['id'], 'title': course['title'], 'pages': course['document']['pages'], 'units': len(course['units']), 'prepared': unit['title']})


if __name__ == '__main__':
    main()
