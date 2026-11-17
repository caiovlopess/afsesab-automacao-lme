(function () {
  'use strict';
  const form = document.getElementById('form');
  const error = document.getElementById('error');
  const btn = document.getElementById('btn');

  async function doLogin() {
    error.textContent = '';
    btn.disabled = true;
    btn.textContent = 'Entrando…';
    try {
      const result = await window.afAuth.submit(
        document.getElementById('user').value.trim(),
        document.getElementById('pass').value,
      );
      await window.afAuth.openMain(result);
    } catch (err) {
      error.textContent = 'Usuário ou senha inválidos.';
      btn.disabled = false;
      btn.textContent = 'Entrar';
    }
  }

  btn.addEventListener('click', doLogin);
  form.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') doLogin();
  });
})();
