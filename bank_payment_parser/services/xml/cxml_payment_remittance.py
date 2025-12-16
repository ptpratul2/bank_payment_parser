"""cXML PaymentRemittanceRequest parser (namespace-agnostic).

Parses Ariba-style cXML PaymentRemittanceRequest into the standard
Bank Payment Advice structure used by bank_payment_parser.

This implementation avoids XML namespace prefixes so it works with
both namespaced and non-namespaced PaymentRemittanceRequest documents.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional
import xml.etree.ElementTree as ET

from .base_xml_parser import BaseXMLParser


class CXMLPaymentRemittanceParser(BaseXMLParser):
    """Parser for cXML PaymentRemittanceRequest documents."""

    source_format = "Ariba cXML Payment Remittance"

    def _iter(self, parent: ET.Element, tag: str):
        """Yield child elements whose local-name matches `tag`.

        This is namespace-agnostic: it strips any `{ns}` prefix from
        the element tag before comparing.
        """
        for el in parent.iter():
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

        root = self.root

        # Locate PaymentRemittanceRequest element
        rem_req = self._find_first(root, "PaymentRemittanceRequest")
        if rem_req is None:
            raise ValueError("PaymentRemittanceRequest element not found in cXML")

        header_data = self._parse_header(rem_req, root)
        invoice_rows = self._parse_invoice_rows(rem_req)

        # Normalise payment_date to a pure date (YYYY-MM-DD)
        payment_date = header_data.get("payment_date")
        if isinstance(payment_date, str) and "T" in payment_date:
            payment_date = payment_date.split("T", 1)[0]

        result: Dict[str, Any] = {
            "customer_name": header_data.get("customer_name"),
            "payment_document_no": header_data.get("payment_remittance_id"),
            "payment_date": payment_date,
            "bank_reference_no": header_data.get("payment_reference_no"),
            "utr_rrn_no": header_data.get("utr_rrn_no"),
            "payment_amount": header_data.get("total_net_amount", 0.0),
            "beneficiary_name": header_data.get("beneficiary_name"),
            "beneficiary_account_no": header_data.get("beneficiary_account_no"),
            "bank_name": header_data.get("bank_name"),
            "currency": header_data.get("currency"),
            "remarks": None,
            "raw_text": None,
            "raw_xml": self.raw_xml,
            "parser_used": self.__class__.__name__,
            "parse_version": self.parse_version,
            "parser_type": self.parser_type,
            "source_format": self.source_format,
            "invoice_table_data": invoice_rows,
            # Accounting fields
            "gross_payment_amount": header_data.get("gross_payment_amount", 0.0),
            "adjustment_amount": header_data.get("adjustment_amount", 0.0),
            "payment_method": header_data.get("payment_method"),
            "payer_name": header_data.get("payer_name"),
            "payer_city": header_data.get("payer_city"),
            "payload_id": header_data.get("payload_id"),
            "cxml_timestamp": header_data.get("cxml_timestamp"),
            "attached_pdf_reference": header_data.get("attached_pdf_reference"),
        }
        return result

    def _parse_header(self, rem_req: ET.Element, root: ET.Element) -> Dict[str, Any]:
        """Parse payment-level header data including accounting fields."""
        data: Dict[str, Any] = {}

        # Extract cXML root-level metadata
        if root is not None:
            data["payload_id"] = root.get("payloadID")
            data["cxml_timestamp"] = root.get("timestamp")
            data["cxml_version"] = root.get("version")

        # Header under Request/PaymentRemittanceRequestHeader
        hdr_el = self._find_first(rem_req, "PaymentRemittanceRequestHeader")
        if hdr_el is not None:
            data["payment_remittance_id"] = hdr_el.get("paymentRemittanceID")
            data["payment_reference_no"] = hdr_el.get("paymentReferenceNumber")
            data["payment_date"] = hdr_el.get("paymentDate")

            # Payment method
            payment_method_el = self._find_first(hdr_el, "PaymentMethod")
            if payment_method_el is not None:
                data["payment_method"] = payment_method_el.get("type", "").upper()

            # UTR / RRN from Extrinsic under header
            utr = None
            attached_pdf = None
            for extr in self._iter(hdr_el, "Extrinsic"):
                name = (extr.get("name") or "").upper()
                text = (extr.text or "").strip()
                if "UTR" in name and text:
                    utr = text
                # Check for attached PDF reference in Comments/Attachment
            data["utr_rrn_no"] = utr

            # PaymentPartner contacts (payer / payee)
            payer_name = None
            payer_city = None
            payee_name = None
            for contact in self._iter(hdr_el, "Contact"):
                role = (contact.get("role") or "").lower()
                name_el = self._find_first(contact, "Name")
                nm = (name_el.text or "").strip() if name_el is not None else None
                
                if role == "payer" and nm:
                    payer_name = nm
                    # Extract payer city from PostalAddress
                    addr_el = self._find_first(contact, "PostalAddress")
                    if addr_el is not None:
                        city_el = self._find_first(addr_el, "City")
                        if city_el is not None and city_el.text:
                            payer_city = city_el.text.strip()
                
                if role == "payee" and nm:
                    payee_name = nm

            data["customer_name"] = self.customer_name or payer_name or payee_name
            data["payer_name"] = payer_name
            data["payer_city"] = payer_city
            data["beneficiary_name"] = payee_name
            data["beneficiary_account_no"] = None
            data["bank_name"] = None

            # Check for attached PDF in Comments/Attachment
            comments_el = self._find_first(hdr_el, "Comments")
            if comments_el is not None:
                attachment_el = self._find_first(comments_el, "Attachment")
                if attachment_el is not None:
                    url_el = self._find_first(attachment_el, "URL")
                    if url_el is not None and url_el.text:
                        data["attached_pdf_reference"] = url_el.text.strip()

        # Summary amounts (PaymentRemittanceSummary)
        currency = None
        total_net = Decimal("0")
        total_gross = Decimal("0")
        total_adjustment = Decimal("0")
        summary_el = self._find_first(rem_req, "PaymentRemittanceSummary")
        if summary_el is not None:
            # NetAmount
            net_el = self._find_first(summary_el, "NetAmount")
            if net_el is not None:
                money_el = self._find_first(net_el, "Money")
                if money_el is not None and money_el.text:
                    currency = money_el.get("currency")
                    try:
                        total_net = Decimal(money_el.text.strip())
                    except Exception:
                        total_net = Decimal(0)
            
            # GrossAmount
            gross_el = self._find_first(summary_el, "GrossAmount")
            if gross_el is not None:
                money_el = self._find_first(gross_el, "Money")
                if money_el is not None and money_el.text:
                    try:
                        total_gross = Decimal(money_el.text.strip())
                    except Exception:
                        total_gross = Decimal(0)
            
            # AdjustmentAmount
            adj_el = self._find_first(summary_el, "AdjustmentAmount")
            if adj_el is not None:
                money_el = self._find_first(adj_el, "Money")
                if money_el is not None and money_el.text:
                    try:
                        total_adjustment = Decimal(money_el.text.strip())
                    except Exception:
                        total_adjustment = Decimal(0)

        data["currency"] = currency
        data["total_net_amount"] = float(total_net)
        data["gross_payment_amount"] = float(total_gross)
        data["adjustment_amount"] = float(total_adjustment)
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

            # Adjustment amount from AdjustmentAmount
            adjustment_amount = Decimal("0")
            adj_el = self._find_first(rd, "AdjustmentAmount")
            if adj_el is not None:
                adj_money = self._find_first(adj_el, "Money")
                if adj_money is not None and adj_money.text:
                    try:
                        adjustment_amount = Decimal(adj_money.text.strip())
                    except Exception:
                        adjustment_amount = Decimal(0)

            # Other Deductions / Security/Retention as residual difference
            other_ded_sec = 0.0
            if gross_amount is not None and net_amount is not None:
                other_ded_sec = float(max(gross_amount - net_amount - float(tds_total) - float(adjustment_amount), 0))

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
                "invoice_date": None,
                "tds_wct": float(tds_total),
                "other_deductions_security_retention": other_ded_sec,
                "invoice_amount": net_amount,
                "invoice_gross_amount": gross_amount,
                "invoice_net_amount": net_amount,
                "invoice_tds_amount": float(tds_total),
                "invoice_adjustment_amount": float(adjustment_amount),
                "gross_amount": gross_amount,  # Keep for backward compatibility
                "tds_amount": float(tds_total),  # Keep for backward compatibility
                "currency": (gross_money.get("currency") if gross_money is not None else None),
                "fiscal_year": fiscal_year,
                "company_code": company_code,
            })

        return rows

