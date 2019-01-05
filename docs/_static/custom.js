$(document).ready(function() {
	// Tag various things with semantic classes so we can style them.
	// Ideally this should be done during HTML generation instead, but Sphinx does not make it easy to figure out how to do that.

	$("em[class*='property']")
		.filter(function (index) {
			return this.textContent.startsWith(' = ');
		}).each(function (index) {
			this.classList.add('py-value');
		});
	$('p')
		.filter(function (index) {
			return this.textContent.startsWith('Bases:');
		}).each(function (index) {
			this.classList.add('py-bases');
		});
	$("span[class*='pre']")
		.filter(function (index) {
			return this.textContent.startsWith('enum.');
		}).each(function (index) {
			// stick enum values inside a <details> tag so they can be collapsed
			const dd = this.closest('dd');

			const details = document.createElement('details');
			const summary = document.createElement('summary');
			summary.innerHTML = '<em>Values</em>';
			details.appendChild(summary);

			for (const child of dd.childNodes) {
				if (child.nodeName.toLowerCase() === 'dl') {
					child.remove();
					details.appendChild(child);
				}
			}

			dd.appendChild(details);
		});
});
