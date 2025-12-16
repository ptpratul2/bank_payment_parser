"""cXML PaymentRemittanceRequest parser (namespace-agnostic).

Parses Ariba-style cXML PaymentRemittanceRequest into the standard
Bank Payment Advice structure used by bank_payment_parser.

This implementation is deliberately conservative and avoids XML
namespaces so it works with both namespaced and non-namespaced
PaymentRemittanceRequest documents.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional
import xml.etree.ElementTree as ET

from .base_xml_parser import BaseXMLParser


class CXMLPaymentRemittanceParser(BaseXMLParser):
    """Parser for cXML PaymentRemittanceRequest documents."""

    source_format = "Ariba cXML PaymentRemittanceRequest"

    def _iter(self, parent: ET.Element, tag: str):
        """Yield child elements whose local-name matches `tag`.

        This is namespace-agnostic: it strips any `{ns}` prefix from
        the element tag before comparing.
        """
        for el in parent.iter():
            # el.tag may look like '{namespace}TagName' or 'TagName'
            full = el.tag
            if isinstance(full, str):
                if full.endswith(tag) and ("{" not in full or full.split("}")[-1] == tag):
                    yield el

    def _find_first(self, parent: ET.Element, tag: str) -> Optional[ET.Element]:
        for el in self._iter(parent, tag):
            return el
        return None

    def parse(self) -> Dict[str, Any]:  # type: ignore[override]
        if not self.root:
            raise ValueError("Invalid or empty XML payload")

        # Locate PaymentRemittanceRequest element
        rem_req = self._find_first(self.root, "PaymentRemittanceRequest")
        if rem_req is None:
            raise ValueError("PaymentRemittanceRequest element not found in cXML")

        header_data = self._parse_header(rem_req)
        invoice_rows = self._parse_invoice_rows(rem_req)

        result: Dict[str, Any] = {
            "customer_name": header_data.get("customer_name"),
            "payment_document_no": header_data.get("payment_remittance_id"),
            "payment_date": header_data.get("payment_date"),
            "bank_reference_no": header_data.get("payment_reference_no"),
            "utr_rrn_no": header_data.get("utr_rrn_no"),
            "payment_amount": header_data.get("total_net_amount", 0.0),
            "beneficiary_name": header_data.get("beneficiary_name"),
            "beneficiary_account_no": header_data.get("beneficiary_account_no"),
            "bank_name": header_data.get("bank_name"),
            "currency": header_data.get("currency"),
            "remarks": None,
            "raw_text": None,
            "raw_xml": self.raw_text,  # entire XML payload
            "parser_used": "CXMLPaymentRemittanceRequest",
            "parse_version": "1.0.0",
            "parser_type": "cxml",
            "source_format": self.source_format,
            "invoice_table_data": invoice_rows,
        }
        return result

    def _parse_header(self, rem_req: ET.Element) -> Dict[str, Any]:
        data: Dict[str, Any] = {}

        hdr = rem_req
        # Attributes on PaymentRemittanceRequestHeader
        hdr_el = self._find_first(rem_req, "PaymentRemittanceRequestHeader")
        if hdr_el is not None:
            data["payment_remittance_id"] = hdr_el.get("paymentRemittanceID")
            data["payment_reference_no"] = hdr_el.get("paymentReferenceNumber")
            data["payment_date"] = hdr_el.get("paymentDate")

            # UTR / RRN from Extrinsic under header
            utr = None
            for extr in self._iter(hdr_el, "Extrinsic"):
                name = (extr.get("name") or "").upper()
                text = (extr.text or "").strip()
                if "UTR" in name and text:
                    utr = text
                    break
            data["utr_rrn_no"] = utr

            # PaymentPartner contacts
            payer_name = None
            payee_name = None
            for contact in self._iter(hdr_el, "Contact"):
                role = (contact.get("role") or "").lower()
                name_el = self._find_first(contact, "Name")
                nm = (name_el.text or "").strip() if name_el is not None else None
                if role == "payer" and nm:
                    payer_name = nm
                if role == "payee" and nm:
                    payee_name = nm

            data["customer_name"] = self.customer_name or payer_name or payee_name
            data["beneficiary_name"] = payee_name
            data["beneficiary_account_no"] = None  # Not present in sample, reserved for future
            data["bank_name"] = None

        # Summary amounts
        currency = None
        total_net = Decimal("0")
        summary_el = self._find_first(rem_req, "PaymentRemittanceSummary")
        if summary_el is not None:
            money_el = self._find_first(summary_el, "Money")
            if money_el is not None and money_el.text:
                currency = money_el.get("currency")
                try:
                    total_net = Decimal(money_el.text.strip())
                except Exception:
                    total_net = Decimal(0)

        data["currency"] = currency
        data["total_net_amount"] = float(total_net)
        return data

    def _parse_invoice_rows(self, rem_req: ET.Element) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []

        for rd in self._iter(rem_req, "RemittanceDetail"):
            # Invoice number from InvoiceIDInfo/@invoiceID or text
            invoice_el = self._find_first(rd, "InvoiceIDInfo")
            invoice_id = None
            if invoice_el is not None:
                invoice_id = invoice_el.get("invoiceID") or (invoice_el.text or "").strip()

            # Gross and Net amounts
            gross_el = self._find_first(rd, "GrossAmount")
            gross_money = self._find_first(gross_el, "Money") if gross_el is not None else None
            net_el = self._find_first(rd, "NetAmount")
            net_money = self._find_first(net_el, "Money") if net_el is not None else None

            def as_amount(el: Optional[Any]) -> Optional[float]:
                if el is not None and getattr(el, "text", None):
                    try:
                        return float((el.text or "").strip())
                    except Exception:
                        return None
                return None

            gross_amount = as_amount(gross_money)
            net_amount = as_amount(net_money)

            # TDS / WCT from AdditionalDeduction
            tds_total = Decimal("0")
            for add in self._iter(rd, "AdditionalDeduction"):
                money_el = self._find_first(add, "Money")
                if money_el is not None and money_el.text:
                    try:
                        tds_total += Decimal(money_el.text.strip())
                    except Exception:
                        pass

            # Other Deductions / Security/Retention can be derived from
            # difference between gross and net minus tds, if needed.
            other_ded_sec = 0.0
            if gross_amount is not None and net_amount is not None:
                other_ded_sec = float(max(gross_amount - net_amount - float(tds_total), 0))

            # Fiscal year & company code from Extrinsic
            fiscal_year = None
            company_code = None
            for extr in self._iter(rd, "Extrinsic"):
                name = (extr.get("name") or "").lower()
                text = (extr.text or "").strip()
                if "fiscal" in name:
                    fiscal_year = text
                elif "companycode" in name or "companycode" in name.replace(" ", ""):
                    company_code = text

            rows.append({
                "invoice_number": invoice_id,
                "invoice_date": None,  # Not present in sample
                "tds_wct": float(tds_total),
                "other_deductions_security_retention": other_ded_sec,
                "invoice_amount": net_amount,
                "gross_amount": gross_amount,
                "tds_amount": float(tds_total),
                "currency": (gross_money.get("currency") if gross_money is not None else None),
                "fiscal_year": fiscal_year,
                "company_code": company_code,
            })

        return rows

