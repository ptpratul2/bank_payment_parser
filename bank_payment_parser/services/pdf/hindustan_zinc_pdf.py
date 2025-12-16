"""PDF parser wrapper for Hindustan Zinc.

Delegates to the existing HindustanZincParser implementation while
exposing PDF-specific metadata (parser_type, source_format).
"""
from typing import Dict, Any
from bank_payment_parser.services.hindustan_zinc import HindustanZincParser


class HindustanZincPDFParser(HindustanZincParser):
	"""Hindustan Zinc PDF parser.

	Keeps the existing parsing logic but tags the parser as PDF-specific.
	"""

	parser_type = "pdf"
	source_format = "Hindustan Zinc PDF"

	def parse(self) -> Dict[str, Any]:  # type: ignore[override]
		result = super().parse()
		# Ensure metadata is present
		result.setdefault("parser_type", self.parser_type)
		result.setdefault("source_format", self.source_format)
		return result

