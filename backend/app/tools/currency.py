from app.domain.enums import DataSourceType
from app.domain.models import ConversionResult, CurrencyConversionInput
from app.tools.base import Tool
from app.tools.mock_data import FX_RATES


class MockCurrencyConversionTool(Tool[CurrencyConversionInput, ConversionResult]):
    name = "currency_conversion"
    description = "Convert using a static mock FX table. Not live market rates."
    input_model = CurrencyConversionInput

    async def _run(self, payload: CurrencyConversionInput) -> ConversionResult:
        src = payload.from_currency.upper()
        dst = payload.to_currency.upper()
        rate = FX_RATES.get((src, dst))
        if rate is None:
            # try via USD
            to_usd = FX_RATES.get((src, "USD"))
            usd_to = FX_RATES.get(("USD", dst))
            if to_usd is None or usd_to is None:
                raise ValueError(f"No mock FX rate for {src}->{dst}")
            rate = to_usd * usd_to
        converted = round(payload.amount * rate, 2)
        return ConversionResult(
            amount=payload.amount,
            from_currency=src,
            to_currency=dst,
            converted=converted,
            rate=rate,
            source_type=DataSourceType.mock,
        )


class RealCurrencyConversionTool(Tool[CurrencyConversionInput, ConversionResult]):
    name = "currency_conversion"
    description = "Live FX via Frankfurter."
    input_model = CurrencyConversionInput

    async def _run(self, payload: CurrencyConversionInput) -> ConversionResult:
        from app.tools.live_apis import frankfurter_rate

        src = payload.from_currency.upper()
        dst = payload.to_currency.upper()
        rate = await frankfurter_rate(src, dst)
        converted = round(payload.amount * rate, 2)
        return ConversionResult(
            amount=payload.amount,
            from_currency=src,
            to_currency=dst,
            converted=converted,
            rate=rate,
            source_type=DataSourceType.live,
        )
