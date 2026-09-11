from app.tools.normalization.location import bilingual_queries, normalize_location


def test_normalize_arabic_and_typos():
    assert normalize_location("alexendria").city == "Alexandria"
    assert normalize_location("الإسكندرية").city == "Alexandria"
    assert normalize_location("التجمع الخامس").city == "New Cairo"
    assert normalize_location("القاهرة").city == "Cairo"
    assert normalize_location("الجيزة").city == "Giza"
    assert normalize_location("Cairo").country == "Egypt"


def test_normalize_hurghada():
    assert normalize_location("Hurghada").city == "Hurghada"
    assert normalize_location("الغردقة").city == "Hurghada"


def test_bilingual_queries_include_arabic():
    qs = bilingual_queries("conference venue", "Cairo", extra="500")
    blob = " ".join(qs)
    assert "Cairo" in blob
    assert "القاهرة" in blob
