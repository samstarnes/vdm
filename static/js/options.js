function savePreference(key, value) {
	localStorage.setItem(key, JSON.stringify(value));
}

function loadPreference(key, defaultValue) {
	const value = localStorage.getItem(key);
	return value !== null ? JSON.parse(value) : defaultValue;
}

document.addEventListener('DOMContentLoaded', function() {
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

	const startInputs = [hours, minutes, seconds];
	const endInputs = [clipHours, clipMinutes, clipSeconds];
	const allInputs = [...startInputs, ...endInputs];

	let startTime = 0;
	let endTime = 0;

	// Load preferences
	const showAdvancedOptions = loadPreference('showAdvancedOptions', false);
	const extractAudio = loadPreference('extractAudio', false);
	const noPlaylist = loadPreference('noPlaylist', false);
	const clipEnabled = loadPreference('clipEnabled', false);

	console.log('Loaded preferences:', { showAdvancedOptions, extractAudio, noPlaylist, clipEnabled });

	function calculateSeconds(h, m, s) {
		return (parseInt(h) || 0) * 3600 + (parseInt(m) || 0) * 60 + (parseInt(s) || 0);
	}

	function formatDuration(totalSeconds) {
		const hours = Math.floor(totalSeconds / 3600);
		const minutes = Math.floor((totalSeconds % 3600) / 60);
		const seconds = totalSeconds % 60;
		return `${hours}h ${minutes}m ${seconds}s`;
	}

	function updateAdvancedOptionsVisibility(show) {
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
			if (clipDuration <= 10 && (clipHours === 0 && clipMinutes === 0)) {
				clipDurationDisplay.textContent = `Clip Duration: Invalid, must be <= 10 seconds.`
				clipSeconds.value = 10;
				console.warn('Invalid clip duration');
			}
		} else {
			clipDurationDisplay.textContent = `Clip Duration: ${formatDuration(clipDuration)}`;
			console.log('Clip duration updated:', formatDuration(clipDuration));
		}
	}

	function updateClipInputs(enabled) {
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

	function handleClipSecondsBlur() {
		let clipSecondsValue = parseInt(clipSeconds.value);
		const clipHoursValue = parseInt(clipHours.value) || 0;
		const clipMinutesValue = parseInt(clipMinutes.value) || 0;

		if (clipSecondsValue <= 10 && (clipHoursValue === 0 && clipMinutesValue === 0)) {
			clipSeconds.value = 10;
			console.log('Clip seconds adjusted to minimum: 10');
		}
		updateEndTime();
		updateClipDuration();
	}

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
			this.value = isChecked ? 'true' : 'false';
			savePreference('extractAudio', isChecked);
			console.log('Extract audio preference saved:', isChecked);
			this.value = this.checked;

			// Create or update hidden input for form submission
			let xaudiohiddenInput = document.getElementById('extractAudioHidden');
			if (!xaudiohiddenInput) {
				xaudiohiddenInput = document.createElement('input');
				xaudiohiddenInput.type = 'hidden';
				xaudiohiddenInput.id = 'extractAudioHidden';
				xaudiohiddenInput.name = 'extractAudio';
				this.parentNode.appendChild(xaudiohiddenInput);
			}
			xaudiohiddenInput.value = isChecked ? 'true' : 'false';

			if (isChecked) {
				const formData = new FormData();
				formData.append('url', document.getElementById('url').value);
				formData.append('extract_audio', 'true');

				fetch('/download', {
					method: 'POST',
					body: formData
				})
				.then(response => response.json())
				.then(data => {
					if (data.status === 'success' && data.download_url) {
						// Trigger the file download by making a GET request to fetch-file
						return fetch(data.download_url, {
							method: 'GET'
						});
					} else {
						throw new Error(data.message || 'Download failed');
					}
				})
				.then(response => response.blob())
				.then(blob => {
					// Create the download link
					const url = window.URL.createObjectURL(blob);
					const a = document.createElement('a');
					a.href = url;
					a.download = data.download_filename;
					document.body.appendChild(a);
					a.click();
					window.URL.revokeObjectURL(url);
					a.remove();
				})
				.catch(error => {
					console.error('Download failed:', error);
				});
			}
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
	clipSeconds.addEventListener('blur', handleClipSecondsBlur);

	// Initial setup
	updateClipInputs(clipEnabled); 
	if (clipEnabled) { 
		updateStartTime(); 
		updateEndTime(); 
	}
});

document.querySelector('form').addEventListener('submit', function (e) {
	e.preventDefault(); // Prevent default form submission

	const formData = new FormData(this);

	// Post the form data to the download route
	fetch('/download', {
		method: 'POST',
		body: formData
	})
	.then(response => {
		// Check if the response is OK (status code 200)
		if (!response.ok) {
			throw new error(`HTTP Error! status ${response.status}`);
		}
		return response.json(); // Parse the JSON response
	})
	.then(data => {
		if (data.status === 'success') {
			console.log(`Redirecting to fetch file from ${data.download_url}`);
			// Redirect to /fetch-file to trigger the download
			window.location.href = data.download_url;
		} else {
			// Show error message in the status div
			console.error(`Error from server`, data.message);
			document.getElementById(`status`).innerText = data.message;
		}
	});
});