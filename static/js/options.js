function savePreference(key, value) {
	console.log(`Saving preference: ${key} = ${JSON.stringify(value)}`);
	localStorage.setItem(key, JSON.stringify(value));
}

function loadPreference(key, defaultValue) {
	const value = localStorage.getItem(key);
	const loadedValue = value !== null ? JSON.parse(value) : defaultValue;
	console.log(`Loading preference: ${key} = ${JSON.stringify(loadedValue)}`);
	return loadedValue;
	// return value !== null ? JSON.parse(value) : defaultValue;
}

document.addEventListener('DOMContentLoaded', function() {
	console.log('DOM fully loaded and parsed');
	const toggleButton = document.getElementById('toggleAdvancedOptions');
	const advancedOptions = document.getElementById('advancedOptions');
	const extractAudioToggle = document.getElementById('extractAudioToggle');
	const noPlaylistToggle = document.getElementById('noPlaylistToggle');
	const clipToggle = document.getElementById('clipToggle');
	
	const hours = document.getElementById('hours');
	const minutes = document.getElementById('minutes');
	const seconds = document.getElementById('seconds');
	const result = document.getElementById('result');

	const clipHours = document.getElementById('clipHours');
	const clipMinutes = document.getElementById('clipMinutes');
	const clipSeconds = document.getElementById('clipSeconds');
	const clipResult = document.getElementById('clipResult');

	const clipDurationRow = document.getElementById('clipDurationRow');
	const clipDurationDisplay = document.getElementById('clipDurationDisplay');

	console.log('All DOM elements retrieved');

	const startInputs = [hours, minutes, seconds];
	const endInputs = [clipHours, clipMinutes, clipSeconds];
	const allInputs = [...startInputs, ...endInputs];

	let startTime = 0;
	let endTime = 0;

	// Load preferences
	const showAdvancedOptions = loadPreference('showAdvancedOptions', false);
	const extractAudio = loadPreference('extractAudio', false);
	extractAudioToggle.checked = extractAudio;
	const noPlaylist = loadPreference('noPlaylist', false);
	const clipEnabled = loadPreference('clipEnabled', false);

	console.log('Loaded preferences:', { showAdvancedOptions, extractAudio, noPlaylist, clipEnabled });

	function calculateSeconds(h, m, s) {
		const total = (parseInt(h) || 0) * 3600 + (parseInt(m) || 0) * 60 + (parseInt(s) || 0);
		console.log(`Calculated seconds: ${total} from h:${h}, m:${m}, s:${s}`);
		return total;
	}

	function formatDuration(totalSeconds) {
		const hours = Math.floor(totalSeconds / 3600);
		const minutes = Math.floor((totalSeconds % 3600) / 60);
		const seconds = totalSeconds % 60;
		const formatted = `${hours}h ${minutes}m ${seconds}s`;
		console.log(`Formatted duration: ${formatted} from ${totalSeconds} seconds`);
		return formatted;
	}

	function validateClipTiming() {
		if (clipToggle.checked) {
			const startTime = calculateSeconds(hours.value, minutes.value, seconds.value);
			const endTime = calculateSeconds(clipHours.value, clipMinutes.value, clipSeconds.value);
	        const duration = endTime - startTime;
            if (duration < 1) {
                alert("Clip duration must be at least 1 second");
                return false;
            }
            if (startTime >= endTime) {
                alert("End time must be greater than start time");
                return false;
            }
		}
		return true;
	}


	function updateAdvancedOptionsVisibility(show) {
		console.log(`Updating advanced options visibility: ${show}`);
		advancedOptions.style.display = show ? 'block' : 'none';
		toggleButton.textContent = show ? 'Hide Advanced Options' : 'Show Advanced Options';
	}

	function updateStartTime() {
		startTime = calculateSeconds(hours.value, minutes.value, seconds.value);
		result.textContent = `Start at: ${startTime} seconds`;
		updateEndTime(); // This will also update clipDuration
		console.log('Start time updated:', startTime);
	}

	function updateEndTime() {
		let clipDuration = calculateSeconds(clipHours.value, clipMinutes.value, clipSeconds.value);
		endTime = startTime + clipDuration;
		clipResult.textContent = `End at: ${endTime} seconds`;
		updateClipDuration(clipDuration);
		console.log('End time updated:', endTime);
	}

	function updateClipDuration(clipDuration) {
		if (isNaN(clipDuration)) {
			console.warn('Invalid clip duration');
			clipDurationDisplay.textContent = `Clip Duration: Invalid`;
		} else {
			clipDurationDisplay.textContent = `Clip Duration: ${formatDuration(clipDuration)}`;
			console.log('Clip duration updated:', formatDuration(clipDuration));
		}
	}

	function updateClipInputs(enabled) {
		console.log(`Updating clip inputs: ${enabled}`);
		allInputs.forEach(input => {
			if (input) {
				input.disabled = !enabled;
				console.log(`Input ${input.id} disabled: ${!enabled}`);
			} else {
				console.error(`Input element not found: ${input}`);
			}
		});
		
		if (clipDurationRow) {
			clipDurationRow.style.display = enabled ? 'flex' : 'none';
		} else {
			console.error('Clip duration row element not found');
		}
	}

	function handleInput(e) {
		let value = parseInt(e.target.value);
		const max = parseInt(e.target.max);
		const min = parseInt(e.target.min);

		if (isNaN(value)) value = 0; // Default to zero if NaN
		if (value > max) value = max; // Cap at max
		if (value < min) value = min; // Floor at min

		e.target.value = value;

		console.log(`Input ${e.target.id} changed to ${value}`);

		if ([clipHours, clipMinutes, clipSeconds].includes(e.target)) {
			updateStartTime(); // This will also update endTime and clipDuration
		} else {
			updateEndTime(); // This will update clipDuration
			updateStartTime()
		}
	}

	// function handleClipSecondsBlur() {
	// 	let clipSecondsValue = parseInt(clipSeconds.value);
	// 	const clipHoursValue = parseInt(clipHours.value) || 0;
	// 	const clipMinutesValue = parseInt(clipMinutes.value) || 0;

	// 	if (clipSecondsValue <= 10 && (clipHoursValue === 0 && clipMinutesValue === 0)) {
	// 		clipSeconds.value = 10;
	// 		console.log('Clip seconds adjusted to minimum: 10');
	// 	}
	// 	updateEndTime();
	// 	updateClipDuration();
	// }

	// Set initial states
	updateAdvancedOptionsVisibility(showAdvancedOptions);
	if (extractAudioToggle) extractAudioToggle.checked = extractAudio;
	if (noPlaylistToggle) noPlaylistToggle.checked = noPlaylist;
	if (clipToggle) {
		clipToggle.checked = clipEnabled;
		updateClipInputs(clipEnabled);
	}

	// Event Listeners
	if (toggleButton) {
		toggleButton.addEventListener('click', function() {
			const isVisible = advancedOptions.style.display === 'block';
			updateAdvancedOptionsVisibility(!isVisible);
			savePreference('showAdvancedOptions', !isVisible);
		});
	}

	if (extractAudioToggle) {
		extractAudioToggle.addEventListener('change', function() {
			const isChecked = this.checked;
			console.log(`Extract audio toggle changed: ${isChecked}`);
			this.value = isChecked ? 'true' : 'false';
			savePreference('extractAudio', isChecked);
			console.log('Extract audio preference saved:', isChecked);
			// this.value = this.checked;

			// Create or update hidden input for form submission
			let xaudiohiddenInput = document.getElementById('extractAudioHidden');
			if (!xaudiohiddenInput) {
				xaudiohiddenInput = document.createElement('input');
				xaudiohiddenInput.type = 'hidden';
				xaudiohiddenInput.id = 'extractAudioHidden';
				xaudiohiddenInput.name = 'extractAudio';
				this.parentNode.appendChild(xaudiohiddenInput);
				console.log('Created hidden input for extract audio');
			}
			xaudiohiddenInput.value = isChecked ? 'true' : 'false';
			console.log(`Set hidden input value to ${xaudiohiddenInput.value}`);

		});
	}

	if (noPlaylistToggle) {
		noPlaylistToggle.addEventListener('change', function() {
			savePreference('noPlaylist', this.checked);
			console.log('No playlist preference saved:', this.checked);
			this.value = this.checked;
		});
	}

	if (clipToggle) {
		clipToggle.addEventListener('change', function() {
			console.log('Clip toggle changed:', this.checked);
			savePreference('clipEnabled', this.checked);
			this.value = this.checked;
			updateClipInputs(this.checked);
			if (this.checked) { 
				updateStartTime();
				updateEndTime();
			} else { 
				result.textContent = '';
				clipResult.textContent = '';
				clipDurationDisplay.textContent = 'Clip Duration: 0h 0m 0s';
			}
		});
	}

	// Attach input event listeners
	allInputs.forEach(input => { 
		if (input) { 
			input.addEventListener('input', handleInput); 
		} 
	});

	// Blur event for clipSeconds
	// clipSeconds.addEventListener('blur', handleClipSecondsBlur);

	// Initial setup
	updateClipInputs(clipEnabled); 
	if (clipEnabled) { 
		updateStartTime(); 
		updateEndTime(); 
	}

	document.querySelector('form').addEventListener('submit', function (e) {
		e.preventDefault(); // Prevent default form submission

		if (!validateClipTiming()) {
			return;
		}

		const formData = new FormData(this);

		if (clipToggle.checked) {
			formData.append('clip_start', `${hours.value}:${minutes.value}:${seconds.value}`);
			formData.append('clip_end', `${clipHours.value}:${clipMinutes.value}:${clipSeconds.value}`);
			formData.append('hours', `${hours.value}`);
			formData.append('minutes', `${minutes.value}`);
			formData.append('seconds', `${hours.value}`);
			formData.append('clipHours', `${clipHours.value}`);
			formData.append('clipMinutes', `${clipMinutes.value}`);
			formData.append('clipSeconds', `${clipSeconds.value}`);
		}

		// Disable the submit button to prevent multiple submissions
		const submitButton = document.querySelector('button[type="submit"]');
		submitButton.disabled = true;
		console.log("Submitting form data:", Array.from(formData.entries()));

		// Post the form data to the download route
		fetch('/download', {
			method: 'POST',
			body: formData,
            headers: {
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content

            }
		})
		.then(response => response.json())
		.then(data => {
			// Re-enable the submit button after response
			submitButton.disabled = false;
			if (data.status === 'success') {
				console.log(`Redirecting to fetch file from ${data.download_url}`);
			// Check if audio extraction is enabled
				if (extractAudioToggle.checked) {
				// Create and display the audio download button
					const audioDownloadBtn = document.createElement('a');
					audioDownloadBtn.href = data.download_url;
					audioDownloadBtn.className = 'btn';
					audioDownloadBtn.textContent = 'Download Audio';
					audioDownloadBtn.download = data.download_filename;
					audioDownloadBtn.style = 'color:rgb(255,255,255)!important'

					// Need a spacer
					const spacer1 = document.createElement('br');
					const spacer2 = document.createElement('br');

					// Insert the button after the main download button
					const mainDownloadBtn = document.querySelector('button.btn[type="submit"]');
					if (mainDownloadBtn) {
        				mainDownloadBtn.parentNode.insertBefore(spacer1, mainDownloadBtn.nextSibling);
        				mainDownloadBtn.parentNode.insertBefore(spacer2, spacer1.nextSibling);
        				mainDownloadBtn.parentNode.insertBefore(audioDownloadBtn, spacer2.nextSibling);
        			} else {
						console.error('Main download button not found');
						document.querySelector('form').appendChild(spacer1);
						document.querySelector('form').appendChild(spacer2);
						document.querySelector('form').appendChild(audioDownloadBtn);
					}
					// Remove the button after 5 minutes
					setTimeout(() => {
						spacer1.remove();
						spacer2.remove();
						audioDownloadBtn.remove();
				}, 300000); // 5 minutes in milliseconds
				} else {
					// Regular video download logic
					window.location.href = data.download_url;
				}
			} else {
				console.error(`Error from server`, data.message);
				document.getElementById('status').innerText = data.message;
			}
		})
		.catch(error => {
			console.error('Download failed:', error);
			document.getElementById('status').innerText = 'Download failed: ' + error.message;
			// Re-enable the submit button on error
			submitButton.disabled = false;

		});
	});	
});