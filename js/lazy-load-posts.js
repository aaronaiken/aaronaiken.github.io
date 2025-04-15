document.addEventListener('DOMContentLoaded', () => {
  const listItems = document.querySelectorAll('.older-updates-list .older-status-item');

  const observer = new IntersectionObserver((entries, observer) => {
	entries.forEach(entry => {
	  if (entry.isIntersecting) {
		entry.target.classList.add('loaded');
		observer.unobserve(entry.target); // Stop observing once loaded
	  }
	});
  }, {
	root: null,
	rootMargin: '0px',
	threshold: 0.5 // Trigger when at least 50% of the item is visible
  });

  listItems.forEach(item => {
	observer.observe(item);
  });
});