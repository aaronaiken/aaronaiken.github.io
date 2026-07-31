/* Tidy notify / signup forms.
   Progressive enhancement: each form carries data-app + data-endpoint.
   On submit we validate the email, POST {email, app} as JSON to the endpoint
   (fire-and-forget), and flip the form into its "you're on the list" state.
   If no endpoint is configured yet, the success state still shows so the
   page previews correctly ahead of the Dispatch backend going live. */
(function () {
  var EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  function wire(form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var input = form.querySelector('input[type=email]');
      var email = (input && input.value || '').trim();
      if (!EMAIL.test(email)) {
        if (input) { input.focus(); input.reportValidity && input.reportValidity(); }
        return;
      }
      var app = form.getAttribute('data-app') || 'hub';
      var endpoint = form.getAttribute('data-endpoint') || '';
      if (endpoint) {
        try {
          fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: email, app: app })
          }).catch(function () {});
        } catch (_) {}
      }
      form.classList.add('is-done', 'done');
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    var forms = document.querySelectorAll('[data-tidy-notify]');
    for (var i = 0; i < forms.length; i++) wire(forms[i]);
  });
})();
