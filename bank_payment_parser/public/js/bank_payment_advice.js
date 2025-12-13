/**
 * Bank Payment Advice Form Scripts
 * 
 * Handles PDF upload, customer selection, and parsing
 */

frappe.ui.form.on('Bank Payment Advice', {
	refresh: function(frm) {
		// Add custom button to parse PDF if not already parsed
		if (frm.doc.pdf_file && frm.doc.parse_status === 'Draft') {
			frm.add_custom_button(__('Parse PDF'), function() {
				parse_pdf(frm);
			});
		}
		
		// Show parser info if available
		if (frm.doc.parser_used) {
			frm.set_df_property('parser_used', 'description', 
				`Parser: ${frm.doc.parser_used} (v${frm.doc.parse_version || '1.0'})`);
		}
	},
	
	onload: function(frm) {
		// Load supported customers for dropdown
		if (frm.is_new()) {
			load_supported_customers(frm);
		}
	}
});

/**
 * Parse PDF file
 */
function parse_pdf(frm) {
	if (!frm.doc.pdf_file) {
		frappe.msgprint(__('Please upload a PDF file first'));
		return;
	}
	
	frappe.call({
		method: 'bank_payment_parser.api.upload.upload_and_parse',
		args: {
			file_url: frm.doc.pdf_file,
			customer: frm.doc.customer,
			use_ocr: false
		},
		freeze: true,
		freeze_message: __('Parsing PDF...'),
		callback: function(r) {
			if (r.message && r.message.success) {
				const data = r.message.parsed_data;
				
				// Update form fields
				if (data.payment_document_no) frm.set_value('payment_document_no', data.payment_document_no);
				if (data.payment_date) frm.set_value('payment_date', data.payment_date);
				if (data.bank_reference_no) frm.set_value('bank_reference_no', data.bank_reference_no);
				if (data.utr_rrn_no) frm.set_value('utr_rrn_no', data.utr_rrn_no);
				if (data.payment_amount) frm.set_value('payment_amount', data.payment_amount);
				if (data.currency) frm.set_value('currency', data.currency);
				if (data.beneficiary_name) frm.set_value('beneficiary_name', data.beneficiary_name);
				if (data.beneficiary_account_no) frm.set_value('beneficiary_account_no', data.beneficiary_account_no);
				if (data.bank_name) frm.set_value('bank_name', data.bank_name);
				if (data.remarks) frm.set_value('remarks', data.remarks);
				if (data.parser_used) frm.set_value('parser_used', data.parser_used);
				if (data.parse_version) frm.set_value('parse_version', data.parse_version);
				if (data.raw_text) frm.set_value('raw_text', data.raw_text);
				
				// Update parse status
				frm.set_value('parse_status', 'Parsed');
				
				// Add invoice details
				if (data.invoice_no && data.invoice_no.length > 0) {
					frm.clear_table('invoices');
					const invoice_nos = Array.isArray(data.invoice_no) ? data.invoice_no : [data.invoice_no];
					const invoice_dates = Array.isArray(data.invoice_date) ? data.invoice_date : 
						(data.invoice_date ? [data.invoice_date] : []);
					
					invoice_nos.forEach((inv_no, idx) => {
						const row = frm.add_child('invoices');
						row.invoice_number = inv_no;
						if (idx < invoice_dates.length) {
							row.invoice_date = invoice_dates[idx];
						}
						row.amount = data.payment_amount / invoice_nos.length;
					});
					frm.refresh_field('invoices');
				}
				
				frappe.show_alert({
					message: __('PDF parsed successfully using {0}', [data.parser_used || 'Generic Parser']),
					indicator: 'green'
				});
			} else {
				frm.set_value('parse_status', 'Error');
				frm.set_value('parsing_error', r.message?.error || 'Unknown error occurred');
				frappe.msgprint(__('Error parsing PDF. Please check the parsing error field.'));
			}
		},
		error: function(r) {
			frm.set_value('parse_status', 'Error');
			frm.set_value('parsing_error', r.message || 'Error occurred during parsing');
			frappe.msgprint(__('Error: {0}', [r.message || 'Unknown error']));
		}
	});
}

/**
 * Load supported customers for dropdown
 */
function load_supported_customers(frm) {
	frappe.call({
		method: 'bank_payment_parser.api.upload.get_supported_customers',
		callback: function(r) {
			if (r.message && r.message.customers) {
				// Store supported customers for reference
				frm.supported_customers = r.message.customers;
			}
		}
	});
}
