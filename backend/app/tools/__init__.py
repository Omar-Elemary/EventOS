from app.core.config import get_settings
from app.tools.base import Tool, ToolError
from app.tools.budget_calculator import BudgetCalculatorTool
from app.tools.currency import MockCurrencyConversionTool, RealCurrencyConversionTool
from app.tools.risk_checker import RiskCheckerTool
from app.tools.schedule_conflicts import ScheduleConflictCheckerTool
from app.tools.vendor_search import MockVendorSearchTool, RealVendorSearchTool
from app.tools.venue_search import MockVenueSearchTool, RealVenueSearchTool
from app.tools.weather import MockWeatherLookupTool, RealWeatherLookupTool
from app.tools.web_research import MockWebResearchTool, RealWebResearchTool


class ToolRegistry:
    def __init__(self, *, use_mock: bool | None = None) -> None:
        mock = get_settings().use_mock_tools if use_mock is None else use_mock
        self.use_mock = mock
        self.venue_search = MockVenueSearchTool() if mock else RealVenueSearchTool()
        self.vendor_search = MockVendorSearchTool() if mock else RealVendorSearchTool()
        self.weather_lookup = MockWeatherLookupTool() if mock else RealWeatherLookupTool()
        self.currency_conversion = MockCurrencyConversionTool() if mock else RealCurrencyConversionTool()
        self.web_research = MockWebResearchTool() if mock else RealWebResearchTool()
        self.budget_calculator = BudgetCalculatorTool()
        self.schedule_conflict_checker = ScheduleConflictCheckerTool()
        self.risk_checker = RiskCheckerTool()

    def all_tools(self) -> list[Tool]:
        return [
            self.venue_search,
            self.vendor_search,
            self.weather_lookup,
            self.currency_conversion,
            self.web_research,
            self.budget_calculator,
            self.schedule_conflict_checker,
            self.risk_checker,
        ]


def default_registry() -> ToolRegistry:
    return ToolRegistry()


__all__ = ["Tool", "ToolError", "ToolRegistry", "default_registry"]
