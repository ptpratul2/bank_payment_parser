"""Generic PDF parser wrapper.

Uses the existing GenericParser but adds PDF-specific hints.
"""
from typing import Dict, Any
from bank_payment_parser.services.generic_parser import GenericParser


class GenericPDFParser(GenericParser):
	parser_type = "pdf"
	source_format = "Generic PDF"

	def parse(self) -> Dict[str, Any]:  # type: ignore[override]
		result = super().parse()
		result.setdefault("parser_type", self.parser_type)
		result.setdefault("source_format", self.source_format)
		return result

