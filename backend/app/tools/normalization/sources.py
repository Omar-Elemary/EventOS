from app.domain.enums import SourceTier

OFFICIAL_HOSTS = (
    "eeca.gov.eg",
    "alexandria.gov.eg",
    "mota.gov.eg",
    "cairo.gov.eg",
    "sis.gov.eg",
    "gov.eg",
)

TRUSTED_HOSTS = (
    "cvent.com",
    "marriott.com",
    "hilton.com",
    "ihg.com",
    "hyatt.com",
    "ave.eg",
    "tripadvisor.com",
    "booking.com",
)


def source_tier_from_url(url: str | None) -> SourceTier:
    host = (url or "").lower()
    if any(h in host for h in OFFICIAL_HOSTS):
        return SourceTier.official
    if any(h in host for h in TRUSTED_HOSTS):
        return SourceTier.trusted
    if host:
        return SourceTier.web
    return SourceTier.mock


def confidence_for_tier(tier: SourceTier) -> float:
    return {
        SourceTier.official: 0.95,
        SourceTier.trusted: 0.75,
        SourceTier.web: 0.45,
        SourceTier.mock: 0.7,
    }.get(tier, 0.5)
