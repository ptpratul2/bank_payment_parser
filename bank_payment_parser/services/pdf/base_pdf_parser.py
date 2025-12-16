"""Base PDF parser.

Thin wrapper over BaseParser to mark PDF-specific parsers.
"""
from bank_payment_parser.services.base_parser import BaseParser


class BasePDFParser(BaseParser):
	"""Base class for all PDF parsers.

	Adds a `parser_type` hint that can be stored on Bank Payment Advice.
	"""

	parser_type = "pdf"
	source_format = "Generic PDF"

