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
 */
function upload_files(frm, dialog) {
	// Get files from dialog - ensure it's an array
	const files = dialog.selected_files || [];
	
	console.log('Upload button clicked. Files selected:', files.length);
	
	if (!files || files.length === 0) {
		frappe.msgprint({
			title: __('No Files Selected'),
			message: __('Please select at least one PDF file. Click "Select Files" or drag and drop PDF files.'),
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
	
	// Disable the button to prevent double-click
	dialog.get_primary_btn().prop('disabled', true);
	dialog.get_primary_btn().text(__('Uploading...'));
	
	// Use existing record if saved, otherwise create new
	const bulk_upload_name = frm.doc.name || null;
	
	if (bulk_upload_name) {
		// Add files to existing record
		upload_file_contents(frm, bulk_upload_name, files, dialog);
	} else {
		// Create new record first
		frappe.call({
			method: 'bank_payment_parser.api.bulk_upload.create_bulk_upload',
			args: {
				customer: frm.doc.customer,
				files: files.map(f => ({
					name: f.name,
					size: f.size,
					type: f.type
				}))
			},
			freeze: true,
			freeze_message: __('Creating bulk upload record...'),
			callback: function(r) {
				if (r.message && r.message.success) {
					// Reload form with new record name, then upload files
					frm.reload_doc().then(function() {
						upload_file_contents(frm, frm.doc.name, files, dialog);
					});
				} else {
					dialog.get_primary_btn().prop('disabled', false);
					dialog.get_primary_btn().text(__('Upload & Process'));
					frappe.msgprint({
						title: __('Error'),
						message: __('Error creating bulk upload record: {0}', [r.message?.error || 'Unknown error']),
						indicator: 'red'
					});
				}
			},
			error: function(r) {
				dialog.get_primary_btn().prop('disabled', false);
				dialog.get_primary_btn().text(__('Upload & Process'));
				frappe.msgprint({
					title: __('Error'),
					message: __('Error creating bulk upload record: {0}', [r.message || 'Unknown error']),
					indicator: 'red'
				});
			}
		});
	}
}

/**
 * Upload file contents
 */
function upload_file_contents(frm, bulk_upload_name, files, dialog) {
	let uploaded = 0;
	const total = files.length;
	let upload_errors = [];
	
	// Upload files sequentially to avoid overwhelming the server
	function upload_next(index) {
		if (index >= total) {
			// All files processed
			dialog.hide();
			frm.reload_doc();
			
			if (upload_errors.length > 0) {
				frappe.msgprint({
					title: __('Upload Complete with Errors'),
					message: __('{0} file(s) uploaded successfully. {1} file(s) failed.', [
						total - upload_errors.length,
						upload_errors.length
					]),
					indicator: 'orange'
				});
			} else {
				frappe.show_alert({
					message: __('{0} file(s) uploaded successfully', [total]),
					indicator: 'green'
				});
			}
			return;
		}
		
		const file = files[index];
		const form_data = new FormData();
		form_data.append('file', file);
		form_data.append('is_private', 1);
		form_data.append('folder', 'Home');
		form_data.append('doctype', 'Bank Payment Bulk Upload Item');
		form_data.append('docname', bulk_upload_name);
		form_data.append('fieldname', 'pdf_file');
		
		// Use custom upload method for XML files to bypass MIME type restrictions
		const is_xml = file.name.toLowerCase().endsWith('.xml');
		if (is_xml) {
			form_data.append('method', 'bank_payment_parser.api.bulk_upload.upload_file_for_bulk_upload');
		}
		
		$.ajax({
			url: '/api/method/upload_file',
			type: 'POST',
			data: form_data,
			processData: false,
			contentType: false,
			headers: {
				'X-Frappe-CSRF-Token': frappe.csrf_token
			},
			success: function(r) {
				uploaded++;
				
				// Handle different response formats
				// Standard upload_file returns: {message: {file_url: "...", file_name: "..."}}
				// Custom method returns: {message: {file_url: "...", file_name: "...", name: "..."}}
				let file_url = null;
				let file_name = file.name;
				
				if (r && r.message) {
					// Check if message is a dict with file_url
					if (r.message.file_url) {
						file_url = r.message.file_url;
						file_name = r.message.file_name || file.name;
					}
					// Check if message is a File document (has name and file_url properties)
					else if (r.message.name && r.message.file_url) {
						file_url = r.message.file_url;
						file_name = r.message.file_name || file.name;
					}
					// Check if message itself is the file_url string
					else if (typeof r.message === 'string') {
						file_url = r.message;
					}
				}
				
				if (file_url) {
					// Add file to bulk upload item
					frappe.call({
						method: 'bank_payment_parser.api.bulk_upload.add_file_to_bulk_upload',
						args: {
							bulk_upload_name: bulk_upload_name,
							file_url: file_url,
							file_name: file_name
						},
						callback: function(add_r) {
							// Continue with next file
							upload_next(index + 1);
						},
						error: function(add_r) {
							console.error('Error adding file to bulk upload:', add_r);
							upload_errors.push(file.name);
							upload_next(index + 1);
						}
					});
				} else {
					console.error('Upload response missing file_url. Response:', r);
					upload_errors.push(file.name);
					upload_next(index + 1);
				}
			},
			error: function(r) {
				uploaded++;
				// Extract error message from various possible response formats
				let error_msg = 'Unknown error';
				if (r.responseJSON) {
					if (r.responseJSON.message) {
						if (typeof r.responseJSON.message === 'string') {
							error_msg = r.responseJSON.message;
						} else if (r.responseJSON.message.message) {
							error_msg = r.responseJSON.message.message;
						} else if (r.responseJSON.message.exc_type) {
							error_msg = `${r.responseJSON.message.exc_type}: ${r.responseJSON.message.exc || r.responseJSON.message.message || 'Unknown error'}`;
						}
					} else if (r.responseJSON.exc) {
						error_msg = r.responseJSON.exc;
					}
				} else if (r.responseText) {
					try {
						const parsed = JSON.parse(r.responseText);
						error_msg = parsed.message?.message || parsed.message || parsed.exc || error_msg;
					} catch (e) {
						error_msg = r.responseText.substring(0, 200); // Limit length
					}
				} else if (r.status) {
					error_msg = `HTTP ${r.status}: ${r.statusText || 'Request failed'}`;
				}
				
				console.error('Error uploading file:', file.name, error_msg);
				upload_errors.push(file.name);
				// Note: Server-side error logging happens in the API endpoint
				// Client-side errors are logged to console for debugging
				upload_next(index + 1);
			}
		});
	}
	
	// Start uploading
	upload_next(0);
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
