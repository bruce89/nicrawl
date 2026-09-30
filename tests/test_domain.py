from dataclasses import replace

import pytest

from nicrawl.domain import InvalidCandidate, JobCandidate, normalize_job, normalize_text

VALID = JobCandidate("id-1", "  Python\n Engineer ", " Ejemplo  &  Hijos ", "/jobs/id-1")


def test_normalization_keeps_meaning_and_does_not_mutate_input() -> None:
    draft = normalize_job(VALID, source_id="demo-html", base_url="https://jobs.example/")
    assert draft.title == "Python Engineer"
    assert draft.company == "Ejemplo & Hijos"
    assert draft.source_url == "https://jobs.example/jobs/id-1"
    assert VALID.title == "  Python\n Engineer "
    assert normalize_text("  C++\u00a0  Ñandú ") == "C++ Ñandú"
    assert normalize_text(" \n ") is None


@pytest.mark.parametrize("field", ["source_job_id", "title", "company", "href"])
def test_required_fields_reject_blanks(field: str) -> None:
    candidate = replace(VALID, **{field: "  "})
    with pytest.raises(InvalidCandidate) as caught:
        normalize_job(candidate, source_id="demo-html", base_url="https://jobs.example/")
    assert caught.value.field == ("source_url" if field == "href" else field)


@pytest.mark.parametrize(
    "href",
    [
        "javascript:alert(1)",
        "file:///secret",
        "https://",
        "https:missing-host",
        "//",
        "https://user:pass@jobs.example/",
        "https://jobs.example:99999/job",
        "https://[broken",
        "/bad path",
        "\nhttps://jobs.example/job",
        "https://jobs.example/\x1b[31m",
        "https://jobs.example\\evil/job",
    ],
)
def test_bad_links_are_rejected_instead_of_presented_as_source(href: str) -> None:
    with pytest.raises(InvalidCandidate, match="enlace"):
        normalize_job(
            replace(VALID, href=href), source_id="demo-html", base_url="https://jobs.example/"
        )
