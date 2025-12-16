/**
 * Bank Payment Bulk Upload Form Scripts
 * 
 * Handles bulk PDF upload, multi-file selection, and background processing
 */

frappe.ui.form.on('Bank Payment Bulk Upload', {
	refresh: function(frm) {
		// Add bulk upload button for new documents or Queued status
		if (frm.is_new() || frm.doc.status === 'Queued') {
			frm.add_custom_button(__('Upload PDFs'), function() {
				show_bulk_upload_dialog(frm);
			}, __('Actions'));
		}
		
		// Add reprocess failed button if there are failed items
		if (!frm.is_new() && frm.doc.status !== 'Completed') {
			const failed_count = frm.doc.failed_count || 0;
			if (failed_count > 0) {
				frm.add_custom_button(__('Reprocess Failed'), function() {
					reprocess_failed(frm);
				}, __('Actions'));
			}
		}
		
		// Show progress indicator
		if (frm.doc.status === 'Processing' || frm.doc.status === 'Queued') {
			show_progress_indicator(frm);
		}
		
		// Auto-refresh if processing
		if (frm.doc.status === 'Processing') {
			setTimeout(function() {
				frm.reload_doc();
			}, 5000); // Refresh every 5 seconds
		}
		
		// Ensure submit button is visible for saved documents with items
		if (!frm.is_new() && frm.doc.docstatus === 0 && frm.doc.items && frm.doc.items.length > 0) {
			// Submit button should be visible by default
			// Make sure form is in editable state
			if (frm.doc.status === 'Queued' || frm.is_dirty()) {
				frm.enable_save();
			}
		}
	},
	
	onload: function(frm) {
		// Set default customer if available
		if (frm.is_new() && !frm.doc.customer) {
			// Try to get last used customer from localStorage
			const lastCustomer = localStorage.getItem('bank_payment_parser_last_customer');
			if (lastCustomer) {
				frm.set_value('customer', lastCustomer);
			}
		}
	},
	
	customer: function(frm) {
		// Save customer preference to localStorage
		if (frm.doc.customer) {
			localStorage.setItem('bank_payment_parser_last_customer', frm.doc.customer);
		}
	}
});

/**
 * Show bulk upload dialog
 */
function show_bulk_upload_dialog(frm) {
	// Ensure customer is set
	if (!frm.doc.customer) {
		frappe.msgprint({
			title: __('Customer Required'),
			message: __('Please select a customer before uploading files'),
			indicator: 'orange'
		});
		return;
	}
	
	// Save document first if it's new
	if (frm.is_new()) {
		frm.save().then(function() {
			show_upload_dialog(frm);
		}).catch(function() {
			frappe.msgprint(__('Please save the document first'));
		});
	} else {
		show_upload_dialog(frm);
	}
}

/**
 * Show the actual upload dialog
 */
function show_upload_dialog(frm) {
	
	const dialog = new frappe.ui.Dialog({
		title: __('Upload Multiple PDFs'),
		fields: [
			{
				fieldtype: 'HTML',
				options: `
					<div class="bulk-upload-area" style="border: 2px dashed #d1d8dd; padding: 20px; text-align: center; border-radius: 4px; margin: 10px 0;">
						<p style="margin: 10px 0; color: #6c7680;">
							<svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-bottom: 10px;">
								<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
								<polyline points="17 8 12 3 7 8"></polyline>
								<line x1="12" y1="3" x2="12" y2="15"></line>
							</svg>
							<br>
							${__('Drag and drop PDF / XML files here or click to browse')}
						</p>
						<input type="file" id="bulk-file-input" multiple accept=".pdf,.xml" style="display: none;">
						<button class="btn btn-primary" onclick="document.getElementById('bulk-file-input').click()">
							${__('Select Files')}
						</button>
					</div>
					<div id="file-list" style="margin-top: 15px; max-height: 300px; overflow-y: auto;"></div>
				`
			}
		],
		primary_action_label: __('Upload & Process'),
		primary_action: function() {
			upload_files(frm, dialog);
		}
	});
	
	// Setup file input handler
	setup_file_input(dialog, frm);
	
	dialog.show();
}

/**
 * Setup file input handler
 */
function setup_file_input(dialog, frm) {
	const file_input = dialog.$wrapper.find('#bulk-file-input')[0];
	const file_list = dialog.$wrapper.find('#file-list')[0];
	const selected_files = [];
	
	if (!file_input || !file_list) {
		console.error('File input or file list element not found');
		return;
	}
	
	// Click handler
	file_input.addEventListener('change', function(e) {
		if (e.target.files && e.target.files.length > 0) {
			handle_files(e.target.files, selected_files, file_list);
		}
	});
	
	// Drag and drop
	const upload_area = dialog.$wrapper.find('.bulk-upload-area')[0];
	
	if (upload_area) {
		upload_area.addEventListener('dragover', function(e) {
			e.preventDefault();
			e.stopPropagation();
			upload_area.style.borderColor = '#8dcdff';
			upload_area.style.backgroundColor = '#f0f9ff';
		});
		
		upload_area.addEventListener('dragleave', function(e) {
			e.preventDefault();
			e.stopPropagation();
			upload_area.style.borderColor = '#d1d8dd';
			upload_area.style.backgroundColor = '';
		});
		
		upload_area.addEventListener('drop', function(e) {
			e.preventDefault();
			e.stopPropagation();
			upload_area.style.borderColor = '#d1d8dd';
			upload_area.style.backgroundColor = '';
			
			if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
				handle_files(e.dataTransfer.files, selected_files, file_list);
			}
		});
	}
	
	// Store selected files in dialog - use a closure to maintain reference
	dialog.selected_files = selected_files;
	
	// Update file list display initially
	update_file_list(selected_files, file_list);
	
	// Debug: Log when files are selected
	console.log('Files selected:', selected_files.length);
}

/**
 * Handle selected files
 */
function handle_files(files, selected_files, file_list) {
	let added = 0;
	Array.from(files).forEach(file => {
		const name = file.name.toLowerCase();
		const mime = (file.type || '').toLowerCase();

		const is_pdf = mime === 'application/pdf' || name.endsWith('.pdf');
		const is_xml = mime === 'application/xml' || mime === 'text/xml' || name.endsWith('.xml');

		if (is_pdf || is_xml) {
			// Check if already selected
			if (!selected_files.find(f => f.name === file.name && f.size === file.size)) {
				selected_files.push(file);
				added++;
			}
		} else {
			console.warn('Skipping unsupported file (only PDF/XML allowed):', file.name);
		}
	});
	
	if (added > 0) {
		update_file_list(selected_files, file_list);
		console.log('Added', added, 'file(s). Total:', selected_files.length);
	} else if (files.length > 0) {
		frappe.show_alert({
			message: __('No new PDF/XML files to add'),
			indicator: 'orange'
		});
	}
}

/**
 * Update file list display
 */
function update_file_list(files, file_list) {
	if (files.length === 0) {
		file_list.innerHTML = '<p style="color: #6c7680; text-align: center;">No files selected</p>';
		return;
	}
	
	let html = '<table class="table table-bordered" style="width: 100%;">';
	html += '<thead><tr><th>File Name</th><th>Size</th><th></th></tr></thead>';
	html += '<tbody>';
	
	files.forEach((file, index) => {
		const size = (file.size / 1024).toFixed(2) + ' KB';
		html += `
			<tr>
				<td>${file.name}</td>
				<td>${size}</td>
				<td>
					<button class="btn btn-sm btn-danger" onclick="remove_file(${index})">
						${__('Remove')}
					</button>
				</td>
			</tr>
		`;
	});
	
	html += '</tbody></table>';
	file_list.innerHTML = html;
	
	// Setup remove handlers
	files.forEach((file, index) => {
		window.remove_file = function(idx) {
			files.splice(idx, 1);
			update_file_list(files, file_list);
		};
	});
}

/**
 * Upload files and add to bulk upload record
 * 
 * Simplified: Just collect files and call ONE backend API.
 * All file handling logic is in Python.
 */
function upload_files(frm, dialog) {
	// Get files from dialog - ensure it's an array
	const files = dialog.selected_files || [];
	
	if (!files || files.length === 0) {
		frappe.msgprint({
			title: __('No Files Selected'),
			message: __('Please select at least one PDF or XML file. Click "Select Files" or drag and drop files.'),
			indicator: 'orange'
		});
		return;
	}
	
	if (!frm.doc.customer) {
		frappe.msgprint({
			title: __('Customer Required'),
			message: __('Please select a customer'),
			indicator: 'orange'
		});
		return;
	}
	
	// Ensure document is saved first
	const bulk_upload_name = frm.doc.name;
	if (!bulk_upload_name) {
		// Save document first
		frm.save().then(function() {
			upload_files_to_backend(frm, dialog, frm.doc.name, files);
		}).catch(function() {
			frappe.msgprint(__('Please save the document first'));
		});
	} else {
		upload_files_to_backend(frm, dialog, bulk_upload_name, files);
	}
}

/**
 * Upload files to backend using single API call
 * 
 * Uses FormData to send files directly to our Python method.
 * No direct calls to /api/method/upload_file.
 */
function upload_files_to_backend(frm, dialog, bulk_upload_name, files) {
	// Disable the button to prevent double-click
	dialog.get_primary_btn().prop('disabled', true);
	dialog.get_primary_btn().text(__('Uploading...'));
	
	// Create FormData with files
	const form_data = new FormData();
	form_data.append('bulk_upload_name', bulk_upload_name);
	
	// Add all files with key "files" (Python will use getlist("files"))
	files.forEach(function(file) {
		form_data.append('files', file);
	});
	
	// Use jQuery AJAX to send FormData (frappe.call doesn't support file uploads directly)
	$.ajax({
		url: '/api/method/bank_payment_parser.api.bulk_upload.upload_bulk_files',
		type: 'POST',
		data: form_data,
		processData: false,
		contentType: false,
		headers: {
			'X-Frappe-CSRF-Token': frappe.csrf_token || frappe.boot.csrf_token
		},
		success: function(r) {
			dialog.hide();
			frm.reload_doc();
			
			// Parse response
			let response = r;
			if (typeof r === 'string') {
				try {
					response = JSON.parse(r);
				} catch (e) {
					console.error('Error parsing response:', e);
				}
			}
			
			if (response && response.message) {
				const uploaded = response.message.uploaded_count || 0;
				const failed = response.message.failed_count || 0;
				const errors = response.message.errors || [];
				
				if (failed > 0) {
					let error_msg = __('{0} file(s) uploaded successfully. {1} file(s) failed.', [uploaded, failed]);
					if (errors.length > 0) {
						error_msg += '\n\n' + errors.slice(0, 5).join('\n');
						if (errors.length > 5) {
							error_msg += '\n... and ' + (errors.length - 5) + ' more errors';
						}
					}
					frappe.msgprint({
						title: __('Upload Complete with Errors'),
						message: error_msg,
						indicator: 'orange'
					});
				} else {
					frappe.show_alert({
						message: __('{0} file(s) uploaded successfully', [uploaded]),
						indicator: 'green'
					});
				}
			}
		},
		error: function(r) {
			dialog.get_primary_btn().prop('disabled', false);
			dialog.get_primary_btn().text(__('Upload & Process'));
			
			let error_msg = __('Unknown error');
			if (r.responseJSON) {
				error_msg = r.responseJSON.message?.message || r.responseJSON.exc || r.responseJSON._error_message || error_msg;
			} else if (r.responseText) {
				try {
					const parsed = JSON.parse(r.responseText);
					error_msg = parsed.message?.message || parsed.exc || error_msg;
				} catch (e) {
					error_msg = r.responseText.substring(0, 200);
				}
			} else if (r.status) {
				error_msg = `HTTP ${r.status}: ${r.statusText || 'Request failed'}`;
			}
			
			frappe.msgprint({
				title: __('Upload Failed'),
				message: error_msg,
				indicator: 'red'
			});
		}
	});
}


/**
 * Reprocess failed files
 */
function reprocess_failed(frm) {
	frappe.confirm(
		__('Reprocess all failed files?'),
		function() {
			frappe.call({
				method: 'bank_payment_parser.api.bulk_upload.reprocess_failed',
				args: {
					bulk_upload_name: frm.doc.name
				},
				freeze: true,
				freeze_message: __('Reprocessing failed files...'),
				callback: function(r) {
					if (r.message && r.message.success) {
						frappe.show_alert({
							message: __('Reprocessing queued'),
							indicator: 'blue'
						});
						frm.reload_doc();
					}
				}
			});
		}
	);
}

/**
 * Show progress indicator
 */
function show_progress_indicator(frm) {
	const progress = frm.doc.processed_files / frm.doc.total_files * 100;
	
	frm.dashboard.add_indicator(
		__('Progress: {0} / {1} files processed ({2}%)', [
			frm.doc.processed_files,
			frm.doc.total_files,
			progress.toFixed(1)
		]),
		frm.doc.status === 'Processing' ? 'blue' : 'orange'
	);
	
	if (frm.doc.success_count > 0) {
		frm.dashboard.add_indicator(
			__('Success: {0}', [frm.doc.success_count]),
			'green'
		);
	}
	
	if (frm.doc.failed_count > 0) {
		frm.dashboard.add_indicator(
			__('Failed: {0}', [frm.doc.failed_count]),
			'red'
		);
	}
}
