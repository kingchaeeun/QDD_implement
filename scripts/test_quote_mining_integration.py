"""
Quick manual test for the quote-mining distortion classifier integration.

Run from the project root:

    cd quote-origin-pipeline
    python scripts/test_quote_mining_integration.py

This does NOT hit Google CSE or the full pipeline; it only checks that
the QuoteMiningDetection checkpoint can be loaded and used for scoring
one (quote, origin-span) pair.
"""

from qdd2.quote_mining import score_quote_pair


def main() -> None:
    # Simple English example pair; adjust freely for experimentation.
    quote = "The economy is declining."
    origin_span = "The president said the economy might slow down in the future, but it is not declining yet."

    print("Quote:", quote)
    print("Origin span:", origin_span)
    print("-" * 80)

    result = score_quote_pair(quote_text=quote, origin_span_text=origin_span)
    print("Distortion scoring result:")
    for k, v in result.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()


