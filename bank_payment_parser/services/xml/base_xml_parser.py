"""Base XML parser for remittance formats (e.g. cXML)."""
from typing import Optional
import xml.etree.ElementTree as ET


class BaseXMLParser:
	parser_type = "cxml"
	source_format = "Generic cXML"

	def __init__(self, xml_text: str, customer_name: Optional[str] = None):
		self.raw_xml = xml_text or ""
		self.customer_name = customer_name
		self.parse_version = "1.0"
		self.root = None
		if self.raw_xml.strip():
			self.root = ET.fromstring(self.raw_xml)

	def _find(self, path: str, namespaces=None):
		return self.root.find(path, namespaces or {}) if self.root is not None else None

	def _findall(self, path: str, namespaces=None):
		return self.root.findall(path, namespaces or {}) if self.root is not None else []

	def parse(self):  # pragma: no cover - abstract
		raise NotImplementedError

