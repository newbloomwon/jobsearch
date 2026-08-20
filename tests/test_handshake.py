import httpx
import pytest

from jobsearch_engine import JobQuery
from jobsearch_engine.providers.handshake import HandshakeProvider

_JOBS_HTML = """
<html><body>
  <div class="posting">
    <a href="/jobs/10086">Software Engineer Intern — Acme</a>
    <a href="/stu/jobs/10087">Data Analyst</a>
    <a href="/jobs/10087">Data Analyst (duplicate href style)</a>
    <a href="/career_fairs/42">Not a job link</a>
  </div>
</body></html>
"""


def _client(html=_JOBS_HTML, status=200, redirect_to=None):
    def handler(request: httpx.Request) -> httpx.Response:
        if redirect_to:
            if "login" in request.url.path:  # already on the login page
                return httpx.Response(200, text="<html>log in</html>")
            return httpx.Response(302, headers={"Location": redirect_to})
        return httpx.Response(status, text=html, headers={"Content-Type": "text/html"})

    return httpx.AsyncClient(
        transport=httpx.MockTransport(handler), follow_redirects=True
    )


def test_not_configured_without_session():
    provider = HandshakeProvider()
    assert provider.is_configured() is False
    assert "HANDSHAKE_SCHOOL" in provider.not_configured_reason()


def test_school_subdomain_extraction():
    provider = HandshakeProvider(school="https://usf.joinhandshake.com/", cookie="x=y")
    assert provider.school == "usf"
    assert provider.is_configured()


async def test_parses_job_links_from_html():
    provider = HandshakeProvider(school="usf", cookie="x=y", client=_client())
    jobs = await provider.search(JobQuery(keywords="engineer"))
    assert len(jobs) == 2
    assert jobs[0].title == "Software Engineer Intern — Acme"
    assert jobs[0].url == "https://usf.joinhandshake.com/jobs/10086"
    assert jobs[1].url.endswith("/stu/jobs/10087") or jobs[1].url.endswith("/jobs/10087")


async def test_login_redirect_reports_expired_session():
    provider = HandshakeProvider(
        school="usf", cookie="x=y", client=_client(redirect_to="/login/sso")
    )
    with pytest.raises(Exception, match="expired"):
        await provider.search(JobQuery(keywords="internship"))


async def test_unparsable_page_raises_clear_error():
    provider = HandshakeProvider(school="usf", cookie="x=y", client=_client(html="<div>React app root</div>"))
    with pytest.raises(Exception, match="no parsable postings"):
        await provider.search(JobQuery(keywords="internship"))


async def test_forbidden_raises_provider_error():
    provider = HandshakeProvider(school="usf", cookie="x=y", client=_client(status=403))
    with pytest.raises(Exception, match="403"):
        await provider.search(JobQuery(keywords="internship"))
