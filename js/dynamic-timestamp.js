document.addEventListener('DOMContentLoaded', function() {
  const latestTimestampElement = document.querySelector('.latest-status .timestamp');

  if (latestTimestampElement) {
	const timestampValue = parseInt(latestTimestampElement.dataset.timestamp) * 1000; // Convert seconds to milliseconds
	const now = new Date().getTime();
	const difference = now - timestampValue;

	const seconds = Math.floor(difference / 1000);
	const minutes = Math.floor(seconds / 60);
	const hours = Math.floor(minutes / 60);
	const days = Math.floor(hours / 24);

	let timeAgo = '';

	if (days > 0) {
	  timeAgo = days + ' day' + (days === 1 ? '' : 's') + ' ago';
	} else if (hours > 0) {
	  timeAgo = hours + ' hour' + (hours === 1 ? '' : 's') + ' ago';
	} else if (minutes > 0) {
	  timeAgo = minutes + ' minute' + (minutes === 1 ? '' : 's') + ' ago';
	} else {
	  timeAgo = 'just now';
	}

	latestTimestampElement.textContent = timeAgo;
  }
});