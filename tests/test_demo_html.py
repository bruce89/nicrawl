import pytest

from nicrawl.sources.demo_html import PageStructureError, Scenario, load_scenario, parse_jobs


def test_basic_separates_valid_jobs_from_rejected_candidate() -> None:
    result = parse_jobs(load_scenario(Scenario.BASIC))
    assert result.candidates == 4
    assert [(job.source_job_id, job.title, job.company) for job in result.jobs] == [
        ("demo-01", "Python Developer", "Empresa Ejemplo"),
        ("demo-02", "iOS Engineer", "Laboratorio Sur"),
        ("demo-03", "Data Engineer", "Datos de Muestra"),
    ]
    assert result.jobs[0].source_url == "https://jobs.example/jobs/demo-01"
    assert result.jobs[0].salary_raw == "USD 80k–100k; período no indicado"
    assert len(result.rejections) == 1
    rejection = result.rejections[0]
    assert (rejection.candidate_index, rejection.source_job_id, rejection.field) == (
        4,
        "demo-04",
        "title",
    )


def test_optional_fields_remain_unknown() -> None:
    result = parse_jobs(load_scenario(Scenario.OPTIONAL_FIELDS))
    assert len(result.jobs) == 1
    assert result.rejections == ()
    job = result.jobs[0]
    assert job.location_raw is None
    assert job.salary_raw is None
    assert job.description_text is None


def test_unicode_entities_and_restrictions_are_preserved() -> None:
    job = parse_jobs(load_scenario(Scenario.UNICODE)).jobs[0]
    assert job.title == "Ingeniería C++ & Python"
    assert job.company == "Ñandú & Compañía"
    assert job.location_raw == "Remoto — US only"
    assert job.salary_raw is None
    assert job.description_text == "Diseñar sistemas confiables."


def test_text_preserves_inline_punctuation_and_separates_blocks() -> None:
    html = load_scenario(Scenario.OPTIONAL_FIELDS).replace(
        "</article>",
        '<div class="description"><p>Usar <strong>Python</strong>.</p>'
        "<p>C++<br>y SQL.</p></div></article>",
    )
    assert parse_jobs(html).jobs[0].description_text == "Usar Python. C++ y SQL."


def test_explicit_empty_page_succeeds() -> None:
    result = parse_jobs(load_scenario(Scenario.EMPTY))
    assert result.candidates == 0
    assert result.jobs == result.rejections == ()


@pytest.mark.parametrize(
    "html",
    [
        "<html><h1>Oops</h1></html>",
        '<main data-page="jobs" data-count="0"></main>',
        '<main data-page="jobs"><div data-job-list></div></main>',
        load_scenario(Scenario.BROKEN_LAYOUT),
        load_scenario(Scenario.EMPTY).replace('data-empty="true"', 'class="empty"'),
        load_scenario(Scenario.EMPTY).replace('data-count="0"', 'data-count="no"'),
        load_scenario(Scenario.EMPTY) + load_scenario(Scenario.EMPTY),
        load_scenario(Scenario.BASIC).replace("</main>", '<p data-empty="true">Vacía</p></main>'),
        load_scenario(Scenario.BASIC).replace(
            'class="job" data-id="demo-02"', 'class="vacancy" data-id="demo-02"'
        ),
    ],
    ids=[
        "missing-page",
        "missing-list",
        "missing-count",
        "changed-selector",
        "missing-empty-marker",
        "invalid-count",
        "two-pages",
        "contradictory-empty",
        "partially-changed-selector",
    ],
)
def test_structure_failures_never_look_like_successful_empty_collection(html: str) -> None:
    with pytest.raises(PageStructureError):
        parse_jobs(html)


def test_irrelevant_banner_does_not_change_extraction() -> None:
    html = load_scenario(Scenario.BASIC)
    changed = html.replace("<div data-job-list>", "<aside>Banner</aside><div data-job-list>")
    assert parse_jobs(changed) == parse_jobs(html)


def test_fields_are_scoped_to_their_own_card() -> None:
    html = load_scenario(Scenario.BASIC).replace('<p class="company">Empresa Ejemplo</p>', "")
    result = parse_jobs(html)
    assert [job.company for job in result.jobs] == ["Laboratorio Sur", "Datos de Muestra"]
    assert [(item.candidate_index, item.field) for item in result.rejections] == [
        (1, "company"),
        (4, "title"),
    ]
